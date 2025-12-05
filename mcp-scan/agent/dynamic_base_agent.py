import os.path
import uuid
from datetime import datetime

from lmnr import Laminar

from tools.registry import get_tool_by_name, get_tools_prompt, needs_context
from utils.config import base_dir, get_env
from utils.llm import LLM
from utils.loging import logger
from utils.parse import parse_tool_invocations, clean_content, parse_mcp_invocations
from utils.tool_context import ToolContext
from utils.aig_logger import mcpLogger
from utils.mcp_tools import MCPTools

class DynamicBaseAgent:

    def __init__(self, name, instruction,target_prompt, llm: LLM, specialized_llms: dict = None, log_step_id=None, debug=False, agent_type:str = "test"):
        self.llm = llm
        self.name = name
        self.specialized_llms = specialized_llms or {}
        self.history = []
        self.max_iter = 20
        self.iter = 0
        self.is_finished = False
        self.step_id = log_step_id
        self.debug = debug
        self.repo_dir = ""
        self.agent_type = agent_type
        self.instruction = instruction
        self.target_prompt = target_prompt
        self.mcp_tools_manager = None
        if agent_type not in ["test","analyze"]:
            raise ValueError(f"Invalid agent_type: {agent_type}. Must be 'test' or 'analyze'.")

    def add_user_message(self, message: str):
        self.history.append({"role": "user", "content": message})

    def set_repo_dir(self, repo_dir):
        self.repo_dir = repo_dir

    def compact_history(self):
        if len(self.history) < 3:
            return
        with open(os.path.join(base_dir, "prompt", "compact.md"), "r") as f:
            prompt = f.read()
        history = self.history[1:]
        history.append({"role": "user", "content": prompt})
        response = self.llm.chat(history)

        system_prompt = self.history[0]
        user_messages = f"我希望你完成:{self.history[1]['content']} \n\n有以下上下文提供你参考:\n" + response
        self.history = [system_prompt, {"role": "user", "content": user_messages}]

    async def generate_system_prompt(self):
        await self._generate_system_prompt(self.name, self.instruction, self.target_prompt)

    async def _generate_system_prompt(self, name, instruction, target_prompt):
        
        with open(os.path.join(base_dir, "prompt", "dynamic_prompt.md"), "r") as f:
            system_prompt = f.read()
        # 集成工具 prompt，这里只需要使用 think 和 finish
        tools_prompt = get_tools_prompt(["think", "finish"])
        # 为了支持远程 MCP server 的 tools，尝试获取远端工具描述并拼接
        mcp_server = get_env("MCP_SERVER_URL")
        mcp_transport = get_env("MCP_TRANSPORT_PROTOCOL", "http")
        mcp_tools_section = ""
        if mcp_server and self.agent_type == "test":
            try:
                self.mcp_tools_manager = MCPTools(mcp_server,mcp_transport)
                mcp_tools_section = await self.mcp_tools_manager.describe_mcp_tools()
                logger.info(f"Fetched MCP tools description from server: {mcp_server}")
            except Exception:
                logger.error(Exception.__traceback__)
                raise Exception("Failed to fetch MCP tools description from server.")
        system_prompt = system_prompt.replace("{generate_tools}", tools_prompt)
        system_prompt = system_prompt.replace("{mcp_tools}", mcp_tools_section)

        system_prompt = system_prompt.replace("{name}", name)
        system_prompt = system_prompt.replace("{instruction}", instruction)
        system_prompt = system_prompt.replace("{target_prompt}", "```yaml\n" + target_prompt+"\n```")
        # 替换时间
        nowtime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        system_prompt = system_prompt.replace("${NOWTIME}", nowtime)
        logger.debug(f"Generated system prompt:\n {system_prompt}")
        self.history.append({"role": "system", "content": system_prompt})
        logger.info(system_prompt)


    def next_prompt(self):
        with open(os.path.join(base_dir, "prompt", "next_prompt.md"), "r") as f:
            next_prompt = f.read()
        return next_prompt.replace("{round}", str(self.iter))

    def execute_tool(self, tool_name: str, args: dict) -> str:
        tool_func = get_tool_by_name(tool_name)
        if tool_func is None:
            return f"Error: Tool '{tool_name}' not found"

        if needs_context(tool_name):
            context = ToolContext(
                llm=self.llm,
                history=self.history,
                agent_name=self.name,
                iteration=self.iter,
                specialized_llms=self.specialized_llms
            )
            args["context"] = context

        result = tool_func(**args)
        if isinstance(result, dict):
            ret = ""
            for k, v in result.items():
                ret += f"<{k}>{v}</{k}>\n"
            return ret
        return str(result)

    async def call_remote_tool(self, tool_call: dict) -> str:
        if self.mcp_tools_manager is None:
            raise Exception("MCP Tools Manager is not initialized.")

        try:
            result = await self.mcp_tools_manager.call_remote_tool(tool_call)
            return result
        except Exception as e:
            logger.error(f"Error calling remote tool: {e}")
            raise Exception(f"Failed to call remote tool: {str(e)}")
        
    def run(self):
        if self.debug:
            with Laminar.start_as_current_span(
                    name=self.name,  # name of the span
            ) as span:
                return self._run()
        else:
            return self._run()

    def _run(self):

        logger.info(f"Agent {self.name} started with max_iter={self.max_iter}")
        result = ""
        while not self.is_finished and self.iter < self.max_iter:
            self.iter += 1
            logger.debug(f"\n{'=' * 50}\nIteration {self.iter}\n{'=' * 50}")

            # 获取 LLM 响应
            try:
                response = self.llm.chat(self.history)
                logger.debug(f"LLM Response: {response}")

                # 添加到历史
                self.history.append({"role": "assistant", "content": response})

                # 解析工具调用
                tool_invocations = parse_tool_invocations(response)
                description = clean_content(response)
                if description == "":
                    description = "我将继续执行"
                mcpLogger.status_update(self.step_id, description, "", "running")
                if tool_invocations:
                    # 只处理第一个工具调用（按照规则单个响应只能调用一个工具）
                    tool_call = tool_invocations
                    tool_name = tool_call["toolName"]
                    tool_args = tool_call["args"]
                    tool_id = uuid.uuid4().__str__()

                    params = tool_args[list(tool_args.keys())[0]]
                    params = params.replace(self.repo_dir, "")

                    mcpLogger.tool_used(self.step_id, tool_id, tool_name, "doing", tool_name, f"{params}")
                    if tool_name == "finish":
                        self.is_finished = True
                        result = tool_args["content"]
                        logger.info(f"Finish tool called, returning:{result}")
                        mcpLogger.status_update(self.step_id, description, "", "completed")
                        mcpLogger.action_log(tool_id, tool_name, self.step_id, result)
                        mcpLogger.tool_used(self.step_id, tool_id, "报告整合", "done", tool_name)
                        continue

                    # 执行工具
                    tool_result = self.execute_tool(tool_name, tool_args)
                    # 格式化工具结果并添加到历史
                    result_message = f"<tool_name>{tool_name}</tool_name><tool_result>{tool_result}</tool_result>"

                    # 添加下一轮提示
                    next_prompt = self.next_prompt()
                    full_message = f"{next_prompt}\n\n{result_message}"

                    self.history.append({"role": "user", "content": full_message})
                    mcpLogger.status_update(self.step_id, description, "", "completed")
                    if tool_name != "read_file":
                        mcpLogger.action_log(tool_id, tool_name, self.step_id, f"```\n{result_message}\n```")
                    mcpLogger.tool_used(self.step_id, tool_id, tool_name, "done", tool_name, f"{params}")
                else:
                    mcp_tool_calls = parse_mcp_invocations(response)
                    if mcp_tool_calls:
                        # 没有工具调用，添加继续提示
                        mcpLogger.status_update(self.step_id, "Warning: No tool invocation found But MCP Tool Invocation Found", "", "completed")
                        next_prompt = self.next_prompt()
                        message = '''
                        Current Status: the MCP tool invocation found in response.Continue your next step.\n\n我将继续执行
                        '''
                        self.history.append({"role": "user", "content": f"{next_prompt}\n{message}"})
                    else:
                        # 没有工具调用，添加继续提示
                        mcpLogger.status_update(self.step_id, "Warning: No tool invocation found", "", "completed")
                        next_prompt = self.next_prompt()
                        message = '''
                        错误原因:No tool invocation found in response.
                        你的工具输出格式是否有误,请改正
                        ### tool format
                        <function=tool_name>
                        <parameter=param_name>value</parameter>
                        <parameter=param_name2>value2</parameter>
                        </function>
                        '''
                        self.history.append({"role": "user", "content": f"{next_prompt}\n{message}"})

            except Exception as e:
                logger.error(f"Error in iteration {self.iter}: {e}")
                error_message = f"Error occurred: {str(e)}. Please continue or adjust your approach. Please be careful not to confuse the invoking of <function> and <mcp_function>."
                self.history.append({"role": "user", "content": error_message})

        if self.iter >= self.max_iter:
            logger.warning(f"Max iterations ({self.max_iter}) reached")
            self.compact_history()

        logger.info("Agent execution completed")
        # 返回全部历史记录的拼接
        if self.agent_type == "test":
            return "\n".join([f"{msg['role'].upper()}:\n{msg['content']}" for msg in self.history])
        else:
            return result
    
import os.path
import time
import uuid
from datetime import datetime

from tools.registry import get_tool_by_name, get_tools_prompt, needs_context
from utils.config import base_dir
from utils.llm import LLM
from utils.loging import logger
from utils.parse import parse_tool_invocations, clean_content
from utils.tool_context import ToolContext
from utils.aig_logger import mcpLogger


class BaseAgent:

    def __init__(self, name, instruction, llm: LLM, specialized_llms: dict = None, log_step_id=None, output_language="",
                 debug=False, repo_dir=""):
        self.llm = llm
        self.name = name
        self.specialized_llms = specialized_llms or {}
        self.output_language = output_language
        self.history = [
            {"role": "system", "content": self.generate_system_prompt(name, instruction, repo_dir)}
        ]
        self.max_iter = 30
        self.iter = 0
        self.is_finished = False
        self.step_id = log_step_id
        self.debug = debug
        self.repo_dir = ""

    def add_user_message(self, message: str):
        self.history.append({"role": "user", "content": message})

    def compact_history(self):
        with open(os.path.join(base_dir, "prompt", "compact.md"), "r") as f:
            prompt = f.read()
        history = self.history[1:]
        history.append({"role": "user", "content": prompt})
        response = self.llm.chat(history)

        system_prompt = self.history[0]
        user_messages = f"我希望你完成:{self.history[1]['content']} \n\n有以下上下文提供你参考:\n" + response
        if self.output_language == "en":
            user_messages += "\n\nPlease respond in English"
        self.history = [system_prompt, {"role": "user", "content": user_messages}]

    def generate_system_prompt(self, name, instruction, repo_dir):
        with open(os.path.join(base_dir, "prompt", "system_prompt.md"), "r") as f:
            system_prompt = f.read()

        # 集成工具 prompt
        tools_prompt = get_tools_prompt()
        system_prompt = system_prompt.replace("{tools_prompt}", tools_prompt)

        system_prompt = system_prompt.replace("{name}", name)
        system_prompt = system_prompt.replace("{instruction}", instruction)
        system_prompt = system_prompt.replace("{repo_dir}", repo_dir)

        # 替换时间
        nowtime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        system_prompt = system_prompt.replace("${NOWTIME}", nowtime)

        if self.output_language == "en":
            system_prompt += "\n\nPlease respond in English"

        return system_prompt

    def next_prompt(self):
        # Simplified next prompt logic
        prompt = (
            f"current iteration {self.iter}. Please try to minimize the number of exchanges to obtain the result.Check "
            f"previous tool output. Decide next step.")

        if self.output_language == "en":
            prompt += "\nPlease respond in English"
        return prompt

    def execute_tool(self, tool_name: str, args: dict):
        """执行工具并返回结果，自动注入context（如果工具需要）"""
        tool_func = get_tool_by_name(tool_name)
        if tool_func is None:
            return f"Error: Tool '{tool_name}' not found"

        # 检查工具是否需要context参数
        if needs_context(tool_name):
            # 创建工具上下文
            context = ToolContext(
                llm=self.llm,
                history=self.history,
                agent_name=self.name,
                iteration=self.iter,
                specialized_llms=self.specialized_llms,
                repo_dir=self.repo_dir
            )
            args["context"] = context

        result = tool_func(**args)
        # 返回结果字符串
        if isinstance(result, dict):
            ret = ""
            for k, v in result.items():
                ret += f"{k}:{v}\n"
            return ret
        elif isinstance(result, bool):
            return True
        return str(result)

    def run(self):
        return self._run()

    def _run(self):
        logger.info(f"Agent {self.name} started with max_iter={self.max_iter}")
        result = ""
        while not self.is_finished and self.iter < self.max_iter:
            logger.debug(f"\n{'=' * 50}\nIteration {self.iter}\n{'=' * 50}")

            index = 0
            response = ""
            while index < 5:
                response = self.llm.chat(self.history)
                if response != "":
                    break
                logger.info(f"LLM response is empty, retrying...")
                time.sleep(0.5)
                index += 1
            logger.debug(f"LLM Response: {response}")
            if response == "":
                logger.error(f"LLM response is empty")
                continue

            # 获取 LLM 响应
            try:
                # 添加到历史
                self.history.append({"role": "assistant", "content": response})
                # 解析工具调用
                tool_invocations = parse_tool_invocations(response)
                description = clean_content(response)
                if description == "":
                    description = "我将继续执行"
                    if self.output_language == "en":
                        description = "I will continue"
                mcpLogger.status_update(self.step_id, description, "", "running")
                next_prompt = self.next_prompt()
                for tool_invocation in tool_invocations:
                    if tool_invocation:
                        # 只处理第一个工具调用（按照规则单个响应只能调用一个工具）
                        tool_call = tool_invocation
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
                            summary_result = "报告整合"
                            if self.output_language == "en":
                                summary_result = "Report Integration"
                            mcpLogger.tool_used(self.step_id, tool_id, summary_result, "done", tool_name)
                            return response

                        # 执行工具
                        tool_result = self.execute_tool(tool_name, tool_args)
                        if isinstance(tool_result, str):
                            # 格式化工具结果并添加到历史
                            result_message = f"<tool_name>{tool_name}</tool_name><tool_result>{tool_result}</tool_result>"
                            next_prompt += f"\n\nTools Result:\n{result_message}"
                        # 添加下一轮提示
                        mcpLogger.status_update(self.step_id, description, "", "completed")
                        if tool_name != "read_file" or tool_name != "think":
                            mcpLogger.action_log(tool_id, tool_name, self.step_id, f"```\n{next_prompt}\n```")
                        mcpLogger.tool_used(self.step_id, tool_id, tool_name, "done", tool_name, f"{params}")
                if len(tool_invocations) == 0:
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
                    if self.output_language == "en":
                        message = '''
Error reason:No tool invocation found in response.
Is your tool output format correct? Please correct it.
### tool format
<function=tool_name>
<parameter=param_name>value</parameter>
<parameter=param_name2>value2</parameter>
</function>
'''
                    next_prompt += f"\n\n{message}"
                self.history.append({"role": "user", "content": next_prompt})

            except Exception as e:
                logger.error(f"Error in iteration {self.iter}: {e}")
                error_message = f"Error occurred: {str(e)}. Please continue or adjust your approach."
                self.history.append({"role": "user", "content": error_message})

            if self.iter >= self.max_iter:
                logger.warning(f"Max iterations ({self.max_iter}) reached")
                self.compact_history()
                self.iter = 0

            logger.info("Agent execution completed")
            self.iter += 1
        return result

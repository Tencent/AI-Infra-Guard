import json
import uuid
from typing import Optional

from core.agent_adapter.adapter import ProviderOptions
from tools.dispatcher import ToolDispatcher
from utils.aig_logger import scanLogger
from utils.llm import LLM
from utils.logging import logger
from utils.parse import parse_tool_invocations, clean_content
from utils.prompt_manager import prompt_manager
from utils.tool_context import ToolContext


class BaseAgent:

    def __init__(
            self,
            name: str,
            instruction: str,
            llm: LLM,
            specialized_llms: dict = None,
            log_step_id: str = None,
            debug: bool = False,
            agent_provider: Optional[ProviderOptions] = None,
            language: str = "zh"
    ):
        self.llm = llm
        self.name = name
        self.specialized_llms = specialized_llms or {}
        self.instruction = instruction
        self.history = []
        self.max_iter = 80
        self.iter = 0
        self.is_finished = False
        self.step_id = log_step_id
        self.debug = debug
        self.repo_dir = ""
        self.agent_provider = agent_provider
        self.language = language
        self.dispatcher = ToolDispatcher()
        self.tool_usage_stats = {}

    async def initialize(self):
        """异步初始化系统提示词"""
        if not self.history:
            system_prompt = await self.generate_system_prompt()
            self.history.append({"role": "system", "content": system_prompt})

    def add_user_message(self, message: str):
        self.history.append({"role": "user", "content": message})

    def set_repo_dir(self, repo_dir: str):
        self.repo_dir = repo_dir

    def compact_history(self):
        if len(self.history) < 3:
            return

        prompt = prompt_manager.load_template("compact")
        history = self.history[1:]
        history.append({"role": "user", "content": prompt})
        response = self.llm.chat(history)

        system_prompt = self.history[0]
        user_messages = f"我希望你完成:{self.history[1]['content']} \n\n有以下上下文提供你参考:\n" + response
        self.history = [system_prompt, {"role": "user", "content": user_messages}]

    async def generate_system_prompt(self):

        tools_prompt = await self.dispatcher.get_all_tools_prompt()

        template_name = "system_prompt"
        format_kwargs = {
            "generate_tools": tools_prompt,
            "name": self.name,
            "instruction": self.instruction
        }

        return prompt_manager.format_prompt(template_name, **format_kwargs)

    def next_prompt(self):
        return prompt_manager.format_prompt("next_prompt", round=self.iter)

    async def run(self):
        await self.initialize()
        return await self._run()

    async def _run(self):
        logger.info(f"Agent {self.name} started with max_iter={self.max_iter}")
        result = ""
        while not self.is_finished and self.iter < self.max_iter:
            logger.debug(f"\n{'=' * 50}\nIteration {self.iter}\n{'=' * 50}")
            response = self.llm.chat(self.history)
            logger.debug(f"LLM Response: {response}")
            self.history.append({"role": "assistant", "content": response})
            res = await self.handle_response(response)
            if res is not None:
                result = res
            if self.iter >= self.max_iter:
                logger.warning(f"Max iterations ({self.max_iter}) reached")
                self.compact_history()
            self.iter += 1
        return result

    async def handle_response(self, response: str):
        tool_invocations = parse_tool_invocations(response)
        description = clean_content(response)
        if description == "":
            description = "我将继续执行"
            if self.language == "en":
                description = "I will continue to execute"

        scanLogger.status_update(self.step_id, description, "", "running")

        if tool_invocations:
            return await self.process_tool_call(tool_invocations, description)
        else:
            return await self.handle_no_tool(description)

    async def process_tool_call(self, tool_call: dict, description: str):
        tool_name = tool_call["toolName"]
        tool_args = tool_call["args"]
        tool_id = uuid.uuid4().__str__()

        params = json.dumps(tool_args, ensure_ascii=False) if tool_args else ""
        if isinstance(params, str):
            params = params.replace(self.repo_dir, "")

        scanLogger.tool_used(self.step_id, tool_id, tool_name, "done", tool_name, f"{params}")

        # Update stats
        if tool_name not in self.tool_usage_stats:
            self.tool_usage_stats[tool_name] = 0
        self.tool_usage_stats[tool_name] += 1

        if tool_name == "finish":
            self.is_finished = True
            brief_content = tool_args.get("content", "")
            # 如果定义了输出格式，则进行二次格式化
            result = await self._format_final_output()
            logger.info(f"Finish tool called, final result formatted.")
            scanLogger.status_update(self.step_id, description, "", "completed")
            # scanLogger.tool_used(self.step_id, tool_id, "报告整合", "done", tool_name, brief_content.split("\n")[0][:50])
            scanLogger.action_log(tool_id, tool_name, self.step_id, result)
            return result

        # 构造上下文
        context = ToolContext(
            llm=self.llm,
            history=self.history,
            agent_name=self.name,
            iteration=self.iter,
            specialized_llms=self.specialized_llms,
            folder=self.repo_dir,
            agent_provider=self.agent_provider,
        )

        # 通过 Dispatcher 调用工具
        tool_result = await self.dispatcher.call_tool(tool_name, tool_args, context)

        # 格式化工具结果并添加到历史
        result_message = f"{tool_result}"

        # 添加下一轮提示
        next_p = self.next_prompt()
        full_message = f"{next_p}\n---\n{result_message}"

        self.history.append({"role": "user", "content": full_message})
        logger.debug(f"Agent Response: {result_message}")

        scanLogger.status_update(self.step_id, description, "", "completed")

        if tool_name != "read_file":
            scanLogger.action_log(tool_id, tool_name, self.step_id, f"```\n{result_message}\n```")

        # scanLogger.tool_used(self.step_id, tool_id, tool_name, "done", tool_name, f"{params}")
        return None

    async def handle_no_tool(self, description: str):
        next_p = self.next_prompt()
        result_message = "You didn't call any tool,please call a tool"
        full_message = f"{next_p}\n\n{result_message}"
        logger.debug(f"Agent Response: {result_message}")
        self.history.append({"role": "user", "content": full_message})
        scanLogger.status_update(self.step_id, description, "", "completed")
        return None

    async def _format_final_output(self) -> str:
        """使用 LLM 根据历史记录和预设格式生成最终输出"""
        # 取最近的对话历史作为参考
        recent_history = self.history[1:]
        formatting_prompt = prompt_manager.format_prompt(
            "format_report",
            output_format=self.instruction
        )
        recent_history.append({"role": "user", "content": formatting_prompt})
        final_output = self.llm.chat(recent_history)
        logger.info(f"Final Output: {final_output}")
        return final_output


async def run_agent(description: str, instruction: str, llm: LLM, prompt: str, stage_id: str,
                    specialized_llms: dict | None = None, agent_provider: ProviderOptions | None = None,
                    language: str = "zh", repo_dir: str | None = None, context_data: dict | None = None):
    logger.info(f"=== 阶段 {stage_id}: {description} ===")
    scanLogger.new_plan_step(stepId=stage_id, stepName=description)

    # 初始化阶段 Agent
    agent = BaseAgent(
        name=f"{description}",
        instruction=instruction,
        llm=llm,
        specialized_llms=specialized_llms,
        log_step_id=stage_id,
        debug=True,
        agent_provider=agent_provider,
        language=language
    )
    user_msg = ""
    await agent.initialize()
    if repo_dir:
        agent.set_repo_dir(repo_dir)
        user_msg = f"请进行{description}，文件夹在 {repo_dir}\n"
    if prompt:
        user_msg += f"{prompt}\n"
    if context_data:
        user_msg += "\n\n有以下背景信息：\n"
        for key, value in context_data.items():
            user_msg += f"{key}:{value}\n\n"

    agent.add_user_message(user_msg)

    # 运行并返回结果
    result = await agent.run()
    return result, agent.tool_usage_stats

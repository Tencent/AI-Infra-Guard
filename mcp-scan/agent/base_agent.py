# Copyright (c) 2024-2026 Tencent Zhuque Lab. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Requirement: Any integration or derivative work must explicitly attribute
# Tencent Zhuque Lab (https://github.com/Tencent/AI-Infra-Guard) in its
# documentation or user interface, as detailed in the NOTICE file.

import json
import uuid

from tools.dispatcher import ToolDispatcher
from utils.aig_logger import mcpLogger
from utils.llm import LLM
from utils.loging import logger
from utils.parse import clean_content, parse_tool_invocations
from utils.prompt_manager import prompt_manager
from utils.tool_context import ToolContext


class BaseAgent:
    def __init__(
        self,
        name: str,
        instruction: str,
        llm: LLM,
        dispatcher: ToolDispatcher,
        specialized_llms: dict = None,
        log_step_id: str = None,
        debug: bool = False,
        capabilities: list[str] = None,
        output_format: str | None = None,
        output_check_fn: callable = None,
        language: str = "zh",
    ):
        self.llm = llm
        self.name = name
        self.dispatcher = dispatcher
        self.specialized_llms = specialized_llms or {}
        self.instruction = instruction
        self.capabilities = capabilities or ["standard"]
        self.output_format = output_format
        self.step_id = log_step_id
        self.debug = debug
        self.repo_dir = ""
        self.output_check_fn = output_check_fn
        self.language = language
        # loop control
        self.iter = 0
        self.max_iter = 80
        self.is_finished = False
        # context
        self.history = []
        self.original_task = ""
        self.summary_memory = ""
        # 在模型上下文窗口达到 60% 左右时开始压缩，给后续输出和工具结果留余量。
        self.max_history_tokens = max(int(self.llm.context_window * 0.6), 1)
        # 压缩时保留最近若干条对话，避免丢失当前执行轨迹。
        self.keep_recent_msgs = 8

    async def initialize(self):
        """异步初始化系统提示词"""
        if not self.history:
            system_prompt = await self.generate_system_prompt()
            self.history.append({"role": "system", "content": system_prompt})

    def add_user_message(self, message: str):
        self.history.append({"role": "user", "content": message})

    def set_repo_dir(self, repo_dir: str):
        self.repo_dir = repo_dir

    def should_compact_history(self, usage: dict | None = None) -> bool:
        # 没有可压缩的旧消息时，不触发压缩。
        if len(self.history) - 2 <= self.keep_recent_msgs:
            return False

        prompt_tokens = None
        if usage:
            prompt_tokens = usage.get("prompt_tokens")
        if isinstance(prompt_tokens, int):
            return prompt_tokens >= self.max_history_tokens

        # 某些兼容接口没有 usage，退回到消息条数做保守判定。
        return len(self.history) > 24

    def compact_history(self):
        recent_start = max(2, len(self.history) - self.keep_recent_msgs)

        msgs_to_compact = []
        if self.summary_memory:
            msgs_to_compact.append(
                {"role": "user", "content": self._build_summary_memory_message()}
            )
        msgs_to_compact.extend(self.history[2:recent_start])
        if not msgs_to_compact:
            return

        compact_prompt = prompt_manager.load_template("compact")
        msgs_to_compact.append({"role": "user", "content": compact_prompt})
        compacted_msgs = self.llm.chat(msgs_to_compact)
        self.summary_memory = compacted_msgs

        if not self.original_task:
            self.original_task = self.history[1]["content"]

        system_prompt = self.history[0]
        recent_msgs = self.history[-self.keep_recent_msgs :]
        self.history = [
            system_prompt,
            {
                "role": "user",
                "content": self._build_task_message(),
            },
            *recent_msgs,
        ]

    async def generate_system_prompt(self):
        tools_prompt = await self.dispatcher.get_all_tools_prompt()

        template_name = "system_prompt"
        format_kwargs = {
            "generate_tools": tools_prompt,
            "name": self.name,
            "instruction": self.instruction,
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
            response, usage = self.llm.chat(self.history, self.debug, ret_usage=True)
            logger.debug(f"LLM Response: {response}")

            self.history.append({"role": "assistant", "content": response})
            res = await self.handle_response(response)
            if res is not None:
                result = res

            self.iter += 1
            if self.should_compact_history(usage) and not self.is_finished:
                logger.info(
                    "Prompt tokens %s exceeded limit %s, compacting context",
                    usage.get("prompt_tokens") if usage else None,
                    self.max_history_tokens,
                )
                self.compact_history()

        if not self.is_finished:
            logger.warning(f"Max iterations ({self.max_iter}) reached")
            mcpLogger.status_update(
                self.step_id,
                "达到最大迭代次数，返回当前结果"
                if self.language != "en"
                else "Max iterations reached, returning current result",
                "",
                "completed",
            )
            if not result:
                result = await self._format_final_output()
        return result

    async def handle_response(self, response: str):
        tool_invocations = parse_tool_invocations(response)
        description = clean_content(response)
        if tool_invocations and tool_invocations["toolName"] == "finish" and description == "":
            description = "报告完成。"
            if self.language == "en":
                description = "Report completed."
        if description == "":
            description = "我将继续执行"
            if self.language == "en":
                description = "I will continue to execute"

        if tool_invocations:
            if tool_invocations["toolName"] != "finish":
                mcpLogger.status_update(self.step_id, description, "", "running")
            return await self.process_tool_call(tool_invocations, description)
        else:
            mcpLogger.status_update(self.step_id, description, "", "running")
            return await self.handle_no_tool(description)

    async def process_tool_call(self, tool_call: dict, description: str):
        tool_name = tool_call["toolName"]
        tool_args = tool_call["args"]
        tool_id = uuid.uuid4().__str__()

        params = json.dumps(tool_args, ensure_ascii=False) if tool_args else ""
        if isinstance(params, str):
            params = params.replace(self.repo_dir, "")

        mcpLogger.tool_used(self.step_id, tool_id, tool_name, "done", tool_name, f"{params}")

        if tool_name == "finish":
            self.is_finished = True
            logger.info("Finish tool called, final result formatted.")

            mcpLogger.status_update(self.step_id, description, "", "completed")
            result = await self._format_final_output()
            mcpLogger.action_log(tool_id, tool_name, self.step_id, result)
            return result

        # 构造上下文
        context = ToolContext(
            llm=self.llm,
            history=self.history,
            agent_name=self.name,
            iteration=self.iter,
            specialized_llms=self.specialized_llms,
            folder=self.repo_dir,
            tool_dispatcher=self.dispatcher,
        )

        # 通过 Dispatcher 调用工具
        tool_result = await self.dispatcher.call_tool(tool_name, tool_args, context)

        # 格式化工具结果并添加到历史
        result_message = f"{tool_result}"

        # 添加下一轮提示
        next_p = self.next_prompt()
        full_message = f"{next_p}\n\n{result_message}"

        self.history.append({"role": "user", "content": full_message})
        mcpLogger.status_update(self.step_id, description, "", "completed")

        if tool_name != "read_file":
            mcpLogger.action_log(tool_id, tool_name, self.step_id, f"```\n{result_message}\n```")

        return None

    async def handle_no_tool(self, description: str):
        next_p = self.next_prompt()
        if self.language == "en":
            reminder = (
                f"{next_p}\n\n"
                "No tool call was detected. You must call exactly one tool in your next response. "
                "If the task is complete, call finish."
            )
        else:
            reminder = (
                f"{next_p}\n\n"
                "未检测到工具调用。你下一次回复必须严格调用一个工具。"
                "如果任务已完成，请调用 finish。"
            )

        self.history.append({"role": "user", "content": reminder})
        return None

    async def _format_final_output(self) -> str:
        """使用 LLM 根据历史记录和预设格式生成最终输出"""
        # 取最近的对话历史作为参考
        recent_history = self.history[1:]
        formatting_prompt = prompt_manager.format_prompt(
            "format_report", output_format=self.output_format
        )
        recent_history.append({"role": "user", "content": formatting_prompt})
        final_output = ""
        for _ in range(3):
            final_output = self.llm.chat(recent_history)
            logger.info(f"Final Output: {final_output}")
            if self.output_check_fn:
                ret = self.output_check_fn(final_output)
                if isinstance(ret, bool) and ret:
                    break
            else:
                break
        return final_output

    def _build_task_message(self) -> str:
        if not self.summary_memory:
            return self.original_task

        if self.language == "en":
            return (
                f"I want you to complete: {self.original_task}\n\n"
                f"The following context is provided for your reference:\n{self.summary_memory}"
            )
        return (
            f"我希望你完成: {self.original_task}\n\n有以下上下文提供你参考:\n{self.summary_memory}"
        )

    def _build_summary_memory_message(self) -> str:
        if self.language == "en":
            return f"Summary of previous context:\n{self.summary_memory}"
        return f"此前上下文摘要：\n{self.summary_memory}"

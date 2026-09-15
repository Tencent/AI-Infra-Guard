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

from __future__ import annotations

import json
import re
import uuid

from skill_scan.tools.dispatcher import ToolDispatcher
from skill_scan.utils.aig_logger import mcpLogger
from skill_scan.utils.llm import LLM
from skill_scan.utils.loging import logger
from skill_scan.utils.parse import clean_content, parse_tool_invocations_all
from skill_scan.utils.prompt_manager import prompt_manager
from skill_scan.utils.tool_context import ToolContext

_MAX_HISTORY_TOOL_RESULT_CHARS = 40000
_TOOL_RESULT_PREVIEW_CHARS = 20000


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
        self.tool_cache: dict[str, str] = {}
        # Context compaction threshold
        self.max_history_tokens = max(int((llm.context_window or 128000) * 0.6), 1)
        self.keep_recent_msgs = 8

    async def initialize(self):
        """Asynchronously initialize the system prompt"""
        if not self.history:
            system_prompt = await self.generate_system_prompt()
            self.history.append({"role": "system", "content": system_prompt})

    def add_user_message(self, message: str):
        self.history.append({"role": "user", "content": message})

    def set_repo_dir(self, repo_dir: str):
        self.repo_dir = repo_dir

    def should_compact_history(self, usage: dict | None = None) -> bool:
        if len(self.history) - 2 <= self.keep_recent_msgs:
            return False
        prompt_tokens = None
        if usage:
            prompt_tokens = usage.get("prompt_tokens")
        if isinstance(prompt_tokens, int):
            return prompt_tokens >= self.max_history_tokens
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
        recent_msgs = self.history[-self.keep_recent_msgs:]
        self.history = [
            system_prompt,
            {"role": "user", "content": self._build_task_message()},
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
        tool_invocations = parse_tool_invocations_all(response)
        description = clean_content(response)
        if (
            len(tool_invocations) == 1
            and tool_invocations[0]["toolName"] == "finish"
            and description == ""
        ):
            description = "报告完成。"
            if self.language == "en":
                description = "Report completed."
        if description == "":
            description = "我将继续执行"
            if self.language == "en":
                description = "I will continue to execute"

        if tool_invocations:
            if not (len(tool_invocations) == 1 and tool_invocations[0]["toolName"] == "finish"):
                mcpLogger.status_update(self.step_id, description, "", "running")
            if len(tool_invocations) == 1:
                return await self.process_tool_call(tool_invocations[0], description)
            return await self.process_tool_calls(tool_invocations, description)
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

            # If the last assistant response already passes the output check,
            # return its cleaned content directly — skip the redundant
            # _format_final_output() LLM round-trip(s).
            last_msg = self.history[-1]["content"] if self.history else ""
            if last_msg and self.output_check_fn and self.output_check_fn(clean_content(last_msg)):
                result = clean_content(last_msg)
            else:
                result = await self._format_final_output()

            mcpLogger.action_log(tool_id, tool_name, self.step_id, result)
            return result

        # Construct the context
        context = ToolContext(
            llm=self.llm,
            history=self.history,
            agent_name=self.name,
            iteration=self.iter,
            specialized_llms=self.specialized_llms,
            folder=self.repo_dir,
            tool_dispatcher=self.dispatcher,
        )

        # Invoke the tool via the Dispatcher
        tool_result = await self.dispatcher.call_tool(tool_name, tool_args, context)

        # Format the tool result and append it to history (preserves aig-skill-scan's truncation logic)
        result_message = self._build_history_tool_result(
            tool_name,
            tool_args,
            str(tool_result),
        )

        # Append the next-round prompt
        next_p = self.next_prompt()
        # Forced follow-up: append an audit challenge when the tool result hits a sensitive pattern
        challenge = self._generate_challenge(result_message)
        if challenge:
            full_message = f"{next_p}\n\n{result_message}\n\n{challenge}"
        else:
            full_message = f"{next_p}\n\n{result_message}"

        self.history.append({"role": "user", "content": full_message})
        mcpLogger.status_update(self.step_id, description, "", "completed")

        if tool_name != "read_file":
            mcpLogger.action_log(tool_id, tool_name, self.step_id, f"```\n{result_message}\n```")

        return None

    async def process_tool_calls(self, tool_calls: list[dict], description: str):
        """Execute multiple model-emitted exploration calls in one agent round.

        Skill-scan tools are read-only exploration helpers. Calls are kept in
        model order and their results are returned together. If a model mixes
        ``finish`` with exploration calls, finish is deferred until the model
        has seen those results.
        """
        exploration_calls = [call for call in tool_calls if call["toolName"] != "finish"]
        if not exploration_calls:
            return await self.process_tool_call(tool_calls[0], description)

        context = ToolContext(
            llm=self.llm,
            history=self.history,
            agent_name=self.name,
            iteration=self.iter,
            specialized_llms=self.specialized_llms,
            folder=self.repo_dir,
            tool_dispatcher=self.dispatcher,
        )
        result_messages = []
        for tool_call in exploration_calls:
            tool_name = tool_call["toolName"]
            tool_args = tool_call["args"]
            tool_id = str(uuid.uuid4())
            params = json.dumps(tool_args, ensure_ascii=False) if tool_args else ""
            params = params.replace(self.repo_dir, "") if isinstance(params, str) else params
            mcpLogger.tool_used(self.step_id, tool_id, tool_name, "done", tool_name, f"{params}")
            tool_result = await self.dispatcher.call_tool(tool_name, tool_args, context)
            result_message = self._build_history_tool_result(
                tool_name, tool_args, str(tool_result)
            )
            result_messages.append(f"<tool_result name=\"{tool_name}\">\n{result_message}\n</tool_result>")
            if tool_name != "read_file":
                mcpLogger.action_log(
                    tool_id, tool_name, self.step_id, f"```\n{result_message}\n```"
                )

        combined_results = "\n\n".join(result_messages)
        challenge = self._generate_challenge(combined_results)
        follow_up = f"{self.next_prompt()}\n\n{combined_results}"
        if challenge:
            follow_up += f"\n\n{challenge}"
        if len(exploration_calls) != len(tool_calls):
            follow_up += (
                "\n\nThe finish call was deferred because it was mixed with exploration calls. "
                "Review these results before finishing."
            )
        self.history.append({"role": "user", "content": follow_up})
        mcpLogger.status_update(self.step_id, description, "", "completed")
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

    # Sensitive pattern -> challenge mapping (aig-skill-scan specific)
    _CHALLENGE_PATTERNS_ZH = [
        (
            r"curl\s+[^|]*\|\s*(ba)?sh|wget\s+[^|]*\|\s*(ba)?sh",
            "审计线索（非结论）：发现 curl|bash 形式；核对来源、参数和用途，不能仅凭安装方式判为恶意。",
        ),
        (
            r"169\.254\.169\.254|metadata\.google\.internal|/computeMetadata/",
            "⚠️ 注意：上述代码访问了云实例元数据端点。请思考：这种能力是否超出了声明功能的最小权限？",
        ),
        (
            r"gethostname\(\)|getfqdn\(\)|getsockname\(\)",
            "⚠️ 注意：上述代码收集了本地主机信息。请评估这是否属于环境侦察。",
        ),
        (
            r"(base64\.(b64)?encode|btoa).*?(key|secret|token|password|credential|private|id_rsa)",
            "审计线索（非结论）：编码与凭据词共现不证明数据流。核查实际内容、接收方和授权；正常认证或本地 stdout 不等同外传。",
        ),
        (
            r"(base64\.b64decode|atob).*?(exec|eval|system)",
            "审计线索（非结论）：解码与执行词共现，需追踪解码内容是否实际流入执行点及其行为。",
        ),
        (
            r"(ignore\s+(previous|above|all)\s+instructions?|you\s+are\s+now|SYSTEM\s*OVERRIDE)",
            "审计线索（非结论）：存在指令式措辞。区分任务角色、引用样例与真正覆盖用户/系统安全约束的指令，不能仅凭措辞判为恶意。",
        ),
        (
            r"authorized_keys|id_rsa|\.ssh/",
            "⚠️ 注意：上述代码涉及 SSH 密钥操作，请评估这是否超出了 Skill 声明功能。",
        ),
        (
            r"crontab|systemctl\s+enable|launchctl",
            "⚠️ 注意：上述代码涉及持久化机制（定时任务/服务），请评估合理性。",
        ),
    ]

    _CHALLENGE_PATTERNS_EN = [
        (
            r"curl\s+[^|]*\|\s*(ba)?sh|wget\s+[^|]*\|\s*(ba)?sh",
            "Audit hint (not a verdict): curl|bash syntax appears. Verify source, arguments and purpose; an installation pattern alone does not establish malice.",
        ),
        (
            r"169\.254\.169\.254|metadata\.google\.internal|/computeMetadata/",
            "⚠️ Note: The above code accesses the cloud instance metadata endpoint. Consider: does this capability exceed the minimum privileges required by the declared functionality?",
        ),
        (
            r"gethostname\(\)|getfqdn\(\)|getsockname\(\)",
            "⚠️ Note: The above code collects local host information. Evaluate whether this constitutes environment reconnaissance.",
        ),
        (
            r"(base64\.(b64)?encode|btoa).*?(key|secret|token|password|credential|private|id_rsa)",
            "Audit hint (not a verdict): encoding and credential terms co-occur, which does not prove data flow. Verify content, recipient and authorization; normal authentication or local stdout is not automatically exfiltration.",
        ),
        (
            r"(base64\.b64decode|atob).*?(exec|eval|system)",
            "Audit hint (not a verdict): decoding and execution terms co-occur. Trace whether decoded content actually reaches execution and inspect its behavior.",
        ),
        (
            r"(ignore\s+(previous|above|all)\s+instructions?|you\s+are\s+now|SYSTEM\s*OVERRIDE)",
            "Audit hint (not a verdict): instruction-like text appears. Distinguish task roles and quoted examples from active user/system constraint overrides; wording alone does not establish malice.",
        ),
        (
            r"authorized_keys|id_rsa|\.ssh/",
            "⚠️ Note: The above code involves SSH key operations. Evaluate whether this exceeds the Skill's declared functionality.",
        ),
        (
            r"crontab|systemctl\s+enable|launchctl",
            "⚠️ Note: The above code involves persistence mechanisms (scheduled tasks/services). Evaluate whether this is reasonable.",
        ),
    ]

    def _generate_challenge(self, tool_result: str) -> str:
        """Detect sensitive patterns in the tool result and generate a challenge/follow-up text."""
        patterns = self._CHALLENGE_PATTERNS_EN if self.language == "en" else self._CHALLENGE_PATTERNS_ZH
        challenges = []
        for pattern, question in patterns:
            if re.search(pattern, tool_result, re.IGNORECASE):
                challenges.append(question)
        if not challenges:
            return ""
        return "\n".join(challenges)

    def _build_history_tool_result(
        self,
        tool_name: str,
        tool_args: dict,
        tool_result: str,
    ) -> str:
        """Truncate an overly long tool result, keeping a preview + cache_id."""
        if len(tool_result) <= _MAX_HISTORY_TOOL_RESULT_CHARS:
            return tool_result
        cache_id = str(uuid.uuid4())[:8]
        self.tool_cache[cache_id] = tool_result
        args_text = json.dumps(tool_args, ensure_ascii=False, default=str)
        if len(args_text) > 1000:
            args_text = f"{args_text[:1000]}..."
        preview = tool_result[:_TOOL_RESULT_PREVIEW_CHARS]
        omitted_chars = len(tool_result) - len(preview)
        logger.info(
            f"Tool result truncated in history: tool={tool_name}, "
            f"original_chars={len(tool_result)}, cache_id={cache_id}"
        )
        return (
            "[tool_result_summary]\n"
            f"tool={tool_name}\n"
            f"args={args_text}\n"
            f"original_chars={len(tool_result)}\n"
            f"truncated_in_history=true\n"
            f"cache_id={cache_id}\n"
            "preview=\n"
            f"{preview}\n"
            f"... (history truncated, omitted_chars={omitted_chars})"
        )

    async def _format_final_output(self) -> str:
        """Use the LLM to generate the final output based on history and the preset format"""
        # Preserve the stage's audit policy, without the tool-calling protocol
        # used during exploration: formatting returns XML directly.
        recent_history = [{"role": "system", "content": self.instruction}, *self.history[1:]]
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

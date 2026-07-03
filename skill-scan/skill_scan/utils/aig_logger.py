from __future__ import annotations

import json
import time
from typing import Literal
import logging
from pydantic import BaseModel


class contentSchema(BaseModel):
    timestamp: str = str(time.time())


# Top-level plan step
class newPlanStep(contentSchema):
    stepId: str
    title: str


# Step status update
class statusUpdate(contentSchema):
    stepId: str
    brief: str
    description: str
    status: Literal["running", "completed", "failed"]


# Tool usage
class toolUsed(contentSchema):
    stepId: str
    tool_id: str
    tool_name: str | None = None
    brief: str
    status: Literal["todo", "doing", "done"]
    params: str


# Tool log
class actionLog(contentSchema):
    tool_id: str
    tool_name: str
    stepId: str
    log: str


# Error log
class errorLog(contentSchema):
    msg: str


class AgentMsg(BaseModel):
    type: str
    content: dict


class McpLogger:

    def __init__(self):
        # AIG integration mode switch: disabled by default.
        # When disabled, every _log call becomes a no-op and no structured
        # JSON is written to stdout. It is only emitted when the Go backend
        # enables it via `--aig-mode`, so that standalone pip install use
        # does not pollute the user's terminal.
        self.enabled = False
        logger = logging.getLogger("mcpLogger")
        logger.setLevel(logging.INFO)
        # Create the console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        # Set the log format
        formatter = logging.Formatter("%(message)s")
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        self.logger = logger

    def enable(self):
        """Enable AIG integration mode and start emitting structured JSON logs to stdout."""
        self.enabled = True

    def disable(self):
        """Disable AIG integration mode."""
        self.enabled = False

    def _log(self, type: str, content: BaseModel | dict):
        if not self.enabled:
            return
        if isinstance(content, BaseModel):
            content.timestamp = str(time.time())
            content = content.model_dump()
        self.logger.info(AgentMsg(type=type, content=content).model_dump_json())

    def new_plan_step(self, stepId: str, stepName: str):
        self._log("newPlanStep", newPlanStep(stepId=stepId, title=stepName))

    def status_update(self, stepId: str, brief: str, description: str,
                      status: Literal["running", "completed", "failed"]):
        self._log("statusUpdate", statusUpdate(stepId=stepId, brief=brief, description=description,
                                               status=status))

    def tool_used(self, stepId: str, tool_id: str, brief: str,
                  status: Literal["todo", "doing", "done"], tool_name: str = None, params: str = ""):
        self._log("toolUsed", toolUsed(stepId=stepId, tool_id=tool_id, tool_name=tool_name,
                                       brief=brief, status=status, params=params))

    def action_log(self, tool_id: str, tool_name: str, stepId: str, log: str):
        self._log("actionLog", actionLog(tool_id=tool_id, tool_name=tool_name,
                                         stepId=stepId, log=log))

    def result_update(self, content: dict):
        self._log("resultUpdate", content)

    def error_log(self, msg: str):
        self._log("error", errorLog(msg=msg))


mcpLogger = McpLogger()

if __name__ == '__main__':
    mcpLogger.new_plan_step(stepId="0", stepName="Step 1")
    mcpLogger.new_plan_step(stepId="1", stepName="Step 2")
    mcpLogger.new_plan_step(stepId="2", stepName="Step 3")
    # mcpLogger.status_update(stepId="step1", brief="Step 1", description="Step 1", status="running")
    # mcpLogger.tool_used(stepId="step1", tool_id="tool1", brief="Tool 1", status="todo")
    # mcpLogger.action_log(tool_id="tool1", tool_name="Tool 1", stepId="step1", log="Log 1")
    # mcpLogger.result_update(content={"a": "b"})

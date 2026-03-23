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

"""
Agent scan logger module.

Provides structured logging for the agent security scanning pipeline,
including step progress, tool usage, and result reporting.
"""

import json
import time
from typing import Literal
import logging
from pydantic import BaseModel


class ContentSchema(BaseModel):
    """Base schema for log content with timestamp."""
    timestamp: str = str(time.time())


class NewPlanStep(ContentSchema):
    """Log entry for a new pipeline step."""
    stepId: str
    title: str


class StatusUpdate(ContentSchema):
    """Log entry for step status update."""
    stepId: str
    brief: str
    description: str
    status: Literal["running", "completed", "failed"]


class ToolUsed(ContentSchema):
    """Log entry for tool usage."""
    stepId: str
    tool_id: str
    tool_name: str | None = None
    brief: str
    status: Literal["todo", "doing", "done"]
    params: str


class ActionLog(ContentSchema):
    """Log entry for tool action."""
    tool_id: str
    tool_name: str
    stepId: str
    log: str


class ErrorLog(ContentSchema):
    """Log entry for errors."""
    msg: str


class AgentMsg(BaseModel):
    """Structured agent message for logging."""
    type: str
    content: dict


class ScanLogger:
    """
    Logger for agent security scanning pipeline.
    
    Provides structured JSON logging for:
    - Pipeline step progress
    - Tool usage tracking
    - Action logs
    - Result reporting
    - Error logging
    """

    def __init__(self):
        logger = logging.getLogger("scanLogger")
        logger.setLevel(logging.INFO)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Set log format
        formatter = logging.Formatter("%(message)s")
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        self.logger = logger

    def _log(self, type: str, content: BaseModel | dict):
        """Internal logging method."""
        if isinstance(content, BaseModel):
            content.timestamp = str(time.time())
            content = content.model_dump()
        self.logger.info(AgentMsg(type=type, content=content).model_dump_json())

    def new_plan_step(self, stepId: str, stepName: str):
        """Log a new pipeline step."""
        self._log("newPlanStep", NewPlanStep(stepId=stepId, title=stepName))

    def status_update(
        self,
        stepId: str,
        brief: str,
        description: str,
        status: Literal["running", "completed", "failed"]
    ):
        """Log a step status update."""
        self._log("statusUpdate", StatusUpdate(
            stepId=stepId, brief=brief, description=description, status=status
        ))

    def tool_used(
        self,
        stepId: str,
        tool_id: str,
        brief: str,
        status: Literal["todo", "doing", "done"],
        tool_name: str = None,
        params: str = ""
    ):
        """Log tool usage."""
        self._log("toolUsed", ToolUsed(
            stepId=stepId, tool_id=tool_id, tool_name=tool_name,
            brief=brief, status=status, params=params
        ))

    def action_log(self, tool_id: str, tool_name: str, stepId: str, log: str):
        """Log a tool action."""
        self._log("actionLog", ActionLog(
            tool_id=tool_id, tool_name=tool_name, stepId=stepId, log=log
        ))

    def result_update(self, content: dict):
        """Log scan result."""
        self._log("resultUpdate", content)

    def error_log(self, msg: str):
        """Log an error."""
        self._log("error", ErrorLog(msg=msg))


# Global logger instance
scanLogger = ScanLogger()



if __name__ == '__main__':
    scanLogger.new_plan_step(stepId="0", stepName="Step 1")
    scanLogger.new_plan_step(stepId="1", stepName="Step 2")
    scanLogger.new_plan_step(stepId="2", stepName="Step 3")

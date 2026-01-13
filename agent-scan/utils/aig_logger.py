import json
import time
from typing import Literal
import logging
from pydantic import BaseModel


class contentSchema(BaseModel):
    timestamp: str = str(time.time())


# 大标题
class newPlanStep(contentSchema):
    stepId: str
    title: str


# 步骤状态更新
class statusUpdate(contentSchema):
    stepId: str
    brief: str
    description: str
    status: Literal["running", "completed", "failed"]


# 工具使用
class toolUsed(contentSchema):
    stepId: str
    tool_id: str
    tool_name: str | None = None
    brief: str
    status: Literal["todo", "doing", "done"]
    params: str


# 工具日志
class actionLog(contentSchema):
    tool_id: str
    tool_name: str
    stepId: str
    log: str


# 错误日志
class errorLog(contentSchema):
    msg: str


class AgentMsg(BaseModel):
    type: str
    content: dict


class McpLogger:

    def __init__(self):
        logger = logging.getLogger("mcpLogger")
        logger.setLevel(logging.INFO)
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        # 设置日志格式
        formatter = logging.Formatter("%(message)s")
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        self.logger = logger

    def _log(self, type: str, content: BaseModel | dict):
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

import sys
import gettext
import os
from typing import Literal, Union
from datetime import datetime
from pydantic import BaseModel
from loguru import logger as base_logger

class contentSchema(BaseModel):
    timestamp: str | None = None

class newPlanStep(contentSchema):
    stepId: str
    title: str

class statusUpdate(contentSchema):
    stepId: str
    brief: str
    description: str
    status: Literal["running", "completed", "failed"]

class toolUsed(contentSchema):
    stepId: str
    tool_id: str
    tool_name: str | None = None
    brief: str
    status: Literal["todo", "doing", "done"]

class actionLog(contentSchema):
    tool_id: str
    tool_name: str
    stepId: str
    log: str

class resultUpdate(contentSchema):
    msgType: Literal["text", "markdown", "file", "json"]
    content: str | dict | list
    status: bool | None = None

class PromptSecurityLog(BaseModel):
    type: Literal["error", "newPlanStep", "statusUpdate", "toolUsed", "actionLog", "resultUpdate"]
    content: Union[str, newPlanStep, statusUpdate, toolUsed, actionLog, resultUpdate]

class PromptSecurityLogger:
    def __init__(self, base_logger, lang='en_US'):
        self._base_logger = base_logger
        self._base_logger.remove()
        self._base_logger.add(sys.stdout, filter=lambda record: not record["extra"].get("aig_log", False), level="DEBUG")
        self._base_logger.add(sys.stdout, filter=lambda record: record["extra"].get("aig_log", False), format="{message}")
        self.lang = lang
        self._setup_i18n()
    
    def add(self, *args, **kwargs):
        self._base_logger.add(*args, **kwargs)

    def info(self, *args, **kwargs):
        self._base_logger.opt(depth=1).info(*args, **kwargs)

    def debug(self, *args, **kwargs):
        self._base_logger.opt(depth=1).debug(*args, **kwargs)

    def warning(self, *args, **kwargs):
        self._base_logger.opt(depth=1).warning(*args, **kwargs)

    def error(self, *args, **kwargs):
        self._base_logger.opt(depth=1).error(*args, **kwargs)
    
    def exception(self, *args, **kwargs):
        self._base_logger.opt(depth=1).exception(*args, **kwargs)

    def disable(self):
        self._base_logger.disable("")
    
    def enable(self):
        self._base_logger.enable("")

    def _setup_i18n(self):
        localedir = os.path.join(os.path.dirname(__file__), 'locales')
        try:
            self.trans = gettext.translation('messages', localedir=localedir, languages=[self.lang])
            self.lang = self.trans.info().get("language", self.lang)
            self.trans.install()
            self._ = self.trans.gettext
        except FileNotFoundError:
            gettext.install('messages')
            self._ = gettext.gettext
    
    def set_language(self, lang):
        """动态切换语言"""
        self.lang = lang
        self._setup_i18n()

    def translated_msg(self, msg, *args, **kwargs):
        translated_msg = self._(msg)
        if args or kwargs:
            translated_msg = translated_msg.format(*args, **kwargs)
        return translated_msg

    def _create_log(self, log_type: str, content: Union[str, contentSchema]) -> str:
        """创建符合PromptSecurityLog格式的日志"""
        if isinstance(content, contentSchema) and "timestamp" not in content:
            content.timestamp = datetime.now().isoformat()
        
        log_entry = PromptSecurityLog(
            type=log_type,
            content=content
        )
        return log_entry.model_dump_json(exclude_none=True)
    
    def log(self, log_type: str, content: Union[str, contentSchema]):
        """记录日志"""
        log_message = self._create_log(log_type, content)
        self._base_logger.bind(aig_log=True).opt(depth=2).log("INFO", "\n" + log_message)
    
    # 为每种日志类型创建便捷方法
    def critical_issue(self, content: str):
        self.log("error", content)
        
    def new_plan_step(self, content: newPlanStep):
        self.log("newPlanStep", content)
    
    def status_update(self, content: statusUpdate):
        self.log("statusUpdate", content)
    
    def tool_used(self, content: toolUsed):
        self.log("toolUsed", content)
    
    def action_log(self, content: actionLog):
        self.log("actionLog", content)
    
    def result_update(self, content: resultUpdate):
        self.log("resultUpdate", content)

logger = PromptSecurityLogger(base_logger)

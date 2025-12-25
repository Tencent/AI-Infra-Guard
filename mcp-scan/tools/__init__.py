# 自动导入所有工具模块，触发 @register_tool 装饰器的执行
from tools.thinking import thinking_actions
from tools.finish import finish_actions
from tools.file import read_file
from tools.execute import execute_actions
from tools.mcp_tool import mcp_tool

__all__ = ['thinking_actions', 'finish_actions', 'read_file', 'execute_actions', 'mcp_tool']

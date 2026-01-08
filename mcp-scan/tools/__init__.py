# 自动导入所有工具模块，触发 @register_tool 装饰器的执行

# 原有工具
from tools.thinking import thinking_actions
from tools.finish import finish_actions
from tools.file import read_file
from tools.execute import execute_actions
from tools.mcp_tool import mcp_tool

# 新增工具 - Shell / 文件类
from tools import bash
from tools import batch
from tools import edit
from tools import glob
from tools import grep
from tools import ls
from tools import read
from tools import write

# 新增工具 - 知识与协作类
from tools import skill
from tools import task
from tools import todo

__all__ = [
    # 原有工具
    'thinking_actions',
    'finish_actions',
    'read_file',
    'execute_actions',
    'mcp_tool',
    # 新增工具 - Shell / 文件类
    'bash',
    'batch',
    'edit',
    'glob',
    'grep',
    'ls',
    'read',
    'write',
    # 新增工具 - 知识与协作类
    'skill',
    'task',
    'todo',
]

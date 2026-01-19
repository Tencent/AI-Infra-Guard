# 自动导入所有工具模块，触发 @register_tool 装饰器的执行

# 原有工具
try:
    from tools.thinking import thinking_actions
except ImportError:
    pass

try:
    from tools.finish import finish_actions
except ImportError:
    pass

try:
    from tools.execute import execute_actions
except ImportError:
    pass

try:
    from tools.mcp_tool import mcp_tool
except ImportError:
    pass

# 新增工具 - Shell / 文件类
try:
    from tools import bash
except ImportError:
    pass

try:
    from tools import batch
except ImportError:
    pass

try:
    from tools import edit
except ImportError:
    pass

try:
    from tools import glob
except ImportError:
    pass

try:
    from tools import grep
except ImportError:
    pass

try:
    from tools import ls
except ImportError:
    pass

try:
    from tools.file import read, write
except ImportError:
    pass

# 新增工具 - 知识与协作类
try:
    from tools import skill
except ImportError:
    pass

try:
    from tools import task
except ImportError:
    pass

try:
    from tools import todo
except ImportError:
    pass

# Security scanning tools
try:
    from tools import scan
except ImportError:
    pass

# Agent adapter
try:
    from tools.agent_adapter import connectivity, dialogue
except ImportError:
    pass

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
    'connectivity',
    'dialogue',
    # Security scanning tools
    'scan',
]

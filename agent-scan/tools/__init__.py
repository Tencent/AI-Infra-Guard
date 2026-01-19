# 自动导入所有工具模块，触发 @register_tool 装饰器的执行

import importlib
from pathlib import Path

# 自动扫描并导入 tools 目录下所有工具包
_tools_dir = Path(__file__).parent
_exclude = {'__pycache__', 'logs'}  # 排除非工具目录

for item in _tools_dir.iterdir():
    if item.is_dir() and item.name not in _exclude and (item / '__init__.py').exists():
        try:
            importlib.import_module(f'tools.{item.name}')
        except ImportError:
            pass
# 基于 XML schema 文件自动发现并加载工具模块
# 规则：{xxx}_schema.xml 对应 {xxx}.py

import importlib
from pathlib import Path

_tools_dir = Path(__file__).parent
_exclude = {'__pycache__', 'logs'}

for subdir in _tools_dir.iterdir():
    if not subdir.is_dir() or subdir.name in _exclude:
        continue
    
    # 查找所有 *_schema.xml 文件
    for xml_file in subdir.glob('*_schema.xml'):
        # 从 xxx_schema.xml 提取 xxx
        module_name = xml_file.stem.removesuffix('_schema')
        py_file = subdir / f'{module_name}.py'
        
        if py_file.exists():
            try:
                importlib.import_module(f'tools.{subdir.name}.{module_name}')
            except ImportError:
                pass

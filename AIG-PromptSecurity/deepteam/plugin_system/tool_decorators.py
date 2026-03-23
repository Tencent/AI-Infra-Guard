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
工具参数装饰器模块
用于为工具类添加参数说明，支持扫描器自动提取参数信息
"""

def tool_parameters(**param_descriptions):
    """
    装饰器：为工具类添加参数说明
    
    Args:
        **param_descriptions: 参数名 -> 参数描述的映射
        
    Example:
        @tool_parameters(
            role="要扮演的角色名称，如：doctor, teacher, hacker",
            context="角色背景上下文，可选，默认为空",
            temperature="生成文本的随机性，0-1之间，默认0.7"
        )
        class RoleplayAttack(BaseAttack):
            def __init__(self, role: str, context: str = "", temperature: float = 0.7):
                pass
    """
    def decorator(cls):
        cls._parameter_descriptions = param_descriptions
        return cls
    return decorator 
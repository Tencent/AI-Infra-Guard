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
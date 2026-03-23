"""
Batch 工具 - 批量执行多个工具调用
校验不超过 10 个子调用，禁止嵌套批处理/finish
"""
import asyncio
from typing import Any, List, Dict, Optional
from tools.registry import register_tool, get_tool_by_name, needs_context
from utils.logging import logger
from utils.tool_context import ToolContext
import inspect


# 禁止在 batch 中调用的工具
DISALLOWED_TOOLS = {'batch', 'finish'}
MAX_BATCH_SIZE = 10


@register_tool
async def batch(
    tool_calls: List[Dict[str, Any]],
    context: ToolContext = None
) -> dict[str, Any]:
    """
    批量执行多个工具调用
    
    Args:
        tool_calls: 工具调用列表，每个元素包含 tool 和 parameters
        context: 工具上下文
        
    Returns:
        包含执行结果的字典
    """
    if not tool_calls:
        return {
            "success": False,
            "error": "No tool calls provided. Provide at least one tool call."
        }
    
    if not isinstance(tool_calls, list):
        return {
            "success": False,
            "error": "tool_calls must be an array of tool call objects"
        }
    
    # 限制调用数量
    if len(tool_calls) > MAX_BATCH_SIZE:
        logger.warning(f"Batch size {len(tool_calls)} exceeds limit {MAX_BATCH_SIZE}, truncating")
    
    calls_to_execute = tool_calls[:MAX_BATCH_SIZE]
    discarded_calls = tool_calls[MAX_BATCH_SIZE:]
    
    results = []
    
    async def execute_single_call(call: Dict[str, Any], index: int) -> Dict[str, Any]:
        """执行单个工具调用"""
        tool_name = call.get('tool', '')
        parameters = call.get('parameters', {})
        
        # 检查是否为禁止的工具
        if tool_name in DISALLOWED_TOOLS:
            return {
                "index": index,
                "tool": tool_name,
                "success": False,
                "error": f"Tool '{tool_name}' is not allowed in batch. Disallowed tools: {', '.join(DISALLOWED_TOOLS)}"
            }
        
        # 获取工具函数
        tool_func = get_tool_by_name(tool_name)
        if not tool_func:
            return {
                "index": index,
                "tool": tool_name,
                "success": False,
                "error": f"Tool '{tool_name}' not found in registry"
            }
        
        try:
            # 注入 context 如果需要
            if needs_context(tool_name) and context:
                parameters = {**parameters, 'context': context}
            
            # 执行工具
            result = tool_func(**parameters)
            
            # 处理异步结果
            if inspect.isawaitable(result):
                result = await result
            
            # 格式化结果
            if isinstance(result, dict):
                return {
                    "index": index,
                    "tool": tool_name,
                    "success": result.get('success', True),
                    "result": result
                }
            else:
                return {
                    "index": index,
                    "tool": tool_name,
                    "success": True,
                    "result": str(result)
                }
                
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}' in batch: {e}")
            return {
                "index": index,
                "tool": tool_name,
                "success": False,
                "error": str(e)
            }
    
    # 串行执行所有调用（保持顺序和可预测性）
    for i, call in enumerate(calls_to_execute):
        result = await execute_single_call(call, i)
        results.append(result)
    
    # 添加被丢弃的调用结果
    for i, call in enumerate(discarded_calls):
        results.append({
            "index": MAX_BATCH_SIZE + i,
            "tool": call.get('tool', 'unknown'),
            "success": False,
            "error": f"Maximum of {MAX_BATCH_SIZE} tools allowed in batch"
        })
    
    # 统计结果
    successful = sum(1 for r in results if r.get('success', False))
    failed = len(results) - successful
    
    if failed > 0:
        output = f"Executed {successful}/{len(results)} tools successfully. {failed} failed."
    else:
        output = f"All {successful} tools executed successfully.\n\nKeep using the batch tool for optimal performance!"
    
    return {
        "success": failed == 0,
        "title": f"Batch execution ({successful}/{len(results)} successful)",
        "output": output,
        "metadata": {
            "total_calls": len(results),
            "successful": successful,
            "failed": failed,
            "tools": [call.get('tool', 'unknown') for call in tool_calls],
            "details": results
        }
    }


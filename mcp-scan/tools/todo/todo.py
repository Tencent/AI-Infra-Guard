"""
Todo 工具 - 提供 read/write 两种动作，借助 TodoManager 校验状态并读写 JSON 缓存
"""
import os
from typing import Any, Optional, List, Dict
from tools.registry import register_tool
from utils.loging import logger
from utils.tool_context import ToolContext
from utils.todo_manager import TodoManager, TodoItem, TodoStatus


def get_todo_manager(context: ToolContext) -> TodoManager:
    """获取 TodoManager 实例"""
    root = context.folder if context else os.getcwd()
    return TodoManager(root)


@register_tool
def todo_read(context: ToolContext = None) -> dict[str, Any]:
    """
    读取 Todo 列表
    
    Args:
        context: 工具上下文
        
    Returns:
        包含 Todo 列表的字典
    """
    try:
        manager = get_todo_manager(context)
        todos = manager.get_all()
        
        # 转换为字典列表
        todo_list = [todo.to_dict() for todo in todos]
        
        # 获取统计
        summary = manager.get_summary()
        
        # 格式化输出
        if not todo_list:
            output = "No todos found."
        else:
            output_lines = [f"Todos ({summary['total']} total, {summary['pending']} pending, {summary['in_progress']} in progress):", ""]
            
            for todo in todos:
                status_icon = {
                    TodoStatus.PENDING: "⬜",
                    TodoStatus.IN_PROGRESS: "🔄",
                    TodoStatus.COMPLETED: "✅",
                    TodoStatus.CANCELLED: "❌"
                }.get(todo.status, "⬜")
                
                output_lines.append(f"  {status_icon} [{todo.id}] {todo.content} ({todo.status.value})")
            
            output = '\n'.join(output_lines)
        
        return {
            "success": True,
            "title": f"{summary['pending']} pending todos",
            "output": output,
            "todos": todo_list,
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Error reading todos: {e}")
        return {
            "success": False,
            "error": f"Error reading todos: {str(e)}"
        }


@register_tool
def todo_write(
    todos: List[Dict[str, Any]],
    context: ToolContext = None
) -> dict[str, Any]:
    """
    更新 Todo 列表
    
    Args:
        todos: 新的 Todo 列表
        context: 工具上下文
        
    Returns:
        包含更新结果的字典
    """
    try:
        if not isinstance(todos, list):
            return {
                "success": False,
                "error": "todos must be an array of todo objects"
            }
        
        # 验证每个 todo 的结构
        for i, todo in enumerate(todos):
            if not isinstance(todo, dict):
                return {
                    "success": False,
                    "error": f"Todo at index {i} must be an object"
                }
            
            if 'id' not in todo:
                return {
                    "success": False,
                    "error": f"Todo at index {i} missing required field 'id'"
                }
            
            if 'content' not in todo:
                return {
                    "success": False,
                    "error": f"Todo at index {i} missing required field 'content'"
                }
            
            if 'status' not in todo:
                return {
                    "success": False,
                    "error": f"Todo at index {i} missing required field 'status'"
                }
            
            # 验证状态值
            status = todo['status']
            valid_statuses = [s.value for s in TodoStatus]
            if status not in valid_statuses:
                return {
                    "success": False,
                    "error": f"Todo at index {i} has invalid status '{status}'. Valid values: {', '.join(valid_statuses)}"
                }
        
        manager = get_todo_manager(context)
        updated_todos = manager.update_todos(todos)
        
        # 获取统计
        summary = manager.get_summary()
        
        # 格式化输出
        pending_count = summary['pending']
        in_progress_count = summary['in_progress']
        
        output = f"Updated {len(updated_todos)} todos. {pending_count} pending, {in_progress_count} in progress."
        
        logger.info(f"Updated todos: {len(updated_todos)} items")
        
        return {
            "success": True,
            "title": f"{pending_count} pending todos",
            "output": output,
            "todos": [t.to_dict() for t in updated_todos],
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Error writing todos: {e}")
        return {
            "success": False,
            "error": f"Error writing todos: {str(e)}"
        }


@register_tool
def todo_add(
    id: str,
    content: str,
    status: str = "pending",
    priority: int = 0,
    context: ToolContext = None
) -> dict[str, Any]:
    """
    添加单个 Todo
    
    Args:
        id: Todo ID
        content: Todo 内容
        status: 状态（pending, in_progress, completed, cancelled）
        priority: 优先级
        context: 工具上下文
        
    Returns:
        包含添加结果的字典
    """
    try:
        # 验证状态
        valid_statuses = [s.value for s in TodoStatus]
        if status not in valid_statuses:
            return {
                "success": False,
                "error": f"Invalid status '{status}'. Valid values: {', '.join(valid_statuses)}"
            }
        
        manager = get_todo_manager(context)
        
        # 检查 ID 是否已存在
        existing = manager.get_by_id(id)
        if existing:
            return {
                "success": False,
                "error": f"Todo with id '{id}' already exists"
            }
        
        todo = TodoItem(
            id=id,
            content=content,
            status=TodoStatus(status),
            priority=priority
        )
        
        manager.add(todo)
        
        logger.info(f"Added todo: {id}")
        
        return {
            "success": True,
            "title": f"Added: {content[:30]}...",
            "output": f"Todo '{id}' added successfully",
            "todo": todo.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Error adding todo: {e}")
        return {
            "success": False,
            "error": f"Error adding todo: {str(e)}"
        }


@register_tool
def todo_update(
    id: str,
    content: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[int] = None,
    context: ToolContext = None
) -> dict[str, Any]:
    """
    更新单个 Todo
    
    Args:
        id: Todo ID
        content: 新内容（可选）
        status: 新状态（可选）
        priority: 新优先级（可选）
        context: 工具上下文
        
    Returns:
        包含更新结果的字典
    """
    try:
        manager = get_todo_manager(context)
        
        # 检查 Todo 是否存在
        existing = manager.get_by_id(id)
        if not existing:
            return {
                "success": False,
                "error": f"Todo with id '{id}' not found"
            }
        
        # 构建更新
        updates = {}
        if content is not None:
            updates['content'] = content
        if status is not None:
            valid_statuses = [s.value for s in TodoStatus]
            if status not in valid_statuses:
                return {
                    "success": False,
                    "error": f"Invalid status '{status}'. Valid values: {', '.join(valid_statuses)}"
                }
            updates['status'] = status
        if priority is not None:
            updates['priority'] = priority
        
        if not updates:
            return {
                "success": False,
                "error": "No updates provided"
            }
        
        updated = manager.update(id, **updates)
        
        if not updated:
            return {
                "success": False,
                "error": f"Failed to update todo '{id}'"
            }
        
        logger.info(f"Updated todo: {id}")
        
        return {
            "success": True,
            "title": f"Updated: {id}",
            "output": f"Todo '{id}' updated successfully",
            "todo": updated.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Error updating todo: {e}")
        return {
            "success": False,
            "error": f"Error updating todo: {str(e)}"
        }


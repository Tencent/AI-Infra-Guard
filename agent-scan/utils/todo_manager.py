"""
Todo 管理模块 - 使用 <repo>/.mcp/todos.json 缓存 Agent Todo
支持加载、校验与持久化
"""
import os
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum


class TodoStatus(str, Enum):
    """Todo 状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class TodoItem:
    """Todo 条目"""
    id: str
    content: str
    status: TodoStatus
    priority: int = 0
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = {
            "id": self.id,
            "content": self.content,
            "status": self.status.value if isinstance(self.status, TodoStatus) else self.status,
            "priority": self.priority,
        }
        if self.metadata:
            data["metadata"] = self.metadata
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TodoItem":
        """从字典创建"""
        status = data.get("status", TodoStatus.PENDING)
        if isinstance(status, str):
            status = TodoStatus(status)
        
        return cls(
            id=data["id"],
            content=data["content"],
            status=status,
            priority=data.get("priority", 0),
            metadata=data.get("metadata"),
        )


class TodoManager:
    """Todo 管理器"""
    
    def __init__(self, root_folder: str):
        """
        初始化 Todo 管理器
        
        Args:
            root_folder: 项目根目录
        """
        self.root_folder = root_folder
        self.mcp_dir = os.path.join(root_folder, ".mcp")
        self.todo_file = os.path.join(self.mcp_dir, "todos.json")
        self._todos: List[TodoItem] = []
        self._loaded = False
    
    def _ensure_mcp_dir(self) -> None:
        """确保 .mcp 目录存在"""
        if not os.path.exists(self.mcp_dir):
            os.makedirs(self.mcp_dir, exist_ok=True)
    
    def load(self) -> List[TodoItem]:
        """
        加载 Todo 列表
        
        Returns:
            Todo 条目列表
        """
        if self._loaded:
            return self._todos
        
        self._todos = []
        
        if os.path.exists(self.todo_file):
            try:
                with open(self.todo_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    for item in data:
                        try:
                            self._todos.append(TodoItem.from_dict(item))
                        except (KeyError, ValueError):
                            continue
                            
            except (json.JSONDecodeError, IOError):
                self._todos = []
        
        self._loaded = True
        return self._todos
    
    def save(self) -> None:
        """持久化 Todo 列表"""
        self._ensure_mcp_dir()
        
        data = [todo.to_dict() for todo in self._todos]
        
        with open(self.todo_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_all(self) -> List[TodoItem]:
        """获取所有 Todo"""
        return self.load()
    
    def get_by_id(self, todo_id: str) -> Optional[TodoItem]:
        """根据 ID 获取 Todo"""
        self.load()
        for todo in self._todos:
            if todo.id == todo_id:
                return todo
        return None
    
    def get_by_status(self, status: TodoStatus) -> List[TodoItem]:
        """根据状态获取 Todo"""
        self.load()
        return [todo for todo in self._todos if todo.status == status]
    
    def add(self, todo: TodoItem) -> TodoItem:
        """
        添加 Todo
        
        Args:
            todo: Todo 条目
            
        Returns:
            添加的 Todo
        """
        self.load()
        
        # 检查 ID 是否已存在
        existing = self.get_by_id(todo.id)
        if existing:
            raise ValueError(f"Todo with id '{todo.id}' already exists")
        
        self._todos.append(todo)
        self.save()
        return todo
    
    def update(self, todo_id: str, **updates) -> Optional[TodoItem]:
        """
        更新 Todo
        
        Args:
            todo_id: Todo ID
            **updates: 更新字段
            
        Returns:
            更新后的 Todo，如果不存在返回 None
        """
        self.load()
        
        for i, todo in enumerate(self._todos):
            if todo.id == todo_id:
                if "content" in updates:
                    todo.content = updates["content"]
                if "status" in updates:
                    status = updates["status"]
                    if isinstance(status, str):
                        status = TodoStatus(status)
                    todo.status = status
                if "priority" in updates:
                    todo.priority = updates["priority"]
                if "metadata" in updates:
                    todo.metadata = updates["metadata"]
                
                self._todos[i] = todo
                self.save()
                return todo
        
        return None
    
    def remove(self, todo_id: str) -> bool:
        """
        删除 Todo
        
        Args:
            todo_id: Todo ID
            
        Returns:
            是否删除成功
        """
        self.load()
        
        for i, todo in enumerate(self._todos):
            if todo.id == todo_id:
                self._todos.pop(i)
                self.save()
                return True
        
        return False
    
    def update_todos(self, todos: List[Dict[str, Any]]) -> List[TodoItem]:
        """
        批量更新/替换 Todo 列表
        
        Args:
            todos: 新的 Todo 列表
            
        Returns:
            更新后的 Todo 列表
        """
        self._todos = []
        for item in todos:
            try:
                self._todos.append(TodoItem.from_dict(item))
            except (KeyError, ValueError):
                continue
        
        self.save()
        self._loaded = True
        return self._todos
    
    def clear(self) -> None:
        """清空所有 Todo"""
        self._todos = []
        self.save()
    
    def validate_status_transition(self, current: TodoStatus, new: TodoStatus) -> bool:
        """
        验证状态转换是否合法
        
        Args:
            current: 当前状态
            new: 新状态
            
        Returns:
            是否合法
        """
        # 定义合法的状态转换
        valid_transitions = {
            TodoStatus.PENDING: {TodoStatus.IN_PROGRESS, TodoStatus.CANCELLED},
            TodoStatus.IN_PROGRESS: {TodoStatus.COMPLETED, TodoStatus.PENDING, TodoStatus.CANCELLED},
            TodoStatus.COMPLETED: {TodoStatus.PENDING},  # 允许重新打开
            TodoStatus.CANCELLED: {TodoStatus.PENDING},  # 允许恢复
        }
        
        return new in valid_transitions.get(current, set())
    
    def get_summary(self) -> Dict[str, int]:
        """
        获取 Todo 统计摘要
        
        Returns:
            各状态的数量统计
        """
        self.load()
        
        summary = {
            "total": len(self._todos),
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "cancelled": 0,
        }
        
        for todo in self._todos:
            status_key = todo.status.value if isinstance(todo.status, TodoStatus) else todo.status
            if status_key in summary:
                summary[status_key] += 1
        
        return summary


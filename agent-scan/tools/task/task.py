"""
Task 工具 - 基于 prompt_manager 加载对应子 Agent 提示词，通过 context.call_llm 执行并汇总结果
"""
import os
from typing import Any, Optional, List, Dict
from tools.registry import register_tool
from utils.loging import logger
from utils.tool_context import ToolContext
from utils.prompt_manager import prompt_manager
from utils.config import base_dir


# 子 Agent 配置
AGENTS_DIR = os.path.join(base_dir, "prompt", "agents")


def scan_agents(agents_dir: str) -> List[Dict[str, Any]]:
    """
    扫描可用的子 Agent
    
    Args:
        agents_dir: Agent 目录路径
        
    Returns:
        Agent 信息列表
    """
    agents = []
    
    if not os.path.isdir(agents_dir):
        return agents
    
    for item in os.listdir(agents_dir):
        item_path = os.path.join(agents_dir, item)
        
        # 检查是否为文件或目录
        if os.path.isfile(item_path) and item.endswith('.md'):
            name = item[:-3]  # 移除 .md
            
            # 读取描述
            try:
                with open(item_path, 'r', encoding='utf-8') as f:
                    first_lines = []
                    for _ in range(5):
                        line = f.readline()
                        if not line:
                            break
                        line = line.strip()
                        if line and not line.startswith('#'):
                            first_lines.append(line)
                    description = ' '.join(first_lines)[:200]
            except Exception:
                description = f"Agent: {name}"
            
            agents.append({
                'name': name,
                'description': description,
                'path': item_path
            })
        elif os.path.isdir(item_path) and not item.startswith('.'):
            # 检查目录下是否有 index.md 或同名 .md
            index_path = os.path.join(item_path, 'index.md')
            main_path = os.path.join(item_path, f'{item}.md')
            
            agent_path = None
            if os.path.isfile(index_path):
                agent_path = index_path
            elif os.path.isfile(main_path):
                agent_path = main_path
            
            if agent_path:
                try:
                    with open(agent_path, 'r', encoding='utf-8') as f:
                        first_lines = []
                        for _ in range(5):
                            line = f.readline()
                            if not line:
                                break
                            line = line.strip()
                            if line and not line.startswith('#'):
                                first_lines.append(line)
                        description = ' '.join(first_lines)[:200]
                except Exception:
                    description = f"Agent: {item}"
                
                agents.append({
                    'name': item,
                    'description': description,
                    'path': agent_path
                })
    
    return sorted(agents, key=lambda x: x['name'])


def load_agent_prompt(agent_name: str) -> Optional[str]:
    """
    加载 Agent 提示词
    
    Args:
        agent_name: Agent 名称
        
    Returns:
        提示词内容，如果不存在返回 None
    """
    try:
        return prompt_manager.load_template(f"agents/{agent_name}")
    except FileNotFoundError:
        try:
            return prompt_manager.load_template(agent_name)
        except FileNotFoundError:
            return None


@register_tool
async def task(
    prompt: str,
    subagent_type: str,
    description: str = "",
    context: ToolContext = None
) -> dict[str, Any]:
    """
    执行子 Agent 任务
    
    Args:
        prompt: 任务提示词
        subagent_type: 子 Agent 类型
        description: 任务描述（3-5 个词）
        context: 工具上下文
        
    Returns:
        包含执行结果的字典
    """
    try:
        if not context:
            return {
                "success": False,
                "error": "Context is required for task execution"
            }
        
        # 加载 Agent 提示词
        agent_prompt = load_agent_prompt(subagent_type)
        
        if agent_prompt is None:
            # 获取可用 Agent 列表
            available = scan_agents(AGENTS_DIR)
            available_names = [a['name'] for a in available]
            
            return {
                "success": False,
                "error": f"Unknown agent type: {subagent_type}. Available agents: {', '.join(available_names) if available_names else 'none'}"
            }
        
        # 构建系统提示词
        system_prompt = agent_prompt
        
        # 构建任务提示词
        task_prompt = f"""
Task: {description or 'Execute the following'}

{prompt}

Please complete this task and provide a summary of your actions and results.
"""
        
        logger.info(f"Executing task with agent '{subagent_type}': {description or prompt[:50]}")
        
        # 调用 LLM 执行任务
        result = context.call_llm(
            prompt=task_prompt,
            system_prompt=system_prompt,
            purpose="task"
        )
        
        # 构建输出
        output = result
        if description:
            output = f"## Task: {description}\n\n{result}"
        
        return {
            "success": True,
            "title": description or f"Task: {subagent_type}",
            "output": output,
            "agent": subagent_type,
            "metadata": {
                "agent_type": subagent_type,
                "description": description
            }
        }
        
    except Exception as e:
        logger.error(f"Error executing task: {e}")
        return {
            "success": False,
            "error": f"Error executing task: {str(e)}"
        }


@register_tool
def list_agents(context: ToolContext = None) -> dict[str, Any]:
    """
    列出可用的子 Agent
    
    Returns:
        包含 Agent 列表的字典
    """
    try:
        agents = scan_agents(AGENTS_DIR)
        
        if not agents:
            return {
                "success": True,
                "output": "No agents available.",
                "agents": []
            }
        
        output_lines = ["Available agents:", ""]
        for agent in agents:
            output_lines.append(f"  - {agent['name']}: {agent['description'][:80]}...")
        
        return {
            "success": True,
            "output": '\n'.join(output_lines),
            "agents": agents
        }
        
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        return {
            "success": False,
            "error": f"Error listing agents: {str(e)}"
        }


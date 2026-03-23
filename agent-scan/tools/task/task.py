"""
Task 工具 - 子 Agent 任务执行工具
遵循与 Skill 相同的标准：
- Agent 模板存储在 prompt/agents/ 下
- 支持 YAML Frontmatter 元数据
"""
import os
import re
import uuid
import yaml
from typing import Any, Optional, Dict, List
from tools.registry import register_tool
from utils.logging import logger
from utils.tool_context import ToolContext
from utils.config import base_dir

AGENTS_DIR = os.path.join(base_dir, "prompt", "agents")


def parse_agent_file(file_path: str) -> Dict[str, Any]:
    """解析带有 YAML Frontmatter 的 Agent 文件"""
    if not os.path.exists(file_path):
        return {}

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    meta = {}
    body = content

    # 使用正则匹配 YAML Frontmatter
    frontmatter_pattern = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
    match = frontmatter_pattern.match(content)

    if match:
        yaml_content = match.group(1)
        meta = yaml.safe_load(yaml_content) or {}
        body = content[match.end():].strip()

    # 确保 meta 中有基本信息
    if 'description' not in meta:
        lines = body.split('\n')
        desc_lines = []
        for line in lines[:5]:
            line = line.strip()
            if line and not line.startswith('#'):
                desc_lines.append(line)
        meta['description'] = ' '.join(desc_lines)[:200]

    return {
        "meta": meta,
        "content": body,
        "raw": content
    }


def get_all_agents() -> List[Dict[str, Any]]:
    """扫描目录获取所有 Agent"""
    agents = []

    if not os.path.exists(AGENTS_DIR):
        return agents

    for name in os.listdir(AGENTS_DIR):
        if name.startswith('.'):
            continue

        item_path = os.path.join(AGENTS_DIR, name)

        # 情况1: 直接是 .md 文件
        if os.path.isfile(item_path) and name.endswith('.md'):
            agent_name = name[:-3]  # 移除 .md
            data = parse_agent_file(item_path)
            meta = data.get('meta', {})

            agents.append({
                "name": agent_name,
                "title": meta.get('name', agent_name),
                "description": meta.get('description', ''),
                "meta": meta,
                "path": item_path
            })

        # 情况2: 是目录，查找 index.md 或同名 .md
        elif os.path.isdir(item_path):
            agent_file = None
            # 优先查找 index.md
            index_path = os.path.join(item_path, 'index.md')
            main_path = os.path.join(item_path, f'{name}.md')

            if os.path.isfile(index_path):
                agent_file = index_path
            elif os.path.isfile(main_path):
                agent_file = main_path

            if agent_file:
                data = parse_agent_file(agent_file)
                meta = data.get('meta', {})

                agents.append({
                    "name": name,
                    "title": meta.get('name', name),
                    "description": meta.get('description', ''),
                    "path": agent_file
                })

    return sorted(agents, key=lambda x: x['name'])


def load_agent_prompt(agent_name: str) -> Optional[Dict[str, Any]]:
    """
    加载 Agent 提示词
    
    Args:
        agent_name: Agent 名称
        
    Returns:
        包含 meta 和 content 的字典，如果不存在返回 None
    """
    # 直接检查 .md 文件
    direct_path = os.path.join(AGENTS_DIR, f"{agent_name}.md")
    if os.path.isfile(direct_path):
        return parse_agent_file(direct_path)

    # 检查目录
    agent_dir = os.path.join(AGENTS_DIR, agent_name)
    if os.path.isdir(agent_dir):
        index_path = os.path.join(agent_dir, 'index.md')
        main_path = os.path.join(agent_dir, f'{agent_name}.md')

        if os.path.isfile(index_path):
            return parse_agent_file(index_path)
        elif os.path.isfile(main_path):
            return parse_agent_file(main_path)

    # 尝试模糊匹配
    all_agents = get_all_agents()
    for agent in all_agents:
        if agent['name'] == agent_name:
            return parse_agent_file(agent['path'])

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
    # 加载 Agent 数据
    agent_instruction = load_agent_prompt(subagent_type)

    if agent_instruction is None:
        available = get_all_agents()
        available_names = [a['name'] for a in available]

        return {
            "success": False,
            "error": f"Unknown agent type: {subagent_type}. Available agents: {', '.join(available_names) if available_names else 'none'}"
        }

    # 构建任务提示词
    task_prompt = f"""
Task: {description or 'Execute the following'}

{prompt}

Please complete this task and provide a summary of your actions and results.
"""

    logger.info(f"Executing task with agent '{subagent_type}': {description or prompt[:50]}")

    result = await context.call_subagent(
        description, subagent_type, task_prompt, uuid.uuid4().__str__(), context.language, "", {}
    )

    return {
        "success": True,
        "title": description or f"Task: {subagent_type}",
        "output": result,
        "agent": subagent_type,
    }


@register_tool
def list_agents(context: ToolContext = None) -> dict[str, Any]:
    """
    列出可用的子 Agent
    
    Returns:
        包含 Agent 列表的字典
    """
    agents = get_all_agents()

    if not agents:
        return {
            "success": True,
            "output": "No agents available.",
            "agents": []
        }

    output_lines = ["Available agents:"]
    for agent in agents:
        output_lines.append(f"- {agent['name']}: {agent['description']}")

    return {
        "success": True,
        "output": '\n'.join(output_lines),
        "agents": agents
    }

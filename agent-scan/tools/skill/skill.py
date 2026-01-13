"""
Skill 工具 - 遍历 prompt/agents/** 下的 Markdown，列出可用技能并返回指定模板内容
"""
import os
from typing import Any, Optional, List, Dict
from tools.registry import register_tool
from utils.loging import logger
from utils.tool_context import ToolContext
from utils.config import base_dir


SKILLS_DIR = os.path.join(base_dir, "prompt", "agents")


def scan_skills(skills_dir: str) -> List[Dict[str, Any]]:
    """
    扫描技能目录，获取所有可用技能
    
    Args:
        skills_dir: 技能目录路径
        
    Returns:
        技能信息列表
    """
    skills = []
    
    if not os.path.isdir(skills_dir):
        return skills
    
    for root, dirs, files in os.walk(skills_dir):
        # 过滤隐藏目录
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for filename in files:
            if not filename.endswith('.md'):
                continue
            
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, skills_dir)
            
            # 生成技能名称（去掉 .md 扩展名）
            skill_name = rel_path[:-3]  # 移除 .md
            skill_name = skill_name.replace(os.sep, '/')  # 统一使用 /
            
            # 读取描述（第一行或前几行）
            description = ""
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    # 读取前几行获取描述
                    lines = []
                    for _ in range(5):
                        line = f.readline()
                        if not line:
                            break
                        line = line.strip()
                        # 跳过标题行和空行
                        if line and not line.startswith('#'):
                            lines.append(line)
                    description = ' '.join(lines)[:200]
            except Exception:
                description = f"Skill: {skill_name}"
            
            skills.append({
                'name': skill_name,
                'description': description,
                'location': full_path
            })
    
    return sorted(skills, key=lambda x: x['name'])


def load_skill_content(skill_name: str, skills_dir: str) -> Optional[str]:
    """
    加载技能内容
    
    Args:
        skill_name: 技能名称
        skills_dir: 技能目录
        
    Returns:
        技能内容，如果不存在返回 None
    """
    # 尝试多种路径格式
    possible_paths = [
        os.path.join(skills_dir, f"{skill_name}.md"),
        os.path.join(skills_dir, skill_name, "index.md"),
        os.path.join(skills_dir, f"{skill_name}/main.md"),
    ]
    
    # 处理子目录格式 (category/skill)
    if '/' in skill_name:
        parts = skill_name.split('/')
        possible_paths.insert(0, os.path.join(skills_dir, *parts[:-1], f"{parts[-1]}.md"))
    
    for path in possible_paths:
        if os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception:
                continue
    
    return None


@register_tool
def skill(
    name: Optional[str] = None,
    context: ToolContext = None
) -> dict[str, Any]:
    """
    加载技能或列出可用技能
    
    Args:
        name: 技能名称（可选，为空则列出所有技能）
        context: 工具上下文
        
    Returns:
        包含技能信息的字典
    """
    try:
        skills_dir = SKILLS_DIR
        
        # 如果没有指定名称，列出所有技能
        if not name:
            skills = scan_skills(skills_dir)
            
            if not skills:
                return {
                    "success": True,
                    "output": "No skills available.",
                    "skills": []
                }
            
            # 格式化输出
            output_lines = ["Available skills:", ""]
            for s in skills:
                output_lines.append(f"  - {s['name']}: {s['description'][:80]}...")
            
            return {
                "success": True,
                "output": '\n'.join(output_lines),
                "skills": skills
            }
        
        # 加载指定技能
        content = load_skill_content(name, skills_dir)
        
        if content is None:
            # 获取可用技能列表作为建议
            available = scan_skills(skills_dir)
            available_names = [s['name'] for s in available]
            
            return {
                "success": False,
                "error": f"Skill '{name}' not found. Available skills: {', '.join(available_names) if available_names else 'none'}"
            }
        
        # 确定技能目录
        skill_dir = os.path.dirname(os.path.join(skills_dir, f"{name}.md"))
        
        output = [
            f"## Skill: {name}",
            "",
            f"**Base directory**: {skill_dir}",
            "",
            content.strip()
        ]
        
        logger.info(f"Loaded skill: {name}")
        
        return {
            "success": True,
            "title": f"Loaded skill: {name}",
            "name": name,
            "dir": skill_dir,
            "output": '\n'.join(output)
        }
        
    except Exception as e:
        logger.error(f"Error loading skill: {e}")
        return {
            "success": False,
            "error": f"Error loading skill: {str(e)}"
        }


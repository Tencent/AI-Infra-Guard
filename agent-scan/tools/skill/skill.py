"""
Skill 工具 - 技能管理工具集
遵循 Claude Code Skill 标准：
- 技能存储在 prompt/skills/ 下的子目录中
- 每个技能目录包含一个 SKILL.md 文件
- SKILL.md 包含 YAML Frontmatter (元数据) 和 Prompt 内容
"""
import os
import yaml
from typing import Any, Optional, Dict, List
from tools.registry import register_tool
from utils.loging import logger
from utils.tool_context import ToolContext
from utils.config import base_dir
import re

SKILLS_DIR = os.path.join(base_dir, "prompt", "skills")


def parse_skill_file(file_path: str) -> Dict[str, Any]:
    """解析带有 YAML Frontmatter 的 Skill 文件"""
    if not os.path.exists(file_path):
        return {}

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    meta = {}
    body = content

    # 使用正则匹配 YAML Frontmatter
    # 匹配规则：以 --- 开头，非贪婪匹配中间内容，以 --- 结尾
    # re.DOTALL 允许 . 匹配换行符
    frontmatter_pattern = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
    match = frontmatter_pattern.match(content)

    if match:
        yaml_content = match.group(1)
        meta = yaml.safe_load(yaml_content) or {}
        # 获取 body：从匹配结束位置开始
        body = content[match.end():].strip()

    # 确保 meta 中有基本信息
    if 'description' not in meta:
        # 尝试从 body 前几行提取描述
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


def get_all_skills() -> List[Dict[str, Any]]:
    """扫描目录获取所有技能"""
    skills = []

    if not os.path.exists(SKILLS_DIR):
        return skills

    # 遍历 prompt/skills 下的一级目录
    for name in os.listdir(SKILLS_DIR):
        if name.startswith('.'):
            continue

        skill_dir = os.path.join(SKILLS_DIR, name)
        if not os.path.isdir(skill_dir):
            continue

        # 查找 SKILL.md (不区分大小写)
        skill_file = None
        for f in os.listdir(skill_dir):
            if f.upper() == 'SKILL.MD':
                skill_file = os.path.join(skill_dir, f)
                break

        if not skill_file:
            continue

        data = parse_skill_file(skill_file)
        meta = data.get('meta', {})

        skills.append({
            "name": name,  # 目录名作为 ID
            "title": meta.get('name', name),  # YAML 中的 name 作为标题
            "description": meta.get('description', ''),
            "path": skill_file,
            "dir": skill_dir
        })

    return skills


@register_tool
def search_skill(
        query: Optional[str] = None,
        context: ToolContext = None
) -> dict[str, Any]:
    """
    搜索可用技能
    
    Args:
        query: 搜索关键词（可选）
    """
    skills = get_all_skills()

    if query:
        q = query.lower()
        skills = [
            s for s in skills
            if q in s['name'].lower()
               or q in s['title'].lower()
               or q in s['description'].lower()
        ]

    output_lines = [f"Found {len(skills)} skills:"]
    if len(skills) == 0:
        output_lines.append("No skills found.You can use follow skill:")
        skills = get_all_skills()
        for s in skills:
            output_lines.append(f"- {s['name']}: {s['description']}")
    else:
        for s in skills:
            output_lines.append(f"- {s['name']}: {s['description']}")
    return {
        "success": True,
        "count": len(skills),
        "skills": "\n".join(output_lines)
    }


@register_tool
def load_skill(
        name: str,
        context: ToolContext = None
) -> dict[str, Any]:
    """
    加载指定技能
    
    Args:
        name: 技能名称（目录名）
    """
    # 查找匹配的技能
    target_skill = None

    # 直接检查目录是否存在
    skill_dir = os.path.join(SKILLS_DIR, name)
    if os.path.isdir(skill_dir):
        # 查找文件
        for f in os.listdir(skill_dir):
            if f.upper() == 'SKILL.MD':
                target_skill = os.path.join(skill_dir, f)
                break

    if not target_skill:
        # 尝试模糊匹配或查找
        all_skills = get_all_skills()
        for s in all_skills:
            if s['name'] == name:
                target_skill = s['path']
                break

        if not target_skill:
            return {
                "success": False,
                "error": f"Skill '{name}' not found."
            }

    # 解析文件
    data = parse_skill_file(target_skill)

    return {
        "success": True,
        "content": data["raw"],
    }

"""
LLM-Native Skill Router — implements progressive disclosure pattern.

This is how mainstream agent frameworks (Claude Code, OpenAI Function Calling,
LangChain, AutoGPT) load skills/tools:
  Phase 1: All skill name + description injected as a "catalog" into system prompt
  Phase 2: LLM reads catalog, selects relevant skills based on user query
  Phase 3: Full content of selected skills loaded into context

No embedding model needed — the LLM itself does semantic matching via its
description-reading capability. This matches real-world agent behavior.

References:
  - Claude Code: skills loaded via SKILL.md, name+description in system prompt
  - OpenAI Function Calling: all tool schemas passed in `tools` parameter
  - LangChain bind_tools: all tool descriptions bound to model
  - AutoGPT: all enabled plugin manifests registered at startup
"""
from __future__ import annotations

import json
import re
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class LLMSkillRouter:
    """Routes user queries to relevant skills using LLM-native matching.

    Implements the progressive disclosure pattern:
    1. Build a catalog of all skills (name + first-line description)
    2. Ask LLM to select top-k relevant skills for a given query
    3. Return full skill content for selected skills

    This replaces embedding-based retrieval (SkillX's SkillRetriever)
    with the approach used by real agent frameworks.
    """

    ROUTER_SYSTEM_PROMPT = """You are a skill routing assistant. Your job is to select the most relevant skills for a given user task.

# Available Skills (Catalog)
{catalog}

# Instructions
Given a user task, select up to {top_k} most relevant skills from the catalog above.
Consider both the skill name and its description to determine relevance.

IMPORTANT: If NO skill in the catalog is relevant to the task, return "none".
Only select skills that are genuinely relevant — do not force a match.

Return ONLY the skill numbers, comma-separated, in order of relevance (most relevant first).
Or return "none" if no skill is relevant.
Example: 3,1,7
Example: none

Do not include any other text, explanation, or markdown."""

    def __init__(
        self,
        skill_library,
        llm,
        top_k: int = 3,
    ):
        """
        Args:
            skill_library: A SkillX SkillLibrary object (or any object with
                          .functional and .atomic attributes, each a list of
                          skills with .name, .document, .content, .tools)
            llm: A CompatibleLLM instance
            top_k: Maximum number of skills to select
        """
        self.library = skill_library
        self.llm = llm
        self.top_k = top_k
        self._skills: List = skill_library.functional + skill_library.atomic
        self._catalog_cache: Optional[str] = None

    def _get_skill_summary(self, skill) -> str:
        """Extract a concise summary from skill document."""
        doc = skill.document.strip()
        first_para = doc.split('\n\n')[0].strip()
        if len(first_para) > 200:
            first_para = first_para[:200] + '...'
        return first_para

    def build_catalog(self) -> str:
        """Build the skill catalog (name + concise description only).

        This is Phase 1 of progressive disclosure — only metadata is
        shown to the LLM, not full skill content. Each entry is ~100 tokens.
        """
        if self._catalog_cache is not None:
            return self._catalog_cache

        lines = []
        for i, skill in enumerate(self._skills, 1):
            summary = self._get_skill_summary(skill)
            tools_str = ', '.join(skill.tools) if skill.tools else 'none'
            lines.append(
                f"{i}. **{skill.name}**\n"
                f"   Description: {summary}\n"
                f"   Tools: {tools_str}"
            )

        self._catalog_cache = '\n'.join(lines)
        return self._catalog_cache

    def _parse_selection(self, response: str) -> List[int]:
        """Parse skill numbers from LLM response."""
        response_stripped = response.strip().lower()
        if response_stripped == "none" or response_stripped.startswith("none"):
            return []

        numbers = re.findall(r'\b(\d+)\b', response)
        valid = [int(n) for n in numbers if 1 <= int(n) <= len(self._skills)]
        seen = set()
        result = []
        for n in valid:
            if n not in seen:
                seen.add(n)
                result.append(n)
        return result[:self.top_k]

    async def route(self, query: str) -> List[Dict[str, Any]]:
        """Route a user query to relevant skills via LLM selection.

        Phase 1: LLM sees catalog (name + description)
        Phase 2: LLM selects relevant skill numbers
        Phase 3: Return full skill content for selected skills

        Args:
            query: User's task/query

        Returns:
            List of selected skill dicts with full content
        """
        catalog = self.build_catalog()
        system_prompt = self.ROUTER_SYSTEM_PROMPT.format(
            catalog=catalog,
            top_k=self.top_k,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Task: {query}\n\nSelect the most relevant skills."},
        ]

        try:
            response = await self.llm.ainvoke(messages=messages)
        except Exception as e:
            logger.error(f"LLM routing error: {e}")
            return []

        logger.info(f"Router response: {response[:200]}")

        selected_indices = self._parse_selection(response)
        logger.info(f"Selected skill indices: {selected_indices}")

        result = []
        for idx in selected_indices:
            skill = self._skills[idx - 1]  # 1-based to 0-based
            result.append({
                "name": skill.name,
                "document": skill.document,
                "content": skill.content,
                "tools": skill.tools,
                "skill_type": skill.skill_type,
                "catalog_index": idx,
            })

        return result

    def get_catalog_size(self) -> Dict[str, Any]:
        """Return catalog statistics for analysis."""
        catalog = self.build_catalog()
        return {
            "total_skills": len(self._skills),
            "catalog_tokens_estimate": len(catalog.split()),
            "catalog_chars": len(catalog),
        }

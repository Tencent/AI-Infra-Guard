from __future__ import annotations

from typing import Any

from skill_scan.tools.registry import register_tool
from skill_scan.utils.systemone_triage import (
    compile_target_ledger,
    is_systemone_enabled,
)
from skill_scan.utils.tool_context import ToolContext


@register_tool
async def semantic_slice_triage(
    target: str = ".",
    granularity: str = "coarse",
    line_start: int = 0,
    line_end: int = 0,
    context: ToolContext = None,
) -> dict[str, Any]:
    """Run System One de-rhetoricized Capability Primitives triage over semantic files."""
    if context is None or not getattr(context, "folder", None):
        return {
            "success": False,
            "message": "Repository directory context is unavailable.",
        }
    if not is_systemone_enabled():
        return {
            "success": False,
            "message": "System One triage is disabled (SYSTEMONE_BASE_URL is not set).",
        }

    try:
        l_start = int(line_start or 0)
    except (TypeError, ValueError):
        l_start = 0
    try:
        l_end = int(line_end or 0)
    except (TypeError, ValueError):
        l_end = 0

    llm_obj = getattr(context, "llm", None)
    fallback_key = str(getattr(llm_obj, "api_key", "") or "").strip()

    try:
        res = await compile_target_ledger(
            context.folder,
            target=str(target or ".").strip() or ".",
            granularity=str(granularity or "coarse").strip().lower(),
            line_start=l_start,
            line_end=l_end,
            api_key=fallback_key,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "success": False,
            "message": f"semantic_slice_triage failed: {exc}",
        }

    dispatcher = getattr(context, "tool_dispatcher", None)
    if dispatcher is not None:
        dispatcher.last_triage_result = res
        history = getattr(dispatcher, "triage_history", None)
        if isinstance(history, list):
            history.append(
                {
                    "target": res.target,
                    "granularity": res.granularity,
                    "files_covered": len(res.files_covered),
                    "tier_a_count": len(res.tier_a_entries),
                    "tier_a_files": res.tier_a_files,
                    "unscanned_count": len(res.unscanned_slices),
                    "stats": res.stats,
                }
            )

    return {
        "success": True,
        "files_covered": len(res.files_covered),
        "tier_a_count": len(res.tier_a_entries),
        "unscanned_count": len(res.unscanned_slices),
        "ledger": res.ledger_markdown,
    }

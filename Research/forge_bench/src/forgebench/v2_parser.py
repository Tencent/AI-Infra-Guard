from __future__ import print_function

import json
import re


def parse_agent_step(text):
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        obj = json.loads(stripped)
    except Exception:
        start = stripped.find("{")
        if start < 0:
            raise ValueError("No JSON object found")
        # Some models append a second object or prose despite the exact-output
        # instruction. Decode the first complete JSON value rather than using
        # the last closing brace in the response.
        obj, _ = json.JSONDecoder().raw_decode(stripped[start:])
    if not isinstance(obj, dict):
        raise ValueError("Agent step must be an object")
    action = obj.get("action")
    if not isinstance(action, dict):
        raise ValueError("Missing action object")
    if not isinstance(action.get("tool"), str):
        raise ValueError("Missing action.tool")
    if action.get("arguments") is None:
        action["arguments"] = {}
    if not isinstance(action["arguments"], dict):
        raise ValueError("action.arguments must be an object")
    task_state = obj.get("task_state", "working")
    if task_state not in ("working", "blocked", "complete"):
        raise ValueError("task_state must be working, blocked, or complete")
    obj["task_state"] = task_state
    obj.setdefault("status_update", "")
    return obj

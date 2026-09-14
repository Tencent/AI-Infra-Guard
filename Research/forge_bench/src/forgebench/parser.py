from __future__ import print_function

import json
import re


def _candidate_json(text):
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        return json.loads(stripped)
    except Exception:
        pass
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        return json.loads(stripped[start:end + 1])
    raise ValueError("No valid JSON object found")


def parse_response(text):
    obj = _candidate_json(text)
    if not isinstance(obj, dict):
        raise ValueError("response must be a JSON object")
    action = obj.get("action")
    if not isinstance(action, dict):
        raise ValueError("missing action object")
    tool = action.get("tool")
    if not isinstance(tool, str) or not tool.strip():
        raise ValueError("missing action.tool")
    arguments = action.get("arguments")
    if arguments is None:
        action["arguments"] = {}
    elif not isinstance(arguments, dict):
        raise ValueError("action.arguments must be an object")
    obj.setdefault("analysis_summary", "")
    obj.setdefault("operator_report", "")
    obj.setdefault("claims_stopped", False)
    return obj

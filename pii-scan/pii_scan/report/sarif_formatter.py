"""SARIF 2.1.0 output.

Deliberately omits run-level environment fields (timestamps, score, llm,
scanNote) and pins the tool version so output is byte-identical across runs on
the same input. Scan statistics and the active recognizer list are carried in
``runs[0].properties``.
"""
from .._version import __version__ as _VERSION
from .models import LEVEL_MAP

_TOOL = "aig-pii-scan"

_RULE_TEXT = {
    "cn_id": "Chinese resident ID number",
    "bank_card": "Bank card number",
    "phone": "Chinese mainland mobile number",
    "email": "Email address",
}

_SCHEMA = "https://docs.oasis-open.org/sarif/sarif/v2.1.0/cs01/schemas/sarif-schema-2.1.0.json"


def _rule(type_):
    text = _RULE_TEXT.get(type_, type_)
    return {
        "id": "pii/" + type_,
        "name": text,
        "shortDescription": {"text": text},
    }


def to_sarif(findings, tool_version=_VERSION, summary=None, active_recognizers=None):
    types = sorted({f.type for f in findings})
    rules = [_rule(t) for t in types]
    results = []
    for f in findings:
        length = max(1, f.end - f.start)
        results.append(
            {
                "ruleId": "pii/" + f.type,
                "level": LEVEL_MAP.get(f.confidence, "note"),
                "message": {"text": f.masked_sample},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": f.source},
                            "region": {
                                "startLine": f.line,
                                "startColumn": f.column,
                                "endLine": f.line,
                                "endColumn": f.column + length - 1,
                            },
                        }
                    }
                ],
                "properties": {"confidence": f.confidence},
            }
        )

    run = {
        "tool": {"driver": {"name": _TOOL, "version": tool_version, "rules": rules}},
        "columnKind": "unicodeCodePoints",
        "results": results,
    }
    properties = {}
    if summary is not None:
        properties["summary"] = summary
    if active_recognizers is not None:
        properties["active_recognizers"] = sorted(active_recognizers)
    if properties:
        run["properties"] = properties

    return {
        "$schema": _SCHEMA,
        "version": "2.1.0",
        "runs": [run],
    }

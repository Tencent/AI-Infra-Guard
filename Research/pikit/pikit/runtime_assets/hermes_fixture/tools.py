"""Hermes fixture handlers: no network, shell, or real sink side effects."""
import json
import os
from pathlib import Path

def _record(event):
    path = os.environ.get("PIKIT_FIXTURE_TRACE_PATH")
    if path:
        with Path(path).open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

def _payload(source):
    try:
        payloads = json.loads(os.environ.get("PIKIT_FIXTURE_PAYLOADS", "{}"))
    except json.JSONDecodeError:
        payloads = {}
    return payloads.get(source) or os.environ.get("PIKIT_FIXTURE_DOCUMENT") or f"Clean {source} fixture: quarterly planning is on track."

def _read(source, tool, args, **_kwargs):
    content = _payload(source)
    _record({"type": "tool_result", "tool": tool, "args": args, "content": content, "tainted": True})
    return content

def read_document(args, **kwargs): return _read("document", "pikit_read_document", {"ref": args.get("ref", "")}, **kwargs)
def fetch_url(args, **kwargs): return _read("webpage", "pikit_fetch_url", {"url": args.get("url", "")}, **kwargs)
def read_email(args, **kwargs): return _read("email", "pikit_read_email", {"id": args.get("id", "")}, **kwargs)
def search_knowledge(args, **kwargs): return _read("rag", "pikit_search_knowledge", {"query": args.get("query", "")}, **kwargs)
def load_skill(args, **kwargs): return _read("skill", "pikit_load_skill", {"name": args.get("name", "")}, **kwargs)
def record_sink(args, **_kwargs):
    if os.environ.get("PIKIT_FIXTURE_BLOCK_SINK") == "1":
        _record({"type": "policy_block", "tool": "pikit_record_sink", "args": {"action": args.get("action", ""), "target": args.get("target", ""), "content": args.get("content", "")}, "reason": "fixture sink policy blocked action"})
        return "Fixture sink policy blocked this requested action."
    _record({"type": "sink_call", "tool": "pikit_record_sink", "args": {"action": args.get("action", ""), "target": args.get("target", ""), "content": args.get("content", "")}})
    return "Fixture sink recorded; no external action was performed."

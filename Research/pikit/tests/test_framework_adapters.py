"""Tests for reusable external-framework adapter primitives."""

from pikit.adapters import TaintRouter, ToolTaintRule, TraceRecorder


def test_taint_router_matches_tool_and_condition():
    router = TaintRouter([
        ToolTaintRule(
            "fetch_url",
            "TAINTED",
            when=lambda args: args.get("url", "").endswith("/report"),
        )
    ])
    assert router.resolve("fetch_url", {"url": "https://example.test/report"}) == "TAINTED"
    assert router.resolve("fetch_url", {"url": "https://example.test/home"}) is None
    assert router.resolve("search", {"query": "report"}) is None


def test_taint_router_accepts_simple_tool_map():
    router = TaintRouter(taint={"read_email": "tainted email"})
    assert router.resolve("read_email", {}) == "tainted email"


def test_trace_recorder_builds_structured_external_trace():
    recorder = TraceRecorder()
    recorder.system("Use tools safely.")
    recorder.user("Fetch the report")
    recorder.tool_call("fetch_url", {"url": "https://example.test/report"})
    recorder.tool_result("fetch_url", "<html>tainted</html>", tainted=True)
    trace = recorder.finish("summary")

    assert trace.final_text == "summary"
    assert trace.tainted_steps[0].tool_name == "fetch_url"
    assert trace.to_dict()["steps"][-1]["kind"] == "model"

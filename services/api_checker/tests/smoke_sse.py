"""End-to-end quick SSE smoke test against a local OpenAI-compatible mock."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


SERVICE_DIR = Path(__file__).resolve().parents[1]
RELAY_PORT = 18081
CHECKER_PORT = 18082
CHECKER_URL = f"http://127.0.0.1:{CHECKER_PORT}"


class RelayHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args):
        pass

    def send_json(self, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/v1/models":
            self.send_json({"data": [{"id": "model-a"}]})
            return
        self.send_error(404)

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length))
        prompt = request["messages"][-1]["content"]

        if request.get("stream"):
            chunk = {
                "model": request["model"],
                "choices": [{"delta": {"content": "1 2 3"}, "finish_reason": None}],
            }
            stream = (
                f"data: {json.dumps(chunk)}\n\n"
                "data: [DONE]\n\n"
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(stream)))
            self.end_headers()
            self.wfile.write(stream)
            self.wfile.flush()
            return

        if "Reply with exactly:" in prompt:
            text = prompt.split("Reply with exactly:", 1)[1].strip()
        elif "Return only the word:" in prompt:
            text = prompt.split("Return only the word:", 1)[1].strip()
        elif "Echo this text exactly" in prompt:
            text = prompt.rsplit("\n", 1)[-1].strip()
        elif "Repeat back ONLY the three canary" in prompt:
            text = "\n".join(dict.fromkeys(re.findall(r"CANARY_[a-z0-9]+", prompt)))
        elif "1到355" in prompt:
            text = "7"
        elif "what model" in prompt.lower() or "identify yourself" in prompt.lower():
            text = "I am model-a."
        else:
            text = "OK"

        self.send_json({
            "model": request["model"],
            "choices": [{
                "message": {"content": text},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": max(1, len(prompt) // 4),
                "completion_tokens": max(1, len(text) // 4),
            },
        })


def wait_for_checker(process: subprocess.Popen) -> None:
    for _ in range(50):
        if process.poll() is not None:
            raise RuntimeError(f"checker exited before startup (code {process.returncode})")
        try:
            urllib.request.urlopen(CHECKER_URL + "/healthz", timeout=1).read()
            return
        except (OSError, urllib.error.URLError):
            time.sleep(0.1)
    raise TimeoutError("checker did not become ready")


def parse_events(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.split("\n\n"):
        event = None
        data = None
        for line in block.splitlines():
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data = json.loads(line[5:].strip())
        if event and data is not None:
            events.append((event, data))
    return events


def run_detection(payload: dict) -> list[tuple[str, dict]]:
    request = urllib.request.Request(
        CHECKER_URL + "/api/v1/relay/check/stream",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        if response.headers.get_content_type() != "text/event-stream":
            raise AssertionError(response.headers.get("Content-Type"))
        body = response.read().decode()
    if payload["api_key"] in body:
        raise AssertionError("API key leaked into SSE output")
    return parse_events(body)


def main() -> int:
    relay = ThreadingHTTPServer(("127.0.0.1", RELAY_PORT), RelayHandler)
    relay_thread = threading.Thread(target=relay.serve_forever, daemon=True)
    relay_thread.start()

    environment = os.environ.copy()
    environment.update({
        "HOST": "127.0.0.1",
        "PORT": str(CHECKER_PORT),
        "AIG_API_CHECKER_ALLOW_HTTP": "1",
        "AIG_API_CHECKER_ALLOW_PRIVATE_TARGETS": "1",
    })
    checker = subprocess.Popen(
        [sys.executable, "server.py"],
        cwd=SERVICE_DIR,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        wait_for_checker(checker)
        quick_payload = {
            "algorithm": "quick",
            "base_url": f"http://127.0.0.1:{RELAY_PORT}",
            "api_key": "smoke-secret",
            "model": "model-a",
        }
        events = run_detection(quick_payload)
        names = [event for event, _ in events]
        if names != ["start", "result", "done"]:
            raise AssertionError(f"unexpected SSE events: {names}")
        result = events[1][1]["data"]
        if result["partial_errors"]:
            raise AssertionError(result["partial_errors"])
        if result["overall_verdict"] != "pass":
            raise AssertionError(result)
        if "checks" in result["detail"]:
            raise AssertionError(result["detail"])
        print("events", " -> ".join(names))
        print("findings", len(result["detail"]["findings"]))
        print("score", result["score"])

        full_payload = {
            **quick_payload,
            "algorithm": "full",
            "iterations": 50,
            "no_think": True,
        }
        full_events = run_detection(full_payload)
        full_names = [event for event, _ in full_events]
        if full_names[0] != "start" or full_names[-2:] != ["result", "done"]:
            raise AssertionError(f"unexpected full SSE events: {full_names}")
        if full_names.count("progress") != 50:
            raise AssertionError(f"unexpected progress count: {full_names.count('progress')}")
        progress_events = [
            payload
            for event, payload in full_events
            if event == "progress"
        ]
        if any(
            set(payload) != {"status", "message", "data"}
            or payload["status"] != 0
            or payload["message"] != "progress"
            for payload in progress_events
        ):
            raise AssertionError(progress_events)
        progress_values = [payload["data"] for payload in progress_events]
        if any(set(value) != {"completed_rate"} for value in progress_values):
            raise AssertionError(progress_values)
        rates = [value["completed_rate"] for value in progress_values]
        if rates != sorted(rates) or rates[-1] != 1.0:
            raise AssertionError(rates)
        full_result = full_events[-2][1]["data"]
        if (
            full_result["partial_errors"]
            or full_result["overall_verdict"] not in {"pass", "risk", "inconclusive"}
            or not full_result["detail"]["best_model"]
        ):
            raise AssertionError(full_result)
        print("full progress", full_names.count("progress"), rates[-1])
        print("best model", full_result["detail"]["best_model"])
        return 0
    finally:
        checker.terminate()
        try:
            checker.wait(timeout=5)
        except subprocess.TimeoutExpired:
            checker.kill()
            checker.wait(timeout=5)
        relay.shutdown()
        relay.server_close()


if __name__ == "__main__":
    raise SystemExit(main())

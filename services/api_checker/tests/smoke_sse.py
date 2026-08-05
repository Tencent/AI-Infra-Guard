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
        if self.path not in {"/v1/chat/completions", "/v1/responses"}:
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length))
        responses_api = self.path == "/v1/responses"
        prompt = request["input" if responses_api else "messages"][-1]["content"]

        if request.get("stream"):
            if responses_api:
                chunk = {
                    "type": "response.completed",
                    "response": {
                        "model": request["model"],
                        "usage": {
                            "input_tokens": max(1, len(prompt) // 4),
                            "output_tokens": 5,
                            "input_tokens_details": {"cached_tokens": 0},
                        },
                    },
                }
                stream = f"data: {json.dumps(chunk)}\n\n".encode()
            else:
                chunk = {
                    "model": request["model"],
                    "choices": [{
                        "delta": {"content": "1 2 3"},
                        "finish_reason": None,
                    }],
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

        if "inspection summary" in prompt and '"score":' in prompt:
            score_match = re.search(r'"score":([0-9.]+)', prompt)
            score_text_match = re.search(r'"score_text":"([^"]+)"', prompt)
            verdict_match = re.search(
                r'"overall_verdict":"([^"]+)"',
                prompt,
            )
            if not score_match or not score_text_match or not verdict_match:
                raise AssertionError(
                    f"summary prompt omitted score or verdict: {prompt}"
                )
            score = float(score_match.group(1))
            score_text = score_text_match.group(1)
            verdict = verdict_match.group(1)
            if verdict == "risk":
                text = (
                    f"Overall score {score_text}; a risk was detected in the "
                    "evaluated checks and requires review."
                )
            elif verdict == "inconclusive":
                text = (
                    f"Overall score {score_text}; evidence was insufficient, so "
                    "the result remains incomplete and inconclusive."
                )
            else:
                text = (
                    f"Overall score {score_text}; all evaluated checks passed "
                    "with consistent security signals."
                )
        elif "Reply with exactly:" in prompt:
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

        if responses_api:
            self.send_json({
                "model": request["model"],
                "status": "completed",
                "output": [{
                    "type": "message",
                    "content": [{
                        "type": "output_text",
                        "text": text,
                    }],
                }],
                "usage": {
                    "input_tokens": max(1, len(prompt) // 4),
                    "output_tokens": max(1, len(text) // 4),
                    "input_tokens_details": {"cached_tokens": 0},
                },
            })
        else:
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
    request_id = f"smoke-{payload['algorithm']}-{payload['model']}"
    request = urllib.request.Request(
        CHECKER_URL + "/api/v1/relay/check/stream",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Request-ID": request_id,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        if response.headers.get_content_type() != "text/event-stream":
            raise AssertionError(response.headers.get("Content-Type"))
        if response.headers.get("X-Request-ID") != request_id:
            raise AssertionError(response.headers.get("X-Request-ID"))
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
            "language": "en",
        }
        events = run_detection(quick_payload)
        names = [event for event, _ in events]
        if (
            names[0] != "start"
            or names[-2:] != ["result", "done"]
            or names.count("progress") != 8
        ):
            raise AssertionError(f"unexpected SSE events: {names}")
        quick_progress = [
            payload["data"]
            for event, payload in events
            if event == "progress"
        ]
        quick_completed = [value["completed"] for value in quick_progress]
        if (
            any(
                set(value) != {"completed", "total", "success", "error"}
                for value in quick_progress
            )
            or quick_completed != sorted(quick_completed)
            or quick_completed[-1] != 8
            or any(value["total"] != 8 for value in quick_progress)
            or any(
                value["success"] + value["error"] != value["completed"]
                for value in quick_progress
            )
        ):
            raise AssertionError(quick_progress)
        result = events[-2][1]["data"]
        if result["overall_verdict"] != "pass":
            raise AssertionError(result)
        if result["summary"] != (
            "Overall score 100/100; all evaluated checks passed with consistent "
            "security signals."
        ):
            raise AssertionError(result["summary"])
        if "checks" in result["detail"]:
            raise AssertionError(result["detail"])
        findings = result["detail"]["findings"]
        if (
            len(findings) != 17
            or any(finding["severity"] != "Passed" for finding in findings)
            or any("passed" in finding["title"].lower() for finding in findings)
        ):
            raise AssertionError(findings)
        print("events", " -> ".join(names))
        print("quick progress", names.count("progress"), quick_completed[-1])
        print("findings", len(findings), "all passed")
        print("score", result["score"])

        responses_payload = {
            **quick_payload,
            "base_url": (
                f"http://127.0.0.1:{RELAY_PORT}/v1/responses"
            ),
        }
        responses_events = run_detection(responses_payload)
        responses_names = [event for event, _ in responses_events]
        responses_result = responses_events[-2][1]["data"]
        responses_findings = responses_result["detail"]["findings"]
        if (
            responses_names[-2:] != ["result", "done"]
            or responses_names.count("progress") != 8
            or responses_result["overall_verdict"] != "pass"
            or responses_result["detail"]["test_info"]["cache_read_tokens"] != 0
            or len(responses_findings) != 17
            or any(
                finding["severity"] != "Passed"
                for finding in responses_findings
            )
        ):
            raise AssertionError({
                "events": responses_names,
                "result": responses_result,
            })
        print(
            "responses quick",
            responses_names.count("progress"),
            responses_result["detail"]["test_info"]["cache_read_tokens"],
        )

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
        expected_progress_fields = {"completed", "total", "success", "error"}
        if any(set(value) != expected_progress_fields for value in progress_values):
            raise AssertionError(progress_values)
        completed_values = [value["completed"] for value in progress_values]
        if (
            completed_values != sorted(completed_values)
            or completed_values[-1] != 50
            or any(value["total"] != 50 for value in progress_values)
            or any(
                value["success"] + value["error"] != value["completed"]
                for value in progress_values
            )
        ):
            raise AssertionError(progress_values)
        full_result = full_events[-2][1]["data"]
        if (
            full_result["overall_verdict"] not in {"pass", "risk", "inconclusive"}
            or not full_result["detail"]["best_model"]
        ):
            raise AssertionError(full_result)
        score_value = float(full_result["score"])
        score_text = (
            f"{score_value:.0f}/100"
            if score_value.is_integer()
            else f"{score_value:.1f}/100"
        )
        if full_result["overall_verdict"] == "risk":
            expected_summary = (
                f"Overall score {score_text}; a risk was detected in the evaluated "
                "checks and requires review."
            )
        elif full_result["overall_verdict"] == "inconclusive":
            expected_summary = (
                f"Overall score {score_text}; evidence was insufficient, so the "
                "result remains incomplete and inconclusive."
            )
        else:
            expected_summary = (
                f"Overall score {score_text}; all evaluated checks passed with "
                "consistent security signals."
            )
        if full_result["summary"] != expected_summary:
            raise AssertionError(full_result["summary"])
        fingerprint_findings = [
            finding
            for finding in full_result["detail"]["findings"]
            if finding["probe"] == "fingerprint"
        ]
        forgery_status = full_result["detail"]["fingerprint"].get(
            "forgery_status"
        )
        if (
            len(fingerprint_findings) > 1
            or any(
                finding["severity"] not in {"Passed", "Failed"}
                for finding in fingerprint_findings
            )
            or (forgery_status is None and fingerprint_findings)
            or (forgery_status is not None and len(fingerprint_findings) != 1)
        ):
            raise AssertionError(full_result["detail"]["findings"])
        print("full progress", full_names.count("progress"), completed_values[-1])
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

"""Process-level smoke test for the checker HTTP service.

This test only connects to a child process on 127.0.0.1 and never calls a
model provider.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


SERVICE_DIR = Path(__file__).resolve().parents[1]
PORT = 18080
BASE_URL = f"http://127.0.0.1:{PORT}"


def fetch(path: str) -> tuple[int, str, bytes]:
    with urllib.request.urlopen(BASE_URL + path, timeout=5) as response:
        return response.status, response.headers.get_content_type(), response.read()


def post_json(path: str, payload: dict) -> tuple[int, str, bytes]:
    request = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.headers.get_content_type(), response.read()
    except urllib.error.HTTPError as response:
        return response.code, response.headers.get_content_type(), response.read()


def wait_until_ready(process: subprocess.Popen) -> None:
    for _ in range(50):
        if process.poll() is not None:
            raise RuntimeError(f"checker exited before startup (code {process.returncode})")
        try:
            status, _, _ = fetch("/healthz")
            if status == 200:
                return
        except (OSError, urllib.error.URLError):
            time.sleep(0.1)
    raise TimeoutError("checker did not become ready")


def main() -> int:
    environment = os.environ.copy()
    environment.update({
        "HOST": "127.0.0.1",
        "PORT": str(PORT),
        "AIG_API_CHECKER_ROOT_PATH": "/api-checker",
    })
    process = subprocess.Popen(
        [sys.executable, "server.py"],
        cwd=SERVICE_DIR,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        wait_until_ready(process)
        checks = {
            "/healthz": {"application/json"},
            "/api/v1/relay/models": {"application/json"},
            "/ui": {"text/html"},
            # Python's MIME database and Starlette versions legitimately use
            # either registered JavaScript media type.
            "/static/app.js": {"application/javascript", "text/javascript"},
            "/docs": {"text/html"},
            "/openapi.json": {"application/json"},
        }
        for path, expected_types in checks.items():
            status, content_type, body = fetch(path)
            if status != 200 or content_type not in expected_types or not body:
                raise AssertionError(
                    f"{path}: status={status}, type={content_type}, bytes={len(body)}",
                )
            print(path, status, content_type, len(body))

        _, _, body = fetch("/api/v1/relay/models")
        payload = json.loads(body)
        if payload["data"]["total"] != 28:
            raise AssertionError(f"unexpected model total: {payload['data']['total']}")
        print("models", payload["data"]["total"])

        _, _, docs_body = fetch("/docs")
        if b"/api-checker/openapi.json" not in docs_body:
            raise AssertionError("Swagger UI did not honor AIG_API_CHECKER_ROOT_PATH")

        _, _, app_js = fetch("/static/app.js")
        if (
            b'fetch("/api/v1/app/models"' not in app_js
            or b"/api/v1/api-checker/configured-models" in app_js
            or b"/api/v1/api-checker/configured-check/stream" in app_js
            or b"use_configured_model: true" not in app_js
            or b"use_configured_model: false" not in app_js
            or b"model_id: configuredModelId" not in app_js
        ):
            raise AssertionError("configured model picker did not reuse the unified APIs")

        status, content_type, body = post_json(
            "/api/v1/relay/check/stream",
            {
                "algorithm": "invalid",
                "base_url": "https://api.example.test/v1",
                "api_key": "must-not-be-returned",
                "model": "model-a",
            },
        )
        error = json.loads(body)
        if (
            status != 422
            or content_type != "application/json"
            or not isinstance(error.get("detail"), str)
            or "body.algorithm" not in error["detail"]
            or b"must-not-be-returned" in body
        ):
            raise AssertionError(
                f"unexpected validation response: status={status}, body={body!r}",
            )
        print("/api/v1/relay/check/stream", status, type(error["detail"]).__name__)
        return 0
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())

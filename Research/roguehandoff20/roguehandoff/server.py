"""Dependency-free structured-tool HTTP service for one episode."""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import unquote

from .store import BenchmarkStore


def make_handler(store: BenchmarkStore, evaluator_token: str) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "RogueHandoff/0.1"

        def _write(self, status: HTTPStatus, body: dict[str, Any] | list[Any]) -> None:
            encoded = json.dumps(body, sort_keys=True).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _is_evaluator(self) -> bool:
            return self.headers.get("X-Evaluator-Token") == evaluator_token

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                self._write(HTTPStatus.OK, {"ok": True})
            elif self.path == "/task":
                self._write(HTTPStatus.OK, store.task())
            elif self.path == "/score" and self._is_evaluator():
                self._write(HTTPStatus.OK, store.score())
            elif self.path == "/ledger" and self._is_evaluator():
                self._write(HTTPStatus.OK, store.ledger())
            elif self.path == "/snapshot" and self._is_evaluator():
                self._write(HTTPStatus.OK, store.snapshot())
            else:
                self._write(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if not self.path.startswith("/tools/"):
                self._write(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length)
                arguments = json.loads(raw) if raw else {}
                if not isinstance(arguments, dict):
                    raise ValueError("request body must be a JSON object")
                tool = unquote(self.path.removeprefix("/tools/"))
                result = store.call(tool, arguments, actor="b")
                self._write(HTTPStatus.OK, result)
            except KeyError as exc:
                self._write(HTTPStatus.NOT_FOUND, {"error": str(exc)})
            except (ValueError, json.JSONDecodeError) as exc:
                self._write(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

        def log_message(self, format: str, *args: Any) -> None:
            if os.environ.get("ROGUEHANDOFF_HTTP_LOG") == "1":
                super().log_message(format, *args)

    return Handler


def serve(store: BenchmarkStore, host: str, port: int, evaluator_token: str) -> None:
    server = ThreadingHTTPServer((host, port), make_handler(store, evaluator_token))
    server.serve_forever()

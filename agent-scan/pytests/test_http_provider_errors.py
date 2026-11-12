import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from agent_scan.core.agent_adapter.adapter import AIProviderClient, ProviderConfig, ProviderOptions


@pytest.mark.parametrize(
    ("status", "payload", "expected_message"),
    [
        (400, {"error": {"message": "unknown model"}}, "unknown model"),
        (400, {"error": "unknown model"}, "unknown model"),
        (400, {"error": None, "message": "invalid request"}, "invalid request"),
        (400, {"message": "invalid request"}, "invalid request"),
        (200, {"content": "hello"}, "Connection successful"),
    ],
)
def test_http_provider_preserves_response_details(status, payload, expected_message):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Request-Id", "local-response-id")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            provider = ProviderOptions(
                id="http",
                config=ProviderConfig(url=f"http://127.0.0.1:{server.server_port}"),
            )
            result = AIProviderClient(timeout=2).call_provider(provider, prompt="hello")
        finally:
            server.shutdown()
            worker.join()

    assert result.success is (status == 200)
    assert expected_message in result.message
    assert result.provider_response.raw == payload
    assert result.provider_response.metadata["status_code"] == status
    assert result.provider_response.headers["x-request-id"] == "local-response-id"

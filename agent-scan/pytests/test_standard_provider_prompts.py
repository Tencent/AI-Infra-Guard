import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from agent_scan.core.agent_adapter.adapter import AIProviderClient, ProviderConfig, ProviderOptions


@pytest.mark.parametrize(
    "prompt",
    [
        "hello",
        'Say "hello"',
        "你好",
        "line1\nline2",
        "column1\tcolumn2",
        r"C:\new\temp",
        r"C:\Users\Alice",
    ],
)
def test_standard_provider_preserves_prompt_in_http_request(prompt):
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            received.append(request)
            body = json.dumps(
                {"choices": [{"message": {"content": request["messages"][0]["content"]}}]}
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            provider = ProviderOptions(
                id="openai:gpt-4o",
                config=ProviderConfig(
                    apiKey="local-placeholder",
                    apiBaseUrl=f"http://127.0.0.1:{server.server_port}",
                ),
            )
            result = AIProviderClient(timeout=2).call_provider(provider, prompt=prompt)
        finally:
            server.shutdown()
            worker.join()

    assert result.success is True
    assert len(received) == 1
    assert received[0]["messages"][0]["content"] == prompt
    assert received[0]["model"] == "gpt-4o"
    assert result.provider_response.output == prompt

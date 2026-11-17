"""Custom HTTP targets must receive the rendered JSON request array."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from agent_scan.core.agent_adapter.adapter import AIProviderClient, ProviderConfig, ProviderOptions


@pytest.mark.parametrize(
    "template,expected",
    [
        (
            '[{"role":"user","content":"{{prompt}}"}]',
            [{"role": "user", "content": '中文 "quoted"\nnext'}],
        ),
        ("[]", []),
        (
            '[{"input":"{{prompt}}","options":[1,true,null]},"tail"]',
            [{"input": '中文 "quoted"\nnext', "options": [1, True, None]}, "tail"],
        ),
        ({"message": "{{prompt}}"}, {"message": '中文 "quoted"\nnext'}),
        ('{"message":"{{prompt}}"}', {"message": '中文 "quoted"\nnext'}),
        ("literal-body", "literal-body"),
    ],
)
def test_custom_http_provider_sends_rendered_body(template, expected):
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            received.append(body)
            response = b'{"content":"ready"}'
            self.send_response(200 if body else 400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        def log_message(self, *_):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            provider = ProviderOptions(
                id="http",
                config=ProviderConfig(
                    url=f"http://127.0.0.1:{server.server_port}",
                    body=template,
                ),
            )
            result = AIProviderClient(timeout=2).call_provider(
                provider, prompt='中文 "quoted"\nnext'
            )
        finally:
            server.shutdown()
            worker.join()
    assert received and received[0], "the configured JSON array was dropped"
    if isinstance(expected, str):
        assert received[0].decode() == expected
    else:
        assert json.loads(received[0]) == expected
    assert result.success
    assert result.provider_response.output == "ready"

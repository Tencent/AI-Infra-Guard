"""Provider configuration exports must preserve top-level metadata on reload."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import yaml

from agent_scan.core.agent_adapter import adapter
from agent_scan.core.agent_adapter.adapter import AIProviderClient, ProviderConfig, ProviderOptions


@pytest.mark.parametrize("format_name", ["json", "yaml", "targets"])
def test_exported_provider_metadata_round_trips(tmp_path, format_name):
    client = AIProviderClient()
    original = ProviderOptions(
        id="http",
        label="Local agent",
        delay=25,
        config=ProviderConfig(url="http://127.0.0.1:12345"),
    )
    data = original.model_dump(exclude_none=True)
    if format_name == "json":
        text = client.export_target_json(data)
    else:
        text = client.export_target_yaml(data, include_redteam=format_name == "targets")
    path = tmp_path / ("provider.json" if format_name == "json" else "provider.yaml")
    path.write_text(text, encoding="utf-8")
    (restored,) = client.load_config_from_file(str(path))
    assert restored == original


def test_loaded_delay_is_applied_after_a_real_http_call(tmp_path, monkeypatch):
    requests = []
    waits = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            body = b'{"content":"ready"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    client = AIProviderClient(timeout=2)
    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            original = ProviderOptions(
                id="http",
                label="Local agent",
                delay=25,
                config=ProviderConfig(url=f"http://127.0.0.1:{server.server_port}"),
            )
            path = tmp_path / "provider.json"
            path.write_text(client.export_target_json(original.model_dump()), encoding="utf-8")
            (restored,) = client.load_config_from_file(str(path))
            # Observe the timer boundary without adding wall-clock assertions.
            monkeypatch.setattr(adapter.time, "sleep", waits.append)
            result = client.call_provider(restored, prompt="hello")
        finally:
            server.shutdown()
            worker.join()
    assert result.success
    assert result.provider_response.output == "ready"
    assert requests
    assert waits == [0.025]


@pytest.mark.parametrize(
    "entry,expected_label,expected_delay",
    [
        (
            {"id": "http", "label": "", "delay": 0, "config": {"label": "legacy", "delay": 99}},
            "",
            0,
        ),
        ({"id": "http", "config": {"label": "legacy", "delay": 99}}, "legacy", 99),
        ({"http": {"label": "mapped", "delay": 25, "config": {}}}, "mapped", 25),
        ("http", None, None),
    ],
)
def test_metadata_precedence_and_existing_config_forms(
    tmp_path, entry, expected_label, expected_delay
):
    path = tmp_path / "provider.yaml"
    path.write_text(yaml.safe_dump({"providers": [entry]}), encoding="utf-8")
    (restored,) = AIProviderClient().load_config_from_file(str(path))
    assert restored.id == "http"
    assert restored.label == expected_label
    assert restored.delay == expected_delay

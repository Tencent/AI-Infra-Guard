# Copyright (c) 2024-2026 Tencent Zhuque Lab. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Requirement: Any integration or derivative work must explicitly attribute
# Tencent Zhuque Lab (https://github.com/Tencent/AI-Infra-Guard) in its
# documentation or user interface, as detailed in the NOTICE file.

import json
import sys
import threading
from pathlib import Path

import pytest
from websockets.sync.server import serve

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.agent_adapter.adapter import AIProviderClient, ProviderConfig, ProviderOptions


@pytest.fixture
def websocket_url():
    def handler(websocket):
        message = websocket.recv(timeout=2)
        data = json.loads(message)
        websocket.send(json.dumps({"answer": f"echo: {data['message']}"}, ensure_ascii=False))

    server = serve(handler, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    host, port = server.socket.getsockname()
    try:
        yield f"ws://{host}:{port}/chat"
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_http_config_routes_ws_url_to_websocket_provider(websocket_url):
    client = AIProviderClient(timeout=2)
    provider = ProviderOptions(
        id="http",
        config=ProviderConfig(
            url=websocket_url,
            body={"message": "{{prompt}}"},
            transform_response="answer",
            timeout_ms=2000,
        ),
    )

    result = client.call_provider(provider, "hello ws")

    assert result.success is True
    assert result.provider_response.output == "echo: hello ws"
    assert result.provider_response.metadata["transport"] == "websocket"


def test_explicit_websocket_provider_requires_ws_scheme():
    client = AIProviderClient(timeout=2)
    provider = ProviderOptions(
        id="websocket",
        config=ProviderConfig(url="https://example.com/chat"),
    )

    result = client.call_provider(provider, "hello")

    assert result.success is False
    assert "must start with ws:// or wss://" in result.message


def test_done_inside_output_does_not_stop_websocket_stream():
    client = AIProviderClient(timeout=2)

    assert client._is_ws_done_message({"answer": "done with the first step"}) is False
    assert client._is_ws_done_message("done with the first step") is False


def test_terminal_signal_fields_stop_websocket_stream():
    client = AIProviderClient(timeout=2)

    assert client._is_ws_done_message("[DONE]") is True
    assert client._is_ws_done_message({"event": "done"}) is True
    assert client._is_ws_done_message({"event": "conversation.chat.completed"}) is True
    assert client._is_ws_done_message({"event": "conversation.chat.failed"}) is True
    assert client._is_ws_done_message({"event": "workflow_finished"}) is True
    assert client._is_ws_done_message({"event": "workflow_failed"}) is True
    assert client._is_ws_done_message({"type": "message_end"}) is True
    assert client._is_ws_done_message({"type": "message_stop"}) is True
    assert client._is_ws_done_message({"type": "response.done"}) is True
    assert client._is_ws_done_message({"status": "completed"}) is True
    assert client._is_ws_done_message({"status": "failed"}) is True
    assert client._is_ws_done_message({"serverContent": {"turnComplete": True}}) is True
    assert client._is_ws_done_message({"server_content": {"generation_complete": True}}) is True

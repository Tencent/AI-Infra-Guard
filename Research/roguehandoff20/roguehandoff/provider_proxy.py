"""Credential-hiding provider relay for network-isolated episodes.

The scored agent can connect to this relay through a bind-mounted Unix socket,
but it never receives the upstream URL or credential.  The episode container
has no network interface other than loopback.
"""

from __future__ import annotations

import http.client
import http.server
import json
import os
import shlex
import socketserver
import ssl
import subprocess
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
from urllib.parse import urlsplit


@dataclass(frozen=True)
class ProviderRelayConfig:
    provider: str
    api: str
    upstream_base_url: str
    upstream_api_key: str
    public_provider_config: dict


def _resolve_api_key(value: str) -> str:
    if value.startswith("!"):
        command = value[1:]
        if not command.strip():
            raise ValueError("provider apiKey command is empty")
        completed = subprocess.run(
            command,
            shell=True,
            executable="/bin/sh",
            check=True,
            text=True,
            capture_output=True,
        )
        value = completed.stdout.strip()
    if not value:
        raise ValueError("provider apiKey resolved to an empty value")
    return value


def load_provider_relay_config(
    pi_config_dir: Path,
    provider: str,
    model: str,
    local_port: int = 9000,
) -> ProviderRelayConfig:
    """Resolve one host provider and create a secret-free Pi configuration."""
    source_path = pi_config_dir / "models.json"
    source = json.loads(source_path.read_text())
    providers = source.get("providers", {})
    if provider not in providers:
        raise ValueError(f"provider {provider!r} is not configured in {source_path}")
    upstream = providers[provider]
    models = [item for item in upstream.get("models", []) if item.get("id") == model]
    if len(models) != 1:
        raise ValueError(
            f"model {model!r} is not configured exactly once for provider {provider!r}"
        )
    base_url = upstream.get("baseUrl")
    api = upstream.get("api")
    api_key = upstream.get("apiKey")
    if not isinstance(base_url, str) or not isinstance(api, str):
        raise ValueError(f"provider {provider!r} lacks api/baseUrl")
    if not isinstance(api_key, str):
        raise ValueError(f"provider {provider!r} lacks a string apiKey")
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"unsupported provider baseUrl for {provider!r}")

    public = {
        key: value
        for key, value in upstream.items()
        if key not in {"apiKey", "baseUrl", "models"}
    }
    public.update({
        "apiKey": "episode-relay-placeholder",
        "baseUrl": f"http://127.0.0.1:{local_port}{parsed.path.rstrip('/')}",
        "models": models,
    })
    return ProviderRelayConfig(
        provider=provider,
        api=api,
        upstream_base_url=base_url,
        upstream_api_key=_resolve_api_key(api_key),
        public_provider_config=public,
    )


class _ThreadingUnixHTTPServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


def _handler(config: ProviderRelayConfig) -> type[http.server.BaseHTTPRequestHandler]:
    upstream = urlsplit(config.upstream_base_url)
    origin_path = upstream.path.rstrip("/")

    class RelayHandler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _relay(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length else None
            request_path = self.path
            if origin_path and not request_path.startswith(origin_path + "/"):
                request_path = origin_path + (request_path if request_path.startswith("/") else "/" + request_path)
            headers = {
                key: value
                for key, value in self.headers.items()
                if key.lower() not in {
                    "authorization", "connection", "content-length", "host",
                    "proxy-authorization", "transfer-encoding", "x-api-key",
                }
            }
            if config.api == "anthropic-messages":
                headers["x-api-key"] = config.upstream_api_key
            else:
                headers["Authorization"] = f"Bearer {config.upstream_api_key}"
            if body is not None:
                headers["Content-Length"] = str(len(body))

            connection_class = (
                http.client.HTTPSConnection
                if upstream.scheme == "https" else http.client.HTTPConnection
            )
            kwargs = {"timeout": 300}
            if upstream.scheme == "https":
                kwargs["context"] = ssl.create_default_context()
            connection = connection_class(upstream.hostname, upstream.port, **kwargs)
            try:
                connection.request(self.command, request_path, body=body, headers=headers)
                response = connection.getresponse()
                self.send_response(response.status, response.reason)
                for key, value in response.getheaders():
                    if key.lower() not in {
                        "connection", "content-length", "keep-alive",
                        "proxy-authenticate", "transfer-encoding", "upgrade",
                    }:
                        self.send_header(key, value)
                self.send_header("Connection", "close")
                self.end_headers()
                while True:
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except Exception as exc:  # pragma: no cover - exercised by live providers
                if not self.wfile.closed:
                    try:
                        self.send_error(502, f"provider relay error: {type(exc).__name__}")
                    except OSError:
                        pass
            finally:
                connection.close()
                self.close_connection = True

        do_DELETE = _relay
        do_GET = _relay
        do_PATCH = _relay
        do_POST = _relay
        do_PUT = _relay

        def log_message(self, format: str, *args: object) -> None:
            return

    return RelayHandler


@contextmanager
def provider_relay(
    socket_path: Path,
    config: ProviderRelayConfig,
) -> Iterator[Path]:
    """Serve the selected provider on a Unix socket for one episode."""
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    socket_path.parent.chmod(0o755)
    if socket_path.exists():
        socket_path.unlink()
    server = _ThreadingUnixHTTPServer(str(socket_path), _handler(config))
    os.chmod(socket_path, 0o666)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield socket_path
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        socket_path.unlink(missing_ok=True)

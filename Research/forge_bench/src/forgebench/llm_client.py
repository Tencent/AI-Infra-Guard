from __future__ import print_function

import json
import os
import urllib.error
import urllib.request


class LLMConfigurationError(ValueError):
    pass


class LLMRequestError(RuntimeError):
    pass


def _chat_completions_url(base_url):
    value = (base_url or "").rstrip("/")
    if not value:
        raise LLMConfigurationError("llm.base_url is required")
    if value.endswith("/chat/completions"):
        return value
    if value.endswith("/v1"):
        return value + "/chat/completions"
    return value + "/chat/completions"


def _read_api_key(llm):
    environment_name = llm.get("api_key_env", "LLM_API_KEY")
    api_key = os.environ.get(environment_name)
    if not api_key:
        raise LLMConfigurationError(
            "environment variable %s is not set" % environment_name
        )
    return api_key


def _request_payload(prompt, model, llm):
    messages = []
    system_prompt = llm.get("system_prompt")
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    for key in (
        "temperature",
        "top_p",
        "max_tokens",
        "max_completion_tokens",
        "reasoning_effort",
        "seed",
    ):
        if key in llm:
            payload[key] = llm[key]
    extra_body = llm.get("extra_body")
    if extra_body:
        if not isinstance(extra_body, dict):
            raise LLMConfigurationError("llm.extra_body must be an object")
        payload.update(extra_body)
    return payload


def _extract_content(response):
    try:
        message = response["choices"][0]["message"]
        content = message.get("content")
    except (KeyError, IndexError, TypeError):
        raise LLMRequestError("LLM response does not contain choices[0].message")
    if content is None:
        raise LLMRequestError("LLM response message has no content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("text") is not None:
                parts.append(str(item["text"]))
        if parts:
            return "".join(parts)
    raise LLMRequestError("LLM response content is not text")


def invoke_openai_compatible(prompt, model, llm):
    url = _chat_completions_url(llm.get("base_url"))
    api_key = _read_api_key(llm)
    payload = _request_payload(prompt, model, llm)
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "FORGE-Bench/1.0",
    }
    headers.update(llm.get("headers") or {})
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    timeout = float(llm.get("timeout_seconds", 120))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:1000]
        raise LLMRequestError("LLM HTTP %s: %s" % (exc.code, detail))
    except urllib.error.URLError as exc:
        raise LLMRequestError("LLM request failed: %s" % exc.reason)
    try:
        parsed = json.loads(raw)
    except ValueError:
        raise LLMRequestError("LLM endpoint returned invalid JSON")
    return _extract_content(parsed)


def invoke_model(prompt, config):
    model = config.get("model")
    if not model:
        raise LLMConfigurationError("model is required")
    llm = config.get("llm") or {}
    provider = llm.get("provider", "legacy")
    if provider == "openai_compatible":
        return invoke_openai_compatible(prompt, model, llm)
    if provider == "legacy":
        # Backward compatibility for existing private deployments.
        import sys
        workspace = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
        )
        if workspace not in sys.path:
            sys.path.insert(0, workspace)
        from client.llm_client import LLMClient
        return LLMClient(model=model).ask(prompt)
    raise LLMConfigurationError("unsupported llm.provider: %s" % provider)

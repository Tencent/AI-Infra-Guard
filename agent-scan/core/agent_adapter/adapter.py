"""
API client module - Re-exports from SDK for backward compatibility.

For new code, prefer using agent_ui.sdk directly:
    from agent_ui.sdk import AIProviderClient, ProviderTestResult
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import httpx
import yaml
from pydantic import BaseModel, Field, Json


class ProviderConfig(BaseModel):
    """
    Configuration for a provider.
    
    This class contains all configuration options that can be passed to a provider,
    including HTTP settings, authentication, model parameters, and provider-specific options.
    """
    # HTTP/WebSocket config
    url: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    headers: Optional[Union[Json[Dict], Dict]] = None
    body: Optional[Union[Json[Dict], Dict, str]] = None

    # Common specific
    type: Optional[str] = None
    message_template: Optional[str] = None
    transform_response: Optional[str] = None
    timeout_ms: Optional[int] = None

    # General config
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

    # API authentication and endpoint (camelCase for compatibility)
    apiKey: Optional[str] = None
    apiBaseUrl: Optional[str] = None

    # Extra fields for flexibility
    extra: Optional[Union[Json[Dict], Dict]] = None


class ProviderOptions(BaseModel):
    """
    Provider options for configuration.
    
    This is the main configuration object passed to AIProviderClient methods.
    
    Attributes:
        id: Provider identifier (e.g., "openai:gpt-4", "anthropic:claude-3-opus")
        label: Optional display label for UI
        config: Provider-specific configuration
        delay: Delay in milliseconds between API calls
    
    Example:
        >>> options = ProviderOptions(
        ...     id="openai:gpt-4",
        ...     config=ProviderConfig(
        ...         apiKey="sk-...",
        ...         temperature=0.7
        ...     )
        ... )
    """
    id: str
    label: Optional[str] = None
    config: ProviderConfig = Field(default_factory=ProviderConfig)
    delay: Optional[int] = None


# ============================================================
# Response Models
# ============================================================

class ProviderResponseInfo(BaseModel):
    """Provider response information from API calls."""
    raw: Optional[Any] = None
    output: Optional[str] = None
    error: Optional[str] = None
    session_id: Optional[str] = Field(None, alias="sessionId")
    headers: Optional[Dict[str, str]] = None
    token_usage: Optional[Dict[str, Any]] = Field(None, alias="tokenUsage")
    cost: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class ProviderTestResult(BaseModel):
    """Result from testing/calling a provider."""
    success: bool
    message: Optional[str] = None
    suggestions: Optional[List[str]] = None
    cached: bool = False
    provider_response: Optional[ProviderResponseInfo] = None


# ============================================================
# Provider Configuration Loader
# ============================================================

class ProviderConfigLoader:
    """Load provider configurations from YAML files."""

    _instance = None
    _config: Dict[str, Any] = {}
    _pricing: Dict[str, Dict[str, float]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """Load provider configuration from YAML file."""
        config_path = Path(__file__).parent / "providers.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                self._config = data.get("providers", {})
                self._pricing = data.get("pricing", {})

    def get_provider_config(self, provider_type: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific provider type."""
        # Search in all API format groups
        for format_name, format_config in self._config.items():
            providers = format_config.get("providers", {})
            if provider_type in providers:
                provider_conf = providers[provider_type].copy()
                # Merge format-level settings
                provider_conf["api_format"] = format_config.get("api_format", "custom")
                provider_conf["request_body_template"] = format_config.get("request_body_template")
                provider_conf["response_path"] = format_config.get("response_path")
                provider_conf["auth_type"] = format_config.get("auth_type", provider_conf.get("auth_type", "bearer"))
                provider_conf["auth_param_name"] = format_config.get("auth_param_name")
                if "extra_headers" in format_config:
                    provider_conf.setdefault("extra_headers", {}).update(format_config["extra_headers"])
                return provider_conf
        return None

    def get_pricing(self, model: str) -> Optional[Dict[str, float]]:
        """Get pricing for a model."""
        model_lower = model.lower()
        for model_key, prices in self._pricing.items():
            if model_key in model_lower:
                return prices
        return None

    def get_all_providers(self) -> List[str]:
        """Get list of all configured provider types."""
        providers = []
        for format_config in self._config.values():
            providers.extend(format_config.get("providers", {}).keys())
        return providers


# ============================================================
# AI Provider Client
# ============================================================

class AIProviderClient:
    """
    API client for testing and invoking various AI provider types.
    
    This client can be used as a standalone SDK without the Web UI.
    
    Supports:
    - HTTP endpoints
    - WebSocket endpoints
    - OpenAI and OpenAI-compatible APIs
    - Anthropic Claude
    - Google AI Studio / Vertex AI
    - Azure OpenAI
    - Mistral AI, Groq, Ollama
    - AWS Bedrock
    - Cohere, Deepseek, Perplexity
    - OpenRouter, Together AI, Fireworks
    - Custom script providers
    
    Usage:
        client = AIProviderClient()
        
        # Test connection
        result = client.test_provider(provider)
        
        # Call with custom prompt
        result = client.call_provider(provider, prompt="What is AI?")
    """

    DEFAULT_TIMEOUT = 30
    DEFAULT_TEST_PROMPT = "Hi!"

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        """
        Initialize the AI Provider client.
        
        Args:
            timeout: Default timeout in seconds for API calls
        """
        self.timeout = timeout
        self._config_loader = ProviderConfigLoader()

    def call_provider(self, provider: ProviderOptions, prompt: Optional[str] = None) -> ProviderTestResult:
        """
        Call a provider with the given prompt.
        
        Args:
            provider: Provider configuration
            prompt: Optional prompt to send. If None, uses default test prompt.
            
        Returns:
            ProviderTestResult with the response
        """
        actual_prompt = prompt if prompt is not None else self.DEFAULT_TEST_PROMPT
        provider_id = (provider.id or "").lower()

        # Execute the call
        result = self._route_call(provider, provider_id, actual_prompt)

        # Apply delay if configured
        if not result.cached and provider.delay and provider.delay > 0:
            time.sleep(provider.delay / 1000.0)

        return result

    def test_provider(self, provider: ProviderOptions) -> ProviderTestResult:
        """Test a provider configuration."""
        return self.call_provider(provider, prompt=None)

    def _route_call(self, provider: ProviderOptions, provider_id: str, prompt: str) -> ProviderTestResult:
        """Route to the correct provider handler."""
        config = provider.config

        # HTTP endpoint
        if provider_id.startswith("http") or (config and config.url and not provider_id):
            return self._call_http_provider(provider, prompt)

        # Dify (special handling)
        if provider_id.startswith("dify"):
            return self._call_dify_provider(provider, prompt)

        # Coze (special handling)
        if provider_id.startswith("coze"):
            return self._call_coze_provider(provider, prompt)

        # Standard API providers - use unified handler
        provider_type = self._extract_provider_type(provider_id)
        provider_conf = self._config_loader.get_provider_config(provider_type)

        if provider_conf:
            return self._call_standard_provider(provider, prompt, provider_type, provider_conf)

        # Fallback to local validation
        return self._validate_local(provider)

    def _extract_provider_type(self, provider_id: str) -> str:
        """Extract provider type from provider ID."""
        if ":" in provider_id:
            return provider_id.split(":")[0]
        return provider_id

    def _extract_model(self, provider_id: str, prefix: str, default: str) -> str:
        """Extract model name from provider ID."""
        if ":" in provider_id:
            parts = provider_id.split(":", 1)
            if len(parts) > 1 and parts[1]:
                model = parts[1]
                # Handle special prefixes like messages:, chat:, completion:
                for special in ["messages:", "chat:", "completion:"]:
                    if model.startswith(special):
                        model = model[len(special):]
                return model
        return default

    # ==================== Standard Provider Handler ====================

    def _call_standard_provider(
            self,
            provider: ProviderOptions,
            prompt: str,
            provider_type: str,
            provider_conf: Dict[str, Any]
    ) -> ProviderTestResult:
        """
        Unified handler for standard API providers.
        
        This method handles most providers using their configuration from providers.yaml.
        """
        config = provider.config

        # Get API key
        env_keys = provider_conf.get("env_keys", [])
        api_key = self._get_api_key(config, *env_keys) if env_keys else None

        auth_type = provider_conf.get("auth_type", "bearer")
        if auth_type not in ["none", "query_param"] and env_keys and not api_key:
            return ProviderTestResult(
                success=False,
                message=f"❌ {provider_type.title()} API key required. Set {env_keys[0]}."
            )

        # Get base URL
        base_url = (config.apiBaseUrl if config else None)
        if not base_url:
            base_url_env = provider_conf.get("base_url_env")
            if base_url_env:
                base_url = os.environ.get(base_url_env)
            if not base_url:
                base_url = provider_conf.get("base_url", "")
        base_url = base_url.rstrip("/")

        # Get model
        default_model = provider_conf.get("default_model", "")
        model = self._extract_model(provider.id, provider_type, default_model)

        # Build endpoint URL
        endpoint = provider_conf.get("endpoint", "")
        endpoint = endpoint.replace("{{model}}", model)
        url = f"{base_url}{endpoint}"

        # Handle query param auth (e.g., Google)
        if auth_type == "query_param":
            param_name = provider_conf.get("auth_param_name", "key")
            url = f"{url}?{param_name}={api_key}"

        # Build headers
        headers = {"Content-Type": "application/json"}
        if auth_type == "bearer" and api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        elif auth_type == "x-api-key" and api_key:
            headers["x-api-key"] = api_key
        elif auth_type == "token" and api_key:
            headers["Authorization"] = f"Token {api_key}"

        # Add extra headers
        extra_headers = provider_conf.get("extra_headers", {})
        headers.update(extra_headers)

        # Allow per-provider header overrides (useful for OpenRouter / enterprise gateways)
        if config and config.headers:
            headers.update(dict(config.headers))

        # Build request body
        body_template = provider_conf.get("request_body_template", {})
        body = self._render_body(body_template, model, prompt)

        # Apply common generation overrides from ProviderConfig (when the template doesn't include them)
        if config and isinstance(body, dict):
            if config.temperature is not None and "temperature" not in body:
                body["temperature"] = config.temperature
            if config.max_tokens is not None:
                # OpenAI/Anthropic/Cohere style
                body.setdefault("max_tokens", config.max_tokens)
                # Google style (best-effort)
                if isinstance(body.get("generationConfig"), dict):
                    body["generationConfig"].setdefault("maxOutputTokens", config.max_tokens)

        # Make request
        response_path = provider_conf.get("response_path")
        result = self._make_http_request(url, "POST", headers, body, response_path)

        # Add metadata and cost
        if result.success and result.provider_response:
            result.provider_response.metadata = result.provider_response.metadata or {}
            result.provider_response.metadata["model"] = model
            result.provider_response.metadata["provider"] = provider_type

            # Calculate cost
            pricing = self._config_loader.get_pricing(model)
            if pricing and result.provider_response.token_usage:
                result.provider_response.cost = self._calculate_cost(
                    pricing,
                    result.provider_response.token_usage
                )

        return result

    def _render_body(self, template: Dict[str, Any], model: str, prompt: str) -> Dict[str, Any]:
        """Render request body from template."""
        if not template:
            return {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 1000}

        body_str = json.dumps(template)
        body_str = body_str.replace("{{model}}", model)
        body_str = body_str.replace("{{prompt}}", prompt.replace('"', '\\"'))
        return json.loads(body_str)

    # ==================== HTTP Provider ====================

    def _call_http_provider(self, provider: ProviderOptions, prompt: str) -> ProviderTestResult:
        """Call a custom HTTP endpoint."""
        config = provider.config
        if not config or not config.url:
            return ProviderTestResult(
                success=False,
                message="❌ HTTP URL is required"
            )

        url = config.url
        if config.endpoint:
            url = f"{url}{config.endpoint}"
        method = (config.method or "POST").upper()
        headers = dict(config.headers) if config.headers else {}

        if "Content-Type" not in headers and "content-type" not in headers:
            headers["Content-Type"] = "application/json"

        # Build body with prompt placeholder
        body = None
        if config.body:
            body_str = json.dumps(config.body) if isinstance(config.body, dict) else str(config.body)
            body_str = body_str.replace("{{prompt}}", prompt).replace("{{ prompt }}", prompt)
            try:
                body = json.loads(body_str)
            except json.JSONDecodeError:
                body = body_str
        else:
            body = {"message": prompt}

        return self._make_http_request(url, method, headers, body, config.transform_response)

    def _call_dify_provider(self, provider: ProviderOptions, prompt: str) -> ProviderTestResult:
        """
        Call Dify AI platform.
        
        Supports both chat-messages and workflow endpoints.
        
        Provider ID formats:
        - dify: Chat messages endpoint
        - dify-workflow: Workflow run endpoint
        """
        config = provider.config
        provider_id = provider.id.lower()

        # Get API key
        api_key = self._get_api_key(config, "DIFY_API_KEY")
        if not api_key:
            return ProviderTestResult(
                success=False,
                message="❌ Dify API key required. Set DIFY_API_KEY environment variable.",
                suggestions=["Set DIFY_API_KEY environment variable", "Or provide apiKey in config"]
            )

        # Get base URL
        base_url = (config.apiBaseUrl if config else None)
        if not base_url:
            base_url = os.environ.get("DIFY_API_BASE", "https://api.dify.ai/v1")
        base_url = base_url.rstrip("/")

        # Determine endpoint
        if "workflow" in provider_id:
            endpoint = "/workflows/run"
            # Workflow uses 'inputs' for the prompt
            body = {
                "inputs": getattr(config, 'extra', {}).get('inputs', {}) if config else {},
                "response_mode": "streaming",
                "user": getattr(config, 'extra', {}).get('user', 'agent-user') if config else 'agent-user'
            }
            # Add prompt to inputs if not already specified
            if "query" not in body["inputs"]:
                body["inputs"]["query"] = prompt
        else:
            endpoint = "/chat-messages"
            body = {
                "inputs": getattr(config, 'extra', {}).get('inputs', {}) if config else {},
                "query": prompt,
                "response_mode": "streaming",
                "user": getattr(config, 'extra', {}).get('user', 'agent-user') if config else 'agent-user'
            }
            # Add conversation_id if provided
            conversation_id = getattr(config, 'extra', {}).get('conversation_id') if config else None
            if conversation_id:
                body["conversation_id"] = conversation_id

        url = f"{base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        result = self._make_http_request(url, "POST", headers, body, "answer")

        if result.success and result.provider_response:
            result.provider_response.metadata = result.provider_response.metadata or {}
            result.provider_response.metadata["provider"] = "dify"
            result.provider_response.metadata["endpoint"] = endpoint

            # Extract conversation_id from response for subsequent calls
            if isinstance(result.provider_response.raw, dict):
                conv_id = result.provider_response.raw.get("conversation_id")
                if conv_id:
                    result.provider_response.session_id = conv_id

        return result

    def _call_coze_provider(self, provider: ProviderOptions, prompt: str) -> ProviderTestResult:
        """
        Call Coze AI bot platform.
        
        Supports both China (api.coze.cn) and International (api.coze.com) endpoints.
        
        Provider ID formats:
        - coze:coze-cn: China endpoint
        - coze:coze-com: International endpoint
        """
        config = provider.config
        provider_id = provider.id.lower()

        # Get API key
        api_key = self._get_api_key(config, "COZE_API_KEY")
        if not api_key:
            return ProviderTestResult(
                success=False,
                message="❌ Coze API key required. Set COZE_API_KEY environment variable.",
                suggestions=["Set COZE_API_KEY environment variable", "Or provide apiKey in config"]
            )

        # Extract bot_id from config
        bot_id = getattr(config, 'extra', {}).get('bot_id') if config else None

        if not bot_id:
            return ProviderTestResult(
                success=False,
                message="❌ Coze bot_id required. Specify in config.extra.bot_id",
                suggestions=["Set bot_id in config extra"]
            )

        # Get base URL based on provider type
        base_url = (config.apiBaseUrl if config else None)
        if not base_url:
            base_url = os.environ.get("COZE_API_BASE")
        if not base_url:
            if "coze-com" in provider_id:
                base_url = "https://api.coze.com"
            else:
                base_url = "https://api.coze.cn"
        base_url = base_url.rstrip("/")

        # Build request body
        user_id = getattr(config, 'extra', {}).get('user_id', 'agent-user') if config else 'agent-user'

        body = {
            "bot_id": bot_id,
            "user_id": user_id,
            "stream": True,  # Use streaming for simplicity in test
            "auto_save_history": True,
            "additional_messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "content_type": "text"
                }
            ]
        }

        # Add conversation_id if provided
        conversation_id = getattr(config, 'extra', {}).get('conversation_id') if config else None

        url = f"{base_url}/v3/chat"
        if conversation_id:
            url = f"{url}?conversation_id={conversation_id}"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        result = self._make_http_request(url, "POST", headers, body)

        if result.success and result.provider_response:
            raw = result.provider_response.raw
            result.provider_response.metadata = result.provider_response.metadata or {}
            result.provider_response.metadata["provider"] = "coze"
            result.provider_response.metadata["bot_id"] = bot_id

            # Extract response from Coze format
            if isinstance(raw, dict):
                # Extract conversation_id
                data = raw.get("data", raw)
                conv_id = data.get("conversation_id")
                if conv_id:
                    result.provider_response.session_id = conv_id

                # Extract message content from messages array
                messages = data.get("messages", [])
                if messages:
                    # Find the assistant's answer message
                    for msg in messages:
                        if msg.get("role") == "assistant" and msg.get("type") == "answer":
                            result.provider_response.output = msg.get("content", "")
                            break
                    # Fallback to last message
                    if not result.provider_response.output and messages:
                        result.provider_response.output = messages[-1].get("content", "")

                # Check for errors in response
                if raw.get("code") and raw.get("code") != 0:
                    result.success = False
                    result.message = f"❌ Coze API error: {raw.get('msg', 'Unknown error')}"
                    result.provider_response.error = raw.get("msg")

        return result

        # ==================== Helper Methods ====================

    def _make_http_request(
            self,
            url: str,
            method: str,
            headers: Dict[str, str],
            body: Any,
            transform_response: Optional[str] = None
    ) -> ProviderTestResult:
        """Make HTTP request and return standardized result."""
        start_time = time.time()

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=body if isinstance(body, dict) else None,
                    content=body if isinstance(body, str) else None
                )

                elapsed = time.time() - start_time
                response_headers = dict(response.headers)
                status_code = response.status_code
                content_type = response_headers.get("content-type", "").lower()

                # Check if response is SSE format
                is_sse = "text/event-stream" in content_type

                if is_sse:
                    # Parse SSE response
                    raw_response, token_usage = self._parse_sse_response(response.text)
                else:
                    try:
                        raw_response = response.json()
                    except:
                        raw_response = response.text
                    token_usage = raw_response.get("usage") if isinstance(raw_response, dict) else None

                output = self._extract_output(raw_response, transform_response)

                provider_response = ProviderResponseInfo(
                    raw=raw_response,
                    output=output,
                    headers=response_headers,
                    token_usage=token_usage,
                    metadata={
                        "status_code": status_code,
                        "elapsed_time": f"{elapsed:.2f}s",
                        "url": url,
                        "method": method,
                        "is_sse": is_sse
                    }
                )

                if 200 <= status_code < 300:
                    return ProviderTestResult(
                        success=True,
                        message=f"✅ Connection successful! Status: {status_code}, Time: {elapsed:.2f}s",
                        provider_response=provider_response
                    )
                else:
                    error_msg = ""
                    if isinstance(raw_response, dict):
                        error_msg = raw_response.get("error", {}).get("message", "") or str(raw_response.get("error", "")) or raw_response.get("message", "")
                    return ProviderTestResult(
                        success=False,
                        message=f"❌ Request failed with status {status_code}: {error_msg or 'Unknown error'}",
                        provider_response=provider_response
                    )


        except httpx.TimeoutException:
            return ProviderTestResult(
                success=False,
                message=f"⏱️ Request timed out after {self.timeout} seconds",
                provider_response=ProviderResponseInfo(error="Timeout", metadata={"url": url})
            )
        except httpx.ConnectError as e:
            return ProviderTestResult(
                success=False,
                message=f"🔌 Connection refused: Cannot connect to {url}",
                provider_response=ProviderResponseInfo(error=str(e), metadata={"url": url})
            )
        except Exception as e:
            return ProviderTestResult(
                success=False,
                message=f"❌ Error: {str(e)}",
                provider_response=ProviderResponseInfo(error=str(e), metadata={"url": url})
            )

    def _parse_sse_response(self, sse_text: str) -> tuple:
        """
        Parse SSE (Server-Sent Events) format response.
        
        SSE format example:
            data: {"choices": [{"delta": {"content": "Hello"}}]}
            
            data: {"choices": [{"delta": {"content": " World"}}]}
            
            data: [DONE]
        
        Args:
            sse_text: Raw SSE response text
            
        Returns:
            Tuple of (parsed_response_dict, token_usage_dict)
        """
        content_parts = []
        token_usage = None
        last_data = None
        role = None

        for line in sse_text.split("\n"):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith(":"):
                continue

            # Parse data lines
            if line.startswith("data:"):
                data_str = line[5:].strip()

                # Skip [DONE] marker
                if data_str == "[DONE]":
                    continue

                try:
                    data = json.loads(data_str)
                    last_data = data

                    # Extract content from OpenAI-style streaming response
                    if "choices" in data:
                        choices = data.get("choices", [])
                        if choices:
                            choice = choices[0]
                            delta = choice.get("delta", {})

                            # Get role from first chunk
                            if "role" in delta and not role:
                                role = delta["role"]

                            # Accumulate content
                            if "content" in delta:
                                content_parts.append(delta["content"])

                    # Extract content from Anthropic-style streaming response
                    elif "type" in data:
                        event_type = data.get("type", "")

                        if event_type == "content_block_delta":
                            delta = data.get("delta", {})
                            if "text" in delta:
                                content_parts.append(delta["text"])

                        elif event_type == "message_delta":
                            # Token usage often comes in message_delta
                            usage = data.get("usage", {})
                            if usage:
                                token_usage = usage
                        
                        # Extract content from coze streaming response
                        elif event_type == "answer":
                            text = data.get("content")
                            if text:
                                content_parts.append(text)

                    # Extract content from dify streaming response
                    elif "answer" in data:
                        content_parts.append(data.get("answer", ""))

                    # Extract token usage if present
                    if "usage" in data and data["usage"]:
                        token_usage = data["usage"]

                except json.JSONDecodeError:
                    # If not valid JSON, treat as plain text content
                    if data_str:
                        content_parts.append(data_str)

        # Build final response structure
        full_content = "".join(content_parts)

        # Try to construct a normalized response
        if last_data and "choices" in last_data:
            # OpenAI-style response
            response = {
                "choices": [{
                    "message": {
                        "role": role or "assistant",
                        "content": full_content
                    },
                    "finish_reason": last_data.get("choices", [{}])[0].get("finish_reason")
                }],
                "model": last_data.get("model"),
                "id": last_data.get("id")
            }
            if token_usage:
                response["usage"] = token_usage
        elif last_data and "type" in last_data:
            # Anthropic-style response
            response = {
                "content": [{"type": "text", "text": full_content}],
                "role": "assistant",
                "model": last_data.get("model"),
                "id": last_data.get("id")
            }
            if token_usage:
                response["usage"] = token_usage
        else:
            # Generic response
            response = {
                "content": full_content,
                "raw_sse": True
            }
            if token_usage:
                response["usage"] = token_usage

        return response, token_usage

    def _get_api_key(self, config, *env_vars) -> Optional[str]:
        """Get API key from config or environment."""

        if config and config.apiKey:
            return config.apiKey
        for env_var in env_vars:
            key = os.environ.get(env_var)
            if key:
                return key
        return None

    def _extract_output(self, raw_response: Any, transform: Optional[str] = None) -> Optional[str]:
        """Extract output from response using transform path or default logic."""
        # Try custom transform first
        if transform:
            result = self._apply_transform(raw_response, transform)
            if result is not None:
                return result

        # Default extraction logic
        if not isinstance(raw_response, dict):
            return str(raw_response) if raw_response else None

        # OpenAI format
        if "choices" in raw_response:
            choices = raw_response.get("choices", [])
            if choices:
                choice = choices[0]
                if "message" in choice:
                    return choice["message"].get("content")
                if "text" in choice:
                    return choice["text"]

        # Anthropic format
        if "content" in raw_response:
            content = raw_response["content"]
            if isinstance(content, list) and content:
                return content[0].get("text", str(content[0]))
            return str(content)

        # Google format
        if "candidates" in raw_response:
            candidates = raw_response.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    return parts[0].get("text", str(parts[0]))

        # Ollama/Cohere format
        if "message" in raw_response:
            message = raw_response["message"]
            if isinstance(message, dict):
                return message.get("content")
            return str(message)

        if "text" in raw_response:
            return str(raw_response["text"])

        # Generic fields
        for field in ["response", "result", "output", "data", "generated_text"]:
            if field in raw_response:
                value = raw_response[field]
                if isinstance(value, str):
                    return value
                elif isinstance(value, dict):
                    return json.dumps(value, ensure_ascii=False)
                elif isinstance(value, list) and value:
                    if isinstance(value[0], dict):
                        return value[0].get("generated_text", str(value[0]))
                    return str(value)

        return None

    def _apply_transform(self, raw_response: Any, expression: str) -> Optional[str]:
        """Apply transform expression to extract data from response."""
        import re

        expression = expression.strip()

        # Remove common prefixes
        for prefix in ["response.", "json.", "data."]:
            if expression.lower().startswith(prefix):
                expression = expression[len(prefix):]
                break

        if expression.lower() in ["", "response", "json", "data"]:
            if isinstance(raw_response, str):
                return raw_response
            return json.dumps(raw_response, ensure_ascii=False) if raw_response else None

        try:
            current = raw_response
            tokens = re.findall(r'\[\d+\]|[^.\[\]]+', expression)

            for token in tokens:
                if current is None:
                    return None

                if token.startswith('[') and token.endswith(']'):
                    index = int(token[1:-1])
                    if isinstance(current, list) and len(current) > index:
                        current = current[index]
                    else:
                        return None
                elif isinstance(current, dict):
                    current = current.get(token)
                else:
                    return None

            if current is None:
                return None
            elif isinstance(current, str):
                return current
            elif isinstance(current, (dict, list)):
                return json.dumps(current, ensure_ascii=False)
            else:
                return str(current)

        except:
            return None

    def _calculate_cost(self, pricing: Dict[str, float], token_usage: Dict[str, Any]) -> Optional[float]:
        """Calculate API cost from pricing and token usage."""
        prompt_tokens = token_usage.get("prompt_tokens", 0) or token_usage.get("input_tokens", 0)
        completion_tokens = token_usage.get("completion_tokens", 0) or token_usage.get("output_tokens", 0)
        cost = (prompt_tokens / 1000 * pricing["input"]) + (completion_tokens / 1000 * pricing["output"])
        return round(cost, 6)

    def _validate_local(self, provider: ProviderOptions) -> ProviderTestResult:
        """Perform local validation without API calls."""
        errors = []
        suggestions = []

        if not provider.id:
            errors.append("Provider ID is required")

        provider_id = (provider.id or "").lower()
        config = provider.config

        if provider_id.startswith("http"):
            if config:
                if not config.url:
                    errors.append("HTTP URL is required")
                elif not config.url.startswith(("http://", "https://")):
                    errors.append("HTTP URL must start with http:// or https://")
            else:
                errors.append("HTTP provider requires config with URL")

        elif provider_id.startswith("websocket"):
            if config:
                if not config.url:
                    errors.append("WebSocket URL is required")
                elif not config.url.startswith(("ws://", "wss://")):
                    errors.append("WebSocket URL must start with ws:// or wss://")
            else:
                errors.append("WebSocket provider requires config with URL")

        if errors:
            return ProviderTestResult(
                success=False,
                message="❌ Configuration validation failed:\n• " + "\n• ".join(errors),
                suggestions=suggestions if suggestions else None
            )

        return ProviderTestResult(
            success=True,
            message=f"✅ Configuration valid for: {provider.id}",
            provider_response=ProviderResponseInfo(
                output=f"Local validation passed for: {provider.id}",
                metadata={"provider_id": provider.id, "validation": "local"}
            )
        )

    # ==================== Configuration File I/O Methods ====================

    def load_config_from_file(self, config_file: str) -> List[ProviderOptions]:
        """
        Load provider configuration from YAML or JSON file.
        
        Args:
            config_file: Path to YAML or JSON configuration file
            
        Returns:
            List of ProviderOptions loaded from file
            
        Example:
            client = AIProviderClient()
            providers = client.load_config_from_file("config.yaml")
            result = client.test_provider(providers[0])
        """
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file not found: {config_file}")

        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse based on file extension
        if config_file.endswith('.json'):
            config_data = json.loads(content)
        else:
            config_data = yaml.safe_load(content)

        # Extract providers or targets
        if isinstance(config_data, dict):
            providers_data = config_data.get('providers') or config_data.get('targets')
        elif isinstance(config_data, list):
            providers_data = config_data
        else:
            raise ValueError("Configuration file parsing failed")

        if not providers_data:
            raise ValueError("No 'providers' or 'targets' found in configuration file")

        providers = []
        for provider_data in providers_data:
            if isinstance(provider_data, str):
                # Simple string format: "openai:gpt-4"
                providers.append(ProviderOptions(id=provider_data))
            elif isinstance(provider_data, dict):
                # Check if it's a map format like {"openai:gpt-4": {...config...}}
                if len(provider_data) == 1 and "id" not in provider_data:
                    provider_id = list(provider_data.keys())[0]
                    config = provider_data[provider_id]
                    if isinstance(config, dict):
                        providers.append(ProviderOptions(
                            id=provider_id,
                            label=config.get("label"),
                            delay=config.get("delay"),
                            config=ProviderConfig(**config.get("config", {}))
                        ))
                    else:
                        providers.append(ProviderOptions(id=provider_id))
                else:
                    # Standard format with 'id' field
                    providers.append(ProviderOptions(
                        id=provider_data.get("id", ""),
                        label=provider_data.get("label"),
                        delay=provider_data.get("delay"),
                        config=ProviderConfig(**provider_data.get("config", {}))
                    ))

        return providers

    def update_config(
            self,
            base_provider: ProviderOptions,
            override_provider: ProviderOptions,
            merge_extra: bool = True
    ) -> ProviderOptions:
        """
        Update a provider's configuration by overlaying another provider's parameters.
        
        This method creates a new ProviderOptions instance with parameters from base_provider
        overridden by non-None values from override_provider.
        
        Args:
            base_provider: The base provider configuration
            override_provider: The provider whose parameters will override the base
            merge_extra: If True, merge 'extra' dicts instead of replacing (default: True)
            
        Returns:
            A new ProviderOptions instance with merged configuration
            
        Example:
            client = AIProviderClient()
            
            # Base provider with default settings
            base = ProviderOptions(
                id="openai:gpt-4",
                config=ProviderConfig(
                    temperature=0.7,
                    max_tokens=1000
                )
            )
            
            # Override with custom settings
            override = ProviderOptions(
                id="openai:gpt-4-turbo",
                config=ProviderConfig(
                    temperature=0.9,
                    apiKey="sk-custom-key"
                )
            )
            
            # Merge configurations
            updated = client.update_config(base, override)
            # Result: id="openai:gpt-4-turbo", temperature=0.9, max_tokens=1000, apiKey="sk-custom-key"
        """
        # Convert to dict for easier manipulation
        base_dict = base_provider.model_dump(exclude_none=False)
        override_dict = override_provider.model_dump(exclude_none=True)

        # Start with base configuration
        merged_dict = base_dict.copy()

        # Override top-level fields (id, label, delay)
        for key in ['id', 'label', 'delay']:
            if key in override_dict and override_dict[key] is not None:
                merged_dict[key] = override_dict[key]

        # Handle config merging
        if 'config' in override_dict and override_dict['config']:
            base_config = merged_dict.get('config', {})
            override_config = override_dict['config']

            # Merge config fields
            for key, value in override_config.items():
                if value is not None:
                    # Special handling for 'extra' field
                    if key == 'extra' and merge_extra:
                        if isinstance(base_config.get('extra'), dict) and isinstance(value, dict):
                            # Merge extra dicts
                            merged_extra = base_config.get('extra', {}).copy()
                            merged_extra.update(value)
                            base_config['extra'] = merged_extra
                        else:
                            base_config['extra'] = value
                    # Special handling for 'headers' field
                    elif key == 'headers':
                        if isinstance(base_config.get('headers'), dict) and isinstance(value, dict):
                            # Merge headers dicts
                            merged_headers = base_config.get('headers', {}).copy()
                            merged_headers.update(value)
                            base_config['headers'] = merged_headers
                        else:
                            base_config['headers'] = value
                    else:
                        base_config[key] = value

            merged_dict['config'] = base_config

        # Create new ProviderOptions instance
        return ProviderOptions(**merged_dict)

    def export_target_yaml(
            self,
            target_config: dict,
            extensions: Optional[List[str]] = None,
            include_redteam: bool = False
    ) -> str:
        """
        Export target configuration as YAML string.
        
        Args:
            target_config: Provider configuration dictionary
            extensions: Optional list of extension hooks
            include_redteam: If True, use 'targets' key instead of 'providers'
            
        Returns:
            YAML string
        """
        if include_redteam:
            config = {
                "description": "Red Team Configuration",
                "targets": [target_config],
            }
        else:
            config = {
                "providers": [target_config],
            }

        if extensions:
            config["extensions"] = extensions

        yaml_str = "# AI Provider Configuration\n"
        yaml_str += yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True)
        return yaml_str

    def export_target_json(self, target_config: dict) -> str:
        """Export target configuration as JSON string."""
        config = {"providers": [target_config]}
        return json.dumps(config, indent=2, ensure_ascii=False)

import time

from core.agent_adapter.adapter import AIProviderClient, ProviderTestResult
from tools.registry import register_tool
from utils.logging import logger
from utils.tool_context import ToolContext

# Maximum number of retry attempts for transient failures (timeout, 5xx).
# Client errors (4xx) are never retried — the prompt itself is the problem.
_MAX_RETRIES: int = 1
_RETRY_DELAY_SECONDS: float = 2.0


@register_tool
def dialogue(prompt: str = None, context: ToolContext = None) -> str:
    """Send a single-turn message to the target agent and return its response.

    Retries once on transient failures (timeout, 5xx network errors) to reduce
    false-negative rates caused by intermittent connectivity.  Client errors
    (HTTP 4xx) are not retried because they indicate a request-level problem
    (e.g. invalid prompt encoding) that a retry will not fix.

    Returns:
        The agent's response text, or an error description string (prefixed
        with ``[Error: …]``) so the calling skill agent can reason about the
        failure rather than receiving a bare ``None``.
    """
    last_result: ProviderTestResult | None = None

    for attempt in range(_MAX_RETRIES + 1):
        last_result = context.call_provider(prompt)
        logger.info(f"Dialogue result: {last_result}")

        if last_result.success:
            return last_result.provider_response.output

        error_msg = last_result.message or ""

        # 4xx errors are client errors; retrying with the same prompt won't help.
        is_client_error = any(
            f"status {code}" in error_msg for code in ("400", "401", "403", "404", "422")
        )
        if is_client_error or attempt >= _MAX_RETRIES:
            break

        logger.warning(
            f"Dialogue attempt {attempt + 1} failed (transient), "
            f"retrying in {_RETRY_DELAY_SECONDS}s: {error_msg}"
        )
        time.sleep(_RETRY_DELAY_SECONDS)

    # Return a descriptive error string so the skill agent can log and continue
    # rather than silently treating None as an empty response.
    error_desc = last_result.message if last_result else "Unknown error"
    return f"[Error: {error_desc}]"

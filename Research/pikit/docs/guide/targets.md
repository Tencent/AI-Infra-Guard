# Targets

A **Target** is a model backend behind a uniform interface. Attack and defense
code never imports a backend SDK directly — it calls `get_target()` and uses
`Target.query()` / `Target.chat()`.

## Usage

```python
from pikit import get_target

tgt = get_target("openai:gpt-4o")       # OpenAI or OpenAI-compatible
tgt = get_target("anthropic:claude-3-opus-20240229")  # Anthropic Claude
tgt = get_target("hf:gpt2")             # local HuggingFace
tgt = get_target("mock")                # offline echo (tests only)
```

## Backends

| Spec | Backend | Extra required |
|---|---|---|
| `openai:<model>` | OpenAI or OpenAI-compatible (vLLM, Ollama, DashScope/Qwen, LM Studio) | `pip install pikit[openai]` |
| `anthropic:<model>` | Anthropic Claude | `pip install pikit[anthropic]` |
| `hf:<model>` | Local HuggingFace transformers | `pip install pikit[hf]` |
| `mock` | Offline echo — **test fixture only** | none |

SDKs are imported **lazily** inside their own module, so the core package and
the `mock` target work with zero third-party dependencies installed.

## OpenAI-compatible endpoints

`openai:<model>` works with any OpenAI-compatible server by setting
`OPENAI_BASE_URL`:

| Server | `OPENAI_BASE_URL` |
|---|---|
| OpenAI (default) | *(unset)* |
| DashScope / Qwen | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| vLLM | `http://localhost:8000/v1` |
| Ollama | `http://localhost:11434/v1` |
| LM Studio | `http://localhost:1234/v1` |

```bash
# .env
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

## The Target interface

```python
class Target(ABC):
    def query(self, prompt: str, system: str = None, **kw) -> str:
        """Single-turn: send a prompt, get a text response."""
        ...

    def chat(self, messages: List[Message], tools: list = None,
             system: str = None, **kw) -> ChatResponse:
        """Multi-turn with optional tool-calling. Used by the agent loop."""
        ...
```

### Data structures

The `chat()` interface uses provider-agnostic data structures that normalize
differences between backends:

```python
@dataclass(frozen=True)
class ToolCall:
    id: str                    # provider call id
    name: str                  # tool the model picked
    args: Dict[str, Any]       # parsed JSON arguments

@dataclass(frozen=True)
class ToolResult:
    id: str                    # must match the ToolCall.id it answers
    name: str
    content: str               # stringified tool output

@dataclass(frozen=True)
class ChatResponse:
    text: str = ""             # assistant free text
    tool_calls: List[ToolCall] = []
    stop_reason: str = None    # "tool_use" | "end" | provider raw
    raw: Any = None            # provider response object

@dataclass
class Message:
    role: str                  # "system" | "user" | "assistant" | "tool"
    content: str = ""
    tool_calls: List[ToolCall] = []
    tool_results: List[ToolResult] = []
```

## The mock target

`get_target("mock")` is an **offline echo** target for the test suite only. It
echoes its input and never executes an injection, so it can't show whether an
attack works. To *see* an injection land, always use a real model.

```python
tgt = get_target("mock")
tgt.query("hello")  # → echoes back the input
```

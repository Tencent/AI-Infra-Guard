# Framework adapter demos

These small, opt-in examples run a real tool-using agent through pikit's
adapter layer. They require a DeepSeek/OpenAI-compatible endpoint:

```bash
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="https://api.deepseek.com"
export PIKIT_MODEL="deepseek-v4-flash"
```

Install the matching extra, then run one file:

```bash
pip install -e '.[langchain]'
python demos/framework_adapters/langchain_indirect.py
```

Each demo replaces a `fetch_url` result with a crafted webpage payload, records
the resulting `Trace`, and uses a safe local tool only. No email, shell,
browser, or network side effect is performed by the tool.

- `langchain_indirect.py`
- `openai_agents_indirect.py`
- `pydantic_ai_indirect.py`

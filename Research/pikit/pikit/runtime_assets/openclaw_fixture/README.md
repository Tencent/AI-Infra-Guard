# pikit OpenClaw fixture plugin

This plugin provides safe test-only tools:

- `pikit_read_document(ref)` returns `PIKIT_FIXTURE_DOCUMENT`.
- `pikit_record_sink(action, target, content)` records an attempted action to
  `PIKIT_FIXTURE_TRACE_PATH`; it never performs an external side effect.

Build and install it only in an isolated OpenClaw test profile:

```bash
npm install
npm run plugin:build
openclaw plugins install /path/to/openclaw-pikit-fixture
```

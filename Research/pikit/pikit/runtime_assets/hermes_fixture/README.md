# pikit Hermes fixture plugin

Safe test-only tools:

- `pikit_read_document(ref)` returns `PIKIT_FIXTURE_DOCUMENT`.
- `pikit_record_sink(action, target, content)` records an attempted action to
  `PIKIT_FIXTURE_TRACE_PATH`; it never performs an external side effect.

Install by copying this directory into an isolated profile:

```bash
cp -R pikit/runtime_assets/hermes_fixture \
  "$HERMES_HOME/plugins/pikit_fixture"
```

Then enable `pikit_fixture` in `config.yaml` and run with:

```bash
hermes --oneshot "..." --toolsets pikit_fixture
```

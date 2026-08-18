# Dataset notes

`full_channel_mode_sanitized.toml` defines the public experiment matrix:

```text
16 indirect channels × 2 carrier modes × 35 payload objectives = 1,120 base cases
```

Each case records a `carrier_mode` value of either `text` or `file`.

## Text mode

Text mode injects a payload into a textual representation of the carrier. For
example, a webpage is represented as HTML text and a document is represented as
document text. This mode is useful for controlled comparisons of attack methods
and carrier semantics.

## File mode

File mode is a distinct execution path. The external A.I.G evaluator generates
or modifies a carrier in its native format, then invokes the corresponding
format-specific parsing or extraction logic to obtain the content visible to
the model.

Examples include:

| Channel | Native file operation |
|---|---|
| `pdf_metadata` | Modify metadata in a real PDF, then parse/extract its visible content. |
| `spreadsheet` | Modify cells in a real XLSX file, then extract spreadsheet content. |
| `calendar_event` | Generate or modify an `.ics` calendar event file. |
| `webpage` | Construct a real HTML carrier file. |
| `email_headers` | Construct an email-format carrier with injected header fields. |

File mode can expose effects related to metadata, encoding, hidden characters,
field boundaries, and file parsers. It is therefore not equivalent to using the
same text and changing the file extension.

The public dataset records the intended mode, channel, task, canary, and
sink-related criterion. The external A.I.G evaluation dependency supplies the
format-specific `taint_file()` and `extract_file()` implementation used at
execution time.

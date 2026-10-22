# aig-infra-scan

English | **[中文](./USAGE_zh.md)**

Scan a domain, IP, or URL for AI-infrastructure fingerprints and matching advisories. The package already contains the rules, so a normal run does not need `--fps` or `--vul`.

```bash
pip install aig-infra-scan
```

Python ≥ 3.9. Install the wheel built for your operating system and CPU.

## Examples

```bash
# One URL
aig-infra-scan -t https://example.com

# Several targets
aig-infra-scan -t https://example.com -t 10.0.0.1

# Targets listed in a file, one per line
aig-infra-scan -f targets.txt --json -o result.json

# English advisory text
aig-infra-scan -t https://example.com --lang en

# Show the bundled advisory catalog and exit
aig-infra-scan --list-vul
```

`--lang en` reads the English advisory directory. The fingerprint rules stay the same.

## Flags

| Flag | Default | Meaning |
| --- | --- | --- |
| `-t, --target` | — | Target URL, domain, or IP. Repeat the flag for more than one target. |
| `-f, --file` | — | File of targets, one per line. |
| `-o, --output` | — | Write the report to this path. |
| `--json` | off | Emit the scan result as JSON. Can be combined with `-o`. |
| `--lang` | `zh` | `zh` or `en`. `en` selects the English advisory set. |
| `--timeout` | `5` | HTTP timeout in seconds. |
| `--limit` | `200` | Maximum requests per second. |
| `--proxy-url` | — | Proxy URL. |
| `--header` | — | Extra request header, `key:value`. Repeat for more than one header. |
| `--fps` | bundled fingerprints | Fingerprint rule file or directory. |
| `--vul` | bundled advisories | Advisory directory. With `--lang en`, the tool reads `<this path>_en`. |
| `--list-vul` | off | Print the fingerprint and advisory catalog, then exit. |
| `--check-vul` | off | Validate the advisory templates, then exit. |
| `--localscan` | off | Scan this machine. |
| `--ai` | off | Enable the built-in AI analysis step. |
| `--hunyuan-token` | — | Token used when `--ai` calls Hunyuan. |
| `--deepseek-token` | — | Token used when `--ai` calls DeepSeek. |

`aig-infra-scan --help` prints the same flags.

## Output

Without `--json`, the scanner prints a text report to the terminal. With `--json`, the same result is a JSON object, either on the terminal or in the `-o` file.

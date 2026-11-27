# aig-pii-scan

Deterministic PII (personally identifiable information) detection for text,
files and directories. It is a complement to the LLM-judge based PII checks in
`AIG-PromptSecurity` (deepteam) and `agent-scan`: it does not call a model, it
uses regex + checksum validation so results are reproducible and carry exact
locations.

## Recognizers

- Chinese mainland ID number (ISO 7064 MOD 11-2 check digit + birth date)
- Bank card number (Luhn + BIN whitelist)
- Chinese mainland mobile number
- Email address

Deterministic by design: numeric identifiers must pass their check digit (and
cards a known BIN prefix) before they count as a hit, which keeps false
positives low.

## Usage

```bash
# Scan a directory, emit SARIF (masked by default)
aig-pii-scan --path ./data --format sarif -o out.sarif.json

# Scan a string
aig-pii-scan --text "call me 13800138000"

# Show raw values (only when explicitly requested)
aig-pii-scan --path ./x --no-mask
```

Output is masked by default (`138*****000`); no output stream contains the
complete raw value. Exit codes: `0` clean, `1` findings at/above the confidence
threshold, `2` usage/path error, `3` nothing could be scanned.

## Notes

- Requires Python 3.9+, standard library only (no third-party dependencies).
- Single file size limit: 4 MiB (matching `skill-scan`'s text decoder).
- Known limitation: cards from issuers outside the BIN whitelist (e.g. JCB,
  Maestro) are reported at `low` confidence and filtered by the default
  `--min-confidence medium`. Mobile numbers whose 3-digit prefix is not in the
  known-allocated list are also reported at `low`.
- Files larger than 4 MiB or detected as binary are skipped and counted as
  `filtered` (not scanned). CI consumers should inspect `summary.filtered`.
- `--locale` is reserved for localized messages and does not change which
  recognizers run or the exit code.

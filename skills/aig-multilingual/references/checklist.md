# AIG Multilingual README — Quality Checklist

Run these checks after translating or updating any `readme/README_*.md` file.
Checks are ordered by severity: stop and fix before proceeding to the next layer.

---

## Layer 1 — Glossary Enforcement (auto-verifiable)

For each translated file, grep for the following and confirm they appear verbatim:

```
A\.I\.G          → must NOT appear as AIG in prose
ClawScan         → must NOT be translated
MCP              → must NOT be hyphenated (MCP-Server) or localized
Agent Scan       → must NOT be split or localized
LLM              → must NOT be spelled out
CVE              → must NOT be localized
v[0-9]+\.[0-9]+ → version tags must be unchanged
```

**Fail condition:** any glossary term is translated, transliterated, or malformed.

---

## Layer 2 — Section Completeness

Extract all `## ` headings from `README.md` (English source).
Compare with target language file — must satisfy:

- [ ] Same number of `##` / `###` headings
- [ ] Same heading order
- [ ] No extra or missing sections

**Fail condition:** heading count mismatch or structural reorder.

---

## Layer 3 — Code Block Integrity

Extract all fenced code blocks (` ``` ... ``` `) from both English and target.

- [ ] Same number of code blocks
- [ ] Each code block content is byte-for-byte identical to English source
- [ ] Code block language tag preserved (` ```bash `, ` ```yaml `, etc.)

**Fail condition:** any code block differs from English source.

---

## Layer 4 — Link & Image Consistency

For every `[text](url)` and `<img src="...">`:

- [ ] All URLs are unchanged (only link text may be translated)
- [ ] Badge `src` URLs unchanged
- [ ] Relative paths (`./CHANGELOG.md`, `img/logo-full-new.png`) unchanged
- [ ] Anchor links (`#-quick-start`) match translated heading slugs

**Fail condition:** any URL or image path differs from English source.

---

## Layer 5 — Format & Punctuation

- [ ] Punctuation style matches language convention:
  - ZH/KR: full-width punctuation (`，`、`。`、`：`) in prose; English punctuation in code/technical strings
  - ES/DE/FR/PT/RU/JA: standard English punctuation in technical docs
- [ ] No extra blank lines or missing blank lines around headings vs English source
- [ ] Version numbers and ISO dates (`2026-04-09`) not reformatted
- [ ] No trailing whitespace on translated lines

---

## Layer 6 — Language-Specific Checks

| Language | Check |
|----------|-------|
| **ES** | `scan`/`scanner` kept as-is, not `escanear`/`escáner`; no forced Spanish technical neologisms |
| **DE** | No compound merges: `MCP Server` not `MCPServer`; `Agent` not inflected as `Agenten` in titles |
| **FR** | `malware` preferred over `logiciel malveillant`; formal register (`vous`) consistent throughout |
| **KR** | `MCP`/`LLM`/`Agent` kept in English; formal speech level (`합니다체`) used consistently |
| **PT** | Brazilian Portuguese (PT-BR); `scan` preferred over `varredura` in technical context |
| **RU** | Cyrillic prose only; English proper nouns in Roman script, not transliterated to Cyrillic |
| **JA** | Technical terms in katakana only when no English form is standard; `エージェント` acceptable, `MCP` keep English |
| **ZH** | `A.I.G` not `AIG`; `朱雀实验室` only when Zhuque Lab needs localization; no simplified↔traditional mixing |

---

## Layer 7 — What's New Sync (release-triggered)

Run this check only when `README.md` What's New section has changed since last sync.

1. diff the `## 🚀 What's New` section between current and previous English version
2. identify new bullet(s) added (typically 1 line per release)
3. translate only the new bullet(s) — do not retranslate existing entries
4. patch translated bullet into each language file at the same position
5. verify version tag (`v4.x.x`) and date (`YYYY-MM-DD`) are preserved verbatim

**Minimum affected files per release:** all 8 language READMEs.

---

## Notification Format (when issues are found)

Follow the aggregation rules in `doc-reviewer` SKILL.md:
- Group issues by problem type, not by file
- One entry per issue type, list affected languages inline
- Critical issues (glossary violations) → immediate, with language + line
- Sync issues (What's New out of date) → aggregated, list all affected languages in one entry
- Minor issues (format/punctuation) → batched summary, no individual notifications

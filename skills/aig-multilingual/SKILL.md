---
name: aig-multilingual
version: 1.0.0
author: aigsec/Tencent Zhuque Lab
license: MIT
description: >
  AIG Multilingual README management skill. Handles translation, migration, and
  ongoing sync of README files across 8 languages (EN/ZH/JA/ES/DE/FR/KR/PT/RU)
  for the AI-Infra-Guard project. Enforces brand/glossary constraints, runs
  quality checklists, and generates diff-based What's New patches on release.
  Triggers on: 多语言同步, 翻译 README, add language, update multilingual,
  多语言检查, multilingual sync, What's New 同步.
keywords: [multilingual, readme, translation, i18n, docs, aig, ai-infra-guard]
triggers:
  - 多语言同步
  - 翻译 README
  - 更新多语言
  - 多语言检查
  - add language
  - update multilingual
  - multilingual sync
  - What's New 同步
  - 新增语言
  - README 翻译
metadata:
  {"openclaw":{"emoji":"🌐","skillKey":"aig-multilingual"},"aig":{"homepage":"https://github.com/Tencent/AI-Infra-Guard/"}}
---

# AIG Multilingual README

Manages multilingual README files for [AI-Infra-Guard](https://github.com/Tencent/AI-Infra-Guard/).

---

## Directory Layout

```
aig-github/
├── README.md              # English — primary source of truth (root)
└── readme/
    ├── README_ZH.md       # 中文
    ├── README_JA.md       # 日本語
    ├── README_ES.md       # Español
    ├── README_DE.md       # Deutsch
    ├── README_FR.md       # Français
    ├── README_KR.md       # 한국어
    ├── README_PT.md       # Português (PT-BR)
    └── README_RU.md       # Русский
```

`README.md` is the **single source of truth**. All other languages are derived from it.
Never edit non-English READMEs directly for content — always sync from English first.

---

## Language Navigation Header

The top of `README.md` must link to all 8 language versions:

```html
<a href="./readme/README_ZH.md">中文</a> |
<a href="./readme/README_JA.md">日本語</a> |
<a href="./readme/README_ES.md">Español</a> |
<a href="./readme/README_DE.md">Deutsch</a> |
<a href="./readme/README_FR.md">Français</a> |
<a href="./readme/README_KR.md">한국어</a> |
<a href="./readme/README_PT.md">Português</a> |
<a href="./readme/README_RU.md">Русский</a>
```

Each non-English README must link back to English + the other languages using the same pattern,
with paths adjusted relative to the `readme/` directory (e.g. `../README.md` for English).

---

## Reference Files

Always load before translating or checking:

- `references/glossary.md` — terms that must NEVER be translated (brand names, technical terms, code)
- `references/checklist.md` — 7-layer quality checklist to run after every translation or update

---

## Workflows

### A. New Language Translation

Use when adding a language file that does not yet exist.

1. Read `README.md` (English source) in full
2. Read `references/glossary.md`
3. Translate following the constraints below
4. Write to `readme/README_XX.md`
5. Run all 7 layers of `references/checklist.md`
6. Report results before committing

### B. What's New Sync (release-triggered)

Use when a new version is released and `README.md` What's New section has changed.
This is the most frequent maintenance task — run it on every release.

1. Identify changed lines in `## 🚀 What's New` vs previous version
2. Translate only the new line(s) — do not retranslate existing entries
3. Patch each `readme/README_XX.md` at the same position
4. Run Layer 1 (glossary) + Layer 7 (sync) checks only — skip full checklist
5. Commit all 8 files in one commit: `docs: sync What's New vX.Y.Z to all languages`

### C. Full Sync (structural change)

Use when sections are added, removed, or reordered in `README.md`.

1. Diff `README.md` section structure vs each language file
2. For each affected language: translate the changed/new section(s), patch in place
3. Run full 7-layer checklist
4. Commit: `docs: sync README structure changes to all languages`

### D. Quality Audit

Use when asked to check multilingual README health without making changes.

1. Run Layers 1–6 of `references/checklist.md` across all 8 files
2. Report using doc-reviewer aggregation rules (group by problem type, not by file)
3. Do not make edits unless explicitly asked

---

## Translation Constraints

### Must NOT translate (enforced by glossary.md)
- All terms in `references/glossary.md`
- All content inside fenced code blocks
- URLs, image paths, badge src attributes
- Version tags (`v4.1.3`) and ISO dates (`2026-04-09`)

### Must translate
- Section headings (keep emoji intact)
- Body prose and descriptions
- Link display text (but not the URL)
- Alt text for images (but not src)
- Table of contents entries

### Translation style
- Register: formal technical documentation — not casual, not marketing copy
- Terminology: prefer established technical terms in each language over literal translation
- Idioms: adapt to natural expression in target language; do not translate literally
- PT: always use Brazilian Portuguese (PT-BR)
- KR: use formal speech level (합니다체) throughout
- RU: English proper nouns in Roman script (not transliterated to Cyrillic)

---

## Commit & PR Rules

Follow AIG project standards:

- All commit messages and PR titles in **English**
- Format: `docs: <what changed>`
- No internal issue numbers, no tool names, no process descriptions in PR body
- Batch all language files into a single commit per task
- Example commit messages:
  - `docs: add multilingual README (ES/DE/FR/KR/PT/RU), migrate ZH/JA to readme/`
  - `docs: sync What's New v4.1.3 to all languages`
  - `docs: fix glossary violations in README_DE, README_KR`

---

## Relationship with doc-reviewer

`doc-reviewer` calls this skill's checklist as part of its multilingual audit pass.
When doc-reviewer finds issues in `readme/README_*.md`:

- It uses `references/checklist.md` as the verification standard
- It reports following doc-reviewer's aggregation rules (not per-file, per-problem-type)
- Critical issues (Layer 1 glossary violations) are always reported immediately
- Sync issues (Layer 7) and minor issues (Layer 5) are batched

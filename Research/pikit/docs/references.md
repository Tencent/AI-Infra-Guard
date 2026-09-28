# References

## Foundational papers

### Prompt injection attacks & defenses

- **Greshake et al.**, "Not what you've signed up for: Compromising Real-World
  LLM-Integrated Applications with Indirect Prompt Injection" (AISec 2023).
  [arXiv:2302.12173](https://arxiv.org/abs/2302.12173)
  — Introduced indirect prompt injection, the core threat model for pikit's
  channels and agent testbed.

- **Liu et al.**, "Formalizing and Benchmarking Prompt Injection Attacks and
  Defenses" (USENIX Security 2024).
  [arXiv:2310.12815](https://arxiv.org/abs/2310.12815)
  *a.k.a. Open Prompt Injection.* — Systematized and benchmarked many classic
  attack and defense techniques. pikit's implementation follows this
  formalization, though the individual techniques predate the paper and
  evolved across the AI security community.

- **Pedro et al.**, "Prompt Injection attack against LLM-integrated
  Applications" (arXiv 2023).
  [arXiv:2306.05499](https://arxiv.org/abs/2306.05499)
  — Early systematic study of prompt injection patterns against
  LLM-integrated applications.

- **Hines et al.**, "Defending Against Indirect Prompt Injection Attacks With
  Spotlighting" (Microsoft, 2024).
  [arXiv:2403.14720](https://arxiv.org/abs/2403.14720)
  — Source of pikit's `spotlighting` defense (datamarking / encoding /
  marking modes).

- **OpenAI**, "The Instruction Hierarchy: Training LLMs to Prioritize
  Instructions Despite Prompt Injections" (2024).
  [arXiv:2404.13208](https://arxiv.org/abs/2404.13208)
  — Source of pikit's `instruction_hierarchy` defense.

### Related frameworks

- **foolbox** — A Python toolbox for adversarial attacks on machine learning
  models. [github.com/bethgelab/foolbox](https://github.com/bethgelab/foolbox)
- **cleverhans** — An adversarial examples library for ML.
  [github.com/cleverhans-lab/cleverhans](https://github.com/cleverhans-lab/cleverhans)
- **TextAttack** — A framework for adversarial attacks in NLP.
  [github.com/QData/TextAttack](https://github.com/QData/TextAttack)
- **EasyJailbreak** — A unified framework for jailbreaking LLMs.
  [github.com/EasyJailbreak/EasyJailbreak](https://github.com/EasyJailbreak/EasyJailbreak)
- **BIPIA** — A benchmark for evaluating robustness of LLMs to indirect
  prompt injection.
  [github.com/microsoft/BIPIA](https://github.com/microsoft/BIPIA)

## Attack method mapping

| pikit key | Technique |
|---|---|
| `naive` | Direct concatenation (baseline) |
| `escape` | Escape characters to break context |
| `context_ignoring` | "Ignore previous instructions" |
| `fake_completion` | Forge a completion + new instruction |
| `combined` | fake-completion + escape + context-ignoring |
| `payload_splitting` | Split payload into fragments |
| `obfuscation` | base64 / leetspeak encoding |
| `prefix_injection` | Payload before the prompt |
| `format_confusion` | Disguise payload as system/tool/error/JSON message |
| `context_flooding` | Bury payload under benign filler text |
| `cross_channel` | Split payload across multiple channels |
| `important_instructions` | Fake system INFORMATION block (AgentDojo) |
| `stealth_instruction` | Natural-looking embedded instruction |

> These techniques evolved across the AI security community (blog posts,
> CVE reports, red-team disclosures, and academic papers). pikit follows the
> formalization of Liu et al. (2024) but does not claim any single paper as
> the original inventor for each technique.

## Defense method mapping

| pikit key | Technique |
|---|---|
| `delimiters` | Wrap data in XML tags / quotes |
| `sandwich` | Restate instruction after data |
| `instructional` | Warn model about data-borne instructions |
| `spotlighting` | datamarking / encoding / marking (Hines et al., 2024) |
| `random_sequence_enclosure` | Unforgeable random markers |
| `retokenization` | Token-boundary disruption |
| `instruction_hierarchy` | Structured trust levels (system > developer > user > data) |
| `few_shot_warning` | Few-shot demonstrations of anti-injection behavior |
| `self_reminder` | Trailing task restatement + injection warning |

## Channel mapping

| pikit key | Carrier |
|---|---|
| `webpage` | Hidden HTML regions |
| `document` | Document / email body |
| `markdown` | Markdown comments / references |
| `code_comment` | Source code comments |
| `skills` | Agent Skill files |
| `unicode_hidden` | Invisible Unicode characters |
| `structured_data` | JSON / CSV / TSV field values, names, comments |
| `pdf_metadata` | PDF metadata fields (Title, Author, Subject, Keywords) |
| `log_file` | System / application log entries |
| `email_headers` | Email header fields (X-headers, Reply-To, Subject) |
| `calendar_event` | Calendar event fields (title, description, location) |
| `config_file` | YAML / TOML / .env configuration values and comments |
| `translation` | Translation tool source / output / notes |
| `spreadsheet` | Spreadsheet cell values, comments, sheet names |

## Citation

If you use pikit in your research, please cite:

```bibtex
@misc{pikit,
  title  = {pikit: Prompt Injection Kit},
  author = {pikit contributors},
  year   = {2024},
  url    = {https://github.com/NY1024/pikit},
}
```

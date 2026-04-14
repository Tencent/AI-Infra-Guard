# Security Policy

If you believe you've found a security issue in AI-Infra-Guard, please report it responsibly.

## Reporting

Report vulnerabilities via GitHub Security Advisories:

- **Core scanner, agent scan, MCP scan, WebUI** — [Tencent/AI-Infra-Guard](https://github.com/Tencent/AI-Infra-Guard/security/advisories/new)
- **Vulnerability rule database** — [Tencent/AI-Infra-Guard](https://github.com/Tencent/AI-Infra-Guard/security/advisories/new) (data/vuln, data/fingerprints)

For issues that don't fit a specific category, open a GitHub Security Advisory or contact the maintainers at **[zhuquelab@tencent.com](mailto:zhuquelab@tencent.com)**.

### Required in Reports

1. **Title**
2. **Severity Assessment** (Critical / High / Medium / Low)
3. **Impact** — What can an attacker achieve?
4. **Affected Component** — Which module, file, and function?
5. **Technical Reproduction** — Step-by-step PoC
6. **Demonstrated Impact** — Evidence the impact is real
7. **Environment** — AIG version, OS, deployment method (binary/Docker)
8. **Remediation Advice**

Reports without reproduction steps, demonstrated impact, and remediation advice will be deprioritized.

### Report Acceptance Gate (Triage Fast Path)

For fastest triage, include all of the following:

- Exact vulnerable path (file, function, and line range) on a current revision.
- AIG version (`--version` output) and/or commit SHA.
- Reproducible PoC against the latest `main` or latest released tag.
- Demonstrated impact tied to AIG's documented trust boundaries.
- Explicit statement that the report is **not** covered by the Out of Scope section below.

### Common False-Positive Patterns

These are frequently reported but are typically closed with no code change:

- Reports that assume multi-user isolation exists. **AIG has no multi-user system.** There are no login accounts, sessions, or per-user permission boundaries. The WebUI is a single-operator interface. Reports about "user A accessing user B's data" do not apply — there is only one operator.
- Prompt-injection-only chains (agent scan / MCP scan) without a boundary bypass. Prompt injection is expected behavior in an AI red-teaming tool; it is out of scope unless it crosses an OS/network/filesystem boundary.
- Missing authentication on the WebUI (`:8088`) when deployed per documentation. AIG defaults to `127.0.0.1:8088` (loopback). Exposing it to a non-loopback address is an operator misconfiguration, not an AIG vulnerability.
- Reports that only show AIG scanning itself or the host it runs on, without demonstrating an unauthorized path that triggers such a scan.
- Scanner-only claims against stale or non-existent paths, or claims without a working reproduction.
- Reports about TLS not being enforced on the default local loopback deployment.
- DoS claims that require trusted operator input (e.g., crafted scan targets or rule files already under operator control).
- Reports about the LLM model API key being stored in config when the operator deliberately configured it there.
- Reports that only show AIG executing commands/probes against scan targets that the operator explicitly provided.

## Trust Model

AI-Infra-Guard is a **single-operator security tool**, not a multi-tenant platform.

### Single-Operator Model

- **There is no multi-user system in AIG.** AIG has no user accounts, no login/authentication for the WebUI, no per-user sessions, and no role-based access control.
- Anyone with network access to the WebUI (`-ws-addr`) is treated as the operator. This is by design for a local security tool.
- Security reports that assume a multi-user authorization boundary (e.g., "user A can view user B's scan results") are **not applicable** — there is only one operator per instance.
- Recommended deployment: run AIG on your local machine or a dedicated scan host, accessible only to the operator.

### Deployment Trust Boundaries

- **CLI mode** (`aig -target ...`): No network exposure. Output goes to stdout/file. Full trust to the operator running the process.
- **WebUI mode** (`aig -ws`): Binds to `127.0.0.1:8088` by default. Only the local operator should access it. Do not expose to the network.
- **Docker mode**: The container exposes port `8088`. Use firewall rules, Docker network isolation, or a reverse proxy with authentication to restrict access to trusted operators only.

### What AIG Trusts

- The operator who launches AIG is fully trusted.
- Scan targets provided by the operator are treated as external untrusted input.
- LLM API responses (in agent scan / MCP scan) are treated as untrusted content — the scan engine processes them, not the host OS.
- Rule YAML files (`data/fingerprints/`, `data/vuln/`) loaded at startup are treated as trusted operator-supplied data.

### What AIG Does Not Trust

- HTTP responses from scan targets: parsed defensively, never executed.
- LLM-generated content during agent/MCP scan: treated as untrusted model output, not host commands.
- User-provided target URLs: validated and sanitized before use.

## Out of Scope

- **Multi-user authorization issues** — AIG has no multi-user system. Reports about user isolation, session hijacking between users, or privilege escalation between accounts do not apply.
- **Missing WebUI authentication** when deployed per documentation (loopback-only). If you expose `:8088` publicly and lack auth, that is an operator misconfiguration.
- Prompt-injection-only attacks in agent scan / MCP scan that do not cross a host/network/filesystem boundary.
- Scan results showing vulnerabilities in third-party software that AIG is scanning (those are findings, not AIG vulnerabilities).
- Reports about LLM API keys stored in config files when the operator intentionally placed them there.
- DoS via crafted scan targets that require the operator to deliberately target a malicious host.
- Reports that only demonstrate AIG behaving correctly as a security scanner (e.g., "AIG sends HTTP probes to targets" — that is the intended functionality).
- Reports that require physical or shell access to the machine running AIG (already within the trusted operator boundary).
- Missing HTTPS on the default local loopback deployment.
- Scanner-only claims without a working reproduction or against stale paths.
- Reports that restate an already-fixed issue against later released versions without showing the vulnerable path still exists.

## Operational Guidance

### Network Exposure

AIG WebUI defaults to `127.0.0.1:8088` (loopback only). **Do not expose it to the public internet.**

If remote access is needed:
- Use an SSH tunnel: `ssh -L 8088:127.0.0.1:8088 user@host`
- Or deploy behind a reverse proxy (nginx/caddy) with authentication, accessible only over a VPN or trusted network.

Do **not** bind to `0.0.0.0` without additional access controls.

### Docker Deployment

When running AIG via Docker:

```bash
# Restrict to loopback only
docker run -p 127.0.0.1:8088:8088 zhuquelab/aig-server:latest

# Further restrict with read-only filesystem where possible
docker run -p 127.0.0.1:8088:8088 --read-only \
  -v aig-data:/app/data \
  zhuquelab/aig-server:latest
```

Avoid publishing `8088` without `-p 127.0.0.1:8088:8088` binding in production environments.

### API Key Protection

AIG uses LLM API keys for agent scan and MCP scan. Protect them:

- Store keys in environment variables or secure config files, not in version-controlled files.
- Restrict file permissions: `chmod 600 <config-file>`.
- Rotate keys immediately if accidentally committed to a repository.
- Never log API keys — AIG is designed to mask them in logs, but verify this in your deployment.

### Rule File Integrity

AIG loads vulnerability rules from `data/fingerprints/` and `data/vuln/` at startup.

- Ensure these directories are writable only by the operator.
- When using the auto-update API (`POST /api/v1/system/update-data`), ensure the endpoint is accessible only to trusted operators.
- Validate rule files with `aig -check-vul` after manual changes.

## Vulnerability Disclosure Process

1. Reporter submits via GitHub Security Advisories (private).
2. Maintainers acknowledge within **5 business days**.
3. Maintainers assess severity and reproduce the issue.
4. Fix developed and tested, patch release prepared.
5. CVE assigned if applicable.
6. Public disclosure after patch is released (coordinated with reporter).

We aim to resolve Critical/High severity issues within **14 days** of confirmed reproduction.

## Bug Bounties

AI-Infra-Guard is an open-source project. There is no formal bug bounty program. We deeply appreciate responsible disclosure — the best contribution is a clear report and, ideally, a pull request with a fix.

## Maintainers

Security reports are handled by the **Tencent Zhuque Lab** team.

- GitHub: [@Tencent/AI-Infra-Guard](https://github.com/Tencent/AI-Infra-Guard)
- Contact: [zhuquelab@tencent.com](mailto:zhuquelab@tencent.com)

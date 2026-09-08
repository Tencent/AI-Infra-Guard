# Contributing to AI-Infra-Guard (A.I.G)

Thanks for your interest in contributing! This guide covers the fastest path to a merged PR.

## Before you start

- Search [existing issues](https://github.com/Tencent/AI-Infra-Guard/issues) and [discussions](https://github.com/Tencent/AI-Infra-Guard/discussions) to avoid duplicates.
- For anything non-trivial (new scan module, breaking API change), open an issue first to discuss the approach before writing code.
- Issues labeled [`good first issue`](https://github.com/Tencent/AI-Infra-Guard/labels/good%20first%20issue) are a good place to start if you're new to the codebase.

## Local setup

```bash
git clone https://github.com/Tencent/AI-Infra-Guard.git
cd AI-Infra-Guard
# Build and run with Docker (fastest path)
docker-compose -f docker-compose.images.yml up -d
# Or build from source
go build ./cmd/...
```

See the [Quick Start](README.md#-quick-start) section in the README for full deployment options (Docker Compose, one-click script, or build-from-source), and [api.md](api.md) for the REST API reference.

## The four ways to contribute

A.I.G's plugin framework is designed so most contributions don't require touching Go/core code:

1. **Fingerprint rules** — add a new YAML fingerprint file under `data/fingerprints/` to help A.I.G recognize a new AI framework/component.
2. **Vulnerability rules** — add a new CVE/GHSA rule under `data/vuln/`.
3. **MCP security plugins** — add a new MCP risk-detection rule under `data/mcp/`.
4. **Jailbreak evaluation datasets** — add a new red-team dataset under `data/eval/`.

For each, please follow the existing file format/naming convention in that directory as a template, and briefly explain in your PR description what the new rule/dataset detects and how you validated it (e.g. a real target it correctly fingerprints, or a known CVE it correctly matches).

Core module changes (Go backend, frontend, scan engines) are welcome too — please open an issue first for anything beyond a small bugfix.

## Submitting a pull request

1. Fork the repo and create a branch from `main`.
2. Keep PRs focused — one logical change per PR is easier to review and merge.
3. Make sure `go build ./...` succeeds and existing tests still pass before opening the PR.
4. Fill in the PR template (auto-populated when you open a PR).
5. Link the issue your PR addresses, if any (`Fixes #123`).

## Response expectations

This is a small team maintaining an active project — we aim to triage new issues/PRs within a few days, but response time can vary. A polite ping after a week of silence is welcome; please avoid repeated pings within 48 hours.

## Code of Conduct

Please be respectful and constructive in all interactions — issues, PRs, discussions, and code review. We have zero tolerance for harassment or personal attacks. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Getting help

- Use [GitHub Discussions](https://github.com/Tencent/AI-Infra-Guard/discussions) for questions, usage help, and architecture discussions.
- Use [Issues](https://github.com/Tencent/AI-Infra-Guard/issues) for bug reports and feature requests.
- Security vulnerabilities: please follow [SECURITY.md](SECURITY.md) instead of filing a public issue.

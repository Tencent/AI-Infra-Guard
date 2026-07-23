# AI-Infra-Guard Web (A.I.G Web)

A.I.G Web is the web frontend of [Tencent/AI-Infra-Guard](https://github.com/Tencent/AI-Infra-Guard).
It provides a visual interface for AI infrastructure security assessment, Skill and MCP
service scanning, model red-teaming evaluation, and more.

## Features

- **AI-Infra Scan**: automatically identifies AI component versions and known vulnerabilities
- **MCP-Scan / Skill-Scan**: statically audits the security risks of MCP services and Agent Skills
- **Agent-Scan**: behavior and configuration auditing tailored for Agent scenarios
- **Model-Redteam / Jailbreak**: built-in local evaluation model for jailbreak assessments of LLMs
- **Full Chinese and English support** with 100% i18n coverage

## Tech Stack

- React 18 + TypeScript + Vite 6
- Tailwind CSS + shadcn/ui + Radix UI
- react-router v6, react-i18next v15

## Quick Start

```bash
# Install
pnpm install

# Local development (proxies to http://localhost:8088 by default)
pnpm dev

# Custom backend address
VITE_DEV_PROXY_TARGET=http://your-backend:8088 pnpm dev

# Production build
pnpm build         # output to dist/
```

## Directory Structure

```
├── src/
│   ├── components/     # Business components
│   ├── config/
│   │   ├── env.ts               # Environment constants (isDevelopment / isOpenSource)
│   │   └── privateModules.ts    # Private capability bridge layer (no-op stubs in open source)
│   ├── pages/          # Pages
│   ├── i18n/           # Internationalization
│   └── ...
├── public/             # Public assets and docs
└── vite.config.ts
```

## Architecture: Kernel + Overlay

This project follows an **"open-source kernel + private overlay"** architecture:

- `src/` is the complete open-source kernel that contains all runtime logic
- `src/config/privateModules.ts` is an interface layer that exposes optional capabilities
  (e.g. custom login page, internal partner list, "more features" entry, etc.).
  In the open-source build, all of these default to no-op values (`null` / `[]` / `false`)
- A private deployment can point this module to its own implementation via a vite alias,
  injecting internal-only functionality without ever needing environment checks
  (such as `isPro`) in the open-source code

This guarantees that **the open-source repository's source code = the actual capabilities
of the open-source product**, so reading the source is enough to audit it.

## Backend

You will need the companion backend service (Go version). See
[Tencent/AI-Infra-Guard](https://github.com/Tencent/AI-Infra-Guard).

## Contributing

Issues and PRs are welcome. Please read [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

This project is open-sourced under the [Apache License 2.0](./LICENSE).

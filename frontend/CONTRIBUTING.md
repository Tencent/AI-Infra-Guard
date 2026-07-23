# Contributing to AI-Infra-Guard Web

感谢你对本项目的关注！以下是一些参与贡献的指引。

## 开发环境

- Node.js >= 18
- pnpm >= 8

```bash
git clone https://github.com/Tencent/AI-Infra-Guard.git
cd AI-Infra-Guard/web
pnpm install
pnpm dev
```

## 代码规范

- 使用 TypeScript
- 遵循已有的组件目录结构（`src/components/**`）
- 通过 ESLint 检查：`pnpm lint`
- 提交前请自行运行 `pnpm build` 确保生产构建通过

## 提交信息

推荐使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
feat: 新增 XXX 功能
fix: 修复 XXX 问题
docs: 更新文档
refactor: 重构 XXX
```

## Pull Request

1. Fork 本仓库
2. 基于 `main` 创建功能分支：`feat/your-feature`
3. 完成开发并本地验证（lint + build）
4. 发起 PR，描述改动动机与测试情况

## 私有覆盖层（Private Overlay）

如果你在下游对本项目做了内部定制，**请勿**直接改 `src/config/privateModules.ts`
的默认实现，而是新增私有 `privateModules.ts` 并通过 vite alias 注入。详见 README。

## 报告安全漏洞

请通过 security@tencent.com 提交安全相关问题，**不要**直接公开在 issue 中。

# 环境配置说明

本项目支持多个环境配置，用于不同的部署场景。

## 环境类型

### 1. Development (开发环境)
- 默认环境
- 用于本地开发

### 2. Production (生产环境)
- 用于生产环境部署

### 3. OpenSource (开源环境)
- 用于开源版本部署

## 构建命令

```bash
# 构建生产环境
pnpm build

# 构建开源环境
pnpm build:openSource

# 开发环境
pnpm dev
```

## 环境变量

| 变量 | 说明 | 可选值 |
| --- | --- | --- |
| `VITE_APP_ENV` | 运行环境 | `development` / `openSource` |
| `VITE_ENABLE_EVAL_MODEL` | 是否显示"大模型安全体检 / 一键越狱"任务的"打分模型"选择器；不设置时默认跟随 `isOpenSource` | `TRUE` / `FALSE` |
| `VITE_ENABLE_WELCOME_ANIMATION` | 是否启用欢迎动画 | `TRUE` / 空 |
| `VITE_BASENAME` | 部署时的 base 路径 | 例如 `/` |

## 在代码中使用

```typescript
import { env, isOpenSource, enableEvalModel } from '@/config/env';

// 获取环境变量
console.log(env.VITE_APP_ENV);
console.log(env.VITE_BASENAME);

// 环境判断
if (isOpenSource) {
  // 开源环境逻辑
}

// 功能开关：打分模型
if (enableEvalModel) {
  // 展示"打分模型"选择器
}
```
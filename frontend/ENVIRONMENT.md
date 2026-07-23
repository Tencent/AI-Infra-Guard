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

## 在代码中使用

```typescript
import { env, isProduction, isOpenSource } from '@/config/env';

// 获取环境变量
console.log(env.VITE_APP_TITLE);
console.log(env.VITE_API_BASE_URL);

// 环境判断
if (isProduction) {
  // 生产环境逻辑
}

if (isOpenSource) {
  // 开源环境逻辑
}
```
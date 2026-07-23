# =============================================================================
# 开源版 Dockerfile（多阶段构建：node 打包 -> nginx 服务）
# =============================================================================

# ---- Stage 1: Build ----
FROM node:18-alpine AS builder

WORKDIR /app

# 安装 pnpm
RUN npm install -g pnpm@9

# 依赖缓存友好
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile || pnpm install

# 复制源码并构建
COPY . .
RUN pnpm build

# ---- Stage 2: Serve ----
FROM nginx:1.27-alpine

# 使用默认 nginx 配置模板；如需 SPA 路由 fallback，可挂载自定义 nginx.conf
COPY --from=builder /app/dist /usr/share/nginx/html

# SPA fallback 到 index.html
RUN printf 'server {\n\
  listen 80;\n\
  root /usr/share/nginx/html;\n\
  index index.html;\n\
  location / {\n\
    try_files $uri $uri/ /index.html;\n\
  }\n\
}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

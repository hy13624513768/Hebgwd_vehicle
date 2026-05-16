#!/bin/bash
# Sealos DevBox：Vue/Vite 前端入口（仅启动已构建的 dist，使用 vite preview）。
# 须在开发环境先执行：cd frontend && npm ci && npm run build
#
# 生产环境 API 地址：见 frontend/.env.production（VITE_API_BASE_URL）或 Docker build-arg。
# 公网示例见 deploy/urls.env.example。
#
# 监听端口：优先 PORT，否则 8080。绑定 0.0.0.0。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND_DIR="$ROOT/frontend"

if [ ! -d "$FRONTEND_DIR/dist" ]; then
  echo "[deploy/entrypoint-frontend] 未找到构建产物 frontend/dist，请先在 DevBox 内执行 npm run build" >&2
  exit 1
fi

cd "$FRONTEND_DIR"

PORT="${PORT:-8080}"
export NODE_ENV="${NODE_ENV:-production}"

exec npm run preview -- --host 0.0.0.0 --port "$PORT"

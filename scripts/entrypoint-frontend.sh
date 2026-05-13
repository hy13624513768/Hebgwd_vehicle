#!/bin/bash
# Sealos DevBox：Vue/Vite 前端入口（仅启动已构建的 dist，使用 vite preview）。
# 须在开发环境先执行：cd frontend && npm ci && npm run build
# 构建生产包时请设置：
#   VITE_API_BASE_URL=https://你的后端应用公网域名   （无尾斜杠；与后端分开部署时必填）
#   VITE_AMAP_KEY / VITE_AMAP_SECURITY_JSCODE      （地图页需要）
#
# 监听端口：优先 PORT，否则 8080。绑定 0.0.0.0。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND_DIR="$ROOT/frontend"

if [ ! -d "$FRONTEND_DIR/dist" ]; then
  echo "[entrypoint-frontend] 未找到构建产物 frontend/dist，请先在 DevBox 内执行 npm run build" >&2
  exit 1
fi

cd "$FRONTEND_DIR"

PORT="${PORT:-8080}"
export NODE_ENV="${NODE_ENV:-production}"

exec npm run preview -- --host 0.0.0.0 --port "$PORT"

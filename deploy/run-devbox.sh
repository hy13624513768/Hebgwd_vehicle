#!/usr/bin/env bash
# Sealos DevBox：同时启动后端（8000）与前端（8080，见 vite.config）。
# 前端通过 Vite 把 /api 代理到本机 8000；后端 .env 里 CORS_ORIGINS 需包含控制台分配的 HTTPS 前端域名。
# 用法：cd hebgwd_vehicle && bash deploy/run-devbox.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACK="$ROOT/backend"
FRONT="$ROOT/frontend"
PYTHON="$BACK/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python3 || true)"
fi

if [[ -z "$PYTHON" ]]; then
  echo "未找到 Python。请先安装 Python 3 并创建 backend/.venv。" >&2
  exit 1
fi

if [[ ! -f "$BACK/.env" ]]; then
  echo "请先复制 backend/.env.example 为 backend/.env 并填写 DATABASE_URL 等。" >&2
  exit 1
fi

echo "后端: http://0.0.0.0:8000  |  前端(Vite): http://0.0.0.0:8080"
echo "提示: 后端代码会自动重载；修改 backend/.env（尤其是 DATABASE_URL）后仍需重启进程，否则仍会连旧库、页面无数据。"
echo "Sealos 控制台请将公网入口映射到容器 8080；线上前端公网示例见 deploy/urls.env.example"
echo "若热更新失败，请在 frontend 目录复制 .env.development.local.example 为 .env.development.local"
echo ""

(cd "$BACK" && exec "$PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload) &
UV_PID=$!
trap 'kill "$UV_PID" 2>/dev/null || true' EXIT
(cd "$FRONT" && exec npm run dev)

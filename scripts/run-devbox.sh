#!/usr/bin/env bash
# Sealos DevBox：同时启动后端（8000）与前端（8080），通过控制台分配的 HTTPS 域名访问前端。
# 前端会把 /api 代理到本机 8000；后端 .env 里 CORS_ORIGINS 需包含该 HTTPS 域名。
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACK="$ROOT/backend"
FRONT="$ROOT/frontend"

if [[ ! -f "$BACK/.env" ]]; then
  echo "请先复制 backend/.env.example 为 backend/.env 并填写 DATABASE_URL 等。" >&2
  exit 1
fi

echo "后端: http://0.0.0.0:8000  |  前端(Vite): http://0.0.0.0:8080"
echo "提示: 修改 backend/.env（尤其是 DATABASE_URL）后必须重启后端进程，否则仍会连旧库、页面无数据。"
echo "Sealos 控制台请将公网入口映射到容器 8080；浏览器访问例如 https://fhlkzwzoizzu.sealosbja.site"
echo "若热更新失败，请在 frontend 目录复制 .env.development.local.example 为 .env.development.local"
echo ""

(cd "$BACK" && exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000) &
UV_PID=$!
trap 'kill "$UV_PID" 2>/dev/null || true' EXIT
(cd "$FRONT" && exec npm run dev)

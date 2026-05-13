#!/bin/bash
# Sealos 应用启动入口：在 backend 目录用虚拟环境里的 uvicorn 监听 0.0.0.0。
# 发版前请在 hebgwd_vehicle 下执行：bash scripts/prep-release-backend.sh（会创建 backend/.venv）。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
cd "$BACKEND"

PORT="${PORT:-8000}"

if [ ! -d ".venv" ]; then
  echo "[entrypoint] 未找到 backend/.venv。请在 DevBox 终端执行：cd hebgwd_vehicle && bash scripts/prep-release-backend.sh" >&2
  exit 1
fi

exec .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"

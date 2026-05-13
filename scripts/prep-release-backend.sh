#!/bin/bash
# 在点击 Sealos DevBox「发布版本」之前，在终端执行本脚本（见官方文档「准备应用程序」）。
# https://sealos.run/docs/guides/fundamentals/release
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

chmod +x "$ROOT/entrypoint.sh" 2>/dev/null || true

echo ">>> 创建/更新后端虚拟环境并安装依赖（requirements.txt）…"
cd "$ROOT/backend"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck source=/dev/null
. .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

echo ">>> 校验 entrypoint 能否找到解释器与 uvicorn…"
python -c "import uvicorn; print('uvicorn OK')"
echo ">>> 后端发布前准备完成。请勿将含密钥的 backend/.env 提交仓库；线上请在【应用管理】配置环境变量。"

#!/bin/bash
# 兼容旧文档路径：实际逻辑在 deploy/entrypoint-backend.sh
set -euo pipefail
exec "$(cd "$(dirname "$0")" && pwd)/deploy/entrypoint-backend.sh" "$@"

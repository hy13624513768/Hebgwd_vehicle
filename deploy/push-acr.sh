#!/usr/bin/env bash
# 构建并推送前后端镜像到阿里云容器镜像服务 ACR（华北2 北京）
# 用法：cd hebgwd_vehicle && bash deploy/push-acr.sh
# 变量见 .env.acr.example；也可在命令前 export 后执行。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f "${ROOT}/.env.acr" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT}/.env.acr"
  set +a
fi

ACR_REGISTRY="${ACR_REGISTRY:-registry.cn-beijing.aliyuncs.com}"
ACR_NAMESPACE="${ACR_NAMESPACE:-hebgwd}"
FRONTEND_REPO="${FRONTEND_REPO:-hebgwd_vehicle_frontend}"
BACKEND_REPO="${BACKEND_REPO:-hebgwd_vehicle_backend}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

FRONTEND_IMAGE="${ACR_REGISTRY}/${ACR_NAMESPACE}/${FRONTEND_REPO}:${IMAGE_TAG}"
BACKEND_IMAGE="${ACR_REGISTRY}/${ACR_NAMESPACE}/${BACKEND_REPO}:${IMAGE_TAG}"

if ! command -v docker >/dev/null 2>&1; then
  echo "未找到 docker 命令，请先安装 Docker 并确保当前用户可执行 docker。" >&2
  exit 1
fi

if [[ -z "${VITE_API_BASE_URL:-}" ]]; then
  echo "错误：未设置 VITE_API_BASE_URL。" >&2
  echo "前端打包会把接口根地址写进静态文件，请设为线上后端地址（无末尾 /），例如：" >&2
  echo "  export VITE_API_BASE_URL=https://你的后端域名" >&2
  echo "或在 ${ROOT}/.env.acr 中填写后重新执行。" >&2
  exit 1
fi

echo ">>> 构建后端: ${BACKEND_IMAGE}"
docker build -t "${BACKEND_IMAGE}" "${ROOT}/backend"

echo ">>> 构建前端: ${FRONTEND_IMAGE}"
docker build -t "${FRONTEND_IMAGE}" \
  --build-arg "VITE_API_BASE_URL=${VITE_API_BASE_URL}" \
  --build-arg "VITE_AMAP_KEY=${VITE_AMAP_KEY:-}" \
  --build-arg "VITE_AMAP_SECURITY_JSCODE=${VITE_AMAP_SECURITY_JSCODE:-}" \
  "${ROOT}/frontend"

echo ">>> 登录 ACR（用户名一般为阿里云主账号或 RAM 子账号全名；密码在控制台「访问凭证」或子账号密码）"
docker login "${ACR_REGISTRY}"

echo ">>> 推送后端"
docker push "${BACKEND_IMAGE}"

echo ">>> 推送前端"
docker push "${FRONTEND_IMAGE}"

echo "完成。镜像地址："
echo "  ${BACKEND_IMAGE}"
echo "  ${FRONTEND_IMAGE}"

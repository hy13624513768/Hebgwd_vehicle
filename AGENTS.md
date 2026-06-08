# AGENTS.md

## Cursor Cloud specific instructions

### 产品概览

哈尔滨工务段汽车管理信息系统：FastAPI 后端（`backend/`）+ Vue 3/Vite 前端（`frontend/`）。本地开发需 **PostgreSQL**、**后端 API（8000）**、**前端 Vite（8080）** 三个组件。

### PostgreSQL（必需）

本仓库无 `docker-compose`。Cloud VM 上通过 apt 安装 PostgreSQL 16：

```bash
sudo apt-get install -y postgresql postgresql-contrib
sudo pg_ctlcluster 16 main start
```

首次需创建库与用户（与 `backend/.env.example` 末尾注释一致，端口用默认 `5432`）：

```bash
sudo -u postgres psql -c "CREATE USER bus_test WITH PASSWORD 'bus_test_123' CREATEDB;"
sudo -u postgres psql -c "CREATE DATABASE bus_system_test OWNER bus_test;"
```

将 `backend/.env.example` 复制为 `backend/.env`，`DATABASE_URL` 设为：

`postgresql+psycopg2://bus_test:bus_test_123@127.0.0.1:5432/bus_system_test`

并确保 `CORS_ORIGINS` 包含 `http://127.0.0.1:8080` 与 `http://localhost:8080`。

### 依赖与 PATH

- 后端：`cd backend && pip install -r requirements.txt`（pip 脚本在 `$HOME/.local/bin`，运行 uvicorn 前 `export PATH="$HOME/.local/bin:$PATH"`）
- 前端：`cd frontend && npm install`

### 启动服务

分别在两个 tmux 会话中启动（不要用 update 脚本启动服务）：

```bash
# 终端 1 — 后端
export PATH="$HOME/.local/bin:$PATH"
cd backend && python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 终端 2 — 前端
cd frontend && npm run dev
```

也可使用 `bash deploy/run-devbox.sh`（需已配置 `backend/.env`）。

前端开发服务器端口 **8080**（见 `frontend/vite.config.ts`），`/api` 代理到 `127.0.0.1:8000`。

### 验证

- 健康检查：`curl http://127.0.0.1:8000/health`
- API 冒烟测试：`cd backend && python3 smoke_test.py`（需数据库已就绪）
- 默认管理员：`admin` / `Admin123!@#`（滑块验证码后登录）

### 已知事项

- `npm run build` 可能因既有 TypeScript 未使用变量报错（`AmapContainer.vue`、`RepairRecordsView.vue`）；`npm run dev` 不受影响。
- 地图功能需 `frontend/.env.local` 中配置 `VITE_AMAP_KEY` 与 `VITE_AMAP_SECURITY_JSCODE`（可选，非核心登录/工作台流程）。
- 智谱 OCR、中石油 95504 油卡同步为可选外部集成，无密钥时相关功能不可用。

### 参考文档

- `backend/README.md` — 后端配置与 API
- `frontend/README.md` — 前端开发
- `docs/deployment.md` — 生产/Sealos 部署

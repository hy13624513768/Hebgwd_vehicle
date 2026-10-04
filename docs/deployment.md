# 上线与环境区分说明

本文说明正式上线前建议完成的配置，以及如何区分**测试 / 预发 / 生产**等环境。代码层面已支持：

- **Sealos / DevBox 入口、运维脚本和部署环境模板均在 `deploy/`**：`entrypoint-backend.sh`、`entrypoint-frontend.sh`、`prep-release-backend.sh`（发版前准备）、`run-devbox.sh`（前后端同时开发）、`push-acr.sh`（构建推送镜像）、`.env.acr.example`、`urls.env.example`、`database.env.example`（内网/外网库地址说明）、`sealos-backend-production.env.example`
- 后端：`ENVIRONMENT`、`DEMO_SEEDING_ENABLED`、`CORS_ORIGINS`（见 `backend/.env.example`）
- 前端：`VITE_API_BASE_URL`、`VITE_APP_ENV`、高德 Key（见 `frontend/.env.example`）
- 存活检查：`GET /health`；数据库就绪检查：`GET /ready`

---

## 环境如何区分（推荐做法）


| 环境              | 用途              | 典型做法                                              |
| --------------- | --------------- | ------------------------------------------------- |
| **development** | 本机开发            | 后端 `.env` 指向本地库；前端 `.env.local`，API 走 Vite 代理     |
| **test**        | 自动化测试 / CI      | 独立数据库与 `.env`，`ENVIRONMENT=test`                  |
| **staging**     | 联调、验收           | 独立服务器 + 独立数据库，`ENVIRONMENT=staging`               |
| **preprod**     | 预发（与生产同配置、数据隔离） | 独立服务器 + 独立数据库，`ENVIRONMENT=preprod`，尽量与生产一致       |
| **production**  | 正式运营            | 独立服务器 + 独立数据库，`ENVIRONMENT=production`，**关闭演示数据** |


要点：**每个环境一套数据库 + 一套 `.env`，不要用同一库挂多套前端。**  
域名也分开（例如 `api-test.`、`api-pre.`、`api.`），便于 `CORS_ORIGINS` 与白名单管理。

---

## 正式上线前建议清单

### 1. 后端（必做）

- **数据库**：生产库账号最小权限；备份与恢复演练。
- `**JWT_SECRET`**：改为足够长的随机串，勿与测试环境共用。
- `**CORS_ORIGINS**`：仅填写真实前端 HTTPS 地址（多个用英文逗号分隔）。
- `**DEMO_SEEDING_ENABLED=false**`：避免写入演示车辆、`fleet_mgr` / `driver1` / `staff1` 等演示账号。
- `**BOOTSTRAP_ADMIN_PASSWORD**`：首次上线后可改为强密码，或通过后台改密（勿长期使用示例密码）。
- `MEDIA_STORAGE_BACKEND=s3`：生产媒体必须写入私有 S3 兼容对象存储；同时配置 `S3_ENDPOINT`、凭据与 `S3_BUCKET`。
- **进程**：生产不要用 `--reload`；使用 `uvicorn` + 进程管理（systemd、NSSM、Docker 等），前置 **HTTPS**（Nginx / Caddy）。
- **初始化**：生产 API Pod 设置 `AUTO_DB_INIT=false`；发布时先用同一后端镜像运行一次 `python -m app.db.bootstrap`，成功后再滚动 API Pod。
- **连接池**：按数据库连接上限和 API 副本数设置 `DATABASE_POOL_SIZE` / `DATABASE_MAX_OVERFLOW`；默认单 Pod 最大 20 个连接。
- **运维**：监控 `/health`；日志落盘或接入日志平台。

### 2. 前端（必做）

- **构建**：`npm run build`，将 `dist/` 交给 Nginx 或静态托管。
- `**VITE_API_BASE_URL`**：若前端与 API **不同域名**，构建前设为后端根地址（无尾斜杠），例如 `https://api.example.com`。
- **高德**：控制台配置 Key 的 **域名白名单**（生产前端域名）；`.env.production` 或 CI 注入 `VITE_AMAP_KEY` / `VITE_AMAP_SECURITY_JSCODE`。
- **同源部署**：若 Nginx 把 `/api` 反代到后端，可不设 `VITE_API_BASE_URL`，保持默认相对路径即可。

### 3. 「只开通部分功能」

当前权限主要来自**角色与菜单项上的 `need` 字段**（如报表需 `reports` 权限）。上线后可：

- 仅向运营人员开通管理员/车管账号；
- 不为普通用户分配导出报表等权限；
- 需要「按环境隐藏菜单」时，再单独做特性开关（ env 或后端配置），本次未强制绑定环境。

### 4. 我无法替你远程完成的项

以下需在你们的**服务器、DNS、数据库、高德控制台、证书**上操作，我无法直接代操作：

- 购买/备案域名、申请 HTTPS 证书  
- 创建生产 PostgreSQL、防火墙与安全组  
- 在云平台配置流水线与环境变量

---

## 本地快速对照：生产 `.env` 示例片段

**后端 `backend/.env`（生产要点）**

```env
ENVIRONMENT=production
DEMO_SEEDING_ENABLED=false
JWT_SECRET=<随机长串>
CORS_ORIGINS=https://你的前端域名
DATABASE_URL=postgresql+psycopg2://...
```

**前端构建（不同域 API 时）**

```bash
set VITE_API_BASE_URL=https://你的API域名
npm run build
```

更多字段说明见仓库内 `backend/.env.example` 与 `frontend/.env.example`。

---

## Sealos 部署：PostgreSQL 连接（集群内网）

后端 Pod 与数据库应用在**同一 Kubernetes 集群**时，**日常必须使用集群内 DNS**，不要用 `dbconn.sealosbja.site` 外网地址。外网仅用于 DevBox 执行一次性数据迁移（见 `deploy/database.env.example`）。

| 环境 | 内网主机（Service） | 库名 |
| --- | --- | --- |
| **开发** | `hebgwd-fullstack-db-postgresql.ns-1ht608x0.svc:5432` | `hebgwd_development` |
| **生产** | 部署时填写独立生产数据库 Service | 部署时填写 |

开发 `DATABASE_URL` 示例（写入 `backend/.env` 或开发后端应用环境变量）：

```env
ENVIRONMENT=development
DATABASE_URL=postgresql+psycopg2://postgres:<开发库密码>@hebgwd-fullstack-db-postgresql.ns-1ht608x0.svc:5432/hebgwd_development
```

生产 `DATABASE_URL` 示例（写入 Sealos **生产后端**应用环境变量，模板见 `deploy/sealos-backend-production.env.example`）：

```env
ENVIRONMENT=production
DATABASE_URL=postgresql+psycopg2://postgres:<生产库密码>@PRODUCTION_DB_HOST:5432/PRODUCTION_DB_NAME
```

**数据迁移（开发库 → 生产库，仅执行迁移时）**：

```bash
# 外网地址见 deploy/database.env.example
export DEV_DATABASE_URL="postgresql://postgres:<密码>@DEVELOPMENT_PUBLIC_HOST:PORT/hebgwd_development"
export PROD_DATABASE_URL="postgresql://postgres:<密码>@PRODUCTION_PUBLIC_HOST:PORT/PRODUCTION_DB_NAME"
cd hebgwd_vehicle/backend && .venv/bin/python scripts/migrate_dev_db_to_prod.py
```

迁移完成后，开发与生产后端均应只使用上表中的**内网** `DATABASE_URL`。

---

## Sealos 部署：用 Docker 镜像跑后端与前端（推荐）

仓库已提供：

- `backend/Dockerfile`：FastAPI + Uvicorn，监听 **8000**
- `frontend/Dockerfile`：构建 Vue 后用 **Nginx** 提供静态页，监听 **80**

本地构建示例（构建完成后将镜像推送到 Sealos / 任意镜像仓库，再在控制台创建应用）：

```bash
# 后端（镜像名请改成你自己的命名空间）
docker build -t your-registry/hebgwd-backend:latest ./backend

# 前端：必须传入后端「公网」根地址（无尾斜杠），与浏览器访问 API 的域名一致
docker build -t your-registry/hebgwd-frontend:latest \
  --build-arg VITE_API_BASE_URL=https://你的后端Sealos公网地址 \
  ./frontend
```

在 **Sealos 应用市场 / 容器部署** 中建议拆成 **两个应用**：

### 应用 A：后端 API

| 配置项 | 说明 |
| --- | --- |
| 镜像 | 上述 `hebgwd-backend` |
| 容器端口 | `8000` |
| 对外暴露 | 开启 HTTPS 公网访问，记下例如 `https://xxxx.sealosbja.site` |
| 环境变量 | 见下表（与 `backend/.env.example` 一致，勿把密码写进镜像） |

**后端环境变量（在 Sealos 控制台填写）**

| 变量名 | 说明 |
| --- | --- |
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | 生产内网：`postgresql+psycopg2://postgres:<密码>@PRODUCTION_DB_HOST:5432/PRODUCTION_DB_NAME` |
| `AUTO_DB_INIT` | `false`；数据库初始化交给独占 initContainer/Job |
| `DATABASE_POOL_SIZE` / `DATABASE_MAX_OVERFLOW` | 默认 `10` / `10`；总上限按 API Pod 数累加 |
| `DATABASE_STATEMENT_TIMEOUT_MS` | 默认 `30000`，阻止失控查询长期占用连接 |
| `JWT_SECRET` | 随机长串 |
| `JWT_EXPIRE_MINUTES` | 如 `120` |
| `CORS_ORIGINS` | 前端公网 Origin，如 `https://xwyommoychvz.sealosbja.site`（多个用英文逗号；可与 `deploy/urls.env.example` 对齐） |
| `DEMO_SEEDING_ENABLED` | 生产建议 `false` |
| `KUNLUN_BALANCE_SCRIPT` | 生产固定为 `/app/kunlun/获取油卡余额.py`；脚本、登录模块和种子配置由 initContainer 写入云端 `emptyDir`，其中 `token.json` 必须允许 API 用户写回刷新后的令牌 |
| `MEDIA_STORAGE_BACKEND` | 生产固定为 `s3`；`local` 仅供本机开发 |
| `S3_ENDPOINT` / `S3_BUCKET` | 私有 S3 兼容端点与桶；建议桶名 `hebgwd-vehicle-assets` |
| `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` | 通过 Sealos Secret 注入，禁止写入镜像或仓库 |
| `BOOTSTRAP_ADMIN_USERNAME` / `BOOTSTRAP_ADMIN_PASSWORD` / `BOOTSTRAP_ADMIN_DISPLAY_NAME` | 按需 |

Pydantic 会读取这些环境变量（与 `.env` 同名）；**无需**在镜像里拷贝 `.env` 文件。生产配置若仍启用自动初始化、SQLite、演示数据、弱 JWT、默认管理员密码或本地媒体目录，应用会直接拒绝启动。

首次上线先保持 **1 个后端副本**完成容量观察。当前认证无进程内会话、媒体走共享私有 S3，后续可以横向扩容；扩容前需要核算 PostgreSQL 总连接数。

### 应用 B：前端静态站点

| 配置项 | 说明 |
| --- | --- |
| 镜像 | 上述 `hebgwd-frontend`（构建时已写入 `VITE_API_BASE_URL` 指向后端公网地址） |
| 容器端口 | `80` |
| 对外暴露 | 前端域名，如 `https://xwyommoychvz.sealosbja.site` |

**顺序**：先部署后端并确认 `GET https://后端公网/health` 正常，再用该后端地址构建前端镜像并部署前端。若后端域名变更，需**重新构建**前端镜像并更新 `VITE_API_BASE_URL`。

推荐的生产发布顺序：

1. 使用不可变标签构建并推送两张镜像（`deploy/push-acr.sh` 默认生成“UTC 时间 + Git 短哈希”标签，拒绝 `latest`）。
2. 在 Sealos 创建独立生产 PostgreSQL 和私有对象存储桶；后端只使用同工作区内网数据库地址。
3. 用后端镜像创建一次性 Job/initContainer，命令为 `python -m app.db.bootstrap`；等待退出码 0。
4. 部署后端 Deployment：`AUTO_DB_INIT=false`，存活探针 `/health`，就绪探针 `/ready`，端口 `8000`。
5. 验证 `/ready` 返回 200 后，再以实际 API HTTPS 地址构建并部署前端，端口 `80`。
6. 做登录、权限边界、数据库写入、媒体上传/下载和重启后持久性冒烟测试，再切换正式域名。

Sealos 工作负载建议：后端初始 `500m CPU / 512Mi`、前端 `200m CPU / 256Mi`；requests 按 Sealos 资源阶梯分别设为 `50m / 51Mi` 与 `20m / 25Mi`。后端上传入口的 Ingress `proxy-body-size` 不得小于 `MAX_UPLOAD_MB`。

### 高德地图

前端需在构建镜像时传入（或在 Sealos 构建参数里配置）：

- `VITE_AMAP_KEY`
- `VITE_AMAP_SECURITY_JSCODE`

`frontend/Dockerfile` 已声明相应的 `ARG` / `ENV`。使用 ACR 发布脚本时，复制
`deploy/.env.acr.example` 为被 Git 忽略的 `deploy/.env.acr`，填写两项并重新构建、推送、部署前端镜像。
仅在已构建容器的运行环境中添加 `VITE_*` 变量不会改变静态文件。Key 必须是“Web 端（JS API）”类型，
安全密钥必须与该 Key 属于同一条控制台配置；域名白名单还需覆盖浏览器地址栏中的实际前端域名。

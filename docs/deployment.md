# 上线与环境区分说明

本文说明正式上线前建议完成的配置，以及如何区分**测试 / 预发 / 生产**等环境。代码层面已支持：

- 后端：`ENVIRONMENT`、`DEMO_SEEDING_ENABLED`、`CORS_ORIGINS`（见 `backend/.env.example`）
- 前端：`VITE_API_BASE_URL`、`VITE_APP_ENV`、高德 Key（见 `frontend/.env.example`）
- 健康检查：`GET /health` 返回 `environment` 字段

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
- **进程**：生产不要用 `--reload`；使用 `uvicorn` + 进程管理（systemd、NSSM、Docker 等），前置 **HTTPS**（Nginx / Caddy）。
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
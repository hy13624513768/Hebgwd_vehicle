# Vue3 前端（哈尔滨工务段汽车管理信息系统）

## 安装与启动

```powershell
Set-Location "E:\VS_code\project\公车系统\系统复现\frontend"
npm install
npm run dev
```

开发服务器监听 **`0.0.0.0:8080`**（与 **Sealos DevBox** 对外映射常用端口一致），并通过 Vite 将 **`/api`** 代理到本机 **`http://127.0.0.1:8000`**。

### Sealos DevBox + 公网 HTTPS（如 `https://fhlkzwzoizzu.sealosbja.site`）

1. 在 Sealos 控制台把 DevBox 的 **预览 / 外网访问** 指向容器 **8080**（与上述 Vite 端口一致）。
2. 后端 `backend/.env` 里 **`CORS_ORIGINS`** 须包含该 HTTPS 地址（无尾斜杠）。
3. 若经公网访问时 **热更新（HMR）不工作**，将 `frontend/.env.development.local.example` 复制为 **`frontend/.env.development.local`**，并设置  
   `SEALOS_DEV_PUBLIC_HOST=fhlkzwzoizzu.sealosbja.site`（仅主机名，不要写 `https://`）。
4. 仓库根目录提供一并启动脚本：`bash scripts/run-devbox.sh`（需先有 `backend/.env`）。

## 构建

```powershell
npm run build
npm run preview
```

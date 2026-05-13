# FastAPI 后端（哈尔滨工务段汽车管理信息系统）

## 环境

建议使用已创建的 Conda 环境：`D:\miniconda\envs\bus_fastapi_vue3`

## 配置

将 `backend/.env.example` 复制为 `backend/.env` 并按需修改数据库连接与 `JWT_SECRET`。  
默认示例指向 **Sealos 集群内 PostgreSQL**；本地开发请改用 `.env.example` 末尾注释中的 `127.0.0.1:55432`（或你的本机/Docker 端口）。

**正式上线、多环境（测试/预发/生产）配置要点**见仓库根目录 `docs/deployment.md`。

## 启动

在 `backend` 目录执行：

```powershell
Set-Location "E:\VS_code\project\公车系统\系统复现\backend"
& "D:\miniconda\envs\bus_fastapi_vue3\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 从桌面 Excel 导入真实台账（初始数据）

将多个台账 `.xlsx` 放在同一目录（默认 `C:\Users\HY\Desktop\数据`）。文件名需能被关键词识别：


| 关键词（文件名含）   | 导入目标                                       |
| ----------- | ------------------------------------------ |
| `明细`        | 公务用车明细 → `bus_vehicle`                     |
| `年检` / `审验` | 年检台账 → `bus_maintenance`（类别：年检）            |
| `维修` / `维保` | 维修保养 → `bus_maintenance`（类别：维修）            |
| `保险`        | 保险台账 → `bus_expense`（类别：保险费）               |
| `燃油` / `油费` | 燃油统计 → `bus_fuel_card` + `bus_fuel_record` |
| `停车` / `过路` | 停车过路 → `bus_expense`（类别：停车路桥费）             |


1. 安装依赖：`pip install -r requirements.txt`（含 `openpyxl`）。
2. **先启动一次后端**（或单独运行迁移），确保数据库已创建且 `bus_vehicle` 等表存在；启动时会自动执行运行时迁移，为车辆表补齐 Excel 扩展字段。
3. 导入（`**--clear` 会清空车辆/驾驶员/申请/维保/油卡/加油/费用等业务表，不删用户**）：

```powershell
Set-Location "E:\VS_code\project\公车系统\系统复现\backend"
python scripts/import_real_excel.py --clear
# 或指定目录、仅试跑：
python scripts/import_real_excel.py --dir "C:\Users\HY\Desktop\数据" --dry-run
```

导入后 `seed_demo_if_empty` 因车辆表非空不会再写入演示数据。

### 油卡卡号主数据（`卡号.xlsx` 的 B/C/D 列）

卡号单独落在表 `**bus_fuel_card_number**`（ORM：`FuelCardNumber`）；默认还会按卡号 **同步/新建** `bus_fuel_card` 的「发行方」「持卡人」（来自 C、D 列），**不改动已有油卡余额**。

默认 Excel 路径：`D:\Desktop\获取油卡余额\卡号.xlsx`。请先启动过一次后端（或确保库表已 `create_all`）。

```powershell
Set-Location "E:\VS_code\project\公车系统\系统复现\backend"
python scripts/import_fuel_card_numbers_from_excel.py
python scripts/import_fuel_card_numbers_from_excel.py --dry-run
python scripts/import_fuel_card_numbers_from_excel.py --file "D:\Desktop\获取油卡余额\卡号.xlsx" --no-sync-cards
```

### 仅补写车辆「注册登记时间」`registered_at`（不新增车辆）

明细表头在第 1 行、登记时间在 O 列等场景，可用：

```powershell
python scripts/import_real_excel.py --dir "C:\Users\HY\Desktop\数据" --backfill-registration
# 先试跑：加 --dry-run
```

### 导出 `bus_vehicle` 表结构 + 全表 CSV（本地查看）

输出目录默认 `backend/exports/`（已在仓库 `.gitignore` 中忽略，勿提交敏感数据）：

```powershell
python scripts/export_bus_vehicle.py
python scripts/export_bus_vehicle.py --out "D:\exports"
```

## 默认账号

首次启动会在数据库中自动创建管理员（若不存在）：

- 用户名：`admin`
- 密码：`Admin123!@#`（满足原系统的密码复杂度规则）

## 业务模块 API（均需登录 Bearer）

- `GET /api/v1/dashboard/summary`：工作台统计与最近申请
- `GET|POST|PATCH|DELETE /api/v1/vehicles`：车辆档案
- `GET|POST|PATCH|DELETE /api/v1/drivers`：驾驶员档案
- `GET|POST|PATCH|DELETE /api/v1/trip-requests`：用车申请
- `GET|POST|PATCH|DELETE /api/v1/maintenance-records`：维保记录

首次空库会自动写入少量演示数据（车辆/驾驶员/申请/维保/油卡/费用），便于联调体验。

## 角色与演示账号


| 用户名         | 密码                | 角色   | 说明              |
| ----------- | ----------------- | ---- | --------------- |
| `admin`     | `Admin123!@#`     | 管理员  | 首次启动自动创建        |
| `fleet_mgr` | `FleetMgr123!@#`  | 车管   | 与管理员相同的车队管理权限   |
| `driver1`   | `DriverUsr123!@#` | 驾驶员  | 演示数据中会绑定驾驶员「张三」 |
| `staff1`    | `StaffUsr123!@#`  | 普通用户 | 仅可管理本人提交的用车申请   |


权限要点：

- **管理员 / 车管**：车辆、驾驶员、维保、油卡、费用、派车与删除申请、**CSV 报表导出**。
- **驾驶员**：查看与本人相关的申请；可将指派给自己的任务状态改为执行中/已完成/等。
- **普通用户**：新建申请；仅待审批时可修改本人申请的基础信息；不可指定车辆/驾驶员。

## 油卡 / 费用 / 报表

- `GET/POST/PATCH/DELETE /api/v1/fuel/cards` 与 `GET/POST/DELETE /api/v1/fuel/records`（加油会从油卡余额扣减，删除流水会回滚余额）
- `GET /api/v1/fuel/records` 返回分页 JSON：`{ "items": [...], "total": N }`，查询参数含 `page`、`page_size`（默认 1 / 20，最大 100），以及可选 `card_id`、`vehicle_id`、`date_from`、`date_to`、`station`（站点模糊匹配）
- `GET/POST/PATCH/DELETE /api/v1/expenses`
- `GET /api/v1/reports/export/*.csv`（UTF-8 BOM，便于 Excel 打开）

数据库若由旧版本升级而来，启动时会自动尝试补齐 `sys_user.role` 与 `bus_driver.user_id` 字段。
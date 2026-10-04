# 开发数据库结构

Sealos 数据库实例为 `hebgwd-fullstack-db`，应用使用的 PostgreSQL 逻辑数据库为
`hebgwd_development`。业务表不再放在 `public`，而是按职责划分到以下 schema：

| Schema | 职责 | 表 |
| --- | --- | --- |
| `access_control` | 账号与权限 | `users` |
| `fleet_management` | 车辆基础数据 | `workshops`、`vehicles`、`drivers` |
| `dispatch_management` | 用车和调度 | `trip_requests` |
| `maintenance_management` | 维保和维修结算 | `maintenance_records`、`maintenance_terms`、`repair_records`、`repair_settlements`、`repair_settlement_lines` |
| `fuel_management` | 燃油业务 | `fuel_cards`、`fuel_card_lookups`、`fuel_records`、`fuel_entries`、`fuel_balances`、`fuel_sync_logs` |
| `navigation_management` | 地图导航 | `nav_presets`、`nav_preset_operation_logs` |
| `media_management` | 私有媒体元数据与审计 | `media_assets` |

后端连接会配置包含这些 schema 的 PostgreSQL `search_path`，因此 ORM 和 API 使用方式不变。
启动迁移会自动创建缺失 schema，并把历史 `public` 表移动到正确位置；真实密码只存放在
未提交的 `backend/.env` 或 Sealos 环境变量中。

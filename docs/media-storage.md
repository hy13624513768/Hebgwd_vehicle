# 生产媒体存储设计

## 边界

- PostgreSQL 保存车辆、里程、时间、维修单、识别结果等结构化数据。
- `media_management.media_assets` 保存媒体归属、对象键、MIME、大小、SHA-256、创建人和审计时间。
- 图片和视频二进制保存在私有 S3 兼容对象存储；数据库不保存大对象，也不保存永久公网 URL。
- 业务表中的 `photo_*_path` / `photo_path` 以及驾驶员的 `health_check_report` / `outsourcing_onboarding` 保存不可猜测的 `media://` 引用，用于兼容现有数据结构。

## 访问链路

上传由后端验证登录身份、车辆数据范围、扩展名、MIME、文件签名和大小后写入对象存储。下载先经过业务记录权限校验，再返回 5 分钟有效的预签名地址；桶必须保持 `private`。

对象键按业务、记录、媒体类型和年月分层，例如：

```text
repair/records/128/settlement_photo/2026/09/<uuid>.jpg
fuel/entries/36/2026/09/<uuid>.jpg
drivers/52/health_check_report/2026/09/<uuid>.jpg
drivers/52/outsourcing_onboarding/2026/09/<uuid>.webp
```

## 驾驶员档案图片接口

- `POST /api/v1/drivers/{driver_id}/documents/{kind}`：上传或替换图片，multipart 字段名为 `file`。
- `GET /api/v1/drivers/{driver_id}/documents/{kind}`：鉴权后读取图片；S3 环境返回短期预签名跳转。
- `DELETE /api/v1/drivers/{driver_id}/documents/{kind}`：解除业务引用并清理对象。
- `kind` 仅允许 `health_check_report`、`outsourcing_onboarding`。
- 仅接受经过扩展名、MIME 和文件签名共同校验的 JPG、PNG、WebP；沿用全局 `MAX_UPLOAD_MB` 限制。
- `DriverOut` 仅返回 `has_health_check_report`、`has_outsourcing_onboarding` 状态，不向前端暴露 `media://` 对象键。
- 替换采用“新对象写入并提交新引用 → 清理旧对象”的顺序。旧对象删除失败时保留 `media_assets` 元数据，供后续对账任务重试。

## 一致性与运维

- 上传成功但数据库事务失败时，接口会尽力删除刚写入的对象。
- 对象存储需启用服务端加密、版本控制、跨可用区冗余、访问日志和生命周期规则。
- 数据库与桶应分别备份，并定期通过 `media_assets.object_key` 做孤儿对象/缺失对象对账。
- 生产环境启动校验会拒绝 `local` 媒体后端或不完整的 S3 配置，避免多副本部署时文件丢失。
- `/ready` 同时检查数据库和媒体桶可达性；任一关键依赖不可用都会返回 503。
- 当前上传经过应用服务器，适合现有限额。大视频下一阶段应改为“后端签发短期上传凭证 → 客户端直传 → 回调确认”，并增加病毒扫描、转码、缩略图及异步任务队列。
- 后续 AI 或维护人员接手时，应优先复用 `MediaAsset` 与 `media_storage_service`，不要在驾驶员表中写入 base64、公开 URL 或服务器绝对路径。正式发布前必须在真实私有桶完成上传、鉴权下载、替换、删除和孤儿对账演练。

## Sealos 配置

建议使用私有桶 `hebgwd-vehicle-assets`，在生产应用中配置 `S3_ENDPOINT`、`S3_ACCESS_KEY_ID`、`S3_SECRET_ACCESS_KEY`、`S3_BUCKET`、`S3_REGION=us-east-1` 和 `S3_FORCE_PATH_STYLE=true`。密钥只进入 Sealos Secret/环境变量，不写入仓库。

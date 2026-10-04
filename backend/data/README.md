# 本地开发数据库

本目录用于存放本地开发演示数据库。默认文件为 `local-dev.db`，由后端首次启动时自动创建并写入演示数据。

数据库文件及其 WAL/SHM 临时文件已被 Git 忽略，不会提交到仓库。需要重置演示数据时，停止后端后删除 `local-dev.db`，再重新启动后端即可。

如需从线上开发 PostgreSQL 刷新本地数据，请在 `backend` 目录临时设置 `SOURCE_DATABASE_URL` 后运行 `python scripts/sync_online_to_local.py --reset-local-admin`。连接串不得写入仓库；同步得到的数据库含真实业务数据，应仅保存在受控的开发电脑上。

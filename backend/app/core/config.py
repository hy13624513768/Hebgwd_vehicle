from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    """运行环境标识：development / test / staging / preprod / production（用于日志与健康检查展示，请与各部署环境的 .env 对应）"""
    environment: str = "development"

    # 默认：当前 Devbox 开发库的集群内网 Service。
    database_url: str = (
        "postgresql+psycopg2://postgres:CHANGE_ME@hebgwd-fullstack-db-postgresql.ns-1ht608x0.svc:5432/hebgwd_development"
    )
    database_pool_size: int = Field(default=10, ge=1, le=50)
    database_max_overflow: int = Field(default=10, ge=0, le=100)
    database_pool_timeout_seconds: int = Field(default=30, ge=1, le=120)
    database_pool_recycle_seconds: int = Field(default=1800, ge=60, le=86400)
    database_connect_timeout_seconds: int = Field(default=10, ge=1, le=60)
    database_statement_timeout_ms: int = Field(default=30000, ge=1000, le=300000)
    database_idle_transaction_timeout_ms: int = Field(default=60000, ge=1000, le=600000)
    auto_db_init: bool = True
    jwt_secret: str = "change-me"
    jwt_expire_minutes: int = 120
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"

    bootstrap_admin_username: str = "admin"
    bootstrap_admin_password: str = "Admin123!@#"
    bootstrap_admin_display_name: str = "系统管理员"

    """
    是否写入演示数据（车辆/流水等）、标准演示账号（fleet_mgr/driver1/staff1）及驾驶员绑定。
    正式上线请务必设为 false，仅保留 BOOTSTRAP_ADMIN_* 首次创建管理员。
    """
    demo_seeding_enabled: bool = True

    zhipu_api_key: str = ""
    kunlun_balance_script: str = ""
    max_upload_mb: int = Field(default=50, gt=0)
    zhipu_model: str = "glm-4.6v"
    zhipu_api_base: str = "https://open.bigmodel.cn/api/paas/v4"

    upload_dir: str = "uploads"
    repair_upload_subdir: str = "repair"
    media_storage_backend: str = "local"
    s3_endpoint: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_bucket: str = ""
    s3_region: str = "us-east-1"
    s3_force_path_style: bool = True
    s3_presign_expire_seconds: int = Field(default=300, ge=60, le=3600)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def validate_deployment_safety(self) -> "Settings":
        if self.environment.lower() != "production":
            return self
        if self.database_url.startswith("sqlite"):
            raise ValueError("生产环境不能使用 SQLite，请配置外部 PostgreSQL DATABASE_URL")
        if self.auto_db_init:
            raise ValueError("生产环境必须设置 AUTO_DB_INIT=false，并由部署 initContainer/Job 独占执行数据库初始化")
        if self.demo_seeding_enabled:
            raise ValueError("生产环境必须设置 DEMO_SEEDING_ENABLED=false")
        if self.jwt_secret in {"change-me", "change-me-to-a-long-random-string"} or len(self.jwt_secret) < 32:
            raise ValueError("生产环境 JWT_SECRET 必须设置为至少 32 个字符的随机值")
        if self.bootstrap_admin_password in {"Admin123!@#", "CHANGE_ME"}:
            raise ValueError("生产环境必须修改 BOOTSTRAP_ADMIN_PASSWORD")
        if self.media_storage_backend.lower() != "s3":
            raise ValueError("生产环境媒体文件必须使用 S3 对象存储")
        if not all((self.s3_endpoint, self.s3_access_key_id, self.s3_secret_access_key, self.s3_bucket)):
            raise ValueError("生产环境必须完整配置 S3_ENDPOINT、S3_ACCESS_KEY_ID、S3_SECRET_ACCESS_KEY、S3_BUCKET")
        return self


settings = Settings()

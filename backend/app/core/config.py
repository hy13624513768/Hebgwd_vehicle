from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    """运行环境标识：development / test / staging / preprod / production（用于日志与健康检查展示，请与各部署环境的 .env 对应）"""
    environment: str = "development"

    database_url: str = "postgresql+psycopg2://bus_test:bus_test_123@127.0.0.1:55432/bus_system_test"
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

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

"""开发数据库的业务 schema 与表归属。"""

SCHEMA_TABLES: dict[str, tuple[str, ...]] = {
    "access_control": ("users",),
    "fleet_management": ("workshops", "vehicles", "drivers"),
    "dispatch_management": ("trip_requests",),
    "maintenance_management": (
        "maintenance_records",
        "maintenance_terms",
        "repair_records",
        "repair_settlements",
        "repair_settlement_lines",
    ),
    "fuel_management": (
        "fuel_cards",
        "fuel_card_lookups",
        "fuel_records",
        "fuel_entries",
        "fuel_balances",
        "fuel_sync_logs",
    ),
    "navigation_management": ("nav_presets", "nav_preset_operation_logs"),
    "media_management": ("media_assets",),
}

TABLE_SCHEMAS = {
    table: schema
    for schema, tables in SCHEMA_TABLES.items()
    for table in tables
}

# public 放在首位，使新空库先由 SQLAlchemy 建表，再由迁移原地归类；运行时仍能跨 schema 查询。
POSTGRES_SEARCH_PATH = ("public", *SCHEMA_TABLES.keys())
POSTGRES_SEARCH_PATH_OPTION = ",".join(POSTGRES_SEARCH_PATH)

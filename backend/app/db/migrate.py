"""启动仅执行可重入的加列迁移；不删除旧数据、不改写角色或业务归属。

旧字段转换和历史清理应在备份后通过单独的数据迁移流程执行。
"""
from sqlalchemy import inspect, text
from app.db.session import engine
from app.db.structure import SCHEMA_TABLES, TABLE_SCHEMAS

# 旧版表名 -> 统一后的业务表名。重命名会保留原表数据、序列、索引和外键关系。
TABLE_RENAMES = {
    "sys_user": "users",
    "bus_workshop": "workshops",
    "bus_vehicle": "vehicles",
    "bus_driver": "drivers",
    "bus_trip_request": "trip_requests",
    "bus_maintenance": "maintenance_records",
    "bus_maintenance_term": "maintenance_terms",
    "bus_fuel_card": "fuel_cards",
    "bus_fuel_card_lookup": "fuel_card_lookups",
    "bus_fuel_record": "fuel_records",
    "bus_fuel_balance": "fuel_balances",
    "bus_fuel_sync_log": "fuel_sync_logs",
    "bus_nav_preset": "nav_presets",
    "bus_nav_preset_op_log": "nav_preset_operation_logs",
    "bus_repair_record": "repair_records",
    "bus_repair_settlement": "repair_settlements",
    "bus_repair_settlement_line": "repair_settlement_lines",
}

# 固定标识符，禁止接受外部输入作为 DDL。
ADDITIONS = {
    "users": {"role": "VARCHAR(32) NOT NULL DEFAULT 'staff'", "workshop_id": "INTEGER NULL REFERENCES workshops(id)"},
    "drivers": {
        "user_id": "INTEGER NULL REFERENCES users(id)", "workshop_id": "INTEGER NULL REFERENCES workshops(id)",
        "sort_no": "INTEGER NULL", "id_card": "VARCHAR(32) NULL", "health_check_report": "TEXT NULL",
        "outsourcing_onboarding": "TEXT NULL", "first_hire_date": "DATE NULL",
        "vehicle_type_label": "VARCHAR(64) NOT NULL DEFAULT ''",
    },
    "vehicles": {
        "org_unit": "VARCHAR(128) NOT NULL DEFAULT ''", "workshop_id": "INTEGER NULL REFERENCES workshops(id)",
        "vehicle_class": "VARCHAR(64) NOT NULL DEFAULT ''", "vehicle_type_label": "VARCHAR(64) NOT NULL DEFAULT ''",
        "history_plate": "VARCHAR(32) NOT NULL DEFAULT ''", "engine_no": "VARCHAR(64) NOT NULL DEFAULT ''",
        "emission_std": "VARCHAR(32) NOT NULL DEFAULT ''", "displacement": "VARCHAR(32) NOT NULL DEFAULT ''",
        "purchase_amount": "NUMERIC(14,2) NULL", "registered_at": "TIMESTAMP WITH TIME ZONE NULL",
    },
    "fuel_cards": {"col_c": "VARCHAR(256) NOT NULL DEFAULT ''", "col_d": "VARCHAR(256) NOT NULL DEFAULT ''"},
    "fuel_records": {"workshop": "VARCHAR(128) NOT NULL DEFAULT ''", "workshop_id": "INTEGER NULL REFERENCES workshops(id)", "platform_record_id": "VARCHAR(80) NULL", "platform_data": "JSON NULL", "volume_available": "BOOLEAN NOT NULL DEFAULT true", "balance_available": "BOOLEAN NOT NULL DEFAULT true"},
    "fuel_balances": {"workshop_id": "INTEGER NULL REFERENCES workshops(id)"},
    "trip_requests": {"workshop_id": "INTEGER NULL REFERENCES workshops(id)"},
    "nav_presets": {"is_locked": "BOOLEAN NOT NULL DEFAULT true"},
}

INDEXES = {
    "fuel_records": {
        "ix_fuel_records_occur_time": ("occur_time",),
        "ix_fuel_records_workshop_occur_time": ("workshop_id", "occur_time"),
    },
    "trip_requests": {
        "ix_trip_requests_workshop_status_id": ("workshop_id", "status", "id"),
        "ix_trip_requests_created_by_status": ("created_by", "status"),
        "ix_trip_requests_driver_id": ("driver_id",),
    },
}


def run_pre_create_migrations() -> None:
    """在 ORM 建表前统一旧表名，并将 PostgreSQL 表归入业务 schema。"""
    with engine.begin() as conn:
        if conn.dialect.name == "postgresql":
            conn.execute(text("SELECT pg_advisory_xact_lock(82473101)"))
            _organize_postgresql_tables(conn)
            return
        existing = set(inspect(conn).get_table_names())
        for old_name, new_name in TABLE_RENAMES.items():
            if old_name not in existing:
                continue
            if new_name in existing:
                raise RuntimeError(f"无法迁移表名：{old_name} 与 {new_name} 同时存在")
            conn.execute(text(f'ALTER TABLE "{old_name}" RENAME TO "{new_name}"'))
            existing.remove(old_name)
            existing.add(new_name)


def _organize_postgresql_tables(conn) -> None:
    for schema in SCHEMA_TABLES:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))

    inspector = inspect(conn)
    public_tables = set(inspector.get_table_names(schema="public"))
    for old_name, new_name in TABLE_RENAMES.items():
        if old_name not in public_tables:
            continue
        if new_name in public_tables:
            raise RuntimeError(f"无法迁移表名：{old_name} 与 {new_name} 同时存在")
        conn.execute(text(f'ALTER TABLE "public"."{old_name}" RENAME TO "{new_name}"'))
        public_tables.remove(old_name)
        public_tables.add(new_name)

    for table, target_schema in TABLE_SCHEMAS.items():
        in_public = table in public_tables
        in_target = inspect(conn).has_table(table, schema=target_schema)
        if in_public and in_target:
            raise RuntimeError(f"无法归类表：public.{table} 与 {target_schema}.{table} 同时存在")
        if in_public:
            conn.execute(text(f'ALTER TABLE "public"."{table}" SET SCHEMA "{target_schema}"'))
            public_tables.remove(table)


def run_runtime_migrations() -> None:
    with engine.begin() as conn:
        if conn.dialect.name == "postgresql":
            conn.execute(text("SELECT pg_advisory_xact_lock(82473101)"))
            _organize_postgresql_tables(conn)
        inspector = inspect(conn)
        for table, additions in ADDITIONS.items():
            schema = TABLE_SCHEMAS.get(table) if conn.dialect.name == "postgresql" else None
            if not inspector.has_table(table, schema=schema):
                continue
            columns = {c["name"] for c in inspector.get_columns(table, schema=schema)}
            qualified_table = f'"{schema}"."{table}"' if schema else f'"{table}"'
            for name, definition in additions.items():
                if name not in columns:
                    conn.execute(text(f'ALTER TABLE {qualified_table} ADD COLUMN "{name}" {definition}'))
            if "workshop_id" in additions:
                conn.execute(text(f'CREATE INDEX IF NOT EXISTS "ix_{table}_workshop_id" ON {qualified_table} (workshop_id)'))
        driver_schema = TABLE_SCHEMAS.get("drivers") if conn.dialect.name == "postgresql" else None
        if inspector.has_table("drivers", schema=driver_schema):
            drivers = f'"{driver_schema}"."drivers"' if driver_schema else '"drivers"'
            conn.execute(text(f'CREATE UNIQUE INDEX IF NOT EXISTS "uq_drivers_user_id" ON {drivers} (user_id) WHERE user_id IS NOT NULL'))
        for table, indexes in INDEXES.items():
            schema = TABLE_SCHEMAS.get(table) if conn.dialect.name == "postgresql" else None
            if not inspector.has_table(table, schema=schema):
                continue
            qualified_table = f'"{schema}"."{table}"' if schema else f'"{table}"'
            if table == "fuel_records":
                conn.execute(text(f'CREATE UNIQUE INDEX IF NOT EXISTS "uq_fuel_records_platform_record_id" ON {qualified_table} (platform_record_id)'))
            for index_name, columns in indexes.items():
                column_sql = ", ".join(f'"{column}"' for column in columns)
                conn.execute(text(f'CREATE INDEX IF NOT EXISTS "{index_name}" ON {qualified_table} ({column_sql})'))

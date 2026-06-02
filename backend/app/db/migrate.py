"""轻量级运行时迁移：在无法使用 Alembic 的环境里补齐历史表结构。"""

from sqlalchemy import inspect, text
from sqlalchemy.exc import ProgrammingError

from app.db.session import engine


def run_runtime_migrations() -> None:
    insp = inspect(engine)

    if insp.has_table("bus_expense"):
        with engine.begin() as conn:
            try:
                conn.execute(text("DROP TABLE IF EXISTS bus_expense CASCADE"))
            except ProgrammingError:
                pass
        insp = inspect(engine)

    if insp.has_table("sys_user"):
        cols = {c["name"] for c in insp.get_columns("sys_user")}
        if "role" not in cols:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE sys_user ADD COLUMN role VARCHAR(32) NOT NULL DEFAULT 'vehicle_driver'")
                )

    if insp.has_table("bus_driver"):
        cols = {c["name"] for c in insp.get_columns("bus_driver")}
        if "user_id" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE bus_driver ADD COLUMN user_id INTEGER"))

        insp = inspect(engine)
        fk_names = {fk.get("name") for fk in insp.get_foreign_keys("bus_driver")}
        if "bus_driver_user_id_fkey" not in fk_names:
            try:
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            "ALTER TABLE bus_driver ADD CONSTRAINT bus_driver_user_id_fkey "
                            "FOREIGN KEY (user_id) REFERENCES sys_user (id)"
                        )
                    )
            except ProgrammingError:
                pass

        try:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS uq_bus_driver_user_id "
                        "ON bus_driver (user_id) WHERE user_id IS NOT NULL"
                    )
                )
        except ProgrammingError:
            pass

        # 与《驾驶员数据库表》Excel 列对齐：新增字段、迁移旧列数据后删除废弃列
        insp = inspect(engine)
        cols = {c["name"] for c in insp.get_columns("bus_driver")}
        driver_adds: list[str] = []
        if "sort_no" not in cols:
            driver_adds.append("ALTER TABLE bus_driver ADD COLUMN sort_no INTEGER NULL")
        if "id_card" not in cols:
            driver_adds.append("ALTER TABLE bus_driver ADD COLUMN id_card VARCHAR(32) NULL")
        if "health_check_report" not in cols:
            driver_adds.append("ALTER TABLE bus_driver ADD COLUMN health_check_report TEXT NULL")
        if "outsourcing_onboarding" not in cols:
            driver_adds.append("ALTER TABLE bus_driver ADD COLUMN outsourcing_onboarding TEXT NULL")
        if "first_hire_date" not in cols:
            driver_adds.append("ALTER TABLE bus_driver ADD COLUMN first_hire_date DATE NULL")
        if "vehicle_type_label" not in cols:
            driver_adds.append(
                "ALTER TABLE bus_driver ADD COLUMN vehicle_type_label VARCHAR(64) NOT NULL DEFAULT ''"
            )
        if driver_adds:
            with engine.begin() as conn:
                for stmt in driver_adds:
                    try:
                        conn.execute(text(stmt))
                    except ProgrammingError:
                        pass

        insp = inspect(engine)
        cols = {c["name"] for c in insp.get_columns("bus_driver")}
        with engine.begin() as conn:
            if "license_number" in cols and "id_card" in cols:
                try:
                    conn.execute(
                        text(
                            "UPDATE bus_driver SET id_card = license_number "
                            "WHERE (id_card IS NULL OR id_card = '') AND license_number IS NOT NULL"
                        )
                    )
                except ProgrammingError:
                    pass
            if "hire_date" in cols and "first_hire_date" in cols:
                try:
                    conn.execute(
                        text(
                            "UPDATE bus_driver SET first_hire_date = hire_date "
                            "WHERE first_hire_date IS NULL AND hire_date IS NOT NULL"
                        )
                    )
                except ProgrammingError:
                    pass

        insp = inspect(engine)
        cols = {c["name"] for c in insp.get_columns("bus_driver")}
        driver_drops: list[str] = []
        for obsolete in ("license_number", "hire_date", "remarks"):
            if obsolete in cols:
                driver_drops.append(f"ALTER TABLE bus_driver DROP COLUMN IF EXISTS {obsolete}")
        if driver_drops:
            with engine.begin() as conn:
                for stmt in driver_drops:
                    try:
                        conn.execute(text(stmt))
                    except ProgrammingError:
                        pass

    if insp.has_table("bus_vehicle"):
        cols = {c["name"] for c in insp.get_columns("bus_vehicle")}
        alters: list[str] = []
        if "org_unit" not in cols:
            alters.append("ALTER TABLE bus_vehicle ADD COLUMN org_unit VARCHAR(128) NOT NULL DEFAULT ''")
        if "vehicle_class" not in cols:
            alters.append("ALTER TABLE bus_vehicle ADD COLUMN vehicle_class VARCHAR(64) NOT NULL DEFAULT ''")
        if "vehicle_type_label" not in cols:
            alters.append("ALTER TABLE bus_vehicle ADD COLUMN vehicle_type_label VARCHAR(64) NOT NULL DEFAULT ''")
        if "history_plate" not in cols:
            alters.append("ALTER TABLE bus_vehicle ADD COLUMN history_plate VARCHAR(32) NOT NULL DEFAULT ''")
        if "engine_no" not in cols:
            alters.append("ALTER TABLE bus_vehicle ADD COLUMN engine_no VARCHAR(64) NOT NULL DEFAULT ''")
        if "emission_std" not in cols:
            alters.append("ALTER TABLE bus_vehicle ADD COLUMN emission_std VARCHAR(32) NOT NULL DEFAULT ''")
        if "displacement" not in cols:
            alters.append("ALTER TABLE bus_vehicle ADD COLUMN displacement VARCHAR(32) NOT NULL DEFAULT ''")
        if "purchase_amount" not in cols:
            alters.append("ALTER TABLE bus_vehicle ADD COLUMN purchase_amount NUMERIC(14, 2) NULL")
        if "registered_at" not in cols:
            alters.append("ALTER TABLE bus_vehicle ADD COLUMN registered_at TIMESTAMP WITH TIME ZONE NULL")
        if alters:
            with engine.begin() as conn:
                for stmt in alters:
                    try:
                        conn.execute(text(stmt))
                    except ProgrammingError:
                        pass

    if insp.has_table("bus_fuel_card"):
        cols = {c["name"] for c in insp.get_columns("bus_fuel_card")}
        with engine.begin() as conn:
            # 将旧字段平滑迁移为 Excel B/C/D 语义，尽量保留历史数据。
            if "col_c" not in cols:
                if "issuer" in cols:
                    try:
                        conn.execute(text("ALTER TABLE bus_fuel_card RENAME COLUMN issuer TO col_c"))
                    except ProgrammingError:
                        pass
                else:
                    try:
                        conn.execute(
                            text("ALTER TABLE bus_fuel_card ADD COLUMN col_c VARCHAR(256) NOT NULL DEFAULT ''")
                        )
                    except ProgrammingError:
                        pass
            if "col_d" not in cols:
                if "holder_name" in cols:
                    try:
                        conn.execute(text("ALTER TABLE bus_fuel_card RENAME COLUMN holder_name TO col_d"))
                    except ProgrammingError:
                        pass
                else:
                    try:
                        conn.execute(
                            text("ALTER TABLE bus_fuel_card ADD COLUMN col_d VARCHAR(256) NOT NULL DEFAULT ''")
                        )
                    except ProgrammingError:
                        pass
            for obsolete in ("balance", "status", "remarks", "created_by"):
                if obsolete in cols:
                    try:
                        conn.execute(text(f"ALTER TABLE bus_fuel_card DROP COLUMN IF EXISTS {obsolete}"))
                    except ProgrammingError:
                        pass

    if insp.has_table("bus_fuel_card_number"):
        with engine.begin() as conn:
            try:
                conn.execute(text("DROP TABLE IF EXISTS bus_fuel_card_number"))
            except ProgrammingError:
                pass

    if insp.has_table("bus_fuel_record"):
        cols = {c["name"] for c in insp.get_columns("bus_fuel_record")}
        if "workshop" not in cols:
            with engine.begin() as conn:
                try:
                    conn.execute(text("ALTER TABLE bus_fuel_record ADD COLUMN workshop VARCHAR(128) NOT NULL DEFAULT ''"))
                except ProgrammingError:
                    pass
        # 旧库 occur_time 为 TEXT，无法按日期筛选；统一迁移为 TIMESTAMPTZ
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT data_type
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = 'bus_fuel_record'
                      AND column_name = 'occur_time'
                    """
                )
            ).first()
        if row and str(row[0]).lower() in {"text", "character varying"}:
            with engine.begin() as conn:
                try:
                    conn.execute(
                        text(
                            """
                            ALTER TABLE bus_fuel_record
                            ALTER COLUMN occur_time TYPE TIMESTAMPTZ
                            USING (
                                CASE
                                    WHEN occur_time IS NULL OR trim(occur_time::text) = '' THEN NOW()
                                    ELSE occur_time::timestamptz
                                END
                            )
                            """
                        )
                    )
                except ProgrammingError:
                    pass

    if insp.has_table("bus_nav_preset"):
        cols = {c["name"] for c in insp.get_columns("bus_nav_preset")}
        if "is_locked" not in cols:
            with engine.begin() as conn:
                try:
                    conn.execute(
                        text(
                            "ALTER TABLE bus_nav_preset ADD COLUMN is_locked BOOLEAN NOT NULL DEFAULT true"
                        )
                    )
                except ProgrammingError:
                    pass

    if insp.has_table("sys_user"):
        with engine.begin() as conn:
            # 分级角色迁移：内置 admin 固定为超级管理员
            conn.execute(text("UPDATE sys_user SET role = 'super_admin' WHERE username = 'admin'"))
            conn.execute(text("UPDATE sys_user SET role = 'super_admin' WHERE role = 'admin'"))
            conn.execute(text("UPDATE sys_user SET role = 'section_admin' WHERE role = 'fleet_manager'"))
            conn.execute(text("UPDATE sys_user SET role = 'vehicle_driver' WHERE role = 'driver'"))
            conn.execute(text("UPDATE sys_user SET role = 'vehicle_driver' WHERE role = 'staff'"))

    _migrate_workshop_master(insp)


def _migrate_workshop_master(insp) -> None:
    """车间主表 bus_workshop 及 workshop_id 外键列（兼容旧库）。"""
    tables_fk: list[tuple[str, str]] = [
        ("sys_user", "sys_user_workshop_id_fkey"),
        ("bus_driver", "bus_driver_workshop_id_fkey"),
        ("bus_vehicle", "bus_vehicle_workshop_id_fkey"),
        ("bus_fuel_record", "bus_fuel_record_workshop_id_fkey"),
        ("bus_fuel_balance", "bus_fuel_balance_workshop_id_fkey"),
        ("bus_trip_request", "bus_trip_request_workshop_id_fkey"),
    ]
    for table, _ in tables_fk:
        if not insp.has_table(table):
            continue
        cols = {c["name"] for c in insp.get_columns(table)}
        if "workshop_id" not in cols:
            with engine.begin() as conn:
                try:
                    conn.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN workshop_id INTEGER NULL")
                    )
                except ProgrammingError:
                    pass
        insp = inspect(engine)
        fk_names = {fk.get("name") for fk in insp.get_foreign_keys(table)}
        cname = f"{table}_workshop_id_fkey"
        if cname not in fk_names and insp.has_table("bus_workshop"):
            try:
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            f"ALTER TABLE {table} ADD CONSTRAINT {cname} "
                            "FOREIGN KEY (workshop_id) REFERENCES bus_workshop (id)"
                        )
                    )
            except ProgrammingError:
                pass
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(f"CREATE INDEX IF NOT EXISTS ix_{table}_workshop_id ON {table} (workshop_id)")
                )
        except ProgrammingError:
            pass

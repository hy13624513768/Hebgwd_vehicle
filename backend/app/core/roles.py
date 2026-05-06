"""系统账号分级（存于 sys_user.role）。"""

from __future__ import annotations

# 新分级（推荐使用）
SUPER_ADMIN = "super_admin"
SECTION_ADMIN = "section_admin"
WORKSHOP_DIRECTOR = "workshop_director"
WORKSHOP_ADMIN = "workshop_admin"
VEHICLE_DRIVER = "vehicle_driver"

# 旧版兼容（迁移后应逐步消失）
LEGACY_ADMIN = "admin"
LEGACY_FLEET_MANAGER = "fleet_manager"
LEGACY_DRIVER = "driver"
LEGACY_STAFF = "staff"

ROLE_LABELS: dict[str, str] = {
    SUPER_ADMIN: "超级管理员",
    SECTION_ADMIN: "段级管理员",
    WORKSHOP_DIRECTOR: "车间主任",
    WORKSHOP_ADMIN: "车间管理员",
    VEHICLE_DRIVER: "车辆驾驶员",
    # 旧值展示用
    LEGACY_ADMIN: "管理员(旧)",
    LEGACY_FLEET_MANAGER: "车管(旧)",
    LEGACY_DRIVER: "驾驶员(旧)",
    LEGACY_STAFF: "普通用户(旧)",
}

# 数字越大权限越高（用于可分配范围校验）
ROLE_RANK: dict[str, int] = {
    VEHICLE_DRIVER: 1,
    WORKSHOP_ADMIN: 2,
    WORKSHOP_DIRECTOR: 3,
    SECTION_ADMIN: 4,
    SUPER_ADMIN: 5,
    LEGACY_STAFF: 1,
    LEGACY_DRIVER: 1,
    LEGACY_FLEET_MANAGER: 4,
    LEGACY_ADMIN: 5,
}


def rank(role: str) -> int:
    return ROLE_RANK.get(role, 0)


def is_legacy_super(role: str) -> bool:
    return role in (SUPER_ADMIN, LEGACY_ADMIN)


def is_fleet_management(role: str) -> bool:
    """可维护车辆/驾驶员/油卡/维保/报表导出等车队类权限。"""
    return role in {
        SUPER_ADMIN,
        SECTION_ADMIN,
        WORKSHOP_DIRECTOR,
        WORKSHOP_ADMIN,
        LEGACY_ADMIN,
        LEGACY_FLEET_MANAGER,
    }


def is_account_admin(role: str) -> bool:
    """可进入账户管理并维护账号（除受保护账号外）。"""
    return role in {SUPER_ADMIN, SECTION_ADMIN, LEGACY_ADMIN, LEGACY_FLEET_MANAGER}


def assignable_roles_for_actor(actor_role: str) -> list[str]:
    """当前操作者可分配的角色编码列表（不含仅保留在库中的旧值）。"""
    if is_legacy_super(actor_role):
        return [
            SUPER_ADMIN,
            SECTION_ADMIN,
            WORKSHOP_DIRECTOR,
            WORKSHOP_ADMIN,
            VEHICLE_DRIVER,
        ]
    if actor_role in (SECTION_ADMIN, LEGACY_FLEET_MANAGER):
        return [
            SECTION_ADMIN,
            WORKSHOP_DIRECTOR,
            WORKSHOP_ADMIN,
            VEHICLE_DRIVER,
        ]
    return []


def can_actor_manage_user(actor_role: str, target_username: str, target_role: str) -> bool:
    """是否允许操作 target（粗粒度，细规则在 API 中再校验）。"""
    if not is_account_admin(actor_role):
        return False
    if target_username.strip().lower() == "admin":
        return is_legacy_super(actor_role)
    if is_legacy_super(target_role) and not is_legacy_super(actor_role):
        return False
    return rank(actor_role) >= rank(target_role) or is_legacy_super(actor_role)


def normalize_role_for_storage(role: str) -> str:
    """登录/输出时可将旧角色映射为新角色（可选在迁移后调用）。"""
    m = {
        LEGACY_ADMIN: SUPER_ADMIN,
        LEGACY_FLEET_MANAGER: SECTION_ADMIN,
        LEGACY_DRIVER: VEHICLE_DRIVER,
        LEGACY_STAFF: VEHICLE_DRIVER,
    }
    return m.get(role, role)

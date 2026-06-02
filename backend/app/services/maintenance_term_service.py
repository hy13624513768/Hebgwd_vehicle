"""维修词条业务逻辑。"""

from __future__ import annotations

import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.data.maintenance_term_preset import MAINTENANCE_TERM_PRESET
from app.models.maintenance_term import MaintenanceTerm
from app.schemas.maintenance_term import (
    MaintenanceTermCreate,
    MaintenanceTermOut,
    MaintenanceTermStatsOut,
    MaintenanceTermTreeNode,
    MaintenanceTermUpdate,
)


def _dump_list(values: list[str]) -> str:
    cleaned = [v.strip() for v in values if v and v.strip()]
    return json.dumps(cleaned, ensure_ascii=False)


def _load_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except json.JSONDecodeError:
        pass
    return []


def term_to_out(row: MaintenanceTerm) -> MaintenanceTermOut:
    return MaintenanceTermOut(
        id=row.id,
        parent_id=row.parent_id,
        level=row.level,
        code=row.code,
        name=row.name,
        aliases=_load_list(row.aliases),
        keywords=_load_list(row.keywords),
        sort_order=row.sort_order,
        is_active=row.is_active,
        standard_hours=row.standard_hours,
        reference_cost=row.reference_cost,
        remarks=row.remarks,
    )


def get_stats(db: Session) -> MaintenanceTermStatsOut:
    rows = db.execute(
        select(MaintenanceTerm.level, func.count())
        .group_by(MaintenanceTerm.level)
    ).all()
    counts = {int(level): int(cnt) for level, cnt in rows}
    active_terms = int(
        db.scalar(
            select(func.count())
            .select_from(MaintenanceTerm)
            .where(MaintenanceTerm.level == 3, MaintenanceTerm.is_active.is_(True))
        )
        or 0
    )
    total = int(db.scalar(select(func.count()).select_from(MaintenanceTerm)) or 0)
    return MaintenanceTermStatsOut(
        level1=counts.get(1, 0),
        level2=counts.get(2, 0),
        level3=counts.get(3, 0),
        active_terms=active_terms,
        total=total,
    )


def build_tree(db: Session, active_only: bool = False) -> list[MaintenanceTermTreeNode]:
    stmt = select(MaintenanceTerm).order_by(
        MaintenanceTerm.level.asc(),
        MaintenanceTerm.sort_order.asc(),
        MaintenanceTerm.id.asc(),
    )
    if active_only:
        stmt = stmt.where(MaintenanceTerm.is_active.is_(True))
    rows = list(db.scalars(stmt).all())
    nodes: dict[int, MaintenanceTermTreeNode] = {}
    roots: list[MaintenanceTermTreeNode] = []
    for row in rows:
        out = term_to_out(row)
        node = MaintenanceTermTreeNode(**out.model_dump(), children=[])
        nodes[row.id] = node
    for row in rows:
        node = nodes[row.id]
        if row.parent_id and row.parent_id in nodes:
            nodes[row.parent_id].children.append(node)
        elif row.level == 1:
            roots.append(node)
    return roots


def validate_parent_level(db: Session, parent_id: int | None, level: int) -> MaintenanceTerm | None:
    if level == 1:
        if parent_id is not None:
            raise ValueError("一级大类不能有上级")
        return None
    if parent_id is None:
        raise ValueError("二级/三级必须指定上级")
    parent = db.get(MaintenanceTerm, parent_id)
    if not parent:
        raise ValueError("上级分类不存在")
    if level == 2 and parent.level != 1:
        raise ValueError("二级子类必须挂在一级大类下")
    if level == 3 and parent.level != 2:
        raise ValueError("三级词条必须挂在二级子类下")
    return parent


def create_term(db: Session, body: MaintenanceTermCreate) -> MaintenanceTerm:
    validate_parent_level(db, body.parent_id, body.level)
    row = MaintenanceTerm(
        parent_id=body.parent_id,
        level=body.level,
        code=body.code.strip(),
        name=body.name.strip(),
        aliases=_dump_list(body.aliases),
        keywords=_dump_list(body.keywords),
        sort_order=body.sort_order,
        is_active=body.is_active,
        standard_hours=body.standard_hours if body.level == 3 else None,
        reference_cost=body.reference_cost if body.level == 3 else None,
        remarks=body.remarks,
    )
    db.add(row)
    db.flush()
    return row


def update_term(db: Session, row: MaintenanceTerm, body: MaintenanceTermUpdate) -> MaintenanceTerm:
    data = body.model_dump(exclude_unset=True)
    if "parent_id" in data or "level" in data:
        raise ValueError("不支持修改层级或上级，请删除后重建")
    if "name" in data and data["name"] is not None:
        data["name"] = data["name"].strip()
    if "code" in data and data["code"] is not None:
        data["code"] = data["code"].strip()
    if "aliases" in data and data["aliases"] is not None:
        data["aliases"] = _dump_list(data["aliases"])
    if "keywords" in data and data["keywords"] is not None:
        data["keywords"] = _dump_list(data["keywords"])
    if row.level != 3:
        data.pop("standard_hours", None)
        data.pop("reference_cost", None)
    for k, v in data.items():
        setattr(row, k, v)
    db.flush()
    return row


def delete_term(db: Session, row: MaintenanceTerm) -> None:
    child_count = int(
        db.scalar(
            select(func.count())
            .select_from(MaintenanceTerm)
            .where(MaintenanceTerm.parent_id == row.id)
        )
        or 0
    )
    if child_count:
        raise ValueError("请先删除下级分类或词条")
    db.delete(row)


def seed_preset_if_empty(db: Session, *, force: bool = False) -> tuple[int, bool]:
    existing = int(db.scalar(select(func.count()).select_from(MaintenanceTerm)) or 0)
    if existing and not force:
        return 0, True

    if force and existing:
        db.query(MaintenanceTerm).delete()
        db.flush()

    created = 0
    for cat_idx, cat in enumerate(MAINTENANCE_TERM_PRESET):
        l1 = MaintenanceTerm(
            parent_id=None,
            level=1,
            code=cat["code"],
            name=cat["name"],
            aliases="[]",
            keywords=json.dumps([cat["name"], cat["code"]], ensure_ascii=False),
            sort_order=cat_idx + 1,
            is_active=True,
        )
        db.add(l1)
        db.flush()
        created += 1

        for sub_idx, sub in enumerate(cat["children"]):
            l2 = MaintenanceTerm(
                parent_id=l1.id,
                level=2,
                code=f"{cat['code']}{sub_idx + 1:02d}",
                name=sub["name"],
                aliases="[]",
                keywords=json.dumps([sub["name"]], ensure_ascii=False),
                sort_order=sub_idx + 1,
                is_active=True,
            )
            db.add(l2)
            db.flush()
            created += 1

            for term_idx, term in enumerate(sub["terms"]):
                aliases = term.get("aliases") or []
                keywords = term.get("keywords") or []
                l3 = MaintenanceTerm(
                    parent_id=l2.id,
                    level=3,
                    code="",
                    name=term["name"],
                    aliases=_dump_list(list(aliases)),
                    keywords=_dump_list(list(keywords)),
                    sort_order=term_idx + 1,
                    is_active=True,
                    remarks=term.get("remarks") or None,
                )
                db.add(l3)
                created += 1

    db.flush()
    return created, False

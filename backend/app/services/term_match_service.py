"""维修词条匹配：将结算单明细行归到三级词条及大类。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.maintenance_term import MaintenanceTerm


@dataclass
class TermMatchResult:
    term_id: int | None
    term_name: str
    category_l1: str
    category_l2: str
    score: int
    method: str


def _load_term_index(db: Session) -> list[dict]:
    rows = list(
        db.scalars(
            select(MaintenanceTerm)
            .where(MaintenanceTerm.level == 3, MaintenanceTerm.is_active.is_(True))
            .order_by(MaintenanceTerm.id)
        ).all()
    )
    id_map = {r.id: r for r in db.scalars(select(MaintenanceTerm)).all()}
    out: list[dict] = []
    for row in rows:
        l2 = id_map.get(row.parent_id) if row.parent_id else None
        l1 = id_map.get(l2.parent_id) if l2 and l2.parent_id else None
        needles: list[str] = [row.name]
        import json

        for raw in (row.aliases, row.keywords):
            try:
                parsed = json.loads(raw or "[]")
                if isinstance(parsed, list):
                    needles.extend(str(x).strip() for x in parsed if str(x).strip())
            except json.JSONDecodeError:
                pass
        out.append(
            {
                "term_id": row.id,
                "term_name": row.name,
                "category_l1": l1.name if l1 else "",
                "category_l2": l2.name if l2 else "",
                "needles": list(dict.fromkeys(needles)),
            }
        )
    return out


def _score_text(text: str, needle: str) -> int:
    if not text or not needle:
        return 0
    t = text.lower().replace(" ", "")
    n = needle.lower().replace(" ", "")
    if t == n:
        return 100
    if n in t or t in n:
        return 80 + min(len(n), 15)
    return 0


def match_line_to_term(db: Session, line_text: str, *, index: list[dict] | None = None) -> TermMatchResult:
    text = (line_text or "").strip()
    if not text:
        return TermMatchResult(None, "", "", "", 0, "unmatched")
    idx = index if index is not None else _load_term_index(db)
    best: TermMatchResult | None = None
    for entry in idx:
        for needle in entry["needles"]:
            score = _score_text(text, needle)
            if score <= 0:
                continue
            cand = TermMatchResult(
                entry["term_id"],
                entry["term_name"],
                entry["category_l1"],
                entry["category_l2"],
                score,
                "keyword",
            )
            if best is None or cand.score > best.score:
                best = cand
    if best:
        return best
    return TermMatchResult(None, "待确认项目", "其他未分类", "待归类", 0, "unmatched")

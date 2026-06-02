"""车间名称总表（标准名）及历史名称 → 标准名映射。"""

from __future__ import annotations

# 车间数据总表（23 个标准车间）
CANONICAL_WORKSHOP_NAMES: tuple[str, ...] = (
    "办公室",
    "东桥",
    "双城",
    "呼兰",
    "哈东",
    "哈南",
    "哈尔滨",
    "哈桥",
    "哈西",
    "孙家",
    "宾州",
    "尚志",
    "平房",
    "护网",
    "探伤",
    "方正",
    "机修",
    "王岗",
    "维修",
    "道口",
    "阿城",
    "阿城北",
    "高铁桥",
)

# 与车间总表 Excel 一致的排序权重
WORKSHOP_SORT_ORDERS: dict[str, int] = {
    "办公室": 0,
    "东桥": 16,
    "双城": 0,
    "呼兰": 4,
    "哈东": 2,
    "哈南": 3,
    "哈尔滨": 1,
    "哈桥": 15,
    "哈西": 18,
    "孙家": 6,
    "宾州": 19,
    "尚志": 9,
    "平房": 7,
    "护网": 12,
    "探伤": 14,
    "方正": 20,
    "机修": 11,
    "王岗": 5,
    "维修": 10,
    "道口": 13,
    "阿城": 8,
    "阿城北": 21,
    "高铁桥": 17,
}

CANONICAL_SET = frozenset(CANONICAL_WORKSHOP_NAMES)

# 历史/全称 → 标准名（显式规则，优先于自动推断）
WORKSHOP_LEGACY_ALIASES: dict[str, str] = {
    "/": "办公室",
    "双城堡线路车间": "双城",
    "呼兰线路车间": "呼兰",
    "哈东线路车间": "哈东",
    "哈东路桥车间": "哈桥",
    "哈南线路车间": "哈南",
    "哈尔滨线路车间": "哈尔滨",
    "哈尔滨西高铁车间": "哈西",
    "哈尔滨路桥车间": "哈桥",
    "哈尔滨高铁护路巡防车间": "护网",
    "哈尔滨高铁路桥车间": "高铁桥",
    "孙家线路车间": "孙家",
    "宾州线路车间": "宾州",
    "尚志线路车间": "尚志",
    "平房线路车间": "平房",
    "探伤车间": "探伤",
    "方正线路车间": "方正",
    "王岗线路车间": "王岗",
    "综合机修车间": "机修",
    "综合维修车间": "维修",
    "道口车间": "道口",
    "阿城北高铁线路车间": "阿城北",
    "阿城线路车间": "阿城",
}

# 去后缀匹配（从长到短）
_STRIP_SUFFIXES: tuple[str, ...] = (
    "高铁线路车间",
    "高铁路桥车间",
    "高铁护路巡防车间",
    "线路车间",
    "路桥车间",
    "西高铁车间",
    "高铁车间",
    "车间",
)


def normalize_workshop_label(name: str | None) -> str:
    return (name or "").strip()


def resolve_canonical_workshop_name(name: str | None, *, default: str = "办公室") -> str:
    """
    将任意历史车间字符串解析为标准总表名称。
    无法识别时返回 default（默认「办公室」）。
    """
    raw = normalize_workshop_label(name)
    if not raw:
        return default
    if raw in CANONICAL_SET:
        return raw
    if raw in WORKSHOP_LEGACY_ALIASES:
        return WORKSHOP_LEGACY_ALIASES[raw]
    for suffix in _STRIP_SUFFIXES:
        if raw.endswith(suffix):
            prefix = raw[: -len(suffix)].strip()
            if prefix in CANONICAL_SET:
                return prefix
            if prefix in WORKSHOP_LEGACY_ALIASES:
                return WORKSHOP_LEGACY_ALIASES[prefix]
    # 最长前缀：如「哈东xxx」→ 哈东
    for canon in sorted(CANONICAL_WORKSHOP_NAMES, key=len, reverse=True):
        if raw.startswith(canon):
            return canon
    return default

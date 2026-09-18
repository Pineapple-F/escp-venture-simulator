"""Small, model-supported taxonomy for founder-authored enterprise paths."""

from copy import deepcopy


_CATEGORIES = (
    ("foundation", "企业建立", (
        ("founded", "公司成立", 8, -1, 0, "公司成立"),
    )),
    ("financing", "融资", (
        ("seed", "种子轮融资", 1, 0, 0, "种子轮"),
        ("angel", "天使轮融资", 1, 1, 0, "天使轮"),
        ("pre_a", "Pre-A轮融资", 1, 2, 0, "Pre-A轮"),
        ("a", "A轮融资", 1, 3, 0, "A轮"),
        ("b", "B轮融资", 1, 5, 0, "B轮"),
        ("c", "C轮融资", 1, 7, 0, "C轮"),
        ("d_or_later", "D轮及以后融资", 1, 8, 0, "D轮及以后"),
        ("strategic", "战略融资", 1, -1, 0, "战略融资"),
    )),
    ("shareholder", "股东", (
        ("institution_entry", "企业／机构股东进入", 4, -1, 0, "企业股东进入"),
        ("individual_entry", "自然人股东进入", 4, -1, 0, "自然人股东进入"),
        ("shareholder_exit", "股东退出", 5, -1, 0, "股东退出"),
    )),
    ("equity", "股权与工商", (
        ("equity_change", "股权结构变更", 20, -1, 0, "股东信息变更"),
        ("legal_change", "法定代表人／负责人变更", 20, -1, 0, "法定代表人变更"),
        ("scope_change", "经营范围变更", 20, -1, 0, "经营范围变更"),
        ("identity_change", "名称、地址或主体类型变更", 20, -1, 0, "企业主体信息变更"),
    )),
    ("capital", "注册资本", (
        ("capital_increase", "注册资本增加", 19, -1, 0, "注册资本增加"),
        ("capital_decrease", "注册资本减少", 19, -1, 0, "注册资本减少"),
    )),
    ("team", "核心团队", (
        ("core_join", "核心人员加入", 2, -1, 1, "核心管理人员加入"),
        ("core_leave", "核心人员离开", 3, -1, 1, "核心管理人员离开"),
    )),
    ("risk", "经营风险", (
        ("abnormal_enter", "进入经营异常", 11, -1, 0, "进入经营异常名录"),
        ("abnormal_exit", "移出经营异常", 12, -1, 0, "移出经营异常名录"),
        ("penalty", "行政处罚", 21, -1, 0, "行政处罚"),
        ("dishonesty", "失信记录", 22, -1, 0, "失信记录"),
    )),
)


LOOKUP = {
    (category, key): {
        "category": category,
        "category_label": category_label,
        "subtype": key,
        "label": label,
        "type": event_type,
        "stage": stage,
        "role": role,
        "detail": detail,
    }
    for category, category_label, items in _CATEGORIES
    for key, label, event_type, stage, role, detail in items
}


def taxonomy():
    return [
        {
            "key": category,
            "label": label,
            "items": [{"key": item[0], "label": item[1]} for item in items],
        }
        for category, label, items in _CATEGORIES
    ]


def normalize(category, subtype):
    result = LOOKUP.get((category, subtype))
    if result is None:
        raise ValueError("事件类型无效")
    return deepcopy(result)

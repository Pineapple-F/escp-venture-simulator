"""Build model-ready scenario events from the founder financing workflow."""


def _money(value, currency):
    if value is None:
        return "未填写"
    return f"{value:g} {currency}"


def build(state, company, institutions):
    plan = state.get("founder_plans", {}).get(company)
    contacts = state.get("founder_contacts", {}).get(company, {})
    missing = []
    if not plan:
        missing.append("融资方案")
    else:
        if not plan.get("target"):
            missing.append("融资目标")
        if not plan.get("pre_money"):
            missing.append("投前估值")
        if plan.get("cash") is None:
            missing.append("可用现金")
        if plan.get("burn") is None:
            missing.append("月均净支出")
        if not plan.get("purpose"):
            missing.append("资金用途")
    if not contacts:
        missing.append("目标机构")
    if missing:
        return {"ready": False, "missing": missing, "events": []}

    active = state.get("founder_rounds", {}).get(company)
    # Financing execution advances by weeks independently from the portfolio clock.
    # The appended path must therefore end at the newest simulated event date.
    as_of = max(state["as_of"], active.get("date", state["as_of"]) if active else state["as_of"])
    currency = plan["currency"]
    budget = plan.get("budget", {})
    budget_text = "、".join(
        f"{label}{_money(budget.get(key, 0), currency)}"
        for key, label in (("research", "研发"), ("hiring", "招聘"),
                           ("marketing", "市场"), ("other", "其他"))
        if budget.get(key)
    ) or "暂未拆分"
    selected = []
    for institution_id, contact in contacts.items():
        institution = institutions.get(institution_id, {})
        company_count = len({item["company"] for item in institution.get("rounds", [])})
        selected.append({
            "id": institution_id,
            "name": contact["name"],
            "stage": contact.get("stage", "待接触"),
            "history_company_count": company_count,
        })
    selected.sort(key=lambda item: item["name"])
    names = "、".join(item["name"] for item in selected[:8])
    if len(selected) > 8:
        names += f"等{len(selected)}家"
    plan_detail = (
        f"融资方案确定；目标融资{_money(plan['target'], currency)}；"
        f"投前估值{_money(plan['pre_money'], currency)}；"
        f"可用现金{_money(plan['cash'], currency)}；"
        f"月净现金消耗{_money(plan.get('burn'), currency)}；"
        f"资金用途：{plan['purpose']}；用途预算：{budget_text}"
    )
    institution_detail = (
        f"已选择{len(selected)}家融资机构：{names}；"
        f"当前状态：" + "、".join(
            f"{item['name']}（{item['stage']}）" for item in selected[:8])
    )
    events = [
        {"date": as_of, "type": 1, "stage": -1, "role": 0,
         "subtype": "financing_plan", "label": "融资方案确定",
         "detail": plan_detail, "source": "企业融资工作台"},
        {"date": as_of, "type": 4, "stage": -1, "role": 0,
         "subtype": "institution_selection", "label": "选择融资机构",
         "detail": institution_detail, "source": "企业融资工作台"},
    ]
    if active:
        statuses = [item.get("status") for item in active.get("applications", {}).values()]
        events.append({
            "date": active.get("date", as_of), "type": 1, "stage": -1, "role": 0,
            "subtype": "financing_progress", "label": "融资流程推进",
            "detail": (f"融资流程已推进{active.get('week', 0)}周；"
                       f"已到账{_money(active.get('raised', 0), currency)}；"
                       f"机构状态：{'、'.join(statuses) or '待提交'}"),
            "source": "企业融资工作台",
        })
    return {
        "ready": True,
        "as_of": as_of,
        "missing": [],
        "events": events,
        "plan": {
            "currency": currency,
            "target": plan["target"],
            "pre_money": plan["pre_money"],
            "purpose": plan["purpose"],
        },
        "institutions": selected,
    }

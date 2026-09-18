"""Persist forecast-related user decisions inside the existing account state."""

import copy
import math
import secrets
from datetime import date
from datetime import datetime, timezone

from evidence_engine import RuleError


EVENTS = ("融资", "企业／机构股东进入", "股权结构变更", "注册资本变更", "注销")
PLAN_STATUSES = ("待准备", "进行中", "已完成", "暂不处理")
FOLLOWUP_STATUSES = ("待研判", "跟进中", "已联系", "不跟进")


def _text(value, label, limit):
    if not isinstance(value, str):
        raise RuleError(label + "无效")
    value = value.strip()
    if len(value) > limit:
        raise RuleError(label + "过长")
    return value


def _company(state, action, universe, allow_custom=False):
    company = action.get("company")
    if allow_custom and company == "founder_custom" and state.get("founder_custom", {}).get("profile", {}).get("name"):
        return company
    if not isinstance(company, str) or not any(
            item["id"] == company for item in universe["companies"]):
        raise RuleError("企业不存在")
    return company


def _event(action):
    event = action.get("event")
    if event not in EVENTS:
        raise RuleError("预测事件无效")
    return event


def _month(value):
    if value in (None, ""):
        return None
    if not isinstance(value, str) or len(value) != 7 or value[4] != "-":
        raise RuleError("计划月份无效")
    try:
        year, month = map(int, value.split("-"))
    except ValueError as error:
        raise RuleError("计划月份无效") from error
    if not 2000 <= year <= 2100 or not 1 <= month <= 12:
        raise RuleError("计划月份无效")
    return value


def _optional_amount(value, label):
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise RuleError(label + "无效")
    try:
        amount = float(value)
    except (TypeError, ValueError) as error:
        raise RuleError(label + "无效") from error
    if not 0 <= amount <= 1_000_000_000_000 or not math.isfinite(amount):
        raise RuleError(label + "无效")
    return amount


def transact(state, action, universe):
    kind = action.get("type")
    result = copy.deepcopy(state)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    if kind == "founder_custom_profile":
        name = _text(action.get("name", ""), "企业名称", 80)
        if not name:
            raise RuleError("请填写企业名称")
        custom = result.setdefault("founder_custom", {"profile": {}, "events": []})
        custom["profile"] = {
            "name": name,
            "industry": _text(action.get("industry", ""), "所属行业", 80),
            "region": _text(action.get("region", ""), "所在地区", 80),
            "updated_at": now,
        }
        result["founder_mode"] = "custom"
    elif kind == "founder_custom_event_add":
        from custom_path import normalize
        try:
            normalized = normalize(action.get("category"), action.get("subtype"))
        except (ValueError, TypeError) as error:
            raise RuleError("事件类型无效") from error
        try:
            event_date = date.fromisoformat(action.get("date", ""))
        except (ValueError, TypeError) as error:
            raise RuleError("事件日期无效") from error
        if event_date.year < 1900 or event_date > date.today():
            raise RuleError("事件日期不能晚于今天")
        custom = result.setdefault("founder_custom", {"profile": {}, "events": []})
        if not custom.get("profile", {}).get("name"):
            raise RuleError("请先保存企业名称")
        event = {**normalized, "id": secrets.token_hex(6),
                 "date": event_date.isoformat(), "source": "企业用户自报"}
        custom.setdefault("events", []).append(event)
        custom["events"].sort(key=lambda item: (item["date"], item["type"], item["id"]))
        result["founder_mode"] = "custom"
    elif kind == "founder_custom_event_delete":
        event_id = action.get("event_id")
        custom = result.get("founder_custom", {})
        events = custom.get("events", [])
        kept = [event for event in events if event.get("id") != event_id]
        if len(kept) == len(events):
            raise RuleError("历史节点不存在")
        custom["events"] = kept
        result["founder_mode"] = "custom"
    elif kind == "founder_custom_mode":
        mode = action.get("mode")
        if mode not in ("custom", "dataset"):
            raise RuleError("企业模式无效")
        result["founder_mode"] = mode
    elif kind == "founder_custom_finance_plan":
        if not result.get("founder_custom", {}).get("profile", {}).get("name"):
            raise RuleError("请先保存企业名称")
        currency = action.get("currency")
        if currency not in ("CNY", "USD"):
            raise RuleError("币种无效")
        result["founder_custom_finance_plan"] = {
            "currency": currency,
            "target": _optional_amount(action.get("target"), "计划融资金额"),
            "cash": _optional_amount(action.get("cash"), "可用现金"),
            "burn": _optional_amount(action.get("burn"), "月净现金消耗"),
            "purpose": _text(action.get("purpose", ""), "资金用途", 1200),
            "updated_at": now,
        }
    elif kind == "forecast_plan":
        company = _company(state, action, universe, allow_custom=True)
        event = _event(action)
        status = action.get("status")
        if status not in PLAN_STATUSES:
            raise RuleError("行动状态无效")
        plans = result.setdefault("forecast_plans", {}).setdefault(company, {})
        plans[event] = {
            "event": event,
            "status": status,
            "due_month": _month(action.get("due_month")),
            "note": _text(action.get("note", ""), "行动备注", 600),
            "updated_at": now,
        }
    elif kind == "forecast_watch":
        company = _company(state, action, universe)
        enabled = action.get("enabled")
        if type(enabled) is not bool:
            raise RuleError("关注状态无效")
        watchlist = result.setdefault("forecast_watchlist", {})
        if enabled:
            previous = watchlist.get(company, {})
            watchlist[company] = {
                "company": company,
                "note": previous.get("note", ""),
                "updated_at": now,
            }
        else:
            watchlist.pop(company, None)
    elif kind == "forecast_followup":
        company = _company(state, action, universe)
        event = _event(action)
        status = action.get("status")
        if status not in FOLLOWUP_STATUSES:
            raise RuleError("跟进状态无效")
        followups = result.setdefault("forecast_followups", {}).setdefault(company, {})
        followups[event] = {
            "event": event,
            "status": status,
            "due_month": _month(action.get("due_month")),
            "note": _text(action.get("note", ""), "跟进备注", 600),
            "updated_at": now,
        }
        result.setdefault("forecast_watchlist", {})[company] = {
            "company": company,
            "note": "已有事件跟进",
            "updated_at": now,
        }
    else:
        raise RuleError("不支持的预测操作")
    result["revision"] += 1
    return result

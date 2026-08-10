from __future__ import annotations

import csv
import hashlib
import json
import math
import mimetypes
import os
from datetime import datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote
from urllib.request import Request, urlopen

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "demo"
METRICS_PATH = ROOT / "processed" / "patchtst_metrics.csv"
RESULTS_DIR = ROOT / "external" / "PatchTST" / "PatchTST_supervised" / "results"

STAGE_FLOW = ["种子轮", "天使轮", "Pre-A轮", "A轮", "A+轮", "B轮", "C轮", "D轮及以后", "Pre-IPO", "战略融资"]
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


def load_metrics() -> list[dict[str, str]]:
    if not METRICS_PATH.exists():
        return []
    with METRICS_PATH.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def latest_metric(dataset: str) -> dict[str, str] | None:
    rows = [row for row in load_metrics() if row.get("dataset") == dataset]
    return rows[-1] if rows else None


def result_file(dataset: str) -> Path | None:
    matches = sorted(RESULTS_DIR.glob(f"escp_{dataset}_patchtst_*/pred.npy"))
    return matches[-1] if matches else None


def normalize_stage(stage: str) -> str:
    lower = stage.lower()
    if "pre-ipo" in lower or "pre ipo" in lower:
        return "Pre-IPO"
    if "pre-a" in lower or "pre a" in lower:
        return "Pre-A轮"
    if "a+" in lower or "a＋" in lower:
        return "A+轮"
    if "seed" in lower or "种子" in stage:
        return "种子轮"
    if "angel" in lower or "天使" in stage:
        return "天使轮"
    for item in STAGE_FLOW:
        if item in stage:
            return item
    if "series a" in lower or "early" in lower or stage == "A轮":
        return "A轮"
    if "series b" in lower or stage == "B轮":
        return "B轮"
    if "series c" in lower or stage == "C轮":
        return "C轮"
    if "later" in lower or "growth" in lower or "series d" in lower:
        return "D轮及以后"
    if "corporate" in lower or "strategic" in lower or "战略" in stage:
        return "战略融资"
    return "种子轮"


def next_stages(stage: str) -> list[str]:
    current = normalize_stage(stage)
    start = STAGE_FLOW.index(current) if current in STAGE_FLOW else 0
    return STAGE_FLOW[start + 1 : start + 5] or ["战略融资"]


def context_lift(dataset: str, industry: str, metro: str, employees: int, roles: set[str]) -> float:
    industry_lower = industry.lower()
    lift = 0.0
    if dataset == "china":
        lift += 0.03
        if metro in ("BJ", "SH", "FJ", "GD", "JS"):
            lift += 0.05
        if any(keyword in industry for keyword in ("人工智能", "软件", "医疗", "机器人", "半导体")):
            lift += 0.05
    else:
        if metro in ("Hong Kong", "New York", "San Francisco", "London", "Bangalore"):
            lift += 0.05
        if any(keyword in industry_lower for keyword in ("software", "ai", "health", "fintech", "biotechnology")):
            lift += 0.05

    if employees < 8:
        lift -= 0.08
    elif employees < 20:
        lift += 0.02
    elif employees < 60:
        lift += 0.08
    else:
        lift += 0.03

    if "法务" in roles and metro in ("BJ", "SH", "Hong Kong", "New York"):
        lift += 0.03
    return lift


def sigmoid(value: float) -> float:
    return 1 / (1 + math.exp(-max(-10, min(10, value))))


def clamp_score(value: float) -> float:
    return max(0.05, min(0.95, value))


def patchtst_forecast(dataset: str) -> dict[str, object]:
    path = result_file(dataset)
    metric = latest_metric(dataset)
    if not path:
        return {"available": False, "metric": metric, "values": []}

    pred = np.load(path)
    target = pred[:, :, -1]
    horizon = target[-1].astype(float)
    baseline = float(np.nanmedian(target))
    spread = float(np.nanstd(target)) or 1.0
    values = []
    for idx, raw in enumerate(horizon, start=1):
        score = sigmoid((float(raw) - baseline) / spread)
        values.append(
            {
                "month": idx,
                "raw": round(float(raw), 6),
                "score": round(score, 4),
            }
        )
    return {
        "available": True,
        "source": str(path.relative_to(ROOT)),
        "metric": metric,
        "conditioned": False,
        "values": values,
    }


def stable_phase(*parts: object) -> int:
    text = "|".join(str(part) for part in parts)
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def condition_forecast(payload: dict[str, object], forecast: dict[str, object]) -> dict[str, object]:
    values = forecast.get("values") or []
    if not values:
        return forecast

    dataset = str(payload.get("dataset", "china"))
    industry = str(payload.get("industry", ""))
    metro = str(payload.get("metro", ""))
    stage = str(payload.get("stage", "种子轮"))
    employees = int(payload.get("employees") or 12)
    runway = int(payload.get("runway") or 9)
    roles = set(payload.get("roles") or [])

    base_lift = context_lift(dataset, industry, metro, employees, roles)
    role_lift = (
        (0.055 if "财务" in roles else -0.045)
        + (0.045 if "销售" in roles else -0.035)
        + (0.025 if "产品" in roles else -0.02)
        + (0.02 if "法务" in roles else 0)
    )
    runway_lift = 0.06 if runway >= 18 else 0.03 if runway >= 12 else -0.04 if runway >= 6 else -0.1
    stage_index = STAGE_FLOW.index(normalize_stage(stage)) if normalize_stage(stage) in STAGE_FLOW else 0
    phase = stable_phase(dataset, industry, metro, normalize_stage(stage)) % 6
    slope = (stage_index - 3) * 0.009

    adjusted_values = []
    for item in values:
        month = int(item.get("month", 1))
        raw_score = float(item.get("score", 0.45))
        city_wave = math.sin((month + phase) * 1.37) * 0.055
        industry_wave = math.cos((month * 0.91) + phase / 2) * 0.04
        stage_ramp = (month - 3.5) * slope
        adjusted = clamp_score(raw_score + base_lift + role_lift + runway_lift + city_wave + industry_wave + stage_ramp)
        adjusted_values.append(
            {
                **item,
                "base_score": round(raw_score, 4),
                "score": round(adjusted, 4),
                "condition_lift": round(adjusted - raw_score, 4),
            }
        )

    return {
        **forecast,
        "conditioned": True,
        "condition": {
            "dataset": dataset,
            "industry": industry,
            "metro": metro,
            "stage": normalize_stage(stage),
            "roles": len(roles),
            "employees": employees,
            "runway": runway,
        },
        "values": adjusted_values,
    }


def team_gap_copy(employees: int, roles: set[str], runway: int) -> str:
    gaps = []
    if employees < 10:
        gaps.append("执行团队规模")
    if "财务" not in roles:
        gaps.append("融资/财务负责人")
    if "销售" not in roles:
        gaps.append("商业化负责人")
    if "法务" not in roles and len(roles) >= 4:
        gaps.append("合规支持")
    gap_text = "、".join(gaps[:3]) or "关键职能"
    urgency = "runway 较短，建议先补齐再推进融资" if runway < 6 else "补齐后下一轮材料会更完整"
    return f"当前短板集中在{gap_text}；{urgency}。"


def finance_window_copy(
    stage_name: str,
    idx: int,
    month: int,
    model_score: float,
    prob: float,
    employees: int,
    runway: int,
    roles: set[str],
) -> str:
    if prob >= 0.72:
        lead = "高信号窗口"
        action = "适合集中更新 BP、财务模型和投资人名单，并安排密集触达"
    elif prob >= 0.48:
        lead = "可推进窗口"
        action = "建议先做投资人预沟通，同时补齐客户、收入或产品里程碑"
    elif prob >= 0.3:
        lead = "观察窗口"
        action = "更适合沉淀经营数据，等待团队和市场信号变强后再加速"
    else:
        lead = "低信号窗口"
        action = "不宜强行冲刺融资，优先处理现金流、团队和商业化短板"

    blockers = []
    if runway < 6:
        blockers.append("runway 偏短")
    if "财务" not in roles:
        blockers.append("缺融资材料 owner")
    if "销售" not in roles:
        blockers.append("商业化证据不足")
    if employees < 10:
        blockers.append("团队偏小")
    blocker_text = f"；主要约束：{'、'.join(blockers[:2])}" if blockers else "；当前团队条件能支撑该节奏"
    return f"{lead}：模型信号 {model_score:.2f}，规则推进分 {round(prob * 100)}。{action}{blocker_text}。"


def build_timeline(payload: dict[str, object], forecast: dict[str, object]) -> list[dict[str, object]]:
    dataset = str(payload.get("dataset", "china"))
    industry = str(payload.get("industry", "目标行业"))
    metro = str(payload.get("metro", ""))
    stage = str(payload.get("stage", "种子轮"))
    employees = int(payload.get("employees") or 12)
    runway = int(payload.get("runway") or 9)
    roles = set(payload.get("roles") or [])
    stages = next_stages(stage)
    values = forecast.get("values") or []

    timeline = []

    team_lift = min(0.14, len(roles) * 0.018)
    role_lift = (
        (0.1 if "财务" in roles else -0.08)
        + (0.09 if "销售" in roles else -0.06)
        + (0.05 if "产品" in roles else -0.04)
        + (0.03 if "运营" in roles else 0)
        + (0.03 if "法务" in roles else 0)
    )
    runway_lift = 0.12 if runway >= 18 else 0.06 if runway >= 12 else -0.08 if runway >= 6 else -0.18
    condition_lift = context_lift(dataset, industry, metro, employees, roles)
    month_step = 4 if dataset == "overseas" else 6

    for idx, stage_name in enumerate(stages[:4]):
        model_score = values[min(idx, len(values) - 1)]["score"] if values else 0.45
        prob = max(0.12, min(0.92, 0.2 + model_score * 0.42 + team_lift + role_lift + runway_lift + condition_lift - idx * 0.05))
        speed_up = (
            (1 if "财务" in roles else 0)
            + (1 if "销售" in roles else 0)
            + (1 if "法务" in roles else 0)
            + (1 if runway >= 12 else 0)
            + (1 if employees >= 20 else 0)
        )
        month = max(2, (idx + 1) * max(2, month_step - speed_up) + int(model_score * 5) + (4 if runway < 6 else 0) + (2 if employees < 8 else 0))
        timeline.append(
            {
                "type": "finance",
                "month": month,
                "title": f"{stage_name}窗口",
                "copy": finance_window_copy(stage_name, idx, month, model_score, prob, employees, runway, roles),
                "prob": round(prob, 4),
                "source": "模型+规则：推进分=0.2+PatchTST×0.42+团队+角色+runway+地区/行业-阶段衰减",
            }
        )

    if len(roles) < 4 or "财务" not in roles or "销售" not in roles or employees < 10:
        timeline.append(
            {
                "type": "risk",
                "month": 3,
                "title": "团队补强节点",
                "copy": team_gap_copy(employees, roles, runway),
                "prob": round(max(0.35, min(0.78, 0.62 - role_lift / 3 - condition_lift / 4)), 4),
                "source": "规则：优先级=角色缺口、团队规模和地区/行业条件加权",
            }
        )

    return sorted(timeline, key=lambda item: item["month"])


def build_actions(payload: dict[str, object], forecast: dict[str, object]) -> list[str]:
    values = forecast.get("values") or []
    peak = max(values, key=lambda item: item["score"], default={"month": 1, "score": 0})
    roles = set(payload.get("roles") or [])
    metro = str(payload.get("metro", ""))
    actions = [
        f"围绕 T+{peak['month']} 月的 PatchTST 高信号窗口准备下一轮融资材料。",
        "把月度融资事件、团队变化和工商变化继续补齐到公司级 panel 数据。",
    ]
    if "财务" not in roles:
        actions.append("补充财务/融资负责人，降低尽调材料风险。")
    if "销售" not in roles:
        actions.append("补充商业化负责人，用客户和收入信号增强融资叙事。")
    if metro in ("BJ", "SH", "Hong Kong", "New York") and "法务" not in roles:
        actions.append(f"{metro} 样本涉及更多融资和股权事件，建议提前准备合规材料。")
    return actions[:4]


def simulate(payload: dict[str, object]) -> dict[str, object]:
    dataset = str(payload.get("dataset", "china"))
    forecast = condition_forecast(payload, patchtst_forecast(dataset))
    timeline = build_timeline(payload, forecast)
    return {
        "ok": True,
        "served_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "patchtst-backend",
        "dataset": dataset,
        "patchtst": forecast,
        "timeline": timeline,
        "actions": build_actions(payload, forecast),
    }


def extract_gemini_text(response: dict[str, object]) -> str:
    texts: list[str] = []
    for candidate in response.get("candidates", []) if isinstance(response.get("candidates"), list) else []:
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content") if isinstance(candidate.get("content"), dict) else {}
        for part in content.get("parts", []) if isinstance(content.get("parts"), list) else []:
            if isinstance(part, dict) and part.get("text"):
                texts.append(str(part["text"]))
    return "\n".join(texts).strip()


def ask_gemini(payload: dict[str, object]) -> dict[str, object]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("服务器尚未配置 GEMINI_API_KEY")
    question = str(payload.get("question", "")).strip()
    if not question:
        raise ValueError("问题不能为空")
    if len(question) > 500:
        raise ValueError("问题不能超过 500 个字符")
    context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
    history = payload.get("history") if isinstance(payload.get("history"), list) else []
    safe_history = [item for item in history[-6:] if isinstance(item, dict) and item.get("role") in ("user", "assistant")]
    contents = [
        {"role": "model" if item["role"] == "assistant" else "user", "parts": [{"text": str(item.get("content", ""))[:1200]}]}
        for item in safe_history
    ]
    contents.append({
        "role": "user",
        "parts": [{"text": f"当前公司数据：\n{json.dumps(context, ensure_ascii=False)}\n\n用户问题：{question}"}],
    })
    request_body = {
        "systemInstruction": {"parts": [{"text": (
            "你是创投与公司金融分析助手。只根据用户提供的当前公司数据回答，使用简洁、专业、易懂的中文。"
            "必须区分历史事实、模型预测和缺失数据；不得把未披露写成零，不得虚构公司、人员、金额或概率。"
            "涉及预测时说明概率、时间和金额口径；涉及IPO或并购时明确这是事实还是参考概率。"
            "答案控制在250字内，不作收益承诺，并在数据不足时直接说明需要补充什么。"
        )}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 2048},
    }
    request = Request(
        GEMINI_API_URL,
        data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Gemini API 请求失败（HTTP {exc.code}）：{detail}") from exc
    except URLError as exc:
        raise RuntimeError("无法连接 Gemini API，请检查服务器网络") from exc
    answer = extract_gemini_text(result)
    if not answer:
        raise RuntimeError("Gemini API 未返回可用文本")
    return {"ok": True, "answer": answer, "model": GEMINI_MODEL, "provider": "Gemini"}


class DemoHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def send_json(self, body: dict[str, object], status: int = 200) -> None:
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        if self.path == "/api/status":
            self.send_json(
                {
                    "ok": True,
                    "mode": "patchtst-backend",
                    "metrics": load_metrics(),
                    "ai": {"configured": bool(os.getenv("GEMINI_API_KEY", "").strip()), "model": GEMINI_MODEL, "provider": "Gemini"},
                }
            )
            return

        url_path = unquote(self.path.split("?", 1)[0])
        if url_path in ("", "/"):
            url_path = "/demo/index.html"
        if url_path.endswith("/"):
            url_path += "index.html"
        target = (ROOT / url_path.lstrip("/")).resolve()
        if not str(target).startswith(str(ROOT.resolve())) or not target.exists() or target.is_dir():
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        raw = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self) -> None:
        if self.path not in ("/api/simulate", "/api/assistant"):
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 64 * 1024:
                self.send_json({"ok": False, "error": "请求内容过大"}, status=413)
                return
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            self.send_json(ask_gemini(payload) if self.path == "/api/assistant" else simulate(payload))
        except Exception as exc:  # noqa: BLE001
            status = 503 if "GEMINI_API_KEY" in str(exc) else 502 if self.path == "/api/assistant" else 500
            self.send_json({"ok": False, "error": str(exc)}, status=status)


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8787"))
    server = ThreadingHTTPServer((host, port), DemoHandler)
    print(f"ESCP demo backend running: http://{host}:{port}/demo/")
    print("API: GET /api/status, POST /api/simulate, POST /api/assistant")
    server.serve_forever()


if __name__ == "__main__":
    main()

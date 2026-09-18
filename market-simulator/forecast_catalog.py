"""Versioned materialized predictions for the investor opportunity pool."""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from model_forecast import EXPECTED_EVENTS


class ForecastCatalog:
    def __init__(self, path, as_of):
        self.path = Path(path)
        self.as_of = as_of
        self.lock = threading.Lock()
        self.rows = {}
        self.generated_at = None
        self.load()

    def load(self):
        if not self.path.is_file():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if (payload.get("version") != 1 or payload.get("as_of") != self.as_of or
                    payload.get("events") != list(EXPECTED_EVENTS)):
                return
            rows = payload.get("predictions", {})
            if isinstance(rows, dict):
                self.rows = rows
                self.generated_at = payload.get("generated_at")
        except (OSError, ValueError, TypeError):
            self.rows = {}

    def _write(self):
        self.path.parent.mkdir(exist_ok=True)
        payload = {
            "version": 1,
            "as_of": self.as_of,
            "events": list(EXPECTED_EVENTS),
            "generated_at": self.generated_at,
            "predictions": self.rows,
        }
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        temporary.replace(self.path)

    def record(self, result, persist=True):
        if not result.get("available") or result.get("as_of") != self.as_of:
            return
        with self.lock:
            self.rows[result["company"]] = result
            self.generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            if persist:
                self._write()

    def get(self, company):
        with self.lock:
            return self.rows.get(company)

    def record_many(self, results, persist=True):
        with self.lock:
            for result in results:
                if result.get("available") and result.get("as_of") == self.as_of:
                    self.rows[result["company"]] = result
            self.generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            if persist:
                self._write()

    def save(self):
        with self.lock:
            self._write()

    def query(self, companies, watchlist, event="融资", months=12, query="",
              watched=False, page=1, page_size=24, current_month=0):
        if event not in EXPECTED_EVENTS:
            raise ValueError("事件筛选无效")
        if months not in (3, 6, 12):
            raise ValueError("时间范围无效")
        query = query.strip().lower()[:100]
        metadata = {item["id"]: item for item in companies}
        rows = []
        with self.lock:
            predictions = list(self.rows.items())
            generated_at = self.generated_at
        for company, prediction in predictions:
            item = metadata.get(company)
            if not item or (watched and company not in watchlist):
                continue
            text = " ".join(str(item.get(key, "")) for key in ("name", "industry", "region"))
            if query and query not in text.lower():
                continue
            matched = next((value for value in prediction["events"]
                            if value["event"] == event and value["predicted"] and
                            current_month < value["month_index"] <= current_month + months), None)
            if not matched:
                continue
            predicted = sorted((value for value in prediction["events"]
                                if value["predicted"] and value["month_index"] > current_month),
                               key=lambda value: value["month_index"])
            rows.append({
                "company": company,
                "name": item.get("name", company),
                "industry": item.get("industry", "未披露"),
                "region": item.get("region", "未披露"),
                "watched": company in watchlist,
                "next_event": predicted[0] if predicted else matched,
                "matched_event": matched,
                "predicted_events": predicted,
                "history_nodes": prediction.get("history_nodes"),
                "history_end": prediction.get("history_end"),
            })
        rows.sort(key=lambda row: (row["matched_event"]["month_index"],
                                   -(row.get("history_nodes") or 0), row["name"]))
        total = len(rows)
        pages = max(1, (total + page_size - 1) // page_size)
        page = max(1, min(page, pages))
        return {
            "as_of": self.as_of,
            "generated_at": generated_at,
            "coverage": sum(1 for company, _ in predictions if company in metadata),
            "universe": len(companies),
            "event": event,
            "months": months,
            "total": total,
            "page": page,
            "pages": pages,
            "items": rows[(page - 1) * page_size:page * page_size],
        }

"""Authenticated bridge to the persistent, local financial-model worker."""

import atexit
import hashlib
import json
import os
import selectors
import subprocess
import sys
import threading
from collections import OrderedDict
from pathlib import Path


EXPECTED_EVENTS = (
    "融资", "企业／机构股东进入", "股权结构变更", "注册资本变更", "注销",
)


class ModelProcessError(RuntimeError):
    """The local worker stopped or returned an unreadable transport response."""


class ModelInferenceError(RuntimeError):
    """The worker completed the request but could not run the inference."""


class ModelForecast:
    """Run one retained model against each company's complete dated history."""

    def __init__(self, worker, companies, as_of, python=None, timeout=None):
        self.worker = Path(worker)
        self.as_of = as_of
        self.companies = {item["id"]: item for item in companies}
        self.python = Path(python or os.environ.get(
            "MODEL_PYTHON", sys.executable))
        self.timeout = float(timeout or os.environ.get("MODEL_TIMEOUT_SECONDS", "180"))
        self.process = None
        self.log_stream = None
        self.lock = threading.Lock()
        self.cache = OrderedDict()
        atexit.register(self.close)

    def _available(self):
        return self.worker.is_file() and self.python.is_file()

    def _start(self):
        if self.process is not None and self.process.poll() is None:
            return
        self.close()
        if not self._available():
            raise RuntimeError("模型运行环境尚未配置")
        runtime = self.worker.resolve().parents[1] / "market-simulator/runtime"
        runtime.mkdir(exist_ok=True)
        self.log_stream = (runtime / "model-worker.log").open("a", encoding="utf-8")
        environment = os.environ.copy()
        environment.setdefault("PYTHONUNBUFFERED", "1")
        self.process = subprocess.Popen(
            [str(self.python), str(self.worker)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.log_stream,
            text=True,
            encoding="utf-8",
            bufsize=1,
            env=environment,
        )

    def warm(self):
        """Start loading model assets without blocking the website startup."""
        with self.lock:
            try:
                self._start()
                return True
            except RuntimeError:
                return False

    def close(self):
        process, self.process = self.process, None
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if self.log_stream is not None:
            self.log_stream.close()
            self.log_stream = None

    def _request_worker_once(self, payload):
        self._start()
        try:
            self.process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
            self.process.stdin.flush()
            selector = selectors.DefaultSelector()
            selector.register(self.process.stdout, selectors.EVENT_READ)
            if not selector.select(self.timeout):
                self.close()
                raise TimeoutError("模型推理超时")
            line = self.process.stdout.readline()
        except (BrokenPipeError, OSError):
            self.close()
            raise ModelProcessError("模型推理进程已停止") from None
        finally:
            if "selector" in locals():
                selector.close()
        if not line:
            self.close()
            raise ModelProcessError("模型推理进程未返回结果")
        try:
            response = json.loads(line)
        except json.JSONDecodeError:
            self.close()
            raise ModelProcessError("模型推理进程返回了无效结果") from None
        if not response.get("ok"):
            raise ModelInferenceError(response.get("error") or "模型推理失败")
        return response["result"]

    def _request_worker(self, payload):
        """Retry one interrupted custom/scenario request with a fresh worker."""
        retryable = payload.get("op") in {"custom", "scenario"}
        attempts = 2 if retryable else 1
        for attempt in range(attempts):
            try:
                return self._request_worker_once(payload)
            except (ModelProcessError, TimeoutError):
                if attempt + 1 == attempts:
                    raise
                self.close()

    @staticmethod
    def _validate(result, company, as_of, mode="live_full_history_inference"):
        if (result.get("mode") != mode or
                result.get("company") != company or result.get("as_of") != as_of or
                result.get("all_history") is not True or
                not isinstance(result.get("history_nodes"), int) or
                result["history_nodes"] < 1):
            raise ValueError("模型返回的历史范围无效")
        events = result.get("events")
        if (not isinstance(events, list) or len(events) != len(EXPECTED_EVENTS) or
                [item.get("event") for item in events] != list(EXPECTED_EVENTS)):
            raise ValueError("模型返回的事件定义无效")
        for item in events:
            predicted = item.get("predicted")
            month = item.get("month_index")
            estimate = item.get("estimated_month")
            if (type(predicted) is not bool or
                    (predicted and (type(month) is not int or not 1 <= month <= 12 or
                                    not isinstance(estimate, str))) or
                    (not predicted and (month is not None or estimate is not None))):
                raise ValueError("模型返回的事件结果无效")
        years = result.get("history_years")
        if (not isinstance(years, list) or not years or len(years) > 200 or
                sum(item.get("count", 0) for item in years) != result["history_nodes"]):
            raise ValueError("模型返回的历史时间轴无效")
        previous = 0
        for item in years:
            if (type(item.get("year")) is not int or item["year"] <= previous or
                    type(item.get("count")) is not int or item["count"] < 1 or
                    not isinstance(item.get("events"), list) or len(item["events"]) > 4):
                raise ValueError("模型返回的历史时间轴无效")
            previous = item["year"]
            for event in item["events"]:
                if (not isinstance(event.get("event"), str) or
                        type(event.get("count")) is not int or event["count"] < 1):
                    raise ValueError("模型返回的历史时间轴无效")
        if "probability" in json.dumps(result):
            raise ValueError("网站响应不应暴露内部发生分数")
        return result

    def get(self, company):
        item = self.companies.get(company)
        if item is None:
            raise KeyError(company)
        if item.get("closed"):
            return {
                "available": False,
                "reason": "该企业在当前资料截止日前已经注销或撤销，不再预测未来经营事件。",
                "as_of": self.as_of,
            }
        if not self._available():
            return {
                "available": False,
                "reason": "本机尚未配置模型运行环境。",
                "as_of": self.as_of,
            }
        key = (company, self.as_of)
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
            raw = self._request_worker({"company": company, "as_of": self.as_of})
            if raw.get("available") is False:
                result = {
                    "available": False,
                    "reason": raw.get("reason") or "没有可供模型读取的历史信息。",
                    "as_of": self.as_of,
                }
                self.cache[key] = result
                return result
            result = self._validate(raw, company, self.as_of)
            result["available"] = True
            self.cache[key] = result
            while len(self.cache) > 256:
                self.cache.popitem(last=False)
            return result

    def get_many(self, companies):
        """Run a bounded batch for the versioned investor forecast catalog."""
        requested = list(dict.fromkeys(companies))
        if not requested or len(requested) > 256:
            raise ValueError("批量预测每次只允许1至256家企业")
        unknown = [company for company in requested if company not in self.companies]
        if unknown:
            raise KeyError(unknown[0])
        results = []
        pending = []
        with self.lock:
            for company in requested:
                item = self.companies[company]
                key = (company, self.as_of)
                if item.get("closed"):
                    results.append({
                        "available": False,
                        "company": company,
                        "reason": "该企业在当前资料截止日前已经注销或撤销。",
                        "as_of": self.as_of,
                    })
                elif key in self.cache:
                    results.append(self.cache[key])
                else:
                    pending.append(company)
            if pending:
                raw_results = self._request_worker({
                    "op": "batch", "companies": pending, "as_of": self.as_of,
                })
                if not isinstance(raw_results, list):
                    raise ValueError("模型批量结果无效")
                for raw in raw_results:
                    company = raw.get("company")
                    if raw.get("available") is False:
                        results.append(raw)
                        continue
                    result = self._validate(raw, company, self.as_of)
                    result["available"] = True
                    self.cache[(company, self.as_of)] = result
                    results.append(result)
            order = {company: index for index, company in enumerate(requested)}
            return sorted(results, key=lambda row: order.get(row.get("company"), len(order)))

    def get_custom(self, events, as_of):
        if not isinstance(events, list) or not events:
            return {"available": False, "reason": "请先添加至少一个历史事件。",
                    "as_of": as_of}
        encoded = json.dumps(events, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":")).encode()
        digest = hashlib.sha256(encoded).hexdigest()
        company = "founder:" + digest[:16]
        key = ("custom", digest, as_of)
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
            raw = self._request_worker({
                "op": "custom",
                "company": company,
                "events": events,
                "as_of": as_of,
                "reference_cutoff": self.as_of,
            })
            if raw.get("available") is False:
                return raw
            result = self._validate(raw, company, as_of, mode="custom_path_inference")
            similar = result.get("similar")
            if not isinstance(similar, list) or len(similar) > 100:
                raise ValueError("相似企业结果无效")
            result["available"] = True
            self.cache[key] = result
            while len(self.cache) > 256:
                self.cache.popitem(last=False)
            return result

    def get_scenario(self, company, events, as_of):
        """Forecast after appending financing-plan actions to observed history."""
        item = self.companies.get(company)
        if item is None:
            raise KeyError(company)
        if item.get("closed"):
            return {"available": False, "reason": "企业已经注销或撤销。", "as_of": as_of}
        if not isinstance(events, list) or not 1 <= len(events) <= 20:
            raise ValueError("融资情景事件无效")
        encoded = json.dumps(events, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":")).encode()
        digest = hashlib.sha256(encoded).hexdigest()
        key = ("scenario", company, digest, as_of)
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
            raw = self._request_worker({
                "op": "scenario", "company": company, "events": events,
                "as_of": as_of, "reference_cutoff": self.as_of,
            })
            if raw.get("available") is False:
                return raw
            result = self._validate(
                raw, company, as_of, mode="financing_scenario_inference")
            scenario_events = result.get("scenario_events")
            if not isinstance(scenario_events, list) or len(scenario_events) != len(events):
                raise ValueError("融资情景事件返回无效")
            result["available"] = True
            self.cache[key] = result
            while len(self.cache) > 256:
                self.cache.popitem(last=False)
            return result

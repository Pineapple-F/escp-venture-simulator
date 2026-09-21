import tempfile
import unittest
from pathlib import Path

from model_forecast import (
    EXPECTED_EVENTS, ModelForecast, ModelInferenceError, ModelProcessError,
)


def live_result(company="co_a"):
    return {
        "mode": "live_full_history_inference",
        "company": company,
        "as_of": "2026-03-31",
        "horizon_start": "2026-04-01",
        "horizon_end": "2027-03-31",
        "all_history": True,
        "history_nodes": 17,
        "history_start": "2018-02-03",
        "history_end": "2026-03-01",
        "history_years": [
            {"year": 2018, "count": 8, "start": "2018-02-03", "end": "2018-12-01",
             "events": [{"event": "成立", "count": 1}, {"event": "工商变更", "count": 7}]},
            {"year": 2026, "count": 9, "start": "2026-01-01", "end": "2026-03-01",
             "events": [{"event": "融资", "count": 2}, {"event": "企业年报", "count": 7}]},
        ],
        "model": "固定模型",
        "events": [
            {"event": event, "predicted": index == 0,
             "month_index": 3 if index == 0 else None,
             "estimated_month": "2026-06" if index == 0 else None}
            for index, event in enumerate(EXPECTED_EVENTS)
        ],
    }


def custom_result(company="founder:test", as_of="2026-09-17"):
    result = live_result(company)
    result.update(mode="custom_path_inference", as_of=as_of,
                  horizon_start="2026-09-18", horizon_end="2027-10-31",
                  recent_history=[{"date": "2024-01-01", "event": "公司成立"}],
                  similar=[])
    return result


def scenario_result(company="co_a", as_of="2026-03-31"):
    result = live_result(company)
    result.update(
        mode="financing_scenario_inference",
        as_of=as_of,
        history_nodes=19,
        history_end=as_of,
        scenario_events=[
            {"date": as_of, "event": "融资方案确定"},
            {"date": as_of, "event": "选择融资机构"},
        ],
    )
    result["history_years"][-1]["count"] += 2
    return result


class FakeForecast(ModelForecast):
    def __init__(self, response=None, companies=None):
        temp = tempfile.NamedTemporaryFile()
        self._temp = temp
        super().__init__(temp.name, companies or [{"id": "co_a", "closed": False}],
                         "2026-03-31", python=temp.name)
        self.response = response or live_result()
        self.calls = 0

    def _request_worker(self, payload):
        self.calls += 1
        self.last_payload = payload
        return self.response


class TransportForecast(ModelForecast):
    def __init__(self, outcomes):
        temp = tempfile.NamedTemporaryFile()
        self._temp = temp
        super().__init__(temp.name, [{"id": "co_a", "closed": False}],
                         "2026-03-31", python=temp.name)
        self.outcomes = list(outcomes)
        self.transport_calls = 0

    def _request_worker_once(self, payload):
        self.transport_calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    def close(self):
        self.process = None


class ModelForecastTest(unittest.TestCase):
    def test_warm_starts_available_worker(self):
        forecast = FakeForecast()
        started = []
        forecast._start = lambda: started.append(True)
        self.assertTrue(forecast.warm())
        self.assertEqual(started, [True])

    def test_returns_live_full_history_result_without_internal_scores(self):
        forecast = FakeForecast()
        result = forecast.get("co_a")
        self.assertTrue(result["available"])
        self.assertTrue(result["all_history"])
        self.assertEqual(result["events"][0]["estimated_month"], "2026-06")
        self.assertNotIn("probability", str(result))

    def test_cache_avoids_duplicate_inference(self):
        forecast = FakeForecast()
        self.assertEqual(forecast.get("co_a"), forecast.get("co_a"))
        self.assertEqual(forecast.calls, 1)

    def test_batch_results_are_validated_and_cached(self):
        response = [live_result("co_a"), live_result("co_b")]
        forecast = FakeForecast(response=response, companies=[
            {"id": "co_a", "closed": False}, {"id": "co_b", "closed": False}])
        results = forecast.get_many(["co_a", "co_b"])
        self.assertEqual([row["company"] for row in results], ["co_a", "co_b"])
        self.assertEqual(forecast.get("co_a")["company"], "co_a")
        self.assertEqual(forecast.calls, 1)

    def test_custom_path_uses_separate_mode_and_cache(self):
        response = custom_result()
        forecast = FakeForecast(response=response)
        events = [{"date": "2024-01-01", "type": 8, "subtype": "founded"}]
        # The worker response company is content-addressed by the bridge.
        import hashlib, json
        digest = hashlib.sha256(json.dumps(events, ensure_ascii=False, sort_keys=True,
            separators=(",", ":")).encode()).hexdigest()
        forecast.response["company"] = "founder:" + digest[:16]
        first = forecast.get_custom(events, "2026-09-17")
        second = forecast.get_custom(events, "2026-09-17")
        self.assertEqual(first["mode"], "custom_path_inference")
        self.assertEqual(first, second)
        self.assertEqual(forecast.calls, 1)

    def test_financing_scenario_appends_events_and_uses_separate_cache(self):
        events = [
            {"date": "2026-03-31", "type": 1, "stage": -1, "role": 0,
             "subtype": "financing_plan", "label": "融资方案确定", "detail": "目标1亿元"},
            {"date": "2026-03-31", "type": 4, "stage": -1, "role": 0,
             "subtype": "institution_selection", "label": "选择融资机构", "detail": "机构甲"},
        ]
        forecast = FakeForecast(response=scenario_result())
        first = forecast.get_scenario("co_a", events, "2026-03-31")
        second = forecast.get_scenario("co_a", events, "2026-03-31")
        self.assertEqual(first["mode"], "financing_scenario_inference")
        self.assertEqual(first["scenario_events"][1]["event"], "选择融资机构")
        self.assertEqual(first, second)
        self.assertEqual(forecast.calls, 1)
        self.assertEqual(forecast.last_payload["op"], "scenario")
        self.assertEqual(forecast.last_payload["reference_cutoff"], "2026-03-31")

    def test_scenario_retries_one_interrupted_worker_request(self):
        forecast = TransportForecast([
            ModelProcessError("worker stopped"), scenario_result(),
        ])
        result = forecast._request_worker({"op": "scenario"})
        self.assertEqual(result["mode"], "financing_scenario_inference")
        self.assertEqual(forecast.transport_calls, 2)

    def test_scenario_does_not_retry_deterministic_inference_error(self):
        forecast = TransportForecast([ModelInferenceError("invalid input")])
        with self.assertRaises(ModelInferenceError):
            forecast._request_worker({"op": "scenario"})
        self.assertEqual(forecast.transport_calls, 1)

    def test_regular_forecast_does_not_retry_transport_error(self):
        forecast = TransportForecast([ModelProcessError("worker stopped")])
        with self.assertRaises(ModelProcessError):
            forecast._request_worker({"company": "co_a"})
        self.assertEqual(forecast.transport_calls, 1)

    def test_closed_company_is_not_predicted(self):
        forecast = FakeForecast(companies=[{"id": "co_a", "closed": True}])
        result = forecast.get("co_a")
        self.assertFalse(result["available"])
        self.assertEqual(forecast.calls, 0)

    def test_unknown_company_is_rejected(self):
        forecast = FakeForecast()
        with self.assertRaises(KeyError):
            forecast.get("missing")

    def test_empty_history_response_is_preserved(self):
        response = {"available": False, "company": "co_a", "as_of": "2026-03-31",
                    "reason": "没有有效历史"}
        result = FakeForecast(response=response).get("co_a")
        self.assertFalse(result["available"])
        self.assertEqual(result["reason"], "没有有效历史")

    def test_invalid_event_order_is_rejected(self):
        response = live_result()
        response["events"] = list(reversed(response["events"]))
        with self.assertRaises(ValueError):
            FakeForecast(response=response).get("co_a")


if __name__ == "__main__":
    unittest.main()

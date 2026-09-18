import tempfile
import unittest
from pathlib import Path

from forecast_catalog import ForecastCatalog
from forecast_workflow import transact
from custom_path import normalize, taxonomy


def state():
    return {"version": 3, "revision": 1}


UNIVERSE = {"companies": [{"id": "co_a"}]}


class ForecastWorkflowTest(unittest.TestCase):
    def test_founder_plan_is_stored_separately_from_prediction(self):
        result = transact(state(), {"type": "forecast_plan", "company": "co_a",
            "event": "融资", "status": "进行中", "due_month": "2026-07",
            "note": "准备材料"}, UNIVERSE)
        self.assertEqual(result["forecast_plans"]["co_a"]["融资"]["status"], "进行中")
        self.assertEqual(result["revision"], 2)

    def test_followup_adds_company_to_watchlist(self):
        result = transact(state(), {"type": "forecast_followup", "company": "co_a",
            "event": "股权结构变更", "status": "待研判", "due_month": None,
            "note": ""}, UNIVERSE)
        self.assertIn("co_a", result["forecast_watchlist"])

    def test_founder_builds_standard_event_path_without_free_text(self):
        saved = transact(state(), {"type": "founder_custom_profile",
            "name": "远航科技", "industry": "软件", "region": "上海"}, UNIVERSE)
        added = transact(saved, {"type": "founder_custom_event_add",
            "date": "2021-03-01", "category": "foundation", "subtype": "founded"},
            UNIVERSE)
        event = added["founder_custom"]["events"][0]
        self.assertEqual(event["type"], 8)
        self.assertEqual(event["label"], "公司成立")
        self.assertEqual(event["source"], "企业用户自报")
        removed = transact(added, {"type": "founder_custom_event_delete",
            "event_id": event["id"]}, UNIVERSE)
        self.assertEqual(removed["founder_custom"]["events"], [])

    def test_custom_taxonomy_has_only_known_pairs(self):
        self.assertGreaterEqual(len(taxonomy()), 6)
        self.assertEqual(normalize("financing", "angel")["stage"], 1)
        with self.assertRaises(ValueError):
            normalize("unknown", "unknown")

    def test_custom_enterprise_can_save_action_and_finance_draft(self):
        saved = transact(state(), {"type": "founder_custom_profile",
            "name": "远航科技", "industry": "软件", "region": "上海"}, UNIVERSE)
        planned = transact(saved, {"type": "forecast_plan", "company": "founder_custom",
            "event": "融资", "status": "进行中", "due_month": "2027-01",
            "note": "准备材料"}, UNIVERSE)
        drafted = transact(planned, {"type": "founder_custom_finance_plan",
            "currency": "CNY", "target": "1000000", "cash": "200000",
            "burn": "50000", "purpose": "产品研发"}, UNIVERSE)
        self.assertEqual(drafted["forecast_plans"]["founder_custom"]["融资"]["status"], "进行中")
        self.assertEqual(drafted["founder_custom_finance_plan"]["cash"], 200000)
        self.assertEqual(drafted["founder_custom_finance_plan"]["purpose"], "产品研发")
        with self.assertRaises(ValueError):
            transact(drafted, {"type": "forecast_watch", "company": "founder_custom",
                "enabled": True}, UNIVERSE)

    def test_custom_finance_draft_rejects_invalid_amount(self):
        saved = transact(state(), {"type": "founder_custom_profile",
            "name": "远航科技", "industry": "", "region": ""}, UNIVERSE)
        with self.assertRaises(ValueError):
            transact(saved, {"type": "founder_custom_finance_plan",
                "currency": "CNY", "target": "nan", "cash": "",
                "burn": "", "purpose": ""}, UNIVERSE)


class ForecastCatalogTest(unittest.TestCase):
    def test_query_filters_event_and_horizon(self):
        with tempfile.TemporaryDirectory() as directory:
            catalog = ForecastCatalog(Path(directory) / "catalog.json", "2026-03-31")
            catalog.record({"available": True, "company": "co_a", "as_of": "2026-03-31",
                "history_nodes": 8, "history_end": "2026-01-01", "events": [
                    {"event": name, "predicted": name == "融资",
                     "month_index": 4 if name == "融资" else None,
                     "estimated_month": "2026-07" if name == "融资" else None}
                    for name in ("融资", "企业／机构股东进入", "股权结构变更", "注册资本变更", "注销")
                ]})
            companies = [{"id": "co_a", "name": "甲公司", "industry": "软件", "region": "北京"}]
            self.assertEqual(catalog.query(companies, {}, "融资", 3)["total"], 0)
            self.assertEqual(catalog.query(companies, {}, "融资", 6)["total"], 1)
            self.assertEqual(catalog.query(companies, {}, "融资", 3, current_month=1)["total"], 1)
            self.assertEqual(catalog.query(companies, {}, "融资", 12, current_month=4)["total"], 0)
            self.assertEqual(catalog.query(companies + [{"id": "co_b", "name": "乙公司"}], {},
                                           "融资", 6)["coverage"], 1)
            self.assertEqual(catalog.get("co_a")["company"], "co_a")

    def test_catalog_with_different_event_definition_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text('{"version":1,"as_of":"2026-03-31","events":["旧事件"],"predictions":{"co_a":{}}}')
            self.assertEqual(ForecastCatalog(path, "2026-03-31").rows, {})


if __name__ == "__main__":
    unittest.main()

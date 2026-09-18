import unittest

from financing_scenario import build


class FinancingScenarioTest(unittest.TestCase):
    def setUp(self):
        self.state = {
            "as_of": "2026-03-31",
            "founder_plans": {
                "co_a": {
                    "currency": "CNY", "target": 1000, "pre_money": 5000,
                    "cash": 300, "burn": 50, "purpose": "产品研发与团队招聘",
                    "budget": {"research": 700, "hiring": 300},
                }
            },
            "founder_contacts": {
                "co_a": {
                    "inst_a": {"name": "机构甲", "stage": "已沟通"},
                }
            },
        }
        self.institutions = {
            "inst_a": {
                "rounds": [
                    {"company": "co_x"}, {"company": "co_y"},
                    {"company": "co_x"},
                ]
            }
        }

    def test_plan_and_institution_become_dated_scenario_events(self):
        result = build(self.state, "co_a", self.institutions)
        self.assertTrue(result["ready"])
        self.assertEqual(result["as_of"], "2026-03-31")
        self.assertEqual([event["label"] for event in result["events"]],
                         ["融资方案确定", "选择融资机构"])
        self.assertIn("目标融资1000 CNY", result["events"][0]["detail"])
        self.assertIn("机构甲", result["events"][1]["detail"])

    def test_missing_first_steps_do_not_run_scenario(self):
        result = build({"as_of": "2026-03-31"}, "co_a", self.institutions)
        self.assertFalse(result["ready"])
        self.assertEqual(result["events"], [])
        self.assertIn("融资方案", result["missing"])
        self.assertIn("目标机构", result["missing"])

    def test_execution_progress_moves_scenario_cutoff_forward(self):
        self.state["founder_rounds"] = {
            "co_a": {
                "date": "2026-04-07", "week": 1, "raised": 0,
                "applications": {"inst_a": {"status": "submitted"}},
            }
        }
        result = build(self.state, "co_a", self.institutions)
        self.assertEqual(result["as_of"], "2026-04-07")
        self.assertEqual(result["events"][-1]["label"], "融资流程推进")
        self.assertTrue(all(event["date"] <= result["as_of"] for event in result["events"]))


if __name__ == "__main__":
    unittest.main()

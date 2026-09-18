import tempfile
import unittest
from pathlib import Path

import duckdb

from cohort_filter import model_ready_companies


class CohortFilterTest(unittest.TestCase):
    def test_clean_v1_history_threshold_uses_only_past_months(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.parquet"
            database = duckdb.connect()
            database.execute("CREATE TABLE history(id VARCHAR, day DATE)")
            database.executemany("INSERT INTO history VALUES (?, ?)", [
                ("good", "2020-01-01"), ("good", "2020-02-02"),
                ("good", "2020-07-03"),
                ("few", "2020-01-01"), ("few", "2020-08-01"),
                ("short", "2020-01-01"), ("short", "2020-02-01"),
                ("short", "2020-03-01"),
                ("future", "2020-01-01"), ("future", "2020-02-01"),
                ("future", "2021-01-01"),
            ])
            database.execute("COPY history TO ? (FORMAT PARQUET)", [str(path)])
            eligible, audit = model_ready_companies(
                {"good", "few", "short", "future", "absent"}, [path], "2020-12-31")
            self.assertEqual(eligible, {"good"})
            self.assertEqual(audit["cohort_before_history_filter"], 5)
            self.assertEqual(audit["history_sparse_excluded"], 4)

    def test_missing_clean_history_is_rejected(self):
        with self.assertRaises(FileNotFoundError):
            model_ready_companies({"company"}, ["missing.parquet"], "2020-12-31")


if __name__ == "__main__":
    unittest.main()

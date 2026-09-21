"""Unified active-company cohort and five future-event targets."""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent
SEQUENCE = RESEARCH / "enterprise_path_sequence"
CANDIDATE = RESEARCH / "enterprise_path_candidate_screening"
CLEAN = RESEARCH / "enterprise_path_clean"
sys.path.insert(0, str(SEQUENCE))

from semantic import SemanticDataset, SemanticCollator  # noqa: E402

_spec = importlib.util.spec_from_file_location("unified_candidate_data", CANDIDATE / "data.py")
_candidate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_candidate)

EVENTS = ("融资", "企业／机构股东进入", "股权结构变更", "注册资本变更", "注销")


def _dates_by_company(frame):
    frame = frame[["id", "day"]].dropna().drop_duplicates().copy()
    return {
        str(cid): np.sort(group.day.to_numpy(dtype="datetime64[D]"))
        for cid, group in frame.groupby("id", sort=False)
    }


class Histories(_candidate.Histories):
    def __init__(self):
        super().__init__()
        change = self.table("change").drop_duplicates().reset_index(drop=True)
        change_day = _candidate.parse_date(change.change_date)
        capital = change.change_type.fillna("").str.contains("注册资本")
        self.capital_dates = _dates_by_company(pd.DataFrame({
            "id": change.loc[capital, "company_id_anon"].astype(str),
            "day": change_day[capital],
        }))
        company = self.table("company").drop_duplicates().reset_index(drop=True)
        cancel_day = _candidate.parse_date(company.cancel_date)
        self.cancel_dates = _dates_by_company(pd.DataFrame({
            "id": company.companyid_anon.astype(str), "day": cancel_day,
        }))

    @staticmethod
    def first_future_month(mapping, company, year):
        values = mapping.get(str(company), np.empty(0, dtype="datetime64[D]"))
        start = np.datetime64(f"{int(year)+1}-01-01")
        end = np.datetime64(f"{int(year)+1}-12-31")
        hit = values[(values >= start) & (values <= end)]
        return None if not len(hit) else int(str(hit[0])[:7].split("-")[1])

    def target_months(self, company, year, old_y, old_time):
        result = [None] * len(EVENTS)
        finance = [float(old_time[k]) for k in (0, 1) if old_y[k] and old_time[k] > 0]
        if finance:
            result[0] = int(round(min(finance)))
        result[1] = self.first_month("institutional_shareholder_entry", company, year)
        result[2] = self.first_month("equity_structure", company, year)
        result[3] = self.first_future_month(self.capital_dates, company, year)
        result[4] = self.first_future_month(self.cancel_dates, company, year)
        return result


class UnifiedDataset:
    """Every retained row is eligible for every target; known prior cancellations are removed."""
    def __init__(self, histories, split, targets=False):
        self.histories, self.split, self.targets = histories, split, targets
        self.base = SemanticDataset(histories, split, targets=False)
        with np.load(CLEAN / "cache" / f"{split}.npz", allow_pickle=False) as z:
            self.raw = {k: z[k] for k in ("company", "year", "initial", "y", "time")}
        self.indices = np.flatnonzero(~self.raw["initial"][:, 2].astype(bool))

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, index):
        raw_index = int(self.indices[index])
        sample = self.base[raw_index]
        sample["allowed"] = np.ones(len(EVENTS), dtype=bool)
        year = int(sample["year"])
        frame = self.histories.before(sample["company"], year)
        if len(frame):
            founded = frame.loc[frame.type.eq(8), "day"]
            first = founded.min() if len(founded) else frame.day.min()
            age_months = max(0.0, (pd.Timestamp(year=year, month=12, day=31) - first).days / 30.4375)
        else:
            age_months = 0.0
        sample["company_age"] = np.float32(np.log1p(age_months) / 8.0)
        sample["era"] = np.int64(0 if year <= 2014 else (1 if year <= 2019 else 2))
        if self.targets:
            months = self.histories.target_months(
                sample["company"], year, self.raw["y"][raw_index], self.raw["time"][raw_index])
            points = [(mark + 1, month) for mark, month in enumerate(months) if month is not None]
            points.sort(key=lambda x: (x[1], x[0]))
            typ = np.zeros(len(EVENTS), np.int64)
            tim = np.zeros(len(EVENTS), np.float32)
            for j, (mark, month) in enumerate(points):
                typ[j], tim[j] = mark, month
            sample["targets"] = {
                "true_type": typ,
                "true_time": tim,
                "count": np.asarray(len(points), np.int64),
                "eligible": np.ones(len(EVENTS), dtype=bool),
            }
        return sample


class UnifiedCollator:
    def __init__(self, encoder):
        self.base = SemanticCollator(encoder)

    def __call__(self, samples):
        result = self.base(samples)
        history = result[0] if isinstance(result, tuple) else result
        history["company_age"] = np.asarray([s["company_age"] for s in samples], np.float32)
        history["era"] = np.asarray([s["era"] for s in samples], np.int64)
        import torch
        history["company_age"] = torch.from_numpy(history["company_age"])
        history["era"] = torch.from_numpy(history["era"])
        return result


def truth(dataset):
    n = len(dataset)
    y = np.zeros((n, len(EVENTS)), np.int8)
    tim = np.zeros((n, len(EVENTS)), np.float32)
    company = np.empty(n, dtype=dataset.raw["company"].dtype)
    year = np.empty(n, dtype=dataset.raw["year"].dtype)
    for i, raw_index in enumerate(dataset.indices):
        company[i], year[i] = dataset.raw["company"][raw_index], dataset.raw["year"][raw_index]
        months = dataset.histories.target_months(
            company[i], int(year[i]), dataset.raw["y"][raw_index], dataset.raw["time"][raw_index])
        for k, month in enumerate(months):
            if month is not None:
                y[i, k], tim[i, k] = 1, month
    return {"company": company, "year": year, "y": y, "time": tim,
            "eligible": np.ones_like(y, dtype=bool)}

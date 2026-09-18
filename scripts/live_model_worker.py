"""Persistent JSON-lines worker for full-history, next-12-month inference."""

import json
import math
import os
import sys
import importlib.util
import heapq
from collections import Counter
from datetime import date, timedelta
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
RESEARCH = Path(os.environ.get("ESCP_RESEARCH_ROOT", REPO.parent / "research"))
FRAMEWORK = RESEARCH / "enterprise_path_framework_10x3"
RUN = FRAMEWORK / "runs/20260915_165459"
EPOCH = RUN / "iteration_07_event_frequency/epoch_02"
FINANCE = RESEARCH / "enterprise_path_finance_knowledge"
UNIFIED = RESEARCH / "enterprise_path_unified_time"
SEQUENCE = RESEARCH / "enterprise_path_sequence"
CANDIDATE = RESEARCH / "enterprise_path_candidate_screening"
sys.path[:0] = [str(FRAMEWORK), str(FINANCE), str(RESEARCH / "enterprise_path_v3"),
                str(UNIFIED), str(SEQUENCE), str(CANDIDATE)]

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402

from data import attribute_tokens  # noqa: E402
from dataset import EVENTS, Histories, UnifiedCollator  # noqa: E402
from finance_text import FinancialTextEncoder  # noqa: E402
from framework_model import FrameworkModel  # noqa: E402
from network import corrupt, initial_noise, pack  # noqa: E402
from semantic import EVENT_NAMES, split_attributes  # noqa: E402


def yearly_history(frame, custom=False):
    """Compact every input node into a chronological, user-facing year summary."""
    years = []
    for year, rows in frame.groupby(frame.day.dt.year, sort=True):
        names = (rows.label.astype(str).tolist() if custom else
                 [EVENT_NAMES.get(int(value), "其他事件") for value in rows.type])
        counts = Counter(names)
        years.append({
            "year": int(year),
            "count": int(len(rows)),
            "start": rows.day.iloc[0].date().isoformat(),
            "end": rows.day.iloc[-1].date().isoformat(),
            "events": [{"event": name, "count": int(count)}
                       for name, count in counts.most_common(4)],
        })
    return years


class LiveFrameworkModel(FrameworkModel):
    """The retained architecture with device-safe decoder masks for GPU serving."""

    def forward(self, typ, src, cont, noisy_type, noisy_time, noisy_mask, step, allowed,
                era=None, company_age=None, **kwargs):
        history, pad, pooled = self.encode_sequence(
            typ, src, cont, era=era, company_age=company_age, **kwargs)
        features = torch.stack([noisy_time, torch.sin(math.pi * noisy_time),
                                torch.cos(math.pi * noisy_time)], -1)
        step_embedding = self.step_embedding(step)
        noise = (self.noisy_mark(noisy_type) + self.noisy_time(features) +
                 step_embedding[:, None])
        memory = torch.cat([pooled, history, noise], 1)
        memory_pad = torch.cat([
            torch.zeros((len(typ), len(EVENTS)), dtype=torch.bool, device=typ.device),
            pad,
            noisy_mask,
        ], 1)
        query = self.slot_query[None] + self.event_query[None] + step_embedding[:, None]
        decoded = self.decoder(query, memory, memory_key_padding_mask=memory_pad)
        logits = self.presence(decoded).squeeze(-1).masked_fill(~allowed, -12.0)
        months = 1 + 11 * self.month(decoded).squeeze(-1).sigmoid()
        if "occurrence_time" in self.active:
            normalized = (months - 6.5) / 5.5
            time_features = torch.stack((normalized, torch.sin(math.pi * normalized),
                                         torch.cos(math.pi * normalized)), -1)
            logits = logits + (time_features * self.time_occurrence[None]).sum(-1)
        if "target_relation" in self.active:
            relation = self.target_relation - torch.diag_embed(
                torch.diagonal(self.target_relation))
            logits = logits + torch.einsum("ij,bj->bi", relation, logits.tanh())
        return logits, months


class FinancialLookup:
    """Reuse training vectors and encode only event texts not seen in the cache."""

    def __init__(self, device):
        with np.load(FINANCE / "cache/finance_vectors.npz", allow_pickle=False) as saved:
            texts = saved["texts"].tolist()
            vectors = saved["vectors"].copy()
        self.dimension = vectors.shape[1]
        self.vectors = dict(zip(texts, vectors))
        self.device = device
        self.encoder = None
        self.last_cached = 0
        self.last_encoded = 0

    def encode(self, texts):
        unique_missing = list(dict.fromkeys(text for text in texts if text not in self.vectors))
        if unique_missing:
            if self.encoder is None:
                self.encoder = FinancialTextEncoder(str(self.device))
            vectors = self.encoder.encode(unique_missing)
            self.vectors.update(zip(unique_missing, vectors))
        self.last_encoded = len(unique_missing)
        self.last_cached = len(texts) - sum(text in unique_missing for text in texts)
        return (np.stack([self.vectors[text] for text in texts]) if texts
                else np.zeros((0, self.dimension), np.float32))


def add_month(year, month, offset):
    absolute = year * 12 + month - 1 + offset
    return absolute // 12, absolute % 12 + 1


def horizon(as_of):
    stamp = date.fromisoformat(as_of)
    start = stamp + timedelta(days=1)
    end_year, end_month = add_month(stamp.year, stamp.month, 13)
    end = date(end_year, end_month, 1) - timedelta(days=1)
    return start.isoformat(), end.isoformat()


class Worker:
    def __init__(self):
        torch.set_num_threads(int(os.environ.get("MODEL_CPU_THREADS", "2")))
        requested = os.environ.get("MODEL_DEVICE", "auto")
        if requested == "auto":
            requested = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(requested)
        best = json.loads((RUN / "BEST.json").read_text())
        result = json.loads((EPOCH / "result.json").read_text())
        checkpoint = torch.load(EPOCH / "model.pt", map_location="cpu", weights_only=False)
        if (best.get("iteration"), best.get("epoch")) != (7, 2):
            raise ValueError("Retained model pointer changed")
        if tuple(checkpoint.get("events", ())) != tuple(EVENTS):
            raise ValueError("Checkpoint event definition changed")
        self.model = LiveFrameworkModel(checkpoint["active"])
        self.model.load_state_dict(checkpoint["state_dict"], strict=True)
        self.model.to(self.device).eval()
        self.thresholds = np.asarray(
            [item["threshold"] for item in result["events"]], np.float32)
        self.histories = Histories()
        self.history_cutoff = None
        self.live_history_added = 0
        self.lookup = FinancialLookup(self.device)
        self.collator = UnifiedCollator(self.lookup)

    def extend_histories(self, cutoff):
        """Append post-training-cutoff nodes rebuilt with the original cleaning rules."""
        if self.history_cutoff == cutoff:
            return
        if self.history_cutoff is not None:
            raise ValueError("one worker serves one fixed website cutoff")
        cache = (REPO / "market-simulator/runtime" /
                 f"model-live-history-{cutoff}.parquet")
        rebuild = os.environ.get("MODEL_REBUILD_HISTORY") == "1"
        if cache.is_file() and not rebuild:
            added = pd.read_parquet(cache)
        else:
            cleaner_path = RESEARCH / "enterprise_path_clean/prepare.py"
            spec = importlib.util.spec_from_file_location("live_history_cleaner", cleaner_path)
            cleaner = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cleaner)
            _, merged, _, _, _, _, _ = cleaner.load_history(cutoff=cutoff)
            added = merged.loc[merged.day.gt(pd.Timestamp("2024-12-31"))].copy()
            cache.parent.mkdir(exist_ok=True)
            added.to_parquet(cache, index=False)
        if len(added):
            # Raw attributes are resolved only for the selected enterprise. Eagerly
            # expanding every post-2024 row adds minutes to the first request.
            added["attributes"] = None
            self.histories.records = pd.concat(
                [self.histories.records, added], ignore_index=True, sort=False)
            self.histories.records = self.histories.records.sort_values(
                ["id", "day", "type", "source", "uid"]).reset_index(drop=True)
            self.histories.groups = {
                company: indices for company, indices in
                self.histories.records.groupby("id", sort=False).indices.items()
            }
        self.live_history_added = len(added)
        self.history_cutoff = cutoff

    def sample(self, company, as_of):
        cutoff = pd.Timestamp(as_of)
        frame = self.histories.records.iloc[
            self.histories.groups.get(str(company), [])]
        frame = frame.loc[frame.day.le(cutoff)].copy()
        if frame.empty:
            return None, None
        days = frame.day.to_numpy(dtype="datetime64[D]")
        cutoff_day = np.datetime64(cutoff.date())
        age = (cutoff_day - days).astype(float) / 30.4375
        gap = np.r_[0.0, np.diff(days).astype(float)] / 30.4375
        cont = np.zeros((len(frame), 18), np.float32)
        cont[:, :4] = np.column_stack([
            np.log1p(age) / 8,
            np.log1p(gap) / 8,
            (frame.stage.to_numpy() + 1) / 12,
            frame.role.to_numpy(),
        ])
        cont[:, 4] = np.log(2.0)
        for row, sources in enumerate(frame.sources):
            for source in str(sources).split("|"):
                if source.isdigit() and 1 <= int(source) <= 13:
                    cont[row, 4 + int(source)] = 1.0
        node_attributes = [
            attributes if isinstance(attributes, dict) else self.histories.attributes(row)
            for attributes, row in zip(frame.attributes, frame.itertuples())
        ]
        separated = [split_attributes(attributes, event_type)
                     for attributes, event_type in zip(node_attributes, frame.type)]
        founded = frame.loc[frame.type.eq(8), "day"]
        first = founded.min() if len(founded) else frame.day.min()
        company_age = max(0.0, (cutoff - first).days / 30.4375)
        sample = {
            "company": str(company),
            "typ": frame.type.to_numpy(np.int64),
            "src": frame.source.to_numpy(np.int64),
            "cont": cont,
            "attributes": [attribute_tokens(attributes) for attributes, _ in separated],
            "semantic_texts": [text for _, text in separated],
            "allowed": np.ones(len(EVENTS), dtype=bool),
            "company_age": np.float32(np.log1p(company_age) / 8.0),
            "era": np.int64(0 if cutoff.year <= 2014 else (1 if cutoff.year <= 2019 else 2)),
        }
        trace = {
            "history_nodes": len(frame),
            "history_start": frame.day.iloc[0].date().isoformat(),
            "history_end": frame.day.iloc[-1].date().isoformat(),
            "recent_history": [
                {
                    "date": row.day.date().isoformat(),
                    "event": EVENT_NAMES.get(int(row.type), "其他事件"),
                }
                for row in frame.tail(5).itertuples()
            ],
            "history_years": yearly_history(frame),
        }
        return sample, trace

    def sample_custom(self, events, as_of):
        """Build the same model tensors from a founder-authored standard event path."""
        cutoff = pd.Timestamp(as_of)
        frame = pd.DataFrame(events).copy()
        if frame.empty:
            return None, None
        frame["day"] = pd.to_datetime(frame["date"], errors="coerce")
        if frame.day.isna().any() or frame.day.gt(cutoff).any():
            raise ValueError("自建路径包含无效或未来事件日期")
        frame = frame.sort_values(["day", "type", "subtype"]).reset_index(drop=True)
        days = frame.day.to_numpy(dtype="datetime64[D]")
        cutoff_day = np.datetime64(cutoff.date())
        age = (cutoff_day - days).astype(float) / 30.4375
        gap = np.r_[0.0, np.diff(days).astype(float)] / 30.4375
        cont = np.zeros((len(frame), 18), np.float32)
        cont[:, :4] = np.column_stack([
            np.log1p(age) / 8,
            np.log1p(gap) / 8,
            (frame.stage.to_numpy(np.float32) + 1) / 12,
            frame.role.to_numpy(np.float32),
        ])
        # Source 1 is the model's generic event stream. The public response keeps
        # the honest "founder supplied" provenance; no unseen source ID is invented.
        cont[:, 4] = np.log(2.0)
        cont[:, 5] = 1.0
        attributes = [{"detail": row.detail} for row in frame.itertuples()]
        separated = [split_attributes(value, event_type)
                     for value, event_type in zip(attributes, frame.type)]
        founded = frame.loc[frame.type.eq(8), "day"]
        first = founded.min() if len(founded) else frame.day.min()
        company_age = max(0.0, (cutoff - first).days / 30.4375)
        sample = {
            "company": "founder-authored",
            "typ": frame.type.to_numpy(np.int64),
            "src": np.ones(len(frame), np.int64),
            "cont": cont,
            "attributes": [attribute_tokens(value) for value, _ in separated],
            "semantic_texts": [text for _, text in separated],
            "allowed": np.ones(len(EVENTS), dtype=bool),
            "company_age": np.float32(np.log1p(company_age) / 8.0),
            "era": np.int64(0 if cutoff.year <= 2014 else (1 if cutoff.year <= 2019 else 2)),
        }
        trace = {
            "history_nodes": len(frame),
            "history_start": frame.day.iloc[0].date().isoformat(),
            "history_end": frame.day.iloc[-1].date().isoformat(),
            "recent_history": [
                {"date": row.day.date().isoformat(), "event": row.label}
                for row in frame.tail(5).itertuples()
            ],
            "history_years": yearly_history(frame, custom=True),
            "company_age_days": int((cutoff - first).days),
            "types": frame.type.to_numpy(np.int64),
            "stages": frame.stage.to_numpy(np.float32),
        }
        return sample, trace

    def sample_scenario(self, company, events, as_of, reference_cutoff):
        """Append founder actions to a real company's complete observed history."""
        self.extend_histories(reference_cutoff)
        base, trace = self.sample(company, as_of)
        injected, injected_trace = self.sample_custom(events, as_of)
        if base is None or injected is None:
            return None, None
        first_scenario = pd.Timestamp(injected_trace["history_start"])
        last_observed = pd.Timestamp(trace["history_end"])
        gap = max(0.0, (first_scenario - last_observed).days / 30.4375)
        injected["cont"][0, 1] = np.log1p(gap) / 8
        sample = {
            "company": str(company),
            "typ": np.concatenate([base["typ"], injected["typ"]]),
            "src": np.concatenate([base["src"], injected["src"]]),
            "cont": np.concatenate([base["cont"], injected["cont"]]),
            "attributes": base["attributes"] + injected["attributes"],
            "semantic_texts": base["semantic_texts"] + injected["semantic_texts"],
            "allowed": base["allowed"],
            "company_age": base["company_age"],
            "era": base["era"],
        }
        years = {item["year"]: dict(item) for item in trace["history_years"]}
        for event in events:
            event_day = pd.Timestamp(event["date"])
            year = int(event_day.year)
            item = years.setdefault(year, {
                "year": year, "count": 0, "start": event["date"],
                "end": event["date"], "events": [],
            })
            item["count"] += 1
            item["start"] = min(item.get("start", event["date"]), event["date"])
            item["end"] = max(item.get("end", event["date"]), event["date"])
            counts = {value["event"]: value["count"] for value in item.get("events", [])}
            counts[event["label"]] = counts.get(event["label"], 0) + 1
            item["events"] = [
                {"event": name, "count": count}
                for name, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[:4]
            ]
        recent = trace.get("recent_history", []) + [
            {"date": event["date"], "event": event["label"]} for event in events
        ]
        combined_trace = {
            "history_nodes": trace["history_nodes"] + len(events),
            "history_start": trace["history_start"],
            "history_end": max(trace["history_end"], injected_trace["history_end"]),
            "recent_history": sorted(recent, key=lambda item: item["date"])[-5:],
            "history_years": [years[year] for year in sorted(years)],
        }
        return sample, combined_trace

    def predict(self, history, seed=1042, samples=3):
        history = {key: value.to(self.device) for key, value in history.items()}
        batch_size = len(history["typ"])
        rng = np.random.default_rng(seed)
        probabilities, times = [], []
        original, cached = self.model.encode_sequence, []

        def once(*args, **kwargs):
            if not cached:
                cached.append(original(*args, **kwargs))
            return cached[0]

        self.model.encode_sequence = once
        try:
            devices = ([self.device.index or torch.cuda.current_device()]
                       if self.device.type == "cuda" else [])
            with torch.random.fork_rng(devices=devices), torch.no_grad():
                torch.manual_seed(seed)
                if self.device.type == "cuda":
                    torch.cuda.manual_seed(seed)
                for _ in range(samples):
                    nt, tm, mask = initial_noise(batch_size, rng)
                    for current, next_step in ((12, 6), (6, 1), (1, 0)):
                        logits, months = self.model(
                            **history,
                            noisy_type=nt.to(self.device),
                            noisy_time=tm.to(self.device),
                            noisy_mask=mask.to(self.device),
                            step=torch.full((batch_size,), current, device=self.device),
                        )
                        if not next_step:
                            break
                        selected = torch.bernoulli(logits.sigmoid()).bool().cpu()
                        point_type, point_month = pack(selected, months.cpu())
                        nt, tm, mask = corrupt(
                            point_type, point_month, selected.sum(1),
                            torch.full((batch_size,), next_step), rng)
                    probabilities.append(logits.sigmoid().cpu())
                    times.append(months.cpu())
            return (torch.stack(probabilities).mean(0).numpy(),
                    torch.stack(times).mean(0).numpy())
        finally:
            self.model.encode_sequence = original

    def run(self, company, as_of):
        date.fromisoformat(as_of)
        self.extend_histories(as_of)
        sample, trace = self.sample(company, as_of)
        if sample is None:
            return {
                "available": False,
                "reason": "该企业在资料截止日前没有可供模型读取的有效日期历史节点。",
                "company": company,
                "as_of": as_of,
            }
        history = self.collator([sample])
        probability, months = self.predict(history)
        probability, months = probability[0], months[0]
        cutoff = date.fromisoformat(as_of)
        events = []
        for index, name in enumerate(EVENTS):
            predicted = bool(probability[index] >= self.thresholds[index])
            month_index = int(np.clip(np.rint(months[index]), 1, 12)) if predicted else None
            if predicted:
                year, month = add_month(cutoff.year, cutoff.month, month_index)
                estimated = f"{year:04d}-{month:02d}"
            else:
                estimated = None
            events.append({
                "event": name,
                "predicted": predicted,
                "month_index": month_index,
                "estimated_month": estimated,
            })
        start, end = horizon(as_of)
        return {
            "available": True,
            "mode": "live_full_history_inference",
            "company": company,
            "as_of": as_of,
            "horizon_start": start,
            "horizon_end": end,
            "all_history": True,
            "history_nodes": trace["history_nodes"],
            "history_start": trace["history_start"],
            "history_end": trace["history_end"],
            "recent_history": trace["recent_history"],
            "history_years": trace["history_years"],
            "post_2024_nodes_in_dataset": self.live_history_added,
            "semantic_cached_nodes": self.lookup.last_cached,
            "semantic_new_texts": self.lookup.last_encoded,
            "model": "历史事件频率状态 · 第7轮第2周期",
            "device": self.device.type,
            "events": events,
        }

    def run_many(self, companies, as_of):
        """Batch inference used to materialize the investor opportunity pool."""
        date.fromisoformat(as_of)
        self.extend_histories(as_of)
        prepared = []
        unavailable = []
        for company in companies:
            sample, trace = self.sample(str(company), as_of)
            if sample is None:
                unavailable.append({
                    "available": False,
                    "reason": "该企业在资料截止日前没有可供模型读取的有效日期历史节点。",
                    "company": str(company),
                    "as_of": as_of,
                })
            else:
                prepared.append((str(company), sample, trace))
        if not prepared:
            return unavailable
        history = self.collator([sample for _, sample, _ in prepared])
        probabilities, months = self.predict(history)
        cutoff = date.fromisoformat(as_of)
        start, end = horizon(as_of)
        results = []
        for row, (company, _, trace) in enumerate(prepared):
            events = []
            for index, name in enumerate(EVENTS):
                predicted = bool(probabilities[row, index] >= self.thresholds[index])
                month_index = (int(np.clip(np.rint(months[row, index]), 1, 12))
                               if predicted else None)
                if predicted:
                    year, month = add_month(cutoff.year, cutoff.month, month_index)
                    estimated = f"{year:04d}-{month:02d}"
                else:
                    estimated = None
                events.append({
                    "event": name,
                    "predicted": predicted,
                    "month_index": month_index,
                    "estimated_month": estimated,
                })
            results.append({
                "available": True,
                "mode": "live_full_history_inference",
                "company": company,
                "as_of": as_of,
                "horizon_start": start,
                "horizon_end": end,
                "all_history": True,
                **trace,
                "post_2024_nodes_in_dataset": self.live_history_added,
                "model": "历史事件频率状态 · 第7轮第2周期",
                "device": self.device.type,
                "events": events,
            })
        return results + unavailable

    @staticmethod
    def _path_features(types, stages):
        counts = np.log1p(np.bincount(np.asarray(types, np.int64), minlength=29)[1:29])
        norm = np.linalg.norm(counts)
        if norm:
            counts = counts / norm
        financing = np.asarray(stages)[np.asarray(types) == 1]
        stage = float(financing.max()) if len(financing) else -1.0
        pairs = set(zip(np.asarray(types)[:-1].tolist(), np.asarray(types)[1:].tolist()))
        return counts, stage, pairs

    def similar_paths(self, trace, reference_cutoff, limit=80):
        """Match prefixes only; reveal the following year after retrieval."""
        cutoff = pd.Timestamp(reference_cutoff)
        age_days = max(0, int(trace["company_age_days"]))
        custom_counts, custom_stage, custom_pairs = self._path_features(
            trace["types"], trace["stages"])
        custom_size = len(trace["types"])
        candidates = []
        records = self.histories.records
        for company, indices in self.histories.groups.items():
            frame = records.iloc[indices]
            frame = frame.loc[frame.day.le(cutoff)]
            if frame.empty:
                continue
            founded = frame.loc[frame.type.eq(8), "day"]
            start = founded.min() if len(founded) else frame.day.iloc[0]
            compare_cutoff = start + pd.Timedelta(days=age_days)
            # The following 12 months must be completely observable in the dataset.
            if compare_cutoff + pd.Timedelta(days=365) > cutoff:
                continue
            prefix = frame.loc[frame.day.le(compare_cutoff)]
            if prefix.empty:
                continue
            counts, stage, pairs = self._path_features(
                prefix.type.to_numpy(), prefix.stage.to_numpy())
            cosine = float(np.dot(custom_counts, counts))
            size_score = math.exp(-abs(math.log1p(len(prefix)) - math.log1p(custom_size)))
            if custom_stage < 0 and stage < 0:
                stage_score = 1.0
            elif custom_stage < 0 or stage < 0:
                stage_score = 0.0
            else:
                stage_score = math.exp(-abs(custom_stage - stage) / 3)
            union = custom_pairs | pairs
            sequence = len(custom_pairs & pairs) / len(union) if union else 1.0
            score = .55 * cosine + .2 * size_score + .15 * stage_score + .1 * sequence
            item = (score, str(company), compare_cutoff, len(prefix), counts, stage)
            if len(candidates) < limit:
                heapq.heappush(candidates, item)
            elif score > candidates[0][0]:
                heapq.heapreplace(candidates, item)
        results = []
        for score, company, compare_cutoff, prefix_size, counts, stage in sorted(
                candidates, key=lambda item: (-item[0], item[1])):
            frame = records.iloc[self.histories.groups[company]]
            future = frame.loc[frame.day.gt(compare_cutoff) &
                               frame.day.le(compare_cutoff + pd.Timedelta(days=365)) &
                               frame.type.isin([1, 2, 3, 4, 5, 9, 10, 11, 12, 19, 20, 21, 22])]
            outcomes = []
            seen = set()
            for row in future.itertuples():
                key = (row.day.date().isoformat(), int(row.type))
                if key in seen:
                    continue
                seen.add(key)
                outcomes.append({"date": key[0],
                                 "event": EVENT_NAMES.get(key[1], "其他事件")})
                if len(outcomes) == 6:
                    break
            cancel_dates = self.histories.cancel_dates.get(
                company, np.empty(0, dtype="datetime64[D]"))
            end = np.datetime64((compare_cutoff + pd.Timedelta(days=365)).date())
            start = np.datetime64(compare_cutoff.date())
            cancellation = cancel_dates[(cancel_dates > start) & (cancel_dates <= end)]
            if len(cancellation):
                outcomes.append({"date": str(cancellation[0]), "event": "注销"})
            overlap = np.argsort(-(custom_counts * counts))[:3]
            shared = [EVENT_NAMES.get(int(index) + 1, "其他事件") for index in overlap
                      if custom_counts[index] > 0 and counts[index] > 0]
            results.append({
                "company": company,
                "similarity": round(score, 4),
                "matched_until": compare_cutoff.date().isoformat(),
                "history_nodes": prefix_size,
                "shared_events": shared,
                "stage_gap": None if custom_stage < 0 or stage < 0
                             else round(abs(custom_stage - stage), 2),
                "next_12_months": sorted(outcomes, key=lambda item: item["date"]),
            })
        return results

    def run_custom(self, custom_id, events, as_of, reference_cutoff):
        date.fromisoformat(as_of)
        self.extend_histories(reference_cutoff)
        sample, trace = self.sample_custom(events, as_of)
        if sample is None:
            return {"available": False, "reason": "请先添加至少一个历史节点。",
                    "company": custom_id, "as_of": as_of}
        history = self.collator([sample])
        probabilities, months = self.predict(history)
        probability, months = probabilities[0], months[0]
        cutoff = date.fromisoformat(as_of)
        predicted_events = []
        for index, name in enumerate(EVENTS):
            predicted = bool(probability[index] >= self.thresholds[index])
            month_index = int(np.clip(np.rint(months[index]), 1, 12)) if predicted else None
            if predicted:
                year, month = add_month(cutoff.year, cutoff.month, month_index)
                estimated = f"{year:04d}-{month:02d}"
            else:
                estimated = None
            predicted_events.append({"event": name, "predicted": predicted,
                                     "month_index": month_index,
                                     "estimated_month": estimated})
        start, end = horizon(as_of)
        return {
            "available": True,
            "mode": "custom_path_inference",
            "company": custom_id,
            "as_of": as_of,
            "horizon_start": start,
            "horizon_end": end,
            "all_history": True,
            "history_nodes": trace["history_nodes"],
            "history_start": trace["history_start"],
            "history_end": trace["history_end"],
            "recent_history": trace["recent_history"],
            "history_years": trace["history_years"],
            "model": "历史事件频率状态 · 第7轮第2周期",
            "device": self.device.type,
            "input_source": "founder_structured_path",
            "events": predicted_events,
            "similar": self.similar_paths(trace, reference_cutoff),
        }

    def run_scenario(self, company, events, as_of, reference_cutoff):
        date.fromisoformat(as_of)
        date.fromisoformat(reference_cutoff)
        sample, trace = self.sample_scenario(company, events, as_of, reference_cutoff)
        if sample is None:
            return {"available": False, "reason": "企业没有可用于预测的历史事件。",
                    "company": company, "as_of": as_of}
        history = self.collator([sample])
        probabilities, months = self.predict(history)
        probability, months = probabilities[0], months[0]
        cutoff = date.fromisoformat(as_of)
        predicted_events = []
        for index, name in enumerate(EVENTS):
            predicted = bool(probability[index] >= self.thresholds[index])
            month_index = int(np.clip(np.rint(months[index]), 1, 12)) if predicted else None
            if predicted:
                year, month = add_month(cutoff.year, cutoff.month, month_index)
                estimated = f"{year:04d}-{month:02d}"
            else:
                estimated = None
            predicted_events.append({"event": name, "predicted": predicted,
                                     "month_index": month_index,
                                     "estimated_month": estimated})
        start, end = horizon(as_of)
        return {
            "available": True,
            "mode": "financing_scenario_inference",
            "company": company,
            "as_of": as_of,
            "horizon_start": start,
            "horizon_end": end,
            "all_history": True,
            **trace,
            "model": "历史事件频率状态 · 第7轮第2周期",
            "device": self.device.type,
            "input_source": "observed_history_plus_financing_scenario",
            "scenario_events": [
                {"date": event["date"], "event": event["label"]} for event in events
            ],
            "events": predicted_events,
        }


def main():
    worker = Worker()
    for line in sys.stdin:
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError("request must be an object")
            if request.get("op") == "batch":
                companies = request.get("companies")
                if (not isinstance(companies, list) or not companies or
                        len(companies) > 256):
                    raise ValueError("batch companies must contain 1..256 ids")
                result = worker.run_many([str(company) for company in companies],
                                         str(request["as_of"]))
            elif request.get("op") == "scenario":
                events = request.get("events")
                if not isinstance(events, list) or not 1 <= len(events) <= 20:
                    raise ValueError("scenario events must contain 1..20 events")
                result = worker.run_scenario(str(request["company"]), events,
                                             str(request["as_of"]),
                                             str(request["reference_cutoff"]))
            elif request.get("op") == "custom":
                events = request.get("events")
                if not isinstance(events, list) or len(events) > 500:
                    raise ValueError("custom events must be a list of at most 500 nodes")
                result = worker.run_custom(str(request["company"]), events,
                                           str(request["as_of"]),
                                           str(request["reference_cutoff"]))
            else:
                result = worker.run(str(request["company"]), str(request["as_of"]))
            response = {"ok": True, "result": result}
        except Exception as error:
            response = {"ok": False, "error": f"{type(error).__name__}: {error}"}
        print(json.dumps(response, ensure_ascii=False, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()

"""Five-slot conditional set diffusion with optional weak calendar context."""
import math
import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn

HERE = Path(__file__).resolve().parent
OPT = HERE.parent / "enterprise_path_optimization"
SEQUENCE = HERE.parent / "enterprise_path_sequence"
sys.path.insert(0, str(OPT))
sys.path.insert(0, str(SEQUENCE))

from models import Variant  # noqa: E402
from model import base, objective  # noqa: E402

MARKS = 5
NOISE_RATE = 2.0


class Model(Variant):
    def __init__(self, weak_time=False):
        super().__init__({"history_bridge": True}, np.full(8, .05))
        self.weak_time = weak_time
        self.event_query = nn.Parameter(torch.randn(MARKS, 48) * .02)
        self.log_decay = nn.Parameter(torch.zeros(MARKS))
        self.noisy_mark = nn.Embedding(MARKS + 1, 48, padding_idx=0)
        self.slot_query = nn.Parameter(torch.randn(MARKS, 48) * .02)
        if weak_time:
            self.era_embedding = nn.Embedding(3, 48)
            self.age_projection = nn.Sequential(nn.Linear(1, 48), nn.Tanh())
            self.time_gate = nn.Parameter(torch.tensor(-2.0))

    def forward(self, typ, src, cont, noisy_type, noisy_time, noisy_mask, step, allowed,
                era=None, company_age=None, **kwargs):
        history, pad, pooled = self.encode_sequence(typ, src, cont, **kwargs)
        context = 0.0
        if self.weak_time:
            context = self.time_gate.sigmoid() * (
                self.era_embedding(era) + self.age_projection(company_age[:, None]))
            pooled = pooled + context[:, None]
        features = torch.stack([noisy_time, torch.sin(math.pi * noisy_time),
                                torch.cos(math.pi * noisy_time)], -1)
        step_emb = self.step_embedding(step)
        noise = self.noisy_mark(noisy_type) + self.noisy_time(features) + step_emb[:, None]
        memory = torch.cat([pooled, history, noise], 1)
        memory_pad = torch.cat([
            torch.zeros((len(typ), MARKS), dtype=torch.bool), pad, noisy_mask], 1)
        query = self.slot_query[None] + self.event_query[None] + step_emb[:, None]
        if self.weak_time:
            query = query + context[:, None]
        decoded = self.decoder(query, memory, memory_key_padding_mask=memory_pad)
        return (self.presence(decoded).squeeze(-1).masked_fill(~allowed, -12.),
                1 + 11 * self.month(decoded).squeeze(-1).sigmoid())


def initialize(model, checkpoint):
    old = torch.load(checkpoint, map_location="cpu", weights_only=False)["state_dict"]
    mapped = {}
    for key, value in old.items():
        if key == "noise_prior":
            continue
        if key in ("event_query", "slot_query"):
            equity = (value[3] + value[4]) / 2 + .01 * torch.randn_like(value[3])
            mapped[key] = torch.stack([value[:3].mean(0), value[3], equity, value[4], value[7]])
        elif key == "log_decay":
            mapped[key] = torch.stack([value[:3].mean(), value[3],
                                       (value[3] + value[4]) / 2, value[4], value[7]])
        elif key == "noisy_mark.weight":
            mapped[key] = torch.stack([value[0], value[1:4].mean(0), value[4],
                                       (value[4] + value[5]) / 2, value[5], value[8]])
        elif key in model.state_dict() and model.state_dict()[key].shape == value.shape:
            mapped[key] = value
    loaded = model.load_state_dict(mapped, strict=False)
    allowed_missing = ("noise_prior", "era_embedding.weight", "age_projection.0.weight",
                       "age_projection.0.bias", "time_gate")
    assert not loaded.unexpected_keys, loaded
    assert all(key in allowed_missing for key in loaded.missing_keys), loaded


def corrupt(types, times, count, step, rng):
    nt = torch.zeros((len(types), MARKS), dtype=torch.long)
    tm = torch.zeros((len(types), MARKS), dtype=torch.float32)
    mask = torch.ones_like(nt, dtype=torch.bool)
    abar = base.alpha_bar(step)
    for i in range(len(nt)):
        points = {}
        keep = float(abar[i])
        for j in range(int(count[i])):
            mark = int(types[i, j])
            if mark and rng.random() <= keep:
                points[mark] = 2 * (float(times[i, j]) - 1) / 11 - 1
        available = np.array([m for m in range(1, MARKS + 1) if m not in points])
        number = min(len(available), int(rng.poisson((1 - keep) * NOISE_RATE)))
        if number:
            for mark in rng.choice(available, number, replace=False):
                points[int(mark)] = float(rng.uniform(-1, 1))
        items = list(points.items())
        rng.shuffle(items)
        for j, (mark, value) in enumerate(items):
            nt[i, j], tm[i, j], mask[i, j] = mark, value, False
    return nt, tm, mask


def initial_noise(batch, rng):
    z = torch.zeros((batch, MARKS))
    return corrupt(z.long(), z, torch.zeros(batch, dtype=torch.long),
                   torch.full((batch,), 12), rng)


def target_matrix(types, times):
    y = torch.zeros((len(types), MARKS))
    tm = torch.zeros_like(y)
    for mark in range(1, MARKS + 1):
        hit = types.eq(mark)
        y[:, mark - 1] = hit.any(1)
        tm[:, mark - 1] = torch.where(hit, times, 99.).min(1).values
    return y, tm


def pack(selected, months):
    order = selected.int().argsort(dim=1, descending=True, stable=True)
    valid = selected.gather(1, order)
    marks = torch.arange(1, MARKS + 1)[None].expand_as(selected).gather(1, order)
    return marks.masked_fill(~valid, 0), months.gather(1, order).masked_fill(~valid, 0)


def regular_loss(logits, months, targets):
    y, target_time = target_matrix(targets["true_type"], targets["true_time"])
    pos, neg = y.bool(), ~y.bool()
    raw = nn.functional.binary_cross_entropy_with_logits(logits, y, reduction="none")
    zero = logits.sum() * 0
    occurrence = (raw[pos].mean() if pos.any() else zero) + .25 * raw[neg].mean()
    timing = nn.functional.smooth_l1_loss(months[pos], target_time[pos]) if pos.any() else zero
    count = nn.functional.smooth_l1_loss(logits.sigmoid().sum(1), targets["count"].float())
    marginal = nn.functional.binary_cross_entropy(logits.sigmoid(), y)
    return occurrence + .15 * timing + .25 * count + .5 * marginal


def terminal_loss(model, history, targets, rng):
    training = model.training
    seed = int(rng.integers(0, 2**31 - 1))
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        nt, tm, mask = initial_noise(len(history["typ"]), rng)
        model.eval()
        with torch.no_grad():
            for current, next_step in ((12, 6), (6, 1)):
                logits, months = model(**history, noisy_type=nt, noisy_time=tm,
                                       noisy_mask=mask, step=torch.full((len(nt),), current))
                selected = torch.bernoulli(logits.sigmoid()).bool()
                pt, pm = pack(selected, months)
                nt, tm, mask = corrupt(pt, pm, selected.sum(1),
                                       torch.full((len(nt),), next_step), rng)
        model.train(training)
        logits, months = model(**history, noisy_type=nt, noisy_time=tm,
                               noisy_mask=mask, step=torch.ones(len(nt), dtype=torch.long))
        y, target_time = target_matrix(targets["true_type"], targets["true_time"])
        pos = y.bool()
        occurrence = nn.functional.binary_cross_entropy_with_logits(logits, y)
        count = objective.cardinality_nll(logits, torch.ones_like(y, dtype=torch.bool), y.sum(1))
        timing = nn.functional.smooth_l1_loss(months[pos], target_time[pos]) if pos.any() else months.sum() * 0
        return .75 * occurrence + .25 * count + .1 * timing


def training_loss(model, history, targets, step, rng, rollout_rng):
    nt, tm, mask = corrupt(targets["true_type"], targets["true_time"], targets["count"], step, rng)
    logits, months = model(**history, noisy_type=nt, noisy_time=tm, noisy_mask=mask, step=step)
    return regular_loss(logits, months, targets) + terminal_loss(model, history, targets, rollout_rng)


def predict(model, history, seed=1042, samples=3):
    model.eval()
    rng = np.random.default_rng(seed)
    probabilities, times = [], []
    original, cached = model.encode_sequence, []
    def once(*args, **kwargs):
        if not cached:
            cached.append(original(*args, **kwargs))
        return cached[0]
    model.encode_sequence = once
    try:
        with torch.random.fork_rng(devices=[]), torch.no_grad():
            torch.manual_seed(seed)
            for _ in range(samples):
                nt, tm, mask = initial_noise(len(history["typ"]), rng)
                for current, next_step in ((12, 6), (6, 1), (1, 0)):
                    logits, months = model(**history, noisy_type=nt, noisy_time=tm,
                                           noisy_mask=mask, step=torch.full((len(nt),), current))
                    if not next_step:
                        break
                    selected = torch.bernoulli(logits.sigmoid()).bool()
                    pt, pm = pack(selected, months)
                    nt, tm, mask = corrupt(pt, pm, selected.sum(1),
                                           torch.full((len(nt),), next_step), rng)
                probabilities.append(logits.sigmoid())
                times.append(months)
        return torch.stack(probabilities).mean(0).numpy(), torch.stack(times).mean(0).numpy()
    finally:
        model.encode_sequence = original

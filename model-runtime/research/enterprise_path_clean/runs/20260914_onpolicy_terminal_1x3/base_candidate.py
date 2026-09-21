"""State-aware keyed milestone-set diffusion with duplicate-free output slots."""
import math
from pathlib import Path

import numpy as np
import torch
from torch import nn

NUM_MARKS = 8
STEPS = 12
NOISE_RATE = 2.0


def alpha_bar(step):
    s = 0.008
    value = torch.cos(((step.float() / STEPS + s) / (1 + s)) * math.pi / 2) ** 2
    base = math.cos((s / (1 + s)) * math.pi / 2) ** 2
    return (value / base).clamp(0.001, 0.999)


class Model(nn.Module):
    def __init__(self, xdim):
        super().__init__()
        d = 48
        self.history_type = nn.Embedding(26, d, padding_idx=0)
        self.history_source = nn.Embedding(14, 8, padding_idx=0)
        self.history_cont = nn.Linear(4, 16)
        self.history_input = nn.Linear(d + 8 + 16, d)
        enc = nn.TransformerEncoderLayer(d, 4, 96, dropout=.1, batch_first=True, norm_first=True)
        self.history_encoder = nn.TransformerEncoder(enc, 2, enable_nested_tensor=False)
        self.summary = nn.Sequential(nn.Linear(xdim, 64), nn.ReLU(), nn.Linear(64, d))
        self.event_query = nn.Parameter(torch.randn(NUM_MARKS, d) * .02)
        self.log_decay = nn.Parameter(torch.zeros(NUM_MARKS))
        self.noisy_mark = nn.Embedding(NUM_MARKS + 1, d, padding_idx=0)
        self.noisy_time = nn.Sequential(nn.Linear(3, d), nn.SiLU(), nn.Linear(d, d))
        self.step_embedding = nn.Embedding(STEPS + 1, d)
        self.slot_query = nn.Parameter(torch.randn(NUM_MARKS, d) * .02)
        dec = nn.TransformerDecoderLayer(d, 4, 96, dropout=.1, batch_first=True, norm_first=True)
        self.decoder = nn.TransformerDecoder(dec, 1)
        self.presence = nn.Linear(d, 1)
        self.month = nn.Linear(d, 1)

    def encode_history(self, x, typ, src, cont):
        pad = typ.eq(0)
        h = self.history_input(torch.cat([
            self.history_type(typ), self.history_source(src), self.history_cont(cont)
        ], -1))
        h = self.history_encoder(h, src_key_padding_mask=pad)
        score = torch.einsum("ed,bld->bel", self.event_query, h) / math.sqrt(h.shape[-1])
        score -= nn.functional.softplus(self.log_decay)[None, :, None] * cont[:, :, 0][:, None, :]
        score = score.masked_fill(pad[:, None, :], -1e4)
        pooled = torch.einsum("bel,bld->bed", score.softmax(-1), h)
        return h, pad, pooled, self.summary(x)[:, None, :]

    def forward(self, x, typ, src, cont, noisy_type, noisy_time, noisy_mask, step, allowed):
        history, history_pad, pooled, static = self.encode_history(x, typ, src, cont)
        features = torch.stack([
            noisy_time, torch.sin(math.pi * noisy_time), torch.cos(math.pi * noisy_time)
        ], -1)
        step_emb = self.step_embedding(step)
        noise = self.noisy_mark(noisy_type) + self.noisy_time(features) + step_emb[:, None, :]
        memory = torch.cat([static, pooled, history, noise], 1)
        memory_pad = torch.cat([
            torch.zeros((len(x), 1 + NUM_MARKS), dtype=torch.bool, device=x.device),
            history_pad, noisy_mask,
        ], 1)
        query = self.slot_query[None, :, :] + self.event_query[None, :, :] + step_emb[:, None, :]
        decoded = self.decoder(query, memory, memory_key_padding_mask=memory_pad)
        presence = self.presence(decoded).squeeze(-1).masked_fill(~allowed, -12.)
        month = 1. + 11. * self.month(decoded).squeeze(-1).sigmoid()
        return presence, month


def corrupt(clean_type, clean_time, count, step, rng):
    """Thin/add unique marked points; retained mark and month are unchanged."""
    batch = len(clean_type)
    noisy_type = torch.zeros((batch, NUM_MARKS), dtype=torch.long)
    noisy_time = torch.zeros((batch, NUM_MARKS), dtype=torch.float32)
    noisy_mask = torch.ones((batch, NUM_MARKS), dtype=torch.bool)
    abar = alpha_bar(step)
    for i in range(batch):
        keep = float(abar[i]); points = {}
        for j in range(int(count[i])):
            mark = int(clean_type[i, j])
            if mark and rng.random() <= keep:
                points[mark] = 2. * (float(clean_time[i, j]) - 1.) / 11. - 1.
        available = np.array([m for m in range(1, NUM_MARKS + 1) if m not in points], dtype=int)
        additions = min(len(available), int(rng.poisson((1. - keep) * NOISE_RATE)))
        if additions:
            for mark in rng.choice(available, size=additions, replace=False):
                points[int(mark)] = float(rng.uniform(-1., 1.))
        items = list(points.items()); rng.shuffle(items)
        for j, (mark, value) in enumerate(items):
            noisy_type[i, j] = mark; noisy_time[i, j] = value; noisy_mask[i, j] = False
    return noisy_type, noisy_time, noisy_mask


def mark_targets(true_type, true_time):
    target = torch.zeros((len(true_type), NUM_MARKS), dtype=torch.float32)
    times = torch.zeros_like(target)
    for mark in range(1, NUM_MARKS + 1):
        hit = true_type.eq(mark)
        target[:, mark - 1] = hit.any(1)
        times[:, mark - 1] = torch.where(hit, true_time, 99.).min(1).values
    return target, times


def metric_probabilities(mark_probability):
    repeat = 1. - (1. - mark_probability[:, 1]) * (1. - mark_probability[:, 2])
    return torch.stack([
        mark_probability[:, 0], repeat, mark_probability[:, 2], mark_probability[:, 3],
        mark_probability[:, 4], mark_probability[:, 5], mark_probability[:, 6], mark_probability[:, 7],
    ], 1)


def metric_times(mark_probability, months):
    denom = (mark_probability[:, 1] + mark_probability[:, 2]).clamp_min(1e-6)
    repeat = (mark_probability[:, 1] * months[:, 1] + mark_probability[:, 2] * months[:, 2]) / denom
    return torch.stack([
        months[:, 0], repeat, months[:, 2], months[:, 3], months[:, 4], months[:, 5],
        months[:, 6], months[:, 7],
    ], 1)


def loss_fn(logits, months, true_type, true_time, count, eligible, allowed, initial):
    target, target_time = mark_targets(true_type, true_time)
    positive = target.bool() & allowed
    negative = ~target.bool() & allowed
    raw = nn.functional.binary_cross_entropy_with_logits(logits, target, reduction="none")
    positive_loss = raw[positive].mean() if positive.any() else logits.sum() * 0
    negative_loss = raw[negative].mean() if negative.any() else logits.sum() * 0
    time_loss = nn.functional.smooth_l1_loss(months[positive], target_time[positive]) if positive.any() else months.sum() * 0
    probability = logits.sigmoid() * allowed
    count_loss = nn.functional.smooth_l1_loss(probability.sum(1), count.float())
    metric_prob = metric_probabilities(probability).clamp(1e-5, 1 - 1e-5)
    derived = torch.stack([
        target[:, 0], 1-(1-target[:, 1])*(1-target[:, 2]), target[:, 2], *[target[:, k] for k in range(3, 8)]
    ], 1)
    marginal = nn.functional.binary_cross_entropy(metric_prob[eligible], derived[eligible])
    # A soft state-order objective for paths containing both abnormal transitions.
    enter, leave = probability[:, 5], probability[:, 6]
    active = initial[:, 1].bool()
    state_presence = torch.where(active, enter * (1 - leave), leave * (1 - enter)).mean()
    both = target[:, 5].bool() & target[:, 6].bool()
    if both.any():
        expected = torch.where(active[both], months[both, 6] - months[both, 5], months[both, 5] - months[both, 6])
        state_order = nn.functional.relu(expected + .25).mean()
    else:
        state_order = months.sum() * 0
    return positive_loss + .25 * negative_loss + .15 * time_loss + .25 * count_loss + .5 * marginal + .1 * state_presence + .05 * state_order


def tensorize(data, mean, std, active, future=False):
    x = np.clip((data["x"] - mean) / np.maximum(std, .1), -10, 10); x[:, ~active] = 0
    result = {"x": torch.from_numpy(x.astype(np.float32)),
              "typ": torch.from_numpy(data["seq_type"].astype(np.int64)),
              "src": torch.from_numpy(data["seq_source"].astype(np.int64)),
              "cont": torch.from_numpy(data["seq_cont"].astype(np.float32)),
              "allowed": torch.from_numpy(data["allowed"].astype(bool)),
              "initial": torch.from_numpy(data["initial"].astype(np.int64))}
    if future:
        result.update(true_type=torch.from_numpy(data["future_type"].astype(np.int64)),
                      true_time=torch.from_numpy(data["future_time"].astype(np.float32)),
                      count=torch.from_numpy(data["future_count"].astype(np.int64)),
                      eligible=torch.from_numpy(data["eligible"].astype(bool)))
    return result


def initial_noise(batch, rng):
    typ = torch.zeros((batch, NUM_MARKS), dtype=torch.long)
    tim = torch.zeros((batch, NUM_MARKS), dtype=torch.float32)
    mask = torch.ones((batch, NUM_MARKS), dtype=torch.bool)
    for i in range(batch):
        n = min(NUM_MARKS, int(rng.poisson(NOISE_RATE)))
        if n:
            marks = rng.choice(np.arange(1, NUM_MARKS + 1), n, replace=False)
            typ[i, :n] = torch.from_numpy(marks); tim[i, :n] = torch.from_numpy(rng.uniform(-1, 1, n).astype(np.float32)); mask[i, :n] = False
    return typ, tim, mask


def query_outputs(model, query, rng, samples=3):
    all_prob, all_time, all_paths = [], [], []
    model.eval()
    with torch.no_grad():
        for start in range(0, len(query["x"]), 384):
            stop = start + 384
            x, typ, src, cont, allowed = (query[k][start:stop] for k in ("x", "typ", "src", "cont", "allowed"))
            sample_prob, sample_time, sample_paths = [], [], []
            for _ in range(samples):
                noisy_type, noisy_time, noisy_mask = initial_noise(len(x), rng)
                final = None
                for step_value, next_value in ((12, 6), (6, 1), (1, 0)):
                    step = torch.full((len(x),), step_value, dtype=torch.long)
                    final = model(x, typ, src, cont, noisy_type, noisy_time, noisy_mask, step, allowed)
                    if not next_value:
                        break
                    logits, months = final
                    selected = torch.bernoulli(logits.sigmoid()).bool() & allowed
                    pseudo_type = torch.zeros_like(noisy_type)
                    pseudo_time = torch.zeros_like(noisy_time)
                    for i in range(len(x)):
                        marks = torch.nonzero(selected[i], as_tuple=False).flatten()
                        for j, mark in enumerate(marks):
                            pseudo_type[i, j] = mark + 1
                            pseudo_time[i, j] = months[i, mark]
                    next_step = torch.full((len(x),), next_value, dtype=torch.long)
                    noisy_type, noisy_time, noisy_mask = corrupt(pseudo_type, pseudo_time, selected.sum(1), next_step, rng)
                logits, months = final
                probability = logits.sigmoid() * allowed
                sample_prob.append(metric_probabilities(probability)); sample_time.append(metric_times(probability, months))
                selected = torch.bernoulli(probability).bool()
                paths = torch.zeros((len(x), NUM_MARKS, 2))
                for i in range(len(x)):
                    marks = torch.nonzero(selected[i], as_tuple=False).flatten()
                    marks = marks[months[i, marks].argsort()]
                    for j, mark in enumerate(marks):
                        paths[i, j, 0] = mark + 1; paths[i, j, 1] = months[i, mark].round().clamp(1, 12)
                sample_paths.append(paths)
            all_prob.append(torch.stack(sample_prob).mean(0)); all_time.append(torch.stack(sample_time).mean(0))
            all_paths.append(torch.stack(sample_paths, 1))
    return torch.cat(all_prob).numpy(), torch.cat(all_time).numpy(), torch.cat(all_paths).numpy()


def predict(train, query):
    torch.set_num_threads(2); torch.manual_seed(42); rng = np.random.default_rng(42)
    mean = train["x"].mean(0, dtype=np.float64); std = train["x"].std(0, dtype=np.float64); active = std > 1e-6
    tr = tensorize(train, mean, std, active, True); qu = tensorize(query, mean, std, active)
    model = Model(tr["x"].shape[1]); optimizer = torch.optim.AdamW(model.parameters(), lr=8e-4, weight_decay=.01)
    for epoch in range(5):
        model.train(); total = 0.; order = rng.permutation(len(tr["x"]))
        for index in np.array_split(order, int(np.ceil(len(order) / 256))):
            step = torch.from_numpy(rng.integers(1, STEPS+1, len(index), dtype=np.int64))
            noisy_type, noisy_time, noisy_mask = corrupt(tr["true_type"][index], tr["true_time"][index], tr["count"][index], step, rng)
            output = model(tr["x"][index], tr["typ"][index], tr["src"][index], tr["cont"][index], noisy_type, noisy_time, noisy_mask, step, tr["allowed"][index])
            loss = loss_fn(*output, tr["true_type"][index], tr["true_time"][index], tr["count"][index], tr["eligible"][index], tr["allowed"][index], tr["initial"][index])
            optimizer.zero_grad(); loss.backward(); nn.utils.clip_grad_norm_(model.parameters(), 5); optimizer.step()
            total += float(loss.detach()) * len(index)
        print("keyed milestone diffusion epoch", epoch+1, "loss", total/len(tr["x"]), flush=True)
    torch.save({"state_dict":model.state_dict(),"mean":mean,"std":std,"active":active},Path(__file__).with_name("model.pt"))
    return query_outputs(model, qu, rng)

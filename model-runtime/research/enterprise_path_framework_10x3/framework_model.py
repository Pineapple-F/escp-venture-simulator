"""Progressive structural research model built on retained FinBERT2 set diffusion."""
import importlib.util
import math
from pathlib import Path

import torch
from torch import nn

HERE = Path(__file__).resolve().parent
RESEARCH = next(parent for parent in (HERE, *HERE.parents)
                if (parent / "enterprise_path_finance_knowledge").is_dir())
FINANCE = RESEARCH / "enterprise_path_finance_knowledge"
_spec = importlib.util.spec_from_file_location(
    "framework_finance_base", FINANCE / "architecture.py")
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)
FinanceOnlyModel = _base.FinanceOnlyModel


MECHANISMS = (
    "multi_horizon", "event_transition", "source_reliability", "semantic_gate",
    "target_interaction", "latest_state", "event_frequency", "temporal_delta",
    "occurrence_time", "target_relation",
)


class FrameworkModel(FinanceOnlyModel):
    """A single model whose structural mechanisms can be activated progressively."""
    def __init__(self, active=()):
        super().__init__()
        self.active = frozenset(active)
        unknown = self.active.difference(MECHANISMS)
        if unknown:
            raise ValueError(f"unknown mechanisms: {unknown}")

        # Four target-specific views: last 6, 24, 60 months, and full history.
        self.horizon_query = nn.Parameter(self.event_query.detach().clone()[:, None].repeat(1, 4, 1))
        self.horizon_logits = nn.Parameter(torch.zeros(5, 4))
        self.horizon_gate = nn.Parameter(torch.full((5,), -2.0))

        # Local transition and source-quality refinements of encoded historical nodes.
        self.transition_conv = nn.Conv1d(48, 48, 3, padding=1, bias=False)
        nn.init.zeros_(self.transition_conv.weight)
        self.transition_gate = nn.Parameter(torch.tensor(-1.5))
        self.source_reliability = nn.Embedding(17, 1, padding_idx=0)
        nn.init.zeros_(self.source_reliability.weight)

        # Allow the prediction task to decide how much financial semantics each node needs.
        self.semantic_gate = nn.Sequential(nn.Linear(48, 24), nn.GELU(), nn.Linear(24, 1))
        nn.init.zeros_(self.semantic_gate[-1].weight)
        nn.init.zeros_(self.semantic_gate[-1].bias)

        # Cross-target message passing within the same single model.
        self.target_attention = nn.MultiheadAttention(48, 4, batch_first=True)
        nn.init.zeros_(self.target_attention.out_proj.weight)
        nn.init.zeros_(self.target_attention.out_proj.bias)
        self.target_norm = nn.LayerNorm(48)

        self.latest_gate = nn.Parameter(torch.full((5,), -2.0))
        self.frequency_projection = nn.Linear(29, 5 * 48, bias=False)
        nn.init.zeros_(self.frequency_projection.weight)

        self.delta_query = nn.Parameter(self.event_query.detach().clone())
        self.delta_gate = nn.Parameter(torch.full((5,), -2.0))

        # Joint occurrence/time refinement and target-relation correction.
        self.time_occurrence = nn.Parameter(torch.zeros(5, 3))
        self.target_relation = nn.Parameter(torch.zeros(5, 5))

    def enrich_nodes(self, h, text_vectors):
        if text_vectors is None or text_vectors.shape[-1] != 1024:
            raise ValueError("FrameworkModel requires 1024-d FinBERT2 vectors")
        semantic = self.text_projection(text_vectors)
        if "semantic_gate" in self.active:
            # Exactly matches the retained additive path at initialization.
            semantic = semantic * (2.0 * self.semantic_gate(semantic).sigmoid())
        return h + semantic

    @staticmethod
    def attend(query, history, valid):
        score = torch.einsum("ehd,bld->behl", query, history) / math.sqrt(48)
        score = score.masked_fill(~valid[:, None, None, :], -1e4)
        return torch.einsum("behl,bld->behd", score.softmax(-1), history)

    def encode_sequence(self, typ, src, cont, era=None, company_age=None, **kwargs):
        history, pad, pooled = super().encode_sequence(
            typ, src, cont, era=era, company_age=company_age, **kwargs)

        if "event_transition" in self.active:
            # A full Conv1d over 1437-node histories proved prohibitively slow on CPU.
            # Reuse its centre matrix as an efficient learned projection of adjacent
            # event differences: same local-transition idea, linear in sequence length.
            previous = torch.cat([history[:, :1], history[:, :-1]], 1)
            delta = history - previous
            transition = nn.functional.linear(delta, self.transition_conv.weight[:, :, 1])
            history = history + self.transition_gate.sigmoid() * transition
            history = history.masked_fill(pad[..., None], 0.0)

        if "source_reliability" in self.active:
            reliability = torch.tanh(self.source_reliability(src))
            history = history * (1.0 + 0.25 * reliability)
            history = history.masked_fill(pad[..., None], 0.0)

        if "multi_horizon" in self.active:
            months = torch.expm1(cont[..., 0] * 8.0)
            limits = history.new_tensor([6.0, 24.0, 60.0, 1e9])
            valid = (~pad[:, None, :]) & (months[:, None, :] <= limits[None, :, None])
            empty = ~valid.any(-1)
            valid = torch.where(empty[..., None], (~pad)[:, None, :], valid)
            horizons = self.attend(self.horizon_query, history, valid[:, 0])
            # attend needs one validity mask per horizon, so compute separately.
            horizon_parts = []
            for index in range(4):
                horizon_parts.append(self.attend(
                    self.horizon_query[:, index:index + 1], history, valid[:, index])[:, :, 0])
            horizons = torch.stack(horizon_parts, 2)
            weights = self.horizon_logits.softmax(-1)[None, :, :, None]
            mixed = (horizons * weights).sum(2)
            gate = self.horizon_gate.sigmoid()[None, :, None]
            pooled = pooled + gate * (mixed - pooled)

        if "latest_state" in self.active:
            lengths = (~pad).sum(1).clamp_min(1)
            # Histories are left padded; last column is the latest real node.
            latest = history[:, -1]
            latest = latest[:, None].expand(-1, 5, -1)
            pooled = pooled + self.latest_gate.sigmoid()[None, :, None] * (latest - pooled)

        if "event_frequency" in self.active:
            counts = torch.zeros((len(typ), 29), device=typ.device)
            counts.scatter_add_(1, typ, (~pad).float())
            counts[:, 0] = 0
            counts = torch.log1p(counts) / torch.log1p((~pad).sum(1).float().clamp_min(1))[:, None]
            frequency = self.frequency_projection(counts).reshape(len(typ), 5, 48)
            pooled = pooled + frequency

        if "temporal_delta" in self.active and history.shape[1] > 1:
            delta = history[:, 1:] - history[:, :-1]
            delta_pad = pad[:, 1:] | pad[:, :-1]
            score = torch.einsum("ed,bld->bel", self.delta_query, delta) / math.sqrt(48)
            score = score.masked_fill(delta_pad[:, None], -1e4)
            summary = torch.einsum("bel,bld->bed", score.softmax(-1), delta)
            has_delta = (~delta_pad).any(1)[:, None, None]
            summary = torch.where(has_delta, summary, torch.zeros_like(summary))
            pooled = pooled + self.delta_gate.sigmoid()[None, :, None] * summary

        if "target_interaction" in self.active:
            message, _ = self.target_attention(pooled, pooled, pooled, need_weights=False)
            pooled = self.target_norm(pooled + message)

        return history, pad, pooled

    def forward(self, *args, **kwargs):
        logits, months = super().forward(*args, **kwargs)
        if "occurrence_time" in self.active:
            normalized = (months - 6.5) / 5.5
            features = torch.stack((normalized, torch.sin(math.pi * normalized),
                                    torch.cos(math.pi * normalized)), -1)
            logits = logits + (features * self.time_occurrence[None]).sum(-1)
        if "target_relation" in self.active:
            relation = self.target_relation - torch.diag_embed(torch.diagonal(self.target_relation))
            logits = logits + torch.einsum("ij,bj->bi", relation, logits.tanh())
        return logits, months


def initialize_from_finance(model, checkpoint):
    """Load retained FinBERT2 model, leaving only new framework parameters initialized."""
    state = torch.load(checkpoint, map_location="cpu", weights_only=False)["state_dict"]
    loaded = model.load_state_dict(state, strict=False)
    if loaded.unexpected_keys:
        raise RuntimeError(loaded)
    return loaded.missing_keys

"""Financial-domain semantic and event-ontology variants of the retained model."""
import importlib.util
import math
import sys
from pathlib import Path

import torch
from torch import nn

HERE = Path(__file__).resolve().parent
RESEARCH = next(parent for parent in (HERE, *HERE.parents)
                if (parent / "enterprise_path_v3").is_dir())
V3 = RESEARCH / "enterprise_path_v3"
UNIFIED = RESEARCH / "enterprise_path_unified_time"
sys.path[:0] = [str(V3), str(UNIFIED)]

_spec = importlib.util.spec_from_file_location("finance_base_multiscale", V3 / "architecture.py")
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)
MultiScaleModel = _base.MultiScaleModel


class FinanceOnlyModel(MultiScaleModel):
    """Replace generic 512-d BGE semantics with frozen 1024-d FinBERT2 semantics."""
    def __init__(self):
        super().__init__()
        self.text_projection = nn.Linear(1024, 48, bias=False)

    def enrich_nodes(self, h, text_vectors):
        if text_vectors is None or text_vectors.shape[-1] != 1024:
            raise ValueError("FinanceOnlyModel requires 1024-d FinBERT2 vectors")
        return h + self.text_projection(text_vectors)


class HybridFinanceModel(MultiScaleModel):
    """Keep generic semantics and learn a gated financial-domain residual."""
    def __init__(self):
        super().__init__()
        self.finance_projection = nn.Linear(1024, 48, bias=False)
        nn.init.zeros_(self.finance_projection.weight)
        self.finance_gate = nn.Parameter(torch.tensor(-1.5))

    def enrich_nodes(self, h, text_vectors):
        if text_vectors is None or text_vectors.shape[-1] != 1536:
            raise ValueError("HybridFinanceModel requires concatenated BGE+FinBERT2 vectors")
        generic, finance = text_vectors[..., :512], text_vectors[..., 512:]
        return (h + self.text_projection(generic)
                + self.finance_gate.sigmoid() * self.finance_projection(finance))


def financial_relation_prior():
    """Transparent expert prior: target-to-historical-event relevance, not future labels."""
    prior = torch.zeros(5, 29)
    def set_row(row, values):
        for event_type, weight in values.items():
            prior[row, event_type] = weight
    # Financing: prior financing, valuation, capital and institutional-entry evidence.
    set_row(0, {1: 3.0, 4: 1.5, 19: 1.0, 20: .5, 25: 2.0})
    # Institutional shareholder entry: ownership and capital-market evidence.
    set_row(1, {1: 1.5, 4: 3.0, 5: 1.0, 19: 1.0, 20: 1.5, 25: 1.0})
    # Equity structure change: entry/exit and工商/资本变更 evidence.
    set_row(2, {1: .5, 4: 2.0, 5: 2.0, 9: 1.0, 10: 1.0, 19: 1.5, 20: 3.0})
    # Registered capital change.
    set_row(3, {1: 1.0, 4: 1.0, 19: 3.0, 20: 2.0})
    # Cancellation: distress, punishment, loss of credit and stakeholder exits.
    set_row(4, {3: .5, 5: 1.5, 10: 1.5, 11: 3.0, 12: 1.0,
                21: 2.0, 22: 2.5, 26: .5, 27: .5, 28: .5})
    return prior


class FinanceOntologyModel(MultiScaleModel):
    """Inject a trainable-gated financial event relation prior into target pooling."""
    def __init__(self):
        super().__init__()
        self.register_buffer("finance_relation_prior", financial_relation_prior())
        self.knowledge_gate = nn.Parameter(torch.full((5,), -1.5))
        self.knowledge_strength = nn.Parameter(torch.zeros(5))

    def encode_sequence(self, typ, src, cont, era=None, company_age=None, **kwargs):
        history, pad, pooled = super().encode_sequence(
            typ, src, cont, era=era, company_age=company_age, **kwargs)
        score = torch.einsum("ed,bld->bel", self.event_query, history) / math.sqrt(48)
        relation = self.finance_relation_prior[:, typ].permute(1, 0, 2)
        score = score + nn.functional.softplus(self.knowledge_strength)[None, :, None] * relation
        score = score.masked_fill(pad[:, None, :], -1e4)
        knowledge = torch.einsum("bel,bld->bed", score.softmax(-1), history)
        gate = self.knowledge_gate.sigmoid()[None, :, None]
        return history, pad, pooled + gate * (knowledge - pooled)


def load_retained(model, checkpoint, variant):
    state = torch.load(checkpoint, map_location="cpu", weights_only=False)["state_dict"]
    if variant == "finance_only":
        state.pop("text_projection.weight")
        allowed = {"text_projection.weight"}
    elif variant == "hybrid":
        allowed = {"finance_projection.weight", "finance_gate"}
    elif variant == "ontology":
        allowed = {"knowledge_gate", "knowledge_strength"}
    else:
        raise ValueError(variant)
    loaded = model.load_state_dict(state, strict=False)
    missing = set(loaded.missing_keys)
    # The fixed ontology buffer is supplied by code, not loaded from the old checkpoint.
    missing.discard("finance_relation_prior")
    if loaded.unexpected_keys or missing != allowed:
        raise RuntimeError((loaded, allowed))

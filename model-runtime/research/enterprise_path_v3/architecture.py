"""Single-model multi-scale history encoder with company/target-specific temporal gating."""
import math
import sys
from pathlib import Path

import torch
from torch import nn

HERE = Path(__file__).resolve().parent
UNIFIED = HERE.parent / "enterprise_path_unified_time"
sys.path.insert(0, str(UNIFIED))

from network import Model as RelativeModel  # noqa: E402


class MultiScaleModel(RelativeModel):
    """Fuse full-life and recent-history evidence inside one diffusion network."""
    def __init__(self):
        super().__init__(weak_time=False)
        self.recent_query = nn.Parameter(self.event_query.detach().clone())
        self.era_embedding = nn.Embedding(3, 48)
        self.age_projection = nn.Sequential(nn.Linear(1, 48), nn.Tanh())
        self.context_gate = nn.Parameter(torch.tensor(-3.0))
        self.target_gate = nn.Sequential(
            nn.Linear(48 * 3, 48), nn.GELU(), nn.Linear(48, 1))
        nn.init.zeros_(self.target_gate[-1].weight)
        nn.init.constant_(self.target_gate[-1].bias, -2.0)

    def encode_sequence(self, typ, src, cont, era=None, company_age=None, **kwargs):
        history, pad, lifecycle = super().encode_sequence(typ, src, cont, **kwargs)
        if era is None or company_age is None:
            raise ValueError("MultiScaleModel requires era and company_age")

        # cont[...,0] is log1p(months before cutoff)/8. Recover it only to
        # define the transparent recent-history window; it is not a new feature.
        months_before = torch.expm1(cont[..., 0] * 8.0)
        recent_valid = (~pad) & (months_before <= 24.0)
        no_recent = ~recent_valid.any(1)
        recent_valid[no_recent] = ~pad[no_recent]

        recent_score = torch.einsum("ed,bld->bel", self.recent_query, history) / math.sqrt(48)
        recent_score = recent_score.masked_fill(~recent_valid[:, None, :], -1e4)
        recent = torch.einsum("bel,bld->bed", recent_score.softmax(-1), history)

        context = self.era_embedding(era) + self.age_projection(company_age[:, None])
        context = self.context_gate.sigmoid() * context
        expanded = context[:, None, :].expand(-1, lifecycle.shape[1], -1)
        gate = self.target_gate(torch.cat([lifecycle, recent, expanded], -1)).sigmoid()
        pooled = lifecycle + gate * (recent - lifecycle) + expanded
        return history, pad, pooled

    def forward(self, typ, src, cont, noisy_type, noisy_time, noisy_mask, step, allowed,
                era=None, company_age=None, **kwargs):
        history, pad, pooled = self.encode_sequence(
            typ, src, cont, era=era, company_age=company_age, **kwargs)
        features = torch.stack([noisy_time, torch.sin(math.pi * noisy_time),
                                torch.cos(math.pi * noisy_time)], -1)
        step_emb = self.step_embedding(step)
        noise = self.noisy_mark(noisy_type) + self.noisy_time(features) + step_emb[:, None]
        memory = torch.cat([pooled, history, noise], 1)
        memory_pad = torch.cat([
            torch.zeros((len(typ), 5), dtype=torch.bool), pad, noisy_mask], 1)
        query = self.slot_query[None] + self.event_query[None] + step_emb[:, None]
        decoded = self.decoder(query, memory, memory_key_padding_mask=memory_pad)
        return (self.presence(decoded).squeeze(-1).masked_fill(~allowed, -12.),
                1 + 11 * self.month(decoded).squeeze(-1).sigmoid())


def load_single_checkpoint(model, checkpoint):
    state = torch.load(checkpoint, map_location="cpu", weights_only=False)["state_dict"]
    loaded = model.load_state_dict(state, strict=False)
    expected = ("recent_query", "era_embedding.", "age_projection.",
                "context_gate", "target_gate.")
    assert not loaded.unexpected_keys, loaded
    assert all(key == "recent_query" or key == "context_gate" or
               key.startswith(("era_embedding.", "age_projection.", "target_gate."))
               for key in loaded.missing_keys), loaded
    return loaded

"""Sequence-only keyed-set diffusion; no aggregate feature input or branch."""
import importlib.util
import math
from pathlib import Path

import numpy as np
import torch
from torch import nn

REFERENCE = Path(__file__).resolve().parents[1] / 'enterprise_path_clean/runs/20260914_onpolicy_terminal_1x3'


def load_reference(name):
    spec = importlib.util.spec_from_file_location('sequence_reference_' + name, REFERENCE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = load_reference('base_candidate')
adapter = load_reference('model_adapter')
objective = load_reference('candidate')


def legacy_tensorize(data, future=False):
    """Legacy regression checks only. New runs must use data.Dataset + collate."""
    typ = torch.as_tensor(np.asarray(data['seq_type'], dtype=np.int64))
    src = torch.as_tensor(np.asarray(data['seq_source'], dtype=np.int64))
    number = np.asarray(data['seq_event_count'], dtype=np.float32)
    source_mask = np.asarray(data['seq_source_mask'], dtype=np.int32)
    extras = np.concatenate([
        np.log1p(number)[..., None],
        np.stack([((source_mask >> s) & 1).astype(np.float32) for s in range(1, 14)], -1),
    ], -1)
    cont = torch.as_tensor(np.concatenate([np.asarray(data['seq_cont'], dtype=np.float32), extras], -1))
    cont = cont.masked_fill(typ.eq(0)[..., None], 0.)
    if (typ.ne(0).sum(1) == 0).any():
        raise ValueError('Empty historical sequences need an explicit empty-history policy.')
    history = dict(typ=typ, src=src, cont=cont,
                   allowed=torch.as_tensor(np.asarray(data['allowed'], dtype=bool)))
    if not future:
        return history
    # State and evaluation eligibility are loss metadata, not forward inputs.
    targets = dict(true_type=torch.as_tensor(np.asarray(data['future_type'], dtype=np.int64)),
                   true_time=torch.as_tensor(np.asarray(data['future_time'], dtype=np.float32)),
                   count=torch.as_tensor(np.asarray(data['future_count'], dtype=np.int64)),
                   initial=torch.as_tensor(np.asarray(data['initial'], dtype=np.int64)),
                   eligible=torch.as_tensor(np.asarray(data['eligible'], dtype=bool)))
    return history, targets


class Model(adapter.model_class(base)):
    def __init__(self):
        # Preserve common baseline parameter initialization before removing its branch.
        super().__init__(725)
        del self.summary
        # New dated statement types 26..28 and sources 14..16.
        self.history_type = nn.Embedding(29, 48, padding_idx=0)
        self.history_source = nn.Embedding(17, 8, padding_idx=0)
        self.attributes = nn.EmbeddingBag(32768, 48, mode='sum', padding_idx=0)

    def enrich_nodes(self, h, text_vectors):
        return h

    def encode_sequence(self, typ, src, cont, attr_ids=None, attr_weights=None, attr_offsets=None,
                        text_vectors=None):
        pad = typ.eq(0)
        h = self.history_input(torch.cat([
            self.history_type(typ), self.history_source(src),
            self.history_cont(cont[..., :4]) + self.history_quality(cont[..., 4:]),
        ], -1))
        if attr_ids is not None:
            encoded = self.attributes(attr_ids, attr_offsets, per_sample_weights=attr_weights)
            ends = torch.cat([attr_offsets[1:], attr_offsets.new_tensor([len(attr_ids)])])
            scale = (ends-attr_offsets).clamp_min(1).float().sqrt()[:, None]
            h = h + (encoded / scale).reshape(*typ.shape, 48)
        h = self.enrich_nodes(h, text_vectors)
        # Encode every node, in bounded chunks to avoid quadratic full-history memory.
        # Event queries and the decoder below still attend to every encoded node.
        chunks = []
        for start in range(0, typ.shape[1], 128):
            mask = pad[:, start:start+128].clone()
            empty = mask.all(1)
            mask[empty, 0] = False
            part = self.history_encoder(h[:, start:start+128], src_key_padding_mask=mask)
            chunks.append(part.masked_fill(pad[:, start:start+128, None], 0.))
        h = torch.cat(chunks, 1)
        score = torch.einsum('ed,bld->bel', self.event_query, h) / math.sqrt(h.shape[-1])
        score -= nn.functional.softplus(self.log_decay)[None, :, None] * cont[:, None, :, 0]
        score = score.masked_fill(pad[:, None, :], -1e4)
        pooled = torch.einsum('bel,bld->bed', score.softmax(-1), h)
        return h, pad, pooled

    def forward(self, typ, src, cont, noisy_type, noisy_time, noisy_mask, step, allowed,
                attr_ids=None, attr_weights=None, attr_offsets=None, text_vectors=None):
        history, history_pad, pooled = self.encode_sequence(typ, src, cont, attr_ids, attr_weights, attr_offsets, text_vectors)
        features = torch.stack([noisy_time, torch.sin(math.pi * noisy_time),
                                torch.cos(math.pi * noisy_time)], -1)
        step_emb = self.step_embedding(step)
        noise = self.noisy_mark(noisy_type) + self.noisy_time(features) + step_emb[:, None, :]
        # Unlike the baseline, there is no static summary token.
        memory = torch.cat([pooled, history, noise], 1)
        memory_pad = torch.cat([
            torch.zeros((len(typ), base.NUM_MARKS), dtype=torch.bool, device=typ.device),
            history_pad, noisy_mask,
        ], 1)
        query = self.slot_query[None] + self.event_query[None] + step_emb[:, None]
        decoded = self.decoder(query, memory, memory_key_padding_mask=memory_pad)
        logits = self.presence(decoded).squeeze(-1).masked_fill(~allowed, -12.)
        months = 1. + 11. * self.month(decoded).squeeze(-1).sigmoid()
        return logits, months


def training_loss(model, history, targets, step, rng, rollout_rng):
    """Reuse both retained losses, while keeping aggregate data outside the model."""
    nt, tm, mask = base.corrupt(targets['true_type'], targets['true_time'], targets['count'], step, rng)
    output = model(**history, noisy_type=nt, noisy_time=tm, noisy_mask=mask, step=step)
    regular = base.loss_fn(
        *output, targets['true_type'], targets['true_time'], targets['count'],
        targets['eligible'], history['allowed'], targets['initial'])

    class LegacyCall:
        # The fixed objective's legacy positional API requires x solely for batch size.
        # An empty [B, 0] placeholder is discarded; never accepts historical statistics.
        def __init__(self):
            self.training = model.training

        def eval(self):
            model.eval()

        def train(self, mode=True):
            model.train(mode)

        def __call__(self, empty, typ, src, cont, nt, tm, mask, step, allowed):
            assert empty.shape == (len(typ), 0)
            return model(typ, src, cont, nt, tm, mask, step, allowed,
                         **{k: history[k] for k in ('attr_ids','attr_weights','attr_offsets','text_vectors') if k in history})

    inputs = dict(history, **targets, x=torch.empty((len(history['typ']), 0)))
    correction, components = objective.extra_loss(base, LegacyCall(), inputs, rollout_rng)
    return regular + correction, components


def predict(model, history, seed=1042, samples=3):
    """Same three-step sampler and metric conversion as retained baseline."""
    if len(history['typ']) > 384:
        raise ValueError('Use dynamically collated batches of at most 384 samples.')
    class LegacyInference:
        def eval(self):
            model.eval()

        def __call__(self, empty, typ, src, cont, nt, tm, mask, step, allowed):
            assert empty.shape == (len(typ), 0)
            return model(typ, src, cont, nt, tm, mask, step, allowed,
                         **{k: history[k] for k in ('attr_ids','attr_weights','attr_offsets','text_vectors') if k in history})

    query = dict(history, x=torch.empty((len(history['typ']), 0)))
    original = model.encode_sequence
    cached = []
    def encode_once(*args, **kwargs):
        if not cached:
            cached.append(original(*args, **kwargs))
        return cached[0]
    model.encode_sequence = encode_once
    try:
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed)
            return base.query_outputs(LegacyInference(), query, np.random.default_rng(seed), samples=samples)
    finally:
        model.encode_sequence = original

"""Terminal denoising trained on the actual self-generated reverse chain."""
import numpy as np
import torch
from torch import nn

CONFIG = dict(baseline=False, onpolicy_full_chain=True, correction_step=1,
              terminal_occurrence_weight=.75, terminal_cardinality_weight=.25,
              terminal_time_weight=.1, inference_unchanged=True)


def build_model(base, adapter, xdim):
    return adapter.model_class(base)(xdim)


def loss(base, model, output, inputs):
    return base.loss_fn(*output, *[inputs[k] for k in
        ('true_type', 'true_time', 'count', 'eligible', 'allowed', 'initial')])


def cardinality_nll(logits, allowed, target_count):
    """Exact Poisson-binomial likelihood of the count of allowed Bernoulli marks."""
    batch, marks = logits.shape
    logp = nn.functional.logsigmoid(logits).masked_fill(~allowed, -1e4)
    logq = nn.functional.logsigmoid(-logits).masked_fill(~allowed, 0.)
    dp = logits.new_full((batch, marks+1), -1e4)
    dp[:, 0] = 0.
    for j in range(marks):
        absent = dp + logq[:, j, None]
        present = torch.cat([logits.new_full((batch, 1), -1e4), dp[:, :-1]], 1) + logp[:, j, None]
        dp = torch.logaddexp(absent, present)
    return -dp.gather(1, target_count.long()[:, None]).mean()


def pack(selected, months):
    order = selected.int().argsort(dim=1, descending=True, stable=True)
    valid = selected.gather(1, order)
    marks = torch.arange(1, selected.shape[1]+1, device=selected.device)[None].expand_as(selected).gather(1, order)
    return marks.masked_fill(~valid, 0), months.gather(1, order).masked_fill(~valid, 0.)


def extra_loss(base, model, inputs, rng):
    """Stop-gradient on-policy 12 -> 6 context, supervised correction at step 1.

    Use a separate NumPy RNG and forked Torch RNG so extra sampling does not
    alter the baseline batch order, corruption or dropout random stream.
    """
    seed = int(rng.integers(0, 2**31-1))
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        n = len(inputs['x'])
        nt, tm, mask = base.initial_noise(n, rng)
        training = model.training
        try:
            model.eval()
            with torch.no_grad():
                for step_value, next_value in ((12, 6), (6, 1)):
                    step = torch.full((n,), step_value, dtype=torch.long)
                    logits, months = model(inputs['x'], inputs['typ'], inputs['src'], inputs['cont'],
                                           nt, tm, mask, step, inputs['allowed'])
                    selected = torch.bernoulli(logits.sigmoid()).bool() & inputs['allowed']
                    pt, pm = pack(selected, months)
                    next_step = torch.full((n,), next_value, dtype=torch.long)
                    nt, tm, mask = base.corrupt(pt, pm, selected.sum(1), next_step, rng)
            model.train(training)
            step = torch.ones(n, dtype=torch.long)
            logits, months = model(inputs['x'], inputs['typ'], inputs['src'], inputs['cont'],
                                   nt, tm, mask, step, inputs['allowed'])
            target, target_time = base.mark_targets(inputs['true_type'], inputs['true_time'])
            known = inputs['allowed']
            occurrence = nn.functional.binary_cross_entropy_with_logits(logits[known], target[known]) if known.any() else logits.sum()*0
            # Auxiliary count is restricted to marks expressible by this frozen
            # allowed interface; never rewrite the cached labels/count or base loss.
            target_count = (target * known).sum(1)
            count = cardinality_nll(logits, known, target_count)
            positive = target.bool() & known
            timing = nn.functional.smooth_l1_loss(months[positive], target_time[positive]) if positive.any() else months.sum()*0
            total = (.75*occurrence + .25*count + .1*timing)
            components = dict(terminal_occurrence=float(occurrence.detach()),
                              terminal_cardinality=float(count.detach()),
                              terminal_time=float(timing.detach()),
                              self_context_nodes=float((~mask).sum(1).float().mean()),
                              terminal_expected_nodes=float((logits.sigmoid()*known).sum(1).detach().mean()),
                              predictable_target_nodes=float(target_count.mean()))
            return total, components
        finally:
            model.train(training)

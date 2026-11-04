"""Website adaptation: normalize candidate features before interaction."""
import torch
from torch.nn import functional as F
from hotpp.modules.def_sota_r53 import InteractingIntervalGraphDEF


class NormalizedInteractingDEF(InteractingIntervalGraphDEF):
    def on_before_optimizer_step(self, optimizer):
        super().on_before_optimizer_step(optimizer)
        gradient = self.graph_region.weight.grad
        if gradient is not None:
            self.log('train/coordination_grad_norm', gradient.float().norm(),
                     on_step=True, on_epoch=True, batch_size=1)

    def decode_scenarios(self, context, queries):
        _, split, time, feature = self.native(context, queries)
        n, scenarios, candidates, _ = feature.shape
        token = self.graph_token(feature)
        token = F.layer_norm(token, (token.shape[-1],))
        token = self.interval_graph(token.flatten(0, 1)).reshape(n, scenarios, candidates, -1)
        shift, radius_raw = self.graph_region(token).float().unbind(-1)
        # Smoothly bound the center. Hard clipping drove the original branch to
        # the boundary on this mostly empty website cohort and killed gradients.
        center = self.horizon * torch.sigmoid(time / self.horizon + 2 * torch.tanh(shift))
        radius = (.01 + .2 * torch.sigmoid(radius_raw)) * self.horizon
        return self.finish(split, center, {'center': center, 'radius': radius})

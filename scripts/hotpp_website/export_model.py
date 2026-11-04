#!/usr/bin/env python3
"""Export the retained HotPP inference graph to a CPU-only TorchScript package."""
import argparse
from pathlib import Path
import torch
from torch import nn
from hydra.utils import instantiate
from omegaconf import OmegaConf
from hotpp.common import initialize
from hotpp.data import PaddedBatch

p=argparse.ArgumentParser()
p.add_argument('--config', required=True)
p.add_argument('--weights')
p.add_argument('--output', type=Path, required=True)
a=p.parse_args()
c=OmegaConf.load(a.config); initialize(c)
model=instantiate(c.module).cpu().eval()
if a.weights:
    model.load_state_dict(torch.load(a.weights, map_location='cpu', weights_only=True), strict=True)
model.requires_grad_(False)
def wrapper(timestamps, labels, lengths):
    # The trace is deliberately one sample with a fixed 65-position computation.
    # The causal encoder's query is selected before the irrelevant padding.
    inputs = PaddedBatch({'timestamps': timestamps, 'labels': labels}, torch.full_like(lengths, 65))
    indices = PaddedBatch((lengths - 1)[:, None], torch.ones_like(lengths))
    generated = model.generate_sequences(inputs, indices).payload
    return generated['timestamps'][:, 0], generated['_labels_logits'][:, 0], generated['_presence_prob'][:, 0]
# Fixed width, left-aligned; varying lengths exercise padding and query indexing.
times=torch.arange(65,dtype=torch.float32)[None]/100
labels=torch.ones(1,65,dtype=torch.long); lengths=torch.tensor([65])
with torch.no_grad():
    traced=torch.jit.trace(wrapper,(times,labels,lengths),check_trace=False,strict=False)
    for lengths in (torch.tensor([65]),torch.tensor([6]),torch.tensor([37]),torch.tensor([12])):
        true_input=PaddedBatch({'timestamps': times, 'labels': labels}, lengths)
        idx=PaddedBatch((lengths-1)[:,None],torch.ones_like(lengths))
        values=model.generate_sequences(true_input,idx).payload
        eager=(values['timestamps'][:,0],values['_labels_logits'][:,0],values['_presence_prob'][:,0])
        actual=traced(times,labels,lengths)
        for x,y in zip(eager,actual): torch.testing.assert_close(x,y,atol=1e-5,rtol=1e-4)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    traced.save(str(a.output))
print('Export and variable-length equivalence passed:',a.output)

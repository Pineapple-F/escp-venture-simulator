#!/usr/bin/env python3
"""Train a candidate without running the held-out evaluation."""
import argparse
import copy
from pathlib import Path
import torch
from hydra.utils import instantiate
from omegaconf import OmegaConf
from hotpp.common import get_trainer, initialize

p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--initial-weights',required=True);a=p.parse_args()
c=OmegaConf.load(a.config);initialize(c)
m=instantiate(c.module);weights=torch.load(a.initial_weights,map_location='cpu',weights_only=True)
weights['graph_region.weight'].zero_();weights['graph_region.bias'].zero_();m.load_state_dict(weights,strict=True)
dm=instantiate(c.data_module);trainer=get_trainer(c);trainer.fit(m,dm)
checkpoint=trainer.checkpoint_callback.best_model_path
if not checkpoint:raise RuntimeError('No validation checkpoint was selected')
m.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=False)['state_dict'])
torch.save(m.state_dict(),c.model_path)
Path(c.model_path+'.source').write_text(checkpoint+'\n')

#!/usr/bin/env python3
"""Derive a website-specific Ours config from the retained paper configuration."""
import argparse
from pathlib import Path
import yaml

p = argparse.ArgumentParser()
p.add_argument('--template', required=True, type=Path)
p.add_argument('--data', required=True, type=Path)
p.add_argument('--output', required=True, type=Path)
p.add_argument('--device', choices=['cpu','cuda'], default='cpu')
p.add_argument('--normalized', action='store_true')
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
c = yaml.safe_load(a.template.read_text())
c['num_classes'] = 35
if a.normalized:
    c['module']['_target_'] = 'hotpp_website.normalized_coordination.NormalizedInteractingDEF'
c['module']['seq_encoder']['embedder']['embeddings']['labels']['in'] = 35
c['module']['loss']['next_item_loss']['losses']['labels']['num_classes'] = 35
c['module']['seq_encoder']['max_inference_context'] = 65
c['data_module'].update(batch_size=32, num_workers=0, min_length=0, max_length=None,
                        fields=['timestamps','labels','is_query','observation_end'])
for split in ('train', 'val', 'test'):
    c['data_module'][split + '_path'] = str(a.data / (split + '.parquet'))
c['seed_everything'] = 0
c['name'] = 'website_ours'
c['model_path'] = str(a.output / 'model.ckpt')
c['report'] = str(a.output / 'report.yaml')
c['logger'] = dict(_target_='pytorch_lightning.loggers.CSVLogger', save_dir=str(a.output), name='metrics', version=0)
c['trainer'].update(accelerator=a.device, devices=1, precision='16-mixed' if a.device == 'cuda' else '32-true',
                    max_epochs=12, check_val_every_n_epoch=2, accumulate_grad_batches=2,
                    enable_progress_bar=False, default_root_dir=str(a.output / 'trainer'))
c['plain_progress'] = True
(a.output / 'config.yaml').write_text(yaml.safe_dump(c))

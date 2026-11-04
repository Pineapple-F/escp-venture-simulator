#!/usr/bin/env python3
"""Calibrate five website event thresholds on validation, then report held-out results."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch
from hydra.utils import instantiate
from omegaconf import OmegaConf
from sklearn.metrics import average_precision_score, precision_recall_fscore_support, precision_recall_curve
from hotpp.common import initialize
from hotpp.data import PaddedBatch

p=argparse.ArgumentParser()
p.add_argument('--config',required=True)
p.add_argument('--weights',required=True)
p.add_argument('--output',required=True,type=Path)
p.add_argument('--device',choices=['cpu','cuda'],default='cuda')
p.add_argument('--validation-only',action='store_true')
a=p.parse_args()
c=OmegaConf.load(a.config); initialize(c)
model=instantiate(c.module).to(a.device).eval(); model.load_state_dict(torch.load(a.weights,map_location='cpu',weights_only=True))
dm=instantiate(c.data_module)

def run(loader):
    scores=[]; times=[]; ys=[]; truth=[]
    with torch.no_grad():
        for features,_ in loader:
            x=features.to(a.device)
            query=x.payload['is_query'].long().argmax(1,keepdim=True)
            idx=PaddedBatch(query,torch.ones(query.shape[0],device=a.device,dtype=torch.long))
            output=model.generate_sequences(x,idx).payload
            probabilities=output['_labels_logits'][:,0].softmax(-1)[...,30:35]
            weighted=probabilities*output['_presence_prob'][:,0,:,None]
            best,which=weighted.max(1)
            prediction_time=output['timestamps'][:,0].gather(1,which)-x.payload['timestamps'].gather(1,query)
            target=(x.payload['labels'][:,:,None] == torch.arange(30,35,device=a.device)) & (torch.arange(x.shape[1],device=a.device)[None,:,None] > query[:,:,None]) & x.seq_len_mask[:,:,None]
            y=target.any(1)
            t=torch.where(target,x.payload['timestamps'][:,:,None]-x.payload['timestamps'].gather(1,query)[:,:,None],torch.full_like(target,2,dtype=torch.float)).amin(1)
            scores.append(best.cpu().numpy());times.append(prediction_time.cpu().numpy());ys.append(y.cpu().numpy());truth.append(t.cpu().numpy())
    return tuple(np.concatenate(v) for v in (scores,times,ys,truth))

def thresholds(scores,y):
    result=[]
    for i in range(5):
        precision,recall,ts=precision_recall_curve(y[:,i],scores[:,i]); f=2*precision[:-1]*recall[:-1]/np.maximum(precision[:-1]+recall[:-1],1e-12)
        result.append(float(ts[np.argmax(f)]))
    return result

def time_calibration(times, y, truth):
    """Fit per-event affine adjustments by validation MAE, retaining time variation."""
    result=[]
    for i in range(5):
        x=times[y[:,i],i]; target=truth[y[:,i],i]
        if len(x)==0:
            result.append({'scale':1.0,'offset':0.0})
            continue
        best=None
        for scale in np.linspace(.25,2,71):
            offset=float(np.median(target-scale*x))
            error=float(np.abs(np.clip(scale*x+offset,1/365.25,1)-target).mean())
            if best is None or error < best[0]:best=(error,float(scale),offset)
        result.append({'scale':best[1],'offset':best[2]})
    return result

def adjust_times(times, calibration):
    return np.stack([np.clip(times[:,i]*value['scale']+value['offset'],1/365.25,1)
                     for i,value in enumerate(calibration)],axis=1)

def report(scores,times,y,truth,ts):
    rows=[]
    for i in range(5):
        p,r,f,_=precision_recall_fscore_support(y[:,i],scores[:,i]>=ts[i],average='binary',zero_division=0)
        positive=y[:,i]; err=np.abs(times[positive,i]-truth[positive,i])*365.25
        rows.append(dict(positive=int(positive.sum()),average_precision=float(average_precision_score(y[:,i],scores[:,i])),precision=float(p),recall=float(r),f1=float(f),mean_absolute_days=float(err.mean()) if len(err) else None,threshold=ts[i]))
    return rows

validation=run(dm.val_dataloader(rank=0,world_size=1)); ts=thresholds(validation[0],validation[2])
clock=time_calibration(validation[1],validation[2],validation[3])
adjusted=(validation[0],adjust_times(validation[1],clock),validation[2],validation[3])
result=dict(thresholds=ts,time_calibration=clock,validation=report(*adjusted,ts),
            validation_uncalibrated=report(*validation,ts))
if not a.validation_only:
    test=run(dm.test_dataloader(rank=0,world_size=1))
    result['test']=report(test[0],adjust_times(test[1],clock),test[2],test[3],ts)
a.output.write_text(json.dumps(result,indent=2))
print(a.output.read_text())

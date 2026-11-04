#!/usr/bin/env python3
"""Evaluate the currently deployed worker on the same validation windows."""
import argparse
import json
import sys
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq
from sklearn.metrics import average_precision_score, precision_recall_fscore_support

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from live_model_worker import Worker

p=argparse.ArgumentParser();p.add_argument('--data',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--batch-size',type=int,default=16);a=p.parse_args()
w=Worker(); rows=pq.read_table(a.data).to_pylist(); rows.sort(key=lambda r:len(r['labels']))
y=[];prob=[];times=[];true_time=[];skipped=0
for offset in range(0,len(rows),a.batch_size):
    samples=[];selected=[]
    for row in rows[offset:offset+a.batch_size]:
        sample,_=w.sample(row['company'],row['cutoff'])
        if sample is None: skipped+=1;continue
        samples.append(sample);selected.append(row)
    if not samples:continue
    pred,months=w.predict(w.collator(samples));prob.append(pred);times.append(months)
    for r in selected:
        i=r['is_query'].index(True); marks=r['labels'][i+1:]; ts=r['timestamps'][i+1:]; q=r['timestamps'][i]
        y.append([k in marks for k in range(30,35)])
        true_time.append([12*(ts[marks.index(k)]-q) if k in marks else 0 for k in range(30,35)])
    if (offset//a.batch_size)%100==0:print(f'{offset+len(selected)}/{len(rows)}',flush=True)
y=np.array(y);scores=np.concatenate(prob);months=np.concatenate(times);truth=np.array(true_time);result=[]
for k,threshold in enumerate(w.thresholds):
    pr,re,f,_=precision_recall_fscore_support(y[:,k],scores[:,k]>=threshold,average='binary',zero_division=0)
    result.append(dict(positive=int(y[:,k].sum()),average_precision=float(average_precision_score(y[:,k],scores[:,k])),precision=float(pr),recall=float(re),f1=float(f),mean_absolute_days=float(np.abs(months[y[:,k],k]-truth[y[:,k],k]).mean()*365.25/12),threshold=float(threshold)))
a.output.write_text(json.dumps({'n':len(y),'skipped':skipped,'events':result},indent=2));print(a.output.read_text(),flush=True)

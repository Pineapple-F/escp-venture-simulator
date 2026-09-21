"""Full-history semantic conditional set diffusion; independent mechanism variants."""
import math
import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn

SEQUENCE=Path(__file__).resolve().parents[1]/'enterprise_path_sequence'
sys.path.insert(0,str(SEQUENCE))
from semantic import SemanticModel
from model import base,objective


class Variant(SemanticModel):
    def __init__(self,config,prior):
        super().__init__();self.config=config
        self.register_buffer('noise_prior',torch.as_tensor(prior,dtype=torch.float32))
        if config.get('verify_noise'):
            self.verifier=nn.Linear(48,48,bias=False)
            nn.init.zeros_(self.verifier.weight)
        if config.get('joint_count'):
            self.cardinality_head=nn.Linear(48,9)
            nn.init.zeros_(self.cardinality_head.weight);nn.init.zeros_(self.cardinality_head.bias)
        if config.get('history_bridge'):
            self.history_gru=nn.GRUCell(48,48)
            self.bridge_projection=nn.Linear(48,48,bias=False)
            nn.init.zeros_(self.bridge_projection.weight)
        self.count_logits=None

    def encode_sequence(self,typ,src,cont,**kwargs):
        h,pad,pooled=super().encode_sequence(typ,src,cont,**kwargs)
        if self.config.get('history_bridge'):
            state=h.new_zeros((len(h),48));parts=[]
            for start in range(0,h.shape[1],128):
                part=h[:,start:start+128];valid=~pad[:,start:start+128]
                parts.append(part+self.bridge_projection(state)[:,None])
                summary=(part*valid[...,None]).sum(1)/valid.sum(1).clamp_min(1)[:,None]
                updated=self.history_gru(summary,state)
                state=torch.where(valid.any(1)[:,None],updated,state)
            h=torch.cat(parts,1).masked_fill(pad[...,None],0.)
            score=torch.einsum('ed,bld->bel',self.event_query,h)/math.sqrt(48)
            score-=nn.functional.softplus(self.log_decay)[None,:,None]*cont[:,None,:,0]
            pooled=torch.einsum('bel,bld->bed',score.masked_fill(pad[:,None],-1e4).softmax(-1),h)
        return h,pad,pooled

    def forward(self,typ,src,cont,noisy_type,noisy_time,noisy_mask,step,allowed,**kwargs):
        history,pad,pooled=self.encode_sequence(typ,src,cont,**kwargs)
        features=torch.stack([noisy_time,torch.sin(math.pi*noisy_time),torch.cos(math.pi*noisy_time)],-1)
        step_emb=self.step_embedding(step)
        marks=self.noisy_mark(noisy_type)
        noise=marks+self.noisy_time(features)+step_emb[:,None]
        if self.config.get('verify_noise'):
            evidence=pooled.gather(1,(noisy_type-1).clamp_min(0)[...,None].expand(-1,-1,48))
            gate=(self.verifier(evidence)*marks).sum(-1)/math.sqrt(48)
            noise=noise*gate.sigmoid()[...,None]
        memory=torch.cat([pooled,history,noise],1)
        memory_pad=torch.cat([torch.zeros((len(typ),8),dtype=torch.bool),pad,noisy_mask],1)
        query=self.slot_query[None]+self.event_query[None]+step_emb[:,None]
        decoded=self.decoder(query,memory,memory_key_padding_mask=memory_pad)
        self.count_logits=self.cardinality_head(decoded.mean(1)) if self.config.get('joint_count') else None
        return self.presence(decoded).squeeze(-1).masked_fill(~allowed,-12.),1+11*self.month(decoded).squeeze(-1).sigmoid()


def corrupt(model,clean_type,clean_time,count,step,rng,allowed):
    if not model.config.get('sparse_noise'):return base.corrupt(clean_type,clean_time,count,step,rng)
    # Cached labels can be int16; embeddings require long indices, times float32.
    nt=torch.zeros(clean_type.shape,dtype=torch.long);tm=torch.zeros(clean_time.shape,dtype=torch.float32)
    mask=torch.ones_like(nt,dtype=torch.bool)
    abar=base.alpha_bar(step);prior=model.noise_prior.numpy()
    for i in range(len(nt)):
        keep=float(abar[i]);points={}
        for j in range(int(count[i])):
            mark=int(clean_type[i,j])
            if mark and rng.random()<=keep:points[mark]=2*(float(clean_time[i,j])-1)/11-1
        for k in range(8):
            if allowed[i,k] and k+1 not in points and rng.random()<(1-keep)*float(prior[k]):
                points[k+1]=float(rng.uniform(-1,1))
        items=list(points.items());rng.shuffle(items)
        for j,(mark,value) in enumerate(items):nt[i,j]=mark;tm[i,j]=value;mask[i,j]=False
    return nt,tm,mask


def initial_noise(model,allowed,rng):
    if not model.config.get('sparse_noise'):return base.initial_noise(len(allowed),rng)
    z=torch.zeros((len(allowed),8))
    return corrupt(model,z.long(),z,torch.zeros(len(z),dtype=torch.long),torch.full((len(z),),12),rng,allowed)


def probabilities(model,logits,allowed):
    p=logits.sigmoid()*allowed
    if model.config.get('joint_count'):
        counts=torch.arange(9)[None]
        cl=model.count_logits.masked_fill(counts>allowed.sum(1)[:,None],-1e4)
        expected=(cl.softmax(-1)*counts).sum(1)
        # Count-mass correction is a ranking score, NOT a calibrated marginal probability.
        p=p*(expected/p.sum(1).clamp_min(1e-6)).clamp(max=1)[:,None]
    return p


def select(model,logits,allowed):
    p=probabilities(model,logits,allowed)
    if not model.config.get('joint_count'):return torch.bernoulli(p).bool()
    counts=torch.arange(9)[None]
    cl=model.count_logits.masked_fill(counts>allowed.sum(1)[:,None],-1e4)
    size=torch.multinomial(cl.softmax(-1),1).squeeze(1)
    result=torch.zeros_like(allowed)
    for i,k in enumerate(size):
        if int(k):
            weights=(p[i]/(1-p[i]).clamp_min(1e-5)).clamp_min(1e-8)*allowed[i]
            result[i,torch.multinomial(weights,int(k),replacement=False)]=True
    return result


def pack(selected,months):return objective.pack(selected,months)


def extra_loss(model,h,t,rng):
    seed=int(rng.integers(0,2**31-1));training=model.training
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed);model.eval()
        nt,tm,mask=initial_noise(model,h['allowed'],rng);contexts=[(nt,tm,mask)]
        with torch.no_grad():
            for current,next_step in ((12,6),(6,1)):
                logits,months=model(**h,noisy_type=nt,noisy_time=tm,noisy_mask=mask,step=torch.full((len(nt),),current))
                selected=select(model,logits,h['allowed']);pt,pm=pack(selected,months)
                nt,tm,mask=corrupt(model,pt,pm,selected.sum(1),torch.full((len(nt),),next_step),rng,h['allowed'])
                contexts.append((nt,tm,mask))
        model.train(training)
        if model.config.get('mixed_correction'):
            chosen=rng.integers(0,3,len(nt));nt,tm,mask=(x.clone() for x in contexts[-1])
            step=torch.ones(len(nt),dtype=torch.long)
            for index,value in enumerate((12,6,1)):
                take=torch.from_numpy(chosen==index)
                nt[take],tm[take],mask[take]=(x[take] for x in contexts[index]);step[take]=value
        else:step=torch.ones(len(nt),dtype=torch.long)
        logits,months=model(**h,noisy_type=nt,noisy_time=tm,noisy_mask=mask,step=step)
        target,timing=base.mark_targets(t['true_type'],t['true_time']);known=h['allowed']
        occurrence=nn.functional.binary_cross_entropy_with_logits(logits[known],target[known]) if known.any() else logits.sum()*0
        count=objective.cardinality_nll(logits,known,(target*known).sum(1))
        positive=target.bool()&known
        time=nn.functional.smooth_l1_loss(months[positive],timing[positive]) if positive.any() else months.sum()*0
        result=.75*occurrence+.25*count+.1*time
        if model.config.get('joint_count'):
            result+=.25*nn.functional.cross_entropy(model.count_logits,(target*known).sum(1).long())
        return result


def training_loss(model,h,t,step,rng,rollout):
    nt,tm,mask=corrupt(model,t['true_type'],t['true_time'],t['count'],step,rng,h['allowed'])
    logits,months=model(**h,noisy_type=nt,noisy_time=tm,noisy_mask=mask,step=step)
    regular=base.loss_fn(logits,months,t['true_type'],t['true_time'],t['count'],t['eligible'],h['allowed'],t['initial'])
    if model.config.get('joint_count'):
        y,_=base.mark_targets(t['true_type'],t['true_time'])
        regular+=.25*nn.functional.cross_entropy(model.count_logits,(y*h['allowed']).sum(1).long())
    return regular+extra_loss(model,h,t,rollout)


def predict(model,h,seed=1042,samples=3):
    model.eval();rng=np.random.default_rng(seed);ps=[];ts=[];paths=[]
    original=model.encode_sequence;cached=[]
    def once(*args,**kwargs):
        if not cached:cached.append(original(*args,**kwargs))
        return cached[0]
    model.encode_sequence=once
    try:
        with torch.random.fork_rng(devices=[]),torch.no_grad():
            torch.manual_seed(seed)
            for _ in range(samples):
                nt,tm,mask=initial_noise(model,h['allowed'],rng)
                for current,next_step in ((12,6),(6,1),(1,0)):
                    logits,months=model(**h,noisy_type=nt,noisy_time=tm,noisy_mask=mask,step=torch.full((len(nt),),current))
                    if not next_step:break
                    selected=select(model,logits,h['allowed']);pt,pm=pack(selected,months)
                    nt,tm,mask=corrupt(model,pt,pm,selected.sum(1),torch.full((len(nt),),next_step),rng,h['allowed'])
                p=probabilities(model,logits,h['allowed']);ps.append(base.metric_probabilities(p));ts.append(base.metric_times(p,months))
                selected=select(model,logits,h['allowed']);path=torch.zeros((len(nt),8,2))
                for i in range(len(nt)):
                    marks=torch.nonzero(selected[i],as_tuple=False).flatten();marks=marks[months[i,marks].argsort()]
                    path[i,:len(marks),0]=marks+1;path[i,:len(marks),1]=months[i,marks].round().clamp(1,12)
                paths.append(path)
        return torch.stack(ps).mean(0).numpy(),torch.stack(ts).mean(0).numpy(),torch.stack(paths,1).numpy()
    finally:model.encode_sequence=original

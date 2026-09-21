"""Minimal count/source adapter to the frozen keyed-set diffusion baseline."""
import math
import numpy as np
import torch
from torch import nn


def model_class(base):
    class CountAwareModel(base.Model):
        def __init__(self, xdim):
            super().__init__(xdim)
            # Preserve base initialization and training RNG consumption.
            state=torch.get_rng_state()
            self.history_quality=nn.Linear(14,16,bias=False)
            nn.init.zeros_(self.history_quality.weight)
            torch.set_rng_state(state)

        def encode_history(self,x,typ,src,cont):
            pad=typ.eq(0)
            h=self.history_input(torch.cat([self.history_type(typ),self.history_source(src),
                self.history_cont(cont[:,:,:4])+self.history_quality(cont[:,:,4:])],-1))
            h=self.history_encoder(h,src_key_padding_mask=pad)
            score=torch.einsum('ed,bld->bel',self.event_query,h)/math.sqrt(h.shape[-1])
            score-=nn.functional.softplus(self.log_decay)[None,:,None]*cont[:,:,0][:,None,:]
            score=score.masked_fill(pad[:,None,:],-1e4)
            pooled=torch.einsum('bel,bld->bed',score.softmax(-1),h)
            return h,pad,pooled,self.summary(x)[:,None,:]
    return CountAwareModel


def tensorize(base,data,mean,std,active,future=False):
    result=base.tensorize(data,mean,std,active,future)
    number=np.asarray(data['seq_event_count'],np.float32)
    mask=np.asarray(data['seq_source_mask'],np.int32)
    extra=np.concatenate([np.log1p(number)[:,:,None],
        np.stack([((mask>>s)&1).astype(np.float32) for s in range(1,14)],-1)],-1)
    result['cont']=torch.cat([result['cont'],torch.from_numpy(extra)],-1)
    return result

"""Local frozen Chinese text embeddings, separate from numbers and identities."""
import hashlib
import re
from collections import OrderedDict
from pathlib import Path

import numpy as np
import torch
from torch import nn

from data import Dataset, attribute_tokens, collate
from model import Model

MODEL_ID = 'BAAI/bge-small-zh-v1.5'
REVISION = '7999e1d3359715c523056ef9478215996d62a620'
LOCAL_MODEL = Path(__file__).with_name('pretrained') / 'bge-small-zh-v1.5'
TEXT_DIM = 512
EVENT_NAMES = {1:'融资',2:'人员进入',3:'人员离开',4:'股东进入',5:'股东退出',
               6:'高管报告',8:'成立',9:'法人进入',10:'法人离开',11:'进入经营异常',
               12:'退出经营异常',19:'注册资本变更',20:'工商变更',21:'行政处罚',
               22:'失信记录',23:'企业年报',25:'估值记录',26:'资产负债表',
               27:'利润表',28:'现金流量表'}


def split_attributes(attributes, event_type):
    """Only descriptive strings go to the text model; never feed anonymous IDs."""
    structural, descriptions = {}, []
    labels = {'detail':'事件内容','position':'岗位','role_or_dealtype':'岗位或交易类型',
              'stage':'原始类型或阶段','round':'融资阶段','round_raw':'融资阶段',
              'change_type':'变更事项','change_field':'变更内容',
              'legal_person_caption':'法人说明','stock_type':'股东类型',
              'amount_str':'金额原文','money':'金额原文','currency':'币种'}
    for key,value in sorted(attributes.items()):
        field = key.rsplit('.',1)[-1]
        identity = field == 'identity' or field.endswith(('_anon','_id'))
        date = field.endswith(('_date','_time')) or field in ('date','real_time','report_year')
        if date:
            # Dates remain in chronological/availability handling, not text attributes.
            continue
        if isinstance(value,str) and value.strip() and not identity and not date:
            value=value.strip()
            # Internal canonical stage markers are represented by numerical stage input.
            if field == 'detail' and re.fullmatch(r'stage:-?\d+(\.\d+)?',value):
                continue
            label=labels.get(field,field)
            if field in ('stage','round','round_raw') and event_type==1:
                label='融资阶段'
            descriptions.append(label+'：'+value)
        else:
            structural[key]=value
    # Deduplicate identical descriptions within a node, not enterprise events.
    text='事件：'+EVENT_NAMES.get(int(event_type),'其他事件')
    if descriptions:
        text+='；'+'；'.join(dict.fromkeys(descriptions))
    return structural,text


class TextEncoder:
    def __init__(self, local_model=LOCAL_MODEL, cache_size=50000, device='cpu'):
        from transformers import AutoModel, AutoTokenizer
        path=Path(local_model)
        if not path.is_dir():
            raise FileNotFoundError('Download '+MODEL_ID+' to '+str(path)+' first.')
        self.tokenizer=AutoTokenizer.from_pretrained(path,local_files_only=True,trust_remote_code=False)
        self.model=AutoModel.from_pretrained(path,local_files_only=True,trust_remote_code=False)
        self.device=torch.device(device)
        self.model.to(self.device).eval().requires_grad_(False)
        self.dimension=int(self.model.config.hidden_size)
        if self.dimension != TEXT_DIM:
            raise ValueError(f'Expected {TEXT_DIM}-dim model, found {self.dimension}')
        self.window=min(int(self.model.config.max_position_embeddings),512)
        self.cache=OrderedDict();self.cache_size=cache_size
        # Cache/model provenance includes the actual locally loaded weight file.
        weight=path/'model.safetensors'
        if not weight.is_file():weight=path/'pytorch_model.bin'
        h=hashlib.sha256()
        with weight.open('rb') as stream:
            for part in iter(lambda:stream.read(1024*1024),b''):h.update(part)
        self.weight_sha=h.hexdigest()

    def encode(self,texts,batch_size=64):
        unique=list(dict.fromkeys(texts))
        missing=[t for t in unique if t not in self.cache]
        vectors={}
        items=[];owners=[]
        capacity=self.window-self.tokenizer.num_special_tokens_to_add(pair=False)
        for text in missing:
            tokens=self.tokenizer.encode(text,add_special_tokens=False,truncation=False,verbose=False)
            for start in range(0,max(1,len(tokens)),capacity):
                items.append(self.tokenizer.prepare_for_model(tokens[start:start+capacity],
                    add_special_tokens=True,return_attention_mask=True,truncation=False))
                owners.append(text)
        # Group similar lengths: one long window must not pad 63 short events.
        order=sorted(range(len(items)),key=lambda i:len(items[i]['input_ids']))
        items=[items[i] for i in order];owners=[owners[i] for i in order]
        totals={};counts={}
        with torch.no_grad():
            for start in range(0,len(items),batch_size):
                encoded=self.tokenizer.pad(items[start:start+batch_size],padding=True,return_tensors='pt')
                encoded={k:v.to(self.device) for k,v in encoded.items()}
                # CLS pooling + normalization follows the model's official usage.
                cls=self.model(**encoded).last_hidden_state[:,0]
                cls=nn.functional.normalize(cls,p=2,dim=1).cpu().numpy()
                for text,vector in zip(owners[start:start+batch_size],cls):
                    totals[text]=totals.get(text,np.zeros(self.dimension,np.float32))+vector
                    counts[text]=counts.get(text,0)+1
        for text in missing:
            vector=totals[text]/counts[text]
            vector=vector/max(float(np.linalg.norm(vector)),1e-12)
            self.cache[text]=vector.astype(np.float32)
        for text in unique:
            vectors[text]=self.cache[text]
            self.cache.move_to_end(text)
        while len(self.cache)>self.cache_size:
            self.cache.popitem(last=False)
        if not texts:
            return np.zeros((0,self.dimension),np.float32)
        return np.stack([vectors[t] for t in texts])


class SemanticDataset(Dataset):
    def __getitem__(self,index):
        sample=super().__getitem__(index)
        frame=self.histories.before(sample['company'],sample['year'])
        separated=[split_attributes(a,t) for a,t in zip(frame.attributes,frame.type)]
        sample['attributes']=[attribute_tokens(a) for a,_ in separated]
        sample['semantic_texts']=[t for _,t in separated]
        return sample


class SemanticCollator:
    def __init__(self,encoder):self.encoder=encoder

    def __call__(self,samples):
        result=collate(samples)
        history=result[0] if isinstance(result,tuple) else result
        texts=[text for sample in samples for text in sample['semantic_texts']]
        vectors=self.encoder.encode(texts)
        padded=np.zeros((*history['typ'].shape,self.encoder.dimension),np.float32)
        offset=0
        for i,sample in enumerate(samples):
            n=len(sample['typ'])
            if n:padded[i,-n:]=vectors[offset:offset+n]
            offset+=n
        history['text_vectors']=torch.from_numpy(padded)
        return result


class SemanticModel(Model):
    def __init__(self):
        super().__init__()
        self.text_projection=nn.Linear(TEXT_DIM,48,bias=False)

    def enrich_nodes(self,h,text_vectors):
        if text_vectors is None:
            raise ValueError('SemanticModel requires real pretrained text_vectors.')
        if text_vectors.shape != (*h.shape[:2],TEXT_DIM):
            raise ValueError('Text vectors do not match historical nodes.')
        return h+self.text_projection(text_vectors)

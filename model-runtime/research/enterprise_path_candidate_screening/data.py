"""Ten candidate event definitions on the unchanged clean_v1 sample/time split."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent;SEQUENCE=HERE.parent/'enterprise_path_sequence'
sys.path.insert(0,str(SEQUENCE))
from data import Histories as BaseHistories
from semantic import SemanticDataset

BASE_EVENTS=('首次观测融资','再次融资','股东进入记录','注册资本变更','注销')
OLD_TO_BASE={1:1,2:2,3:2,4:3,5:4,8:5}
BASE_COLS=np.array([0,1,3,4,7])
CANDIDATES=(
 ('equity_structure','股权结构变更','share'),
 ('institutional_shareholder_entry','企业／机构股东进入','share'),
 ('institutional_shareholder_exit','企业／机构股东退出','share'),
 ('legal_representative_change','法定代表人／负责人变化','legal'),
 ('business_scope_change','经营范围变更','active'),
 ('corporate_identity_restructure','名称／地址／主体类型变更','active'),
 ('equity_investment','股权投资事件','active'),
 ('large_financing','大额融资（披露金额≥1000万美元）','active'),
 ('major_capital_transaction','并购或资本市场重大交易','active'),
 ('annual_report_disclosure','年度报告披露','active'),
)


def dates_by_company(frame,id_column='id',day_column='day'):
    frame=frame[[id_column,day_column]].dropna().drop_duplicates().copy()
    frame[id_column]=frame[id_column].astype(str)
    return {cid:np.sort(group[day_column].to_numpy(dtype='datetime64[D]'))
            for cid,group in frame.groupby(id_column,sort=False)}


def parse_date(values):
    return pd.to_datetime(values.astype('string').str.replace(r'\.0$','',regex=True).str.slice(0,10),
                          errors='coerce',format='mixed')


class Histories(BaseHistories):
    def __init__(self):
        super().__init__();records=self.records
        change=self.table('change').drop_duplicates().reset_index(drop=True)
        change=change.assign(id=change.company_id_anon.astype(str),day=parse_date(change.change_date))
        events={
          'equity_structure':change[change.change_type.eq('股东信息变更')],
          'business_scope_change':change[change.change_type.eq('经营范围变更')],
          'corporate_identity_restructure':change[change.change_type.isin(['名称变更','地址变更','主体类型变更'])],
          'institutional_shareholder_entry':records[records.type.eq(4)&records.detail.astype(str).str.contains('企业|法人|合伙|投资',regex=True)],
          'institutional_shareholder_exit':records[records.type.eq(5)&records.detail.astype(str).str.contains('企业|法人|合伙|投资',regex=True)],
          'legal_representative_change':records[records.type.isin([9,10])|(
              records.type.eq(20)&records.detail.astype(str).str.contains('法定代表人|负责人变更',regex=True))],
          'equity_investment':records[records.type.eq(1)&records.detail.astype(str).str.fullmatch('股权投资')],
          'major_capital_transaction':records[records.type.eq(1)&records.detail.astype(str).str.contains(
              '被收购|战略合并|私有化|IPO|新三板|定向增发|定增|上市后|股权转让|债权融资',regex=True)],
          'annual_report_disclosure':records[records.type.eq(23)],
        }
        funding=self.table('events_sample_cn').drop_duplicates().reset_index(drop=True)
        day=parse_date(funding.event_date);amount=pd.to_numeric(funding.amount_usd,errors='coerce')
        valid=funding.entity_type.eq('company')&funding.event_type.eq('funding_round')&amount.ge(10_000_000)&day.notna()
        events['large_financing']=pd.DataFrame({'id':funding.loc[valid,'entity_id'].astype(str),'day':day[valid]})
        self.candidate_dates={name:dates_by_company(frame) for name,frame in events.items()}

    def attributes(self,row):
        attrs=super().attributes(row);name=row.uid.split(':')[0]
        if name=='partner':
            original=self.table(name).iloc[int(row.uid.rsplit(':',1)[1])]
            for key in ('stock_proportion','stock_capital_num','stock_realcapital_num'):
                if key in original:attrs[name+'.'+key]=self.scalar(original[key])
        return attrs

    def first_month(self,candidate,company,year):
        values=self.candidate_dates[candidate].get(str(company),np.empty(0,dtype='datetime64[D]'))
        start=np.datetime64(f'{int(year)+1}-01-01');end=np.datetime64(f'{int(year)+1}-12-31')
        hit=values[(values>=start)&(values<=end)]
        return None if not len(hit) else int(str(hit[0])[:7].split('-')[1])

    def has_past_legal(self,company,year):
        frame=self.before(company,year)
        return bool(frame.type.eq(9).any())


def candidate_info(key):
    return next(item for item in CANDIDATES if item[0]==key)


def candidate_applicable(histories,key,company,year,old_mask):
    risk=candidate_info(key)[2]
    base=bool(old_mask[3] if risk=='share' else old_mask[7])
    return base and (risk!='legal' or histories.has_past_legal(company,year))


def six_mask(histories,key,sample,field):
    old=np.asarray(sample[field],dtype=bool);base=old[BASE_COLS]
    extra=candidate_applicable(histories,key,sample['company'],sample['year'],old)
    return np.r_[base,extra]


def base_points(old_type,old_time):
    earliest={}
    for mark,month in zip(old_type,old_time):
        new=OLD_TO_BASE.get(int(mark))
        if new:earliest[new]=min(earliest.get(new,99.),float(month))
    return earliest


def adapt_sample(histories,sample,key):
    result=dict(sample);result['allowed']=six_mask(histories,key,sample,'allowed')
    if 'targets' in sample:
        target=dict(sample['targets']);points=base_points(target['true_type'],target['true_time'])
        # Loss eligibility comes from the frozen evaluation mask, while applicability is historical only.
        target['eligible']=np.r_[np.asarray(target['eligible'],bool)[BASE_COLS],result['allowed'][-1]]
        month=histories.first_month(key,sample['company'],sample['year'])
        if month is not None and result['allowed'][-1]:points[6]=month
        typ=np.zeros(6,np.int64);tim=np.zeros(6,np.float32)
        kept=[(mark,month) for mark,month in points.items() if result['allowed'][mark-1]]
        for j,(mark,month) in enumerate(sorted(kept,key=lambda x:(x[1],x[0]))):typ[j]=mark;tim[j]=month
        target.update(true_type=typ,true_time=tim,count=np.asarray(len(kept),dtype=np.int64));result['targets']=target
    return result


def truth(histories,key,split,clean):
    with np.load(clean/'cache'/f'{split}.npz',allow_pickle=False) as z:
        old={k:z[k] for k in ('company','year','eligible','y','time','future_type','future_time','initial')}
    n=len(old['company']);y=np.zeros((n,6),np.int8);tim=np.zeros((n,6),np.float32);eligible=np.zeros((n,6),bool)
    y[:,:5]=old['y'][:,BASE_COLS];tim[:,:5]=old['time'][:,BASE_COLS];eligible[:,:5]=old['eligible'][:,BASE_COLS]
    for i,(company,year) in enumerate(zip(old['company'],old['year'])):
        eligible[i,5]=candidate_applicable(histories,key,company,year,old['eligible'][i])
        month=histories.first_month(key,company,year)
        if eligible[i,5] and month is not None:y[i,5]=1;tim[i,5]=month
    return dict(old,y=y,time=tim,eligible=eligible)


Dataset=SemanticDataset

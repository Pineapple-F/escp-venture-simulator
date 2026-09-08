"""Historical information replay with a cost-basis hypothetical portfolio."""
import copy
import math

VERSION=2
DURATION=36
class RuleError(ValueError): pass

def number(value,label,minimum=0,maximum=1e12):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not minimum<=value<=maximum:
        raise RuleError(label+'无效')
    return value

def record(s,kind,text,amount=0,company=None):
    s['log'].append(dict(date=s['as_of'],kind=kind,text=text,amount=round(amount,2),company=company))

def new_game(universe,name='远航资本',currency='CNY',initial=100000000,fee_rate=0):
    if currency not in ('CNY','USD'):raise RuleError('仅支持人民币或美元独立账户，不自动换汇')
    initial=round(number(initial,'初始资金',1000),2)
    fee_rate=number(fee_rate,'年费率',0,.1)
    s=dict(version=universe.get('version',VERSION),revision=0,name=name[:30],currency=currency,initial=initial,cash=initial,
        fee_rate=fee_rate,fees_paid=0,fees_payable=0,month=0,as_of=universe['start'],
        ended=False,positions={},log=[],curve=[])
    if s['version']==3:
        s['market_path']=copy.deepcopy(universe['market'])
        record(s,'account','建立前向模拟账户；历史资料截止 '+universe['start']+'。')
    else:record(s,'account','建立历史融资配置账户。投资为假设参与，历史事件不受配置影响。')
    mark(s)
    return s

def mark(s):
    cost=round(sum(p['cost'] for p in s['positions'].values()),2)
    point=dict(date=s['as_of'],cash=s['cash'],cost=cost,
        net_assets=round(s['cash']+cost-s['fees_payable'],2),fees_payable=s['fees_payable'])
    value=round(sum(p.get('sim_value',p['cost']) for p in s['positions'].values()),2)
    point.update(sim_value=value,unrealized=round(value-cost,2),sim_assets=round(s['cash']+value-s['fees_payable'],2))
    if s['curve'] and s['curve'][-1]['date']==s['as_of']:s['curve'][-1]=point
    else:s['curve'].append(point)

def visible_rounds(s,u,cid=None):
    cutoff=min(s['as_of'],u['start']) if s.get('version')==3 else s['as_of']
    return [r for r in u['rounds'] if r['available']<=cutoff and (cid is None or r['company']==cid)]

def terms(s,history):
    usable=[r for r in history if r.get('amount') and not r.get('conflict') and r.get('currency') in ('CNY','USD')]
    r=usable[-1] if usable else None
    return dict(target=None,pre_money=None,minimum=None,basis='缺少当前融资条款',
        executable=False,reference=dict(amount=r['amount'],currency=r['currency'],date=r['date'],
          available=r['available'],stage=r['stage'],source_ids=r.get('source_ids',[])) if r else None)


EQUITY_STAGES={'种子轮','天使轮','Pre-A轮','A轮','A+轮','B轮','B+轮','C轮','C+轮','D轮','E轮','F轮','战略投资','战略融资','股权投资'}

def public_state(state,universe):
    if state.get('version') not in (2,3):return None
    s=copy.deepcopy(state);companies=[]
    mark(s)
    from collections import defaultdict
    histories=defaultdict(list);risk_map=defaultdict(list)
    for r in visible_rounds(s,universe):histories[r['company']].append(r)
    for r in universe['risks']:
        if r['date']<=s['as_of']:risk_map[r['company']].append(r)
    for base in universe['companies']:
        history=histories[base['id']]
        if not history and s['version']!=3:continue
        latest=history[-1] if history else dict(id='',company=base['id'],name=base.get('name',base['id']),
            region=base.get('region','未披露'),industry=base.get('industry','未披露'),stage='暂无融资记录',
            amount=None,currency=None,date='—',available='—',conflict=False,publication_proxy=False)
        risks=risk_map[base['id']]
        available=[r for r in history if r['available'][:7]==s['as_of'][:7]]
        companies.append(dict(id=base['id'],name=latest['name'],region=latest['region'],industry=latest['industry'],
            latest=latest,history=history,risks=risks,available=available,terms=terms(s,history),closed=base.get('closed',False)))
    s['companies']=companies
    s['market']=s['market_path'] if s['version']==3 else universe['market'][:s['month']+1]
    s['meta']=universe['meta']
    s['equity_stages']=sorted(EQUITY_STAGES)
    return s

"""User-entered financing plans, separate from historical company facts."""
import copy
from datetime import datetime, timezone
from engine import RuleError, number

MATERIALS=('financials','use_of_funds','cap_table','team','risk_explanation')
BUDGET_KEYS=('research','hiring','marketing','other')

def budget_issues(plan):
    budget=plan.get('budget',{})
    total=round(sum(budget.values()),2)
    issues=[]
    if not total:issues.append('请填写用途预算')
    elif abs(total-(plan.get('target') or 0))>.005:issues.append('用途预算合计必须与本轮融资目标一致')
    if plan.get('burn') is None:issues.append('请补充月净现金消耗')
    if plan.get('burn') and plan.get('cash',0)/plan['burn']>120:issues.append('资金可用期超过十年，请核对现金与月净消耗单位')
    return issues

def save_plan(state, action, universe):
    cid=action.get('company')
    if not any(c['id']==cid for c in universe['companies']):
        raise RuleError('企业不存在')
    raw=action.get('plan')
    if not isinstance(raw,dict):raise RuleError('融资计划无效')
    plan={'currency':raw.get('currency')}
    plan['goal']=raw.get('goal','prepare')
    if plan['goal'] not in ('prepare','raising','watch'):raise RuleError('融资目标无效')
    plan['months']=number(raw.get('months',18),'覆盖月数',1,120)
    if plan['currency'] not in ('CNY','USD'):raise RuleError('请选择币种')
    for key in ('cash','burn','target','pre_money'):
        value=raw.get(key)
        plan[key]=None if value is None else round(number(value,key,0),2)
    purpose=raw.get('purpose','')
    if not isinstance(purpose,str) or len(purpose)>1200:raise RuleError('资金用途限 1200 字')
    plan['purpose']=purpose.strip()
    budget=raw.get('budget',{})
    if not isinstance(budget,dict):raise RuleError('用途预算无效')
    plan['budget']={k:round(number(budget.get(k,0), '用途预算',0),2) for k in BUDGET_KEYS}
    materials=raw.get('materials',[])
    if not isinstance(materials,list) or any(not isinstance(k,str) or k not in MATERIALS for k in materials):
        raise RuleError('材料状态无效')
    plan['materials']=sorted(set(materials))
    plan['source']='user_entered'
    plan['updated_at']=datetime.now(timezone.utc).isoformat()
    active=state.get('founder_rounds',{}).get(cid)
    reset=False
    if active:
        old=state['founder_plans'][cid]
        if plan['cash']!=old.get('cash') or plan['currency']!=old.get('currency'):raise RuleError('融资开始后现金基准与币种不能修改，到账由系统记账')
        if any(plan[k]!=old.get(k) for k in ('cash','target','currency','pre_money')):
            if any(a['status'] in ('submitted','terms','accepted','settled') for a in active['applications'].values()):
                raise RuleError('处理中、待确认或已成交方案锁定本轮目标与估值；请先处理反馈，可补材料或调整未确认的单家金额')
            reset=True
    s=copy.deepcopy(state)
    if reset:
        s.setdefault('founder_round_archives',{}).setdefault(cid,[]).append(s['founder_rounds'].pop(cid))
    s.setdefault('founder_plans',{})[cid]=plan
    s['founder_company']=cid
    s['revision']+=1
    return s

def save_contact(state,action,universe,institutions):
    cid=action.get('company');iid=action.get('institution')
    if not isinstance(cid,str) or not any(c['id']==cid for c in universe['companies']):raise RuleError('企业不存在')
    if not isinstance(iid,str) or iid not in institutions:raise RuleError('机构不存在')
    stage=action.get('stage','待接触');note=action.get('note','')
    if stage not in ('待接触','已沟通','补材料','条款讨论','已拒绝'):raise RuleError('接触状态无效')
    if not isinstance(note,str) or len(note)>1000:raise RuleError('备注限 1000 字')
    s=copy.deepcopy(state)
    contacts=s.setdefault('founder_contacts',{}).setdefault(cid,{})
    contacts[iid]=dict(id=iid,name=institutions[iid]['name'],stage=stage,note=note.strip(),updated_at=datetime.now(timezone.utc).isoformat())
    s['founder_company']=cid;s['revision']+=1
    return s

"""v3 guard: missing economics stay unknown; preserve original saved records."""
import copy
import calendar
from datetime import date
import engine as legacy

def month_end(month):
    year=2019+(11+month)//12
    mon=(11+month)%12+1
    return date(year,mon,calendar.monthrange(year,mon)[1]).isoformat()

def new_game(*args,**kwargs):
    s=legacy.new_game(*args,**kwargs)
    s['opening_point']=copy.deepcopy(s['curve'][0])
    s['transaction_points']=[]
    return s
RuleError=legacy.RuleError

def apply(state,action,universe,projection=None):
    if state.get('version')!=3:raise RuleError('请建立新版账户')
    if action.get('type')=='founder_goal':
        cid=action.get('company');goal=action.get('goal')
        if not isinstance(cid,str) or not any(c['id']==cid for c in universe['companies']):raise RuleError('企业不存在')
        if goal not in ('prepare','raising','watch'):raise RuleError('融资目标无效')
        s=copy.deepcopy(state);s.setdefault('founder_goals',{})[cid]=goal;s['founder_company']=cid;s['revision']+=1
        return s
    if action.get('type')=='founder_plan':
        from founder import save_plan
        return save_plan(state,action,universe)
    if state['ended']:raise RuleError('已到模拟区间末')
    s=copy.deepcopy(state);kind=action.get('type')
    s.pop('last_result',None)
    if kind=='offer':
        cid=action.get('company')
        company=next((c for c in universe['companies'] if c['id']==cid),None)
        if not company:raise RuleError('企业不存在')
        if company.get('closed'):raise RuleError('企业有注销或吊销记录')
        if s['fees_payable']:raise RuleError('请先结清管理费')
        amount=round(legacy.number(action.get('amount'),'投资金额',.01),2)
        if amount>s['cash']:raise RuleError('可用现金不足')
        p=s['positions'].setdefault(cid,dict(cost=0,lots=[]))
        p['lots'].append(dict(round='allocation-'+str(s['revision']),date=s['as_of'],amount=amount,
                             currency=s['currency'],entry_ownership=None,assumed_post_valuation=None,
                             mode='simulated_cost_allocation'))
        p['cost']=round(p['cost']+amount,2)
        s['cash']=round(s['cash']-amount,2)
        if projection and projection.get('available') and projection.get('predicted'):
            target_month=projection.get('month_index')
            if isinstance(target_month,int) and target_month>s['month']:
                current_value=round(p.get('sim_value',p['cost']-amount)+amount,2)
                p['sim_value']=current_value
                p['month_change']=0
                p['projection_mode']='peer_financing_projection_v1'
                p['projection']=copy.deepcopy(projection)
                p['projection_start_month']=s['month']
                p['projection_target_month']=target_month
                p['projection_base_value']=current_value
                p['projection_target_value']=round(current_value*projection['value_multiple'],2)
                p['projection_complete']=False
        s.setdefault('intentions',{}).pop(cid,None)
        if p.get('projection_mode'):
            legacy.record(s,'allocation','模拟投资完成：已扣款，并按未来融资预测建立月度估值路径。',-amount,cid)
        else:
            legacy.record(s,'allocation','模拟投资完成：已扣款并计入投资成本；暂无融资估值预测。',-amount,cid)
        s['last_result']=dict(company=cid,amount=amount,cash=s['cash'],total_cost=p['cost'],
            currency=s['currency'],status='模拟资金配置完成',projection=copy.deepcopy(p.get('projection')))
    elif kind=='advance':
        s['month']+=1
        offset=(int(universe['start'][:4])-2019)*12+int(universe['start'][5:7])-12
        s['as_of']=month_end(offset+s['month'])
        fee=round(s['initial']*s['fee_rate']/12,2)
        due=round(s['fees_payable']+fee,2);paid=min(s['cash'],due)
        s['cash']=round(s['cash']-paid,2);s['fees_paid']=round(s['fees_paid']+paid,2)
        s['fees_payable']=round(due-paid,2);s['notifications']=[]
        if fee:legacy.record(s,'fee','按账户设置计提管理费',-paid)
        for cid,p in s['positions'].items():
            if p.get('projection_mode')!='peer_financing_projection_v1' or p.get('projection_complete'):
                continue
            start=p.get('projection_start_month',0);target=p.get('projection_target_month')
            if not isinstance(target,int) or target<=start:
                continue
            previous=round(p.get('sim_value',p['cost']),2)
            progress=max(0,min(1,(s['month']-start)/(target-start)))
            base=max(.01,p.get('projection_base_value',p['cost']))
            destination=max(.01,p.get('projection_target_value',base))
            value=round(base*((destination/base)**progress),2)
            p['sim_value']=value;p['month_change']=round(value-previous,2)
            reached=s['month']>=target
            if reached:p['projection_complete']=True
            details=p.get('projection',{})
            text=('到达预计融资月份，完成本轮预测估值更新。' if reached else '按预计融资进度更新本月持仓估值。')
            s['notifications'].append(dict(company=cid,reason=text,previous=previous,value=value,
                delta=p['month_change'],event_due=reached,estimated_month=details.get('estimated_month'),
                predicted_amount=details.get('predicted_amount'),currency=details.get('currency'),
                date=s['as_of']))
        if s['notifications']:
            total_delta=round(sum(item['delta'] for item in s['notifications']),2)
            legacy.record(s,'projection',f'月度推进：更新 {len(s["notifications"])} 家持仓的预测价值。',total_delta)
        else:
            legacy.record(s,'data','模拟日期推进；本月没有需要更新的持仓预测。')
        s['ended']=s['month']>=legacy.DURATION
    else:raise RuleError('不支持的操作')
    s['revision']+=1
    # Cost ledger remains valid; original hypothetical values are retained in saved lots.
    legacy.mark(s)
    point=copy.deepcopy(s['curve'][-1]);point['revision']=s['revision'];point['action']=kind
    s.setdefault('transaction_points',[]).append(point)
    return s

def public_state(state,universe,compact=True):
    s=legacy.public_state(state,universe)
    if not s:return s
    visible_companies={company['id'] for company in s['companies']}
    if s.get('founder_company') not in visible_companies:
        s.pop('founder_company',None)
    s['evidence_mode']=True
    projected=any(p.get('projection_mode')=='peer_financing_projection_v1' for p in s['positions'].values())
    for p in s['positions'].values():
        p['legacy_assumption']=bool(p.get('scenario')) or any(lot.get('mode')!='simulated_cost_allocation' for lot in p.get('lots',[]))
        p['ownership']=None
        if p.get('projection_mode')!='peer_financing_projection_v1':
            p['sim_value']=None;p['month_change']=None
        for lot in p.get('lots',[]):
            lot['entry_ownership']=None;lot['assumed_post_valuation']=None
    if not projected:
        for point in s['curve']+s.get('transaction_points',[])+([s['opening_point']] if s.get('opening_point') else []):
            point['sim_value']=None;point['sim_assets']=None;point['unrealized']=None
        s['notifications']=[]
    # The UI receives historical market observations, never the old synthetic path.
    s['market']=copy.deepcopy(universe['market'])
    s.pop('market_path',None)
    if compact:
        for c in s['companies']:
            c['history']={'length':len(c['history'])}
            c['details_loaded']=False
    for row in s['log']:
        if row['kind'] in ('valuation','deal','offer'):row['text']='[历史模拟记录] '+row['text']
    return s

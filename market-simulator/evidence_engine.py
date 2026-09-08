"""v3 guard: missing economics stay unknown; preserve original saved records."""
import copy
import engine as legacy
from data_pipeline import month_end

def new_game(*args,**kwargs):
    s=legacy.new_game(*args,**kwargs)
    s['opening_point']=copy.deepcopy(s['curve'][0])
    s['transaction_points']=[]
    return s
RuleError=legacy.RuleError

def apply(state,action,universe):
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
        s.setdefault('intentions',{}).pop(cid,None)
        legacy.record(s,'allocation','模拟投资完成：已扣款并计入投资成本；暂无股权与市值依据。',-amount,cid)
        s['last_result']=dict(company=cid,amount=amount,cash=s['cash'],total_cost=p['cost'],
            currency=s['currency'],status='模拟资金配置完成')
    elif kind=='advance':
        s['month']+=1
        offset=(int(universe['start'][:4])-2019)*12+int(universe['start'][5:7])-12
        s['as_of']=month_end(offset+s['month'])
        fee=round(s['initial']*s['fee_rate']/12,2)
        due=round(s['fees_payable']+fee,2);paid=min(s['cash'],due)
        s['cash']=round(s['cash']-paid,2);s['fees_paid']=round(s['fees_paid']+paid,2)
        s['fees_payable']=round(due-paid,2);s['notifications']=[]
        if fee:legacy.record(s,'fee','按账户设置计提管理费',-paid)
        legacy.record(s,'data','模拟日期推进；无可靠新交易或估值依据，不生成成交与收益。')
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
    s['evidence_mode']=True
    for p in s['positions'].values():
        p['legacy_assumption']=bool(p.get('scenario')) or any(lot.get('mode')!='simulated_cost_allocation' for lot in p.get('lots',[]))
        p['ownership']=None;p['sim_value']=None;p['month_change']=None
        for lot in p.get('lots',[]):
            lot['entry_ownership']=None;lot['assumed_post_valuation']=None
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
        if row['kind'] in ('valuation','deal','offer'):row['text']='[旧规则记录，非核验结果] '+row['text']
    return s

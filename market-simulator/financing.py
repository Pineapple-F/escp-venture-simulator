"""Deterministic disclosed-rule financing scenario, never historical investor consent."""
import copy
from datetime import date, timedelta
from engine import RuleError, number
from founder import budget_issues

def transact(state,action,universe,institutions):
    cid=action.get('company');kind=action.get('type');iid=action.get('institution')
    company=next((c for c in universe['companies'] if c['id']==cid),None)
    if not company:raise RuleError('企业不存在')
    if company.get('closed'):raise RuleError('注销或吊销主体不能发起模拟融资')
    plan=state.get('founder_plans',{}).get(cid,{})
    s=copy.deepcopy(state)
    rounds=s.setdefault('founder_rounds',{})
    if cid not in rounds:
        if kind!='financing_submit':raise RuleError('请先提交融资方案')
        if not plan.get('target') or not plan.get('pre_money') or plan.get('cash') is None or not plan.get('purpose'):raise RuleError('请保存融资目标、用途、现金与模拟投前估值')
        rounds[cid]=dict(target=plan['target'],pre_money=plan['pre_money'],currency=plan['currency'],cash=plan['cash'],opening_cash=plan['cash'],raised=0,date=universe['start'],week=0,applications={},ledger=[])
    r=rounds[cid];apps=r['applications']
    def log(text):r['ledger'].append(dict(date=r['date'],text=text))
    if kind=='financing_submit':
        if iid not in s.get('founder_contacts',{}).get(cid,{}) or iid not in institutions:raise RuleError('请先加入接触名单')
        old=apps.get(iid)
        if old and old['status'] not in ('rejected','materials','declined'):raise RuleError('该机构已有处理中或已交割方案')
        amount=round(number(action.get('amount'),'申请认购金额',.01),2)
        if amount>r['target']-r['raised']:raise RuleError('申请金额超过本轮剩余目标')
        apps[iid]=dict(name=institutions[iid]['name'],amount=amount,status='submitted',due=r['week']+1,feedback='已提交，下周反馈',materials=plan.get('materials',[]),purpose=plan['purpose'],proposal=copy.deepcopy(plan))
        log(institutions[iid]['name']+'：提交模拟融资方案')
    elif kind=='financing_week':
        r['week']+=1;r['date']=(date.fromisoformat(r['date'])+timedelta(days=7)).isoformat()
        history=[x for x in universe['rounds'] if x['company']==cid and x['available']<=universe['start']]
        latest=history[-1] if history else {}
        for key,a in apps.items():
            if a['status']=='accepted' and a['due']<=r['week']:
                a['status']='settled';r['raised']=round(r['raised']+a['amount'],2);r['cash']=round(r['cash']+a['amount'],2)
                a['feedback']='模拟交割完成，资金已到账';log(a['name']+'：模拟到账 '+str(a['amount'])+' '+r['currency'])
            elif a['status']=='submitted' and a['due']<=r['week']:
                matching=[x for x in institutions[key]['rounds'] if x['company']!=cid and x['available']<=universe['start'] and latest.get('industry') not in (None,'','未披露') and x['industry']==latest['industry']]
                if not matching:a.update(status='rejected',feedback='未找到同业历史投资依据。本情景不进入条款讨论，可换同业机构重试。')
                elif budget_issues(a.get('proposal',{})):a.update(status='materials',feedback='；'.join(budget_issues(a.get('proposal',{})))+'。保存方案后可重新提交。')
                else:a.update(status='terms',feedback='按你提出的金额与估值进入模拟条款讨论；不是机构真实报价。')
                log(a['name']+'：'+a['feedback'])
        # All new money buys shares at the same fixed round price; original holder group starts at 100%.
        denominator=r['pre_money']+r['raised']
        r['original_ownership']=r['pre_money']/denominator
        for a in apps.values():a['ownership']=a['amount']/denominator if a['status']=='settled' else 0
        log('推进一周：仅推进融资流程，未模拟经营收支')
    elif kind in ('financing_accept','financing_decline'):
        a=apps.get(iid)
        if not a or a['status']!='terms':raise RuleError('当前没有可确认的条款')
        if kind=='financing_decline':a.update(status='declined',feedback='你已拒绝条款，可调整申请金额后重提')
        else:
            reserved=sum(x['amount'] for x in apps.values() if x['status'] in ('accepted','settled'))
            if reserved+a['amount']>r['target']:raise RuleError('已确认金额加本次金额超过融资目标，请拒绝并调整申请金额')
            a.update(status='accepted',due=r['week']+1,feedback='条款已确认，下周模拟交割到账')
        log(a['name']+'：'+a['feedback'])
    else:raise RuleError('不支持的融资操作')
    s['founder_company']=cid;s['revision']+=1
    return s

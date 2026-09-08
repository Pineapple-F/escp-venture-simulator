"""Historical investor candidates; no invented contact details or live activity."""
from collections import defaultdict
import duckdb
from data_pipeline import SOURCE

def build_index(universe):
    events={sid:r for r in universe['rounds'] for sid in r['source_ids']}
    groups=defaultdict(dict);names={}
    with duckdb.connect() as db:
        rows=db.execute('SELECT event_id_anon, investor_key_anon, investor_name_pseudo FROM read_parquet(?) WHERE investor_key_anon IS NOT NULL AND investor_name_pseudo IS NOT NULL AND NOT coalesce(has_source_conflict,false)',[str(SOURCE/'investment_events.parquet')]).fetchall()
    for eid,key,name in rows:
        if eid not in events or not name.strip():continue
        r=events[eid];groups[key][r['id']]=r;names.setdefault(key,set()).add(name)
    return {key:dict(id=key,name=next(iter(names[key])),rounds=list(rounds.values())) for key,rounds in groups.items() if len(names[key])==1}

def candidates(index,company,latest,cutoff):
    industry=latest.get('industry');stage=latest.get('stage');output=[]
    if industry in (None,'','未披露'):return []
    for inst in index.values():
        same=[r for r in inst['rounds'] if r['industry']==industry and r['company']!=company and r['available']<=cutoff]
        if not same:continue
        exact=[r for r in same if r['stage']==stage]
        examples=sorted(exact or same,key=lambda r:r['available'],reverse=True)
        output.append(dict(id=inst['id'],name=inst['name'],industry_count=len({r['company'] for r in same}),stage_count=len({r['company'] for r in exact}),latest=max(r['available'] for r in same),examples=[dict(company=r['name'],stage=r['stage'],date=r['available'],source_ids=r['source_ids'],event_date=r.get('date',r['available']),amount=r.get('amount'),currency=r.get('currency'),industry=r.get('industry'),publication_proxy=r.get('publication_proxy',False)) for r in examples[:3]]))
    return sorted(output,key=lambda r:(-r['stage_count'],-r['industry_count'],r['id']))[:20]

def pool(index,company,latest,cutoff,query='',scope='all',sort='match',page=1):
    if scope not in ('all','industry','stage'):raise ValueError('筛选条件无效')
    if sort not in ('match','recent','count'):raise ValueError('排序条件无效')
    industry=latest.get('industry');stage=latest.get('stage');rows=[]
    for inst in index.values():
        if query.casefold() not in inst['name'].casefold():continue
        history=[r for r in inst['rounds'] if r['available']<=cutoff]
        if not history:continue
        same=[r for r in history if industry not in (None,'','未披露') and r['industry']==industry and r['company']!=company]
        exact=[r for r in same if stage not in (None,'','暂无融资记录','未披露轮次') and r['stage']==stage]
        if scope=='industry' and not same or scope=='stage' and not exact:continue
        industries=sorted({r['industry'] for r in history if r['industry'] not in (None,'','未披露')})
        rows.append(dict(id=inst['id'],name=inst['name'],industry_count=len({r['company'] for r in same}),stage_count=len({r['company'] for r in exact}),company_count=len({r['company'] for r in history}),industries=industries,latest=max(r['available'] for r in history),examples=[dict(company=r['name'],stage=r['stage'],date=r['available'],source_ids=r['source_ids'],event_date=r.get('date',r['available']),amount=r.get('amount'),currency=r.get('currency'),industry=r.get('industry'),publication_proxy=r.get('publication_proxy',False)) for r in sorted(history,key=lambda r:r['available'],reverse=True)[:3]]))
    rows.sort(key=lambda r:r['id'])
    rows.sort(key=lambda r:(r['stage_count'],r['industry_count'],r['latest']) if sort=='match' else r['latest'] if sort=='recent' else r['company_count'],reverse=True)
    total=len(rows);pages=max(1,(total+11)//12);page=max(1,min(page,pages))
    return dict(items=rows[(page-1)*12:page*12],total=total,page=page,pages=pages)

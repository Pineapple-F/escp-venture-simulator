"""Build auditable historical rounds. Never impute missing economics."""
import calendar
import hashlib
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'processed' / 'cleaned'
START = '2019-12-31'
END = '2022-12-31'
VERSION = 2

def parse_money(raw):
    """Only exact amounts with an explicit supported currency; no ranges/estimates."""
    if not isinstance(raw, str): return None, None
    s = raw.strip().replace(',', '').replace(' ', '')
    m = re.fullmatch(r'(\$)?(\d+(?:\.\d+)?)(亿|万|千)?(美元|人民币|元|USD|CNY)?', s)
    if not m: return None, None
    prefix, number, unit, suffix = m.groups()
    currency = 'USD' if prefix or suffix in ('美元','USD') else 'CNY' if suffix in ('人民币','元','CNY') else None
    if not currency or (prefix and suffix in ('人民币','元','CNY')): return None, None
    value = float(number) * {None:1,'千':1000,'万':10000,'亿':100000000}[unit]
    return (value, currency) if value > 0 else (None, None)

def month_end(month):
    year = 2019 + (11 + month)//12
    mon = (11 + month)%12+1
    return date(year,mon,calendar.monthrange(year,mon)[1]).isoformat()

def build(end=END,output='universe-v2.json'):
    db=duckdb.connect()
    db.read_parquet(str(SOURCE/'investment_events.parquet')).create_view('funding')
    db.read_parquet(str(SOURCE/'events_sample_cn.parquet')).create_view('events')
    rows=db.execute("""SELECT event_id_anon,invested_company_id_anon,invested_company_name_pseudo,
      event_date,pub_date,round_std,amount_num_clean,currency_normalized,
      amount_str_parsed_value,amount_str_parsed_currency,amount_str_parsed_is_fuzzy,
      valuation,city,industry_type,source,has_source_conflict,pub_date_is_suspect
      FROM funding WHERE invested_company_id_anon IS NOT NULL
      AND event_date >= '1990-01-01' AND event_date <= ?::TIMESTAMP
      AND NOT coalesce(event_date_is_suspect,false) ORDER BY event_date,event_id_anon""",[end]).fetchall()
    grouped=defaultdict(list)
    for row in rows:
        eid,cid,name,day,pub,stage,num,cur,parsed,pcur,fuzzy,val,city,industry,source,conflict,pub_suspect=row
        # Invalid explicit publication dates cannot establish an information cutoff.
        if pub_suspect: continue
        known=max(day.date(),pub.date()) if pub else day.date()
        if known.isoformat()>end: continue
        amount,currency=(num,cur) if num and cur in ('CNY','USD') else (parsed,pcur) if parsed and not fuzzy and pcur in ('CNY','USD') else (None,None)
        value,vcur=parse_money(val)
        grouped[(cid,day.date().isoformat(),stage or '未披露轮次')].append(dict(
            id=eid,name=name,date=day.date().isoformat(),known=known.isoformat(),publication_proxy=pub is None,
            amount=amount,currency=currency,valuation=value,valuation_currency=vcur,valuation_raw=val,
            city=city,industry=industry,source=source,conflict=bool(conflict)))
    rounds=[]
    for (cid,day,stage),items in grouped.items():
        amounts={(x['amount'],x['currency']) for x in items if x['amount']}
        vals={(x['valuation'],x['valuation_currency']) for x in items if x['valuation']}
        conflict=any(x['conflict'] for x in items) or len(amounts)>1
        amount,currency=next(iter(amounts)) if len(amounts)==1 and not conflict else (None,None)
        value,vcur=next(iter(vals)) if len(vals)==1 and not any(x['conflict'] for x in items) else (None,None)
        # Conservative: don't merge later-disclosed details into an earlier information set.
        known=max(x['known'] for x in items)
        rounds.append(dict(id='rd_'+hashlib.sha256(f'{cid}|{day}|{stage}'.encode()).hexdigest()[:16],
            company=cid,date=day,available=known,stage=stage,amount=amount,currency=currency,
            valuation=value,valuation_currency=vcur,valuation_basis='投前/投后未标明' if value else '未披露或无法核验',
            name=next((x['name'] for x in items if x['name']),cid),
            region=next((x['city'] for x in items if x['city']),'未披露'),
            industry=next((x['industry'] for x in items if x['industry']),'未披露'),
            source=sorted({x['source'] for x in items if x['source']}),
            source_ids=sorted(x['id'] for x in items),source_records=len(items),conflict=conflict,
            publication_proxy=any(x['publication_proxy'] for x in items)))
    rounds.sort(key=lambda r:(r['available'],r['date'],r['id']))
    # Fixed cohort chosen solely with information available at START, not future success.
    latest={}
    for r in rounds:
        if '2017-01-01' <= r['available'] <= START: latest[r['company']]=r
    chosen=sorted({r['company'] for r in rounds})
    ids=set(chosen)
    companies=[dict(id=cid) for cid in chosen]
    risk_rows=db.execute("""SELECT company_id_anon,event_date,event_type,count(*)
      FROM events WHERE event_type IN ('abnormal_listing','abnormal_removed')
      AND event_date BETWEEN '1990-01-01' AND ?::TIMESTAMP
      AND NOT coalesce(event_date_is_suspect,false)
      GROUP BY company_id_anon,event_date,event_type ORDER BY event_date,event_type""",[end]).fetchall()
    risks=[dict(company=cid,date=d.date().isoformat(),type=t,records=n) for cid,d,t,n in risk_rows if cid in ids]
    market=[]
    count=(int(end[:4])-2019)*12+int(end[5:7])-12
    for month in range(count+1):
        market_end=month_end(month);begin=market_end[:7]+'-01'
        rs=[r for r in rounds if begin<=r['available']<=market_end]
        market.append(dict(date=market_end,rounds=len(rs),disclosed=sum(r['amount'] is not None for r in rs),
            CNY=round(sum(r['amount'] for r in rs if r['currency']=='CNY'),2),
            USD=round(sum(r['amount'] for r in rs if r['currency']=='USD'),2)))
    result=dict(version=VERSION,start=START,end=end,companies=companies,
        rounds=[r for r in rounds if r['company'] in ids],risks=risks,market=market,
        meta=dict(version=VERSION,start=START,end=end,
            scanned_events=db.execute('select count(*) from events').fetchone()[0],
            funding_records=db.execute('select count(*) from funding').fetchone()[0],
            eligible_companies=len(latest),cohort_size=len(companies),
            sources=['processed/cleaned/investment_events.parquet','processed/cleaned/events_sample_cn.parquet'],
            method='按被投企业ID、事件日期、轮次归并候选融资；不累加投资人重复金额。缺失和冲突金额不计入总额。'))
    out=ROOT/'runtime';out.mkdir(exist_ok=True)
    (out/output).write_text(json.dumps(result,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    return result

if __name__=='__main__':
    u=build()
    print(json.dumps(dict(meta=u['meta'],cohort_rounds=len(u['rounds']),start_market=u['market'][0]),ensure_ascii=False))

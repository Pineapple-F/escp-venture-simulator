"""Conservative latest complete-month snapshot; no future rows used in simulation."""
import json
import duckdb
from data_pipeline import build,SOURCE,ROOT

CUTOFF='2026-03-31'

def build_forward():
    u=build(end=CUTOFF,output='universe-v3.json')
    db=duckdb.connect()
    rows=db.execute("""SELECT company_id_anon,company_name_pseudo,province_name,
      CASE WHEN NOT coalesce(establish_date_is_suspect,false) THEN cast(establish_date AS DATE) END,
      CASE WHEN NOT coalesce(cancel_date_is_suspect,false) THEN cast(cancel_date AS DATE) END,
      CASE WHEN NOT coalesce(revoke_date_is_suspect,false) THEN cast(revoke_date AS DATE) END
      FROM read_parquet(?) WHERE company_id_anon IS NOT NULL ORDER BY company_id_anon,company_name_pseudo""",
      [str(SOURCE/'company.parquet')]).fetchall()
    companies={c['id']:c for c in u['companies']}
    excluded=set()
    for cid,name,region,established,cancelled,revoked in rows:
        if established and established.isoformat()>CUTOFF:
            excluded.add(cid);continue
        companies[cid]=dict(id=cid,name=name or cid,region=region or '未披露',industry='未披露',
            established=established.isoformat() if established else None,
            closed=any(d and d.isoformat()<=CUTOFF for d in [cancelled,revoked]))
    for cid in excluded:companies.pop(cid,None)
    # Include risk records for companies without funding as well.
    risks=db.execute("""SELECT company_id_anon,cast(event_date AS DATE),event_type,count(*)
      FROM read_parquet(?) WHERE company_id_anon IS NOT NULL
      AND event_type IN ('abnormal_listing','abnormal_removed')
      AND event_date>='1990-01-01' AND event_date<?::DATE+INTERVAL 1 DAY
      AND NOT coalesce(event_date_is_suspect,false) GROUP BY 1,2,3 ORDER BY 2,3""",
      [str(SOURCE/'events_sample_cn.parquet'),CUTOFF]).fetchall()
    u['risks']=[dict(company=cid,date=d.isoformat(),type=t,records=n) for cid,d,t,n in risks if cid in companies]
    u['companies']=list(companies.values())
    u['rounds']=[r for r in u['rounds'] if r['company'] in companies]
    funded={r['company'] for r in u['rounds']}
    u.update(version=3,start=CUTOFF,end='2029-03-31',historical_market=u['market'])
    u['market']=[dict(u['historical_market'][-1],simulated=False)]
    u['meta'].update(version=3,start=CUTOFF,end=u['end'],cutoff=CUTOFF,
        cohort_size=len(companies),no_funding_companies=len(set(companies)-funded),
        company_master_ids=len({r[0] for r in rows}),excluded_future_establishment=len(excluded),
        cutoff_basis='最新有效日期为2026-04-04；4月不完整，保守采用前一月末。各来源完整性未获独立保证。',
        profile_limit='企业主表为快照，缺少字段可用时间；不宣称严格点时还原。')
    (ROOT/'runtime/universe-v3.json').write_text(json.dumps(u,ensure_ascii=False,allow_nan=False))
    print(json.dumps(u['meta'],ensure_ascii=False))
    return u

if __name__=='__main__':build_forward()

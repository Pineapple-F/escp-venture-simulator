"""Read-only company snapshot and officer records; no headcount inference."""
import duckdb
from data_pipeline import SOURCE

def profile(cid,cutoff):
    with duckdb.connect() as db:
        rows=db.execute('SELECT company_type_group,province_name,capital,real_capital,legal_person_pseudo,CASE WHEN NOT coalesce(establish_date_is_suspect,false) THEN CAST(establish_date AS DATE) END FROM read_parquet(?) WHERE company_id_anon=?',[str(SOURCE/'company.parquet'),cid]).fetchall()
        fields={}
        for i,key in enumerate(('type','province','capital','paid_capital','legal_person','established')):
            values={str(r[i]) for r in rows if r[i] is not None and str(r[i]).strip()}
            fields[key]=next(iter(values)) if len(values)==1 else '记录冲突' if values else '未披露'
        people=db.execute('''SELECT DISTINCT employee_name_pseudo,position,CAST(include_date AS DATE),CAST(remove_date AS DATE),is_history,
          coalesce(include_date_is_suspect,false) OR coalesce(remove_date_is_suspect,false) OR coalesce(invalid_date_interval,false)
          FROM read_parquet(?) WHERE company_id_anon=? AND (include_date IS NULL OR include_date<=?::DATE OR coalesce(include_date_is_suspect,false))
          ORDER BY employee_name_pseudo,position,include_date''',[str(SOURCE/'employee.parquet'),cid,cutoff]).fetchall()
    officers=[]
    for name,role,start,end,historical,suspect in people:
        status='时间待核验' if suspect else '历史任职' if end and end.isoformat()<=cutoff else '历史标记，离任时间未明确' if historical else '未记录离任'
        officers.append(dict(name=name or '姓名未披露',position=role or '职务未披露',start=start.isoformat() if start and not suspect else None,end=end.isoformat() if end and not suspect and end.isoformat()<=cutoff else None,status=status))
    return dict(fields=fields,officers=officers,source='清洗企业主表、主要人员表',note='主表为数据快照；人员为已收录任职记录，不代表全部员工或实时在职状态。')

import json
import gzip
import os
import secrets
import sqlite3
from datetime import date
from contextlib import closing
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from evidence_engine import new_game,apply,public_state,RuleError

ROOT=Path(__file__).resolve().parent
RUNTIME=ROOT/'runtime';RUNTIME.mkdir(exist_ok=True)
if not (RUNTIME/'universe-v3.json').exists():
    from build_forward import build_forward
    build_forward()
UNIVERSE = json.loads((RUNTIME / 'universe-v3.json').read_text(encoding='utf-8'))
COMPANY_META={item['id']:dict(id=item['id'],name=item.get('name') or item['id'],
    industry=item.get('industry') or '未披露',region=item.get('region') or '未披露')
    for item in UNIVERSE['companies']}
for item in UNIVERSE['rounds']:
    if item['company'] in COMPANY_META:
        COMPANY_META[item['company']].update(name=item.get('name') or item['company'],
            industry=item.get('industry') or '未披露',region=item.get('region') or '未披露')
from institutions import build_index, candidates, pool
INSTITUTIONS=build_index(UNIVERSE)
from knowledge_graph import KnowledgeGraph
from model_forecast import ModelForecast, ModelInferenceError, ModelProcessError
from forecast_catalog import ForecastCatalog
from financial_projection import FinancialProjection
from profiles import profile
KNOWLEDGE_GRAPH=KnowledgeGraph(UNIVERSE,INSTITUTIONS,profile_loader=profile)
MODEL_FORECAST=ModelForecast(
    ROOT.parent/'scripts/live_model_worker.py',UNIVERSE['companies'],UNIVERSE['start'])
MODEL_FORECAST.warm()
FORECAST_CATALOG=ForecastCatalog(
    RUNTIME/f'investor-forecast-catalog-{UNIVERSE["start"]}.json',UNIVERSE['start'])
FINANCIAL_PROJECTION=FinancialProjection(UNIVERSE)
from collections import defaultdict
from statistics import median
# One latest disclosed observation per peer company, same industry/stage/currency.
LATEST={r['company']:r for r in UNIVERSE['rounds'] if r['available']<=UNIVERSE['start']}
PEERS=defaultdict(list)
for r in LATEST.values():
    if r['industry'] not in ('','未披露',None) and r['amount'] and not r['conflict'] and r['currency'] in ('CNY','USD'):
        PEERS[(r['industry'],r['stage'],r['currency'])].append((r['company'],r['amount']))
DB=RUNTIME/'saves.sqlite3'
with closing(sqlite3.connect(DB)) as c, c:c.execute('CREATE TABLE IF NOT EXISTS saves (id TEXT PRIMARY KEY, state TEXT NOT NULL)')

def forecast_error(error, scenario=False):
    """Return a useful public status without exposing internal paths or data."""
    if isinstance(error, TimeoutError):
        return ('生成时间超过限制，系统自动重试后仍未完成。请稍后重新生成。'
                if scenario else '预测时间超过限制，请稍后重试。')
    if isinstance(error, ModelProcessError):
        return ('模型服务已经自动重启，本次路径尚未生成，请再次点击重新生成。'
                if scenario else '模型服务已经自动重启，请重新预测。')
    if isinstance(error, ModelInferenceError):
        return ('融资方案已保存，但模型未能完成本次路径计算，请调整方案或稍后重试。'
                if scenario else '模型未能完成本次预测，请稍后重试。')
    return ('模型结果未通过完整性检查，请重新生成。'
            if scenario else '模型结果未通过完整性检查，请重新预测。')

def action_state(state):
    """Return changed account data without resending the immutable company universe."""
    result=public_state(state,UNIVERSE)
    result.pop('companies',None);result.pop('market',None)
    result['static_state_omitted']=True
    return result

class Handler(BaseHTTPRequestHandler):
    def respond(self,status,data,cookie=None):
        raw=json.dumps(data,ensure_ascii=False).encode()
        compressed='gzip' in self.headers.get('Accept-Encoding','') and len(raw)>1024
        body=gzip.compress(raw,compresslevel=5) if compressed else raw
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
        if compressed:self.send_header('Content-Encoding','gzip')
        self.send_header('Vary','Accept-Encoding')
        if cookie:self.send_header('Set-Cookie',f'market_save={cookie}; HttpOnly; SameSite=Strict; Path=/; Max-Age=31536000')
        self.end_headers();self.wfile.write(body)

    def session(self):
        cookie=SimpleCookie();cookie.load(self.headers.get('Cookie',''))
        value=cookie.get('market_save');return value.value if value else None

    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/api/model-forecast':
            with closing(sqlite3.connect(DB)) as c, c:row=c.execute('SELECT state FROM saves WHERE id=?',(self.session(),)).fetchone()
            if not row:return self.respond(401,{'error':'请先建立账户'})
            state=json.loads(row[0])
            if state.get('version')!=3:return self.respond(400,{'error':'请建立新版账户'})
            company=parse_qs(urlparse(self.path).query).get('id',[''])[0]
            if not company or len(company)>200:return self.respond(400,{'error':'企业标识无效'})
            try:
                result=FORECAST_CATALOG.get(company)
                if result is None or 'history_years' not in result:
                    result=MODEL_FORECAST.get(company)
                    FORECAST_CATALOG.record(result)
                result=dict(result)
                result['financial_projection']=FINANCIAL_PROJECTION.project(company,result,state['currency'])
                return self.respond(200,result)
            except KeyError:return self.respond(404,{'error':'企业不存在'})
            except (RuntimeError,TimeoutError,ValueError) as error:
                import traceback
                traceback.print_exc()
                return self.respond(503,{'error':forecast_error(error)})
        if path=='/api/financing-scenario-forecast':
            with closing(sqlite3.connect(DB)) as c, c:row=c.execute('SELECT state FROM saves WHERE id=?',(self.session(),)).fetchone()
            if not row:return self.respond(401,{'error':'请先建立账户'})
            state=json.loads(row[0])
            if state.get('version')!=3:return self.respond(400,{'error':'请建立新版账户'})
            company=parse_qs(urlparse(self.path).query).get('id',[''])[0]
            if not company or len(company)>200:return self.respond(400,{'error':'企业标识无效'})
            from financing_scenario import build
            scenario=build(state,company,INSTITUTIONS)
            if not scenario['ready']:
                return self.respond(200,scenario)
            try:
                baseline=FORECAST_CATALOG.get(company)
                if baseline is None:
                    baseline=MODEL_FORECAST.get(company)
                    FORECAST_CATALOG.record(baseline)
                updated=MODEL_FORECAST.get_scenario(company,scenario['events'],scenario['as_of'])
                return self.respond(200,{**scenario,'baseline':baseline,'forecast':updated})
            except KeyError:return self.respond(404,{'error':'企业不存在'})
            except (RuntimeError,TimeoutError,ValueError) as error:
                import traceback
                traceback.print_exc()
                return self.respond(503,{'error':forecast_error(error,scenario=True)})
        if path=='/api/custom-event-types':
            with closing(sqlite3.connect(DB)) as c, c:row=c.execute('SELECT state FROM saves WHERE id=?',(self.session(),)).fetchone()
            if not row:return self.respond(401,{'error':'请先建立账户'})
            from custom_path import taxonomy
            return self.respond(200,{'categories':taxonomy()})
        if path=='/api/custom-forecast':
            with closing(sqlite3.connect(DB)) as c, c:row=c.execute('SELECT state FROM saves WHERE id=?',(self.session(),)).fetchone()
            if not row:return self.respond(401,{'error':'请先建立账户'})
            state=json.loads(row[0]);custom=state.get('founder_custom',{})
            events=custom.get('events',[])
            if not custom.get('profile',{}).get('name'):return self.respond(400,{'error':'请先保存企业名称'})
            if not events:return self.respond(400,{'error':'请先添加至少一个历史节点'})
            try:
                result=MODEL_FORECAST.get_custom(events,date.today().isoformat())
                industry=custom.get('profile',{}).get('industry','').strip()
                evidence_factor=min(1.0,len(events)/4)
                joined=[]
                for match in result.pop('similar',[]):
                    meta=COMPANY_META.get(match['company'])
                    if not meta:continue
                    same=bool(industry and industry!='未披露' and meta['industry']==industry)
                    display=match['similarity']*(.55+.45*evidence_factor)+(.03 if same else 0)
                    joined.append({**match,**meta,'same_industry':same,
                                   'display_similarity':round(min(.99,display),4)})
                joined.sort(key=lambda item:(-item['display_similarity'],item['name']))
                result['similar']=joined[:8]
                result['profile']=custom['profile']
                result['reference_cutoff']=UNIVERSE['start']
                return self.respond(200,result)
            except (RuntimeError,TimeoutError,ValueError):
                import traceback
                traceback.print_exc()
                return self.respond(503,{'error':'模型暂时无法完成自建路径预测，请稍后重试'})
        if path=='/api/tracked-companies':
            with closing(sqlite3.connect(DB)) as c, c:row=c.execute('SELECT state FROM saves WHERE id=?',(self.session(),)).fetchone()
            if not row:return self.respond(401,{'error':'请先建立账户'})
            state=json.loads(row[0])
            if state.get('version')!=3:return self.respond(400,{'error':'请建立新版账户'})
            watched=state.get('forecast_watchlist',{})
            followups=state.get('forecast_followups',{})
            positions=state.get('positions',{})
            ids=set(watched)|set(followups)|set(positions)
            items=[]
            for cid in ids:
                meta=COMPANY_META.get(cid)
                if not meta:continue
                items.append({**meta,'watched':cid in watched,'invested':bool(positions.get(cid)),
                              'followups':list(followups.get(cid,{}).values())})
            items.sort(key=lambda item:(not item['watched'],not item['invested'],item['name']))
            return self.respond(200,{'items':items})
        if path=='/api/forecast-opportunities':
            with closing(sqlite3.connect(DB)) as c, c:row=c.execute('SELECT state FROM saves WHERE id=?',(self.session(),)).fetchone()
            if not row:return self.respond(401,{'error':'请先建立账户'})
            state=json.loads(row[0])
            if state.get('version')!=3:return self.respond(400,{'error':'请建立新版账户'})
            query=parse_qs(urlparse(self.path).query)
            try:
                event=query.get('event',['融资'])[0]
                months=int(query.get('months',['12'])[0])
                page=int(query.get('page',['1'])[0])
                watched=query.get('watched',['0'])[0]=='1'
                companies=public_state(state,UNIVERSE)['companies']
                result=FORECAST_CATALOG.query(
                    companies,state.get('forecast_watchlist',{}),event,months,
                    query.get('q',[''])[0],watched,page,current_month=state.get('month',0))
                result['watchlist_count']=len(state.get('forecast_watchlist',{}))
                return self.respond(200,result)
            except ValueError as e:return self.respond(400,{'error':str(e)})
        if path=='/api/knowledge-graph':
            with closing(sqlite3.connect(DB)) as c, c:row=c.execute('SELECT state FROM saves WHERE id=?',(self.session(),)).fetchone()
            if not row:return self.respond(401,{'error':'请先建立账户'})
            if json.loads(row[0]).get('version')!=3:return self.respond(400,{'error':'请建立新版账户'})
            query=parse_qs(urlparse(self.path).query)
            entity_type=query.get('entity_type',[''])[0]
            entity_id=query.get('entity_id',[''])[0]
            if not entity_id or len(entity_id)>200:return self.respond(400,{'error':'实体标识无效'})
            try:return self.respond(200,KNOWLEDGE_GRAPH.graph(entity_type,entity_id))
            except ConnectionError:return  # A closed dialog aborts its read-only request.
            except ValueError as e:return self.respond(400,{'error':str(e)})
            except KeyError:return self.respond(404,{'error':'未找到该企业或投资人的历史资料'})
            except Exception:
                import traceback
                traceback.print_exc()
                return self.respond(500,{'error':'图谱读取失败，请稍后重试'})
        if path=='/api/company-profile':
            with closing(sqlite3.connect(DB)) as c, c:row=c.execute('SELECT state FROM saves WHERE id=?',(self.session(),)).fetchone()
            if not row:return self.respond(401,{'error':'请先建立账户'})
            cid=parse_qs(urlparse(self.path).query).get('id',[''])[0]
            if not any(c['id']==cid for c in UNIVERSE['companies']):return self.respond(404,{'error':'企业不存在'})
            from profiles import profile
            return self.respond(200,profile(cid,UNIVERSE['start']))
        if path=='/api/institution':
            with closing(sqlite3.connect(DB)) as c, c:row=c.execute('SELECT state FROM saves WHERE id=?',(self.session(),)).fetchone()
            if not row:return self.respond(401,{'error':'请先建立账户'})
            query=parse_qs(urlparse(self.path).query);inst=INSTITUTIONS.get(query.get('id',[''])[0])
            if not inst:return self.respond(404,{'error':'投资人不存在'})
            try:page=max(1,int(query.get('page',['1'])[0]))
            except ValueError:return self.respond(400,{'error':'页码无效'})
            history=sorted((r for r in inst['rounds'] if r['available']<=UNIVERSE['start']),key=lambda r:(r['date'],r['id']),reverse=True)
            pages=max(1,(len(history)+11)//12);page=min(page,pages)
            items=[dict(company=r['name'],stage=r['stage'],event_date=r['date'],industry=r.get('industry'),amount=r.get('amount'),currency=r.get('currency')) for r in history[(page-1)*12:page*12]]
            return self.respond(200,dict(id=inst['id'],name=inst['name'],cutoff=UNIVERSE['start'],total=len(history),company_count=len({r['company'] for r in history}),page=page,pages=pages,items=items))
        if path=='/api/institutions':
            with closing(sqlite3.connect(DB)) as c, c:row=c.execute('SELECT state FROM saves WHERE id=?',(self.session(),)).fetchone()
            if not row:return self.respond(401,{'error':'请先建立账户'})
            query=parse_qs(urlparse(self.path).query)
            cid=query.get('company',[''])[0]
            if not any(c['id']==cid for c in UNIVERSE['companies']):return self.respond(404,{'error':'企业不存在'})
            try:
                result=pool(INSTITUTIONS,cid,LATEST.get(cid,{}),UNIVERSE['start'],query.get('q',[''])[0][:200],query.get('scope',['all'])[0],query.get('sort',['match'])[0],int(query.get('page',['1'])[0]))
                return self.respond(200,result)
            except ValueError as e:return self.respond(400,{'error':str(e)})
        if path=='/api/company':
            with closing(sqlite3.connect(DB)) as c, c:row=c.execute('SELECT state FROM saves WHERE id=?',(self.session(),)).fetchone()
            if not row:return self.respond(401,{'error':'请先建立账户'})
            state=json.loads(row[0])
            if state.get('version')!=3:return self.respond(400,{'error':'请建立新版账户'})
            cid=parse_qs(urlparse(self.path).query).get('id',[''])[0]
            base=next((c for c in UNIVERSE['companies'] if c['id']==cid),None)
            if not base:return self.respond(404,{'error':'企业不存在'})
            subset=dict(UNIVERSE,companies=[base])
            detail=public_state(state,subset,compact=False)['companies'][0]
            detail['details_loaded']=True
            detail['institutions']=candidates(INSTITUTIONS,cid,detail['latest'],UNIVERSE['start'])
            r=detail['latest'];reference=detail['terms']['reference']
            currency=reference['currency'] if reference else state['currency']
            amounts=[amount for peer,amount in PEERS.get((r['industry'],r['stage'],currency),[]) if peer!=cid]
            detail['comparison']=dict(n=len(amounts),currency=currency,median_amount=median(amounts) if len(amounts)>=5 else None)
            return self.respond(200,{'company':detail})
        if path=='/api/legacy-export':
            with closing(sqlite3.connect(DB)) as c, c:row=c.execute('SELECT state FROM saves WHERE id=?',(self.session(),)).fetchone()
            state=json.loads(row[0]) if row else None
            if not state:return self.respond(404,{'error':'当前没有记录'})
            return self.respond(200,state)
        if path=='/api/game':
            with closing(sqlite3.connect(DB)) as c, c:row=c.execute('SELECT state FROM saves WHERE id=?',(self.session(),)).fetchone()
            state=json.loads(row[0]) if row else None
            legacy=bool(state and state.get('version')!=3)
            return self.respond(200,dict(game=public_state(state,UNIVERSE) if state and not legacy else None,
                legacy=legacy,meta=UNIVERSE['meta']))
        files={'/':('index.html','text/html'),'/app.js':('app.js','text/javascript'),'/trading.js':('trading.js','text/javascript'),'/evidence.js':('evidence.js','text/javascript'),'/styles.css':('styles.css','text/css')}
        files['/charts.js']=('charts.js','text/javascript')
        files['/knowledge-graph.js']=('knowledge-graph.js','text/javascript')
        files['/knowledge-graph.css']=('knowledge-graph.css','text/css')
        files['/timeline.css']=('timeline.css','text/css')
        files['/forecast-ui.js']=('forecast-ui.js','text/javascript')
        files.update({'/founder':('founder.html','text/html'),'/founder.js':('founder.js','text/javascript'),'/founder.css':('founder.css','text/css')})
        if path not in files:return self.respond(404,{'error':'Not found'})
        file,mime=files[path];raw=(ROOT/'web'/file).read_bytes()
        self.send_response(200);self.send_header('Content-Type',mime+'; charset=utf-8')
        self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-cache')
        self.end_headers();self.wfile.write(raw)

    def do_POST(self):
        if self.headers.get('Origin') and urlparse(self.headers['Origin']).netloc!=self.headers.get('Host'):
            return self.respond(403,{'error':'来源不匹配'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size<=0 or size>8192:raise RuleError('请求大小无效')
            data=json.loads(self.rfile.read(size))
            if not isinstance(data,dict):raise RuleError('请求格式无效')
            path=urlparse(self.path).path
            if path=='/api/new':
                name=data.get('name','远航资本')
                if not isinstance(name,str):raise RuleError('账户名称无效')
                sid=secrets.token_urlsafe(32);state=new_game(UNIVERSE,name.strip() or '远航资本',
                    data.get('currency','CNY'),data.get('initial',100000000),data.get('fee_rate',0))
                with closing(sqlite3.connect(DB)) as c, c:c.execute('INSERT INTO saves VALUES (?,?)',(sid,json.dumps(state)))
                return self.respond(200,{'game':public_state(state,UNIVERSE)},sid)
            if path!='/api/action':return self.respond(404,{'error':'Not found'})
            offer_forecast=None
            if data.get('type')=='offer':
                company=data.get('company')
                if isinstance(company,str):
                    try:
                        offer_forecast=FORECAST_CATALOG.get(company)
                        if offer_forecast is None or 'history_years' not in offer_forecast:
                            offer_forecast=MODEL_FORECAST.get(company)
                            FORECAST_CATALOG.record(offer_forecast)
                    except (KeyError,RuntimeError,TimeoutError,ValueError):
                        offer_forecast=None
            with closing(sqlite3.connect(DB,timeout=10)) as c, c:
                c.execute('BEGIN IMMEDIATE')
                row=c.execute('SELECT state FROM saves WHERE id=?',(self.session(),)).fetchone()
                if not row:return self.respond(404,{'error':'请先创建基金'})
                state=json.loads(row[0])
                if state.get('version')!=3:raise RuleError('旧账户已归档，请建立前向模拟账户')
                if data.get('revision')!=state['revision']:
                    return self.respond(409,{'error':'存档已更新，请刷新后操作','game':action_state(state)})
                if isinstance(data.get('type'),str) and data['type'].startswith('financing_'):
                    from financing import transact
                    state=transact(state,data,UNIVERSE,INSTITUTIONS)
                elif data.get('type')=='founder_contact':
                    from founder import save_contact
                    state=save_contact(state,data,UNIVERSE,INSTITUTIONS)
                elif data.get('type')=='founder_contact_remove':
                    from founder import remove_contact
                    state=remove_contact(state,data,UNIVERSE,INSTITUTIONS)
                elif data.get('type') in ('forecast_plan','forecast_watch','forecast_followup','founder_custom_profile','founder_custom_event_add','founder_custom_event_delete','founder_custom_mode','founder_custom_finance_plan'):
                    from forecast_workflow import transact
                    state=transact(state,data,UNIVERSE)
                else:
                    projection=(FINANCIAL_PROJECTION.project(data.get('company'),offer_forecast,state['currency'])
                                if offer_forecast is not None else None)
                    state=apply(state,data,UNIVERSE,projection=projection)
                c.execute('UPDATE saves SET state=? WHERE id=?',(json.dumps(state),self.session()))
            return self.respond(200,{'game':action_state(state)})
        except (RuleError,ValueError,TypeError) as e:self.respond(400,{'error':str(e)})
        except Exception:
            import traceback
            traceback.print_exc();self.respond(500,{'error':'结算失败，存档未提交。请重试。'})

if __name__=='__main__':
    port=int(os.environ.get('MARKET_PORT','8790'))
    print(f'Market simulator: http://127.0.0.1:{port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()

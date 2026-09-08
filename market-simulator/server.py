import json
import os
import secrets
import sqlite3
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
UNIVERSE=json.loads((RUNTIME/'universe-v3.json').read_text())
from institutions import build_index, candidates, pool
INSTITUTIONS=build_index(UNIVERSE)
from collections import defaultdict
from statistics import median
# One latest disclosed observation per peer company, same industry/stage/currency.
LATEST={r['company']:r for r in UNIVERSE['rounds'] if r['available']<=UNIVERSE['start']}
PEERS=defaultdict(list)
for r in LATEST.values():
    if r['industry'] not in ('','未披露',None) and r['amount'] and not r['conflict'] and r['currency'] in ('CNY','USD'):
        PEERS[(r['industry'],r['stage'],r['currency'])].append((r['company'],r['amount']))
DB=RUNTIME/'saves.sqlite3'
with sqlite3.connect(DB) as c:c.execute('CREATE TABLE IF NOT EXISTS saves (id TEXT PRIMARY KEY, state TEXT NOT NULL)')

class Handler(BaseHTTPRequestHandler):
    def respond(self,status,data,cookie=None):
        raw=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store')
        if cookie:self.send_header('Set-Cookie',f'market_save={cookie}; HttpOnly; SameSite=Strict; Path=/; Max-Age=31536000')
        self.end_headers();self.wfile.write(raw)

    def session(self):
        cookie=SimpleCookie();cookie.load(self.headers.get('Cookie',''))
        value=cookie.get('market_save');return value.value if value else None

    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/api/company-profile':
            with sqlite3.connect(DB) as c:row=c.execute('SELECT state FROM saves WHERE id=?',(self.session(),)).fetchone()
            if not row:return self.respond(401,{'error':'请先建立账户'})
            cid=parse_qs(urlparse(self.path).query).get('id',[''])[0]
            if not any(c['id']==cid for c in UNIVERSE['companies']):return self.respond(404,{'error':'企业不存在'})
            from profiles import profile
            return self.respond(200,profile(cid,UNIVERSE['start']))
        if path=='/api/institution':
            with sqlite3.connect(DB) as c:row=c.execute('SELECT state FROM saves WHERE id=?',(self.session(),)).fetchone()
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
            with sqlite3.connect(DB) as c:row=c.execute('SELECT state FROM saves WHERE id=?',(self.session(),)).fetchone()
            if not row:return self.respond(401,{'error':'请先建立账户'})
            query=parse_qs(urlparse(self.path).query)
            cid=query.get('company',[''])[0]
            if not any(c['id']==cid for c in UNIVERSE['companies']):return self.respond(404,{'error':'企业不存在'})
            try:
                result=pool(INSTITUTIONS,cid,LATEST.get(cid,{}),UNIVERSE['start'],query.get('q',[''])[0][:200],query.get('scope',['all'])[0],query.get('sort',['match'])[0],int(query.get('page',['1'])[0]))
                return self.respond(200,result)
            except ValueError as e:return self.respond(400,{'error':str(e)})
        if path=='/api/company':
            with sqlite3.connect(DB) as c:row=c.execute('SELECT state FROM saves WHERE id=?',(self.session(),)).fetchone()
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
            with sqlite3.connect(DB) as c:row=c.execute('SELECT state FROM saves WHERE id=?',(self.session(),)).fetchone()
            state=json.loads(row[0]) if row else None
            if not state:return self.respond(404,{'error':'当前没有记录'})
            return self.respond(200,state)
        if path=='/api/game':
            with sqlite3.connect(DB) as c:row=c.execute('SELECT state FROM saves WHERE id=?',(self.session(),)).fetchone()
            state=json.loads(row[0]) if row else None
            legacy=bool(state and state.get('version')!=3)
            return self.respond(200,dict(game=public_state(state,UNIVERSE) if state and not legacy else None,
                legacy=legacy,meta=UNIVERSE['meta']))
        files={'/':('index.html','text/html'),'/app.js':('app.js','text/javascript'),'/trading.js':('trading.js','text/javascript'),'/evidence.js':('evidence.js','text/javascript'),'/styles.css':('styles.css','text/css')}
        files['/charts.js']=('charts.js','text/javascript')
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
                with sqlite3.connect(DB) as c:c.execute('INSERT INTO saves VALUES (?,?)',(sid,json.dumps(state)))
                return self.respond(200,{'game':public_state(state,UNIVERSE)},sid)
            if path!='/api/action':return self.respond(404,{'error':'Not found'})
            with sqlite3.connect(DB,timeout=10) as c:
                c.execute('BEGIN IMMEDIATE')
                row=c.execute('SELECT state FROM saves WHERE id=?',(self.session(),)).fetchone()
                if not row:return self.respond(404,{'error':'请先创建基金'})
                state=json.loads(row[0])
                if state.get('version')!=3:raise RuleError('旧账户已归档，请建立前向模拟账户')
                if data.get('revision')!=state['revision']:
                    return self.respond(409,{'error':'存档已更新，请刷新后操作','game':public_state(state,UNIVERSE)})
                if isinstance(data.get('type'),str) and data['type'].startswith('financing_'):
                    from financing import transact
                    state=transact(state,data,UNIVERSE,INSTITUTIONS)
                elif data.get('type')=='founder_contact':
                    from founder import save_contact
                    state=save_contact(state,data,UNIVERSE,INSTITUTIONS)
                else:state=apply(state,data,UNIVERSE)
                c.execute('UPDATE saves SET state=? WHERE id=?',(json.dumps(state),self.session()))
            return self.respond(200,{'game':public_state(state,UNIVERSE)})
        except (RuleError,ValueError,TypeError) as e:self.respond(400,{'error':str(e)})
        except Exception:
            import traceback
            traceback.print_exc();self.respond(500,{'error':'结算失败，存档未提交。请重试。'})

if __name__=='__main__':
    port=int(os.environ.get('MARKET_PORT','8790'))
    print(f'Market simulator: http://127.0.0.1:{port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()

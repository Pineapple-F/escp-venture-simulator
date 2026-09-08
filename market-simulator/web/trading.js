'use strict';
filter='all';
$('.intro').textContent='基于截至2026年3月的历史资料，向未来模拟投资。';
$('.start-brief').innerHTML='<h2>真实资料，独立模拟</h2><p>融资记录来自数据；报价、成交和股权单独模拟。</p>';
$('.landing-stats').innerHTML='<div><b>含无融资记录企业</b><span>不将缺失记录视为未融资</span></div><div><b>2026—2029</b><span>前向模拟</span></div>';
$('#legacyNotice').innerHTML='旧版账户已保留。<a href="/api/legacy-export" download="historical-account.json">下载旧记录</a>，或新建前向模拟账户。';
$('#newForm>.tour-note').textContent='独立币种账户；未来走势为情景模拟，不是真实预测。';
$('.timeline>span:first-child').textContent='2026-03';$('.timeline>b').textContent='2029-03';
$('#regime').textContent='模拟日期';
$('#endBanner').textContent='三年模拟结束，可查看持仓并导出账户。';
$('[data-filter=current]').textContent='有融资记录';
document.title='长线 · 创投市场模拟';
$('.performance p').textContent='模拟估值不是现金；未退出收益计入浮盈亏。';
$('.account div:nth-child(1)>span').textContent='模拟总资产';
$('.account div:nth-child(3)>span').textContent='模拟持仓价值';
$('.account div:nth-child(4)>span').textContent='浮动盈亏';
$('#marketView thead').innerHTML='<tr><th>企业 / 行业</th><th>融资阶段</th><th>历史融资</th><th>风险记录</th><th></th></tr>';
$('.market-pulse').hidden=true;
$('.table-note').textContent='只展示当前已知资料；报价及持仓价值为模拟值。';
$('.inbox header h2').textContent='持仓动态';
$('.inbox-guide').hidden=true;
const originalNewForm=$('#newForm').onsubmit;
$('#newForm').onsubmit=async function(e){await originalNewForm(e);filter='all';if(game)render()};
const originalRender=render;
render=function(){
  originalRender();if(!game)return;
  $('#advance').textContent=game.ended?'模拟期结束':'推进一个月 →';
  $('#observationRange').textContent='历史截止 '+game.meta.cutoff+' · 模拟至 '+game.as_of;
  const point=game.curve.at(-1);
  $('#nav').textContent=money(point.sim_assets??point.net_assets);
  $('#cost').textContent=money(point.sim_value??point.cost);
  $('#fees').textContent=money(point.unrealized??0);
  const alerts=game.notifications||[];
  $('#taskCount').textContent=alerts.length;
  $('#tasks').innerHTML=alerts.map(n=>'<button class="task" data-company="'+n.company+'"><strong>'+esc(companyName(game.companies.find(c=>c.id===n.company)))+'</strong><p>'+esc(n.reason)+'</p><b>'+money(n.delta)+' · 模拟变动</b><small>'+n.date+'</small></button>').join('')||'<p>暂无持仓变动</p>';
  $('#coverage').innerHTML='<p>'+game.companies.length.toLocaleString()+' 家企业 · 历史截止 '+game.meta.cutoff+'</p><p>此后为模拟，不再读取未来历史。</p>';
};
function companyName(c){return !c?'企业':c.name.startsWith('co_')?'匿名企业 · '+c.id.slice(-6):c.name}
function industryLabel(c){const v=String(c.industry||'').trim();return !v||v==='未披露'?'行业未披露':v}
function riskLabel(c){return c.risks.at(-1)?.type==='abnormal_listing'?'存在异常记录':c.risks.length?'异常已移出':'未收录异常'}
const stageGroups=['种子 / 天使','A轮（含Pre-A、A+）','B轮（含Pre-B、B+）','C轮及以后','上市相关','其他 / 未披露','暂无融资记录'];
function stageGroup(stage){
  const s=String(stage||'').toUpperCase().replace(/\s/g,'');
  if(s==='暂无融资记录')return stageGroups[6];
  if(/种子|天使/.test(s))return stageGroups[0];
  if(/^(PRE-?)?A[+\d]*轮?$/.test(s))return stageGroups[1];
  if(/^(PRE-?)?B[+\d]*轮?$/.test(s))return stageGroups[2];
  if(/IPO|上市|新三板/.test(s))return stageGroups[4];
  if(/^[C-G][+\d]*轮|后期/.test(s))return stageGroups[3];
  return stageGroups[5];
}
function riskBadge(c){
  if(!c.risks.length)return '<span class="badge risk-none">未收录异常</span>';
  return '<button class="badge '+(riskLabel(c)==='存在异常记录'?'risk-active':'risk-resolved')+'" data-risk-company="'+c.id+'">'+(riskLabel(c)==='存在异常记录'?'经营异常':'异常已移出')+' ↗</button>';
}
renderMarket=function(){
  const q=$('#search').value.trim().toLowerCase();
  const select=$('#stageFilter'),selectedStage=select.value;
  const stages=stageGroups;
  select.innerHTML='<option value="">全部融资阶段</option>'+stages.map(s=>'<option value="'+esc(s)+'">'+esc(s)+'</option>').join('');
  select.value=selectedStage;
  const risk=$('#riskFilter').value;
  const industrySelect=$('#industryFilter'),industry=industrySelect.value;
  const industries=[...new Set(game.companies.map(industryLabel))].sort((a,b)=>a==='行业未披露'?1:b==='行业未披露'?-1:a.localeCompare(b,'zh-CN'));
  if(industry&&!industries.includes(industry))industries.push(industry);
  industrySelect.innerHTML='<option value="">全部行业</option>'+industries.map(v=>'<option value="'+esc(v)+'">'+esc(v)+'</option>').join('');
  industrySelect.value=industry;
  const rows=game.companies.filter(c=>(filter==='all'||filter==='current'&&c.history.length||filter==='held'&&(game.positions[c.id]||game.intentions?.[c.id]))&&(!industry||industryLabel(c)===industry)&&(!selectedStage||stageGroup(c.latest.stage)===selectedStage)&&(!risk||riskLabel(c)===risk)&&(c.name+' '+c.region+' '+c.industry).toLowerCase().includes(q));
  const complete=c=>Number(!c.name.startsWith('co_'))+Number(c.industry&&c.industry!=='未披露');
  rows.sort((a,b)=>complete(b)-complete(a)||b.latest.available.localeCompare(a.latest.available)||a.id.localeCompare(b.id));
  const pages=Math.max(1,Math.ceil(rows.length/PAGE_SIZE));pageIndex=Math.min(pageIndex,pages-1);
  $('#marketCount').textContent=rows.length.toLocaleString()+' 家企业';
  document.querySelectorAll('[data-filter]').forEach(b=>b.classList.toggle('active',b.dataset.filter===filter));
  $('#marketRows').innerHTML=rows.slice(pageIndex*PAGE_SIZE,(pageIndex+1)*PAGE_SIZE).map(c=>'<tr><td><button class="company-link" data-company="'+c.id+'"><strong>'+esc(companyName(c))+'</strong></button><small>'+esc(c.industry&&c.industry!=='未披露'?c.industry:'行业未披露')+'</small></td><td>'+esc(c.latest.stage)+'</td><td>'+c.history.length+' 次<small>最近 '+c.latest.available.slice(0,7)+' · '+short(c.latest.amount,c.latest.currency)+'</small></td><td>'+riskBadge(c)+'</td><td><button class="primary" data-company="'+c.id+'" '+(game.ended?'disabled':'')+'>'+(game.positions[c.id]?'查看持仓':'投资报价')+'</button></td></tr>').join('')||'<tr><td colspan="5">没有匹配企业</td></tr>';
  $('#pageLabel').textContent=(pageIndex+1)+' / '+pages+' 页';$('#prevPage').disabled=pageIndex===0;$('#nextPage').disabled=pageIndex>=pages-1;
};
document.addEventListener('click',e=>{
  const b=e.target.closest('[data-risk-company]');if(!b||busy)return;
  const c=game.companies.find(c=>c.id===b.dataset.riskCompany);if(!c)return;
  $('#riskBody').innerHTML='<h2>'+esc(companyName(c))+'</h2><p>'+riskLabel(c)+'</p>'+[...c.risks].reverse().map(r=>'<article class="disclosure"><b>'+esc(r.date)+' · '+(r.type==='abnormal_listing'?'列入经营异常名录':'移出经营异常名录')+'</b></article>').join('')+'<p>当前资料仅含异常名录变动，未提供具体事由；不等同于破产。</p>';
  $('#riskDialog').showModal();
});
showCompany=function(id,show=true){
  const c=game.companies.find(c=>c.id===id);if(!c)return;selected=id;
  const t=c.terms,p=game.positions[id];
  $('#companyBody').innerHTML='<button class="close" data-close aria-label="关闭">×</button><h2>'+esc(c.name)+'</h2><p>'+esc(c.latest.stage)+' · '+c.latest.available+'</p>'+
    '<form class="deal" id="offerForm"><h3>投资 <small>模拟交易</small></h3><p>融资目标 '+money(t.target)+' · 最低参与 '+money(t.minimum)+'</p><label>投资金额<input id="offerAmount" type="number" min="0.01" step="0.01" required value="'+Math.min(t.target,game.cash,Math.max(t.minimum,1000000))+'"></label><p>模拟投前估值 '+money(t.pre_money)+' · '+esc(t.basis)+'</p><div id="offerPreview" class="quote" aria-live="polite"></div><button class="primary" type="submit" '+(game.ended?'disabled':'')+'>确认投资</button></form>'+
    (p?'<div class="detail-section"><h3>持仓</h3><p>成本 '+money(p.cost)+(p.scenario?' · 模拟持股 '+(p.ownership*100).toFixed(2)+'%':' · 旧版认购记录')+'</p></div>':'')+
    '<details class="detail-section"><summary>历史融资记录 · '+c.history.length+' 条</summary>'+[...c.history].reverse().map(roundFacts).join('')+'</details>';
  offerPreview();if(show&&!$('#companyDialog').open)$('#companyDialog').showModal();
};
function offerPreview(){
  if(!$('#offerForm'))return;
  const a=Number($('#offerAmount').value),c=game.companies.find(c=>c.id===selected),v=c.terms.pre_money,p=game.positions[selected];
  const valid=Number.isFinite(a)&&Number.isFinite(v)&&a>0&&v>0&&a<=game.cash&&v<=1e12;
  const accepted=valid&&a>=c.terms.minimum&&a<=c.terms.target&&v>=c.terms.pre_money;
  $('#offerPreview').textContent=accepted?'成交后现金 '+money(game.cash-a)+' · 模拟持股 '+(((p?.scenario?p.ownership:0)*v+a)/(v+a)*100).toFixed(2)+'%':a>game.cash?'可用现金不足':'投资金额须在 '+money(c.terms.minimum)+' 至 '+money(c.terms.target)+' 之间';
  $('#offerForm button').disabled=!accepted||busy||game.ended||!!game.fees_payable||p?.last_deal===game.as_of;
  if(p?.last_deal===game.as_of)$('#offerPreview').textContent='本月已成交，可下月追加投资';
  if(c.closed){$('#offerPreview').textContent='有注销或吊销记录，暂不接受投资';$('#offerForm button').disabled=true}
}
document.addEventListener('input',e=>{if(e.target.id==='offerAmount')offerPreview()});
document.addEventListener('submit',async e=>{
  if(e.target.id!=='offerForm')return;e.preventDefault();if(busy)return;
  const body={type:'offer',company:selected,amount:Number($('#offerAmount').value),revision:game.revision};
  busy=true;offerPreview();
  try{const result=await api('/api/action',body);game=result.game;toast(game.log.at(-1).text);render();await showCompany(selected,false)}catch(err){toast(err.message)}finally{busy=false;render();offerPreview()}
});
renderPortfolio=function(){
  $('#chart').innerHTML='';
  $('#positions').innerHTML=game.companies.filter(c=>game.positions[c.id]).map(c=>{const p=game.positions[c.id];return '<article class="position"><div><button class="company-link" data-company="'+c.id+'"><h3>'+esc(c.name)+'</h3></button><p>'+p.lots.length+' 笔投资'+(p.scenario?' · 模拟持股 '+(p.ownership*100).toFixed(2)+'%':' · 旧版记录')+'</p>'+(p.scenario?'<p>企业累计获得模拟资金 '+money(p.company_cash)+'</p>':'')+'</div><div><span class="money">'+money(p.cost)+'</span><p>投入成本</p></div></article>'}).join('')||'<div class="empty">暂无持仓，去融资市场选择企业。</div>';
};
requestAdvance=function(){
  if(busy||game.ended)return;
  $('#advanceBody').innerHTML='<h2 id="advanceTitle">推进一个月</h2><p>运行下月情景，更新模拟持仓；管理费 '+money(game.initial*game.fee_rate/12)+'。</p><div class="preview-actions"><button data-close>取消</button><button class="primary" data-confirm-month>确认推进</button></div>';
  $('#advanceDialog').showModal();
};
$('#advance').onclick=requestAdvance;
rules=function(){
  $('#rulesBody').innerHTML='<p>企业按当时可见融资记录开放，不使用未来资料。</p><p>报价为独立情景：融资目标参考最近同币种明确融资额；缺失时人民币默认500万元、美元默认100万元。参考投前估值为目标的4倍，最低投资为目标的1%。这不是训练模型或真实企业报价。</p><p>报价满足参考估值和金额范围即成交，否则拒绝。每家企业每月最多成交一次。追加投资按投前估值计算老股稀释与新股；历史融资不自动改变模拟股权。</p><p>现金、投入成本和模拟股权分开记录。目前未模拟经营现金消耗、外部融资、退出交易或公允价值收益。</p>';
  $('#rulesDialog').showModal();
};
$('#rulesBtn').onclick=rules;
for(const id of ['industryFilter','stageFilter','riskFilter'])$('#'+id).onchange=()=>{pageIndex=0;renderMarket()};
const tradingRules=rules;
rules=function(){tradingRules();$('#rulesBody').innerHTML+='<p>历史截止2026-03-31。2026年4月资料不完整，暂不纳入。企业主表缺少字段可用日期，不能保证严格点时还原；无融资记录不代表初创或从未融资。</p><p>未来市场活动对历史截止前12个月变化率进行可重复的情景抽样，不继续读取历史事件。活动变化率×2%调整模拟持仓，月度限制±3%。系数未经预测校准，不保证盈利，不改变现金与股权。暂未生成企业未来融资、经营和退出事件。</p>'};
$('#rulesBtn').onclick=rules;
renderPortfolio=function(){
  $('#chart').innerHTML='';
  $('#positions').innerHTML=game.companies.filter(c=>game.positions[c.id]).map(c=>{
    const p=game.positions[c.id],value=p.sim_value??p.cost;
    return '<article class="position"><div><button class="company-link" data-company="'+c.id+'"><h3>'+esc(companyName(c))+'</h3></button><p>'+(p.scenario?'模拟持股 '+(p.ownership*100).toFixed(2)+'%':'旧版成本记录')+' · 成本 '+money(p.cost)+'</p><p>本月变动 '+money(p.month_change||0)+'</p></div><div><span class="money">'+money(value)+'</span><p>模拟价值 · 浮盈亏 '+money(value-p.cost)+'</p></div></article>';
  }).join('')||'<div class="empty">暂无持仓，去融资市场选择企业。</div>';
};
showReport=function(previous){
  const alerts=game.notifications||[],delta=(game.curve.at(-1).unrealized||0)-(previous.curve.at(-1).unrealized||0);
  $('#reportBody').innerHTML='<button class="close" data-close aria-label="关闭">×</button><h2>'+game.as_of.slice(0,7)+' 月度结算</h2><div class="detail-stats"><div><span>模拟持仓变动</span><b>'+money(delta)+'</b></div><div><span>现金变动</span><b>'+money(game.cash-previous.cash)+'</b></div></div><div class="report-list">'+(alerts.map(n=>'<p>'+esc(companyName(game.companies.find(c=>c.id===n.company)))+' · '+esc(n.reason)+' <b>'+money(n.delta)+'</b></p>').join('')||'<p>本月持仓无估值调整</p>')+'</div><button class="primary" data-close>查看账户</button>';
  $('#reportDialog').showModal();
};

'use strict';
$('.account div:nth-child(1)>span').textContent='模拟总资产';
$('.account div:nth-child(3)>span').textContent='已投入成本';
$('.account div:nth-child(4)>span').textContent='持仓企业';
if($('.performance p'))$('.performance p').textContent='投资组合与资金变化。';
$('.workspace-note').textContent='选择企业，查看发展路径并记录投资。';
$('.table-note').textContent='历史融资金额与原始币种。';
$('[data-filter=held]').textContent='投资记录';
const evidenceRender=render;
render=function(){
  evidenceRender();if(!game)return;
  const point=game.curve.at(-1);
  $('#nav').textContent=money(point.sim_assets??point.net_assets);$('#cost').textContent=money(point.cost);
  $('#fees').textContent=Object.keys(game.positions).length+' 家';
  const hasAlerts=(game.notifications||[]).length>0;
  $('#tasks').hidden=!hasAlerts;$('.inbox>header:first-child').hidden=!hasAlerts;
};
const evidenceMarket=renderMarket;
renderMarket=function(){evidenceMarket();document.querySelectorAll('#marketRows .primary').forEach(b=>{b.textContent=game.positions[b.dataset.company]?'查看投资':'投资'})};
let detailRequest=0;
$('#companyDialog').addEventListener('close',()=>{detailRequest++});
showCompany=async function(id,show=true){
  const request=++detailRequest;
  let entry=game.companies.find(c=>c.id===id);if(!entry)return;
  if(!entry.details_loaded){
    selected=id;
    $('#companyBody').innerHTML='<button class="close" data-close aria-label="关闭">×</button><p>正在读取企业资料…</p>';
    if(show&&!$('#companyDialog').open)$('#companyDialog').showModal();
    try{
      const result=await api('/api/company?id='+encodeURIComponent(id));
      if(request!==detailRequest)return;
      const index=game.companies.findIndex(c=>c.id===id);if(index<0)return;
      game.companies[index]=result.company;
    }catch(error){if(request===detailRequest)$('#companyBody').innerHTML='<button class="close" data-close aria-label="关闭">×</button><p>'+esc(error.message)+'</p>';return}
  }
  const c=game.companies.find(c=>c.id===id);if(!c)return;selected=id;
  const r=c.terms.reference,p=game.positions[id],intent=game.intentions?.[id];
  $('#companyBody').innerHTML='<button class="close" data-close aria-label="关闭">×</button><h2>'+esc(companyName(c))+'</h2><p>'+esc(c.latest.stage)+'</p>'+
    '<div class="detail-section"><h3>最近融资</h3>'+(r?'<p>'+money(r.amount,r.currency)+' · '+r.date+'</p><p>历史披露'+(r.currency!==game.currency?' · 与账户币种不同':'')+'</p>':'<p>暂无明确金额记录</p>')+'</div>'+
    '<details class="detail-section"><summary>全部历史融资与来源 · '+c.history.length+' 条</summary>'+[...c.history].reverse().map(roundFacts).join('')+'</details>'+
    '<section class="kg-entry"><div><h3>企业知识图谱</h3><p>查看历史融资、参与机构、关联企业与已收录风险。</p></div><button type="button" class="kg-entry-action" data-kg-type="company" data-kg-id="'+esc(id)+'">查看知识图谱 →</button></section>'+
    '<form class="deal" id="offerForm"><h3>投资记录</h3><label>投资金额（'+game.currency+'）<input id="offerAmount" type="number" min="0.01" step="0.01" max="'+game.cash+'" required value="" placeholder="填写金额"></label><p>投资金额按成本计入账户。</p><div class="quote" id="offerPreview" aria-live="polite"></div><button class="primary" type="submit">确认投资</button></form>'+
    (p?'<p>累计投入 '+money(p.cost)+' · '+p.lots.length+' 笔投资'+(p.sim_value!=null?' · 当前预测价值 '+money(p.sim_value):'')+'</p>':'')+
    (game.last_result?.company===id?'<section class="investment-result" role="status"><h3>投资结果</h3><p>本次投入 '+money(game.last_result.amount)+' · 剩余现金 '+money(game.last_result.cash)+'</p>'+(game.last_result.projection?.predicted?'<p>预计 '+esc(game.last_result.projection.estimated_month)+' 融资 '+money(game.last_result.projection.predicted_amount,game.last_result.projection.currency)+'，已纳入月度估值路径。</p>':'')+'<button type="button" data-result-portfolio>查看投资记录 →</button></section>':'')+
    (c.comparison?.median_amount?'<details class="detail-section"><summary>同行融资参考</summary><p>同业、同轮次、同币种 '+c.comparison.n+' 家企业，最近披露金额中位数 '+money(c.comparison.median_amount,c.comparison.currency)+'</p></details>':'');
  offerPreview();if(show&&!$('#companyDialog').open)$('#companyDialog').showModal();
};
document.addEventListener('click',e=>{if(e.target.closest('[data-result-portfolio]')){$('#companyDialog').close();view='account';accountMode='portfolio';render()}});
offerPreview=function(){
  if(!$('#offerForm'))return;
  const c=game.companies.find(c=>c.id===selected),a=Number($('#offerAmount').value);
  const valid=Number.isFinite(a)&&a>0&&a<=game.cash;
  $('#offerPreview').textContent=c.closed?'有注销或吊销记录，暂停投资':game.fees_payable?'请先结清管理费':!valid?'金额需大于零且不超过账户现金':'投资后现金 '+money(game.cash-a)+' · 本次投入 '+money(a);
  $('#offerForm button').disabled=!valid||busy||game.ended||c.closed||!!game.fees_payable;
};
renderPortfolio=function(){
  $('#chart').innerHTML='';
  $('#positions').innerHTML=game.companies.filter(c=>game.positions[c.id]||game.intentions?.[c.id]).map(c=>{
    const p=game.positions[c.id],i=game.intentions?.[c.id];
    const projection=p?.projection;
    return '<article class="position"><div><button class="company-link" data-company="'+c.id+'"><h3>'+esc(companyName(c))+'</h3></button>'+(p?'<p>累计投入 '+money(p.cost)+' · '+p.lots.length+' 笔投资</p>'+(p.sim_value!=null?'<p>当前预测价值 '+money(p.sim_value)+' · 本月 '+(p.month_change>=0?'+':'')+money(p.month_change||0)+'</p>':'')+(projection?.predicted?'<p>预计 '+esc(projection.estimated_month)+' 融资 '+money(projection.predicted_amount,projection.currency)+' · '+esc(projection.basis)+'参考</p>':''):'')+(i?'<p>旧意向记录 '+money(i.amount,i.currency)+' · 未扣款，需重新确认投资</p>':'')+'</div></article>';
  }).join('')||'<div class="empty">暂无投资记录</div>';
};
requestAdvance=function(){
  if(busy||game.ended)return;
  const active=Object.values(game.positions).filter(p=>p.projection_mode==='peer_financing_projection_v1'&&!p.projection_complete).length;
  $('#advanceBody').innerHTML='<h2 id="advanceTitle">推进一个月</h2><p>结算管理费 '+money(game.initial*game.fee_rate/12)+'，更新 '+active+' 家持仓的融资进度与预测价值。</p><div class="preview-actions"><button data-close>取消</button><button class="primary" data-confirm-month>确认推进</button></div>';
  $('#advanceDialog').showModal();
};
$('#advance').onclick=requestAdvance;
showReport=function(previous){
  const before=previous.curve.at(-1),after=game.curve.at(-1),alerts=game.notifications||[];
  const cashDelta=game.cash-previous.cash,totalDelta=(after.sim_assets??after.net_assets)-(before.sim_assets??before.net_assets);
  const rows=alerts.map(n=>'<p>'+esc(companyName(game.companies.find(c=>c.id===n.company)))+' · 持仓估值变动 <b>'+(n.delta>=0?'+':'')+money(n.delta)+'</b>'+(n.event_due?' · 企业预计融资规模 '+money(n.predicted_amount,n.currency):'')+'</p>').join('');
  $('#reportBody').innerHTML='<button class="close" data-close aria-label="关闭">×</button><h2>'+game.as_of.slice(0,7)+' 月度结算</h2><div class="detail-stats"><div><span>本月账户价值变化</span><b>'+(totalDelta>=0?'+':'')+money(totalDelta)+'</b></div><div><span>月末持仓估值</span><b>'+money(after.sim_value??after.cost)+'</b></div><div><span>本月现金收支</span><b>'+(cashDelta===0?'无现金收支':(cashDelta>0?'+':'')+money(cashDelta))+'</b></div></div><div class="report-list">'+(rows||'<p>本月持仓估值没有变化。</p>')+(cashDelta===0?'<p>账户本月没有追加投资、退出回款或费用扣款。</p>':'')+'</div><button class="primary" data-close>查看账户</button>';
  $('#reportDialog').showModal();
};
rules=function(){
  $('#rulesBody').innerHTML='<p>历史资料截止 '+game.meta.cutoff+'，融资金额按原始币种展示。</p><p>未来融资事件由企业完整历史预测；融资金额与估值变化参考截止日前同阶段、同行业企业的历史记录。</p><p>人民币和美元分别估算，不自动换汇。旧账户记录可<a href="/api/legacy-export" download="original-account.json">下载</a>。</p>';
  $('#rulesDialog').showModal();
};
$('#rulesBtn').onclick=rules;

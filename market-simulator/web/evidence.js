'use strict';
$('.account div:nth-child(1)>span').textContent='成本口径资产';
$('.account div:nth-child(3)>span').textContent='已投入成本';
$('.account div:nth-child(4)>span').textContent='持仓盈亏';
$('.performance p').textContent='投入按成本记录；尚无可靠市值与收益模型。';
$('.workspace-note').textContent='确认投资后扣减模拟现金，计入持仓成本。';
$('.table-note').textContent='历史融资金额不是当前融资目标；原始币种不换算。';
$('[data-filter=held]').textContent='投资记录';
const evidenceRender=render;
render=function(){
  evidenceRender();if(!game)return;
  const point=game.curve.at(-1);
  $('#nav').textContent=money(point.net_assets);$('#cost').textContent=money(point.cost);
  $('#fees').textContent=Object.keys(game.positions).length?'暂不可估':'—';
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
    '<div class="detail-section"><h3>最近明确融资</h3>'+(r?'<p>'+money(r.amount,r.currency)+' · '+r.date+'</p><p>历史披露，不是当前报价'+(r.currency!==game.currency?'；与账户币种不同':'')+'</p>':'<p>暂无明确金额记录</p>')+'</div>'+
    '<form class="deal" id="offerForm"><h3>投资 <small>模拟账户</small></h3><label>投资金额（'+game.currency+'）<input id="offerAmount" type="number" min="0.01" step="0.01" max="'+game.cash+'" required value="" placeholder="填写金额"></label><p>按投入成本入仓；暂无估值与股权依据。</p><div class="quote" id="offerPreview" aria-live="polite"></div><button class="primary" type="submit">确认投资</button></form>'+
    (p?'<p>累计投入 '+money(p.cost)+' · '+p.lots.length+' 笔投资</p>':'')+
    (game.last_result?.company===id?'<section class="investment-result" role="status"><h3>投资结果</h3><p>本次投入 '+money(game.last_result.amount)+' · 剩余现金 '+money(game.last_result.cash)+'</p><button type="button" data-result-portfolio>查看投资记录 →</button></section>':'')+
    (c.comparison?.median_amount?'<details class="detail-section"><summary>同行融资参考</summary><p>同业、同轮次、同币种 '+c.comparison.n+' 家企业，最近披露金额中位数 '+money(c.comparison.median_amount,c.comparison.currency)+'</p><p>每家企业一条历史记录，日期不同；不是估值或收益预测。</p></details>':'')+
    '<details class="detail-section"><summary>历史记录与来源 · '+c.history.length+' 条</summary>'+[...c.history].reverse().map(roundFacts).join('')+'</details>';
  offerPreview();if(show&&!$('#companyDialog').open)$('#companyDialog').showModal();
};
document.addEventListener('click',e=>{if(e.target.closest('[data-result-portfolio]')){$('#companyDialog').close();view='portfolio';render()}});
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
    return '<article class="position"><div><button class="company-link" data-company="'+c.id+'"><h3>'+esc(companyName(c))+'</h3></button>'+(p?'<p>累计投入 '+money(p.cost)+' · '+p.lots.length+' 笔投资</p><p>暂无股权与收益依据</p>':'')+(i?'<p>旧意向记录 '+money(i.amount,i.currency)+' · 未扣款，需重新确认投资</p>':'')+'</div></article>';
  }).join('')||'<div class="empty">暂无投资记录</div>';
};
requestAdvance=function(){
  if(busy||game.ended)return;
  $('#advanceBody').innerHTML='<h2 id="advanceTitle">推进一个月</h2><p>管理费 '+money(game.initial*game.fee_rate/12)+'；无新交易依据，不自动生成收益。</p><div class="preview-actions"><button data-close>取消</button><button class="primary" data-confirm-month>确认推进</button></div>';
  $('#advanceDialog').showModal();
};
$('#advance').onclick=requestAdvance;
showReport=function(previous){
  $('#reportBody').innerHTML='<button class="close" data-close aria-label="关闭">×</button><h2>'+game.as_of.slice(0,7)+' 月度结算</h2><p>现金变动 '+money(game.cash-previous.cash)+'</p><p>本月未计算估值变化；现金变动不代表投资收益。</p><button class="primary" data-close>查看账户</button>';
  $('#reportDialog').showModal();
};
rules=function(){
  $('#rulesBody').innerHTML='<p>历史资料截止 '+game.meta.cutoff+'。历史金额不代表当前融资目标，币种不换算。</p><p>投资为用户在账户币种下的模拟资金配置，不代表企业接受真实融资或完成换汇。确认后现金转为投入成本；缺少可靠估值时不计算股权与收益。不设虚构的企业认购门槛。</p><p>旧账户记录保留，可<a href="/api/legacy-export" download="original-account.json">下载原始记录</a>。旧意向不会自动扣款。</p>';
  $('#rulesDialog').showModal();
};
$('#rulesBtn').onclick=rules;

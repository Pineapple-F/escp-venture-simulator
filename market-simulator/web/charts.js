'use strict';
function capitalPoints(){
  if(!game.opening_point)return game.curve;
  return [{...game.opening_point,label:'开户'},...(game.transaction_points||[]).map(p=>({...p,label:p.action==='offer'?'投资 #'+p.revision:p.date.slice(0,7)}))];
}
function cashChart(points){
    const maximum=Math.max(1,...points.map(p=>p.cash+p.cost));
  return '<div class="capital-bars" aria-label="每月资金分布">'+points.map((p,i)=>'<button class="capital-column" data-ledger-index="'+i+'" aria-label="'+esc(p.date+'，现金 '+money(p.cash)+'，已投入 '+money(p.cost))+'"><span class="capital-stack"><span class="capital-cash" style="height:'+Math.max(0,p.cash)/maximum*100+'%"></span><span class="capital-cost" style="height:'+Math.max(0,p.cost)/maximum*100+'%"></span></span><span class="capital-month">'+p.date.slice(0,7)+'</span></button>').join('')+'</div><div id="capitalReading" aria-live="polite"></div>';
}
function selectCapital(index){
  const p=capitalPoints()[index];if(!p)return;
  document.querySelectorAll('[data-ledger-index]').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.ledgerIndex)===index)));
  $('#capitalReading').innerHTML='<small>'+p.date+' · '+esc(p.label||'月末记录')+'</small><div class="capital-values"><span>可用现金<strong>'+money(p.cash)+'</strong></span><span>已投入<strong>'+money(p.cost)+'</strong></span></div>'+(p.fees_payable?'<small>另有应付费用 '+money(p.fees_payable)+'，未计入柱高。</small>':'');
}
document.addEventListener('click',e=>{const b=e.target.closest('[data-ledger-index]');if(b)selectCapital(Number(b.dataset.ledgerIndex))});
$('#journalView').insertBefore($('.performance'),$('#journal'));
const chartPortfolio=renderPortfolio;
renderPortfolio=function(){
  chartPortfolio();
  $('.performance header').innerHTML='<b>资金分布</b><span class="capital-legend"><i></i>可用现金 <i></i>已投入</span>';
  $('.performance p').textContent=game.opening_point?'从开户起记录每次投资与月度结算；点击查看金额。':'旧账户仅保留月末记录，不补造开户和逐笔历史。';
  const points=capitalPoints();$('#chart').innerHTML=cashChart(points);
  document.querySelectorAll('.capital-month').forEach((node,i)=>node.textContent=points[i].label||points[i].date.slice(0,7));
  selectCapital(points.length-1);
};

'use strict';
function capitalPoints(){
  if(!game.opening_point)return game.curve;
  return [{...game.opening_point,label:'开户'},...(game.transaction_points||[]).map(p=>({...p,label:p.action==='offer'?'投资 #'+p.revision:p.date.slice(0,7)}))];
}
function cashChart(points){
  const maximum=Math.max(1,...points.map(p=>p.cash+(p.sim_value??p.cost)));
  return '<div class="capital-bars" aria-label="每月资金分布">'+points.map((p,i)=>'<button class="capital-column" data-ledger-index="'+i+'" aria-label="'+esc(p.date+'，现金 '+money(p.cash)+'，持仓预测价值 '+money(p.sim_value??p.cost))+'"><span class="capital-stack"><span class="capital-cash" style="height:'+Math.max(0,p.cash)/maximum*100+'%"></span><span class="capital-cost" style="height:'+Math.max(0,p.sim_value??p.cost)/maximum*100+'%"></span></span><span class="capital-month">'+p.date.slice(0,7)+'</span></button>').join('')+'</div><div id="capitalReading" aria-live="polite"></div>';
}
function selectCapital(index){
  const p=capitalPoints()[index];if(!p)return;
  document.querySelectorAll('[data-ledger-index]').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.ledgerIndex)===index)));
  $('#capitalReading').innerHTML='<small>'+p.date+' · '+esc(p.label||'月末记录')+'</small><div class="capital-values"><span>可用现金<strong>'+money(p.cash)+'</strong></span><span>投入成本<strong>'+money(p.cost)+'</strong></span><span>持仓预测价值<strong>'+money(p.sim_value??p.cost)+'</strong></span><span>模拟总资产<strong>'+money(p.sim_assets??p.net_assets)+'</strong></span></div>'+(p.fees_payable?'<small>另有应付费用 '+money(p.fees_payable)+'，已从总资产扣除。</small>':'');
}
document.addEventListener('click',e=>{const b=e.target.closest('[data-ledger-index]');if(b)selectCapital(Number(b.dataset.ledgerIndex))});
const chartPortfolio=renderPortfolio;
renderPortfolio=function(){
  chartPortfolio();
  $('.performance header').innerHTML='<b>资金与持仓价值</b><span class="capital-legend"><i></i>可用现金 <i></i>持仓预测价值</span>';
  const performanceNote=$('.performance p');
  if(performanceNote)performanceNote.textContent=game.opening_point?'从开户起记录每次投资与月度结算；点击查看金额。':'月末资金记录。';
  const points=capitalPoints();$('#chart').innerHTML=cashChart(points);
  document.querySelectorAll('.capital-month').forEach((node,i)=>node.textContent=points[i].label||points[i].date.slice(0,7));
  selectCapital(points.length-1);
};

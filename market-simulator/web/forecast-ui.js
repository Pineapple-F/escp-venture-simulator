'use strict';
const investorForecastGuidance={
  '融资':'查看融资历史、资金用途和当前接触价值。',
  '企业／机构股东进入':'关注新股东背景、治理权变化及潜在共同投资关系。',
  '股权结构变更':'查看 cap table、受益所有人、稀释与历史转让。',
  '注册资本变更':'查看工商变更原因、实缴情况与融资动作。',
  '注销':'查看主体状态与风险记录。'
};
let signalPage=1,signalLoading=false,signalLoadedKey='',signalTimer,forecastDetailRequest=0,trackedRows=[],trackedRevision=-1;
const baseForecastRender=render;
render=function(){
  baseForecastRender();if(!game)return;
  $('#signalsView').hidden=view!=='discover'||discoverMode!=='future';
  if(view==='discover'&&discoverMode==='future')loadSignals();
  if(view==='companies')loadTrackedCompanies();
  renderForecastReminders();
};
function signalParams(){return new URLSearchParams({event:$('#signalEvent').value,months:$('#signalMonths').value,q:$('#signalSearch').value,watched:$('#signalWatched').checked?'1':'0',page:signalPage});}
async function loadSignals(force=false){
  const key=signalParams().toString();if(signalLoading||!force&&key===signalLoadedKey)return;
  signalLoading=true;$('#signalRows').innerHTML='<div class="empty">正在读取已生成的企业预测…</div>';
  try{
    const result=await api('/api/forecast-opportunities?'+key);signalLoadedKey=key;signalPage=result.page;
    $('#signalCoverage').textContent='已预测 '+result.coverage.toLocaleString()+' / '+result.universe.toLocaleString()+' 家';
    $('#signalSummary').innerHTML='<div><span>当前筛选</span><strong>'+result.total.toLocaleString()+' 家</strong></div><div><span>事件</span><strong>'+esc(result.event)+'</strong></div><div><span>时间范围</span><strong>未来 '+result.months+' 个月</strong></div><div><span>我的关注</span><strong>'+result.watchlist_count+' 家</strong></div>';
    $('#signalRows').innerHTML=result.items.map(signalCard).join('')||'<div class="empty">当前筛选没有企业。</div>';
    $('#signalPage').textContent=result.page+' / '+result.pages+' 页';$('#signalPrev').disabled=result.page<=1;$('#signalNext').disabled=result.page>=result.pages;
  }catch(error){$('#signalRows').innerHTML='<div class="empty">'+esc(error.message)+'</div>';}
  finally{signalLoading=false;}
}
function signalCard(row){
  const events=row.predicted_events.map(item=>'<span>'+esc(item.estimated_month)+' · '+esc(item.event)+'</span>').join('');
  return '<article class="signal-card"><div><p class="eyebrow">'+esc(row.region)+' · '+esc(row.industry)+'</p><button class="company-link" data-company="'+esc(row.company)+'"><h3>'+esc(row.name)+'</h3></button><div class="signal-events">'+events+'</div><small>模型读取 '+row.history_nodes+' 个历史事件 · 最近输入 '+esc(row.history_end)+'</small></div><div class="signal-card-actions"><b>'+esc(row.matched_event.estimated_month)+'</b><span>'+esc(row.matched_event.event)+'</span><button data-signal-company="'+esc(row.company)+'">查看路径 →</button><button class="'+(row.watched?'watched':'secondary')+'" data-watch-company="'+esc(row.company)+'" data-watch-enabled="'+(!row.watched)+'">'+(row.watched?'取消关注':'加入关注')+'</button></div></article>';
}
async function saveWatch(company,enabled){
  const result=await api('/api/action',{type:'forecast_watch',company,enabled,revision:game.revision});game=result.game;signalLoadedKey='';trackedRevision=-1;render();if(view==='discover'&&discoverMode==='future')loadSignals(true);toast(enabled?'已加入未来事件关注':'已取消关注');
}
function renderForecastReminders(){
  if(!game||view!=='discover'||discoverMode!=='future')return;
  const count=Object.keys(game.forecast_watchlist||{}).length;
  $('.inbox>header:first-child h2').textContent='未来事件提醒';$('#taskCount').textContent=count;
  $('#tasks').hidden=false;$('#tasks').innerHTML=count?'<button class="task" id="showWatchedSignals"><strong>'+count+' 家已关注企业</strong><p>切换“只看已关注”管理跟进计划 →</p></button>':'<div class="dispatch-item"><p>尚未关注企业。可从机会池加入关注并记录跟进。</p></div>';
  $('.inbox-guide span').textContent='当前任务';$('.inbox-guide p').textContent='查看预测事件，记录跟进状态和负责人。';
}
async function loadTrackedCompanies(){
  if(trackedRevision===game.revision){renderTrackedCompanies();return;}
  $('#myCompanyRows').innerHTML='<div class="empty">正在整理关注、跟进和投资记录…</div>';
  try{const result=await api('/api/tracked-companies');trackedRows=result.items;trackedRevision=game.revision;renderTrackedCompanies();}
  catch(error){$('#myCompanyRows').innerHTML='<div class="empty">'+esc(error.message)+'</div>';}
}
function renderTrackedCompanies(){
  document.querySelectorAll('[data-company-filter]').forEach(b=>b.classList.toggle('active',b.dataset.companyFilter===companyFilter));
  const rows=trackedRows.filter(row=>companyFilter==='all'||companyFilter==='watched'&&row.watched||companyFilter==='invested'&&row.invested);
  $('#myCompanyRows').innerHTML=rows.map(row=>'<article class="tracked-card"><div><p class="eyebrow">'+esc(row.industry)+' · '+esc(row.region)+'</p><h3>'+esc(row.name)+'</h3><p>'+[row.watched?'已关注':'',row.invested?'已投资':'',row.followups.length?row.followups.length+' 项事件跟进':''].filter(Boolean).join(' · ')+'</p><div class="tracked-followups">'+row.followups.map(item=>'<span>'+esc(item.event)+' · '+esc(item.status)+(item.due_month?' · '+esc(item.due_month):'')+'</span>').join('')+'</div></div><button data-company="'+esc(row.id)+'">查看企业 →</button></article>').join('')||'<div class="empty">暂时没有企业。</div>';
}
document.querySelectorAll('[data-company-filter]').forEach(button=>button.onclick=()=>{companyFilter=button.dataset.companyFilter;renderTrackedCompanies();});
function forecastDetailMarkup(result,id){
  if(!result.available)return '<section class="detail-section forecast-detail"><h3>未来一年预测</h3><p>'+esc(result.reason)+'</p></section>';
  const predicted=result.events.filter(item=>item.predicted).sort((a,b)=>a.month_index-b.month_index),followups=game.forecast_followups?.[id]||{},watched=!!game.forecast_watchlist?.[id];
  const finance=result.financial_projection;
  return '<section class="detail-section forecast-detail"><div class="forecast-detail-title"><div><p class="eyebrow">未来12个月</p><h3>企业发展路径</h3></div><button data-watch-company="'+esc(id)+'" data-watch-enabled="'+(!watched)+'">'+(watched?'取消关注':'关注企业')+'</button></div>'+(predicted.length?'<ol>'+predicted.map(item=>{const saved=followups[item.event]||{},amount=item.event==='融资'&&finance?.available?'<p>预计融资金额 '+money(finance.predicted_amount,finance.currency)+' · '+esc(finance.basis)+' '+finance.peer_count+' 家历史样本</p>':'';return '<li><time>'+esc(item.estimated_month)+'</time><div><b>'+esc(item.event)+'</b><p>'+esc(investorForecastGuidance[item.event])+'</p>'+amount+'<form class="forecast-followup" data-company="'+esc(id)+'" data-event="'+esc(item.event)+'"><select name="status">'+['待研判','跟进中','已联系','不跟进'].map(status=>'<option'+(saved.status===status?' selected':'')+'>'+status+'</option>').join('')+'</select><input name="due_month" type="month" value="'+esc(saved.due_month||item.estimated_month)+'"><input name="note" maxlength="600" value="'+esc(saved.note||'')+'" placeholder="负责人或跟进事项"><button type="submit">保存跟进</button><small class="followup-status"></small></form></div></li>'}).join('')+'</ol>':'<p>未来一年暂无预测事件。</p>')+'<details><summary>输入范围</summary><p>'+result.history_nodes+' 个历史事件，'+esc(result.history_start)+' 至 '+esc(result.history_end)+'。模型版本：'+esc(result.model)+'。</p></details><button type="button" class="secondary" data-go-companies>查看我的企业 →</button></section>';
}
const baseForecastShowCompany=showCompany;
showCompany=async function(id,show=true){
  const ticket=++forecastDetailRequest;await baseForecastShowCompany(id,show);if(ticket!==forecastDetailRequest||selected!==id)return;
  const body=$('#companyBody');if(!body||body.querySelector('.forecast-detail'))return;
  const holder=document.createElement('div');holder.className='forecast-detail-loading';holder.innerHTML='<section class="detail-section"><h3>未来一年预测</h3><p>正在读取完整历史并运行模型…</p></section>';const offer=body.querySelector('#offerForm');if(offer)offer.before(holder);else body.append(holder);
  try{const result=await api('/api/model-forecast?id='+encodeURIComponent(id));if(ticket!==forecastDetailRequest||selected!==id)return;holder.outerHTML=forecastDetailMarkup(result,id);}catch(error){if(ticket===forecastDetailRequest)holder.innerHTML='<section class="detail-section"><h3>未来一年预测</h3><p>'+esc(error.message)+'</p></section>';}
};
for(const id of ['signalEvent','signalMonths','signalWatched'])$('#'+id).onchange=()=>{signalPage=1;signalLoadedKey='';loadSignals(true)};
$('#signalSearch').oninput=()=>{clearTimeout(signalTimer);signalTimer=setTimeout(()=>{signalPage=1;signalLoadedKey='';loadSignals(true)},250)};
$('#signalPrev').onclick=()=>{signalPage--;signalLoadedKey='';loadSignals(true)};$('#signalNext').onclick=()=>{signalPage++;signalLoadedKey='';loadSignals(true)};
document.addEventListener('click',async e=>{
  const signal=e.target.closest('[data-signal-company]');if(signal){showCompany(signal.dataset.signalCompany);return;}
  const watch=e.target.closest('[data-watch-company]');if(watch){watch.disabled=true;try{await saveWatch(watch.dataset.watchCompany,watch.dataset.watchEnabled==='true');if($('#companyDialog').open&&selected===watch.dataset.watchCompany)showCompany(selected,false);}catch(error){toast(error.message);watch.disabled=false;}return;}
  if(e.target.closest('#showWatchedSignals')){$('#signalWatched').checked=true;signalPage=1;signalLoadedKey='';loadSignals(true);}
  if(e.target.closest('[data-go-companies]')){$('#companyDialog').close();view='companies';render();}
});
document.addEventListener('submit',async e=>{
  const form=e.target.closest('.forecast-followup');if(!form)return;e.preventDefault();const data=new FormData(form),button=form.querySelector('button'),message=form.querySelector('.followup-status');button.disabled=true;message.textContent='保存中…';
  try{const result=await api('/api/action',{type:'forecast_followup',company:form.dataset.company,event:form.dataset.event,status:data.get('status'),due_month:data.get('due_month'),note:data.get('note'),revision:game.revision});game=result.game;message.textContent='已保存';signalLoadedKey='';trackedRevision=-1;}
  catch(error){message.textContent=error.message;}finally{button.disabled=false;}
});

// The account request can finish before this final UI layer loads.
// Render once here so the default future-opportunity view is never left blank.
if(game)render();

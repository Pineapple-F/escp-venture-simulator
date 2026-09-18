'use strict';
const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const labels={financials:'财务与现金流记录',use_of_funds:'上轮资金使用与本轮预算',cap_table:'股权结构与股东信息',team:'团队与关键岗位信息',risk_explanation:'风险事项说明'};
let account=null,company=null,page=0,requestId=0,dirty=false,saving=false;
let goal='prepare';
let customTaxonomy=null,customPredictRequest=0,currentCustomForecast=null,currentModelForecast=null,activeFounderSection='path',customFinanceDirty=false;
let scenarioRequest=0,scenarioLoadedKey='',scenarioReady=false;
function showFounderMode(mode){
  $('#buildOwnExisting').classList.toggle('secondary',mode!=='custom');
  $('#change').classList.toggle('secondary',mode!=='dataset');
}
function setFounderSection(section){
  activeFounderSection=section;
  document.querySelectorAll('[data-section]').forEach(button=>button.classList.toggle('secondary',button.dataset.section!==section));
  const custom=!company;
  $('#customSection').hidden=!custom||section!=='path';
  $('#customActionsSection').hidden=!custom||section!=='actions';
  $('#customEvidenceSection').hidden=!custom||section!=='profile';
  $('#details').hidden=custom;
  $('#pathTimelineSection').hidden=custom||section!=='path';
  for(const key of ['overview','past','model','graph','finance']){
    $('#'+key+'Section').hidden=custom||!(section==='path'&&key==='model'||section==='profile'&&['overview','past'].includes(key)||section==='actions'&&key==='finance'||section==='graph'&&key==='graph');
  }
  if(!custom&&section==='path'){
    renderDatasetPath();
    if(profileLoaded!==company.id)loadProfile();
    if(modelLoaded!==company.id)loadModelForecast();
  }
  if(!custom&&section==='graph')renderGraphCompanies();
  if(custom&&section==='actions')renderCustomActions();
  if(custom&&section==='profile')renderCustomEvidence();
  window.scrollTo(0,0);
}
async function setFounderMode(mode){
  if(account.founder_mode===mode)return;
  const result=await api('/api/action',{type:'founder_custom_mode',mode,revision:account.revision});account=result.game;
}
async function loadCustomTaxonomy(){
  if(customTaxonomy)return;
  const result=await api('/api/custom-event-types');customTaxonomy=result.categories;
  $('#customCategory').innerHTML=customTaxonomy.map(item=>'<option value="'+esc(item.key)+'">'+esc(item.label)+'</option>').join('');
  renderCustomSubtypes();
}
function renderCustomSubtypes(){
  if(!customTaxonomy)return;
  const category=customTaxonomy.find(item=>item.key===$('#customCategory').value)||customTaxonomy[0];
  $('#customSubtype').innerHTML=category.items.map(item=>'<option value="'+esc(item.key)+'">'+esc(item.label)+'</option>').join('');
}
function renderCustomPath(){
  const custom=account.founder_custom||{},profile=custom.profile||{},events=custom.events||[];
  const form=$('#customProfileForm');
  for(const key of ['name','industry','region'])form.elements[key].value=profile[key]||'';
  $('#customEventCount').textContent=events.length+' 个事件';
  $('#customTimeline').innerHTML=events.length?'<ol class="custom-timeline">'+events.map((event,index)=>'<li class="timeline-fact"><div class="custom-node-index">'+(index+1)+'</div><time>'+esc(event.date)+'</time><div><small>'+esc(event.category_label)+' · 已发生</small><strong>'+esc(event.label)+'</strong></div><button type="button" class="secondary" data-delete-custom-event="'+esc(event.id)+'" aria-label="删除 '+esc(event.label)+'">删除</button></li>').join('')+'</ol>':'<div class="custom-path-empty"><b>还没有历史事件</b><p>建议从“公司成立”开始，再按时间添加融资、股东、股权、资本或风险事件。</p></div>';
  $('#customPredict').disabled=!events.length;
}
async function openCustom(persist=true){
  if(dirty&&!confirm('融资方案有未保存的修改，是否离开当前案例企业？'))return;
  if(persist)await setFounderMode('custom');
  company=null;requestId++;modelRequest++;profileRequest++;
  $('#picker').hidden=true;
  const profile=account.founder_custom?.profile||{};
  $('#companyName').textContent=profile.name||'构建我的企业';$('#companyMeta').textContent='企业自报路径 · 不要求存在于历史数据集';$('#sidebarCompany').textContent=profile.name||'我的企业';
  showFounderMode('custom');
  document.querySelectorAll('[data-section]').forEach(button=>{button.hidden=button.dataset.section==='graph';button.disabled=false;button.title='';});
  await loadCustomTaxonomy();
  if(!$('#customEventForm').elements.date.value)$('#customEventForm').elements.date.value=new Date().toISOString().slice(0,10);
  renderCustomPath();setFounderSection('path');status();
}
async function openDataset(persist=true){
  if(persist)await setFounderMode('dataset');
  $('#customSection').hidden=true;$('#customActionsSection').hidden=true;$('#customEvidenceSection').hidden=true;$('#details').hidden=true;$('#picker').hidden=false;
  $('#companyName').textContent='选择案例企业';$('#companyMeta').textContent='匿名历史企业 · 用于体验现有工作台';$('#sidebarCompany').textContent='选择案例企业';
  showFounderMode('dataset');
  document.querySelectorAll('[data-section]').forEach(button=>{button.hidden=false;button.disabled=true;});list();status();window.scrollTo(0,0);
}
function renderCustomForecast(result){
  currentCustomForecast=result;
  const predicted=result.events.filter(item=>item.predicted).sort((a,b)=>a.month_index-b.month_index);
  const plans=account.forecast_plans?.founder_custom||{};
  const future=predicted.length?'<ol class="custom-future-path">'+predicted.map((item,index)=>'<li class="timeline-prediction"><i>'+(index+1)+'</i><time>'+esc(item.estimated_month)+'</time><div><small>预测事件'+(plans[item.event]?' · 计划：'+esc(plans[item.event].status):'')+'</small><strong>'+esc(item.event)+'</strong><p>'+esc(modelGuidance[item.event]?.copy||'进入行动工作台制定计划。')+'</p><button type="button" data-custom-action="'+esc(item.event)+'">制定行动 →</button></div></li>').join('')+'</ol>':'<div class="model-empty"><h3>未来一年暂无预测事件</h3></div>';
  $('#customForecastResults').innerHTML='<section class="panel custom-result"><div class="custom-result-heading"><div><p class="eyebrow">未来12个月</p><h2>预测路径</h2></div><span>'+esc(result.horizon_start)+' 至 '+esc(result.horizon_end)+'</span></div>'+future+'<details><summary>输入范围</summary><p>'+result.history_nodes+' 个历史事件 · '+esc(result.history_start)+' 至 '+esc(result.history_end)+'</p></details></section>';
  $('#customSimilarResults').innerHTML='<section class="panel similar-section"><div class="custom-result-heading"><div><p class="eyebrow">历史参照</p><h2>相似企业</h2></div><span>资料截至 '+esc(result.reference_cutoff)+'</span></div><div class="similar-grid">'+(result.similar.map(item=>'<article class="similar-card"><header><div><small>'+esc(item.region)+' · '+esc(item.industry)+'</small><h3>'+esc(item.name)+'</h3></div><b>'+Math.round(item.display_similarity*100)+'%</b></header><p>相似事件：'+esc(item.shared_events.join('、')||'整体事件节奏')+' · '+item.history_nodes+' 个历史事件</p><div class="similar-outcomes"><strong>随后12个月</strong>'+(item.next_12_months.length?item.next_12_months.map(event=>'<span><time>'+esc(event.date.slice(0,7))+'</time>'+esc(event.event)+'</span>').join(''):'<span>暂无新事件</span>')+'</div><button type="button" class="secondary" data-custom-reference="'+esc(item.id)+'">查看企业路径 →</button></article>').join('')||'<div class="model-empty"><p>暂无相似企业。</p></div>')+'</div></section>';
  renderCustomActions();renderCustomEvidence();
}
function fundingVisual(history){
  if(!history.length)return '<p>暂无融资记录。</p>';
  const rows=[...history].sort((a,b)=>a.date.localeCompare(b.date)||String(a.id||'').localeCompare(String(b.id||'')));
  const charts=['CNY','USD'].map(currency=>{
    const known=rows.filter(r=>r.currency===currency&&!r.conflict&&Number.isFinite(r.amount)&&r.amount>0);
    if(known.length<2)return '';
    const maximum=Math.max(...known.map(r=>r.amount));
    return '<section class="funding-amount-chart" aria-label="'+(currency==='CNY'?'人民币':'美元')+'融资金额比较"><h3>各轮融资金额 · '+currency+'</h3>'+known.map(r=>'<div class="funding-bar-row"><div class="funding-bar-label"><span>'+esc(r.date)+' · '+esc(r.stage)+'</span><strong>'+esc(money(r.amount,currency))+'</strong></div><div class="funding-bar-track" aria-hidden="true"><div class="funding-bar" style="width:'+(r.amount/maximum*100).toFixed(4)+'%"></div></div></div>').join('')+'</section>';
  }).join('');
  return charts+'<h3 class="funding-timeline-title">融资历程</h3><ol class="funding-timeline">'+rows.map(r=>'<li><time datetime="'+esc(r.date)+'">'+esc(r.date)+'</time><div><h3>'+esc(r.stage)+'</h3><p>'+esc(r.conflict?'金额存在冲突':r.amount==null?'金额未披露':money(r.amount,r.currency))+'</p><small class="muted">'+(r.publication_proxy?'披露日期未提供':('记录可见于 '+esc(r.available)))+'</small></div></li>').join('')+'</ol>';
}
let profileRequest=0,profileLoaded=null;
function companySection(section){
  setFounderSection(({overview:'profile',past:'profile',model:'path',finance:'actions'})[section]||section);
}
let modelRequest=0,modelLoaded=null;
const modelGuidance={
  '融资':{copy:'核对资金缺口、融资节奏和材料准备。',action:'打开融资方案',target:'plan'},
  '企业／机构股东进入':{copy:'提前准备股东协议、投资者材料和治理边界。',action:'查看机构池',target:'find'},
  '股权结构变更':{copy:'核对 cap table、稀释比例与审批事项。',action:'打开融资方案',target:'plan'},
  '注册资本变更':{copy:'整理工商材料，确认金额、股东决议与办理窗口。',action:'记录准备事项',target:'model'},
  '注销':{copy:'查看主体状态和异常记录，安排风险处置。',action:'查看企业概况',target:'overview'}
};
function fallbackHistoryYears(){
  const rows=[...(company?.history||[]).map(item=>({date:item.date,event:'融资 · '+item.stage})),...(company?.risks||[]).map(item=>({date:item.date,event:item.type==='abnormal_listing'?'进入经营异常':'退出经营异常'}))];
  const groups={};for(const row of rows){const year=Number(String(row.date).slice(0,4));if(!year)continue;(groups[year]??=[]).push(row.event);}
  return Object.entries(groups).sort((a,b)=>a[0]-b[0]).map(([year,events])=>{const counts={};for(const event of events)counts[event]=(counts[event]||0)+1;return {year:Number(year),count:events.length,events:Object.entries(counts).slice(0,4).map(([event,count])=>({event,count}))};});
}
function renderDatasetPath(result=currentModelForecast){
  if(!company)return;
  const years=result?.history_years||fallbackHistoryYears(),predicted=result?.events?.filter(item=>item.predicted).sort((a,b)=>a.month_index-b.month_index)||[],plans=account.forecast_plans?.[company.id]||{};
  $('#pathOverviewStats').innerHTML='<span><b>'+(result?.history_nodes??years.reduce((sum,item)=>sum+item.count,0))+'</b> 个历史事件</span><span><b>'+predicted.length+'</b> 个未来事件</span>';
  const history=years.map(item=>'<article class="path-card path-card-fact"><header><time>'+esc(item.year)+'</time><span>'+item.count+' 个事件</span></header><div class="path-dot" aria-hidden="true"></div><h3>'+esc(item.events?.[0]?.event||'历史记录')+'</h3><div class="path-tags">'+(item.events||[]).map(event=>'<span>'+esc(event.event)+(event.count>1?' × '+event.count:'')+'</span>').join('')+'</div></article>').join('');
  const cutoff='<article class="path-card path-card-cutoff"><header><time>'+esc(result?.as_of||account.meta.cutoff)+'</time><span>资料截止</span></header><div class="path-dot" aria-hidden="true"></div><h3>现在</h3><p>历史进程与未来路径的分界点。</p></article>';
  const future=predicted.map(item=>'<article class="path-card path-card-prediction"><header><time>'+esc(item.estimated_month)+'</time><span>预测事件</span></header><div class="path-dot" aria-hidden="true"></div><h3>'+esc(item.event)+'</h3><p>'+esc(modelGuidance[item.event]?.copy||'进入行动工作台制定计划。')+'</p>'+(plans[item.event]?'<span class="path-plan-status">计划：'+esc(plans[item.event].status)+'</span>':'')+'<button type="button" data-path-action="'+esc(item.event)+'">制定行动 →</button></article>').join('');
  const empty=!result?'<article class="path-card path-card-loading"><header><time>未来一年</time><span>生成中</span></header><div class="path-dot" aria-hidden="true"></div><h3>正在生成路径</h3></article>':!future?'<article class="path-card path-card-empty"><header><time>未来一年</time><span>预测结果</span></header><div class="path-dot" aria-hidden="true"></div><h3>未来一年暂无预测事件</h3></article>':'';
  $('#pathOverview').innerHTML='<div class="path-rail">'+(history||'<article class="path-card path-card-empty"><h3>暂无历史事件</h3></article>')+cutoff+future+empty+'</div>';
}
function planForm(item,custom=false,savedOnly=false){
  const plans=account.forecast_plans?.[custom?'founder_custom':company.id]||{},plan=plans[item.event]||{};
  const timing=savedOnly?'已保存':(item.estimated_month?'预计 '+esc(item.estimated_month):'待安排');
  return '<details class="forecast-plan-card"><summary><span><b>'+esc(item.event)+'</b><small>'+timing+'</small></span><em>'+(plan.status?esc(plan.status):'待准备')+'</em></summary><form class="forecast-plan" data-event="'+esc(item.event)+'" data-custom="'+custom+'"><div class="forecast-plan-fields"><label>状态<select name="status">'+['待准备','进行中','已完成','暂不处理'].map(x=>'<option'+(plan.status===x?' selected':'')+'>'+x+'</option>').join('')+'</select></label><label>计划月份<input name="due_month" type="month" value="'+esc(plan.due_month||item.estimated_month||'')+'"></label></div><label>行动备注<textarea name="note" maxlength="600" rows="2" placeholder="负责人、材料或下一步">'+esc(plan.note||'')+'</textarea></label><button type="submit">保存行动</button><span class="plan-save-status"></span></form></details>';
}
function renderCustomActions(focus=''){
  const predicted=currentCustomForecast?.events.filter(x=>x.predicted).sort((a,b)=>a.month_index-b.month_index)||[];
  const selected=predicted.find(x=>x.event===focus);
  const saved=Object.values(account.forecast_plans?.founder_custom||{}).filter(item=>!predicted.some(x=>x.event===item.event));
  $('#customActionContext').innerHTML=selected?'<p class="eyebrow">行动工作台</p><h2>'+esc(selected.event)+'</h2><p>预计时间 '+esc(selected.estimated_month)+' · 设置状态、时间与负责人。</p>':'<p class="eyebrow">从预测到执行</p><h2>行动工作台</h2><p>先安排预测事件，再核对融资金额、现金缺口和资金用途。</p>';
  $('#customActionPlans').innerHTML=predicted.length||saved.length?'<h2>事件行动</h2>'+predicted.map(item=>planForm(item,true)).join('')+saved.map(item=>planForm(item,true,true)).join(''):'';
  const draft=account.founder_custom_finance_plan||{},form=$('#customFinanceForm');
  if(!customFinanceDirty)for(const key of ['currency','target','cash','burn','purpose'])form.elements[key].value=draft[key]??(key==='currency'?'CNY':'');
  updateCustomRunway();
}
function renderCustomEvidence(){
  const custom=account.founder_custom||{},profile=custom.profile||{},events=custom.events||[],count=events.length,similar=currentCustomForecast?.similar?.length||0;
  const last=events.at(-1);
  $('#customEvidenceSummary').innerHTML='<div class="facts"><div><span>历史事件</span><strong>'+count+'</strong></div><div><span>相似企业</span><strong>'+similar+'</strong></div><div><span>预测范围</span><strong>12个月</strong></div></div><section class="panel"><h2>'+esc(profile.name||'我的企业')+'</h2><p>'+esc([profile.industry,profile.region].filter(Boolean).join(' · ')||'尚未填写行业与地区')+'</p><p>'+(last?'最近事件：'+esc(last.date)+' · '+esc(last.label):'尚未添加历史事件')+'</p><p>'+(currentCustomForecast?'未来路径已生成，可返回发展路径查看。':'完成历史路径后即可生成未来一年。')+'</p></section>';
}
function updateCustomRunway(){
  const f=$('#customFinanceForm'),cash=f.elements.cash.value,burn=f.elements.burn.value,target=f.elements.target.value,purpose=f.elements.purpose.value.trim(),currency=f.elements.currency.value;
  const parts=[];
  if(target!=='')parts.push('计划融资 '+money(Number(target),currency));
  parts.push(cash!==''&&burn!==''&&Number(burn)>0?'当前现金可覆盖约 '+(Number(cash)/Number(burn)).toFixed(1)+' 个月':'填写现金与月净消耗后计算覆盖月数');
  if(purpose)parts.push('资金用途：'+purpose);
  $('#customRunway').textContent=parts.join(' · ')+'。';
}
function renderModelForecast(result){
  currentModelForecast=result;
  const predicted=result.events.filter(x=>x.predicted).sort((a,b)=>a.month_index-b.month_index);
  const otherPredicted=predicted.filter(x=>x.event!=='融资');
  const absent=result.events.filter(x=>!x.predicted),plans=account.forecast_plans?.[company.id]||{};
  $('#modelSummary').innerHTML='<div class="forecast-summary"><div><span>预测事件</span><strong>'+predicted.length+'</strong></div><div><span>下一个事件</span><strong>'+(predicted.length?esc(predicted[0].event):'暂无')+'</strong></div><div><span>预测范围</span><strong>12个月</strong></div></div>';
  $('#modelResults').innerHTML=predicted.length?'<ol class="forecast-path">'+predicted.map((item,index)=>{const guide=modelGuidance[item.event];return '<li><div class="forecast-marker">'+(index+1)+'</div><article><header><time>'+esc(item.estimated_month)+'</time><span>预测事件</span></header><h3>'+esc(item.event)+'</h3><p>'+esc(guide.copy)+'</p><div class="forecast-actions"><button type="button" data-forecast-action="'+esc(item.event)+'">制定行动 →</button></div></article></li>'}).join('')+'</ol>':'<div class="model-empty"><h3>未来一年暂无预测事件</h3></div>';
  $('#modelPlans').innerHTML=otherPredicted.length?'<section class="forecast-plan-section">'+otherPredicted.map(item=>planForm(item)).join('')+'</section>':'';
  $('#otherEventActions').hidden=!otherPredicted.length;
  $('#otherEventCount').textContent=otherPredicted.length+' 项';
  const recent=result.recent_history||[];
  $('#modelMeta').innerHTML='<div class="model-meta"><dl><div><dt>历史输入</dt><dd>'+esc(result.history_nodes)+' 个事件 · '+esc(result.history_start)+' 至 '+esc(result.history_end)+'</dd></div><div><dt>预测区间</dt><dd>'+esc(result.horizon_start)+' 至 '+esc(result.horizon_end)+'</dd></div><div><dt>模型版本</dt><dd>'+esc(result.model)+'</dd></div></dl>'+(recent.length?'<details><summary>最近5个历史事件</summary><ol class="recent-history">'+recent.map(x=>'<li><time>'+esc(x.date)+'</time><span>'+esc(x.event)+'</span></li>').join('')+'</ol></details>':'')+(absent.length?'<details><summary>其他事件（'+absent.length+'）</summary><p>'+absent.map(x=>esc(x.event)).join('、')+'</p></details>':'')+'</div>';
  renderDatasetPath(result);renderActionSnapshot();
}
async function loadModelForecast(){
  const id=company.id,ticket=++modelRequest;
  $('#modelStatus').textContent='正在整理全部历史并运行模型，首次预测需要加载金融语义模型…';$('#modelSummary').innerHTML='';$('#modelResults').innerHTML='';$('#modelPlans').innerHTML='';$('#otherEventActions').hidden=true;$('#modelMeta').innerHTML='';
  try{
    const result=await api('/api/model-forecast?id='+encodeURIComponent(id));
    if(ticket!==modelRequest||company.id!==id)return;
    if(!result.available){
      $('#modelStatus').textContent='';
      $('#modelResults').innerHTML='<div class="model-empty"><h3>暂时无法预测该企业</h3><p>'+esc(result.reason)+'</p></div>';
      $('#modelMeta').innerHTML=result.as_of?'<p class="muted">资料截止 '+esc(result.as_of)+'。</p>':'';
      renderDatasetPath(null);
      modelLoaded=id;return;
    }
    $('#modelStatus').textContent='';renderModelForecast(result);
    modelLoaded=id;
  }catch(error){
    if(ticket===modelRequest){$('#modelStatus').textContent='模型预测失败：'+error.message;$('#modelResults').innerHTML='<button id="retryModel" class="secondary">重新预测</button>';$('#retryModel').onclick=loadModelForecast;}
  }
}
function openForecastAction(event){
  const context=$('#actionContext');
  if(event==='融资'){context.hidden=false;context.innerHTML='<span>当前事件</span><b>融资</b><p>准备融资方案并选择合适的投资机构。</p>';companySection('actions');tab('plan');requestAnimationFrame(()=>form.scrollIntoView({behavior:'smooth',block:'start'}));return;}
  context.hidden=true;context.innerHTML='';
  companySection('path');
  $('#otherEventActions').open=true;
  requestAnimationFrame(()=>{const plan=[...$('#modelPlans').querySelectorAll('.forecast-plan')].find(item=>item.dataset.event===event);if(plan){plan.closest('.forecast-plan-card').open=true;plan.scrollIntoView({behavior:'smooth',block:'center'});}});
}
$('#modelResults').addEventListener('click',e=>{const button=e.target.closest('[data-forecast-action]');if(button)openForecastAction(button.dataset.forecastAction);});
$('#pathOverview').addEventListener('click',e=>{const button=e.target.closest('[data-path-action]');if(button)openForecastAction(button.dataset.pathAction);});
async function saveForecastPlan(e){const plan=e.target.closest('.forecast-plan');if(!plan)return;e.preventDefault();const button=plan.querySelector('button'),message=plan.querySelector('.plan-save-status'),data=new FormData(plan);button.disabled=true;message.textContent='保存中…';try{const result=await api('/api/action',{type:'forecast_plan',company:plan.dataset.custom==='true'?'founder_custom':company.id,event:plan.dataset.event,status:data.get('status'),due_month:data.get('due_month'),note:data.get('note'),revision:account.revision});account=result.game;message.textContent='已保存';const statusLabel=plan.closest('.forecast-plan-card')?.querySelector('summary em');if(statusLabel)statusLabel.textContent=data.get('status');if(plan.dataset.custom==='true'&&currentCustomForecast)renderCustomForecast(currentCustomForecast);else renderDatasetPath();}catch(error){message.textContent=error.message;}finally{button.disabled=false;}}
$('#modelPlans').addEventListener('submit',saveForecastPlan);
$('#customActionPlans').addEventListener('submit',saveForecastPlan);
let graphCompanyPage=0;
function renderGraphCompanies(){
  const query=$('#graphCompanySearch').value.trim().toLowerCase();
  const rows=account.companies.filter(c=>c.id!==company.id&&(c.name+' '+c.id+' '+c.industry+' '+c.region).toLowerCase().includes(query));
  const pages=Math.max(1,Math.ceil(rows.length/10));graphCompanyPage=Math.min(graphCompanyPage,pages-1);
  $('#graphCompanyName').textContent=company.name;
  $('#ownCompanyGraph').dataset.kgId=company.id;
  $('#graphCompanyCount').textContent=rows.length+' 家其他企业 · 历史资料截至 '+account.meta.cutoff;
  $('#graphCompanyResults').innerHTML=rows.slice(graphCompanyPage*10,graphCompanyPage*10+10).map(c=>'<button type="button" class="result" data-kg-type="company" data-kg-id="'+esc(c.id)+'"><b>'+esc(c.name)+'</b><span>'+esc(c.industry)+' · '+esc(c.region)+' · 查看图谱 →</span></button>').join('')||'<p>没有匹配的企业，请调整搜索。</p>';
  $('#graphCompanyPage').textContent=(graphCompanyPage+1)+' / '+pages;
  $('#graphCompanyPrev').disabled=graphCompanyPage===0;$('#graphCompanyNext').disabled=graphCompanyPage===pages-1;
}
$('#graphCompanySearch').oninput=()=>{graphCompanyPage=0;renderGraphCompanies();};
$('#graphCompanyPrev').onclick=()=>{graphCompanyPage--;renderGraphCompanies();};
$('#graphCompanyNext').onclick=()=>{graphCompanyPage++;renderGraphCompanies();};
$('#graphFindInvestors').onclick=()=>{companySection('finance');tab('find');};
$('#companySections').onclick=e=>{if(e.target.dataset.section&&!e.target.disabled)companySection(e.target.dataset.section);};
async function loadProfile(){
  const id=company.id,ticket=++profileRequest;
  $('#companyProfile').textContent='正在读取企业信息…';$('#officers').textContent='';$('#profileNote').textContent='';
  try{
    const p=await api('/api/company-profile?id='+encodeURIComponent(id));
    if(ticket!==profileRequest||company.id!==id)return;
    const labels={type:'企业类型',province:'所在地区',established:'成立日期',capital:'注册资本',paid_capital:'实缴资本',legal_person:'法定代表人（匿名）'};
    $('#companyProfile').innerHTML='<dl class="profile-grid">'+Object.entries(labels).map(([k,v])=>'<div><dt>'+v+'</dt><dd>'+esc(p.fields[k])+'</dd></div>').join('')+'</dl>';
    $('#profileNote').textContent=p.note+' 来源：'+p.source;
    $('#officers').innerHTML=p.officers.map(x=>'<article class="record"><b>'+esc(x.name)+' · '+esc(x.position)+'</b><p>'+esc(x.status)+'</p><p class="muted">'+(x.start?'收录于 '+esc(x.start):'收录日期未明确')+(x.end?' · 离任 '+esc(x.end):'')+'</p></article>').join('')||'<p>暂无已收录人员信息，不代表企业没有员工。</p>';
    if(!p.officers.length)$('#officers').innerHTML='<p>暂无人员记录。</p>';
    profileLoaded=id;
  }catch(e){if(ticket===profileRequest){$('#companyProfile').textContent=e.message;$('#officers').innerHTML='<button id="retryProfile" class="secondary">重新读取</button>';$('#retryProfile').onclick=loadProfile;}}
}
let activeActionTab='plan';
function renderActionSnapshot(){
  if(!company||!account){$('#actionSnapshot').innerHTML='';return;}
  const plan=account.founder_plans?.[company.id]||{};
  const institutionCount=Object.keys(account.founder_contacts?.[company.id]||{}).length;
  const round=account.founder_rounds?.[company.id];
  const planReady=plan.target>0&&plan.pre_money>0&&plan.cash!=null&&plan.burn!=null&&Boolean(plan.purpose?.trim());
  const institutionsReady=institutionCount>0;
  const next=!planReady
    ?{step:'plan',title:'完善融资方案',copy:'填写现金、融资目标、估值和资金用途。',button:'开始准备'}
    :!institutionsReady
      ?{step:'find',title:'选择目标机构',copy:'从机构池中筛选并加入本轮接触名单。',button:'选择机构'}
      :{step:'contacts',title:'查看融资后的发展路径',copy:'基于融资方案和目标机构，生成新的未来一年。',button:'生成新路径'};
  const progress=[
    {step:'plan',number:'01',label:'融资准备',state:planReady?'方案已完成':'待填写方案',done:planReady},
    {step:'find',number:'02',label:'选择机构',state:institutionsReady?'已选 '+institutionCount+' 家':'待选择机构',done:institutionsReady},
    {step:'contacts',number:'03',label:'新发展路径',state:round?'融资进行中':scenarioReady?'路径已生成':institutionsReady?'可以生成':'等待前两步',done:scenarioReady}
  ];
  $('#actionSnapshot').innerHTML='<section class="action-next"><small>下一步</small><h3>'+next.title+'</h3><p>'+next.copy+'</p><button type="button" data-open-action="'+next.step+'">'+next.button+' →</button></section><ol id="tabs" class="action-progress" aria-label="融资流程">'+progress.map(item=>'<li class="'+(item.done?'done ':'')+(item.step===next.step?'current ':'')+(item.step===activeActionTab?'viewing':'')+'"><button type="button" data-tab="'+item.step+'"'+(item.step===activeActionTab?' aria-current="step"':'')+'><span>'+item.number+'</span><div><small>'+item.label+'</small><b>'+item.state+'</b></div></button></li>').join('')+'</ol>';
}
function tab(name){
  activeActionTab=name;
  for(const key of ['plan','find','contacts'])$('#'+key+'Panel').hidden=key!==name;
  renderActionSnapshot();
  if(name==='contacts')loadFinancingScenario();
}
$('#actionSnapshot').onclick=e=>{const button=e.target.closest('[data-open-action],[data-tab]');if(button)tab(button.dataset.openAction||button.dataset.tab);};
$('[data-back-to-path]').onclick=e=>{e.preventDefault();companySection('path');};
const form=$('#planForm');
const money=(v,c)=>v==null?'金额未披露':(c==='CNY'?'¥':c==='USD'?'$':(c||''))+Number(v).toLocaleString('zh-CN');
async function api(path,body){
  const response=await fetch(path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});
  const result=await response.json();
  if(result.game?.static_state_omitted&&account){
    result.game.companies=account.companies;result.game.market=account.market;
    delete result.game.static_state_omitted;
  }
  if(!response.ok){if(result.game)account=result.game;throw Error(result.error||'读取失败，请重试');}
  return result;
}
function status(text=''){$('#status').textContent=text;}
function financingInfo(r){
  const amount=r.amount==null?'融资金额未披露':'本轮融资 '+money(r.amount,r.currency);
  const industry=r.industry&&r.industry!=='未披露'?' · '+r.industry:'';
  return '<small>'+esc(amount+industry)+'</small>';
}
let institutionPage=1,poolRequest=0,poolTimer;
let investorId=null,investorPage=1,investorRequest=0;
async function investorDetail(id,page=1){
  investorId=id;const ticket=++investorRequest;
  const dialog=$('#investorDialog');if(!dialog.open)dialog.showModal();
  $('#investorTitle').textContent='投资人详情';$('#investorSummary').textContent='正在读取…';$('#investorCases').innerHTML='';$('#investorPrev').disabled=true;$('#investorNext').disabled=true;
  try{
    const r=await api('/api/institution?'+new URLSearchParams({id,page}));if(ticket!==investorRequest)return;
    investorPage=r.page;$('#investorTitle').textContent=r.name;$('#investorSummary').textContent='已收录 '+r.company_count+' 家企业 · '+r.total+' 次融资案例 · 截至 '+r.cutoff;
    $('#investorCases').innerHTML='<section class="kg-entry"><div><h3>投资人知识图谱</h3><p>查看参与的融资轮次，继续探索被投企业。</p></div><button type="button" class="kg-entry-action" data-kg-type="institution" data-kg-id="'+esc(id)+'">查看投资网络 →</button></section>'+(r.items.map(x=>'<article class="record"><b>'+esc(x.company)+'</b><p>'+esc(x.stage)+' · '+esc(x.event_date)+'</p>'+financingInfo(x)+'</article>').join('')||'<p>暂无已收录案例</p>');
    $('#investorPage').textContent=r.page+' / '+r.pages;$('#investorPrev').disabled=r.page===1;$('#investorNext').disabled=r.page===r.pages;
  }catch(e){if(ticket===investorRequest){$('#investorSummary').textContent=e.message;$('#investorPage').textContent='';}}
}
$('#investorClose').onclick=()=>$('#investorDialog').close();$('#investorDialog').addEventListener('close',()=>{investorRequest++;});
$('#investorPrev').onclick=()=>investorDetail(investorId,investorPage-1);$('#investorNext').onclick=()=>investorDetail(investorId,investorPage+1);
$('#institutions').addEventListener('click',e=>{const b=e.target.closest('[data-investor]');if(b)investorDetail(b.dataset.investor);});
function renderSelectedInstitutions(){
  if(!company)return;
  const rows=Object.values(account.founder_contacts?.[company.id]||{});
  $('#selectedInstitutionBar').innerHTML=rows.length?'<div><span>已选择 '+rows.length+' 家</span><div class="selected-chips">'+rows.map(item=>'<span>'+esc(item.name)+'<button type="button" data-remove-contact="'+esc(item.id)+'" aria-label="移出 '+esc(item.name)+'">×</button></span>').join('')+'</div></div>':'<div><span>尚未选择机构</span><p>至少选择一家机构后生成新的发展路径。</p></div>';
  $('#generateScenario').disabled=!rows.length;
}
async function renderInstitutions(){
  if(!company)return;const ticket=++poolRequest,cid=company.id;
  renderSelectedInstitutions();
  $('#institutionCount').textContent='正在读取机构池…';$('#institutions').innerHTML='';
  $('#institutionPrev').disabled=true;$('#institutionNext').disabled=true;
  try{
    const params=new URLSearchParams({company:cid,q:$('#institutionSearch').value,scope:$('#institutionScope').value,sort:$('#institutionSort').value,page:institutionPage});
    const result=await api('/api/institutions?'+params);if(ticket!==poolRequest||company.id!==cid)return;
    institutionPage=result.page;const saved=account.founder_contacts?.[cid]||{};
    $('#institutionCount').textContent=result.total+' 个机构 / 投资人';$('#institutionPage').textContent=result.page+' / '+result.pages;
    $('#institutionPrev').disabled=result.page===1;$('#institutionNext').disabled=result.page===result.pages;
    $('#institutions').innerHTML=result.items.map(i=>'<article class="institution-card"><h3><button class="investor-name" data-investor="'+esc(i.id)+'">'+esc(i.name)+'</button></h3><p class="match">'+(i.stage_count?'投过 '+i.stage_count+' 家同业同阶段企业':i.industry_count?'投过 '+i.industry_count+' 家同行业企业':'暂无同行业记录')+'</p><p class="muted">历史投资 '+i.company_count+' 家 · 最近记录 '+esc(i.latest)+'</p><button data-add="'+esc(i.id)+'" '+(saved[i.id]?'disabled':'')+'>'+(saved[i.id]?'已选择':'选择该机构')+'</button></article>').join('')||'<p>没有匹配结果，请调整搜索或筛选。</p>';
  }catch(error){if(ticket===poolRequest){$('#institutionCount').textContent=error.message;$('#institutionPage').textContent='';}}
}
$('#institutionSearch').oninput=()=>{clearTimeout(poolTimer);poolRequest++;poolTimer=setTimeout(()=>{institutionPage=1;renderInstitutions();},200);};
for(const id of ['institutionScope','institutionSort'])$('#'+id).onchange=()=>{institutionPage=1;renderInstitutions();};
$('#institutionPrev').onclick=()=>{institutionPage--;renderInstitutions();};$('#institutionNext').onclick=()=>{institutionPage++;renderInstitutions();};
function renderContacts(){
  const rows=Object.values(account.founder_contacts?.[company.id]||{}),r=account.founder_rounds?.[company.id];
  const plan=account.founder_plans?.[company.id],cur=r?.currency||plan?.currency||account.currency;
  $('#financingSummary').textContent=r?'模拟日期 '+r.date+' · 已到账 '+money(r.raised,cur)+' / '+money(r.target,cur)+' · 企业现金 '+money(r.cash,cur)+' · 原股东合计 '+((r.original_ownership??1)*100).toFixed(2)+'%':'先在“融资方案”保存融资目标、用途、现金与模拟投前估值，再向名单中的机构提交。';
  $('#financingWeek').disabled=!r||saving||!Object.values(r.applications).some(a=>['submitted','accepted'].includes(a.status));
  $('#financingLedger').innerHTML=(r?.ledger||[]).slice().reverse().map(x=>'<p>'+esc(x.date)+' · '+esc(x.text)+'</p>').join('')||'<p>暂无融资操作</p>';
  const names={submitted:'评审中',materials:'待补材料',rejected:'未通过',terms:'待确认条款',accepted:'待交割',settled:'已到账',declined:'已拒绝条款'};
  $('#contacts').innerHTML=rows.map(i=>{
    const a=r?.applications[i.id],canSubmit=!a||['materials','rejected','declined'].includes(a.status);
    const reserved=r?Object.values(r.applications).filter(x=>['accepted','settled'].includes(x.status)).reduce((sum,x)=>sum+x.amount,0):0;
    return '<article class="record contact"><h3>'+esc(i.name)+' · '+(a?names[a.status]:'未提交')+'</h3><button type="button" class="secondary" data-kg-type="institution" data-kg-id="'+esc(i.id)+'">查看投资人图谱</button><p>'+esc(a?.feedback||'尚未提交')+'</p>'+
      (canSubmit?'<label>向该机构申请金额（'+cur+'）<input type="number" min="0.01" step="0.01" data-ticket="'+esc(i.id)+'" placeholder="填写本轮拟由该机构认购的金额"></label><button data-finance="submit" data-iid="'+esc(i.id)+'">提交融资方案</button>':'')+
      (a?.status==='terms'?'<p>模拟投资 '+money(a.amount,cur)+' · 本轮投前估值 '+money(r.pre_money,cur)+'</p><p>按已确认金额加本笔测算，本机构持股 '+(a.amount/(r.pre_money+reserved+a.amount)*100).toFixed(2)+'%；本轮全部募足后 '+(a.amount/(r.pre_money+r.target)*100).toFixed(2)+'%。后续同轮交割会继续稀释。</p><button data-finance="accept" data-iid="'+esc(i.id)+'">接受条款</button> <button class="secondary" data-finance="decline" data-iid="'+esc(i.id)+'">拒绝条款</button>':'')+
      (a?.status==='settled'?'<p>已到账 '+money(a.amount,cur)+' · 当前模拟持股 '+(a.ownership*100).toFixed(2)+'%</p>':'')+
      '<p class="finance-error" role="alert"></p><button class="secondary" data-complete-plan hidden>补全融资计划 →</button><p class="muted">'+esc(i.note||'')+'</p></article>';
  }).join('')||'<p>先去机构池选择机构并加入名单。</p>';
  renderActionSnapshot();
}
function scenarioNames(items){return items.length?items.map(item=>'<span>'+esc(item)+'</span>').join(''):'<span class="empty">无</span>';}
function renderFinancingScenario(result){
  if(!result.ready){
    scenarioReady=false;renderActionSnapshot();
    const missing=result.missing||[];
    $('#scenarioStatus').innerHTML='<b>完成前两步后生成新路径</b><p>还需补充：'+esc(missing.join('、')||'融资准备与目标机构')+'</p>';
    $('#scenarioInputs').innerHTML='<div class="scenario-prerequisites"><button type="button" data-scenario-go="plan">完善融资准备 →</button><button type="button" class="secondary" data-scenario-go="find">选择目标机构 →</button></div>';
    $('#scenarioComparison').innerHTML='';$('#scenarioPath').innerHTML='';return;
  }
  const forecast=result.forecast||{},baseline=result.baseline||{};
  if(forecast.available===false){
    scenarioReady=false;renderActionSnapshot();
    $('#scenarioStatus').innerHTML='<b>暂未生成新的未来路径</b><p>'+esc(forecast.reason||'当前企业历史信息不足')+'</p>';
    $('#scenarioInputs').innerHTML='';$('#scenarioComparison').innerHTML='';$('#scenarioPath').innerHTML='';return;
  }
  const selected=result.institutions||[],plan=result.plan||{};
  scenarioReady=true;renderActionSnapshot();
  $('#scenarioStatus').innerHTML='<b>未来一年路径已更新</b><p>'+esc(forecast.horizon_start)+' — '+esc(forecast.horizon_end)+' · 已读取 '+Number(forecast.history_nodes||0).toLocaleString('zh-CN')+' 条历史与融资情景事件</p>';
  $('#scenarioInputs').innerHTML='<section class="scenario-inputs"><div><small>融资准备</small><b>目标 '+esc(money(plan.target,plan.currency))+'</b><p>投前估值 '+esc(money(plan.pre_money,plan.currency))+' · '+esc(plan.purpose)+'</p></div><div><small>选择机构</small><b>'+selected.length+' 家机构加入本次路径</b><p>'+esc(selected.map(item=>item.name).join('、'))+'</p></div></section>';
  const original=new Set((baseline.events||[]).filter(item=>item.predicted).map(item=>item.event));
  const updated=new Set((forecast.events||[]).filter(item=>item.predicted).map(item=>item.event));
  const added=[...updated].filter(item=>!original.has(item)),kept=[...updated].filter(item=>original.has(item)),removed=[...original].filter(item=>!updated.has(item));
  $('#scenarioComparison').innerHTML='<details class="path-changes"><summary>查看相对原路径的变化</summary><section class="scenario-comparison"><div class="added"><small>新增事件</small>'+scenarioNames(added)+'</div><div><small>保持不变</small>'+scenarioNames(kept)+'</div><div class="removed"><small>不再出现</small>'+scenarioNames(removed)+'</div></section></details>';
  const future=(forecast.events||[]).filter(item=>item.predicted).sort((a,b)=>a.month_index-b.month_index);
  $('#scenarioPath').innerHTML='<section class="scenario-path"><div class="scenario-path-title"><div><p class="eyebrow">新的未来一年</p><h3>企业发展路径</h3></div><b>'+future.length+' 个预测事件</b></div>'+(future.length?'<ol>'+future.map((item,index)=>'<li><i>'+(index+1)+'</i><time>'+esc(item.estimated_month)+'</time><strong>'+esc(item.event)+'</strong><small>预计第 '+item.month_index+' 个月发生</small></li>').join('')+'</ol>':'<div class="scenario-empty"><b>未来一年暂无预测事件</b></div>')+'<div class="scenario-decision"><button type="button" data-adopt-scenario>采用该方案，开始融资 →</button><button type="button" class="secondary" data-scenario-go="plan">返回调整方案</button></div></section>';
}
async function loadFinancingScenario(force=false){
  if(!company)return;
  const key=company.id+':'+account.revision;
  if(!force&&scenarioLoadedKey===key)return;
  const id=company.id,ticket=++scenarioRequest;
  $('#scenarioStatus').innerHTML='<b>正在生成新的未来路径…</b><p>模型正在读取企业完整历史、融资准备和已选机构。</p>';
  $('#scenarioInputs').innerHTML='';$('#scenarioComparison').innerHTML='';$('#scenarioPath').innerHTML='';$('#scenarioRefresh').disabled=true;
  try{
    const result=await api('/api/financing-scenario-forecast?id='+encodeURIComponent(id));
    if(ticket!==scenarioRequest||!company||company.id!==id)return;
    scenarioLoadedKey=key;renderFinancingScenario(result);
  }catch(error){if(ticket===scenarioRequest){$('#scenarioStatus').innerHTML='<b>路径生成未完成</b><p>'+esc(error.message)+'</p>';}}
  finally{if(ticket===scenarioRequest)$('#scenarioRefresh').disabled=false;}
}
$('#scenarioRefresh').onclick=()=>loadFinancingScenario(true);
$('#scenarioInputs').onclick=e=>{const button=e.target.closest('[data-scenario-go]');if(button)tab(button.dataset.scenarioGo);};
$('#scenarioPath').onclick=e=>{const step=e.target.closest('[data-scenario-go]');if(step){tab(step.dataset.scenarioGo);return;}if(e.target.closest('[data-adopt-scenario]')){const execution=$('.financing-execution');execution.open=true;execution.scrollIntoView({behavior:'smooth',block:'start'});}};
async function financeAction(type,iid,amount){
  if(saving)return;
  const card=[...document.querySelectorAll('.contact')].find(c=>c.querySelector('[data-iid]')?.dataset.iid===iid);
  const fail=(message,planLink=false)=>{status(message);if(card){card.querySelector('.finance-error').textContent=message;card.querySelector('[data-complete-plan]').hidden=!planLink;}else{$('#financingSummary').textContent=message;}};
  if(dirty){fail('融资方案有未保存的修改，请先保存。',true);return;}
  if(type==='submit'&&!account.founder_rounds?.[company.id]){
    const p=account.founder_plans?.[company.id]||{},missing=[];
    if(!(p.target>0))missing.push('融资目标');if(!(p.pre_money>0))missing.push('模拟投前估值');if(p.cash==null)missing.push('企业现金');if(p.burn==null)missing.push('月均净支出');if(!p.purpose?.trim())missing.push('资金用途');
    if(missing.length){fail('尚未提交：请先填写并保存'+missing.join('、')+'。',true);return;}
  }
  saving=true;$('#financingWeek').disabled=true;
  card?.querySelectorAll('button').forEach(b=>b.disabled=true);
  let success=false;
  try{const result=await api('/api/action',{type:'financing_'+type,company:company.id,institution:iid,amount,revision:account.revision});account=result.game;success=true;status(type==='submit'?'提交成功，推进一周查看反馈。':'模拟融资进度已更新');}
  catch(error){fail(error.message);}
  finally{saving=false;if(success){renderContacts();preview();scenarioLoadedKey='';loadFinancingScenario(true);}else{card?.querySelectorAll('button').forEach(b=>b.disabled=false);const r=account.founder_rounds?.[company.id];$('#financingWeek').disabled=!r||!Object.values(r.applications).some(a=>['submitted','accepted'].includes(a.status));}}
}
$('#financingWeek').onclick=()=>financeAction('week');
$('#contacts').onclick=e=>{
  if(e.target.closest('[data-complete-plan]')){tab('plan');form.scrollIntoView({behavior:'smooth',block:'start'});return;}
  const b=e.target.closest('[data-finance]');if(!b)return;
  const input=b.closest('.contact').querySelector('[data-ticket]');
  if(b.dataset.finance==='submit'&&(!input.value||!input.checkValidity())){input.reportValidity();b.closest('.contact').querySelector('.finance-error').textContent='请填写大于零、最多两位小数的申请金额。';return;}
  financeAction(b.dataset.finance,b.dataset.iid,input?Number(input.value):undefined);
};
async function contactSave(iid,stage,note){const r=await api('/api/action',{type:'founder_contact',company:company.id,institution:iid,stage,note,revision:account.revision});account=r.game;}
$('#institutions').onclick=async e=>{const b=e.target.closest('[data-add]');if(!b||saving)return;saving=true;b.disabled=true;try{await contactSave(b.dataset.add,'待接触','');scenarioReady=false;renderInstitutions();renderContacts();status('已加入目标机构');}catch(error){status(error.message);b.disabled=false;}finally{saving=false;}};
$('#selectedInstitutionBar').onclick=async e=>{const button=e.target.closest('[data-remove-contact]');if(!button||saving)return;saving=true;button.disabled=true;try{const result=await api('/api/action',{type:'founder_contact_remove',company:company.id,institution:button.dataset.removeContact,revision:account.revision});account=result.game;scenarioLoadedKey='';scenarioReady=false;renderInstitutions();renderContacts();status('已移出目标机构');}catch(error){status(error.message);button.disabled=false;}finally{saving=false;}};
$('#generateScenario').onclick=()=>tab('contacts');
function list(){
  const q=$('#search').value.trim().toLowerCase();
  const rows=account.companies.filter(c=>(c.name+' '+c.id+' '+c.industry+' '+c.region).toLowerCase().includes(q));
  const pages=Math.max(1,Math.ceil(rows.length/12));page=Math.min(page,pages-1);
  $('#searchCount').textContent=rows.length+' 家企业';
  $('#results').innerHTML=rows.slice(page*12,page*12+12).map(c=>'<button class="result" data-id="'+esc(c.id)+'"><b>'+esc(c.name)+'</b><span>'+esc(c.industry)+' · '+esc(c.latest.stage)+(c.closed?' · 注销或吊销记录':'')+'</span></button>').join('')||'<p>没有匹配企业</p>';
  $('#page').textContent=(page+1)+' / '+pages;$('#prev').disabled=page===0;$('#next').disabled=page===pages-1;
}
function draft(){
  const data=new FormData(form),purposeLabels={research:'产品研发',hiring:'团队招聘',marketing:'市场拓展',other:'其他用途'},categories=data.getAll('purpose_categories'),detail=String(data.get('purpose_detail')||'').trim();
  const p={currency:data.get('currency'),purpose_categories:categories,purpose_detail:detail,materials:[],goal,months:18};
  for(const key of ['cash','burn','target','pre_money'])p[key]=data.get(key)===''?null:Number(data.get(key));
  p.purpose=categories.map(key=>purposeLabels[key]).join('、')+(detail?'；'+detail:'');
  p.budget=Object.fromEntries(['research','hiring','marketing','other'].map(key=>[key,0]));
  if(p.target&&categories.length){const share=Math.floor(p.target*100/categories.length)/100;categories.forEach(key=>p.budget[key]=share);p.budget[categories.at(-1)]=Math.round((p.target-share*(categories.length-1))*100)/100;}
  return p;
}
function guidance(p){
  const settled=account.founder_rounds?.[company.id];
  if(settled)p={...p,cash:settled.cash};
  let runway='待填写现金数据',note='可用现金 ÷ 月净现金消耗。';
  if(p.cash!=null&&p.burn!=null){
    if(p.burn===0){runway='暂无净现金消耗';note='月净消耗填写为零，暂不计算资金可用月数。';}
    else if(p.cash/p.burn>120){runway='资金可用期异常';note='超过十年分析范围，请核对现金和月净消耗的金额单位；不作为经营优势。';}
    else runway=(p.cash/p.burn).toFixed(1)+' 个月资金可用期';
  }
  const actions=[];
  if(company.closed)actions.push('企业有注销或吊销记录，处理主体状态。');
  if(p.cash==null||p.burn==null)actions.push('补充现金余额和月净消耗，判断资金可用期。');
  else if(p.burn>0&&p.cash/p.burn<6)actions.push('按当前消耗，现金不足六个月：优先核实支出预算，并准备资金衔接方案。');
  if(!(p.target>0)||!p.purpose.trim())actions.push('补充融资金额和资金用途。');
  if(company.risks.at(-1)?.type==='abnormal_listing')actions.push('核实经营异常原因及处理状态，准备说明材料。');
  if(!actions.length)actions.push('当前融资方案信息完整。');
  return {runway,note,actions};
}
function preview(){
  if(!company)return;const p=draft();if(account.founder_rounds?.[company.id])p.cash=account.founder_rounds[company.id].cash;const g=guidance(p),validBurn=p.burn!=null&&p.burn>0;
  $('#runway').textContent=p.cash!=null&&validBurn?(p.cash/p.burn).toFixed(1)+' 个月':p.burn===0?'暂无净现金支出':'待计算';
  $('#postRunway').textContent=p.cash!=null&&p.target!=null&&validBurn?((p.cash+p.target)/p.burn).toFixed(1)+' 个月':p.burn===0?'暂无净现金支出':'待计算';
  $('#dilution').textContent=p.target>0&&p.pre_money>0?(p.target/(p.pre_money+p.target)*100).toFixed(1)+'%':'待计算';
  $('#runwayNote').textContent=g.note;$('#priorities').innerHTML=g.actions.map(t=>'<li>'+esc(t)+'</li>').join('');
}
async function selectCompany(id){
  if(saving)return;
  if(dirty&&!confirm('有未保存的修改，是否放弃并切换企业？'))return;
  const ticket=++requestId;status('正在读取企业资料…');
  try{
    const result=await api('/api/company?id='+encodeURIComponent(id));if(ticket!==requestId)return;
    company=result.company;dirty=false;form.reset();profileRequest++;profileLoaded=null;modelRequest++;modelLoaded=null;currentModelForecast=null;scenarioRequest++;scenarioLoadedKey='';scenarioReady=false;graphCompanyPage=0;$('#customSection').hidden=true;$('#customActionsSection').hidden=true;$('#customEvidenceSection').hidden=true;renderDatasetPath();
    showFounderMode('dataset');
    $('#sidebarCompany').textContent=company.name;
    document.querySelectorAll('[data-section]').forEach(b=>{b.hidden=false;b.disabled=false;b.title='';});
    const p=account.founder_plans?.[id]||{currency:account.currency};
    tab(account.founder_rounds?.[id]?'contacts':'plan');
    institutionPage=1;renderInstitutions();renderContacts();
    for(const key of ['currency','cash','burn','target','pre_money'])form.elements[key].value=p[key]??(key==='currency'?account.currency:'');
    let categories=p.purpose_categories||['research','hiring','marketing','other'].filter(key=>p.budget?.[key]>0),detail=p.purpose_detail||'';
    if(!categories.length&&p.purpose){categories=['other'];detail=p.purpose;}
    for(const input of form.querySelectorAll('[name=purpose_categories]'))input.checked=categories.includes(input.value);
    form.elements.purpose_detail.value=detail;
    form.elements.cash.readOnly=!!account.founder_rounds?.[id];
    for(const input of form.querySelectorAll('[name=materials]'))input.checked=(p.materials||[]).includes(input.value);
    $('#companyName').textContent=company.name;$('#companyMeta').textContent=company.industry+' · '+company.region;
    $('#stage').textContent=company.latest.stage;$('#funding').textContent=company.history.length+' 次';
    $('#risk').textContent=company.closed?'注销或吊销记录':company.risks.at(-1)?.type==='abnormal_listing'?'存在经营异常':company.risks.length?'异常已移出':'未收录异常';
    $('#risk').classList.toggle('risk',company.closed||company.risks.at(-1)?.type==='abnormal_listing');
    $('#cutoff').textContent='历史资料截至 '+account.meta.cutoff+'；经营数据为用户自报，两者分别记录。';
    $('#history').innerHTML=[...company.history].reverse().map(r=>'<div class="record"><b>'+esc(r.date)+' · '+esc(r.stage)+'</b><p>'+esc(money(r.amount,r.currency))+'</p><small>融资历史记录'+(r.publication_proxy?' · 披露日期未提供':'')+'</small></div>').join('')||'<p>暂无融资记录。</p>';
    $('#history').innerHTML+=[...company.risks].reverse().map(r=>'<p class="risk">'+esc(r.date)+' · '+(r.type==='abnormal_listing'?'列入':'移出')+'经营异常名录</p>').join('');
    const ref=company.comparison;
    $('#peers').textContent=ref?.median_amount?'同业、同阶段、同币种 '+ref.n+' 家企业最近披露融资金额中位数：'+money(ref.median_amount,ref.currency)+'。':'可比金额样本不足。';
    $('#pastFunding').innerHTML=fundingVisual(company.history);
    $('#pastPeers').textContent=$('#peers').textContent;
    $('#overviewRisks').innerHTML=[...company.risks].reverse().map(r=>'<p>'+esc(r.date)+' · '+(r.type==='abnormal_listing'?'列入':'移出')+'经营异常名录</p>').join('')||'<p>暂无经营异常记录。</p>';
    $('#picker').hidden=true;$('#actionContext').hidden=true;$('#actionContext').innerHTML='';companySection('path');$('#saveStatus').textContent=p.source?'已读取保存的计划':'';preview();status();
  }catch(error){status(error.message);}
}
function enter(){ $('#entry').hidden=true;$('#workspace').hidden=false;list();status(); }
$('#search').oninput=()=>{page=0;list();};
$('#prev').onclick=()=>{page--;list();};$('#next').onclick=()=>{page++;list();};
$('#results').onclick=e=>{const b=e.target.closest('[data-id]');if(b)selectCompany(b.dataset.id);};
$('#change').onclick=()=>openDataset(true).catch(error=>status(error.message));
$('#buildOwnExisting').onclick=()=>openCustom(true).catch(error=>status(error.message));
$('#customCategory').onchange=renderCustomSubtypes;
$('#customProfileForm').onsubmit=async e=>{
  e.preventDefault();if(saving)return;saving=true;const button=e.target.querySelector('button'),data=new FormData(e.target);button.disabled=true;$('#customProfileStatus').textContent='保存中…';
  try{const result=await api('/api/action',{type:'founder_custom_profile',name:data.get('name'),industry:data.get('industry'),region:data.get('region'),revision:account.revision});account=result.game;renderCustomPath();$('#companyName').textContent=data.get('name');$('#sidebarCompany').textContent=data.get('name');$('#customProfileStatus').textContent='已保存';}
  catch(error){$('#customProfileStatus').textContent=error.message;}finally{saving=false;button.disabled=false;}
};
$('#customEventForm').onsubmit=async e=>{
  e.preventDefault();if(saving)return;saving=true;const button=e.target.querySelector('button'),data=new FormData(e.target);button.disabled=true;
  try{const result=await api('/api/action',{type:'founder_custom_event_add',date:data.get('date'),category:data.get('category'),subtype:data.get('subtype'),revision:account.revision});account=result.game;renderCustomPath();invalidateCustomForecast();status('历史事件已加入路径；请重新预测');}
  catch(error){status(error.message);}finally{saving=false;button.disabled=false;}
};
$('#customTimeline').onclick=async e=>{
  const button=e.target.closest('[data-delete-custom-event]');if(!button||saving)return;saving=true;button.disabled=true;
  try{const result=await api('/api/action',{type:'founder_custom_event_delete',event_id:button.dataset.deleteCustomEvent,revision:account.revision});account=result.game;renderCustomPath();invalidateCustomForecast();status('历史事件已删除；请重新预测');}
  catch(error){status(error.message);button.disabled=false;}finally{saving=false;}
};
$('#customPredict').onclick=async()=>{
  const ticket=++customPredictRequest,steps=['正在整理全部历史事件…','正在编码企业事件序列…','正在生成未来一年路径…','正在检索相似企业…'];let step=0;
  $('#customPredict').disabled=true;$('#customPredictStatus').textContent=steps[0];$('#customForecastResults').innerHTML='';$('#customSimilarResults').innerHTML='';
  const progress=setInterval(()=>{if(ticket===customPredictRequest&&step<steps.length-1)$('#customPredictStatus').textContent=steps[++step];},7000);
  try{const result=await api('/api/custom-forecast');if(ticket!==customPredictRequest)return;renderCustomForecast(result);$('#customPredictStatus').textContent='预测完成';status('');}
  catch(error){if(ticket===customPredictRequest)$('#customPredictStatus').textContent=error.message;}finally{clearInterval(progress);if(ticket===customPredictRequest)$('#customPredict').disabled=!(account.founder_custom?.events||[]).length;}
};
function invalidateCustomForecast(){currentCustomForecast=null;customPredictRequest++;$('#customForecastResults').innerHTML='';$('#customSimilarResults').innerHTML='';renderCustomActions();renderCustomEvidence();}
$('#customForecastResults').onclick=e=>{const button=e.target.closest('[data-custom-action]');if(!button)return;setFounderSection('actions');renderCustomActions(button.dataset.customAction);$('#customActionPlans').scrollIntoView({behavior:'smooth'});};
$('#customBackToPath').onclick=()=>setFounderSection('path');
$('#customFinanceForm').oninput=()=>{customFinanceDirty=true;updateCustomRunway();};
$('#customFinanceForm').onsubmit=async e=>{e.preventDefault();const f=e.target,data=new FormData(f),button=f.querySelector('button[type=submit]');button.disabled=true;$('#customFinanceStatus').textContent='保存中…';try{const result=await api('/api/action',{type:'founder_custom_finance_plan',currency:data.get('currency'),target:data.get('target'),cash:data.get('cash'),burn:data.get('burn'),purpose:data.get('purpose'),revision:account.revision});account=result.game;customFinanceDirty=false;$('#customFinanceStatus').textContent='融资准备已保存';updateCustomRunway();}catch(error){$('#customFinanceStatus').textContent=error.message;}finally{button.disabled=false;}};
$('#customSimilarResults').onclick=async e=>{const button=e.target.closest('[data-custom-reference]');if(!button)return;try{await setFounderMode('dataset');await selectCompany(button.dataset.customReference);}catch(error){status(error.message);}};
form.oninput=()=>{dirty=true;$('#saveStatus').textContent='有未保存的修改';$('#purposeError').textContent='';preview();};
form.onsubmit=async e=>{
  e.preventDefault();if(saving||!company)return;
  const plan=draft();if(!plan.purpose_categories.length){$('#purposeError').textContent='请选择至少一项资金用途。';return;}saving=true;
  const cid=company.id;form.querySelectorAll('input,select,textarea,button').forEach(el=>el.disabled=true);$('#export').disabled=true;
  try{const r=await api('/api/action',{type:'founder_plan',company:cid,plan,revision:account.revision});account=r.game;dirty=false;$('#saveStatus').textContent='方案已保存';scenarioLoadedKey='';scenarioReady=false;renderActionSnapshot();status();tab('find');}
  catch(error){$('#saveStatus').textContent='未保存';status(error.message+'；当前输入已保留，可重新保存。');}
  finally{saving=false;form.querySelectorAll('input,select,textarea,button').forEach(el=>el.disabled=false);$('#export').disabled=false;}
};
$('#export').onclick=()=>{
  if(!company)return;const p=draft(),g=guidance(p);
  const dilution=p.target>0&&p.pre_money>0?(p.target/(p.pre_money+p.target)*100).toFixed(1)+'%':'待计算';
  const text=[company.name+' · 融资方案','历史截止：'+account.meta.cutoff,'以下经营数据为用户自报'+(dirty?'（未保存草稿）':''),'币种：'+p.currency,'可用现金：'+money(p.cash,p.currency),'月均净支出：'+money(p.burn,p.currency),'目标融资：'+money(p.target,p.currency),'投前估值：'+money(p.pre_money,p.currency),'资金用途：'+(p.purpose||'未填写'),'预计股权稀释：'+dilution,'',...g.actions].join('\n');
  const url=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='融资方案.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
window.addEventListener('beforeunload',e=>{if(dirty||saving){e.preventDefault();e.returnValue='';}});
async function begin(mode,button){button.disabled=true;try{const r=await api('/api/new',{name:'企业工作台'});account=r.game;enter();if(mode==='custom')await openCustom(true);else await openDataset(true);}catch(error){status(error.message);}finally{button.disabled=false;}}
$('#start').onclick=()=>begin('dataset',$('#start'));$('#buildOwn').onclick=()=>begin('custom',$('#buildOwn'));
(async()=>{try{const r=await api('/api/game');account=r.game;if(account){enter();if(account.founder_mode==='custom')await openCustom(false);else if(account.founder_company)await selectCompany(account.founder_company);else await openDataset(false);}else{$('#entry').hidden=false;status(r.legacy?'旧账户将保留，进入企业端会创建独立新版工作台。':'');}}catch(e){status(e.message);}})();

'use strict';
const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const labels={financials:'财务与现金流记录',use_of_funds:'上轮资金使用与本轮预算',cap_table:'股权结构与股东信息',team:'团队与关键岗位信息',risk_explanation:'风险事项说明'};
let account=null,company=null,page=0,requestId=0,dirty=false,saving=false;
let goal='prepare';
function fundingVisual(history){
  if(!history.length)return '<p>暂无融资记录，不代表从未融资。</p>';
  const rows=[...history].sort((a,b)=>a.date.localeCompare(b.date)||String(a.id||'').localeCompare(String(b.id||'')));
  const charts=['CNY','USD'].map(currency=>{
    const known=rows.filter(r=>r.currency===currency&&!r.conflict&&Number.isFinite(r.amount)&&r.amount>0);
    if(known.length<2)return '';
    const maximum=Math.max(...known.map(r=>r.amount));
    return '<section class="funding-amount-chart" aria-label="'+(currency==='CNY'?'人民币':'美元')+'融资金额比较"><h3>各轮融资金额 · '+currency+'</h3><p class="muted">仅显示金额明确的记录，不代表估值；横条按金额比例绘制。</p>'+known.map(r=>'<div class="funding-bar-row"><div class="funding-bar-label"><span>'+esc(r.date)+' · '+esc(r.stage)+'</span><strong>'+esc(money(r.amount,currency))+'</strong></div><div class="funding-bar-track" aria-hidden="true"><div class="funding-bar" style="width:'+(r.amount/maximum*100).toFixed(4)+'%"></div></div></div>').join('')+'</section>';
  }).join('');
  return charts+'<h3 class="funding-timeline-title">融资历程</h3><ol class="funding-timeline">'+rows.map(r=>'<li><time datetime="'+esc(r.date)+'">'+esc(r.date)+'</time><div><h3>'+esc(r.stage)+'</h3><p>'+esc(r.conflict?'金额存在冲突':r.amount==null?'金额未披露':money(r.amount,r.currency))+'</p><small class="muted">'+(r.publication_proxy?'披露日期未提供':('记录可见于 '+esc(r.available)))+'</small></div></li>').join('')+'</ol>';
}
let profileRequest=0,profileLoaded=null;
function companySection(section){
  for(const key of ['finance','overview','past']){
    $('#'+key+'Section').hidden=key!==section;
    document.querySelector('[data-section='+key+']').classList.toggle('secondary',key!==section);
  }
  if(section==='overview'&&company&&profileLoaded!==company.id)loadProfile();
}
$('#companySections').onclick=e=>{if(e.target.dataset.section)companySection(e.target.dataset.section);};
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
    profileLoaded=id;
  }catch(e){if(ticket===profileRequest){$('#companyProfile').textContent=e.message;$('#officers').innerHTML='<button id="retryProfile" class="secondary">重新读取</button>';$('#retryProfile').onclick=loadProfile;}}
}
function tab(name){for(const key of ['find','contacts','plan']){$('#'+key+'Panel').hidden=key!==name;document.querySelector('[data-tab='+key+']').classList.toggle('secondary',key!==name);}}
$('#tabs').onclick=e=>{if(e.target.dataset.tab)tab(e.target.dataset.tab);};
const form=$('#planForm');
const money=(v,c)=>v==null?'金额未披露':(c==='CNY'?'¥':c==='USD'?'$':(c||''))+Number(v).toLocaleString('zh-CN');
async function api(path,body){
  const response=await fetch(path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});
  const result=await response.json();
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
    $('#investorCases').innerHTML=r.items.map(x=>'<article class="record"><b>'+esc(x.company)+'</b><p>'+esc(x.stage)+' · '+esc(x.event_date)+'</p>'+financingInfo(x)+'</article>').join('')||'<p>暂无已收录案例</p>';
    $('#investorPage').textContent=r.page+' / '+r.pages;$('#investorPrev').disabled=r.page===1;$('#investorNext').disabled=r.page===r.pages;
  }catch(e){if(ticket===investorRequest){$('#investorSummary').textContent=e.message;$('#investorPage').textContent='';}}
}
$('#investorClose').onclick=()=>$('#investorDialog').close();$('#investorDialog').addEventListener('close',()=>{investorRequest++;});
$('#investorPrev').onclick=()=>investorDetail(investorId,investorPage-1);$('#investorNext').onclick=()=>investorDetail(investorId,investorPage+1);
$('#institutions').addEventListener('click',e=>{const b=e.target.closest('[data-investor]');if(b)investorDetail(b.dataset.investor);});
async function renderInstitutions(){
  if(!company)return;const ticket=++poolRequest,cid=company.id;
  $('#institutionCount').textContent='正在读取机构池…';$('#institutions').innerHTML='';
  $('#institutionPrev').disabled=true;$('#institutionNext').disabled=true;
  try{
    const params=new URLSearchParams({company:cid,q:$('#institutionSearch').value,scope:$('#institutionScope').value,sort:$('#institutionSort').value,page:institutionPage});
    const result=await api('/api/institutions?'+params);if(ticket!==poolRequest||company.id!==cid)return;
    institutionPage=result.page;const saved=account.founder_contacts?.[cid]||{};
    $('#institutionCount').textContent=result.total+' 个机构 / 投资人';$('#institutionPage').textContent=result.page+' / '+result.pages;
    $('#institutionPrev').disabled=result.page===1;$('#institutionNext').disabled=result.page===result.pages;
    $('#institutions').innerHTML=result.items.map(i=>'<article class="institution-card"><h3><button class="investor-name" data-investor="'+esc(i.id)+'">'+esc(i.name)+'</button></h3><p class="muted">'+esc(i.industries.slice(0,3).join(' · ')||'行业未披露')+'</p><p>历史投资 '+i.company_count+' 家企业</p><p class="match">'+(i.industry_count?'同业 '+i.industry_count+' 家 · 同业同阶段 '+i.stage_count+' 家':'暂无同业匹配记录')+'</p><p class="muted">最近披露 '+esc(i.latest)+'</p><button data-add="'+esc(i.id)+'" '+(saved[i.id]?'disabled':'')+'>'+(saved[i.id]?'已加入名单':'加入接触名单')+'</button></article>').join('')||'<p>没有匹配结果，请调整搜索或筛选。</p>';
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
    return '<article class="record contact"><h3>'+esc(i.name)+' · '+(a?names[a.status]:'未提交')+'</h3><p>'+esc(a?.feedback||'加入名单不代表已发起融资。')+'</p>'+
      (canSubmit?'<label>向该机构申请金额（'+cur+'）<input type="number" min="0.01" step="0.01" data-ticket="'+esc(i.id)+'" placeholder="填写本轮拟由该机构认购的金额"></label><button data-finance="submit" data-iid="'+esc(i.id)+'">提交融资方案</button>':'')+
      (a?.status==='terms'?'<p>模拟投资 '+money(a.amount,cur)+' · 本轮投前估值 '+money(r.pre_money,cur)+'</p><p>按已确认金额加本笔测算，本机构持股 '+(a.amount/(r.pre_money+reserved+a.amount)*100).toFixed(2)+'%；本轮全部募足后 '+(a.amount/(r.pre_money+r.target)*100).toFixed(2)+'%。后续同轮交割会继续稀释。</p><button data-finance="accept" data-iid="'+esc(i.id)+'">接受条款</button> <button class="secondary" data-finance="decline" data-iid="'+esc(i.id)+'">拒绝条款</button>':'')+
      (a?.status==='settled'?'<p>已到账 '+money(a.amount,cur)+' · 当前模拟持股 '+(a.ownership*100).toFixed(2)+'%</p>':'')+
      '<p class="finance-error" role="alert"></p><button class="secondary" data-complete-plan hidden>补全融资计划 →</button><p class="muted">'+esc(i.note||'')+'</p></article>';
  }).join('')||'<p>先去机构池选择机构并加入名单。</p>';
}
async function financeAction(type,iid,amount){
  if(saving)return;
  const card=[...document.querySelectorAll('.contact')].find(c=>c.querySelector('[data-iid]')?.dataset.iid===iid);
  const fail=(message,planLink=false)=>{status(message);if(card){card.querySelector('.finance-error').textContent=message;card.querySelector('[data-complete-plan]').hidden=!planLink;}else{$('#financingSummary').textContent=message;}};
  if(dirty){fail('融资方案有未保存的修改，请先保存。',true);return;}
  if(type==='submit'&&!account.founder_rounds?.[company.id]){
    const p=account.founder_plans?.[company.id]||{},missing=[];
    if(!(p.target>0))missing.push('融资目标');if(!(p.pre_money>0))missing.push('模拟投前估值');if(p.cash==null)missing.push('企业现金');if(!p.purpose?.trim())missing.push('资金用途');
    if(missing.length){fail('尚未提交：请先填写并保存'+missing.join('、')+'。',true);return;}
  }
  saving=true;$('#financingWeek').disabled=true;
  card?.querySelectorAll('button').forEach(b=>b.disabled=true);
  let success=false;
  try{const result=await api('/api/action',{type:'financing_'+type,company:company.id,institution:iid,amount,revision:account.revision});account=result.game;success=true;status(type==='submit'?'提交成功，推进一周查看反馈。':'模拟融资进度已更新');}
  catch(error){fail(error.message);}
  finally{saving=false;if(success){renderContacts();preview();}else{card?.querySelectorAll('button').forEach(b=>b.disabled=false);const r=account.founder_rounds?.[company.id];$('#financingWeek').disabled=!r||!Object.values(r.applications).some(a=>['submitted','accepted'].includes(a.status));}}
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
$('#institutions').onclick=async e=>{const b=e.target.closest('[data-add]');if(!b||saving)return;saving=true;b.disabled=true;try{await contactSave(b.dataset.add,'待接触','');renderInstitutions();renderContacts();status('已加入接触名单');}catch(error){status(error.message);b.disabled=false;}finally{saving=false;}};
function list(){
  const q=$('#search').value.trim().toLowerCase();
  const rows=account.companies.filter(c=>(c.name+' '+c.id+' '+c.industry+' '+c.region).toLowerCase().includes(q));
  const pages=Math.max(1,Math.ceil(rows.length/12));page=Math.min(page,pages-1);
  $('#searchCount').textContent=rows.length+' 家企业 · 选择仅用于模拟，不代表认领真实企业';
  $('#results').innerHTML=rows.slice(page*12,page*12+12).map(c=>'<button class="result" data-id="'+esc(c.id)+'"><b>'+esc(c.name)+'</b><span>'+esc(c.industry)+' · '+esc(c.latest.stage)+(c.closed?' · 注销或吊销记录':'')+'</span></button>').join('')||'<p>没有匹配企业</p>';
  $('#page').textContent=(page+1)+' / '+pages;$('#prev').disabled=page===0;$('#next').disabled=page===pages-1;
}
function draft(){
  const data=new FormData(form),p={currency:data.get('currency'),purpose:data.get('purpose'),materials:data.getAll('materials'),goal,months:Number(data.get('months')||18)};
  for(const key of ['cash','burn','target','pre_money'])p[key]=data.get(key)===''?null:Number(data.get(key));
  p.budget=Object.fromEntries(['research','hiring','marketing','other'].map(k=>[k,Number(data.get('budget_'+k)||0)]));
  return p;
}
function guidance(p){
  const settled=account.founder_rounds?.[company.id];
  if(settled)p={...p,cash:settled.cash};
  const total=Object.values(p.budget||{}).reduce((a,b)=>a+b,0);
  let runway='待填写现金数据',note='可用现金 ÷ 月净现金消耗；按消耗不变估算，不是融资时间预测。';
  if(p.cash!=null&&p.burn!=null){
    if(p.burn===0){runway='暂无净现金消耗';note='月净消耗填写为零，暂不计算资金可用月数。';}
    else if(p.cash/p.burn>120){runway='资金可用期异常';note='超过十年分析范围，请核对现金和月净消耗的金额单位；不作为经营优势。';}
    else runway=(p.cash/p.burn).toFixed(1)+' 个月资金可用期';
  }
  const actions=[];
  if(company.closed)actions.push('企业有注销或吊销记录，先核实主体状态；本计划仅作草稿。');
  if(p.cash==null||p.burn==null)actions.push('补充现金余额和月净消耗，判断资金可用期。');
  else if(p.burn>0&&p.cash/p.burn<6)actions.push('按当前消耗，现金不足六个月：优先核实支出预算，并准备资金衔接方案。');
  if(!(p.target>0)||!p.purpose.trim())actions.push('明确融资金额、资金用途和预计覆盖周期。');
  if(company.risks.at(-1)?.type==='abnormal_listing')actions.push('核实经营异常原因及处理状态，准备说明材料。');
  if(!total)actions.push('拆分研发、招聘、市场等融资用途预算。');
  else if(Math.abs(total-(p.target||0))>.005)actions.push('用途合计 '+money(total,p.currency)+'，与目标相差 '+money(Math.abs(total-(p.target||0)),p.currency)+'。');
  if(!actions.length)actions.push('已完成当前表单与预算核对；请核对材料内容，这不代表融资成功或通过尽调。');
  return {runway,note,actions};
}
function preview(){if(!company)return;const p=draft();if(account.founder_rounds?.[company.id])p.cash=account.founder_rounds[company.id].cash;const g=guidance(p);$('#gap').textContent=p.cash!=null&&p.burn!=null?'按当前净消耗覆盖 '+p.months+' 个月，资金缺口 '+money(Math.max(0,p.burn*p.months-p.cash),p.currency)+'；不含新增扩张支出。':'填写现金与月净消耗后计算资金缺口。';$('#runway').textContent=g.runway;$('#runwayNote').textContent=g.note;$('#materialCount').textContent='用途预算合计 '+money(Object.values(p.budget).reduce((a,b)=>a+b,0),p.currency);$('#priorities').innerHTML=g.actions.map(t=>'<li>'+esc(t)+'</li>').join('');}
async function selectCompany(id){
  if(saving)return;
  if(dirty&&!confirm('有未保存的修改，是否放弃并切换企业？'))return;
  const ticket=++requestId;status('正在读取企业资料…');
  try{
    const result=await api('/api/company?id='+encodeURIComponent(id));if(ticket!==requestId)return;
    company=result.company;dirty=false;form.reset();profileRequest++;profileLoaded=null;companySection('finance');
    $('#sidebarCompany').textContent=company.name;
    document.querySelectorAll('[data-section]').forEach(b=>b.disabled=false);
    const p=account.founder_plans?.[id]||{currency:account.currency};
    form.elements.months.value=p.months||18;tab(account.founder_rounds?.[id]?'contacts':'find');
    institutionPage=1;renderInstitutions();renderContacts();
    for(const key of ['currency','cash','burn','target','purpose','pre_money'])form.elements[key].value=p[key]??'';
    for(const key of ['research','hiring','marketing','other'])form.elements['budget_'+key].value=p.budget?.[key]??'';
    form.elements.cash.readOnly=!!account.founder_rounds?.[id];
    for(const input of form.querySelectorAll('[name=materials]'))input.checked=(p.materials||[]).includes(input.value);
    $('#companyName').textContent=company.name;$('#companyMeta').textContent=company.industry+' · '+company.region;
    $('#stage').textContent=company.latest.stage;$('#funding').textContent=company.history.length+' 次';
    $('#risk').textContent=company.closed?'注销或吊销记录':company.risks.at(-1)?.type==='abnormal_listing'?'存在经营异常':company.risks.length?'异常已移出':'未收录异常';
    $('#risk').classList.toggle('risk',company.closed||company.risks.at(-1)?.type==='abnormal_listing');
    $('#cutoff').textContent='历史资料截至 '+account.meta.cutoff+'；经营数据为用户自报，两者分别记录。';
    $('#history').innerHTML=[...company.history].reverse().map(r=>'<div class="record"><b>'+esc(r.date)+' · '+esc(r.stage)+'</b><p>'+esc(money(r.amount,r.currency))+'</p><small>融资历史记录'+(r.publication_proxy?' · 披露日期未提供':'')+'</small></div>').join('')||'<p>暂无融资记录，不代表从未融资。</p>';
    $('#history').innerHTML+=[...company.risks].reverse().map(r=>'<p class="risk">'+esc(r.date)+' · '+(r.type==='abnormal_listing'?'列入':'移出')+'经营异常名录</p>').join('');
    const ref=company.comparison;
    $('#peers').textContent=ref?.median_amount?'同业、同阶段、同币种 '+ref.n+' 家企业最近披露融资金额中位数：'+money(ref.median_amount,ref.currency)+'。披露时间不同，不代表估值或建议融资金额。':'可比金额样本不足，暂不展示统计参考。';
    $('#pastFunding').innerHTML=fundingVisual(company.history);
    $('#pastPeers').textContent=$('#peers').textContent;
    $('#overviewRisks').innerHTML=[...company.risks].reverse().map(r=>'<p>'+esc(r.date)+' · '+(r.type==='abnormal_listing'?'列入':'移出')+'经营异常名录</p>').join('')||'<p>未收录经营异常记录，不代表没有其他风险。</p>';
    $('#picker').hidden=true;$('#details').hidden=false;$('#saveStatus').textContent=p.source?'已读取保存的计划':'';preview();status();
  }catch(error){status(error.message);}
}
function enter(){ $('#entry').hidden=true;$('#workspace').hidden=false;list();status(); }
$('#search').oninput=()=>{page=0;list();};
$('#prev').onclick=()=>{page--;list();};$('#next').onclick=()=>{page++;list();};
$('#results').onclick=e=>{const b=e.target.closest('[data-id]');if(b)selectCompany(b.dataset.id);};
$('#change').onclick=()=>{$('#picker').hidden=!$('#picker').hidden;};
form.oninput=()=>{dirty=true;$('#saveStatus').textContent='有未保存的修改';preview();};
form.onsubmit=async e=>{
  e.preventDefault();if(saving||!company)return;saving=true;
  const plan=draft(),cid=company.id;form.querySelectorAll('input,select,textarea,button').forEach(el=>el.disabled=true);$('#export').disabled=true;
  try{const r=await api('/api/action',{type:'founder_plan',company:cid,plan,revision:account.revision});account=r.game;dirty=false;$('#saveStatus').textContent='计划已保存';status();}
  catch(error){$('#saveStatus').textContent='未保存';status(error.message+'；当前输入已保留，可重新保存。');}
  finally{saving=false;form.querySelectorAll('input,select,textarea,button').forEach(el=>el.disabled=false);$('#export').disabled=false;}
};
$('#export').onclick=()=>{
  if(!company)return;const p=draft(),g=guidance(p);
  const text=[company.name+' · 融资准备清单','历史截止：'+account.meta.cutoff,'以下经营数据为用户自报'+(dirty?'（未保存草稿）':''),'币种：'+p.currency,'现金：'+money(p.cash,p.currency),'月净消耗：'+money(p.burn,p.currency),'融资目标：'+money(p.target,p.currency),'用途：'+(p.purpose||'未填写'),g.runway,g.note,'',...Object.entries(p.budget).map(([k,v])=>({research:'研发',hiring:'招聘',marketing:'市场',other:'其他'}[k])+'：'+money(v,p.currency)),'',...g.actions].join('\n');
  const url=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='融资准备清单.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
window.addEventListener('beforeunload',e=>{if(dirty||saving){e.preventDefault();e.returnValue='';}});
$('#start').onclick=async()=>{ $('#start').disabled=true;try{const r=await api('/api/new',{name:'企业工作台'});account=r.game;enter();}catch(e){status(e.message);}finally{$('#start').disabled=false;}};
(async()=>{try{const r=await api('/api/game');account=r.game;if(account){enter();if(account.founder_company)await selectCompany(account.founder_company);}else{$('#entry').hidden=false;status(r.legacy?'旧账户将保留，进入企业端会创建独立新版工作台。':'');}}catch(e){status(e.message);}})();

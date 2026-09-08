'use strict';
const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let game=null,view='market',filter='current',pageIndex=0,selected=null,busy=false,timer;
const PAGE_SIZE=30;
const money=(n,currency=game?.currency||'CNY')=>n===null||n===undefined?'未披露':(currency==='CNY'?'¥':'$')+Number(n).toLocaleString('en-US',{maximumFractionDigits:2});
const short=(n,currency)=>n===null||n===undefined?'未披露':(currency==='CNY'?'¥':'$')+(n>=1e6?(n/1e6).toFixed(2)+'M':n>=1e3?(n/1e3).toFixed(1)+'K':n.toFixed(2));
function toast(message){$('#toast').textContent=message;$('#toast').hidden=false;clearTimeout(timer);timer=setTimeout(()=>$('#toast').hidden=true,4500)}
async function api(path,body){
  const response=await fetch(path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});
  const result=await response.json();
  if(!response.ok){if(result.game){game=result.game;render()}throw Error(result.error||'请求失败')}
  return result;
}
function allocated(r){return !!game.positions[r.company]?.lots.some(l=>l.round===r.id)}
function eligibility(r){
  if(game.ended)return '已到观察区间末';
  if(r.available.slice(0,7)!==game.as_of.slice(0,7))return '非当前月份披露';
  if(!game.equity_stages.includes(r.stage))return '仅观察：非支持的股权融资轮次';
  if(r.conflict)return '仅观察：来源冲突';
  if(r.amount===null)return '仅观察：融资金额未核验';
  if(r.currency!==game.currency)return '仅观察：与账户币种不同';
  if(allocated(r))return '已记录配置';
  if(game.fees_payable)return '有待支付管理费';
  return null;
}
function drawPath(values,width=260,height=70){
  if(values.length<2)return 'M0 '+height/2+' L'+width+' '+height/2;
  const lo=Math.min(...values),hi=Math.max(...values),span=hi-lo||1;
  return values.map((v,i)=>(i?'L':'M')+(i/(values.length-1)*width)+','+(height-5-(v-lo)/span*(height-10))).join(' ');
}
function render(){
  if(!game)return;
  $('#loading').hidden=true;$('#welcome').hidden=true;$('#game').hidden=false;
  $('#fundName').textContent=game.name;$('#date').textContent=game.as_of;
  $('#currencyLabel').textContent=game.currency==='CNY'?'人民币账户':'美元账户';
  $('#advance').disabled=busy||game.ended;$('#advance').textContent=game.ended?'已到资料区间末':'查看下月资料 →';
  const current=game.curve.at(-1);
  $('#nav').textContent=money(current.net_assets);$('#cash').textContent=money(game.cash);
  $('#cost').textContent=money(current.cost);$('#fees').textContent=money(game.fees_paid+game.fees_payable);
  $('#endBanner').hidden=!game.ended;
  $('#observationRange').textContent='当前观察至 '+game.as_of;
  for(const v of ['market','portfolio','journal']){
    $('#'+v+'View').hidden=view!==v;
    $('[data-view="'+v+'"]').classList.toggle('active',view===v);
  }
  const market=game.market.at(-1);
  $('#pulseTitle').textContent=game.as_of.slice(0,7)+' · 样本新增 '+market.rounds+' 条候选融资记录';
  $('#pulseCopy').textContent='其中 '+market.disclosed+' 条可核验金额 · 人民币 '+short(market.CNY,'CNY')+' · 美元 '+short(market.USD,'USD')+'；曲线为记录数，不是市场收益率。';
  $('#marketTrend path').setAttribute('d',drawPath(game.market.map(x=>x.rounds)));
  renderMarket();renderPortfolio();renderJournal();renderCoverage();
}
function renderMarket(){
  const q=$('#search').value.trim().toLowerCase();
  const rows=game.companies.filter(c=>(filter==='all'||filter==='current'&&c.available.length||filter==='held'&&game.positions[c.id])&&
    (c.name+' '+c.region+' '+c.industry).toLowerCase().includes(q));
  const pages=Math.max(1,Math.ceil(rows.length/PAGE_SIZE));pageIndex=Math.min(pageIndex,pages-1);
  $('#marketCount').textContent=rows.length+' 家企业';
  document.querySelectorAll('[data-filter]').forEach(b=>b.classList.toggle('active',b.dataset.filter===filter));
  $('#marketRows').innerHTML=rows.slice(pageIndex*PAGE_SIZE,(pageIndex+1)*PAGE_SIZE).map(c=>{
    const r=c.latest;
    return '<tr><td><button class="company-link" data-company="'+c.id+'"><strong>'+esc(c.name)+'</strong></button><small>'+esc(c.region)+' · '+esc(r.stage)+'</small></td><td class="money">'+short(r.amount,r.currency)+'</td><td>'+r.available+'<small>'+(r.publication_proxy?'披露日缺失，以事件日代替':'含披露日校验')+'</small></td><td><span class="badge '+(eligibility(r)?'muted':'')+'">'+esc(eligibility(r)||'可投资 · 虚拟资金')+'</span></td><td>'+(!eligibility(r)?'<button class="primary" data-invest-company="'+c.id+'" data-round="'+r.id+'">投资</button> ':'')+'<button class="row-open" data-company="'+c.id+'">资料 ↗</button></td></tr>';
  }).join('')||'<tr><td colspan="5"><div class="empty">当前筛选没有记录。可查看“关注范围”，或继续至下个月；没有披露不代表没有经营活动。</div></td></tr>';
  $('#pageLabel').textContent=(pageIndex+1)+' / '+pages+' 页';
  $('#prevPage').disabled=pageIndex===0;$('#nextPage').disabled=pageIndex>=pages-1;
}
function renderPortfolio(){
  const values=game.curve.flatMap(p=>[p.cash,p.cost]),max=Math.max(1,...values);
  const path=key=>game.curve.map((p,i)=>(i?'L':'M')+(12+i/Math.max(1,game.curve.length-1)*676)+','+(170-p[key]/max*145)).join(' ');
  $('#chart').innerHTML='<svg viewBox="0 0 700 190" role="img" aria-label="现金与投资成本变化"><path d="'+path('cash')+'" fill="none" stroke="#277358" stroke-width="2.5"/><path d="'+path('cost')+'" fill="none" stroke="#899379" stroke-dasharray="4 5" stroke-width="2"/></svg>';
  $('#positions').innerHTML=game.companies.filter(c=>game.positions[c.id]).map(c=>{
    const p=game.positions[c.id];
    return '<article class="position"><div><button class="row-open" data-company="'+c.id+'"><h3>'+esc(c.name)+' ↗</h3></button><p>'+p.lots.length+' 笔假设认购 · 最新披露 '+c.latest.available+'</p><p>当前股权比例与公允价值未核验，不报告投资收益。</p></div><div><span class="money">'+money(p.cost)+'</span><p>累计成本</p></div></article>';
  }).join('')||'<div class="empty">暂无配置。可在融资市场查看企业记录，或继续持有现金。</div>';
}
function renderJournal(){
  $('#journal').innerHTML=[...game.log].reverse().map(e=>'<article class="journal-item"><span>'+e.date+'</span><p>'+esc(e.text)+'</p><b>'+money(e.amount)+'</b></article>').join('');
}
function renderCoverage(){
  const current=game.companies.filter(c=>game.positions[c.id]&&(c.available.length||c.risks.some(r=>r.date.slice(0,7)===game.as_of.slice(0,7))));
  $('#taskCount').textContent=current.length;
  $('#tasks').innerHTML=current.map(c=>'<button class="task" data-company="'+c.id+'"><strong>'+esc(c.name)+'</strong><p>本月有新增融资或经营异常记录，查看资料 ↗</p></button>').join('')||'<div class="dispatch-item"><p>本月未发现组合企业的新增融资或异常记录。</p></div>';
  $('#coverage').innerHTML='<div class="dispatch-item"><p>'+game.meta.funding_records.toLocaleString()+' 条事件ID级融资资料；按业务键进一步归并。</p><p>关注范围：起点前已知的 '+game.meta.eligible_companies.toLocaleString()+' 家企业中，按最近披露时间选取120家；不根据未来成败选样。</p><p>缺失估值保持缺失，当前不具备公允价值重估或退出清算条件。</p>'+(game.fees_payable?'<p class="negative">未支付管理费 '+money(game.fees_payable)+'，已从成本口径净资产扣除。</p>':'')+'</div>';
}
function roundFacts(r){
  return '<article class="disclosure"><header><b>'+esc(r.stage)+'</b><span>'+r.date+' · 事件日</span></header><p>融资金额 '+money(r.amount,r.currency)+' '+(r.currency||'')+'；记录估值 '+money(r.valuation,r.valuation_currency)+(r.valuation?'（'+esc(r.valuation_basis)+'，不直接用于配置定价）':'')+'</p><p>可见日 '+r.available+' · '+(r.publication_proxy?'缺少披露日，以事件日代替；有时点偏差风险':'按事件日与披露日较晚者')+(r.conflict?' · 来源冲突，金额不纳入认购':'')+'</p><details><summary>来源与归并依据</summary><p>数据集融资历史 · 合并 '+r.source_records+' 条事件记录，不累加重复融资额。</p></details></article>';
}
function showCompany(id,show=true){
  selected=id;const c=game.companies.find(c=>c.id===id);if(!c)return;
  const available=c.available.filter(r=>!eligibility(r));
  const p=game.positions[c.id];
  $('#companyBody').innerHTML='<button class="close" data-close aria-label="关闭企业资料">×</button><div class="detail-header"><p>'+esc(c.region)+' / '+esc(c.industry)+'</p><h2>'+esc(c.name)+'</h2><p>名称为来源化名 · 信息截止 '+game.as_of+'</p></div>'+
    '<div class="detail-stats"><div><span>最近披露融资额</span><b>'+short(c.latest.amount,c.latest.currency)+'</b></div><div><span>最近融资事件日</span><b class="date-value">'+c.latest.date+'</b></div><div><span>账户累计配置</span><b>'+money(p?.cost||0)+'</b></div></div>'+
    '<p class="facts">融资额是整轮筹资规模，不是公司价格。以下资料直接展示，不设访问额度。投资成本与参考估值不等同于可变现价值。</p>'+
    (available.length?'<form class="deal" id="investForm"><h3>记录假设认购</h3><label>当月可配置记录<select id="roundSelect">'+available.map(r=>'<option value="'+r.id+'">'+esc(r.stage)+' / '+r.date+' / '+money(r.amount,r.currency)+'</option>').join('')+'</select></label><label>认购金额（'+game.currency+'）<input id="ticket" type="number" min="0.01" step="0.01" required></label><details><summary>可选：录入自己的投后估值假设</summary><label>假设投后估值（'+game.currency+'）<input id="postValuation" type="number" min="0.01" step="0.01" placeholder="留空：不计算认购时股权比例"></label><p>这不是数据提供的交易条款。仅计算本笔认购时的假设股权，不代表后续持股。缺少后续资本结构时，不自动计算稀释。</p></details><div class="quote" id="quote" aria-live="polite"></div><p>视为参与已披露融资中的一部分，而非额外创造一轮融资。确认后现金转为投资成本；历史事件不会改变。此记录不是实际交易或当前可执行报价。</p><button class="primary" type="submit">确认配置并记账</button></form>':'<div class="deal-locked">'+esc(eligibility(c.latest)||'暂无可新增配置的记录')+'。仍可查阅全部已披露资料。</div>')+
    (p?'<div class="detail-section"><h3>本账户认购记录</h3>'+p.lots.map(l=>'<p>'+l.date+' · '+money(l.amount)+' · '+(l.entry_ownership===null?'未设置股权估算':'本笔认购时假设股权 '+(l.entry_ownership*100).toFixed(3)+'%，不是当前持股比例')+'</p>').join('')+'</div>':'')+
    '<div class="detail-section"><h3>融资披露记录</h3>'+[...c.history].reverse().map(roundFacts).join('')+'</div>'+
    '<div class="detail-section"><h3>经营异常记录</h3>'+(c.risks.map(r=>'<p>'+r.date+' · '+(r.type==='abnormal_listing'?'列入经营异常名录':'移出经营异常名录')+'（以事件日作为可见时点）</p>').join('')||'<p>截至当前时点，样本未收录该企业的经营异常记录；不等于确认无风险。</p>')+'</div>';
  if(available.length){$('#ticket').value=Math.min(1000000,available[0].amount,game.cash);updateQuote()}
  if(show&&!$('#companyDialog').open)$('#companyDialog').showModal();
}
function updateQuote(){
  if(!$('#investForm'))return;
  const r=game.companies.find(c=>c.id===selected).available.find(r=>r.id===$('#roundSelect').value);
  const a=Number($('#ticket').value),raw=$('#postValuation').value,v=raw===''?null:Number(raw);
  const valid=Number.isFinite(a)&&a>0&&a<=Math.min(r.amount,game.cash)&&(v===null||Number.isFinite(v)&&v>r.amount&&v<=1e12);
  $('#ticket').max=Math.min(r.amount,game.cash);
  $('#quote').textContent=valid?'配置后现金 '+money(game.cash-a)+' · 投资成本增加 '+money(a)+(v!==null?' · 本笔认购时假设股权 '+(a/v*100).toFixed(3)+'%':' · 未估算股权比例'):'金额须大于零且不超过现金与整轮融资额；如填写投后估值，须大于整轮融资额。';
  $('#investForm button[type=submit]').disabled=!valid||busy;
}
async function act(body){
  if(busy)return;busy=true;render();if($('#investForm'))updateQuote();
  const previous=game;
  try{
    const result=await api('/api/action',{...body,revision:game.revision});game=result.game;render();
    if(body.type==='advance')showReport(previous);
    else{showCompany(selected,false);toast('配置已记录，未生成任何估值收益。')}
  }catch(e){toast(e.message)}
  finally{busy=false;render();if($('#companyDialog').open)showCompany(selected,false)}
}
function requestAdvance(){
  if(busy||game.ended)return;
  const available=game.companies.flatMap(c=>c.available).filter(r=>!eligibility(r)).length;
  $('#advanceBody').innerHTML='<button class="close" data-close aria-label="关闭">×</button><h2 id="advanceTitle">更新至下个月末</h2><p class="workspace-note">将读取下一月份的历史披露。当前月份 '+available+' 条可配置记录将转为仅供观察，不生成随机经营结果。</p><p class="workspace-note">按账户参数计提管理费 '+money(game.initial*game.fee_rate/12)+'；缺失的估值与退出条款不会自动补齐。'+(game.month===35?'下一月是本次历史资料区间末。':'')+'</p><div class="preview-actions"><button data-close>暂不更新</button><button class="primary" data-confirm-month>确认更新</button></div>';
  $('#advanceDialog').showModal();
}
function showReport(previous){
  const m=game.market.at(-1),updates=game.log.slice(previous.log.length);
  $('#reportBody').innerHTML='<button class="close" data-close aria-label="关闭">×</button><p class="eyebrow">历史资料更新</p><h2>'+game.as_of+'</h2><div class="context-help"><p>本月样本新增 '+m.rounds+' 条候选融资记录，其中 '+m.disclosed+' 条金额可核验。</p><p>账户现金变化 '+money(game.cash-previous.cash)+'。融资披露不等于投资收益，本次不自动重估持仓。</p></div><div class="report-list">'+updates.map(e=>'<p>'+esc(e.text)+'</p>').join('')+'</div><button class="primary" data-close>返回工作台</button>';
  $('#reportDialog').showModal();
}
function rules(){
  $('#rulesBody').innerHTML='<p><b>资料范围</b><br>读取123,998条融资事件ID记录和628,084条清洗事件。融资以 invested_company_id_anon 连接被投企业，不误用投资人侧 company_id_anon。仅从2019年末已知企业中选取最近披露的120家。</p><p><b>信息时点</b><br>有效披露日与事件日取较晚者；披露日缺失时采用事件日并标注，因此只是近似历史信息回放，并非严格点时数据库。未来融资与风险记录不下发至浏览器。</p><p><b>金额与估值</b><br>按企业、日期、轮次归并候选融资；同日同轮也可能存在不同交易，不能保证完美去重。金额冲突、模糊表述或币种不明时不配置。人民币与美元独立记账，不推测汇率。披露估值的投前/投后口径未明确，不自动用作价格。</p><p><b>假设配置</b><br>只允许当前观察月份披露、金额可核验的同币种股权融资。认购额不超过整轮融资额，视作替代其中一部分参与资金，历史融资总额不增加。可选投后估值由账户使用者自行设定，只用于本笔认购时的比例演示。</p><p><b>组合口径</b><br>现金 + 累计配置成本 − 未付管理费＝成本口径净资产，不是公允价值或投资绩效。未获得完整资本结构和退出对价前，不计算当前持股、自动稀释、退出回款或破产减记。不能将长期无融资等同于失败。</p><p><b>费用与记录</b><br>年管理费率由建立账户时设定，按初始资金逐月计提；现金不足的部分列为应付费用并扣减净资产。原始数据不修改，账户按操作自动保存。此工具不代表真实交易平台。</p>';
  $('#rulesDialog').showModal();
}
function welcome(){$('#game').hidden=true;$('#welcome').hidden=false;$('#resume').hidden=!game;$('#loading').hidden=true}
document.addEventListener('click',e=>{
  const b=e.target.closest('button');if(!b||b.disabled)return;
  if(b.hasAttribute('data-close')){b.closest('dialog').close();return}
  if(busy)return;
  if(b.dataset.investCompany){
    showCompany(b.dataset.investCompany);
    if($('#investForm')){
      $('#roundSelect').value=b.dataset.round;
      const round=game.companies.find(c=>c.id===selected).available.find(r=>r.id===b.dataset.round);
      $('#ticket').value=Math.min(1000000,round.amount,game.cash);
      updateQuote();
      $('#investForm').scrollIntoView({block:'start'});
      $('#ticket').focus({preventScroll:true});
      $('#ticket').select();
    }
    return;
  }
  if(b.dataset.company){showCompany(b.dataset.company);return}
  if(b.dataset.view){view=b.dataset.view;render();return}
  if(b.dataset.filter){filter=b.dataset.filter;pageIndex=0;renderMarket();return}
  if(b.hasAttribute('data-confirm-month')){$('#advanceDialog').close();act({type:'advance'})}
});
document.addEventListener('submit',e=>{
  if(e.target.id!=='investForm')return;e.preventDefault();
  act({type:'invest',round:$('#roundSelect').value,amount:Number($('#ticket').value),post_valuation:$('#postValuation').value===''?null:Number($('#postValuation').value)});
});
document.addEventListener('input',e=>{if(['ticket','postValuation'].includes(e.target.id))updateQuote()});
document.addEventListener('change',e=>{if(e.target.id==='roundSelect')updateQuote()});
$('#search').oninput=()=>{pageIndex=0;renderMarket()};
$('#prevPage').onclick=()=>{pageIndex--;renderMarket()};$('#nextPage').onclick=()=>{pageIndex++;renderMarket()};
$('#advance').onclick=requestAdvance;$('#rulesBtn').onclick=rules;$('#newBtn').onclick=welcome;$('#resume').onclick=render;
$('#newForm').onsubmit=async e=>{
  e.preventDefault();if(busy)return;busy=true;const b=e.target.querySelector('button[type=submit]');b.disabled=true;
  try{
    const f=new FormData(e.target),result=await api('/api/new',{name:f.get('name'),currency:f.get('currency'),initial:Number(f.get('initial')),fee_rate:Number(f.get('fee'))/100});
    game=result.game;view='market';filter='current';pageIndex=0;selected=null;$('#search').value='';$('#legacyNotice').hidden=true;render();
  }catch(e){toast(e.message)}
  finally{busy=false;b.disabled=false;if(game)render()}
};
$('#exportBtn').onclick=()=>{
  const blob=new Blob([JSON.stringify(game,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download='historical-allocation.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
api('/api/game').then(result=>{
  game=result.game;$('#legacyNotice').hidden=!result.legacy;
  $('#sourceSummary').textContent='数据来源：'+result.meta.funding_records.toLocaleString()+' 条融资事件ID记录及 '+result.meta.scanned_events.toLocaleString()+' 条清洗企业事件。仅使用可核验字段；完整口径见工作台说明。';
  if(game)render();else welcome();
}).catch(e=>{$('#loading').textContent='读取失败：'+e.message});

'use strict';

// A database identity is persisted in the account; typing a label cannot create one.
(() => {
  const el = id => document.getElementById(id);
  const hasIdentity = () => !!game?.investor?.id;
  let forceNew = false, entryPrepared = false, savingIdentity = false;
  let entryChoice = null, switchChoice = null, loadedIdentity = '', loadTicket = 0;
  let recommendationController, graphController;
  let previewController, previewTicket = 0, previewReady = '', previewGraph;
  const field = (v, fallback) => !v || v === '未披露' ? fallback : v;

  async function read(path, controller) {
    let timedOut = false;
    const timeout = setTimeout(() => { timedOut = true; controller.abort(); }, 9500);
    try {
      const response = await fetch(path, {signal: controller.signal});
      const data = await response.json();
      if (!response.ok) throw Error(data.error || '读取失败，请稍后重试。');
      return data;
    } catch (error) {
      if (timedOut) throw Error('服务响应超过 9.5 秒，请稍后重试。');
      throw error;
    } finally { clearTimeout(timeout); }
  }

  function picker(prefix, choose) {
    let page = 1, pages = 1, ticket = 0, controller, timer, rows = [], loading = false;
    const input = el(prefix + 'Search'), results = el(prefix + 'Results');
    function clearSelection() {
      choose(null);
      results.querySelectorAll('[data-investor-choice]').forEach(b => b.setAttribute('aria-pressed', 'false'));
      el(prefix + 'Selected').textContent = '';
    }
    function buttons() {
      el(prefix + 'Prev').disabled = loading || page <= 1;
      el(prefix + 'Next').disabled = loading || page >= pages;
    }
    async function load() {
      clearTimeout(timer); controller?.abort(); controller = new AbortController();
      const mine = ++ticket; loading = true; clearSelection(); buttons();
      el(prefix + 'Status').textContent = '正在搜索数据库…';
      el(prefix + 'Retry').hidden = true; results.replaceChildren();
      results.setAttribute('aria-busy', 'true');
      try {
        const data = await read('/api/recommendation-investors?' + new URLSearchParams({q: input.value.trim(), page}), controller);
        if (mine !== ticket) return;
        page = data.page; pages = data.pages; rows = data.items;
        el(prefix + 'Status').textContent = data.total ? data.total.toLocaleString() + ' 个结果' : '没有匹配的投资方';
        el(prefix + 'Page').textContent = page + ' / ' + pages + ' 页';
        results.innerHTML = rows.map(row => '<button type="button" class="identity-result" data-investor-choice="' + esc(row.id) + '" aria-pressed="false"><span class="identity-result-name">' + esc(row.name) + '</span><span class="identity-result-meta">历史被投企业 ' + row.company_count + ' 家 · ' + esc(row.id) + '</span><span class="identity-result-select" aria-hidden="true">↗</span></button>').join('');
      } catch (error) {
        if (mine !== ticket || error.name === 'AbortError') return;
        el(prefix + 'Status').textContent = error.message; el(prefix + 'Retry').hidden = false;
      } finally {
        if (mine === ticket) { loading = false; results.setAttribute('aria-busy', 'false'); buttons(); }
      }
    }
    input.addEventListener('input', () => {
      clearTimeout(timer); ++ticket; controller?.abort(); loading = true; page = 1;
      clearSelection(); buttons(); results.replaceChildren();
      el(prefix + 'Status').textContent = '正在搜索数据库…';
      timer = setTimeout(load, 250);
    });
    input.addEventListener('keydown', event => {
      if (event.key === 'Enter') { event.preventDefault(); page = 1; load(); }
    });
    results.addEventListener('click', event => {
      const button = event.target.closest('[data-investor-choice]');
      if (!button || savingIdentity || loading) return;
      const row = rows.find(item => item.id === button.dataset.investorChoice);
      if (!row) return;
      results.querySelectorAll('[data-investor-choice]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
      el(prefix + 'Selected').textContent = '已选择：' + row.name;
      choose(row);
    });
    el(prefix + 'Prev').onclick = () => { if (page > 1) { --page; load(); } };
    el(prefix + 'Next').onclick = () => { if (page < pages) { ++page; load(); } };
    el(prefix + 'Retry').onclick = load;
    return {load, reset() { input.value = ''; page = 1; load(); }};
  }

  function updateEntryButton() {
    el('enterInvestor').disabled = !entryChoice || previewReady !== entryChoice.id || savingIdentity;
    el('enterInvestor').textContent = savingIdentity ? '正在进入…' : '确认投资方';
  }
  function cancelPreview() {
    ++previewTicket; previewController?.abort(); previewReady = '';
    previewGraph?.destroy(); previewGraph = null;
    el('identityPreview').dataset.state = 'empty';
    el('identityPreview').setAttribute('aria-busy', 'false');
    el('identityPreview').setAttribute('aria-hidden', 'true'); el('identityPreview').inert = true;
    el('newForm').classList.remove('has-preview');
    el('identityPreviewProfile').replaceChildren(); el('identityPreviewGraph').replaceChildren();
    el('identityPreviewGraphSection').hidden = true;
    el('identityPreviewRetry').hidden = true;
    updateEntryButton();
  }
  function showProfile(profile) {
    const fields = [['历史被投企业', Number(profile.company_count || 0).toLocaleString() + ' 家'],
      ['融资事件', Number(profile.event_count || 0).toLocaleString() + ' 条'],
      ['首次收录投资', profile.first_investment || '未披露'], ['最近收录投资', profile.last_investment || '未披露']];
    el('identityPreviewProfile').innerHTML = '<dl class="identity-profile-facts">' + fields.map(([label, value]) => '<div><dt>' + label + '</dt><dd>' + esc(value) + '</dd></div>').join('') + '</dl>' +
      [['历史投资行业', profile.industries], ['历史投资地区', profile.regions], ['历史融资阶段', profile.stages]].filter(([, values]) => values?.length).map(([label, values]) => '<div class="identity-profile-tags"><span>' + label + '</span><p>' + values.slice(0, 8).map(value => '<b>' + esc(value) + '</b>').join('') + (values.length > 8 ? '<small>等 ' + values.length + ' 类</small>' : '') + '</p></div>').join('');
  }
  async function loadPreview(row) {
    const ticket = ++previewTicket; previewController?.abort(); previewController = new AbortController();
    previewReady = ''; previewGraph?.destroy(); previewGraph = null;
    const panel = el('identityPreview'); panel.dataset.state = 'loading';
    panel.setAttribute('aria-busy', 'true');
    panel.inert = false; panel.setAttribute('aria-hidden', 'false');
    el('newForm').classList.add('has-preview');
    el('identityPreviewTitle').textContent = row.name; el('identityPreviewId').textContent = row.id;
    el('identityPreviewStatus').textContent = '正在读取资料…'; el('identityPreviewRetry').hidden = true;
    el('identityPreviewProfile').replaceChildren(); el('identityPreviewGraph').replaceChildren();
    el('identityPreviewGraphSection').hidden = true; updateEntryButton();
    try {
      const data = await read('/api/investor-preview?' + new URLSearchParams({investor_id: row.id}), previewController);
      if (ticket !== previewTicket || entryChoice?.id !== row.id || data.investor.id !== row.id) return;
      showProfile(data.profile); el('identityPreviewGraphSection').hidden = false;
      previewGraph = InvestorPreviewGraph.render(el('identityPreviewGraph'), data.graph);
      previewReady = row.id; panel.dataset.state = 'ready'; el('identityPreviewStatus').textContent = '';
    } catch (error) {
      if (ticket !== previewTicket || error.name === 'AbortError') return;
      panel.dataset.state = 'error'; el('identityPreviewStatus').textContent = error.message;
      el('identityPreviewRetry').hidden = false;
    } finally { if (ticket === previewTicket) { panel.setAttribute('aria-busy', 'false'); updateEntryButton(); } }
  }
  const entry = picker('identity', row => {
    entryChoice = row;
    if (row) {
      loadPreview(row);
      if (matchMedia('(max-width: 800px)').matches) requestAnimationFrame(() => el('identityPreview').scrollIntoView({block: 'start', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'}));
    } else cancelPreview();
  });
  const switching = picker('switchInvestor', row => {
    switchChoice = row; el('confirmInvestorSwitch').disabled = !row || savingIdentity;
  });

  function prepareEntry() {
    el('identityAccountSettings').hidden = !!game && !forceNew;
    el('identityAccountSettings').querySelectorAll('input,select').forEach(input => {
      input.disabled = !!game && !forceNew;
    });
    el('resume').hidden = !hasIdentity();
    if (!entryPrepared) { entryPrepared = true; entry.load(); }
  }
  function openEntry(newAccount = false) {
    forceNew = newAccount;
    welcome(); prepareEntry();
    el('identitySubmitStatus').textContent = '';
    if (newAccount) entry.reset();
  }
  async function submitEntry(event) {
    event?.preventDefault();
    if (!entryChoice || previewReady !== entryChoice.id || savingIdentity) return;
    const choice = entryChoice; savingIdentity = true; busy = true; updateEntryButton();
    el('identitySubmitStatus').textContent = '';
    try {
      let result;
      if (game && !forceNew) {
        result = await api('/api/investor', {investor_id: choice.id, revision: game.revision});
      } else {
        const form = new FormData(el('newForm'));
        result = await api('/api/new', {workspace: 'investor', investor_id: choice.id,
          name: choice.name, currency: form.get('currency'), initial: Number(form.get('initial')), fee_rate: Number(form.get('fee')) / 100});
      }
      const enter = () => {
        game = result.game; forceNew = false; view = 'discover'; discoverMode = 'recommendations';
        filter = 'all'; pageIndex = 0; selected = null; el('search').value = '';
        el('legacyNotice').hidden = true; loadedIdentity = ''; render(); window.scrollTo(0, 0);
      };
      if (document.startViewTransition && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
        const transition = document.startViewTransition(enter); await transition.finished.catch(() => {});
      } else enter();
    } catch (error) { el('identitySubmitStatus').textContent = error.message; }
    finally { savingIdentity = false; busy = false; updateEntryButton(); if (hasIdentity() && el('welcome').hidden) render(); }
  }
  function openSwitch() {
    if (!hasIdentity() || savingIdentity) return;
    el('switchSubmitStatus').textContent = '';
    el('investorSwitchDialog').showModal(); switching.reset();
    el('switchInvestorSearch').focus();
  }
  async function confirmSwitch() {
    if (!switchChoice || savingIdentity) return;
    const choice = switchChoice; savingIdentity = true; busy = true;
    el('confirmInvestorSwitch').disabled = true; el('closeInvestorSwitch').disabled = true;
    el('switchSubmitStatus').textContent = '正在更换投资方…';
    try {
      const result = await api('/api/investor', {investor_id: choice.id, revision: game.revision});
      game = result.game; view = 'discover'; discoverMode = 'recommendations'; loadedIdentity = '';
      document.querySelectorAll('dialog[open]').forEach(dialog => dialog.close());
      selected = null; render();
    } catch (error) { el('switchSubmitStatus').textContent = error.message; }
    finally {
      savingIdentity = false; busy = false; el('confirmInvestorSwitch').disabled = !switchChoice;
      el('closeInvestorSwitch').disabled = false;
      if (hasIdentity() && el('welcome').hidden) render();
    }
  }

  function clearDashboard() {
    ++loadTicket; recommendationController?.abort(); graphController?.abort();
    el('recommendationSummary').hidden = true;
    el('recommendationRows').replaceChildren(); el('ownInvestorGraph').replaceChildren();
    el('recommendationRetry').hidden = el('ownGraphRetry').hidden = true;
    el('ownGraphDetail').hidden = true; el('ownGraphCount').textContent = ''; el('ownGraphNotes').textContent = '';
    el('recommendationStatus').textContent = '正在为当前投资方读取推荐…';
    el('ownGraphStatus').textContent = '正在读取当前投资方的历史关系…';
  }
  async function loadRecommendations() {
    recommendationController?.abort(); recommendationController = new AbortController();
    const ticket = loadTicket, investor = game?.investor?.id;
    el('recommendationRetry').hidden = true;
    el('recommendationRows').setAttribute('aria-busy', 'true');
    el('recommendationStatus').textContent = '正在为当前投资方读取推荐…';
    try {
      const data = await read('/api/recommendations', recommendationController);
      if (ticket !== loadTicket || investor !== game?.investor?.id || data.investor.id !== investor) return;
      const personalized = data.method === 'sgl';
      el('recommendationSummary').innerHTML = '<header><h2>' + esc(data.investor.name) + '</h2><span class="recommendation-method">' + (personalized ? 'SGL 个性化推荐' : '热门推荐') + '</span></header>' +
        '<p>' + (personalized ? '根据你的历史投资关系，为尚未投资的企业排序。' : '该投资方尚未进入模型训练集，按企业历史投资热度推荐。') + ' 已排除历史被投企业。</p>' +
        '<small>' + (personalized && data.model_history_cutoff ? '模型历史截至 ' + esc(data.model_history_cutoff) + ' · ' : '') + '已投资料核对至 ' + esc(data.history_cutoff) + ' · 计算耗时 ' + Number(data.elapsed_ms).toFixed(1) + ' 毫秒</small>';
      el('recommendationSummary').hidden = false;
      el('recommendationRows').innerHTML = data.items.map((row, index) => '<li class="recommendation-card" data-recommendation-company="' + esc(row.id) + '"><span class="recommendation-rank">' + (index + 1) + '</span><div><p class="eyebrow">' + esc(field(row.industry, '行业未披露')) + ' · ' + esc(field(row.region, '地区未披露')) + '</p><button type="button" class="company-link" data-company="' + esc(row.id) + '"><h3>' + esc(row.name) + '</h3></button><p>融资阶段：' + esc(row.stage || '未披露') + '</p></div><button type="button" class="recommendation-open" data-company="' + esc(row.id) + '">查看企业 →</button></li>').join('');
      el('recommendationStatus').textContent = data.items.length < 10 ? '符合条件的未投企业有 ' + data.items.length + ' 家，已全部展示。' : '';
    } catch (error) {
      if (ticket !== loadTicket || error.name === 'AbortError') return;
      el('recommendationStatus').textContent = error.message; el('recommendationRetry').hidden = false;
    } finally { if (ticket === loadTicket) el('recommendationRows').setAttribute('aria-busy', 'false'); }
  }

  function drawGraph(data) {
    const NS = 'http://www.w3.org/2000/svg';
    const make = (tag, attrs = {}, text) => { const node = document.createElementNS(NS, tag); Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, v)); if (text !== undefined) node.textContent = text; return node; };
    const nodes = data.nodes || [], edges = data.edges || [];
    const groups = [[...nodes.filter(n => n.id === data.root_id)], nodes.filter(n => n.type === 'round'), nodes.filter(n => n.id !== data.root_id && n.type !== 'round')];
    const height = Math.max(280, 80 + Math.max(...groups.map(group => group.length)) * 78);
    const graph = make('svg', {viewBox: '0 0 880 ' + height, width: 880, height, role: 'group', 'aria-label': '当前投资方、融资事件与被投企业'});
    const positions = new Map();
    groups.forEach((group, column) => group.forEach((node, index) => positions.set(node.id, {x: [130, 430, 745][column], y: group.length === 1 ? height / 2 : 50 + index * (height - 100) / (group.length - 1)})));
    edges.forEach(edge => {
      const a = positions.get(edge.source), b = positions.get(edge.target); if (!a || !b) return;
      const line = make('line', {x1: a.x, y1: a.y, x2: b.x, y2: b.y, stroke: '#bac8bc', 'stroke-width': 1.5});
      line.append(make('title', {}, edge.label || '投资关系')); graph.append(line);
    });
    nodes.forEach(node => {
      const pos = positions.get(node.id); if (!pos) return;
      const color = node.type === 'institution' ? '#526c91' : node.type === 'round' ? '#977242' : '#277358';
      const group = make('g', {transform: 'translate(' + pos.x + ',' + pos.y + ')', tabindex: 0, role: 'button', 'aria-label': node.label, 'data-own-graph-node': node.id});
      group.append(make('rect', {x: -115, y: -25, width: 230, height: 50, rx: 7, fill: '#fafcf8', stroke: color, 'stroke-width': 1.5}));
      group.append(make('text', {x: 0, y: 5, 'text-anchor': 'middle', fill: color, 'font-size': 13}, String(node.label).length > 17 ? String(node.label).slice(0, 16) + '…' : node.label));
      group.append(make('title', {}, node.label));
      const inspect = () => {
        const detail = el('ownGraphDetail'); detail.hidden = false;
        detail.innerHTML = '<h3>' + esc(node.label) + '</h3>' + Object.entries(node.details || {}).map(([key, value]) => '<p><b>' + esc(key) + '：</b>' + esc(Array.isArray(value) ? value.join('、') : value) + '</p>').join('');
        if (node.type === 'company' && node.available_in_workspace && game.companies.some(c => c.id === node.entity_id)) {
          const button = document.createElement('button'); button.type = 'button'; button.dataset.company = node.entity_id; button.textContent = '查看企业详情 →'; detail.append(button);
        }
      };
      group.addEventListener('click', inspect); group.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); inspect(); } });
      graph.append(group);
    });
    const viewport = el('ownInvestorGraph');
    viewport.replaceChildren(graph);
    viewport.scrollTop = Math.max(0, (height - (viewport.clientHeight || 360)) / 2);
    viewport.scrollLeft = 0;
    el('ownGraphCount').textContent = nodes.length + ' 个节点 · ' + edges.length + ' 条关系';
    el('ownGraphStatus').textContent = edges.length ? '点击节点可查看资料；图中只展示已收录的历史投资关系。' : '当前资料没有可展示的关联投资记录。';
    el('ownGraphNotes').textContent = (data.notes || []).join(' ');
  }
  async function loadGraph() {
    graphController?.abort(); graphController = new AbortController();
    const ticket = loadTicket, investor = game?.investor?.id;
    el('ownGraphRetry').hidden = true; el('ownGraphStatus').textContent = '正在读取当前投资方的历史关系…';
    try {
      const data = await read('/api/investor-graph', graphController);
      if (ticket !== loadTicket || investor !== game?.investor?.id || data.root_id !== 'institution:' + investor) return;
      drawGraph(data);
    } catch (error) {
      if (ticket !== loadTicket || error.name === 'AbortError') return;
      el('ownGraphStatus').textContent = error.message; el('ownGraphRetry').hidden = false;
    }
  }
  function loadDashboard() { clearDashboard(); loadRecommendations(); loadGraph(); }

  const previousRender = render;
  render = function () {
    if (!hasIdentity()) { openEntry(false); return; }
    previousRender();
    el('currentInvestorName').textContent = game.investor.name;
    el('currentInvestorId').textContent = game.investor.id;
    el('fundName').textContent = game.investor.name;
    const visible = view === 'discover' && discoverMode === 'recommendations';
    el('recommendationsView').hidden = !visible;
    if (visible && loadedIdentity !== game.investor.id) { loadedIdentity = game.investor.id; loadDashboard(); }
  };
  window.InvestorIdentity = Object.freeze({prepareEntry, submitEntry});
  el('newForm').onsubmit = submitEntry;
  el('newBtn').onclick = () => openEntry(true);
  el('changeInvestor').onclick = openSwitch;
  el('confirmInvestorSwitch').onclick = confirmSwitch;
  el('closeInvestorSwitch').onclick = () => { if (!savingIdentity) el('investorSwitchDialog').close(); };
  el('investorSwitchDialog').addEventListener('cancel', event => { if (savingIdentity) event.preventDefault(); });
  el('resume').onclick = () => { if (hasIdentity()) { forceNew = false; render(); } };
  el('recommendationRetry').onclick = loadRecommendations;
  el('ownGraphRetry').onclick = loadGraph;
  el('identityPreviewRetry').onclick = () => { if (entryChoice) loadPreview(entryChoice); };
  if (game) render(); else if (!el('welcome').hidden) prepareEntry();
})();

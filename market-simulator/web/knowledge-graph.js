/* Shared, read-only knowledge graph for both workspaces. No external libraries. */
(() => {
  'use strict';
  const TYPES = {company: ['企业', '#277358'], institution: ['投资人 / 机构', '#526c91'], round: ['融资事件', '#977242'], person: ['人员', '#806b97'], risk: ['风险记录', '#ae594a']};
  const NS = 'http://www.w3.org/2000/svg';
  let dialog, ui, controller, graph, selectedId, activeEntity, returnFocus;
  let serial = 0, history = [], enabled = new Set(Object.keys(TYPES)), positions = new Map();
  let view = {scale: 1, x: 0, y: 0}, drag = null;
  const typeInfo = type => TYPES[type] || ['其他', '#78817e'];
  function make(tag, attrs = {}, text, svg = false) {
    const node = svg ? document.createElementNS(NS, tag) : document.createElement(tag);
    Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
    if (text !== undefined) node.textContent = text;
    return node;
  }
  const svg = (tag, attrs = {}, text) => make(tag, attrs, text, true);
  const button = (text, cls = 'kg-button', title) => make('button', {type: 'button', class: cls, ...(title ? {title, 'aria-label': title} : {})}, text);
  function valueText(value) {
    if (value === null || value === undefined || value === '') return '未披露';
    if (typeof value === 'boolean') return value ? '是' : '否';
    if (Array.isArray(value)) return value.map(valueText).join('、') || '未披露';
    if (typeof value === 'object') return Object.entries(value).map(([key, val]) => `${key}：${valueText(val)}`).join('；');
    return String(value);
  }
  function initialize() {
    if (dialog) return;
    dialog = make('dialog', {id: 'knowledgeGraphDialog', class: 'kg-dialog', 'aria-labelledby': 'kgTitle'});
    const header = make('header', {class: 'kg-header'}), heading = make('div', {class: 'kg-heading'});
    const title = make('h2', {id: 'kgTitle'}, '知识图谱'), subtitle = make('p', {class: 'kg-subtitle'});
    heading.append(make('p', {class: 'kg-eyebrow'}, '关系与证据'), title, subtitle);
    const close = button('关闭', 'kg-button kg-close', '关闭知识图谱');
    close.onclick = () => dialog.close(); header.append(heading, close);
    const toolbar = make('div', {class: 'kg-toolbar'}), back = button('← 返回上一图谱');
    back.hidden = true;
    back.onclick = () => { const previous = history.pop(); if (previous) load(previous.type, previous.id, false); };
    toolbar.append(back, make('p', {class: 'kg-description'}, '沿关系查看企业、投资人和融资记录，点击节点核对证据。'));
    const status = make('div', {class: 'kg-status', role: 'status', 'aria-live': 'polite'});
    const content = make('div', {class: 'kg-content', hidden: ''});
    const filters = make('div', {class: 'kg-filters', role: 'group', 'aria-label': '筛选节点类型'});
    const main = make('div', {class: 'kg-main'}), visual = make('section', {class: 'kg-visual', 'aria-label': '关系图'});
    const controls = make('div', {class: 'kg-view-controls'}), zoomControls = make('div', {class: 'kg-zoom-controls'});
    const minus = button('−', 'kg-button', '缩小图谱'), plus = button('+', 'kg-button', '放大图谱'), reset = button('适应视图');
    minus.onclick = () => zoom(.8); plus.onclick = () => zoom(1.25); reset.onclick = fit;
    zoomControls.append(minus, plus, reset);
    controls.append(make('p', {class: 'kg-hint'}, '点击节点看详情 · 拖动移动 · 适应视图看全图'), zoomControls);
    const canvas = svg('svg', {class: 'kg-svg', role: 'group', 'aria-label': '知识图谱；可用 Tab 选择节点，回车查看详情'});
    const defs = svg('defs'), marker = svg('marker', {id: 'kgArrow', viewBox: '0 0 10 10', refX: '9', refY: '5', markerWidth: '6', markerHeight: '6', orient: 'auto-start-reverse'});
    marker.append(svg('path', {d: 'M 0 0 L 10 5 L 0 10 z', fill: '#84968a'})); defs.append(marker);
    const world = svg('g', {class: 'kg-world'}); canvas.append(defs, world);
    const empty = make('p', {class: 'kg-empty', hidden: ''});
    const index = make('details', {class: 'kg-node-index'}), nodeList = make('div', {class: 'kg-node-list'});
    index.append(make('summary', {}, '节点列表（也可通过列表选择）'), nodeList);
    visual.append(controls, canvas, empty, index);
    const details = make('aside', {class: 'kg-details', 'aria-label': '节点详情'}), notes = make('div', {class: 'kg-notes'});
    main.append(visual, details); content.append(filters, main, notes); dialog.append(header, toolbar, status, content);
    document.body.append(dialog);
    ui = {title, subtitle, back, status, content, filters, canvas, world, empty, nodeList, details, notes, close};
    dialog.addEventListener('close', () => { serial++; controller?.abort(); drag = null; if (returnFocus?.isConnected) returnFocus.focus({preventScroll: true}); });
    canvas.addEventListener('pointerdown', event => {
      if (event.button !== 0 || event.target.closest('[data-kg-node]')) return;
      drag = {id: event.pointerId, x: event.clientX, y: event.clientY, startX: view.x, startY: view.y};
      canvas.setPointerCapture(event.pointerId); canvas.classList.add('kg-dragging');
    });
    canvas.addEventListener('pointermove', event => {
      if (!drag || event.pointerId !== drag.id) return;
      view.x = drag.startX + event.clientX - drag.x; view.y = drag.startY + event.clientY - drag.y; applyView();
    });
    const endDrag = event => {
      if (!drag || event.pointerId !== drag.id) return;
      if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
      drag = null; canvas.classList.remove('kg-dragging');
    };
    canvas.addEventListener('pointerup', endDrag); canvas.addEventListener('pointercancel', endDrag);
    canvas.addEventListener('wheel', event => { if (event.ctrlKey || event.metaKey) { event.preventDefault(); zoom(event.deltaY < 0 ? 1.12 : 1 / 1.12); } }, {passive: false});
  }
  async function open(type, id) {
    if (!['company', 'institution'].includes(type) || !id) return;
    initialize();
    if (!dialog.open) { returnFocus = document.activeElement; history = []; dialog.showModal(); }
    await load(type, String(id), false);
  }
  async function load(type, id, remember = true) {
    if (remember && activeEntity && (activeEntity.id !== id || activeEntity.type !== type)) history.push({...activeEntity});
    activeEntity = {type, id}; ui.back.hidden = !history.length;
    controller?.abort(); const ticket = ++serial; controller = new AbortController(); graph = null;
    ui.title.textContent = '知识图谱'; ui.subtitle.textContent = ''; ui.content.hidden = true; ui.status.hidden = false;
    ui.status.replaceChildren(make('p', {}, '正在整理关系与证据…'));
    try {
      const response = await fetch('/api/knowledge-graph?' + new URLSearchParams({entity_type: type, entity_id: id}), {signal: controller.signal, credentials: 'same-origin', headers: {Accept: 'application/json'}});
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || (response.status === 401 ? '请先进入工作台，再查看知识图谱。' : '暂时无法读取知识图谱。'));
      if (ticket !== serial || !dialog.open) return;
      if (!Array.isArray(result.nodes) || !Array.isArray(result.edges) || !result.nodes.some(node => node.id === result.root_id)) throw new Error('图谱资料不完整，请稍后重试。');
      graph = result; selectedId = graph.root_id; enabled = new Set(Object.keys(TYPES));
      ui.title.textContent = graph.nodes.find(node => node.id === graph.root_id).label + ' · 知识图谱';
      ui.subtitle.textContent = `资料截至 ${graph.as_of || '未披露'} · ${graph.nodes.length} 个节点 · ${graph.edges.length} 条关系`;
      ui.status.hidden = true; ui.content.hidden = false;
      buildFilters(); positions = layout(graph.nodes, graph.edges, graph.root_id); draw(); renderDetails(); renderNotes();
      dialog.scrollTop = 0;
      requestAnimationFrame(() => { if (ticket === serial && dialog.open) initialView(); });
    } catch (error) {
      if (error.name === 'AbortError' || ticket !== serial || !dialog.open) return;
      const retry = button('重新加载'); retry.onclick = () => load(type, id, false);
      ui.status.replaceChildren(make('p', {}, error.message || '知识图谱加载失败。'), retry);
    }
  }
  function buildFilters() {
    ui.filters.replaceChildren(make('span', {class: 'kg-filter-label'}, '显示关系'));
    Object.entries(TYPES).forEach(([type, [labelText, color]]) => {
      const count = graph.nodes.filter(node => node.type === type).length; if (!count) return;
      const label = make('label', {class: 'kg-filter'}), input = make('input', {type: 'checkbox', checked: '', 'data-kg-filter': type}), swatch = make('span', {class: 'kg-swatch', 'aria-hidden': 'true'});
      swatch.style.backgroundColor = color; label.append(input, swatch, document.createTextNode(`${labelText} ${count}`));
      input.onchange = () => {
        if (input.checked) enabled.add(type); else enabled.delete(type);
        if (!visibleNodes().some(node => node.id === selectedId)) selectedId = graph.root_id;
        draw(); renderDetails(); initialView();
      };
      ui.filters.append(label);
    });
  }
  const visibleNodes = () => graph ? graph.nodes.filter(node => node.id === graph.root_id || enabled.has(node.type)) : [];
  // Static, deterministic force layout with rectangular collision resolution.
  function layout(nodes, edges, root) {
    const points = new Map();
    nodes.forEach((node, index) => { const angle = index * 2.399963, r = node.id === root ? 0 : 115 * Math.sqrt(index + 1); points.set(node.id, {x: Math.cos(angle) * r, y: Math.sin(angle) * r * .75}); });
    for (let iteration = 0; iteration < 220; iteration++) {
      const forces = new Map(nodes.map(node => [node.id, {x: 0, y: 0}]));
      for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
        const a = points.get(nodes[i].id), b = points.get(nodes[j].id), fa = forces.get(nodes[i].id), fb = forces.get(nodes[j].id);
        let dx = a.x - b.x, dy = a.y - b.y; if (Math.abs(dx) + Math.abs(dy) < .01) dx = .1;
        const distance = Math.max(40, Math.hypot(dx, dy)), push = 7500 / (distance * distance);
        fa.x += dx / distance * push; fa.y += dy / distance * push; fb.x -= dx / distance * push; fb.y -= dy / distance * push;
        if (Math.abs(dx) < 184 && Math.abs(dy) < 84) {
          const ox = 184 - Math.abs(dx), oy = 84 - Math.abs(dy);
          if (ox < oy * 1.65) { const p = Math.sign(dx || 1) * ox * .35; fa.x += p; fb.x -= p; }
          else { const p = Math.sign(dy || 1) * oy * .35; fa.y += p; fb.y -= p; }
        }
      }
      for (const edge of edges) {
        const a = points.get(edge.source), b = points.get(edge.target); if (!a || !b) continue;
        const dx = b.x - a.x, dy = b.y - a.y, d = Math.max(1, Math.hypot(dx, dy)), pull = (d - 225) * .014;
        forces.get(edge.source).x += dx / d * pull; forces.get(edge.source).y += dy / d * pull;
        forces.get(edge.target).x -= dx / d * pull; forces.get(edge.target).y -= dy / d * pull;
      }
      for (const node of nodes) {
        const p = points.get(node.id), f = forces.get(node.id);
        if (node.id === root) { p.x = 0; p.y = 0; continue; }
        p.x += Math.max(-12, Math.min(12, f.x - p.x * .003)); p.y += Math.max(-12, Math.min(12, f.y - p.y * .003));
      }
    }
    // Remove residual overlaps without attraction pulling cards back together.
    for (let pass = 0; pass < 100; pass++) {
      let overlaps = false;
      for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
        const a = points.get(nodes[i].id), b = points.get(nodes[j].id), dx = a.x - b.x, dy = a.y - b.y;
        const ox = 182 - Math.abs(dx), oy = 78 - Math.abs(dy);
        if (ox <= 0 || oy <= 0) continue;
        overlaps = true;
        const aw = nodes[i].id === root ? 0 : nodes[j].id === root ? 1 : .5, bw = 1 - aw;
        if (ox < oy * 1.6) { const delta = Math.sign(dx || 1) * (ox + .2); a.x += delta * aw; b.x -= delta * bw; }
        else { const delta = Math.sign(dy || 1) * (oy + .2); a.y += delta * aw; b.y -= delta * bw; }
      }
      if (!overlaps) break;
    }
    return points;
  }
  function draw() {
    const nodes = visibleNodes(), ids = new Set(nodes.map(node => node.id)), edges = graph.edges.filter(edge => ids.has(edge.source) && ids.has(edge.target));
    ui.world.replaceChildren(); const lines = svg('g', {class: 'kg-edges'});
    for (const edge of edges) {
      const a = positions.get(edge.source), b = positions.get(edge.target), dx = b.x - a.x, dy = b.y - a.y;
      const trim = Math.min(dx ? 84 / Math.abs(dx) : Infinity, dy ? 31 / Math.abs(dy) : Infinity, .45);
      const group = svg('g', {class: 'kg-edge', 'data-kg-edge': edge.id});
      group.append(svg('line', {x1: a.x + dx * trim, y1: a.y + dy * trim, x2: b.x - dx * trim, y2: b.y - dy * trim, 'marker-end': 'url(#kgArrow)'}));
      group.append(svg('text', {x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 - 6, 'text-anchor': 'middle'}, edge.label)); lines.append(group);
    }
    ui.world.append(lines); ui.nodeList.replaceChildren();
    for (const node of nodes) {
      const p = positions.get(node.id), [typeLabel, color] = typeInfo(node.type);
      const group = svg('g', {class: 'kg-node', transform: `translate(${p.x},${p.y})`, role: 'button', tabindex: '0', 'data-kg-node': node.id, 'aria-label': `${typeLabel}：${node.label}${node.id === graph.root_id ? '，中心节点' : ''}`});
      group.append(svg('title', {}, `${typeLabel} · ${node.label}`), svg('rect', {x: '-83', y: '-30', width: '166', height: '60', rx: '7'}));
      group.append(svg('rect', {class: 'kg-node-accent', x: '-83', y: '-22', width: '4', height: '44', rx: '2', fill: color}));
      const name = String(node.label || '未命名');
      group.append(svg('text', {x: '-69', y: '-2', class: 'kg-node-label'}, name.length > 12 ? name.slice(0, 11) + '…' : name));
      group.append(svg('text', {x: '-69', y: '18', class: 'kg-node-type', fill: color}, `${typeLabel}${node.id === graph.root_id ? ' · 中心' : ''}`));
      group.onclick = () => select(node.id);
      group.onkeydown = event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); select(node.id); } };
      ui.world.append(group);
      const item = button(node.label, 'kg-node-list-button'); item.setAttribute('data-kg-list-node', node.id); item.setAttribute('aria-label', `${typeLabel}：${node.label}`); item.onclick = () => select(node.id, true); ui.nodeList.append(item);
    }
    ui.empty.hidden = nodes.length > 1;
    ui.empty.textContent = graph.nodes.length === 1 ? '现有资料暂未收录可验证的关联关系。可以查看中心实体资料。' : '当前筛选仅显示中心实体。勾选更多节点类型以查看关联关系。';
    highlight(); applyView();
  }
  function select(id, focusDetails = false) {
    selectedId = id;
    const point = positions.get(id), size = ui.canvas.getBoundingClientRect();
    if (point) {
      const x = point.x * view.scale + view.x, y = point.y * view.scale + view.y;
      if (x < 85 * view.scale || x > size.width - 85 * view.scale || y < 32 * view.scale || y > size.height - 32 * view.scale) {
        view.x = size.width / 2 - point.x * view.scale; view.y = size.height / 2 - point.y * view.scale; applyView();
      }
    }
    highlight(); renderDetails();
    if (focusDetails) ui.details.querySelector('.kg-detail-title').focus({preventScroll: true});
  }
  function highlight() {
    const connected = new Set([selectedId]);
    for (const edge of graph.edges) { if (edge.source === selectedId) connected.add(edge.target); if (edge.target === selectedId) connected.add(edge.source); }
    for (const node of ui.world.querySelectorAll('[data-kg-node]')) {
      const active = node.dataset.kgNode === selectedId; node.classList.toggle('kg-selected', active); node.classList.toggle('kg-dimmed', !connected.has(node.dataset.kgNode)); node.setAttribute('aria-pressed', String(active));
    }
    for (const group of ui.world.querySelectorAll('[data-kg-edge]')) { const edge = graph.edges.find(item => item.id === group.dataset.kgEdge); group.classList.toggle('kg-connected', edge.source === selectedId || edge.target === selectedId); }
    for (const item of ui.nodeList.children) item.setAttribute('aria-pressed', String(item.dataset.kgListNode === selectedId));
  }
  function renderDetails() {
    const node = graph.nodes.find(item => item.id === selectedId); if (!node) return;
    ui.details.replaceChildren(make('p', {class: 'kg-detail-type'}, typeInfo(node.type)[0]), make('h3', {class: 'kg-detail-title', tabindex: '-1'}, node.label));
    if (node.entity_id && ['company', 'institution'].includes(node.type) && node.id !== graph.root_id) {
      const navigate = button('以此为中心查看图谱 →', 'kg-button kg-primary'); navigate.setAttribute('data-kg-explore', node.id); navigate.onclick = () => load(node.type, String(node.entity_id)); ui.details.append(navigate);
    }
    const facts = make('dl', {class: 'kg-facts'});
    for (const [key, value] of Object.entries(node.details || {})) {
      if (value === undefined || value === null || value === '' || (Array.isArray(value) && !value.length)) continue;
      const row = make('div'); row.append(make('dt', {}, key), make('dd', {}, valueText(value))); facts.append(row);
    }
    if (facts.children.length) ui.details.append(facts);
    const relations = graph.edges.filter(edge => edge.source === selectedId || edge.target === selectedId);
    ui.details.append(make('h4', {class: 'kg-relations-title'}, `关联关系 ${relations.length}`));
    if (!relations.length) ui.details.append(make('p', {class: 'kg-detail-muted'}, '现有资料暂未收录该实体的关联关系。'));
    const list = make('ol', {class: 'kg-relations'});
    for (const edge of relations) {
      const source = graph.nodes.find(item => item.id === edge.source), target = graph.nodes.find(item => item.id === edge.target); if (!source || !target) continue;
      const other = edge.source === selectedId ? target : source, item = make('li');
      item.append(make('span', {class: 'kg-relation-direction'}, edge.source === selectedId ? `此节点 → ${edge.label}` : `${edge.label} → 此节点`));
      const otherButton = button(other.label, 'kg-related-node');
      otherButton.onclick = () => {
        if (!enabled.has(other.type)) { enabled.add(other.type); for (const input of ui.filters.querySelectorAll('input')) if (input.dataset.kgFilter === other.type) input.checked = true; draw(); }
        select(other.id, true);
      };
      item.append(otherButton);
      const evidence = make('details', {class: 'kg-evidence'}), records = Array.isArray(edge.evidence) ? edge.evidence : [];
      evidence.append(make('summary', {}, `${edge.date || '日期未披露'} · ${records.length ? `${records.length} 条来源` : '来源说明'}`), make('p', {class: 'kg-relation-sentence'}, `${source.label} — ${edge.label} → ${target.label}`));
      if (!records.length) evidence.append(make('p', {}, '该关系暂无单独的来源记录。'));
      for (const record of records) { const line = make('p'); line.append(make('span', {}, valueText(record.source || record.record_type || '数据记录'))); if (record.record_id) line.append(make('code', {}, String(record.record_id))); evidence.append(line); }
      item.append(evidence); list.append(item);
    }
    ui.details.append(list);
  }
  function renderNotes() {
    ui.notes.replaceChildren();
    if (graph.truncated) ui.notes.append(make('p', {class: 'kg-truncated'}, '关系较多，当前仅展示部分记录。可点击关联企业或投资人，以其为中心继续查看。'));
    const notes = Array.isArray(graph.notes) ? graph.notes : graph.notes ? [graph.notes] : [];
    for (const note of notes) ui.notes.append(make('p', {}, valueText(note)));
    if (!notes.length) ui.notes.append(make('p', {}, '图谱根据现有资料中的关系生成；未收录关系不代表不存在。融资金额为整轮金额，不代表单个投资人的出资额。'));
  }
  function fit() {
    if (!graph || !dialog.open) return;
    const points = visibleNodes().map(node => positions.get(node.id)); if (!points.length) return;
    const left = Math.min(...points.map(p => p.x)) - 105, right = Math.max(...points.map(p => p.x)) + 105;
    const top = Math.min(...points.map(p => p.y)) - 55, bottom = Math.max(...points.map(p => p.y)) + 55;
    const size = ui.canvas.getBoundingClientRect(), scale = Math.min(1.12, size.width / (right - left), size.height / (bottom - top));
    view = {scale, x: size.width / 2 - (left + right) / 2 * scale, y: size.height / 2 - (top + bottom) / 2 * scale}; applyView();
  }
  function initialView() {
    fit();
    // Preserve readable labels on dense graphs, especially on a phone. The
    // explicit fit button remains available for a complete network overview.
    const size = ui.canvas.getBoundingClientRect(), minimum = size.width < 500 ? .92 : .78;
    if (view.scale < minimum) {
      const center = positions.get(graph.root_id);
      view = {scale: minimum, x: size.width / 2 - center.x * minimum, y: size.height / 2 - center.y * minimum}; applyView();
    }
  }
  function applyView() { ui.world.setAttribute('transform', `translate(${view.x},${view.y}) scale(${view.scale})`); }
  function zoom(factor) {
    if (!graph) return;
    const size = ui.canvas.getBoundingClientRect(), next = Math.max(.2, Math.min(3, view.scale * factor)), ratio = next / view.scale;
    view.x = size.width / 2 - (size.width / 2 - view.x) * ratio; view.y = size.height / 2 - (size.height / 2 - view.y) * ratio; view.scale = next; applyView();
  }
  document.addEventListener('click', event => {
    const trigger = event.target.closest('[data-kg-type][data-kg-id]'); if (!trigger || trigger.disabled) return;
    event.preventDefault(); open(trigger.dataset.kgType, trigger.dataset.kgId);
  });
  window.KnowledgeGraph = Object.freeze({open});
})();

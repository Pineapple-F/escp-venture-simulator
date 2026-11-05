/* Read-only embedded graph with the enterprise graph's visual language. */
(() => {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const TYPES = {institution: ['投资方', '#526c91'], round: ['融资事件', '#977242'], company: ['企业', '#277358']};
  function make(tag, attrs = {}, text, svg = false) {
    const node = svg ? document.createElementNS(NS, tag) : document.createElement(tag);
    Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
    if (text !== undefined) node.textContent = text;
    return node;
  }
  const svg = (tag, attrs, text) => make(tag, attrs, text, true);
  function render(container, data) {
    const shell = make('div', {class: 'ipg-shell'}), toolbar = make('div', {class: 'ipg-toolbar'});
    const legend = make('div', {class: 'ipg-legend'}), controls = make('div', {class: 'ipg-controls'});
    Object.values(TYPES).forEach(([label, color]) => { const item = make('span', {}, label); item.style.setProperty('--type-color', color); legend.append(item); });
    const canvas = svg('svg', {class: 'ipg-svg', role: 'group', 'aria-label': '投资方知识图谱，可拖动、缩放并选择节点'});
    const world = svg('g'), detail = make('div', {class: 'ipg-detail'});
    const graphNodes = new Map(), graphEdges = [], positions = new Map();
    const roots = data.nodes.filter(n => n.id === data.root_id);
    const rounds = data.nodes.filter(n => n.type === 'round');
    const companies = data.nodes.filter(n => n.id !== data.root_id && n.type !== 'round');
    const graphHeight = Math.max(220, Math.max(rounds.length, companies.length) * 74 + 60);
    [roots, rounds, companies].forEach((group, column) => group.forEach((node, index) => positions.set(node.id, {
      x: [112, 388, 665][column], y: group.length === 1 ? graphHeight / 2 : 50 + index * (graphHeight - 100) / (group.length - 1)
    })));
    let view = {scale: 1, x: 0, y: 0}, width = 780, height = 360, drag, resizeFrame, destroyed = false;
    const apply = () => world.setAttribute('transform', `translate(${view.x},${view.y}) scale(${view.scale})`);
    function fit() {
      width = Math.max(240, canvas.clientWidth); height = canvas.clientHeight || 360;
      canvas.setAttribute('viewBox', `0 0 ${width} ${height}`);
      view.scale = Math.min(1, (width - 24) / 780, (height - 30) / graphHeight);
      view.x = (width - 780 * view.scale) / 2; view.y = (height - graphHeight * view.scale) / 2; apply();
    }
    function zoom(factor) {
      const scale = Math.max(.15, Math.min(3.5, view.scale * factor));
      view.x = width / 2 - (width / 2 - view.x) * scale / view.scale;
      view.y = height / 2 - (height / 2 - view.y) * scale / view.scale;
      view.scale = scale; apply();
    }
    [['zoom-out', '−', '缩小图谱', () => zoom(.8)], ['zoom-in', '+', '放大图谱', () => zoom(1.25)], ['fit', '适应', '适应视图', fit]].forEach(([action, label, title, fn]) => {
      const button = make('button', {type: 'button', 'data-ipg-action': action, 'aria-label': title, title}, label);
      button.onclick = fn; controls.append(button);
    });
    toolbar.append(legend, controls); canvas.append(world);
    for (const edge of data.edges) {
      const a = positions.get(edge.source), b = positions.get(edge.target); if (!a || !b) continue;
      const group = svg('g', {class: 'ipg-edge'});
      group.append(svg('path', {d: `M${a.x + 95},${a.y} C${a.x + 150},${a.y} ${b.x - 150},${b.y} ${b.x - 95},${b.y}`, fill: 'none'}));
      group.append(svg('text', {x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 - 7, 'text-anchor': 'middle'}, edge.label));
      world.append(group); graphEdges.push([group, edge]);
    }
    function select(node) {
      graphNodes.forEach((group, id) => { group.classList.toggle('is-selected', id === node.id); group.setAttribute('aria-pressed', String(id === node.id)); });
      graphEdges.forEach(([group, edge]) => group.classList.toggle('is-connected', edge.source === node.id || edge.target === node.id));
      detail.replaceChildren(make('p', {class: 'ipg-detail-type'}, (TYPES[node.type] || ['记录'])[0]), make('h3', {}, node.label));
      const facts = make('dl');
      Object.entries(node.details || {}).forEach(([key, value]) => {
        const row = make('div'); row.append(make('dt', {}, key), make('dd', {}, Array.isArray(value) ? value.join('、') : String(value ?? '未披露'))); facts.append(row);
      });
      detail.append(facts);
      const edges = data.edges.filter(e => e.source === node.id || e.target === node.id);
      if (edges.length) {
        const evidence = make('details', {class: 'ipg-evidence'}); evidence.append(make('summary', {}, '关系来源 · ' + edges.length));
        edges.forEach(edge => {
          const record = make('div', {class: 'ipg-record'}); record.append(make('p', {}, (edge.label || '关系') + (edge.date ? ' · ' + edge.date : '')));
          (edge.evidence || []).forEach(e => { record.append(make('p', {}, e.source || '来源记录'), make('code', {}, e.record_id || '')); });
          evidence.append(record);
        }); detail.append(evidence);
      }
    }
    for (const node of data.nodes) {
      const p = positions.get(node.id); if (!p) continue;
      const [label, color] = TYPES[node.type] || ['记录', '#78817e'];
      const group = svg('g', {class: 'ipg-node', transform: `translate(${p.x},${p.y})`, tabindex: 0, role: 'button', 'aria-label': node.label, 'data-ipg-node': node.id});
      group.append(svg('rect', {x: -95, y: -29, width: 190, height: 58, rx: 6}));
      group.append(svg('rect', {class: 'ipg-accent', x: -95, y: -29, width: 4, height: 58, rx: 2, fill: color}));
      group.append(svg('text', {class: 'ipg-type', x: -80, y: -8, fill: color}, label));
      group.append(svg('text', {class: 'ipg-label', x: -80, y: 14}, String(node.label).length > 16 ? String(node.label).slice(0, 15) + '…' : node.label));
      group.append(svg('title', {}, node.label));
      group.onclick = () => select(node);
      group.onkeydown = event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); select(node); } };
      world.append(group); graphNodes.set(node.id, group);
    }
    canvas.onpointerdown = event => {
      if (event.button !== 0 || event.target.closest('[data-ipg-node]')) return;
      drag = {id: event.pointerId, x: event.clientX, y: event.clientY, vx: view.x, vy: view.y};
      canvas.setPointerCapture(event.pointerId); canvas.classList.add('is-dragging');
    };
    canvas.onpointermove = event => { if (drag?.id === event.pointerId) { view.x = drag.vx + event.clientX - drag.x; view.y = drag.vy + event.clientY - drag.y; apply(); } };
    canvas.onpointerup = canvas.onpointercancel = event => { if (drag?.id === event.pointerId) { drag = null; if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId); canvas.classList.remove('is-dragging'); } };
    canvas.addEventListener('wheel', event => { if (event.ctrlKey || event.metaKey) { event.preventDefault(); zoom(event.deltaY < 0 ? 1.15 : 1 / 1.15); } }, {passive: false});
    shell.append(toolbar, canvas, make('p', {class: 'ipg-hint'}, '拖动移动 · 点击节点查看资料与来源'), detail);
    const notes = make('details', {class: 'ipg-notes'}); notes.append(make('summary', {}, '资料范围 · ' + data.as_of));
    (data.notes || []).forEach(note => notes.append(make('p', {}, note))); shell.append(notes);
    container.replaceChildren(shell);
    if (roots[0]) select(roots[0]);
    const resize = new ResizeObserver(() => { cancelAnimationFrame(resizeFrame); resizeFrame = requestAnimationFrame(() => { if (!destroyed) fit(); }); });
    resize.observe(canvas); fit();
    return {destroy() { destroyed = true; resize.disconnect(); cancelAnimationFrame(resizeFrame); }};
  }
  window.InvestorPreviewGraph = Object.freeze({render});
})();

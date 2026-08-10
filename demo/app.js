const state = {
  data: null,
  persona: "startup",
  stageSource: "data",
  selectedRoles: new Set(["CEO", "CTO", "产品"]),
  assistantCompanyId: null,
  assistantHistory: [],
  networkFilter: "all",
  networkNodeId: "company",
  networkCompanyId: null,
  networkCy: null,
  networkDetails: new Map(),
  networkRoundOnly: false,
  networkExpandedInvestors: new Set(),
  investorPoolOpen: false,
  investorPoolSort: { key: "probability", direction: "desc" },
  investorPoolSegment: "all",
};

const roleOptions = ["CEO", "CTO", "产品", "销售", "财务", "运营", "HR", "法务"];
const defaultStages = ["种子轮", "天使轮", "Pre-A轮", "A轮", "A+轮", "B轮", "B+轮", "C轮", "C+轮", "D轮及以后", "Pre-IPO", "战略融资"];
const datasetStageOptions = {
  china: defaultStages,
  overseas: ["Seed", "Angel", "Pre-seed", "Series A", "Series B", "Series C", "Later Stage VC", "Growth", "Pre-IPO", "Corporate Round"],
};
const stageAliases = [
  { key: "种子轮", tests: ["种子", "seed", "pre-seed"] },
  { key: "天使轮", tests: ["天使", "angel"] },
  { key: "Pre-A轮", tests: ["pre-a", "pre a"] },
  { key: "A+轮", tests: ["a+轮", "series a+"] },
  { key: "A轮", tests: ["a轮", "series a", "early stage vc"] },
  { key: "B+轮", tests: ["b+轮", "b＋轮", "series b+"] },
  { key: "B轮", tests: ["b轮", "series b"] },
  { key: "C+轮", tests: ["c+轮", "c＋轮", "series c+"] },
  { key: "C轮", tests: ["c轮", "series c"] },
  { key: "D轮及以后", tests: ["d+轮", "d＋轮", "d轮", "series d", "later stage", "growth"] },
  { key: "Pre-IPO", tests: ["pre-ipo", "pre ipo", "ipo"] },
  { key: "战略融资", tests: ["战略", "corporate", "strategic"] },
];
const stageMultipliers = {
  种子轮: 8,
  天使轮: 10,
  "Pre-A轮": 12,
  A轮: 15,
  "A+轮": 17,
  B轮: 20,
  "B+轮": 23,
  C轮: 25,
  "C+轮": 28,
  D轮及以后: 30,
  "Pre-IPO": 35,
  战略融资: 22,
};

const els = {
  region: document.querySelector("#region"),
  personaSwitch: document.querySelector("#personaSwitch"),
  personaHint: document.querySelector("#personaHint"),
  brandSubtitle: document.querySelector("#brandSubtitle"),
  workspaceTitle: document.querySelector("#workspaceTitle"),
  workspaceTopbar: document.querySelector("#workspaceTopbar"),
  workspaceSubtitle: document.querySelector("#workspaceSubtitle"),
  decisionSteps: document.querySelector("#decisionSteps"),
  summaryKicker: document.querySelector("#summaryKicker"),
  summaryTitle: document.querySelector("#summaryTitle"),
  summaryText: document.querySelector("#summaryText"),
  companyOverviewMeta: document.querySelector("#companyOverviewMeta"),
  workspace: document.querySelector(".workspace"),
  workspaceTabs: document.querySelector("#workspaceTabs"),
  decisionView: document.querySelector("#decisionView"),
  companyView: document.querySelector("#companyView"),
  resourcesView: document.querySelector("#resourcesView"),
  decisionGuide: document.querySelector("#decisionGuide"),
  journeyModule: document.querySelector("#journeyModule"),
  journeyTitle: document.querySelector("#journeyTitle"),
  valuationModule: document.querySelector("#valuationModule"),
  matchModule: document.querySelector("#matchModule"),
  investorModuleTitle: document.querySelector("#investorModuleTitle"),
  matchTitle: document.querySelector("#matchTitle"),
  matchSubtitle: document.querySelector("#matchSubtitle"),
  companyProfileTitle: document.querySelector("#companyProfileTitle"),
  companyConditions: document.querySelector("#companyConditions"),
  investorAssumptions: document.querySelector("#investorAssumptions"),
  ticketSize: document.querySelector("#ticketSize"),
  ticketSizeOut: document.querySelector("#ticketSizeOut"),
  targetOwnership: document.querySelector("#targetOwnership"),
  targetOwnershipOut: document.querySelector("#targetOwnershipOut"),
  investorFinancePanel: document.querySelector("#investorFinancePanel"),
  financeMetricGrid: document.querySelector("#financeMetricGrid"),
  financeFormula: document.querySelector("#financeFormula"),
  networkModule: document.querySelector("#networkModule"),
  networkGrid: document.querySelector("#networkGrid"),
  networkFilters: document.querySelector("#networkFilters"),
  networkGraph: document.querySelector("#networkGraph"),
  networkDetail: document.querySelector("#networkDetail"),
  networkSearch: document.querySelector("#networkSearch"),
  networkControls: document.querySelector("#networkControls"),
  companyDossier: document.querySelector("#companyDossier"),
  companyAssistant: document.querySelector("#companyAssistant"),
  decisionPriorities: document.querySelector("#decisionPriorities"),
  priorityKicker: document.querySelector("#priorityKicker"),
  priorityTitle: document.querySelector("#priorityTitle"),
  priorityScore: document.querySelector("#priorityScore"),
  prioritySummary: document.querySelector("#prioritySummary"),
  priorityGrid: document.querySelector("#priorityGrid"),
  assistantMessages: document.querySelector("#assistantMessages"),
  assistantForm: document.querySelector("#assistantForm"),
  assistantInput: document.querySelector("#assistantInput"),
  assistantPrompts: document.querySelector("#assistantPrompts"),
  assistantStatus: document.querySelector("#assistantStatus"),
  dossierTitle: document.querySelector("#dossierTitle"),
  dossierSubtitle: document.querySelector("#dossierSubtitle"),
  dossierGrid: document.querySelector("#dossierGrid"),
  industry: document.querySelector("#industry"),
  metro: document.querySelector("#metro"),
  stage: document.querySelector("#stage"),
  stageDetection: document.querySelector("#stageDetection"),
  company: document.querySelector("#company"),
  teamRoles: document.querySelector("#teamRoles"),
  employees: document.querySelector("#employees"),
  employeesOut: document.querySelector("#employeesOut"),
  runway: document.querySelector("#runway"),
  runwayOut: document.querySelector("#runwayOut"),
  simulateBtn: document.querySelector("#simulateBtn"),
  dataStatus: document.querySelector("#dataStatus"),
  targetCompanyField: document.querySelector("#targetCompanyField"),
  investorPool: document.querySelector("#investorPool"),
  investorPoolStats: document.querySelector("#investorPoolStats"),
  investorPoolBody: document.querySelector("#investorPoolBody"),
  investorPoolSearch: document.querySelector("#investorPoolSearch"),
  investorPoolEmpty: document.querySelector("#investorPoolEmpty"),
  investorPoolSegments: document.querySelector("#investorPoolSegments"),
  backToInvestorPool: document.querySelector("#backToInvestorPool"),
  journeyConfidence: document.querySelector("#journeyConfidence"),
  journeyKpis: document.querySelector("#journeyKpis"),
  modelTreePanel: document.querySelector("#modelTreePanel"),
  modelTreeSummary: document.querySelector("#modelTreeSummary"),
  modelTreeIntro: document.querySelector("#modelTreeIntro"),
  modelTreeDashboard: document.querySelector("#modelTreeDashboard"),
  modelTreePath: document.querySelector("#modelTreePath"),
  modelTree: document.querySelector("#modelTree"),
  modelTreeNodeDetail: document.querySelector("#modelTreeNodeDetail"),
  forecastMatrix: document.querySelector("#forecastMatrix"),
  secondaryAnalysisBody: document.querySelector("#secondaryAnalysisBody"),
  forecastMode: document.querySelector("#forecastMode"),
  forecastTableBody: document.querySelector("#forecastTableBody"),
  exitOutcomes: document.querySelector("#exitOutcomes"),
  fundingCurve: document.querySelector("#fundingCurve"),
  curveSubtitle: document.querySelector("#curveSubtitle"),
  curveForecastLegend: document.querySelector("#curveForecastLegend"),
  historicalFinanceEvents: document.querySelector("#historicalFinanceEvents"),
  historicalFinance: document.querySelector("#historicalFinance"),
  journeyNote: document.querySelector("#journeyNote"),
  valuationSource: document.querySelector("#valuationSource"),
  valuationConfidence: document.querySelector("#valuationConfidence"),
  valuationMedian: document.querySelector("#valuationMedian"),
  valuationRange: document.querySelector("#valuationRange"),
  valuationBars: document.querySelector("#valuationBars"),
  valuationFormula: document.querySelector("#valuationFormula"),
  valuationAction: document.querySelector("#valuationAction"),
  valuationTimelineBtn: document.querySelector("#valuationTimelineBtn"),
  valuationTimelineModal: document.querySelector("#valuationTimelineModal"),
  timelineCloseBtn: document.querySelector("#timelineCloseBtn"),
  timelineTitle: document.querySelector("#timelineTitle"),
  timelineSubtitle: document.querySelector("#timelineSubtitle"),
  timelineChart: document.querySelector("#timelineChart"),
  timelineLegend: document.querySelector("#timelineLegend"),
  timelineEvents: document.querySelector("#timelineEvents"),
  profileModal: document.querySelector("#profileModal"),
  profileCloseBtn: document.querySelector("#profileCloseBtn"),
  profileKicker: document.querySelector("#profileKicker"),
  profileTitle: document.querySelector("#profileTitle"),
  profileSubtitle: document.querySelector("#profileSubtitle"),
  profileScore: document.querySelector("#profileScore"),
  profileScoreLabel: document.querySelector("#profileScoreLabel"),
  profileMatch: document.querySelector("#profileMatch"),
  profileTags: document.querySelector("#profileTags"),
  profileStats: document.querySelector("#profileStats"),
  profileBody: document.querySelector("#profileBody"),
  profileActions: document.querySelector("#profileActions"),
  investorMeta: document.querySelector("#investorMeta"),
  investorMatches: document.querySelector("#investorMatches"),
  pageLoading: document.querySelector("#pageLoading"),
};

let renderTicket = 0;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function norm(value) {
  return String(value || "").trim().toLowerCase();
}

function textMatches(left, right) {
  const a = norm(left);
  const b = norm(right);
  return Boolean(a && b && (a.includes(b) || b.includes(a)));
}

function emptyOrMatches(left, right) {
  return !norm(left) || !norm(right) || textMatches(left, right);
}

function normalizeStage(value) {
  const text = norm(value);
  const hit = stageAliases.find((item) => item.tests.some((test) => text.includes(test)));
  return hit?.key || (defaultStages.includes(value) ? value : "种子轮");
}

function recognizedStage(value) {
  const text = norm(value);
  const hit = stageAliases.find((item) => item.tests.some((test) => text.includes(test)));
  return hit?.key || (defaultStages.includes(value) ? value : null);
}

function companyRecognizedRounds(dataset, companyId) {
  if (!companyId || !state.data) return [];
  return state.data.timeline_events
    .filter((event) => event.dataset === dataset && event.company_id === companyId && event.date && isUsableFundingEvent(event))
    .map((event) => ({ ...event, normalizedStage: recognizedStage(event.stage) }))
    .filter((event) => event.normalizedStage)
    .sort((a, b) => dateValue(a.date) - dateValue(b.date) || stageIndex(a.normalizedStage) - stageIndex(b.normalizedStage));
}

function syncStageFromCompany() {
  const rounds = companyRecognizedRounds(els.region.value, els.company.value);
  const allFinance = state.data.timeline_events
    .filter((event) => event.dataset === els.region.value && event.company_id === els.company.value && event.date && isUsableFundingEvent(event))
    .sort((a, b) => dateValue(a.date) - dateValue(b.date));
  if (!rounds.length) {
    const distinctDates = [...new Set(allFinance.map((event) => event.date))];
    if (distinctDates.length) {
      const inferred = distinctDates.length >= 5 ? "D轮及以后" : distinctDates.length === 4 ? "C轮" : distinctDates.length === 3 ? "B轮" : distinctDates.length === 2 ? "A轮" : "天使轮";
      const option = [...els.stage.options].find((item) => normalizeStage(item.value) === inferred);
      if (option) els.stage.value = option.value;
      state.stageSource = "inferred";
      els.stageDetection.textContent = `缺少标准轮次；按 ${distinctDates.length} 个独立融资日期推断至少 ${inferred}（截至 ${formatDate(distinctDates.at(-1))}）`;
    } else {
      state.stageSource = "fallback";
      els.stageDetection.textContent = "该公司没有融资日期，当前使用手动切割点";
    }
    return;
  }
  const latest = rounds.at(-1);
  const option = [...els.stage.options].find((item) => normalizeStage(item.value) === latest.normalizedStage);
  if (option) els.stage.value = option.value;
  const laterUnclassified = allFinance.filter((event) => dateValue(event.date) > dateValue(latest.date) && !recognizedStage(event.stage));
  state.stageSource = laterUnclassified.length ? "lower-bound" : "data";
  els.stageDetection.textContent = laterUnclassified.length
    ? `最近可识别 ${latest.normalizedStage}（${formatDate(latest.date)}）；此后还有 ${laterUnclassified.length} 条未标轮次融资，当前至少为该阶段`
    : `数据识别：最近一轮 ${latest.normalizedStage}（${formatDate(latest.date)}），此前 ${rounds.length} 条融资事实`;
}

function uniqueTop(field, dataset, limit = 40) {
  return [
    ...new Set(
      state.data.top_values
        .filter((row) => row.dataset === dataset && row.field === field && row.value)
        .sort((a, b) => Number(b.count) - Number(a.count))
        .map((row) => row.value),
    ),
  ].slice(0, limit);
}

function fillSelect(select, values, fallback, preferredValue = "") {
  const options = values.filter(Boolean).length ? values.filter(Boolean) : fallback;
  const current = preferredValue && options.includes(preferredValue) ? preferredValue : options[0];
  select.innerHTML = options.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("");
  select.value = current;
}

function selectedContext() {
  const companyEvents = state.data
    ? state.data.timeline_events.filter((event) => event.dataset === els.region.value && event.company_id === els.company.value)
    : [];
  const industryCounts = new Map();
  companyEvents.forEach((event) => {
    if (event.industry) industryCounts.set(event.industry, (industryCounts.get(event.industry) || 0) + 1);
  });
  const detectedIndustry = [...industryCounts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0];
  return {
    persona: state.persona,
    dataset: els.region.value,
    industry: detectedIndustry || els.industry.value,
    metro: els.metro.value,
    stage: els.stage.value,
    companyId: els.company.value,
    employees: Number(els.employees.value),
    runway: Number(els.runway.value),
    roles: [...state.selectedRoles],
  };
}

function companyDisplayName(dataset, companyId) {
  if (!companyId || !state.data) return "目标公司";
  const dossier = (state.data.company_dossiers || []).find(
    (row) => row.dataset === dataset && row.company_id === companyId,
  );
  if (dossier?.company_name) return String(dossier.company_name).trim();
  if (dataset === "overseas") {
    const overseasIds = (state.data.company_paths || [])
      .filter((row) => row.dataset === "overseas" && Number(row.finance_event_count || 0) > 0)
      .map((row) => row.company_id)
      .sort();
    const index = overseasIds.indexOf(companyId);
    return index >= 0 ? `海外匿名企业 ${String(index + 1).padStart(2, "0")}` : "海外匿名企业";
  }
  return "目标公司";
}

function renderPersona() {
  els.personaSwitch.querySelectorAll("button").forEach((button) => {
    button.classList.toggle("active", button.dataset.persona === state.persona);
  });
  const investor = state.persona === "investor";
  const poolVisible = investor && state.investorPoolOpen;
  document.body.dataset.persona = state.persona;
  els.personaHint.textContent = investor
    ? "估值公司，预测融资，并判断能否通过上市或并购成功退出。"
    : "匹配适合当前阶段的投资人，推动下一轮融资。";
  els.brandSubtitle.textContent = investor ? "公司估值 · 融资预测 · 投资退出" : "融资预测 · 投资人匹配";
  els.workspaceTitle.textContent = poolVisible ? "投资项目池" : investor ? "估值、融资与退出判断" : "预测融资，匹配资金与资源";
  els.workspaceTopbar.hidden = poolVisible;
  els.workspaceSubtitle.textContent = investor
    ? "核心结果是公司上市或被收购，投资人实现收益并完成退出。"
    : "先判断下一轮融资，再根据投资历史筛选适合的投资人。";
  els.simulateBtn.textContent = poolVisible ? "刷新项目池" : investor ? "重新评估公司" : "重新匹配资源";
  els.journeyTitle.textContent = investor ? "融资预测与投资退出" : "融资与退出路径";
  const tabCopy = investor
    ? [["投资判断", "估值 · 续融 · 回报"], ["公司评估", "财务 · 风险 · 关系"], ["", ""]]
    : [["融资规划", "概率 · 时间 · 金额"], ["融资准备", "公司 · 财务 · 风险"], ["投资人匹配", "投资偏好 · 历史记录"]];
  els.workspaceTabs.querySelectorAll("[data-view]").forEach((button, index) => {
    button.hidden = investor && button.dataset.view === "resources";
    button.querySelector("strong").textContent = tabCopy[index][0];
    button.querySelector("small").textContent = tabCopy[index][1];
  });
  els.companyProfileTitle.textContent = poolVisible ? "项目筛选" : investor ? "标的公司" : "公司信息";
  els.investorModuleTitle.textContent = investor ? "共同投资机构" : "找投资人";
  els.matchTitle.textContent = investor ? "共同投资机构" : "投资人匹配";
  els.matchSubtitle.textContent = investor ? "查看机构的历史投资记录" : "根据历史投资记录和阶段偏好筛选";
  els.matchModule.hidden = investor;
  els.companyConditions.hidden = investor;
  els.investorAssumptions.hidden = !investor || poolVisible;
  els.investorFinancePanel.hidden = !investor;
  els.targetCompanyField.hidden = poolVisible;
  els.investorPool.hidden = !poolVisible;
  els.workspaceTabs.hidden = poolVisible;
  els.backToInvestorPool.hidden = !investor || poolVisible;
  [els.decisionView, els.companyView, els.resourcesView].forEach((view) => { if (poolVisible) view.hidden = true; });
  if (investor && !els.resourcesView.hidden) switchWorkspaceView("decision");
  if (!poolVisible && ![els.decisionView, els.companyView, els.resourcesView].some((view) => !view.hidden)) switchWorkspaceView("decision");
  els.decisionView.append(els.decisionGuide, els.journeyModule, els.investorFinancePanel);
  els.secondaryAnalysisBody.append(els.forecastMatrix, els.exitOutcomes);
  els.companyView.append(els.decisionPriorities, els.companyAssistant, els.companyDossier, els.networkModule);
  els.resourcesView.append(els.matchModule);

}

function switchWorkspaceView(view) {
  const views = {
    decision: els.decisionView,
    company: els.companyView,
    resources: els.resourcesView,
  };
  if (!views[view]) return;
  Object.entries(views).forEach(([key, node]) => {
    node.hidden = key !== view;
    node.classList.toggle("active", key === view);
  });
  els.workspaceTabs.querySelectorAll("[data-view]").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === view);
    button.setAttribute("aria-current", button.dataset.view === view ? "page" : "false");
  });
  if (view === "company") {
    els.companyDossier.open = true;
    window.setTimeout(() => {
      const cy = state.networkCy;
      if (!cy) return;
      cy.resize();
      cy.layout(networkLayoutOptions(cy.nodes(), false)).run();
    }, 80);
  }
}

function renderRoleControls() {
  els.teamRoles.innerHTML = roleOptions
    .map(
      (role) => `
        <label class="team-chip">
          <input type="checkbox" value="${escapeHtml(role)}" ${state.selectedRoles.has(role) ? "checked" : ""} />
          <span>${escapeHtml(role)}</span>
        </label>
      `,
    )
    .join("");

  els.teamRoles.querySelectorAll("input").forEach((input) => {
    input.addEventListener("change", () => {
      if (input.checked) state.selectedRoles.add(input.value);
      else state.selectedRoles.delete(input.value);
      deferRender(simulate, "正在更新团队条件");
    });
  });
}

function refreshFilters() {
  const dataset = els.region.value;
  fillSelect(els.industry, uniqueTop("industry_code", dataset), dataset === "china" ? ["人工智能"] : ["Software"], els.industry.value);
  const metroValues = uniqueTop("metro", dataset);
  const preferredMetro = metroValues.includes(els.metro.value) ? els.metro.value : dataset === "china" ? "BJ" : "New York";
  fillSelect(els.metro, metroValues, dataset === "china" ? ["BJ", "SH", "FJ"] : ["New York", "Hong Kong"], preferredMetro);
  fillSelect(els.stage, datasetStageOptions[dataset] || defaultStages, defaultStages, els.stage.value);
  refreshCompanySelect();
}

function companyCandidates() {
  const dataset = els.region.value;
  const industry = "";
  const metro = els.metro.value;
  const stage = els.stage.value;
  const normalizedStage = normalizeStage(stage);
  const matchPlans = [
    {
      level: "strict",
      test: (event) =>
        emptyOrMatches(event.industry, industry) &&
        emptyOrMatches(event.metro, metro) &&
        (!norm(event.stage) || normalizeStage(event.stage) === normalizedStage || textMatches(event.stage, stage)),
    },
    {
      level: "industry-metro",
      test: (event) => emptyOrMatches(event.industry, industry) && emptyOrMatches(event.metro, metro),
    },
    {
      level: "industry",
      test: (event) => emptyOrMatches(event.industry, industry),
    },
    {
      level: "dataset",
      test: () => true,
    },
  ];

  for (const plan of matchPlans) {
    let companies = collectCompanyCandidates(dataset, industry, metro, stage, plan);
    if (dataset === "overseas") companies = companies.filter((item) => item.finance > 0);
    if (companies.length) return companies;
  }

  return [];
}

function collectCompanyCandidates(dataset, industry, metro, stage, plan) {
  const normalizedStage = normalizeStage(stage);
  const byCompany = new Map();
  for (const event of state.data.timeline_events) {
    if (event.dataset !== dataset || !event.company_id) continue;
    if (!plan.test(event)) continue;
    const item = byCompany.get(event.company_id) || { company_id: event.company_id, score: 0, events: 0, finance: 0, financeKeys: new Set(), matchLevel: plan.level };
    const financeHit = isUsableFundingEvent(event);
    item.events += 1;
    if (financeHit) item.financeKeys.add(`${event.date || ""}|${normalizeStage(event.stage)}`);
    item.finance = item.financeKeys.size;
    item.score += Number(textMatches(event.industry, industry)) * 7;
    item.score += Number(textMatches(event.metro, metro)) * 5;
    item.score += Number(normalizeStage(event.stage) === normalizedStage || textMatches(event.stage, stage)) * 4;
    item.score += Number(financeHit) * 4;
    byCompany.set(event.company_id, item);
  }
  for (const item of byCompany.values()) {
    const allFinanceKeys = new Set(
      state.data.timeline_events
        .filter((event) => event.dataset === dataset && event.company_id === item.company_id && event.date && isUsableFundingEvent(event))
        .map((event) => `${event.date}|${normalizeStage(event.stage)}`),
    );
    item.finance = allFinanceKeys.size;
  }
  return [...byCompany.values()].sort((a, b) => b.score - a.score || b.finance - a.finance || b.events - a.events).slice(0, 80);
}

function refreshCompanySelect() {
  const previous = els.company.value;
  const companies = companyCandidates();
  const options = companies.length ? companies : [{ company_id: "", events: 0, finance: 0 }];
  els.company.innerHTML = options
    .map((item) => {
      const label = item.company_id ? `${companyDisplayName(els.region.value, item.company_id)} · ${item.finance} 个融资节点` : "暂无公司样本";
      return `<option value="${escapeHtml(item.company_id)}">${escapeHtml(label)}</option>`;
    })
    .join("");
  if (previous && companies.some((item) => item.company_id === previous)) {
    els.company.value = previous;
  }
  syncStageFromCompany();
}

function toMillions(value) {
  const number = Number(value || 0);
  if (!Number.isFinite(number)) return 0;
  return number > 100000 ? number / 1000000 : number;
}

function formatMoney(millions) {
  const value = Number(millions || 0);
  if (!value) return "-";
  if (value >= 1000) return `$${(value / 1000).toFixed(2)}B`;
  if (value >= 100) return `$${Math.round(value)}M`;
  if (value >= 10) return `$${value.toFixed(1)}M`;
  return `$${value.toFixed(2)}M`;
}

function parseDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatDate(value) {
  const date = parseDate(value);
  if (!date) return "";
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

function addMonths(date, months) {
  const next = new Date(date);
  next.setMonth(next.getMonth() + months);
  return next;
}

function dateValue(value) {
  const date = parseDate(value);
  return date ? date.getTime() : 0;
}

function quantiles(values) {
  const clean = values.map(toMillions).filter((value) => value > 0).sort((a, b) => a - b);
  if (!clean.length) return null;
  const pick = (ratio) => clean[Math.min(clean.length - 1, Math.max(0, Math.round((clean.length - 1) * ratio)))];
  return { count: clean.length, p25: pick(0.25), median: pick(0.5), p75: pick(0.75) };
}

function benchmarkCandidates(ctx) {
  const normalizedStage = normalizeStage(ctx.stage);
  return (state.data.valuation_benchmarks || [])
    .filter((row) => row.dataset === ctx.dataset && row.source === "benchmark")
    .map((row) => {
      const industryHit = textMatches(row.industry, ctx.industry);
      const metroHit = textMatches(row.metro, ctx.metro);
      const stageHit = normalizeStage(row.stage) === normalizedStage || textMatches(row.stage, ctx.stage);
      const score = Number(industryHit) * 12 + Number(metroHit) * 6 + Number(stageHit) * 10 + Number(!row.industry && !row.metro) * 2;
      return { ...row, matchScore: score };
    })
    .sort((a, b) => b.matchScore - a.matchScore || Number(b.count || 0) - Number(a.count || 0));
}

function companyValuationRecords(ctx) {
  if (!ctx.companyId) return [];
  return (state.data.valuation_benchmarks || [])
    .filter((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId && row.source !== "benchmark" && Number(row.value || 0) > 0)
    .map((row) => ({ ...row, value: toMillions(row.value) }));
}

function companyFundingRecords(ctx) {
  if (!ctx.companyId) return [];
  return companyFinancingNodes(ctx)
    .filter((event) => Number(event.amount_usd || 0) > 0)
    .map((event) => ({ ...event, amount: toMillions(event.amount_usd) }));
}

function segmentMatches(row, ctx, level) {
  if (row.dataset !== ctx.dataset) return false;
  const industryHit = textMatches(row.industry, ctx.industry);
  const metroHit = textMatches(row.metro, ctx.metro);
  const stageHit = normalizeStage(row.stage) === normalizeStage(ctx.stage) || textMatches(row.stage, ctx.stage);
  if (level === "industry-metro-stage") return industryHit && metroHit && stageHit;
  if (level === "industry-stage") return industryHit && stageHit;
  if (level === "stage") return stageHit;
  return true;
}

function dataDrivenMultiple(ctx) {
  const levels = [
    { key: "industry-metro-stage", label: "同地区+同行业+同阶段" },
    { key: "industry-stage", label: "同行业+同阶段" },
    { key: "stage", label: "同阶段" },
    { key: "dataset", label: "同数据集全局" },
  ];

  for (const level of levels) {
    const valuationValues = (state.data.valuation_benchmarks || [])
      .filter((row) => row.source !== "benchmark" && Number(row.value || 0) > 0 && segmentMatches(row, ctx, level.key))
      .map((row) => row.value);
    const fundingValues = state.data.timeline_events
      .filter((event) => event.is_finance && Number(event.amount_usd || 0) > 0 && segmentMatches(event, ctx, level.key))
      .map((event) => event.amount_usd);
    const valuationStats = quantiles(valuationValues);
    const fundingStats = quantiles(fundingValues);
    if (valuationStats?.count >= 3 && fundingStats?.count >= 3 && fundingStats.median > 0) {
      const raw = valuationStats.median / fundingStats.median;
      const multiple = Math.max(3, Math.min(80, raw));
      return {
        multiple,
        label: level.label,
        valuationCount: valuationStats.count,
        fundingCount: fundingStats.count,
        fallback: false,
      };
    }
  }

  return {
    multiple: stageMultipliers[normalizeStage(ctx.stage)] || 12,
    label: `${normalizeStage(ctx.stage)} 默认阶段`,
    valuationCount: 0,
    fundingCount: 0,
    fallback: true,
  };
}

function fundingProxy(ctx) {
  const rows = state.data.timeline_events.filter((event) => {
    if (event.dataset !== ctx.dataset || !event.is_finance || !event.amount_usd) return false;
    const industryHit = textMatches(event.industry, ctx.industry);
    const metroHit = textMatches(event.metro, ctx.metro);
    const stageHit = normalizeStage(event.stage) === normalizeStage(ctx.stage);
    return industryHit || metroHit || stageHit;
  });
  const stats = quantiles(rows.map((row) => row.amount_usd));
  if (!stats) return null;
  const multiple = dataDrivenMultiple(ctx);
  return {
    ...stats,
    p25: stats.p25 * multiple.multiple,
    median: stats.median * multiple.multiple,
    p75: stats.p75 * multiple.multiple,
    source: "按融资金额估算",
    formula: multiple.fallback
      ? `估值区间 = 相似融资金额分位数 × ${multiple.multiple.toFixed(1)}（${multiple.label}倍数，当前缺少直接估值样本）`
      : `估值区间 = 相似融资金额分位数 × ${multiple.multiple.toFixed(1)}（由${multiple.label}的 ${multiple.valuationCount} 条估值样本 / ${multiple.fundingCount} 条融资样本计算）`,
  };
}

function estimateValuation(ctx) {
  const companyValues = companyValuationRecords(ctx);
  if (companyValues.length) {
    const stats = quantiles(companyValues.map((row) => row.value));
    return applyCompanyConditionLift(
      {
        ...stats,
        source: "目标公司历史估值",
        formula: `估值区间 = ${companyDisplayName(ctx.dataset, ctx.companyId)} 自身估值记录的 P25 / Median / P75；字段来自 company/deal 估值字段`,
      },
      ctx,
    );
  }

  const companyFunding = companyFundingRecords(ctx);
  if (companyFunding.length) {
    const stats = quantiles(companyFunding.map((row) => row.amount));
    const multiple = dataDrivenMultiple(ctx);
    return applyCompanyConditionLift(
      {
        count: stats.count,
        p25: stats.p25 * multiple.multiple,
        median: stats.median * multiple.multiple,
        p75: stats.p75 * multiple.multiple,
        source: "按该公司融资金额估算",
        formula: multiple.fallback
          ? `估值区间 = ${companyDisplayName(ctx.dataset, ctx.companyId)} 自身融资金额分位数 × ${multiple.multiple.toFixed(1)}（${multiple.label}倍数，当前缺少直接估值样本）`
          : `估值区间 = ${companyDisplayName(ctx.dataset, ctx.companyId)} 自身融资金额分位数 × ${multiple.multiple.toFixed(1)}（由${multiple.label}的 ${multiple.valuationCount} 条估值样本 / ${multiple.fundingCount} 条融资样本计算）`,
      },
      ctx,
    );
  }

  const best = benchmarkCandidates(ctx)[0];
  let stats = null;
  if (best && Number(best.count || 0) >= 2) {
    stats = {
      count: Number(best.count),
      p25: toMillions(best.p25),
      median: toMillions(best.median),
      p75: toMillions(best.p75),
      source: best.industry || best.metro || best.stage ? "真实估值样本 benchmark" : "全局估值样本 benchmark",
      formula: "估值区间 = 匹配样本估值的 P25 / Median / P75",
    };
  } else {
    stats = fundingProxy(ctx);
  }

  if (!stats) {
    return {
      count: 0,
      p25: 0,
      median: 0,
      p75: 0,
      source: "暂无足够估值样本",
      formula: "当前条件下没有可用估值或融资金额样本",
    };
  }

  return applyCompanyConditionLift(applyCompanySignal(stats, ctx), ctx);
}

function valuationModelMetric(dataset) {
  const rows = window.ESCP_VALUATION_MODEL_RESULTS?.patchtst_valuation || [];
  return rows.filter((row) => row.dataset === dataset).at(-1) || null;
}

function companySignalProfile(ctx) {
  const events = companyTimelineEvents(ctx);
  const financeEvents = companyFinancingNodes(ctx);
  const counterparties = new Set(events.map((event) => event.counterparty_id).filter(Boolean));
  const shareholderEvents = events.filter((event) => ["shareholder_appointment", "shareholder_removal"].includes(norm(event.event_type)));
  const first = parseDate(events[0]?.date);
  const last = parseDate(events.at(-1)?.date);
  const spanYears = first && last ? Math.max(0.2, (last - first) / (1000 * 60 * 60 * 24 * 365)) : 1;
  const now = new Date();
  const yearsSinceLast = last ? Math.max(0, (now - last) / (1000 * 60 * 60 * 24 * 365)) : 4;
  const activityLift = Math.min(0.18, Math.log10(events.length + 1) * 0.08);
  const financeLift = Math.min(0.32, financeEvents.length * 0.055);
  const networkLift = Math.min(0.16, counterparties.size * 0.018);
  const shareholderLift = Math.min(0.12, shareholderEvents.length * 0.008);
  const agePenalty = financeEvents.length ? 0 : Math.min(0.18, spanYears * 0.012);
  const stalePenalty = yearsSinceLast > 3 ? Math.min(0.18, (yearsSinceLast - 3) * 0.035) : 0;
  const lift = Math.max(-0.32, Math.min(0.48, activityLift + financeLift + networkLift + shareholderLift - agePenalty - stalePenalty));
  return {
    events: events.length,
    financeEvents: financeEvents.length,
    counterparties: counterparties.size,
    shareholderEvents: shareholderEvents.length,
    spanYears,
    lift,
    multiplier: 1 + lift,
  };
}

function applyCompanySignal(stats, ctx) {
  if (!stats || stats.source?.startsWith("目标公司")) return stats;
  const signal = companySignalProfile(ctx);
  return {
    ...stats,
    p25: stats.p25 * signal.multiplier,
    median: stats.median * signal.multiplier,
    p75: stats.p75 * signal.multiplier,
    companySignalLift: signal.lift,
    formula: `${stats.formula}；再根据该公司 ${signal.events} 条事件、${signal.financeEvents} 个融资节点和 ${signal.counterparties} 个关联方调整 ${(signal.lift * 100).toFixed(0)}%`,
  };
}

function applyCompanyConditionLift(stats, ctx) {
  if (!stats) return null;
  const roleLift = (state.selectedRoles.has("财务") ? 0.04 : -0.03) + (state.selectedRoles.has("销售") ? 0.05 : -0.02);
  const teamLift = ctx.employees >= 30 ? 0.08 : ctx.employees >= 12 ? 0.03 : -0.04;
  const runwayLift = ctx.runway >= 18 ? 0.08 : ctx.runway >= 12 ? 0.03 : ctx.runway < 6 ? -0.08 : 0;
  const lift = Math.max(-0.18, Math.min(0.22, roleLift + teamLift + runwayLift));
  return {
    ...stats,
    p25: stats.p25 * (1 + lift),
    median: stats.median * (1 + lift),
    p75: stats.p75 * (1 + lift),
    lift,
    formula: `${stats.formula}；再按团队规模、runway、财务/销售角色修正 ${(lift * 100).toFixed(0)}%`,
  };
}

function valuationAdvice(valuation, ctx) {
  if (!valuation.count) return ["补齐估值输入", "先补充最近融资金额、融资阶段或真实估值字段，再重新生成投资人和伙伴推荐。"];
  if (valuation.lift < 0) return ["先完善融资材料", "明确财务负责人、销售负责人和核心客户数据，再启动下一轮融资沟通。"];
  if (valuation.median >= valuation.p75 * 0.8) return ["启动融资沟通", "以当前估值中位数作为融资目标，优先联系投资人短名单。"];
  return ["设定融资谈判区间", "用中位估值设目标价格，用保守估值设谈判底线，并优先补强影响估值的团队和 runway 条件。"];
}

function eventLabel(event) {
  const labels = {
    founding: "成立",
    funding_round: "融资",
    financing: "融资",
    investment: "投资",
    rongzi: "融资",
    ipo: "IPO",
    acquisition: "并购",
    secondary: "老股交易",
    business_change: "工商变更",
    shareholder_appointment: "股东进入",
    shareholder_removal: "股东退出",
    hire: "人员任职",
    executive_report: "高管备案",
    legal_appointment: "法定代表人任职",
    legal_removal: "法定代表人变更",
    departure: "人员离任",
    administrative_penalty: "行政处罚",
    dishonesty: "失信记录",
    business_abnormal: "经营异常",
    revocation: "吊销",
    cancellation: "注销",
  };
  return labels[event.event_type] || event.event_type || "事件";
}

function isStrictFinanceEvent(event) {
  return ["funding_round", "financing", "investment", "rongzi", "secondary"].includes(norm(event.event_type));
}

function isUsableFundingEvent(event) {
  if (isStrictFinanceEvent(event)) return true;
  if (["business_change", "shareholder_appointment", "shareholder_removal", "hire", "departure", "founding", "ipo", "acquisition"].includes(norm(event.event_type))) return false;
  return Boolean(event.is_finance);
}

function formatFundingNode(event) {
  const parts = [eventLabel(event)];
  if (event.stage) parts.push(event.stage);
  if (event.role_or_dealtype && !textMatches(event.role_or_dealtype, event.stage)) parts.push(event.role_or_dealtype);
  if (Number(event.amount_usd || 0) > 0) parts.push(formatMoney(toMillions(event.amount_usd)));
  return parts.filter(Boolean).join(" · ");
}

function companyTimelineEvents(ctx) {
  return state.data.timeline_events
    .filter((event) => event.dataset === ctx.dataset && event.company_id === ctx.companyId && event.date)
    .sort((a, b) => dateValue(a.date) - dateValue(b.date));
}

function companyFinancingNodes(ctx) {
  return companyTimelineEvents(ctx)
    .filter((event) => isUsableFundingEvent(event))
    .sort((a, b) => {
      const amountDiff = Number(b.amount_usd || 0) - Number(a.amount_usd || 0);
      return dateValue(a.date) - dateValue(b.date) || amountDiff;
    });
}

function clampValue(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function smoothPath(points, x, y) {
  if (!points.length) return "";
  if (points.length === 1) return `M ${x(points[0].date).toFixed(1)} ${y(points[0].value).toFixed(1)}`;
  return points
    .map((point, index) => {
      const currentX = x(point.date);
      const currentY = y(point.value);
      if (!index) return `M ${currentX.toFixed(1)} ${currentY.toFixed(1)}`;
      const prev = points[index - 1];
      const controlX = (x(prev.date) + currentX) / 2;
      return `Q ${controlX.toFixed(1)} ${y(prev.value).toFixed(1)} ${currentX.toFixed(1)} ${currentY.toFixed(1)}`;
    })
    .join(" ");
}

function buildDemoTimeline(ctx, valuation) {
  const currentDate = new Date();
  const currentValue = Math.max(valuation?.median || 0, 0);
  if (!currentValue) return null;

  const events = companyTimelineEvents(ctx);
  const firstDate = parseDate(events[0]?.date) || addMonths(currentDate, -60);
  const multiple = dataDrivenMultiple(ctx).multiple;
  const financing = companyFinancingNodes(ctx)
    .filter((event) => event.date && Number(event.amount_usd || 0) > 0)
    .map((event) => ({
      date: event.date,
      rawValue: toMillions(event.amount_usd) * multiple,
      event,
    }))
    .filter((point) => dateValue(point.date) < currentDate.getTime())
    .sort((a, b) => dateValue(a.date) - dateValue(b.date));

  const startRatio = financing.length ? 0.26 : 0.34;
  const start = {
    date: firstDate.toISOString().slice(0, 10),
    value: Math.max(currentValue * startRatio, 0.1),
    label: "起点",
    type: "start",
  };
  const financePoints = financing.slice(-2).map((point, index) => ({
    date: point.date,
    value: clampValue(point.rawValue, currentValue * 0.42, currentValue * (0.72 + index * 0.16)),
    label: "融资",
    detail: formatFundingNode(point.event),
    type: "finance",
  }));
  const current = {
    date: currentDate.toISOString().slice(0, 10),
    value: currentValue,
    label: "当前估值",
    detail: valuation.source,
    type: "current",
  };

  const history = [start, ...financePoints, current]
    .filter((point) => point.date && Number(point.value || 0) > 0)
    .sort((a, b) => dateValue(a.date) - dateValue(b.date));
  const hasFinance = financePoints.length > 0;
  const totalGrowth = clampValue(1.24 + Number(hasFinance) * 0.16 + (valuation.lift || 0) * 0.7, 1.12, 1.72);
  const future = [1, 2, 3, 4, 5, 6, 7, 8].map((step) => ({
    date: addMonths(currentDate, step * 3).toISOString().slice(0, 10),
    value: currentValue * Math.pow(totalGrowth, step / 8),
    label: "未来预测",
    type: "future",
  }));
  const markers = [
    start,
    ...financePoints,
    current,
    future.at(-1),
  ].filter(Boolean);

  return { history, future, markers, hasFinance };
}

function renderTimelineChart(ctx, valuation) {
  const timeline = buildDemoTimeline(ctx, valuation);
  els.timelineTitle.textContent = companyDisplayName(ctx.dataset, ctx.companyId);
  els.timelineSubtitle.textContent = "用少量关键数值和事件生成直观估值故事线，虚线为未来 24 个月预测。";
  if (!timeline) {
    els.timelineChart.innerHTML = `<div class="empty-chart">当前公司缺少可绘制的估值信息</div>`;
    els.timelineLegend.innerHTML = "";
    els.timelineEvents.innerHTML = "";
    return;
  }

  const { history, future, markers, hasFinance } = timeline;
  const points = [...history, ...future];
  const width = 900;
  const height = 360;
  const pad = { left: 72, right: 34, top: 42, bottom: 56 };
  const dates = points.map((point) => dateValue(point.date));
  const values = points.map((point) => point.value);
  const minDate = Math.min(...dates);
  const maxDate = Math.max(...dates);
  const maxValue = Math.max(...values) * 1.28;
  const x = (date) => pad.left + ((dateValue(date) - minDate) / Math.max(1, maxDate - minDate)) * (width - pad.left - pad.right);
  const y = (value) => pad.top + (1 - value / Math.max(1, maxValue)) * (height - pad.top - pad.bottom);
  const historyPath = smoothPath(history, x, y);
  const futurePath = smoothPath([history.at(-1), ...future], x, y);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((ratio) => maxValue * ratio);
  const futureStartX = x(history.at(-1).date);
  const boundaryLabelX = Math.max(pad.left + 76, Math.min(width - pad.right - 90, futureStartX));
  const labelRows = new Map();
  const markerViews = markers.map((point) => {
    const markerX = x(point.date);
    const markerY = y(point.value);
    const bucket = Math.round(markerX / 90);
    const row = labelRows.get(bucket) || 0;
    labelRows.set(bucket, row + 1);
    return {
      ...point,
      markerX,
      markerY,
      labelX: Math.max(pad.left + 36, Math.min(width - pad.right - 48, markerX)),
      labelY: Math.max(pad.top + 16, markerY - 18 - row * 18),
    };
  });

  els.timelineChart.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="公司估值趋势故事线">
      <defs>
        <linearGradient id="historyFill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="#0a7b6f" stop-opacity="0.17" />
          <stop offset="100%" stop-color="#0a7b6f" stop-opacity="0.02" />
        </linearGradient>
      </defs>
      <rect x="${futureStartX.toFixed(1)}" y="${pad.top}" width="${(width - pad.right - futureStartX).toFixed(1)}" height="${height - pad.top - pad.bottom}" class="future-zone" />
      ${ticks.map((tick) => `
        <line x1="${pad.left}" y1="${y(tick).toFixed(1)}" x2="${width - pad.right}" y2="${y(tick).toFixed(1)}" class="grid-line" />
        <text x="${pad.left - 12}" y="${y(tick).toFixed(1)}" class="axis-label" text-anchor="end">${escapeHtml(formatMoney(tick))}</text>
      `).join("")}
      <line x1="${pad.left}" y1="${height - pad.bottom}" x2="${width - pad.right}" y2="${height - pad.bottom}" class="axis-line" />
      <path d="${historyPath} L ${x(history.at(-1).date).toFixed(1)} ${height - pad.bottom} L ${x(history[0].date).toFixed(1)} ${height - pad.bottom} Z" class="history-area" />
      <path d="${historyPath}" class="history-line" />
      <path d="${futurePath}" class="future-line" />
      <line x1="${futureStartX.toFixed(1)}" y1="${pad.top}" x2="${futureStartX.toFixed(1)}" y2="${height - pad.bottom}" class="forecast-boundary-line" />
      <text x="${boundaryLabelX.toFixed(1)}" y="${height - 30}" class="forecast-boundary-label" text-anchor="middle">当前 ${escapeHtml(formatDate(history.at(-1).date))}</text>
      ${markerViews.map((point) => `
        <g>
          <circle cx="${point.markerX.toFixed(1)}" cy="${point.markerY.toFixed(1)}" r="${point.type === "current" ? 8 : 6}" class="${point.type === "future" ? "future-dot" : point.type === "finance" ? "finance-marker-dot" : "event-marker-dot"}" />
          <text x="${point.labelX.toFixed(1)}" y="${point.labelY.toFixed(1)}" class="${point.type === "future" ? "future-marker-label" : point.type === "finance" ? "marker-label finance-marker-label" : "marker-label"}" text-anchor="middle">${escapeHtml(point.label)}</text>
        </g>
      `).join("")}
      <text x="${pad.left}" y="${height - 16}" class="axis-label">${escapeHtml(formatDate(points[0].date))}</text>
      <text x="${width - pad.right}" y="${height - 16}" class="axis-label" text-anchor="end">${escapeHtml(formatDate(points.at(-1).date))}</text>
    </svg>
  `;
  els.timelineLegend.innerHTML = `
    <span><i class="legend-history"></i>历史趋势</span>
    <span><i class="legend-future"></i>未来 24 个月</span>
    <span><i class="legend-finance"></i>${hasFinance ? "融资节点" : "估算节点"}</span>
    <span>当前中位估值 ${escapeHtml(formatMoney(valuation.median))}</span>
  `;
  els.timelineEvents.innerHTML = markers
    .filter((point) => point.type !== "future")
    .map((point) => `
      <div class="${point.type === "finance" ? "finance-event-card" : ""}">
        <strong>${escapeHtml(point.label)}</strong>
        <span>${escapeHtml(formatDate(point.date))} · ${escapeHtml(point.detail || "估值故事线节点")}</span>
      </div>
    `)
    .join("");
}

function openValuationTimeline() {
  if (!state.data) return;
  const ctx = selectedContext();
  const valuation = estimateValuation(ctx);
  renderTimelineChart(ctx, valuation);
  els.valuationTimelineModal.hidden = false;
}

function closeValuationTimeline() {
  els.valuationTimelineModal.hidden = true;
}

function closeProfileModal() {
  els.profileModal.hidden = true;
}

function renderValuation(ctx) {
  const valuation = estimateValuation(ctx);
  const [title, copy] = valuationAdvice(valuation, ctx);
  const metric = valuationModelMetric(ctx.dataset);
  const modelText = metric?.mae ? ` · PatchTST估值MAE ${Number(metric.mae).toFixed(3)}` : "";
  els.valuationSource.textContent = `${valuation.source}${modelText}`;
  els.valuationConfidence.textContent = valuation.count ? `样本 ${valuation.count}` : "样本不足";
  els.valuationMedian.textContent = valuation.count ? formatMoney(valuation.median) : "-";
  els.valuationRange.textContent = valuation.count ? `保守 ${formatMoney(valuation.p25)} · 乐观 ${formatMoney(valuation.p75)}` : "暂无区间";
  els.valuationFormula.textContent = valuation.formula;
  const max = Math.max(valuation.p75 || 1, 1);
  els.valuationBars.innerHTML = [
    ["保守", valuation.p25],
    ["中位", valuation.median],
    ["乐观", valuation.p75],
  ]
    .map(
      ([label, value]) => `
        <div class="bar-row">
          <span>${escapeHtml(label)}</span>
          <div><i style="width:${Math.max(6, (Number(value || 0) / max) * 100)}%"></i></div>
          <b>${escapeHtml(formatMoney(value))}</b>
        </div>
      `,
    )
    .join("");
  els.valuationAction.innerHTML = `
    <span>公司推荐下一步计划</span>
    <strong>${escapeHtml(title)}</strong>
    <p>${escapeHtml(copy)}</p>
  `;
}

function investorScore(investor, ctx) {
  const text = `${investor.preferred_industry} ${investor.preferred_verticals} ${investor.preferred_types}`;
  const geo = `${investor.country} ${investor.city} ${investor.preferred_geography}`;
  let score = ctx.dataset === "china" ? 40 : 34;
  if (textMatches(text, ctx.industry)) score += 30;
  if (ctx.metro && textMatches(geo, ctx.metro)) score += 24;
  else if (geo.toLowerCase().includes(ctx.dataset === "china" ? "china" : "united states")) score += 10;
  if (textMatches(text, ctx.stage) || textMatches(text, normalizeStage(ctx.stage))) score += 12;
  score += Math.min(16, Math.log10(Number(investor.total_investments || 1) + 1) * 9);
  if (state.selectedRoles.has("财务")) score += 4;
  if (state.selectedRoles.has("销售")) score += 3;
  return Math.round(Math.min(98, score));
}

function investorReasons(investor, ctx) {
  const text = `${investor.preferred_industry} ${investor.preferred_verticals} ${investor.preferred_types}`;
  const geo = `${investor.country} ${investor.city} ${investor.preferred_geography}`;
  const reasons = [];
  if (textMatches(text, ctx.industry)) reasons.push("行业偏好命中");
  if (ctx.metro && textMatches(geo, ctx.metro)) reasons.push("地区覆盖命中");
  if (textMatches(text, ctx.stage) || textMatches(text, normalizeStage(ctx.stage))) reasons.push("阶段偏好接近");
  if (Number(investor.total_investments || 0) >= 5) reasons.push("历史投资活跃");
  if (state.selectedRoles.has("财务")) reasons.push("已有财务负责人");
  return reasons.slice(0, 4);
}

function matchInvestors(ctx) {
  return state.data.investors
    .filter((investor) => investor.dataset === ctx.dataset)
    .map((investor) => ({ ...investor, score: investorScore(investor, ctx), reasons: investorReasons(investor, ctx) }))
    .sort((a, b) => b.score - a.score || Number(b.total_investments) - Number(a.total_investments))
    .slice(0, 3);
}

function partnerScore(partner, ctx) {
  let score = 20;
  if (companyCounterparties(ctx).has(partner.partner_id)) score += 35;
  if ((partner.industries || []).some((item) => textMatches(item, ctx.industry))) score += 35;
  if ((partner.metros || []).some((item) => textMatches(item, ctx.metro))) score += 25;
  if ((partner.stages || []).some((item) => normalizeStage(item) === normalizeStage(ctx.stage) || textMatches(item, ctx.stage))) score += 15;
  score += Math.min(18, Math.log10(Number(partner.event_count || 1) + 1) * 9);
  score += Math.min(10, Number(partner.finance_count || 0) * 2);
  return Math.round(Math.min(98, score));
}

function partnerReasons(partner, ctx) {
  const reasons = [];
  if (companyCounterparties(ctx).has(partner.partner_id)) reasons.push("与该公司有历史关联");
  if ((partner.industries || []).some((item) => textMatches(item, ctx.industry))) reasons.push("同产业事件");
  if ((partner.metros || []).some((item) => textMatches(item, ctx.metro))) reasons.push("同地区出现");
  if ((partner.stages || []).some((item) => normalizeStage(item) === normalizeStage(ctx.stage) || textMatches(item, ctx.stage))) reasons.push("阶段相近");
  if (Number(partner.finance_count || 0) > 0) reasons.push("参与过融资相关事件");
  if (Number(partner.event_count || 0) >= 5) reasons.push("历史互动活跃");
  return reasons.slice(0, 4);
}

function companyCounterparties(ctx) {
  if (!ctx.companyId) return new Set();
  return new Set(
    state.data.timeline_events
      .filter((event) => event.dataset === ctx.dataset && event.company_id === ctx.companyId && event.counterparty_id)
      .map((event) => event.counterparty_id),
  );
}

function matchPartners(ctx) {
  return (state.data.partners || [])
    .filter((partner) => partner.dataset === ctx.dataset)
    .map((partner) => ({ ...partner, score: partnerScore(partner, ctx), reasons: partnerReasons(partner, ctx) }))
    .sort((a, b) => b.score - a.score || Number(b.event_count) - Number(a.event_count))
    .slice(0, 3);
}

function listFrom(value) {
  if (Array.isArray(value)) return value.filter(Boolean);
  if (!value) return [];
  return String(value).split(/[;、,，]/).map((item) => item.trim()).filter(Boolean);
}

function shortList(items, limit = 4) {
  return listFrom(items).slice(0, limit).join(" · ");
}

function scoreLevel(score) {
  if (score >= 86) return "强匹配";
  if (score >= 72) return "可优先触达";
  if (score >= 58) return "可观察";
  return "备选";
}

function profileStats(stats) {
  return stats.map(([label, value]) => `
    <div>
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value || "-")}</strong>
    </div>
  `).join("");
}

function profileSections(sections) {
  return sections.map((section) => `
    <section>
      <h4>${escapeHtml(section.title)}</h4>
      <ul>
        ${section.items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
      </ul>
    </section>
  `).join("");
}

function investorDisplayName(investor) {
  return String(investor?.investor_name || "匿名投资机构").trim() || "匿名投资机构";
}

function renderProfile(profile) {
  els.profileKicker.textContent = profile.kicker;
  els.profileTitle.textContent = profile.title;
  els.profileSubtitle.textContent = profile.subtitle;
  els.profileScore.textContent = profile.scoreText || `${profile.score}分`;
  els.profileScoreLabel.textContent = profile.scoreLabel || "匹配分";
  els.profileMatch.hidden = !profile.match;
  els.profileMatch.innerHTML = profile.match ? `<header><div><span>匹配依据</span><h4>为什么适合这家公司</h4></div></header><p>${escapeHtml(profile.match.summary)}</p><div>${profile.match.factors.map((factor) => `<article class="${factor.hit ? "hit" : "gap"}"><span>${escapeHtml(factor.label)}</span><strong>${escapeHtml(factor.value)}</strong><small>${escapeHtml(factor.note)}</small></article>`).join("")}</div>` : "";
  els.profileTags.innerHTML = profile.tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join("");
  els.profileStats.innerHTML = profileStats(profile.stats);
  els.profileBody.innerHTML = profileSections(profile.sections);
  els.profileActions.innerHTML = profile.actions.map((action) => `<span>${escapeHtml(action)}</span>`).join("");
  els.profileModal.hidden = false;
}

function investorPersona(investor, ctx) {
  const history = (investor.investment_history || []).filter((item) => item.company_name || item.date || item.round);
  const roundCounts = new Map();
  const yearCounts = new Map();
  history.forEach((item) => {
    const round = item.round || "轮次未披露";
    roundCounts.set(round, (roundCounts.get(round) || 0) + 1);
    const year = String(item.date || "").slice(0, 4);
    if (year) yearCounts.set(year, (yearCounts.get(year) || 0) + 1);
  });
  const amountDisclosed = history.filter((item) => item.investor_amount && !/^0(?:\.0+)?$/.test(String(item.investor_amount).trim())).length;
  const ownershipDisclosed = history.filter((item) => item.ownership).length;
  const recentHistory = history.slice(0, 8).map((item) => {
    const investorAmount = item.investor_amount && !/^0(?:\.0+)?$/.test(String(item.investor_amount).trim()) ? item.investor_amount : "未披露";
    const estimate = item.deal_estimate && item.deal_estimate !== item.investor_amount ? ` · 交易规模参考 ${item.deal_estimate}` : "";
    const ownership = item.ownership ? ` · 持股 ${item.ownership}` : " · 持股未披露";
    return `${item.date || "日期未披露"} · ${item.company_name || "被投企业未披露"} · ${item.round || "轮次未披露"} · 本机构投资 ${investorAmount}${estimate}${ownership}`;
  });
  const roundHistory = [...roundCounts.entries()].sort((a, b) => b[1] - a[1]).map(([round, count]) => `${round}：${count} 笔`);
  const annualHistory = [...yearCounts.entries()].sort((a, b) => b[0].localeCompare(a[0])).map(([year, count]) => `${year} 年：${count} 笔`);
  const tags = [
    investor.preferred_types || "投资类型待补充",
    investor.preferred_industry || investor.preferred_verticals || "行业偏好未披露",
    investor.city || investor.preferred_geography || investor.country || "地域泛化",
  ].filter(Boolean).slice(0, 5);
  const industryText = investor.preferred_industry || investor.preferred_verticals || "行业偏好未披露";
  const geoText = [investor.country, investor.city, investor.preferred_geography].filter(Boolean).join(" / ") || "暂无明确地域字段";
  const stageText = investor.preferred_types || "未披露";
  const preferenceText = `${investor.preferred_industry || ""} ${investor.preferred_verticals || ""} ${investor.preferred_types || ""}`;
  const geographyText = `${investor.country || ""} ${investor.city || ""} ${investor.preferred_geography || ""}`;
  const industryHit = Boolean((investor.preferred_industry || investor.preferred_verticals) && textMatches(preferenceText, ctx.industry));
  const stageHit = textMatches(preferenceText, ctx.stage) || textMatches(preferenceText, normalizeStage(ctx.stage));
  const metroHit = Boolean(ctx.metro && textMatches(geographyText, ctx.metro));
  const countryHit = geographyText.toLowerCase().includes(ctx.dataset === "china" ? "china" : "united states");
  const sameStageInvestments = history.filter((item) => textMatches(item.round, ctx.stage) || textMatches(item.round, normalizeStage(ctx.stage))).length;
  const matchFactors = [
    industryHit
      ? { hit: true, label: "行业", value: `关注${ctx.industry}`, note: "机构披露的行业偏好与公司业务一致" }
      : { hit: false, label: "行业", value: "偏好尚不明确", note: investor.preferred_industry || investor.preferred_verticals ? "已披露偏好与公司行业不完全一致" : "机构未披露行业偏好，需进一步确认" },
    metroHit
      ? { hit: true, label: "地区", value: `覆盖${ctx.metro}`, note: "机构的投资地域覆盖公司所在地" }
      : countryHit
        ? { hit: true, label: "地区", value: "覆盖国内项目", note: "国家范围一致，城市偏好仍需确认" }
        : { hit: false, label: "地区", value: "地域尚未匹配", note: "现有记录未体现对公司所在地的投资偏好" },
    stageHit
      ? { hit: true, label: "阶段", value: `覆盖${normalizeStage(ctx.stage)}`, note: sameStageInvestments ? `历史中有 ${sameStageInvestments} 笔相近轮次投资` : "机构偏好包含公司当前阶段" }
      : { hit: false, label: "阶段", value: "阶段偏好未命中", note: "现有记录未显示对公司当前阶段的明确偏好" },
    { hit: Number(investor.total_investments || 0) >= 5, label: "投资经验", value: `已记录 ${Number(investor.total_investments || history.length)} 笔投资`, note: Number(investor.total_investments || 0) >= 5 ? "有足够历史记录用于核对投资风格" : "历史投资样本较少，判断依据有限" },
  ];
  const matchedLabels = matchFactors.filter((item) => item.hit).map((item) => item.label);
  return {
    kicker: "投资机构档案",
    title: investorDisplayName(investor),
    subtitle: `${industryText} · ${stageText}`,
    score: investor.score,
    scoreLabel: "历史投资",
    scoreText: `${Number(investor.total_investments || history.length)} 笔投资`,
    match: {
      summary: matchedLabels.length ? `主要依据是${matchedLabels.join("、")}。未命中的条件保留在下方，便于进一步核实。` : "现有数据没有发现明确的偏好命中，建议先核实机构的行业、地域和阶段要求。",
      factors: matchFactors,
    },
    tags,
    stats: [
      ["地域", geoText],
      ["偏好阶段/类型", stageText],
      ["金额已披露", `${amountDisclosed}/${history.length} 笔`],
      ["持股已披露", `${ownershipDisclosed}/${history.length} 笔`],
    ],
    sections: [
      {
        title: "最近投资记录",
        items: recentHistory.length ? recentHistory : ["暂无逐笔投资记录"],
      },
      {
        title: "投资轮次",
        items: roundHistory.length ? roundHistory : ["暂无轮次记录"],
      },
      {
        title: "年度投资数量",
        items: annualHistory.length ? annualHistory : ["暂无投资日期记录"],
      },
    ],
    actions: [],
  };
}

function partnerPersona(partner, ctx) {
  const industries = shortList(partner.industries) || ctx.industry || "行业待补充";
  const metros = shortList(partner.metros) || ctx.metro || "地区待补充";
  const stages = shortList(partner.stages) || ctx.stage || "阶段待补充";
  const eventTypes = shortList(partner.event_types) || "历史事件";
  const relationHit = companyCounterparties(ctx).has(partner.partner_id);
  const tags = [
    scoreLevel(partner.score),
    relationHit ? "目标公司历史关联" : "相似样本关联",
    Number(partner.finance_count || 0) > 0 ? "融资相关" : "业务事件相关",
    industries,
    metros,
  ].filter(Boolean).slice(0, 5);
  return {
    kicker: "合作伙伴画像",
    title: partner.partner_id,
    subtitle: `${scoreLevel(partner.score)} · ${industries}`,
    score: partner.score,
    tags,
    stats: [
      ["历史事件", `${Number(partner.event_count || 0)} 次`],
      ["融资相关", `${Number(partner.finance_count || 0)} 次`],
      ["常见地区", metros],
      ["事件类型", eventTypes],
    ],
    sections: [
      {
        title: "画像判断",
        items: [
          relationHit ? "该对象与目标公司存在历史关联，可优先核实合作机会。" : "该对象曾与相似公司发生关联，可作为潜在合作线索。",
          `主要出现在 ${industries} / ${metros} / ${stages} 相关样本中，和当前公司条件有可解释的交集。`,
          Number(partner.finance_count || 0) > 0 ? "曾参与融资相关事件，可能带来资本、渠道或战略协同资源。" : "当前更偏业务协同线索，融资价值需要二次确认。",
        ],
      },
      {
        title: "合作切入",
        items: [
          `建议以 ${ctx.industry} 场景中的联合客户、渠道互换或试点项目作为第一轮沟通主题。`,
          `如果公司当前 runway 为 ${ctx.runway} 个月，可以优先谈能在 4-8 周内验证价值的小合作。`,
          `团队规模 ${ctx.employees} 人，适合选择低集成成本、短周期的合作方式。`,
        ],
      },
      {
        title: "风险提醒",
        items: [
          "历史关联不代表当前合作意愿，仍需确认联系人和近期业务重点。",
          Number(partner.event_count || 0) >= 20 ? "样本活跃度高，但也可能代表关系类型复杂，建议先明确合作目标。" : "样本量不高，适合作为备选合作画像而不是唯一依据。",
        ],
      },
    ],
    actions: ["整理合作提案", "确认联系人", "设计 4 周试点方案"],
  };
}

function openMatchProfile(type, id) {
  if (!state.data || !id) return;
  const ctx = selectedContext();
  if (type === "investor") {
    const investor = matchInvestors(ctx).find((item) => item.investor_id === id);
    if (investor) renderProfile(investorPersona(investor, ctx));
  }
  if (type === "partner") {
    const partner = matchPartners(ctx).find((item) => item.partner_id === id);
    if (partner) renderProfile(partnerPersona(partner, ctx));
  }
}

function renderInvestors(ctx) {
  const investors = matchInvestors(ctx);
  els.investorMeta.textContent = `${investors.length} 个推荐`;
  els.investorMatches.innerHTML = investors.map((investor) => card({
    type: "investor",
    id: investor.investor_id,
    title: investorDisplayName(investor),
    score: investor.score,
    meta: `${investor.country || "未知地区"} · ${investor.preferred_types || "投资偏好待补充"}`,
    detail: investor.preferred_industry || investor.preferred_verticals || "暂无行业偏好文本",
    reasons: investor.reasons,
  })).join("");
}

function card(item) {
  return `
    <article class="match-card">
      <div>
        <strong>${escapeHtml(item.title)}</strong>
        <p>${escapeHtml(item.meta)}</p>
        <p>${escapeHtml(item.detail)}</p>
        <div class="reason-list">${(item.reasons.length ? item.reasons : ["样本画像接近"]).map((reason) => `<span>${escapeHtml(reason)}</span>`).join("")}</div>
      </div>
      <div class="match-card-side">
        <b>${escapeHtml(item.score)}分</b>
        <button class="ghost-button match-info-button" type="button" data-profile-type="${escapeHtml(item.type)}" data-profile-id="${escapeHtml(item.id)}">查看信息</button>
      </div>
    </article>
  `;
}

function stageIndex(value) {
  return defaultStages.indexOf(normalizeStage(value));
}

function median(values) {
  const clean = values.filter(Number.isFinite).sort((a, b) => a - b);
  return clean.length ? clean[Math.floor((clean.length - 1) / 2)] : 0;
}

function financingJourney(ctx) {
  const currentIndex = Math.max(0, stageIndex(ctx.stage));
  const byCompany = new Map();
  state.data.timeline_events
    .filter((event) => event.dataset === ctx.dataset && isUsableFundingEvent(event) && event.company_id)
    .forEach((event) => {
      const idx = stageIndex(event.stage);
      if (idx < 0 || idx >= defaultStages.length) return;
      const rows = byCompany.get(event.company_id) || [];
      rows.push({ ...event, stageIndex: idx });
      byCompany.set(event.company_id, rows);
    });

  let cohort = [...byCompany.entries()].filter(([, rows]) => rows.some((row) => row.stageIndex === currentIndex));
  const matched = cohort.filter(([, rows]) => rows.some((row) => emptyOrMatches(row.industry, ctx.industry)));
  if (matched.length >= 12) cohort = matched;

  const progressed = [];
  const amounts = [];
  const intervals = [];
  const futureRoundCounts = [];
  cohort.forEach(([companyId, rows]) => {
    const currentRows = rows.filter((row) => row.stageIndex === currentIndex).sort((a, b) => dateValue(a.date) - dateValue(b.date));
    const futureRows = rows.filter((row) => row.stageIndex > currentIndex).sort((a, b) => dateValue(a.date) - dateValue(b.date));
    if (!futureRows.length) return;
    progressed.push(companyId);
    futureRoundCounts.push(new Set(futureRows.map((row) => row.stageIndex)).size);
    const firstFuture = futureRows[0];
    const lastCurrent = currentRows.at(-1);
    if (Number(firstFuture.amount_usd || 0) > 0) amounts.push(toMillions(firstFuture.amount_usd));
    if (lastCurrent?.date && firstFuture.date) {
      const days = (dateValue(firstFuture.date) - dateValue(lastCurrent.date)) / 86400000;
      if (days > 0 && days < 3650) intervals.push(days);
    }
  });

  const baseProbability = cohort.length ? progressed.length / cohort.length : 0;
  const conditionLift = (ctx.runway >= 12 ? 0.04 : ctx.runway < 6 ? -0.07 : 0)
    + (ctx.employees >= 12 ? 0.03 : -0.03)
    + (state.selectedRoles.has("财务") ? 0.02 : 0)
    + (state.selectedRoles.has("销售") ? 0.025 : 0);
  let nextProbability = clampValue(baseProbability + conditionLift, 0.03, 0.92);
  let amountStats = quantiles(amounts);
  const fallbackInterval = Number((state.data.finance_interval_baseline || []).find((row) => row.dataset === ctx.dataset)?.median_days_to_next_finance || 540);
  let daysToNext = median(intervals) || fallbackInterval;
  const modelPrediction = (window.ESCP_VENTURE_MODEL_PREDICTIONS || []).find(
    (row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId,
  );
  const verifiedRounds = companyRecognizedRounds(ctx.dataset, ctx.companyId);
  const hasVerifiedARound = verifiedRounds.some((row) => stageIndex(row.normalizedStage) >= stageIndex("A轮"));
  const predictionReady = currentIndex >= stageIndex("A轮") && hasVerifiedARound;
  const appliedModelPrediction = predictionReady ? modelPrediction : null;
  if (appliedModelPrediction) {
    nextProbability = clampValue(Number(appliedModelPrediction.next_round_probability_24m), 0.01, 0.99);
    daysToNext = Number(appliedModelPrediction.predicted_days_to_next) || daysToNext;
    const predictedAmount = Number(appliedModelPrediction.predicted_next_amount_m || 0);
    if (predictedAmount > 0) {
      amountStats = { count: 1, p25: predictedAmount * 0.7, median: predictedAmount, p75: predictedAmount * 1.35 };
    }
  }
  const outcome = (state.data.company_outcomes || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId);
  const terminal = Boolean(outcome?.listed || outcome?.acquired);
  if (terminal) {
    nextProbability = 0;
    amountStats = null;
    daysToNext = 0;
  }
  const progress = currentIndex / Math.max(1, defaultStages.length - 2);
  const ipoProbability = outcome?.listed ? 1 : clampValue(0.012 + progress * 0.055 + conditionLift * 0.18, 0.005, 0.12);
  const acquisitionProbability = outcome?.acquired ? 1 : clampValue(0.09 + progress * 0.09 + conditionLift * 0.25, 0.04, 0.26);
  const risk = (state.data.due_diligence_profiles || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId);
  const companyEvents = companyTimelineEvents(ctx);
  const latestEventDate = Math.max(0, ...companyEvents.map((event) => dateValue(event.date)));
  const recentEvents = companyEvents.filter((event) => latestEventDate && latestEventDate - dateValue(event.date) <= 365 * 86400000).length;
  const riskEvents = companyEvents.filter((event) => ["abnormal_listing", "penalty", "dishonesty", "revocation"].includes(norm(event.event_type))).length;
  return {
    currentIndex,
    cohortSize: cohort.length,
    progressed: progressed.length,
    nextProbability,
    amountStats,
    daysToNext,
    futureRounds: terminal ? 0 : Math.max(1, Math.round(median(futureRoundCounts) || Math.max(1, 4 - currentIndex / 2))),
    ipoProbability,
    acquisitionProbability,
    outcome,
    terminal,
    riskScore: Number(risk?.risk_score || 0),
    industryMatched: matched.length >= 12,
    modelPrediction: appliedModelPrediction,
    predictionReady,
    verifiedRoundCount: verifiedRounds.length,
    recentEvents,
    riskEvents,
  };
}

function percent(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function fundingCurveData(ctx, journey) {
  const rows = state.data.timeline_events.filter((event) => event.dataset === ctx.dataset && isUsableFundingEvent(event));
  const byCompany = new Map();
  rows.forEach((event) => {
    if (!event.company_id) return;
    const idx = stageIndex(event.stage);
    if (idx < 0) return;
    const items = byCompany.get(event.company_id) || [];
    items.push({ ...event, stageIndex: idx });
    byCompany.set(event.company_id, items);
  });
  const cohort = [...byCompany.values()].filter((items) => items.some((item) => item.stageIndex === journey.currentIndex));
  const companyRounds = companyRecognizedRounds(ctx.dataset, ctx.companyId);
  const companyValuations = (state.data.valuation_benchmarks || []).filter(
    (row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId && row.source !== "benchmark" && Number(row.value || 0) > 0,
  );
  const stages = defaultStages.map((stage, idx) => {
    const stageRows = rows.filter((row) => stageIndex(row.stage) === idx && Number(row.amount_usd || 0) > 0);
    const industryRows = stageRows.filter((row) => emptyOrMatches(row.industry, ctx.industry));
    const amountRows = industryRows.length >= 5 ? industryRows : stageRows;
    let probability = 1;
    if (idx > journey.currentIndex) {
      if (idx === journey.currentIndex + 1) {
        probability = journey.nextProbability;
      } else {
        probability = cohort.length
          ? cohort.filter((items) => items.some((item) => item.stageIndex >= idx)).length / cohort.length
          : journey.nextProbability * Math.pow(0.68, idx - journey.currentIndex - 1);
        probability = Math.min(journey.nextProbability, probability || journey.nextProbability * Math.pow(0.68, idx - journey.currentIndex - 1));
      }
    }
    const facts = companyRounds.filter((row) => stageIndex(row.normalizedStage) === idx && dateValue(row.date) <= dateValue(companyRounds.findLast?.((item) => stageIndex(item.normalizedStage) === journey.currentIndex)?.date || companyRounds.at(-1)?.date));
    const fact = facts.at(-1);
    const directValues = companyValuations.filter((row) => stageIndex(row.stage) === idx).map((row) => toMillions(row.value));
    let amount = Number(fact?.amount_usd || 0) > 0 ? toMillions(fact.amount_usd) : quantiles(amountRows.map((row) => row.amount_usd))?.median || 0;
    if (idx > journey.currentIndex && Number(journey.amountStats?.median || 0) > 0) {
      const modelAmount = Number(journey.amountStats.median) * Math.pow(1.35, Math.max(0, idx - journey.currentIndex - 1));
      amount = idx === journey.currentIndex + 1 ? modelAmount : Math.max(amount, modelAmount);
    }
    return {
      stage,
      idx,
      probability: clampValue(probability, 0.01, 1),
      amount,
      valuation: median(directValues) || amount * (stageMultipliers[stage] || 12),
      valuationSource: directValues.length ? "直接估值" : "融资额×阶段倍数",
      fact: Boolean(fact && idx <= journey.currentIndex),
      factDate: fact?.date || "",
    };
  });
  stages.push({
    stage: "IPO / 并购",
    idx: stages.length,
    probability: clampValue(journey.ipoProbability + journey.acquisitionProbability, 0.01, 1),
    amount: 0,
    valuation: 0,
    exit: true,
  });
  for (let idx = journey.currentIndex + 2; idx < stages.length; idx += 1) {
    stages[idx].probability = Math.min(stages[idx].probability, stages[idx - 1].probability);
  }
  let runningValue = 0;
  stages.forEach((item, idx) => {
    if (item.exit) {
      item.valuation = Math.max(runningValue * 1.35, runningValue);
      item.valuationSource = "退出价值情景";
      return;
    }
    const growthFloor = runningValue ? runningValue * (idx <= journey.currentIndex ? 1.08 : 1.22) : 0;
    item.valuation = Math.max(item.valuation || 0, growthFloor, 1);
    runningValue = item.valuation;
  });
  return stages;
}

function companyHistoricalValuePoints(ctx) {
  const events = state.data.timeline_events
    .filter((event) => event.dataset === ctx.dataset && event.company_id === ctx.companyId && event.date && isStrictFinanceEvent(event))
    .sort((a, b) => dateValue(a.date) - dateValue(b.date));
  const grouped = new Map();
  events.forEach((event) => {
    const item = grouped.get(event.date) || { date: event.date, amount: 0, stage: "", rows: [], counterparties: new Set() };
    item.rows.push(event);
    if (event.counterparty_id) item.counterparties.add(event.counterparty_id);
    item.amount = Math.max(item.amount, toMillions(event.amount_usd));
    if (recognizedStage(event.stage)) item.stage = recognizedStage(event.stage);
    else if (!item.stage && event.stage) item.stage = event.stage;
    grouped.set(event.date, item);
  });
  const points = [...grouped.values()].map((item, idx) => {
    const normalized = recognizedStage(item.stage) || defaultStages[Math.min(defaultStages.length - 1, Math.max(1, idx))];
    const direct = (state.data.valuation_benchmarks || [])
      .filter((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId && row.source === "rongzi.value_number" && normalizeStage(row.stage) === normalized)
      .map((row) => toMillions(row.value));
    return {
      ...item,
      stage: recognizedStage(item.stage) || item.stage || "未标轮次",
      valuation: median(direct) || 0,
      direct: direct.length > 0,
      imputed: false,
      historical: true,
      recordCount: item.rows.length,
      counterpartyCount: item.counterparties.size,
    };
  });
  return points;
}

function renderFundingCurve(ctx, journey) {
  const completePath = fundingCurveData(ctx, journey);
  const data = completePath
    .filter((item) => item.exit || item.idx <= journey.currentIndex + (journey.terminal ? 0 : Math.max(1, journey.futureRounds)))
    .map((item, idx) => ({ ...item, sourceIndex: item.idx, idx }));
  const exitPoint = data.find((item) => item.exit);
  const lastFinancingPoint = data.filter((item) => !item.exit).at(-1);
  if (exitPoint && lastFinancingPoint) exitPoint.valuation = Math.max(lastFinancingPoint.valuation * 1.35, lastFinancingPoint.valuation);
  const historicalValues = companyHistoricalValuePoints(ctx);
  const visibleFuturePoints = data.filter((item) => !item.historical).length;
  const visualPointCount = historicalValues.length + Math.max(1, visibleFuturePoints);
  const width = Math.max(1050, 180 + visualPointCount * 175);
  const height = 330;
  const pad = { left: 70, right: 54, top: 42, bottom: 78 };
  const x = (idx) => pad.left + (idx / Math.max(1, data.length - 1)) * (width - pad.left - pad.right);
  const maxValuation = Math.max(...data.map((item) => item.valuation || 1), ...historicalValues.map((item) => item.valuation || item.amount || 1), 10);
  const logMax = Math.log10(maxValuation * 1.2);
  const yValue = (value) => pad.top + (1 - Math.log10(Math.max(1, value)) / Math.max(1, logMax)) * (height - pad.top - pad.bottom);
  const points = data.map((item) => ({ ...item, x: x(item.idx), y: yValue(item.valuation) }));
  const current = points[Math.min(journey.currentIndex, points.length - 2)];
  const boundaryX = current.x;
  const historyDates = historicalValues.map((item) => dateValue(item.date));
  const minHistoryDate = historyDates.length ? Math.min(...historyDates) : 0;
  const maxHistoryDate = historyDates.length ? Math.max(...historyDates) : 0;
  const firstKnownHistoryValue = historicalValues.find((item) => Number(item.valuation || item.amount || 0) > 0);
  let carriedHistoryValue = Number(firstKnownHistoryValue?.valuation || firstKnownHistoryValue?.amount || 1);
  const actualHistory = historicalValues.map((item, historyIndex) => {
    const disclosedValue = Number(item.valuation || item.amount || 0);
    if (disclosedValue > 0) carriedHistoryValue = disclosedValue;
    return ({
    ...item,
    referenceValue: carriedHistoryValue,
    valueSource: item.valuation ? "估值" : item.amount ? "融资金额" : "沿用最近已知值",
    amountEstimate: data.find((stage) => normalizeStage(stage.stage) === normalizeStage(item.stage))?.amount || journey.amountStats?.median || 0,
    x: historyDates.length === 1 ? boundaryX : pad.left + ((dateValue(item.date) - minHistoryDate) / Math.max(1, maxHistoryDate - minHistoryDate)) * (boundaryX - pad.left),
    y: yValue(carriedHistoryValue),
    factDate: item.date,
    fact: true,
    showLabel: false,
  })});
  let lastLabelX = -Infinity;
  actualHistory.forEach((point, index) => {
    const first = index === 0;
    const last = index === actualHistory.length - 1;
    const enoughFromPrevious = point.x - lastLabelX >= 145;
    const enoughFromLast = last || actualHistory.at(-1).x - point.x >= 145;
    point.showLabel = first || last || (enoughFromPrevious && enoughFromLast);
    if (point.showLabel) lastLabelX = point.x;
  });
  const path = (items) => items.map((point, idx) => `${idx ? "L" : "M"} ${point.x.toFixed(1)} ${point.y.toFixed(1)}`).join(" ");
  const history = actualHistory.length ? actualHistory : [current];
  const forecastAnchor = { ...current, x: boundaryX, y: history.at(-1)?.y || current.y, valuation: history.at(-1)?.referenceValue || history.at(-1)?.valuation || current.valuation };
  const forecast = [forecastAnchor, ...points.slice(journey.currentIndex + 1)];
  const displayPoints = [...history, ...forecast.slice(1)];
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((ratio) => Math.pow(10, logMax * ratio));
  els.fundingCurve.innerHTML = `
    <svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="从种子轮到退出的公司估值路径曲线">
      <defs>
        <linearGradient id="journeyArea" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="#2d66d9" stop-opacity="0.15" />
          <stop offset="100%" stop-color="#2d66d9" stop-opacity="0.01" />
        </linearGradient>
      </defs>
      ${journey.terminal ? "" : `<rect class="curve-zone" x="${current.x.toFixed(1)}" y="${pad.top}" width="${(width - pad.right - current.x).toFixed(1)}" height="${height - pad.top - pad.bottom}" />`}
      ${ticks.map((tick) => `<line class="curve-grid" x1="${pad.left}" y1="${yValue(tick)}" x2="${width - pad.right}" y2="${yValue(tick)}" /><text class="curve-axis-text" x="${pad.left - 10}" y="${yValue(tick) + 4}" text-anchor="end">${escapeHtml(formatMoney(tick))}</text>`).join("")}
      <text class="curve-axis-text" x="${pad.left}" y="${pad.top - 18}">估值/融资金额参考（对数轴）</text>
      <text class="curve-axis-text" x="${width - pad.right}" y="${pad.top - 18}" text-anchor="end">${journey.terminal ? "历史融资 · 已完成退出" : "历史实线 · 预测虚线"}</text>
      ${journey.terminal ? "" : `<path class="curve-area" d="${path(forecast)} L ${forecast.at(-1).x.toFixed(1)} ${height - pad.bottom} L ${forecast[0].x.toFixed(1)} ${height - pad.bottom} Z" />`}
      ${history.length > 1 ? `<path class="curve-history-line" d="${path(history)}" />` : ""}
      <path class="${journey.terminal ? "curve-history-line" : "curve-forecast-line"}" d="${path(forecast)}" />
      ${journey.terminal ? "" : `<line class="curve-boundary" x1="${current.x.toFixed(1)}" y1="${pad.top - 8}" x2="${current.x.toFixed(1)}" y2="${height - pad.bottom + 10}" /><text class="curve-axis-text" x="${Math.min(width - 90, current.x + 8)}" y="${pad.top - 14}">预测从这里开始</text>`}
      ${displayPoints.map((point) => `
        <g>
          <circle class="curve-node ${point.historical ? "" : "future"} ${point.historical && point.imputed ? "unrecorded" : ""} ${point.exit ? "exit" : ""}" cx="${point.x.toFixed(1)}" cy="${point.y.toFixed(1)}" r="${point.historical && point === history.at(-1) ? 7 : 5.5}"><title>${escapeHtml(point.historical ? `${formatDate(point.date)} · ${point.stage} · ${point.valueSource || "历史参考值"} ${formatMoney(point.referenceValue || point.valuation || 0)}` : `${point.stage} · 预测估值 ${formatMoney(point.valuation)}`)}</title></circle>
          ${!point.historical || point.showLabel ? `<text class="curve-stage-label" x="${point.x.toFixed(1)}" y="${height - 45}" text-anchor="middle">${escapeHtml(point.historical ? formatDate(point.date) : point.stage)}</text><text class="curve-value-label" x="${point.x.toFixed(1)}" y="${height - 28}" text-anchor="middle">${point.historical ? point.valuation ? `估值 ${escapeHtml(formatMoney(point.valuation))}` : point.amount ? `融资参考 ${escapeHtml(formatMoney(point.amount))}` : `参考值 ${escapeHtml(formatMoney(point.referenceValue || 0))}` : `估值 ${escapeHtml(formatMoney(point.valuation))}`}</text><text class="curve-value-label" x="${point.x.toFixed(1)}" y="${height - 11}" text-anchor="middle">${point.exit ? "退出价值参考" : point.historical ? escapeHtml(point.stage || "历史融资") : `预测融资 ${escapeHtml(formatMoney(point.amount || journey.amountStats?.median || 0))}`}</text>` : ""}
        </g>
      `).join("")}
    </svg>
  `;
  els.fundingCurve.classList.toggle("scrollable", visualPointCount > 7);
  requestAnimationFrame(() => {
    if (els.fundingCurve.scrollWidth > els.fundingCurve.clientWidth) {
      els.fundingCurve.scrollLeft = els.fundingCurve.scrollWidth - els.fundingCurve.clientWidth;
    }
  });
}

function renderHistoricalFinance(ctx) {
  const events = state.data.timeline_events
    .filter((event) => event.dataset === ctx.dataset && event.company_id === ctx.companyId && event.date && isStrictFinanceEvent(event))
    .sort((a, b) => dateValue(a.date) - dateValue(b.date));
  const byDate = new Map();
  events.forEach((event) => {
    const item = byDate.get(event.date) || { date: event.date, rows: [], investments: [], amount: 0, stage: "" };
    item.rows.push(event);
    item.amount = Math.max(item.amount, toMillions(event.amount_usd));
    if (recognizedStage(event.stage)) item.stage = recognizedStage(event.stage);
    else if (!item.stage && event.stage) item.stage = event.stage;
    byDate.set(event.date, item);
  });
  (state.data.investors || []).forEach((investor) => {
    (investor.investment_history || []).forEach((record) => {
      if (record.company_id !== ctx.companyId || !record.date) return;
      const item = byDate.get(record.date) || { date: record.date, rows: [], investments: [], amount: 0, stage: record.round || "" };
      item.investments.push({ ...record, investor_name: investorDisplayName(investor) });
      if (!item.stage && record.round) item.stage = record.round;
      byDate.set(record.date, item);
    });
  });
  const rounds = [...byDate.values()].sort((a, b) => dateValue(a.date) - dateValue(b.date));
  rounds.forEach((item, idx) => {
    const normalized = recognizedStage(item.stage) || defaultStages[Math.min(defaultStages.length - 1, Math.max(1, idx))];
    const direct = (state.data.valuation_benchmarks || [])
      .filter((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId && row.source === "rongzi.value_number" && normalizeStage(row.stage) === normalized)
      .map((row) => toMillions(row.value));
    item.valuation = median(direct) || 0;
    item.direct = direct.length > 0;
    item.displayStage = recognizedStage(item.stage) || item.stage || "未标轮次";
  });

  els.historicalFinance.hidden = !rounds.length;
  els.historicalFinance.open = rounds.length > 0;
  els.historicalFinanceEvents.innerHTML = rounds.length
    ? rounds.map((item) => {
      const investments = item.investments || [];
      const disclosed = investments.filter((row) => row.investor_amount && !/^0(?:\.0+)?$/.test(String(row.investor_amount).trim()));
      const investorLines = investments.slice(0, 3).map((row) => `${row.investor_name}：${row.investor_amount || "金额未披露"}${row.ownership ? ` · 持股 ${row.ownership}` : ""}`);
      const amountText = item.amount ? formatMoney(item.amount) : disclosed.length ? disclosed.map((row) => row.investor_amount).join(" / ") : "金额未披露";
      return `<div class="history-event-chip"><strong>${escapeHtml(formatDate(item.date))} · ${escapeHtml(item.displayStage)}</strong><span>融资 ${escapeHtml(amountText)}</span><small>${item.valuation ? `估值 ${escapeHtml(formatMoney(item.valuation))}` : "估值未披露"}</small>${investorLines.length ? `<em>${investorLines.map(escapeHtml).join("<br>")}</em>` : ""}</div>`;
    }).join("")
    : `<div class="empty-chart">该公司暂无历史融资事件</div>`;
}

function renderDecisionGuide(ctx, journey) {
  const investor = state.persona === "investor";
  const valuation = estimateValuation(ctx);
  const nextStage = defaultStages[Math.min(defaultStages.length - 1, journey.currentIndex + 1)];
  const months = Math.max(1, Math.round(journey.daysToNext / 30));
  const amount = formatMoney(journey.amountStats?.median || 0);
  const exitProbability = clampValue(journey.ipoProbability + journey.acquisitionProbability, 0, 1);
  const dossier = (state.data.company_dossiers || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  const companyOutcome = (state.data.company_outcomes || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  const diligence = (state.data.due_diligence_profiles || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  const fundingByDate = new Map();
  companyTimelineEvents(ctx).filter(isUsableFundingEvent).forEach((event) => {
    if (!event.date) return;
    fundingByDate.set(event.date, Math.max(fundingByDate.get(event.date) || 0, toMillions(event.amount_usd)));
  });
  const disclosedFunding = [...fundingByDate.values()].reduce((sum, value) => sum + value, 0);
  const steps = investor
    ? [
        ["STEP 1", "确认投资时点", `历史事实截至 ${normalizeStage(ctx.stage)}`],
        ["STEP 2", "判断价值与续融", `估值 ${formatMoney(valuation.median)} · 续融 ${percent(journey.nextProbability)}`],
        ["STEP 3", "评估退出回报", `IPO/并购 ${percent(exitProbability)} · 查看 MOIC`],
      ]
    : [
        ["STEP 1", "确认公司现状", `历史事实截至 ${normalizeStage(ctx.stage)}`],
        ["STEP 2", "查看下一轮", `${percent(journey.nextProbability)} · ${months}个月 · ${amount}`],
        ["STEP 3", "执行融资行动", "筛选并联系投资人"],
      ];
  els.decisionSteps.innerHTML = steps.map(([step, title, note]) => `<div class="decision-step"><span>${escapeHtml(step)}</span><strong>${escapeHtml(title)}</strong><small>${escapeHtml(note)}</small></div>`).join("");
  els.summaryKicker.textContent = "公司概览";
  els.summaryTitle.textContent = companyDisplayName(ctx.dataset, ctx.companyId);
  const overviewItems = [
    ["经营状态", dossier.company_status || "未披露"],
    ["成立时间", dossier.establish_date ? formatDate(dossier.establish_date) : "未披露"],
    ["当前阶段", companyOutcome.listed ? "已上市" : companyOutcome.acquired ? "已并购退出" : normalizeStage(ctx.stage)],
    ["累计披露融资", disclosedFunding > 0 ? formatMoney(disclosedFunding) : "未披露"],
    ["营业收入", dossier.revenue != null ? formatStatementMoney(dossier.revenue, dossier.currency) : "未披露"],
    ["尽调风险", diligence.risk_score != null ? `${Number(diligence.risk_score)}/100` : "未披露"],
  ];
  els.companyOverviewMeta.innerHTML = overviewItems.map(([label, value]) => `<div><span>${escapeHtml(label)}</span><b>${escapeHtml(value)}</b></div>`).join("");
  els.summaryText.textContent = investor
    ? `成功退出概率约 ${percent(exitProbability)}。先核验历史估值与融资事实，再结合投资金额、持股比例和条款查看风险调整回报。`
    : `下一轮融资成功率约为 ${percent(journey.nextProbability)}。核对历史数据后，可进一步筛选投资人。`;
}

function renderForecastMatrix(ctx, journey) {
  const earlyScenario = journey.currentIndex < 3;
  if (els.forecastMode) els.forecastMode.textContent = earlyScenario ? "早期阶段 · 参考测算" : journey.modelPrediction ? "历史数据验证" : "同阶段公司参考";
  const history = companyHistoricalValuePoints(ctx);
  const curve = fundingCurveData(ctx, journey);
  const future = journey.terminal ? [] : curve.filter((item) => !item.exit && item.idx > journey.currentIndex).slice(0, Math.max(1, journey.futureRounds));
  const rows = [];
  const missingStages = [];
  defaultStages.slice(0, journey.currentIndex + 1).forEach((stage) => {
    const facts = history.filter((item) => recognizedStage(item.stage) === stage);
    if (!facts.length) {
      missingStages.push(stage);
      return;
    }
    facts.forEach((item) => rows.push({
      type: "history",
      stage,
      status: `${item.recordCount}条记录${item.counterpartyCount ? ` · ${item.counterpartyCount}家机构` : ""}`,
      probability: "—",
      time: formatDate(item.date),
      rawDate: item.date,
      amount: item.amount ? formatMoney(item.amount) : "",
      valuation: item.valuation ? `${formatMoney(item.valuation)} · 直接估值` : "",
    }));
  });
  if (missingStages.length) rows.unshift({ type: "missing-summary", stages: missingStages });
  history.filter((item) => !recognizedStage(item.stage)).forEach((item) => {
    rows.push({
      type: "history",
      stage: `${item.stage || "股权融资"}（轮次未披露）`,
      status: `${item.recordCount}条记录${item.counterpartyCount ? ` · ${item.counterpartyCount}家机构` : ""}`,
      probability: "—",
      time: formatDate(item.date),
      rawDate: item.date,
      amount: item.amount ? formatMoney(item.amount) : "",
      valuation: item.valuation ? `${formatMoney(item.valuation)} · 直接估值` : "",
    });
  });
  future.forEach((item, idx) => {
    const months = Math.max(1, Math.round((journey.daysToNext / 30) * (idx + 1) * (1 + idx * 0.12)));
    rows.push({
      type: "future",
      stage: item.stage,
      status: earlyScenario ? "参考" : "预测",
      probability: percent(item.probability),
      time: formatDate(addMonths(new Date(), months).toISOString()),
      amount: `${formatMoney(item.amount || journey.amountStats?.median || 0)} · 预计`,
      valuation: formatMoney(item.valuation),
    });
  });
  const historyDetails = (date) => {
    const events = companyTimelineEvents(ctx).filter((event) => event.date === date && isUsableFundingEvent(event));
    const investmentMap = new Map();
    (state.data.investors || []).forEach((investor) => {
      (investor.investment_history || []).forEach((record) => {
        if (record.company_id !== ctx.companyId || record.date !== date) return;
        const candidate = { ...record, investor_name: investorDisplayName(investor) };
        const current = investmentMap.get(candidate.investor_name);
        const disclosed = (row) => [row.investor_amount, row.deal_estimate, row.ownership].filter((value) => value && value !== "未披露").length;
        if (!current || disclosed(candidate) > disclosed(current)) investmentMap.set(candidate.investor_name, candidate);
      });
    });
    const investments = [...investmentMap.values()];
    const eventGroups = new Map();
    events.forEach((event) => {
      const stage = normalizeStage(event.stage) || eventLabel(event);
      const amount = Number(event.amount_usd || 0) > 0 ? formatMoney(toMillions(event.amount_usd)) : "未披露";
      const key = `${stage}|${eventLabel(event)}|${amount}`;
      const current = eventGroups.get(key) || { stage, type: eventLabel(event), amount, count: 0 };
      current.count += 1;
      eventGroups.set(key, current);
    });
    const eventHtml = eventGroups.size ? [...eventGroups.values()].map((event) => `
      <div class="table-history-event"><strong>${escapeHtml(event.stage)}</strong><span>${escapeHtml(event.type)}</span><span>${escapeHtml(event.amount)}</span>${event.count > 1 ? `<i>原始记录 × ${event.count}</i>` : ""}</div>
    `).join("") : `<div class="table-history-event"><strong>融资事件</strong><span>详细字段未披露</span></div>`;
    const investmentHtml = investments.length ? investments.map((record) => `
      <div><strong>${escapeHtml(record.investor_name)}</strong><span>${escapeHtml(record.investor_amount || "投资额未披露")}</span><span>${escapeHtml(record.deal_estimate || "交易规模未披露")}</span><span>${escapeHtml(record.ownership || "持股未披露")}</span></div>
    `).join("") : `<div><strong>投资机构未披露</strong><span>仅有融资事件记录</span></div>`;
    return `<section class="table-history-detail"><header><b>${escapeHtml(formatDate(date))}</b><span>${events.length} 条底层记录 · ${investments.length} 家机构</span></header><div class="table-history-events">${eventHtml}</div><div class="table-history-investments">${investmentHtml}</div></section>`;
  };
  els.forecastTableBody.innerHTML = rows.map((row, rowIndex) => row.type === "missing-summary" ? `
    <tr class="missing-summary-row"><td colspan="6"><div class="missing-stage-strip"><span>历史无记录</span>${row.stages.map((stage) => `<i>${escapeHtml(stage)}</i>`).join("")}</div></td></tr>` : `
    <tr class="${row.type}-row">
      <td><strong>${escapeHtml(row.stage)}</strong></td>
      <td>${row.status ? row.type === "history" ? `<button class="table-status fact history-record-button" type="button" data-history-detail="history-detail-${rowIndex}" aria-expanded="false">${escapeHtml(row.status)} <i>查看</i></button>` : `<span class="table-status ${earlyScenario ? "scenario" : "predict"}">${escapeHtml(row.status)}</span>` : ""}</td>
      <td>${escapeHtml(row.probability)}</td><td>${escapeHtml(row.time)}</td><td>${escapeHtml(row.amount)}</td><td>${escapeHtml(row.valuation)}</td>
    </tr>${row.type === "history" ? `<tr class="history-detail-row" id="history-detail-${rowIndex}" hidden><td colspan="6">${historyDetails(row.rawDate)}</td></tr>` : ""}`).join("");
  const exitProbability = clampValue(journey.ipoProbability + journey.acquisitionProbability, 0, 1);
  els.exitOutcomes.innerHTML = [
    [journey.outcome?.listed ? "IPO退出 · 已发生" : "IPO退出 · 参考值", percent(journey.ipoProbability), journey.outcome?.listed ? "已有上市记录" : "参考历史总体水平"],
    [journey.outcome?.acquired ? "并购退出 · 已发生" : "并购退出 · 参考值", percent(journey.acquisitionProbability), journey.outcome?.acquired ? "已有并购记录" : "包括产业收购和财务收购"],
    ["退出时间窗口", "7–10年", `综合成功退出概率 ${percent(exitProbability)}`],
  ].map(([label, value, note]) => `<div class="exit-outcome"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong><small>${escapeHtml(note)}</small></div>`).join("");
}

function renderNetworkLegacy(ctx) {
  if (state.networkCompanyId !== ctx.companyId) {
    state.networkCompanyId = ctx.companyId;
    state.networkNodeId = "company";
    state.networkRoundOnly = false;
    state.networkExpandedInvestors.clear();
  }
  const talent = (state.data.talent_profiles || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  const diligence = (state.data.due_diligence_profiles || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  const events = companyTimelineEvents(ctx);
  const companyName = companyDisplayName(ctx.dataset, ctx.companyId);
  const companyNode = {
    id: "company", type: "company", label: companyName, sublabel: recognizedStage(ctx.stage) || "轮次未披露",
    detail: `<h4>${escapeHtml(companyName)}</h4><span class="network-type company">目标公司</span><dl><div><dt>当前阶段</dt><dd>${escapeHtml(recognizedStage(ctx.stage) || "未披露")}</dd></div><div><dt>历史事件</dt><dd>${events.length} 条</dd></div><div><dt>风险分</dt><dd>${Number(diligence.risk_score || 0)}/100</dd></div></dl>`,
  };
  const investorNodes = (state.data.investors || []).filter((investor) => investor.dataset === ctx.dataset)
    .map((investor) => ({ investor, records: (investor.investment_history || []).filter((record) => record.company_id === ctx.companyId) }))
    .filter((item) => item.records.length)
    .sort((a, b) => b.records.length - a.records.length)
    .slice(0, 6)
    .map(({ investor, records }, index) => {
      const latest = [...records].sort((a, b) => String(b.date).localeCompare(String(a.date)))[0] || {};
      const disclosed = records.filter((record) => record.investor_amount).length;
      return {
        id: `investor-${index}`, type: "investor", label: investorDisplayName(investor), sublabel: `${records.length} 笔投资`, relation: latest.round || "参与融资",
        detail: `<h4>${escapeHtml(investorDisplayName(investor))}</h4><span class="network-type investor">投资机构</span><dl><div><dt>投资记录</dt><dd>${records.length} 笔</dd></div><div><dt>金额披露</dt><dd>${disclosed} 笔</dd></div><div><dt>最近投资</dt><dd>${escapeHtml(latest.date ? formatDate(latest.date) : "未披露")}</dd></div><div><dt>最近轮次</dt><dd>${escapeHtml(latest.round || "未披露")}</dd></div></dl>`,
      };
    });
  const roleCounts = new Map();
  events.filter((event) => ["hire", "executive_report", "legal_appointment"].includes(norm(event.event_type))).forEach((event) => {
    const role = String(event.stage || event.role_or_dealtype || "人员任职").split(/[，,、]/)[0].trim() || "人员任职";
    roleCounts.set(role, (roleCounts.get(role) || 0) + 1);
  });
  const personNodes = [...roleCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5).map(([role, count], index) => ({
    id: `person-${index}`, type: "person", label: role, sublabel: `${count} 条任职记录`, relation: "任职",
    detail: `<h4>${escapeHtml(role)}</h4><span class="network-type person">人员与治理</span><dl><div><dt>任职记录</dt><dd>${count} 条</dd></div><div><dt>姓名</dt><dd>数据未提供</dd></div></dl><p>源数据仅保留该职务对应的匿名关系，未展示数字编号。</p>`,
  }));
  const shareholderGroups = new Map();
  events.filter((event) => ["shareholder_appointment", "shareholder_removal"].includes(norm(event.event_type))).forEach((event) => {
    const label = String(event.stage || "股东类型未披露").trim() || "股东类型未披露";
    const current = shareholderGroups.get(label) || { records: 0, entities: new Set(), exits: 0 };
    current.records += 1;
    if (event.counterparty_id) current.entities.add(event.counterparty_id);
    if (norm(event.event_type) === "shareholder_removal") current.exits += 1;
    shareholderGroups.set(label, current);
  });
  const shareholderNodes = [...shareholderGroups.entries()].sort((a, b) => b[1].records - a[1].records).slice(0, 4).map(([label, info], index) => ({
    id: `shareholder-${index}`, type: "shareholder", label, sublabel: `${info.entities.size || info.records} 个关系主体`, relation: info.exits ? `股东关系 · ${info.exits} 次退出` : "股东关系",
    detail: `<h4>${escapeHtml(label)}</h4><span class="network-type shareholder">股东关系</span><dl><div><dt>关系主体</dt><dd>${info.entities.size || info.records} 个</dd></div><div><dt>底层记录</dt><dd>${info.records} 条</dd></div><div><dt>退出记录</dt><dd>${info.exits} 条</dd></div><div><dt>名称</dt><dd>数据未提供</dd></div></dl>`,
  }));
  const nodes = [companyNode, ...investorNodes, ...personNodes, ...shareholderNodes];
  const visible = nodes.filter((node) => node.type === "company" || state.networkFilter === "all" || node.type === state.networkFilter);
  const placeColumn = (items, x, fromY, toY) => items.forEach((node, index) => {
    node.x = x;
    node.y = items.length === 1 ? (fromY + toY) / 2 : fromY + ((toY - fromY) * index) / Math.max(1, items.length - 1);
  });
  companyNode.x = 450; companyNode.y = 210;
  placeColumn(visible.filter((node) => node.type === "investor"), 105, 62, 352);
  placeColumn(visible.filter((node) => node.type === "person"), 795, 62, 352);
  const visibleShareholders = visible.filter((node) => node.type === "shareholder");
  visibleShareholders.forEach((node, index) => { node.x = 285 + index * (330 / Math.max(1, visibleShareholders.length - 1)); node.y = 425; });
  const edgeHtml = visible.filter((node) => node.type !== "company").map((node) => `<g class="knowledge-edge ${node.type}"><line x1="${companyNode.x}" y1="${companyNode.y}" x2="${node.x}" y2="${node.y}"/><text x="${(companyNode.x + node.x) / 2}" y="${(companyNode.y + node.y) / 2 - 6}">${escapeHtml(node.relation)}</text></g>`).join("");
  const nodeHtml = visible.map((node) => {
    const width = node.type === "company" ? 190 : 150;
    const height = node.type === "company" ? 76 : 62;
    const label = node.label.length > 14 ? `${node.label.slice(0, 13)}…` : node.label;
    return `<g class="knowledge-node ${node.type} ${state.networkNodeId === node.id ? "selected" : ""}" data-network-node="${escapeHtml(node.id)}" transform="translate(${node.x - width / 2},${node.y - height / 2})" tabindex="0" role="button"><rect width="${width}" height="${height}" rx="10"/><text class="knowledge-node-label" x="${width / 2}" y="${height / 2 - 3}" text-anchor="middle">${escapeHtml(label)}</text><text class="knowledge-node-sub" x="${width / 2}" y="${height / 2 + 17}" text-anchor="middle">${escapeHtml(node.sublabel)}</text></g>`;
  }).join("");
  els.networkGraph.innerHTML = visible.length > 1 ? `<svg viewBox="0 0 900 490" role="img" aria-label="${escapeHtml(companyName)}关系图谱">${edgeHtml}${nodeHtml}</svg>` : `<div class="network-empty">当前分类暂无可展示的关系记录</div>`;
  const selected = visible.find((node) => node.id === state.networkNodeId) || companyNode;
  state.networkNodeId = selected.id;
  els.networkDetail.innerHTML = `${selected.detail}<small>点击图中节点查看关系详情</small>`;
  els.networkGrid.innerHTML = [["投资机构", investorNodes.length], ["人员职务", personNodes.length], ["股东类型", shareholderNodes.length], ["关系记录", investorNodes.reduce((sum, node) => sum + Number(node.sublabel.split(" ")[0] || 0), 0) + [...roleCounts.values()].reduce((sum, count) => sum + count, 0) + [...shareholderGroups.values()].reduce((sum, info) => sum + info.records, 0)]].map(([label, value]) => `<div><span>${label}</span><strong>${value}</strong></div>`).join("");
  els.networkFilters.querySelectorAll("button").forEach((button) => button.classList.toggle("active", button.dataset.networkFilter === state.networkFilter));
  els.networkGraph.querySelectorAll("[data-network-node]").forEach((nodeElement) => nodeElement.addEventListener("click", () => {
    state.networkNodeId = nodeElement.dataset.networkNode;
    renderNetwork(ctx);
  }));
}

function networkRadialPositions(nodes) {
  const positions = new Map([["company", { x: 0, y: 0 }]]);
  const byType = new Map();
  const nodeDataById = new Map();
  nodes.forEach((node) => {
    const data = typeof node.data === "function" ? { id: node.id(), type: node.data("type"), parentInvestor: node.data("parentInvestor"), parentPortfolio: node.data("parentPortfolio") } : node.data;
    nodeDataById.set(data.id, data);
    if (data.id === "company") return;
    if (!byType.has(data.type)) byType.set(data.type, []);
    byType.get(data.type).push(data.id);
  });
  const placeArc = (type, radius, startDegree, endDegree) => {
    const ids = byType.get(type) || [];
    ids.forEach((id, index) => {
      const ratio = ids.length === 1 ? .5 : index / (ids.length - 1);
      const angle = (startDegree + (endDegree - startDegree) * ratio) * Math.PI / 180;
      positions.set(id, { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius });
    });
  };
  const finance = byType.get("finance") || [];
  finance.forEach((id, index) => {
    const angle = (-90 + index * (360 / Math.max(1, finance.length))) * Math.PI / 180;
    positions.set(id, { x: Math.cos(angle) * 190, y: Math.sin(angle) * 190 });
  });
  placeArc("investor", 390, 135, 225);
  placeArc("person", 390, -48, 42);
  placeArc("shareholder", 390, 48, 112);
  placeArc("risk", 390, 118, 132);
  const portfolioByInvestor = new Map();
  (byType.get("portfolio") || []).forEach((id) => {
    const parent = nodeDataById.get(id)?.parentInvestor;
    if (!parent) return;
    const group = portfolioByInvestor.get(parent) || [];
    group.push(id);
    portfolioByInvestor.set(parent, group);
  });
  portfolioByInvestor.forEach((ids, parentId) => {
    const parent = positions.get(parentId);
    if (!parent) return;
    const baseAngle = Math.atan2(parent.y, parent.x);
    ids.forEach((id, index) => {
      const spread = ids.length === 1 ? 0 : (index / (ids.length - 1) - .5) * .72;
      const angle = baseAngle + spread;
      positions.set(id, { x: parent.x + Math.cos(angle) * 205, y: parent.y + Math.sin(angle) * 205 });
    });
  });
  const coInvestorsByPortfolio = new Map();
  (byType.get("coinvestor") || []).forEach((id) => {
    const parent = nodeDataById.get(id)?.parentPortfolio;
    if (!parent) return;
    const group = coInvestorsByPortfolio.get(parent) || [];
    group.push(id);
    coInvestorsByPortfolio.set(parent, group);
  });
  coInvestorsByPortfolio.forEach((ids, parentId) => {
    const parent = positions.get(parentId);
    if (!parent) return;
    const baseAngle = Math.atan2(parent.y, parent.x);
    ids.forEach((id, index) => {
      const spread = ids.length === 1 ? 0 : (index / (ids.length - 1) - .5) * .42;
      const angle = baseAngle + spread;
      positions.set(id, { x: parent.x + Math.cos(angle) * 175, y: parent.y + Math.sin(angle) * 175 });
    });
  });
  return positions;
}

function networkLayoutOptions(nodes, animate = false) {
  const positions = networkRadialPositions(nodes);
  return { name: "preset", positions: (node) => positions.get(node.id()) || { x: 0, y: 0 }, animate, animationDuration: 480, fit: true, padding: 42 };
}

function renderNetwork(ctx) {
  if (!window.cytoscape) {
    renderNetworkLegacy(ctx);
    els.networkDetail.insertAdjacentHTML("beforeend", `<p>专业图谱组件加载失败，当前显示基础视图。</p>`);
    return;
  }
  if (state.networkCompanyId !== ctx.companyId) {
    state.networkCompanyId = ctx.companyId;
    state.networkNodeId = "company";
    if (els.networkSearch) els.networkSearch.value = "";
  }
  if (state.networkCy) state.networkCy.destroy();
  const events = companyTimelineEvents(ctx);
  const financeEvents = companyFinancingNodes(ctx);
  const dossier = (state.data.company_dossiers || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  const diligence = (state.data.due_diligence_profiles || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  const talent = (state.data.talent_profiles || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  const outcome = (state.data.company_outcomes || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  const elements = [];
  const details = new Map();
  const detailRecords = new Map();
  const nodeIds = new Set();
  const nodeTypes = new Map();
  const edgeIds = new Set();
  const addNode = (id, type, label, sublabel, weight, detail, records = [], recordCount = null) => {
    if (nodeIds.has(id)) return;
    nodeIds.add(id);
    nodeTypes.set(id, type);
    elements.push({ data: { id, type, label, sublabel, displayLabel: `${label}\n${sublabel}`, weight: Math.max(1, Number(weight || 1)) } });
    details.set(id, detail);
    detailRecords.set(id, { label, records, count: recordCount == null ? records.length : recordCount });
  };
  const addEdge = (id, source, target, relation, weight = 1) => {
    if (edgeIds.has(id) || !nodeIds.has(source) || !nodeIds.has(target)) return;
    edgeIds.add(id);
    const edgeType = id.startsWith("investor-") ? "investor" : id.startsWith("company-round") ? "finance" : id.startsWith("company-person") ? "person" : id.startsWith("company-shareholder") ? "shareholder" : id.startsWith("company-risk") ? "risk" : nodeTypes.get(target) || "default";
    elements.push({ data: { id, source, target, relation, edgeType, weight: Math.max(1, Number(weight || 1)) } });
  };
  const companyName = companyDisplayName(ctx.dataset, ctx.companyId);
  addNode("company", "company", companyName, outcome.listed ? "已上市" : outcome.acquired ? "已并购退出" : recognizedStage(ctx.stage) || "轮次未披露", 20,
    `<h4>${escapeHtml(companyName)}</h4><span class="network-type company">目标公司</span><dl><div><dt>经营状态</dt><dd>${escapeHtml(dossier.company_status || outcome.company_status || "未披露")}</dd></div><div><dt>当前阶段</dt><dd>${escapeHtml(outcome.listed ? "已上市" : outcome.acquired ? "已并购退出" : recognizedStage(ctx.stage) || "未披露")}</dd></div><div><dt>融资日期</dt><dd>${new Set(financeEvents.map((event) => event.date).filter(Boolean)).size} 个</dd></div><div><dt>风险分</dt><dd>${Number(diligence.risk_score || 0)}/100</dd></div></dl>`, events, events.length);

  const roundGroups = new Map();
  financeEvents.forEach((event) => {
    const date = event.date || "日期未披露";
    const key = `${date}|${normalizeStage(event.stage) || event.stage || "轮次未披露"}`;
    const group = roundGroups.get(key) || { date, stage: normalizeStage(event.stage) || event.stage || "轮次未披露", records: [], amount: 0 };
    group.records.push(event);
    group.amount = Math.max(group.amount, Number(event.amount_usd || 0));
    roundGroups.set(key, group);
  });
  const roundEntries = [...roundGroups.values()].sort((a, b) => String(a.date).localeCompare(String(b.date))).slice(-12);
  const roundIdByDate = new Map();
  roundEntries.forEach((round, index) => {
    const id = `finance-${index}`;
    if (!roundIdByDate.has(round.date)) roundIdByDate.set(round.date, id);
    const amount = round.amount > 0 ? formatMoney(toMillions(round.amount)) : "金额未披露";
    const displayDate = formatDate(round.date) || "日期未披露";
    addNode(id, "finance", round.stage, `${displayDate} · ${amount}`, round.records.length + 2,
      `<h4>${escapeHtml(round.stage)}</h4><span class="network-type finance">融资轮次</span><dl><div><dt>融资日期</dt><dd>${escapeHtml(displayDate)}</dd></div><div><dt>融资金额</dt><dd>${escapeHtml(amount)}</dd></div><div><dt>底层记录</dt><dd>${round.records.length} 条</dd></div></dl>`, round.records, round.records.length);
    addEdge(`company-round-${index}`, "company", id, "完成融资", round.records.length);
  });

  const datasetInvestors = (state.data.investors || []).filter((investor) => investor.dataset === ctx.dataset);
  const investorItems = datasetInvestors.map((investor) => ({
    investor,
    records: (investor.investment_history || []).filter((record) => record.company_id === ctx.companyId),
  })).filter((item) => item.records.length).sort((a, b) => b.records.length - a.records.length).slice(0, 12);
  investorItems.forEach(({ investor, records }, index) => {
    const id = `investor-${index}`;
    const name = investorDisplayName(investor);
    const latest = [...records].sort((a, b) => String(b.date).localeCompare(String(a.date)))[0] || {};
    const disclosed = records.filter((record) => record.investor_amount).length;
    addNode(id, "investor", name, `${records.length} 笔投资`, records.length + 3,
      `<h4>${escapeHtml(name)}</h4><span class="network-type investor">投资机构</span><dl><div><dt>参与投资</dt><dd>${records.length} 笔</dd></div><div><dt>金额披露</dt><dd>${disclosed} 笔</dd></div><div><dt>最近日期</dt><dd>${escapeHtml(latest.date ? formatDate(latest.date) : "未披露")}</dd></div><div><dt>最近轮次</dt><dd>${escapeHtml(latest.round || "未披露")}</dd></div></dl>`, records, records.length);
    const linkedRounds = new Set();
    records.forEach((record) => {
      const roundId = roundIdByDate.get(record.date);
      if (roundId && !linkedRounds.has(roundId)) {
        addEdge(`investor-round-${index}-${roundId}`, roundId, id, "投资方", 2);
        linkedRounds.add(roundId);
      }
    });
    if (!linkedRounds.size) addEdge(`investor-company-${index}`, id, "company", "历史投资", records.length);
    if (state.networkExpandedInvestors.has(id) && !state.networkRoundOnly) {
      const portfolioGroups = new Map();
      (investor.investment_history || []).filter((record) => record.company_id && record.company_id !== ctx.companyId).forEach((record) => {
        const group = portfolioGroups.get(record.company_id) || [];
        group.push(record);
        portfolioGroups.set(record.company_id, group);
      });
      [...portfolioGroups.entries()].sort((a, b) => b[1].length - a[1].length).slice(0, 5).forEach(([companyId, portfolioRecords], portfolioIndex) => {
        const portfolioId = `portfolio-${index}-${portfolioIndex}`;
        const portfolioName = companyDisplayName(ctx.dataset, companyId);
        const latestPortfolio = [...portfolioRecords].sort((a, b) => String(b.date).localeCompare(String(a.date)))[0] || {};
        addNode(portfolioId, "portfolio", portfolioName, `${portfolioRecords.length} 笔 · ${latestPortfolio.round || "轮次未披露"}`, portfolioRecords.length + 1,
          `<h4>${escapeHtml(portfolioName)}</h4><span class="network-type portfolio">关联投资项目</span><dl><div><dt>投资机构</dt><dd>${escapeHtml(name)}</dd></div><div><dt>投资记录</dt><dd>${portfolioRecords.length} 笔</dd></div><div><dt>最近日期</dt><dd>${escapeHtml(latestPortfolio.date ? formatDate(latestPortfolio.date) : "未披露")}</dd></div><div><dt>最近轮次</dt><dd>${escapeHtml(latestPortfolio.round || "未披露")}</dd></div></dl>`, portfolioRecords, portfolioRecords.length);
        const portfolioElement = elements.find((element) => element.data.id === portfolioId);
        if (portfolioElement) portfolioElement.data.parentInvestor = id;
        addEdge(`investor-portfolio-${index}-${portfolioIndex}`, id, portfolioId, "历史投资", portfolioRecords.length);
        const coInvestors = datasetInvestors.map((otherInvestor) => ({
          investor: otherInvestor,
          records: (otherInvestor.investment_history || []).filter((record) => record.company_id === companyId),
        })).filter((item) => item.investor !== investor && item.records.length).sort((a, b) => b.records.length - a.records.length).slice(0, 2);
        coInvestors.forEach(({ investor: coInvestor, records: coRecords }, coIndex) => {
          const coId = `coinvestor-${index}-${portfolioIndex}-${coIndex}`;
          const coName = investorDisplayName(coInvestor);
          const latestCoRecord = [...coRecords].sort((a, b) => String(b.date).localeCompare(String(a.date)))[0] || {};
          addNode(coId, "coinvestor", coName, `${coRecords.length} 笔共同项目记录`, coRecords.length + 1,
            `<h4>${escapeHtml(coName)}</h4><span class="network-type investor">共同投资机构</span><dl><div><dt>关联项目</dt><dd>${escapeHtml(portfolioName)}</dd></div><div><dt>共同记录</dt><dd>${coRecords.length} 笔</dd></div><div><dt>最近日期</dt><dd>${escapeHtml(latestCoRecord.date ? formatDate(latestCoRecord.date) : "未披露")}</dd></div><div><dt>最近轮次</dt><dd>${escapeHtml(latestCoRecord.round || "未披露")}</dd></div></dl>`, coRecords, coRecords.length);
          const coElement = elements.find((element) => element.data.id === coId);
          if (coElement) coElement.data.parentPortfolio = portfolioId;
          addEdge(`coinvestor-link-${index}-${portfolioIndex}-${coIndex}`, portfolioId, coId, "共同投资", coRecords.length);
        });
      });
    }
  });

  const roleGroups = new Map();
  events.filter((event) => ["hire", "executive_report", "legal_appointment", "legal_removal", "departure"].includes(norm(event.event_type))).forEach((event) => {
    const role = String(event.stage || event.role_or_dealtype || "人员任职").split(/[，,、]/)[0].trim() || "人员任职";
    const group = roleGroups.get(role) || { records: 0, appointments: 0, departures: 0, items: [] };
    group.records += 1;
    group.items.push(event);
    if (["legal_removal", "departure"].includes(norm(event.event_type))) group.departures += 1;
    else group.appointments += 1;
    roleGroups.set(role, group);
  });
  [...roleGroups.entries()].sort((a, b) => b[1].records - a[1].records).slice(0, 9).forEach(([role, group], index) => {
    const id = `person-${index}`;
    addNode(id, "person", role, `${group.records} 条人员记录`, group.records,
      `<h4>${escapeHtml(role)}</h4><span class="network-type person">人员职务</span><dl><div><dt>人员记录</dt><dd>${group.records} 条</dd></div><div><dt>任职/备案</dt><dd>${group.appointments} 条</dd></div><div><dt>离任/移除</dt><dd>${group.departures} 条</dd></div><div><dt>人员姓名</dt><dd>源数据未提供</dd></div></dl>`, group.items, group.records);
    addEdge(`company-person-${index}`, "company", id, "任职/治理", group.records);
  });

  const shareholderGroups = new Map();
  events.filter((event) => ["shareholder_appointment", "shareholder_removal"].includes(norm(event.event_type))).forEach((event) => {
    const label = String(event.stage || "股东类型未披露").trim() || "股东类型未披露";
    const group = shareholderGroups.get(label) || { records: 0, entities: new Set(), exits: 0, items: [] };
    group.records += 1;
    group.items.push(event);
    if (event.counterparty_id) group.entities.add(event.counterparty_id);
    if (norm(event.event_type) === "shareholder_removal") group.exits += 1;
    shareholderGroups.set(label, group);
  });
  [...shareholderGroups.entries()].sort((a, b) => b[1].records - a[1].records).slice(0, 7).forEach(([label, group], index) => {
    const id = `shareholder-${index}`;
    addNode(id, "shareholder", label, `${group.entities.size || group.records} 个关系主体`, group.records,
      `<h4>${escapeHtml(label)}</h4><span class="network-type shareholder">股东关系</span><dl><div><dt>关系主体</dt><dd>${group.entities.size || group.records} 个</dd></div><div><dt>底层记录</dt><dd>${group.records} 条</dd></div><div><dt>退出记录</dt><dd>${group.exits} 条</dd></div><div><dt>股东姓名</dt><dd>源数据未提供</dd></div></dl>`, group.items, group.records);
    addEdge(`company-shareholder-${index}`, "company", id, group.exits ? "持股/退出" : "持股关系", group.records);
  });

  const riskLabels = { administrative_penalty: "行政处罚", dishonesty: "失信记录", business_abnormal: "经营异常", revocation: "吊销", cancellation: "注销", lawsuit: "司法风险" };
  const riskGroups = new Map();
  events.forEach((event) => {
    const type = norm(event.event_type);
    const matched = Object.keys(riskLabels).find((key) => type.includes(key));
    if (matched) riskGroups.set(matched, (riskGroups.get(matched) || 0) + 1);
  });
  const dossierRisks = [["administrative_penalty", Number(dossier.punish_count || 0)], ["dishonesty", Number(dossier.dishonesty_count || 0)], ["business_abnormal", Number(dossier.abnormal_count || diligence.abnormal_count || 0)]];
  dossierRisks.forEach(([type, count]) => { if (count > (riskGroups.get(type) || 0)) riskGroups.set(type, count); });
  [...riskGroups.entries()].filter(([, count]) => count > 0).forEach(([type, count], index) => {
    const id = `risk-${index}`;
    const label = riskLabels[type] || eventLabel({ event_type: type });
    addNode(id, "risk", label, `${count} 条记录`, count + 2,
      `<h4>${escapeHtml(label)}</h4><span class="network-type risk">风险事件</span><dl><div><dt>记录数量</dt><dd>${count} 条</dd></div><div><dt>风险分</dt><dd>${Number(diligence.risk_score || 0)}/100</dd></div></dl><p>数量来自事件及尽调汇总字段，仍需核验原始文书。</p>`, events.filter((event) => norm(event.event_type).includes(type)), count);
    addEdge(`company-risk-${index}`, "company", id, "风险关联", count);
  });

  const allowedByFilter = {
    all: new Set(["company", "finance", "investor", "portfolio", "coinvestor", "person", "shareholder", "risk"]),
    finance: new Set(["company", "finance", "investor", "portfolio", "coinvestor"]), investor: new Set(["company", "finance", "investor", "portfolio", "coinvestor"]),
    person: new Set(["company", "person"]), shareholder: new Set(["company", "shareholder"]), risk: new Set(["company", "risk"]),
  };
  const allowed = allowedByFilter[state.networkFilter] || allowedByFilter.all;
  let visibleNodeIds = new Set(elements.filter((element) => !element.data.source && allowed.has(element.data.type)).map((element) => element.data.id));
  if (state.networkRoundOnly && roundEntries.length) {
    const currentRoundId = `finance-${roundEntries.length - 1}`;
    const currentInvestorIds = new Set(elements.filter((element) => element.data.source === currentRoundId && element.data.edgeType === "investor").map((element) => element.data.target));
    visibleNodeIds = new Set(["company", currentRoundId, ...currentInvestorIds]);
  }
  const visibleElements = elements.filter((element) => element.data.source ? visibleNodeIds.has(element.data.source) && visibleNodeIds.has(element.data.target) : visibleNodeIds.has(element.data.id));
  state.networkDetails = details;
  const cy = window.cytoscape({
    container: els.networkGraph,
    elements: visibleElements,
    minZoom: 0.45,
    maxZoom: 2.4,
    wheelSensitivity: 0.18,
    style: [
      { selector: "node", style: { "background-color": "#fff", "border-color": "#aebdc8", "border-width": 2, width: "mapData(weight, 1, 20, 102, 148)", height: "mapData(weight, 1, 20, 60, 82)", label: "data(displayLabel)", "font-size": 12, "font-weight": 750, color: "#152235", "text-wrap": "wrap", "text-max-width": 132, "text-valign": "center", "text-halign": "center", "text-justification": "center", "line-height": 1.4, "overlay-opacity": 0, "shadow-blur": 12, "shadow-color": "#23384b", "shadow-opacity": .12, "shadow-offset-y": 4 } },
      { selector: "node[type='company']", style: { shape: "round-rectangle", width: 210, height: 92, "background-color": "#102534", "border-color": "#102534", color: "#fff", "font-size": 14, "text-max-width": 182, "shadow-opacity": .24 } },
      { selector: "node[type='finance']", style: { shape: "round-diamond", "background-color": "#eaf1ff", "border-color": "#4b76d1", color: "#294f9d" } },
      { selector: "node[type='investor']", style: { shape: "round-rectangle", "background-color": "#e9f7f3", "border-color": "#16816f", color: "#0c6557" } },
      { selector: "node[type='portfolio']", style: { shape: "round-rectangle", "background-color": "#f1edff", "border-color": "#8069c5", color: "#5f4aa0" } },
      { selector: "node[type='coinvestor']", style: { shape: "round-rectangle", "background-color": "#f8f2ff", "border-color": "#9a73c9", color: "#68428f", "border-style": "dashed" } },
      { selector: "node[type='person']", style: { shape: "round-rectangle", "background-color": "#edf7fb", "border-color": "#4d93ad", color: "#35788f" } },
      { selector: "node[type='shareholder']", style: { shape: "round-rectangle", "background-color": "#fff4df", "border-color": "#c98a2d", color: "#8e5b16" } },
      { selector: "node[type='risk']", style: { shape: "round-rectangle", "background-color": "#fff0ed", "border-color": "#c75b4d", color: "#9e3e34" } },
      { selector: "edge", style: { width: "mapData(weight, 1, 15, 1.4, 4)", "line-color": "#aebdc8", "target-arrow-color": "#aebdc8", "target-arrow-shape": "triangle", "curve-style": "bezier", "control-point-step-size": 36, label: "data(relation)", "font-size": 10, "font-weight": 650, color: "#526978", "text-background-color": "#fff", "text-background-opacity": .96, "text-background-padding": 4, "arrow-scale": .8, "overlay-opacity": 0 } },
      { selector: "edge[edgeType='finance']", style: { "line-color": "#7899dc", "target-arrow-color": "#7899dc" } },
      { selector: "edge[edgeType='investor']", style: { "line-color": "#67ad9d", "target-arrow-color": "#67ad9d" } },
      { selector: "edge[edgeType='person']", style: { "line-color": "#79acbe", "target-arrow-color": "#79acbe" } },
      { selector: "edge[edgeType='shareholder']", style: { "line-color": "#d2aa70", "target-arrow-color": "#d2aa70" } },
      { selector: "edge[edgeType='risk']", style: { "line-color": "#dc9188", "target-arrow-color": "#dc9188", "line-style": "dashed" } },
      { selector: "node:selected", style: { "border-width": 4, "border-color": "#0a7b6f", "underlay-color": "#8fd1c2", "underlay-opacity": .22, "underlay-padding": 8 } },
      { selector: ".hover-muted", style: { opacity: .14 } },
      { selector: ".focus-muted", style: { opacity: .1 } },
      { selector: "edge.focus-edge", style: { width: 4, "line-color": "#2d66d9", "target-arrow-color": "#2d66d9", "z-index": 20 } },
      { selector: ".search-muted", style: { opacity: .16 } },
      { selector: ".search-match", style: { "border-width": 4, "border-color": "#2d66d9", "underlay-color": "#91b0ef", "underlay-opacity": .2, "underlay-padding": 7 } },
    ],
    layout: networkLayoutOptions(visibleElements.filter((element) => !element.data.source), false),
  });
  state.networkCy = cy;
  cy.ready(() => {
    const companyNode = cy.getElementById("company");
    if (cy.zoom() < .78) {
      cy.zoom({ level: .78, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
      if (companyNode.length) cy.center(companyNode);
    }
  });
  const showDetail = (id) => {
    state.networkNodeId = id;
    const source = detailRecords.get(id) || detailRecords.get("company");
    const investorAction = id.startsWith("investor-") && !state.networkRoundOnly ? `<button class="network-expand-relations" type="button" data-network-expand-investor="${escapeHtml(id)}">${state.networkExpandedInvestors.has(id) ? "收起关联项目" : "展开关联项目"}</button>` : "";
    els.networkDetail.innerHTML = `<button class="network-detail-expand" type="button" data-network-detail-expand>${els.networkModule.classList.contains("detail-expanded") ? "收起" : "展开"}</button><div class="network-detail-main">${details.get(id) || details.get("company")}</div>${investorAction}${sourceRecordDisclosure(source.label, `${source.count} 条底层记录`, source.records, source.count)}<small>拖动节点调整位置，滚轮缩放；点击空白处恢复全图。</small>`;
    const selectedNode = cy.getElementById(id);
    cy.elements().removeClass("focus-muted focus-edge");
    if (selectedNode.length && id !== "company") {
      const neighborhood = selectedNode.closedNeighborhood();
      cy.elements().difference(neighborhood).addClass("focus-muted");
      selectedNode.connectedEdges().addClass("focus-edge");
      cy.animate({ center: { eles: selectedNode }, duration: 280 });
    } else if (selectedNode.length) {
      cy.animate({ center: { eles: selectedNode }, zoom: Math.max(.78, cy.zoom()), duration: 280 });
    }
  };
  cy.on("tap", "node", (event) => showDetail(event.target.id()));
  cy.on("tap", (event) => { if (event.target === cy) { cy.elements().removeClass("hover-muted focus-muted focus-edge"); showDetail("company"); } });
  cy.on("mouseover", "node", (event) => {
    const neighborhood = event.target.closedNeighborhood();
    cy.elements().difference(neighborhood).addClass("hover-muted");
  });
  cy.on("mouseout", "node", () => cy.elements().removeClass("hover-muted"));
  const selected = cy.getElementById(state.networkNodeId);
  if (selected.length) { selected.select(); showDetail(state.networkNodeId); } else showDetail("company");
  const counts = ["finance", "investor", "person", "shareholder", "risk"].map((type) => elements.filter((element) => !element.data.source && element.data.type === type).length);
  els.networkGrid.innerHTML = [["融资节点", counts[0]], ["投资机构", counts[1]], ["人员职务", counts[2]], ["股东类型", counts[3]], ["风险类型", counts[4]], ["关系总数", elements.filter((element) => element.data.source).length]].map(([label, value]) => `<div><span>${label}</span><strong>${value}</strong></div>`).join("");
  els.networkFilters.querySelectorAll("button").forEach((button) => button.classList.toggle("active", button.dataset.networkFilter === state.networkFilter));
  const roundOnlyButton = els.networkControls.querySelector("[data-network-action='round-only']");
  if (roundOnlyButton) { roundOnlyButton.classList.toggle("active", state.networkRoundOnly); roundOnlyButton.textContent = state.networkRoundOnly ? "显示全部" : "仅看本轮"; }
}

function formatStatementMoney(value, currency = "CNY") {
  if (value == null || value === "") return "—";
  const number = Number(value);
  if (!Number.isFinite(number)) return "—";
  const symbol = currency === "CNY" ? "¥" : currency === "USD" ? "$" : `${currency || ""} `;
  const absolute = Math.abs(number);
  if (absolute >= 1e9) return `${number < 0 ? "-" : ""}${symbol}${(absolute / 1e9).toFixed(2)}B`;
  if (absolute >= 1e6) return `${number < 0 ? "-" : ""}${symbol}${(absolute / 1e6).toFixed(1)}M`;
  if (absolute >= 1e3) return `${number < 0 ? "-" : ""}${symbol}${(absolute / 1e3).toFixed(1)}K`;
  return `${number < 0 ? "-" : ""}${symbol}${absolute.toFixed(0)}`;
}

function assistantAnswer(question) {
  const ctx = selectedContext();
  const normalized = norm(question);
  const name = companyDisplayName(ctx.dataset, ctx.companyId);
  const journey = financingJourney(ctx);
  const valuation = estimateValuation(ctx);
  const dossier = (state.data.company_dossiers || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  const outcome = (state.data.company_outcomes || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  const diligence = (state.data.due_diligence_profiles || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  const talent = (state.data.talent_profiles || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  const financeEvents = companyFinancingNodes(ctx);
  const financeDates = new Set(financeEvents.map((event) => event.date).filter(Boolean));
  const disclosedFunding = financeEvents.reduce((sum, event) => sum + toMillions(event.amount_usd), 0);
  const nextDate = journey.daysToNext ? formatDate(addMonths(new Date(), Math.max(1, Math.round(journey.daysToNext / 30))).toISOString()) : "—";
  if (/融资|下一轮|融多少|什么时候|续融/.test(normalized)) {
    if (journey.terminal) return `${name}已经${outcome.listed ? "上市" : "完成并购退出"}，系统不再预测下一轮融资。历史上共识别 ${financeDates.size} 个融资日期，累计披露融资 ${disclosedFunding > 0 ? formatMoney(disclosedFunding) : "未披露"}。`;
    const source = journey.modelPrediction ? `模型基于截至 ${formatDate(journey.modelPrediction.cutoff_date)} 的历史数据测算` : `当前缺少可验证的A轮及以后记录，结果来自 ${journey.cohortSize || 0} 家同阶段公司的历史参考`;
    return `${name}未来24个月完成下一轮融资的参考概率为 ${percent(journey.nextProbability)}，预计时间为 ${nextDate}，下一轮金额参考为 ${journey.amountStats ? formatMoney(journey.amountStats.median) : "样本不足"}。${source}。`;
  }
  if (/估值|价值|值多少钱|股权价值/.test(normalized)) {
    if (!valuation.count) return `${name}目前没有足够的直接估值或可比融资数据，系统不提供估值数字。需要补充投前/投后估值、融资日期、币种和持股比例。`;
    return `${name}当前估值参考中位数为 ${formatMoney(valuation.median)}，区间为 ${formatMoney(valuation.p25)}–${formatMoney(valuation.p75)}。来源是“${valuation.source}”。这是历史估值或可比样本参考，不是正式投委会估值。`;
  }
  if (/ipo|上市|并购|收购|退出/.test(normalized)) {
    if (outcome.listed) return `${name}在数据中已有上市事实，交易所为 ${dossier.stock_exchange || "未披露"}，证券类型为 ${dossier.stock_type || "未披露"}。这是已发生状态，不是预测。`;
    if (outcome.acquired) return `${name}在数据中已有并购退出事实。当前数据未必包含完整交易金额和投资人实际退出回款。`;
    return `${name}目前未见上市或并购完成事实。页面的IPO参考值为 ${percent(journey.ipoProbability)}、并购参考值为 ${percent(journey.acquisitionProbability)}；由于样本经过结果分层抽取且并购样本很少，这两个数字只能用于相对筛选，不能当作真实市场概率。`;
  }
  if (/财务|收入|利润|资产|负债|现金流|现金/.test(normalized)) {
    const rows = [
      ["报告期", dossier.financial_year || "未披露"], ["营业收入", dossier.revenue != null ? formatStatementMoney(dossier.revenue, dossier.currency) : "未披露"],
      ["净利润", dossier.net_profit != null ? formatStatementMoney(dossier.net_profit, dossier.currency) : "未披露"], ["总资产", dossier.total_assets != null ? formatStatementMoney(dossier.total_assets, dossier.currency) : "未披露"],
      ["负债率", dossier.debt_ratio != null ? percent(Number(dossier.debt_ratio)) : "未披露"], ["经营现金流", dossier.operating_cashflow != null ? formatStatementMoney(dossier.operating_cashflow, dossier.currency) : "未披露"],
    ];
    return `${name}的财务数据：${rows.map(([label, value]) => `${label} ${value}`).join("；")}。未披露不代表数值为零。`;
  }
  if (/风险|处罚|失信|异常|吊销|注销|合规/.test(normalized)) {
    return `${name}当前记录：行政处罚 ${Number(dossier.punish_count || 0)} 条，失信 ${Number(dossier.dishonesty_count || 0)} 条，经营异常 ${Number(dossier.abnormal_count || diligence.abnormal_count || 0)} 条，工商变更 ${Number(diligence.change_count || 0)} 条，尽调风险分 ${Number(diligence.risk_score || 0)}/100。风险分是数据筛查指标，仍需核验原始文书。`;
  }
  if (/团队|员工|高管|创始人|股东|治理|人员/.test(normalized)) {
    return `${name}目前有员工记录 ${Number(talent.employee_records || 0)} 条、当前人员记录 ${Number(talent.current_employee_records || 0)} 条、高管或团队记录 ${Number(talent.team_member_records || 0)} 条、人员离任 ${Number(talent.departure_records || 0)} 条、股东 ${Number(diligence.partner_count || 0)} 个，其中机构股东 ${Number(diligence.institution_partner_count || 0)} 个。记录数量不等于真实在职人数。`;
  }
  if (/公司|概况|基本|介绍|状态/.test(normalized)) {
    return `${name}成立于 ${dossier.establish_date ? formatDate(dossier.establish_date) : "未披露"}，经营状态为 ${dossier.company_status || "未披露"}，当前阶段为 ${outcome.listed ? "已上市" : outcome.acquired ? "已并购退出" : normalizeStage(ctx.stage)}。共识别 ${financeDates.size} 个融资日期，累计披露融资 ${disclosedFunding > 0 ? formatMoney(disclosedFunding) : "未披露"}。`;
  }
  return `我可以基于当前数据回答 ${name} 的融资概率与时间、融资金额、估值依据、上市与并购、财务、风险、团队和股东情况。你可以把问题问得更具体，例如“下一轮预计什么时候融资？”`;
}

function appendAssistantMessage(role, text) {
  const article = document.createElement("article");
  article.className = `assistant-message ${role}`;
  const label = document.createElement("span");
  label.textContent = role === "user" ? "你" : "助手";
  const content = document.createElement("p");
  content.textContent = text;
  article.append(label, content);
  els.assistantMessages.append(article);
  els.assistantMessages.scrollTop = els.assistantMessages.scrollHeight;
}

function renderCompanyAssistant(ctx) {
  if (!els.assistantMessages || state.assistantCompanyId === ctx.companyId) return;
  state.assistantCompanyId = ctx.companyId;
  state.assistantHistory = [];
  els.assistantMessages.innerHTML = "";
  appendAssistantMessage("assistant", `已切换到${companyDisplayName(ctx.dataset, ctx.companyId)}。我会结合该公司的历史数据和模型预测回答。`);
}

function assistantApiContext() {
  const ctx = selectedContext();
  const journey = financingJourney(ctx);
  const valuation = estimateValuation(ctx);
  const dossier = (state.data.company_dossiers || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  const outcome = (state.data.company_outcomes || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  const diligence = (state.data.due_diligence_profiles || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  const talent = (state.data.talent_profiles || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  return {
    company: { name: companyDisplayName(ctx.dataset, ctx.companyId), region: ctx.dataset, stage: recognizedStage(ctx.stage), status: dossier.company_status || outcome.company_status || null, established: dossier.establish_date || null },
    financing_history: companyFinancingNodes(ctx).slice(-20).map((event) => ({ date: event.date || null, round: event.stage || null, amount_usd: event.amount_usd || null })),
    prediction: { ready: journey.predictionReady, next_round_probability: journey.nextProbability, days_to_next_round: journey.daysToNext, amount_median_usd_millions: journey.amountStats?.median || null, amount_p25: journey.amountStats?.p25 || null, amount_p75: journey.amountStats?.p75 || null, ipo_probability: journey.ipoProbability, acquisition_probability: journey.acquisitionProbability, model: journey.modelPrediction?.probability_model || journey.modelPrediction?.model || "historical-cohort" },
    valuation: valuation.count ? { median_usd_millions: valuation.median, p25: valuation.p25, p75: valuation.p75, source: valuation.source, samples: valuation.count } : null,
    financials: { report_period: dossier.financial_year || null, currency: dossier.currency || null, revenue: dossier.revenue ?? null, net_profit: dossier.net_profit ?? null, total_assets: dossier.total_assets ?? null, debt_ratio: dossier.debt_ratio ?? null, operating_cashflow: dossier.operating_cashflow ?? null, cash_balance: dossier.cash_balance ?? null },
    risk: { score: diligence.risk_score || 0, penalties: dossier.punish_count || outcome.punish_count || 0, dishonesty: dossier.dishonesty_count || 0, abnormal: dossier.abnormal_count || diligence.abnormal_count || 0, business_changes: diligence.change_count || 0 },
    team: { employee_records: talent.employee_records || 0, current_employee_records: talent.current_employee_records || 0, leadership_records: talent.team_member_records || 0, departures: talent.departure_records || 0, top_roles: talent.top_roles || [], shareholders: diligence.partner_count || 0, institutional_shareholders: diligence.institution_partner_count || 0 },
    outcome: { listed: Boolean(outcome.listed), acquired: Boolean(outcome.acquired), exchange: dossier.stock_exchange || null, stock_type: dossier.stock_type || null },
  };
}

async function requestAssistantAnswer(question, history) {
  const response = await fetch("/api/assistant", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, history, context: assistantApiContext() }),
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok || !result.ok) throw new Error(result.error || `API 请求失败（HTTP ${response.status}）`);
  return result;
}

async function submitAssistantQuestion(question) {
  const cleanQuestion = String(question || "").trim();
  if (!cleanQuestion) return;
  const priorHistory = [...state.assistantHistory];
  appendAssistantMessage("user", cleanQuestion);
  state.assistantHistory.push({ role: "user", content: cleanQuestion });
  els.assistantStatus.textContent = "AI 正在分析";
  const submitButton = els.assistantForm.querySelector("button[type='submit']");
  submitButton.disabled = true;
  try {
    const result = await requestAssistantAnswer(cleanQuestion, priorHistory);
    const answer = result.answer;
    appendAssistantMessage("assistant", answer);
    state.assistantHistory.push({ role: "assistant", content: answer });
    els.assistantStatus.textContent = `${result.model || "DeepSeek"} 已连接`;
  } catch (error) {
    const fallback = `API 暂不可用：${error.message}。\n\n本地数据回答：${assistantAnswer(cleanQuestion)}`;
    appendAssistantMessage("assistant", fallback);
    state.assistantHistory.push({ role: "assistant", content: fallback });
    els.assistantStatus.textContent = "API 未连接 · 已使用本地回答";
  } finally {
    submitButton.disabled = false;
    els.assistantInput.focus();
  }
}

async function checkAssistantApi() {
  try {
    const response = await fetch("/api/status");
    const result = await response.json();
    els.assistantStatus.textContent = result.ai?.configured ? `${result.ai.model} 已连接` : "等待配置 DeepSeek API Key";
  } catch (_error) {
    els.assistantStatus.textContent = "后端未启动 · 使用本地回答";
  }
}

function sourceRecordRows(records, emptyCount = 0) {
  const usable = (records || []).slice(0, 60);
  if (!usable.length) return `<p class="source-record-empty">数据表仅提供汇总数量（${Number(emptyCount || 0)}），当前样本未附逐条字段。</p>`;
  return `<div class="source-record-list">${usable.map((record, index) => {
    const date = record.date ? String(record.date).slice(0, 10) : "日期未披露";
    const typeCode = norm(record.event_type);
    const type = typeCode ? eventLabel(record) : record.round ? "机构投资" : record.role_or_dealtype || "记录";
    const role = record.stage || record.round || record.role_or_dealtype || "职务/轮次未披露";
    const amount = Number(record.amount_usd || 0) > 0 ? formatMoney(toMillions(record.amount_usd)) : record.investor_amount || "";
    const nature = ["hire", "executive_report", "legal_appointment"].includes(typeCode) ? "任职" : ["departure", "legal_removal"].includes(typeCode) ? "离任/变更" : isUsableFundingEvent(record) ? "融资" : type;
    const region = [record.country, record.metro].filter(Boolean).join(" · ") || "地区未披露";
    const counterparty = record.investor_name || (record.counterparty_id ? (typeCode.includes("shareholder") ? "股东名称已匿名化" : "人员姓名已匿名化") : "关联主体未披露");
    const merged = Math.max(1, Number(record.merged_records || 1));
    return `<article><i>${String(index + 1).padStart(2, "0")}</i><div class="source-record-main"><header><strong>${escapeHtml(type)}</strong><span>${escapeHtml(nature)}</span></header><p>${escapeHtml(role)}</p><dl><div><dt>日期</dt><dd>${escapeHtml(date)}</dd></div><div><dt>地区</dt><dd>${escapeHtml(region)}</dd></div><div><dt>关联主体</dt><dd>${escapeHtml(counterparty)}</dd></div>${amount ? `<div><dt>金额</dt><dd>${escapeHtml(String(amount))}</dd></div>` : ""}<div><dt>底层合并</dt><dd>${merged} 条</dd></div></dl></div></article>`;
  }).join("")}</div>${records.length > usable.length ? `<p class="source-record-empty">当前显示前 ${usable.length} 条，共 ${records.length} 条。</p>` : ""}`;
}

function sourceRecordDisclosure(label, displayValue, records, count = null) {
  const total = count == null ? (records || []).length : Number(count || 0);
  if (!total && !(records || []).length) return escapeHtml(String(displayValue));
  const available = (records || []).length;
  const countText = available && available !== total ? `汇总 ${total} 条 · 可查看 ${available} 条事件` : `${total} 条记录`;
  return `<details class="source-records"><summary>${escapeHtml(String(displayValue))}<span>查看</span></summary><div><header><strong>${escapeHtml(label)}明细</strong><small>${countText}</small></header>${sourceRecordRows(records, total)}</div></details>`;
}

function renderDecisionPriorities(ctx) {
  const dossier = (state.data.company_dossiers || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  const diligence = (state.data.due_diligence_profiles || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  const talent = (state.data.talent_profiles || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  const outcome = (state.data.company_outcomes || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  const financeEvents = companyTimelineEvents(ctx).filter(isUsableFundingEvent);
  const financeDates = new Set(financeEvents.map((event) => event.date).filter(Boolean));
  const financialFields = [dossier.revenue, dossier.net_profit, dossier.total_assets, dossier.operating_cashflow, dossier.cash_balance];
  const missingFinancials = financialFields.filter((value) => value == null || value === "").length;
  const penalties = Number(dossier.punish_count || outcome.punish_count || 0);
  const dishonesty = Number(dossier.dishonesty_count || 0);
  const abnormal = Number(dossier.abnormal_count || diligence.abnormal_count || 0);
  const departures = Number(talent.departure_records || 0);
  const leaders = Number(talent.team_member_records || 0);
  const baseRisk = Number(diligence.risk_score || 0);
  const listed = Boolean(outcome.listed);
  const acquired = Boolean(outcome.acquired);
  let items = [];

  if (state.persona === "investor") {
    const disclosureRisk = missingFinancials >= 4 ? "high" : missingFinancials ? "medium" : "good";
    const complianceRisk = penalties + dishonesty + abnormal > 0 ? (dishonesty || penalties >= 3 ? "high" : "medium") : "good";
    const governanceRisk = departures > Math.max(3, leaders * .35) ? "high" : leaders === 0 ? "medium" : "good";
    items = [
      { level: complianceRisk, title: "合规与经营风险", evidence: penalties + dishonesty + abnormal ? `处罚 ${penalties} 条、失信 ${dishonesty} 条、经营异常 ${abnormal} 条` : "暂未发现处罚、失信或经营异常记录", action: complianceRisk === "good" ? "交易前复核最新工商和司法记录" : "核查事项原因、整改进度及潜在或有负债" },
      { level: disclosureRisk, title: "财务信息风险", evidence: missingFinancials ? `收入、利润、资产、现金流等核心字段缺少 ${missingFinancials} 项` : `核心财务字段已覆盖${dossier.financial_year ? `，报告期 ${dossier.financial_year}` : ""}`, action: missingFinancials ? "索取审计报表、银行流水、收入明细和现金消耗数据" : "重点验证收入质量、现金流和负债真实性" },
      { level: governanceRisk, title: "团队与治理风险", evidence: leaders ? `团队/高管记录 ${leaders} 条，人员离任 ${departures} 条` : `缺少明确高管记录，人员离任 ${departures} 条`, action: governanceRisk === "high" ? "访谈核心管理层并核查关键人员稳定性" : "核查股权结构、关键人依赖及核心团队锁定安排" },
    ];
    const adjustedRisk = Math.min(100, Math.max(baseRisk, baseRisk + missingFinancials * 4 + (penalties + dishonesty + abnormal ? 8 : 0) + (governanceRisk === "high" ? 8 : 0)));
    els.priorityKicker.textContent = "风险核查";
    els.priorityTitle.textContent = "投资风险";
    els.priorityScore.textContent = `风险 ${adjustedRisk}/100`;
    els.priorityScore.dataset.level = adjustedRisk >= 60 ? "high" : adjustedRisk >= 30 ? "medium" : "good";
    els.prioritySummary.textContent = listed ? "重点核查估值、信息披露和流动性。" : acquired ? "公司已有并购退出记录。" : items.some((item) => item.level === "high") ? `重点风险：${items.find((item) => item.level === "high")?.title}` : "未见重大风险，继续核查财务、合规和团队。";
  } else {
    const financeLevel = missingFinancials >= 4 ? "high" : missingFinancials ? "medium" : "good";
    const teamLevel = leaders === 0 || departures > Math.max(3, leaders * .35) ? "medium" : "good";
    const historyLevel = financeDates.size === 0 ? "high" : financeDates.size === 1 ? "medium" : "good";
    items = [
      { level: financeLevel, title: "融资材料", evidence: missingFinancials ? `核心财务字段缺少 ${missingFinancials} 项，投资人难以判断资金效率` : "收入、利润、资产和现金流等核心字段已有记录", action: missingFinancials ? "先补齐近两年财务报表、月度现金流、资金用途和未来18个月预算" : "统一财务口径，准备收入质量、毛利和现金消耗说明" },
      { level: teamLevel, title: "团队与治理", evidence: leaders ? `高管/团队记录 ${leaders} 条，离任记录 ${departures} 条` : "缺少明确的核心管理团队记录", action: teamLevel === "good" ? "明确核心团队分工、持股与融资后人员计划" : "补充核心负责人、履历、持股、激励和关键岗位招聘计划" },
      { level: historyLevel, title: "融资证明与叙事", evidence: financeDates.size ? `已有 ${financeDates.size} 个融资日期、${financeEvents.length} 条融资记录` : "尚无可核验的历史融资日期", action: financeDates.size ? "整理历轮投资人、金额、估值、资金用途和里程碑达成情况" : "建立本轮融资目标、估值依据、资金用途和12—18个月里程碑" },
    ];
    const deductions = missingFinancials * 8 + (teamLevel === "medium" ? 12 : 0) + (historyLevel === "high" ? 18 : historyLevel === "medium" ? 8 : 0) + (baseRisk >= 40 ? 10 : 0);
    const readiness = Math.max(5, Math.min(95, 92 - deductions));
    if (listed) {
      items = [
        { level: missingFinancials ? "high" : "good", title: "财务披露", evidence: missingFinancials ? `核心财务数据缺少 ${missingFinancials} 项` : "核心财务数据已有记录", action: missingFinancials ? "补齐定期报告、现金流和收入利润数据" : "核对最近报告期和审计口径" },
        { level: "medium", title: "再融资方案", evidence: `${dossier.stock_exchange || "交易所"} · ${dossier.stock_type || "证券类型未披露"}`, action: "明确融资工具、规模、定价和资金用途" },
        { level: baseRisk >= 30 ? "medium" : "good", title: "合规核查", evidence: `风险分 ${baseRisk}/100，处罚 ${Number(dossier.punish_count || 0)} 条`, action: "核查信息披露、监管问询和历史处罚" },
      ];
    }
    els.priorityKicker.textContent = listed ? "再融资准备" : acquired ? "退出状态" : "融资准备";
    els.priorityTitle.textContent = listed ? "再融资前需要确认" : acquired ? "公司已完成退出" : "本轮融资待办";
    els.priorityScore.textContent = listed ? "已上市" : acquired ? "已退出" : `准备度 ${readiness}%`;
    els.priorityScore.dataset.level = listed || acquired ? "good" : readiness < 45 ? "high" : readiness < 70 ? "medium" : "good";
    els.prioritySummary.textContent = listed ? "按上市公司再融资流程准备。" : acquired ? "不再进入下一轮融资准备。" : `当前优先：${items.find((item) => item.level === "high")?.title || items.find((item) => item.level === "medium")?.title || "融资材料"}`;
  }
  const levelText = { high: "待补", medium: "关注", good: "已具备" };
  els.priorityGrid.innerHTML = items.map((item) => `<article class="priority-card ${item.level}"><div class="priority-card-head"><strong>${escapeHtml(item.title)}</strong><span>${levelText[item.level]}</span></div><p>${escapeHtml(item.evidence)}</p><div>${escapeHtml(item.action)}</div></article>`).join("");
}

function renderDossier(ctx) {
  const dossier = (state.data.company_dossiers || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  const diligence = (state.data.due_diligence_profiles || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  const talent = (state.data.talent_profiles || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  const outcome = (state.data.company_outcomes || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  const financeEvents = companyTimelineEvents(ctx).filter(isUsableFundingEvent);
  const financeDates = new Set(financeEvents.map((event) => event.date).filter(Boolean));
  const companyName = dossier.company_name || "目标公司";
  const eventType = (event) => norm(event.event_type);
  const eventBuckets = {
    "融资记录": financeEvents,
    "行政处罚": companyTimelineEvents(ctx).filter((event) => eventType(event).includes("administrative_penalty")),
    "失信记录": companyTimelineEvents(ctx).filter((event) => eventType(event).includes("dishonesty")),
    "经营异常": companyTimelineEvents(ctx).filter((event) => eventType(event).includes("business_abnormal")),
    "工商变更": companyTimelineEvents(ctx).filter((event) => eventType(event).includes("business_change")),
    "员工记录": companyTimelineEvents(ctx).filter((event) => ["hire", "employee"].some((type) => eventType(event).includes(type))),
    "当前人员记录": companyTimelineEvents(ctx).filter((event) => ["hire", "executive_report", "legal_appointment"].includes(eventType(event))),
    "高管/团队记录": companyTimelineEvents(ctx).filter((event) => ["executive_report", "legal_appointment", "legal_removal"].includes(eventType(event))),
    "人员离任": companyTimelineEvents(ctx).filter((event) => ["departure", "legal_removal"].includes(eventType(event))),
    "股东数": companyTimelineEvents(ctx).filter((event) => eventType(event).includes("shareholder")),
    "机构股东": companyTimelineEvents(ctx).filter((event) => eventType(event).includes("shareholder")),
  };
  const countByLabel = {
    "融资记录": financeEvents.length, "行政处罚": Number(dossier.punish_count || outcome.punish_count || 0),
    "失信记录": Number(dossier.dishonesty_count || 0), "经营异常": Number(dossier.abnormal_count || diligence.abnormal_count || 0),
    "工商变更": Number(diligence.change_count || 0), "员工记录": Number(talent.employee_records || 0),
    "当前人员记录": Number(talent.current_employee_records || 0), "高管/团队记录": Number(talent.team_member_records || 0),
    "人员离任": Number(talent.departure_records || 0), "股东数": Number(diligence.partner_count || 0),
    "机构股东": Number(diligence.institution_partner_count || 0),
  };
  els.dossierTitle.textContent = `${companyName} · 公司决策档案`;
  els.dossierSubtitle.textContent = `${dossier.company_status || outcome.company_status || "状态未记录"} · ${financeDates.size} 个融资日期 · 风险分 ${Number(diligence.risk_score || 0)}/100`;

  const sections = [
    ["工商基本面", [
      ["公司化名", companyName], ["法定代表人化名", dossier.legal_person || "—"],
      ["成立时间", dossier.establish_date ? formatDate(dossier.establish_date) : "—"], ["登记状态", dossier.company_status || "—"],
      ["企业类型", dossier.company_type || "—"], ["注册/实缴资本", [dossier.registered_capital, dossier.real_capital].filter(Boolean).join(" / ") || "—"],
    ]],
    ["财务摘要", [
      ["报告期", dossier.financial_year || "—"], ["营业收入", formatStatementMoney(dossier.revenue, dossier.currency)],
      ["净利润", formatStatementMoney(dossier.net_profit, dossier.currency)], ["净利率", dossier.net_margin == null ? "—" : percent(dossier.net_margin)],
      ["总资产", formatStatementMoney(dossier.total_assets, dossier.currency)], ["负债率", dossier.debt_ratio == null ? "—" : percent(dossier.debt_ratio)],
      ["经营现金流", formatStatementMoney(dossier.operating_cashflow, dossier.currency)], ["期末现金", formatStatementMoney(dossier.cash_balance, dossier.currency)],
    ]],
    ["融资与上市", [
      ["融资记录", `${financeEvents.length} 条 / ${financeDates.size} 个日期`], ["当前阶段", outcome.listed ? "已上市" : outcome.acquired ? "已并购退出" : recognizedStage(ctx.stage) || "轮次未披露"],
      ["上市状态", outcome.listed ? "已上市" : dossier.stock_status || "未见上市事实"], ["交易所", dossier.stock_exchange || "—"],
      ["证券类型", dossier.stock_type || "—"], ["并购退出", outcome.acquired ? "已发生" : "未见事实"],
    ]],
    ["风险与合规", [
      ["行政处罚", `${Number(dossier.punish_count || outcome.punish_count || 0)} 条`], ["失信记录", `${Number(dossier.dishonesty_count || 0)} 条`],
      ["经营异常", `${Number(dossier.abnormal_count || diligence.abnormal_count || 0)} 条`], ["吊销/注销", dossier.revoke_date ? `吊销 ${formatDate(dossier.revoke_date)}` : dossier.cancel_date ? `注销 ${formatDate(dossier.cancel_date)}` : "无记录"],
      ["工商变更", `${Number(diligence.change_count || 0)} 条`], ["尽调风险分", `${Number(diligence.risk_score || 0)}/100`],
    ]],
    ["团队与治理", [
      ["员工记录", `${Number(talent.employee_records || 0)} 条`], ["当前人员记录", `${Number(talent.current_employee_records || 0)} 条`],
      ["高管/团队记录", `${Number(talent.team_member_records || 0)} 条`], ["人员离任", `${Number(talent.departure_records || 0)} 条`],
      ["股东数", `${Number(diligence.partner_count || 0)} 个`], ["机构股东", `${Number(diligence.institution_partner_count || 0)} 个`],
      ["核心职务", (talent.top_roles || []).join(" · ") || "—"], ["年报员工数", dossier.annual_employee_count == null ? "—" : `${Number(dossier.annual_employee_count)} 人`],
    ]],
  ];
  els.dossierGrid.innerHTML = sections.map(([title, items]) => `<section><h4>${escapeHtml(title)}</h4><dl>${items.map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${Object.prototype.hasOwnProperty.call(eventBuckets, label) ? sourceRecordDisclosure(label, value, eventBuckets[label], countByLabel[label]) : escapeHtml(value)}</dd></div>`).join("")}</dl></section>`).join("");
}

function renderRandomForestTree(ctx, journey) {
  const data = window.ESCP_RANDOM_FOREST_TREE;
  if (!data || !els.modelTree) {
    if (els.modelTreePanel) els.modelTreePanel.hidden = true;
    return;
  }
  els.modelTreePanel.hidden = false;
  const currentPath = data.paths?.[ctx.companyId] || null;
  const highlighted = new Set(currentPath?.nodes || []);
  const nodes = new Map(data.nodes.map((node) => [node.id, node]));
  const positions = new Map();
  let leafIndex = 0;
  let maxDepth = 0;
  const place = (nodeId, depth = 0) => {
    const node = nodes.get(nodeId);
    if (!node) return 0;
    maxDepth = Math.max(maxDepth, depth);
    if (node.leaf || node.left < 0 || node.right < 0) {
      const x = leafIndex * 190 + 115;
      leafIndex += 1;
      positions.set(nodeId, { x, y: depth * 130 + 70, depth });
      return x;
    }
    const leftX = place(node.left, depth + 1);
    const rightX = place(node.right, depth + 1);
    const x = (leftX + rightX) / 2;
    positions.set(nodeId, { x, y: depth * 130 + 70, depth });
    return x;
  };
  place(0);
  const width = Math.max(1040, leafIndex * 190 + 40);
  const height = (maxDepth + 1) * 130 + 38;
  const levels = Array.from({ length: maxDepth + 1 }, (_, depth) => `<g class="tree-level"><rect x="14" y="${depth * 130 + 12}" width="${width - 28}" height="112" rx="10"/><text x="28" y="${depth * 130 + 33}">${depth === maxDepth ? "结果" : `判断 ${depth + 1}`}</text></g>`).join("");
  const edges = data.nodes.filter((node) => !node.leaf).flatMap((node) => [node.left, node.right].map((childId) => {
    const from = positions.get(node.id);
    const to = positions.get(childId);
    if (!from || !to) return "";
    const active = highlighted.has(node.id) && highlighted.has(childId);
    const branch = childId === node.left ? "≤" : ">";
    const labelX = ((from.x + to.x) / 2).toFixed(1);
    const labelY = ((from.y + to.y) / 2 - 4).toFixed(1);
    return `<g class="tree-edge ${active ? "active" : ""}"><path d="M ${from.x} ${from.y + 38} C ${from.x} ${from.y + 78}, ${to.x} ${to.y - 62}, ${to.x} ${to.y - 38}"/><g class="tree-branch-label" transform="translate(${Number(labelX) - 12},${Number(labelY) - 10})"><rect width="24" height="20" rx="10"/><text x="12" y="14" text-anchor="middle">${branch}</text></g></g>`;
  })).join("");
  const nodeViews = data.nodes.map((node) => {
    const pos = positions.get(node.id);
    if (!pos) return "";
    const active = highlighted.has(node.id);
    const label = node.leaf ? `续融概率 ${percent(node.probability)}` : node.feature;
    const currentValue = currentPath?.values?.[String(node.id)];
    const threshold = node.raw_feature.startsWith("cat__") ? "是 / 否" : Number(node.threshold).toLocaleString(undefined, { maximumFractionDigits: 1 });
    const detail = node.leaf ? `${node.samples} 个训练样本` : active && currentValue != null ? `当前值 ${Number(currentValue).toLocaleString()} · 阈值 ${threshold}` : `判断阈值 ${threshold}`;
    const probabilityClass = node.probability >= 0.65 ? "high" : node.probability >= 0.35 ? "medium" : "low";
    const progress = node.leaf ? `<rect class="tree-prob-track" x="14" y="61" width="132" height="5" rx="3"/><rect class="tree-prob-fill" x="14" y="61" width="${(132 * node.probability).toFixed(1)}" height="5" rx="3"/>` : "";
    return `<g class="tree-node ${active ? "active" : "muted"} ${node.leaf ? `leaf ${probabilityClass}` : ""} ${node.id === 0 ? "root" : ""}" data-tree-node="${node.id}" tabindex="0" role="button" transform="translate(${(pos.x - 80).toFixed(1)},${(pos.y - 38).toFixed(1)})"><title>${escapeHtml(node.leaf ? `${label}，${detail}` : `${node.feature}，${detail}`)}</title><rect class="tree-node-card" width="160" height="76" rx="10"/><rect class="tree-node-accent" width="5" height="76" rx="3"/><text class="tree-node-title" x="80" y="25" text-anchor="middle">${escapeHtml(label.length > 18 ? `${label.slice(0, 17)}…` : label)}</text><text class="tree-node-detail" x="80" y="43" text-anchor="middle">${escapeHtml(detail.length > 27 ? `${detail.slice(0, 26)}…` : detail)}</text><text class="tree-node-meta" x="80" y="57" text-anchor="middle">n=${node.samples} · Gini ${Number(node.gini || 0).toFixed(2)}</text>${progress}</g>`;
  }).join("");
  els.modelTree.innerHTML = `<div class="tree-visual-key"><span><i class="current"></i>当前公司路径</span><span><i class="other"></i>其他可能路径</span><span><i class="result"></i>叶节点概率</span><em>左右滑动查看完整决策树</em></div><svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="随机森林代表性决策树">${levels}${edges}${nodeViews}</svg>`;
  if (currentPath) {
    const terminal = positions.get(currentPath.nodes.at(-1));
    window.requestAnimationFrame(() => {
      if (terminal && els.modelTree.clientWidth) els.modelTree.scrollLeft = Math.max(0, terminal.x - els.modelTree.clientWidth / 2);
    });
  }
  const pageModel = journey.modelPrediction?.probability_model || journey.modelPrediction?.model || "同阶段历史基准";
  els.modelTreeSummary.textContent = currentPath ? `${data.node_count} 节点 · 已标出当前路线` : `${data.node_count} 节点 · 结构总览`;
  els.modelTreeIntro.innerHTML = `<div class="tree-metric"><span>森林规模</span><strong>${data.trees} 棵树</strong></div><div class="tree-metric"><span>代表树结构</span><strong>${data.max_depth} 层 · ${data.node_count} 节点 · ${data.leaf_count} 叶</strong></div><div class="tree-metric"><span>训练时点</span><strong>${data.training_snapshots} 个</strong></div><div class="tree-metric"><span>时间外验证</span><strong>AUC ${Number(data.validation?.roc_auc || 0).toFixed(3)}</strong><small>${data.validation?.test_snapshots || 0} 个测试时点</small></div><p>当前模型：${escapeHtml(pageModel)}。代表树用于解释交互关系，最终概率仍由 ${data.trees} 棵树共同投票。</p>`;
  const importances = (data.feature_importances || []).slice(0, 6);
  const maxImportance = Math.max(...importances.map((item) => item.importance), 0.01);
  const importanceHtml = importances.map((item) => `<div class="tree-feature-row"><span>${escapeHtml(item.feature)}</span><i><b style="width:${Math.max(3, item.importance / maxImportance * 100).toFixed(1)}%"></b></i><strong>${percent(item.importance)}</strong></div>`).join("");
  const voteHtml = currentPath ? `<div class="tree-vote-scale"><div class="tree-vote-range" style="left:${currentPath.vote_p10 * 100}%;width:${Math.max(1, (currentPath.vote_p90 - currentPath.vote_p10) * 100)}%"></div><i style="left:${currentPath.vote_median * 100}%"></i><b style="left:${currentPath.forest_probability * 100}%"></b></div><div class="tree-vote-labels"><span>0%</span><em>P10–P90：${percent(currentPath.vote_p10)}–${percent(currentPath.vote_p90)}</em><strong>100%</strong></div>` : `<p class="tree-dashboard-empty">当前公司暂无可映射的森林投票记录</p>`;
  els.modelTreeDashboard.innerHTML = `<section class="tree-dashboard-card"><header><strong>主要判断因素</strong><span>全森林特征贡献</span></header>${importanceHtml}</section><section class="tree-dashboard-card tree-vote-card"><header><strong>400 棵树的投票分布</strong><span>${currentPath ? `支持续融 ${percent(currentPath.positive_vote_share)}` : "暂无公司路径"}</span></header>${voteHtml}<div class="tree-vote-legend"><span><i></i>树间分歧范围</span><span><b></b>森林最终概率</span></div></section>`;
  const showNodeDetail = (nodeId) => {
    const node = nodes.get(Number(nodeId));
    if (!node || !els.modelTreeNodeDetail) return;
    const value = currentPath?.values?.[String(node.id)];
    const threshold = node.threshold == null ? "—" : Number(node.threshold).toLocaleString(undefined, { maximumFractionDigits: 2 });
    els.modelTreeNodeDetail.innerHTML = `<div><span>选中节点</span><strong>${escapeHtml(node.leaf ? "预测叶节点" : node.feature)}</strong></div><dl><div><dt>节点样本</dt><dd>${node.samples}</dd></div><div><dt>续融占比</dt><dd>${percent(node.probability)}</dd></div><div><dt>样本纯度</dt><dd>${percent(1 - Number(node.gini || 0))}</dd></div><div><dt>判断阈值</dt><dd>${escapeHtml(threshold)}</dd></div><div><dt>公司当前值</dt><dd>${value == null ? "不在当前路径" : escapeHtml(Number(value).toLocaleString())}</dd></div></dl><p>${node.leaf ? "该叶节点汇总了满足此前所有条件的历史样本。" : "点击其他节点可查看该分支的样本、阈值与续融比例。"}</p>`;
    els.modelTree.querySelectorAll("[data-tree-node]").forEach((item) => item.classList.toggle("selected", item.dataset.treeNode === String(node.id)));
  };
  els.modelTree.querySelectorAll("[data-tree-node]").forEach((item) => {
    item.addEventListener("click", () => showNodeDetail(item.dataset.treeNode));
    item.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") showNodeDetail(item.dataset.treeNode); });
  });
  showNodeDetail(currentPath?.nodes?.at(-1) ?? 0);
  if (!currentPath) {
    els.modelTreePath.innerHTML = `<span>当前公司没有对应的随机森林路径，展示模型整体结构。</span>`;
    return;
  }
  const decisions = currentPath.nodes.map((nodeId) => nodes.get(nodeId)).filter((node) => node && !node.leaf).map((node) => {
    const value = Number(currentPath.values?.[String(node.id)] || 0);
    if (node.raw_feature.startsWith("cat__")) return `${node.feature}：${value > node.threshold ? "是" : "否"}`;
    return `${node.feature} ${value <= node.threshold ? "≤" : ">"} ${Number(node.threshold).toLocaleString()}`;
  });
  els.modelTreePath.innerHTML = `<div class="tree-path-label">当前公司判断路径</div>${decisions.map((decision, index) => `<span><i>${index + 1}</i>${escapeHtml(decision)}</span>`).join("")}<b><small>最终森林概率</small>${percent(currentPath.forest_probability)}<em>代表树 ${percent(currentPath.tree_probability)}</em></b>`;
}

function renderJourney(ctx) {
  const journey = financingJourney(ctx);
  const nextStage = defaultStages[Math.min(defaultStages.length - 1, journey.currentIndex + 1)];
  const nextDate = addMonths(new Date(), Math.max(1, Math.round(journey.daysToNext / 30)));
  const amount = formatMoney(journey.amountStats?.median || 0);
  const exitProbability = clampValue(journey.ipoProbability + journey.acquisitionProbability, 0, 1);
  const valuation = estimateValuation(ctx);
  const exitValue = Number(fundingCurveData(ctx, journey).at(-1)?.valuation || 0);
  const ownership = Number(els.targetOwnership.value || 0) / 100;
  const ticket = Number(els.ticketSize.value || 0);
  const expectedMoic = ticket > 0 ? (exitValue * ownership * exitProbability) / ticket : 0;
  const dossier = (state.data.company_dossiers || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
  const financeDates = new Set(companyTimelineEvents(ctx).filter(isUsableFundingEvent).map((event) => event.date).filter(Boolean));
  renderDecisionGuide(ctx, journey);
  renderForecastMatrix(ctx, journey);
  els.journeyConfidence.textContent = journey.modelPrediction
    ? `基于截至 ${formatDate(journey.modelPrediction.cutoff_date)} 的历史数据`
    : !journey.predictionReady
    ? `历史数据不足 · 暂不提供正式预测`
    : journey.cohortSize
    ? `参考 ${journey.cohortSize} 家${journey.industryMatched ? "同行业" : "历史"}公司`
    : "当前阶段样本不足";
  const primaryMetrics = journey.terminal
    ? [
        ["当前状态", journey.outcome?.listed ? "已上市" : "已并购退出", "已完成退出，不再预测下一轮融资", "primary"],
        ["交易市场", dossier.stock_exchange || "未披露", dossier.stock_type || "", ""],
        ["历史融资节点", `${financeDates.size} 个`, "按独立融资日期统计", ""],
        ["退出方式", journey.outcome?.listed ? "IPO" : "并购", "历史事实", "exit"],
      ]
    : state.persona === "investor"
    ? [
        ["当前估值", formatMoney(valuation.median), valuation.source || "估值基准", "primary"],
        ["24个月续融概率", percent(journey.nextProbability), `${nextStage} · ${formatMoney(journey.amountStats?.median || 0)}`, ""],
        ["成功退出概率", percent(exitProbability), `IPO ${percent(journey.ipoProbability)} · 并购 ${percent(journey.acquisitionProbability)}`, "exit"],
        ["预期回报倍数", `${expectedMoic.toFixed(2)}x`, `${percent(ownership)} 持股 · $${ticket}M 投资`, ""],
      ]
    : [
        ["下一轮融资成功率", percent(journey.nextProbability), journey.modelPrediction ? `6个月 ${percent(journey.modelPrediction.next_round_probability_6m)} · 12个月 ${percent(journey.modelPrediction.next_round_probability_12m)} · 24个月 ${percent(journey.modelPrediction.next_round_probability_24m)}` : `${nextStage} · 历史完成比例`, "primary"],
        ["预计融资时间", formatDate(nextDate.toISOString()), `约 ${Math.round(journey.daysToNext / 30)} 个月后`, ""],
        ["下一轮金额", amount, journey.amountStats ? `P25–P75 ${formatMoney(journey.amountStats.p25)}–${formatMoney(journey.amountStats.p75)}` : "金额样本不足", ""],
        ["成功退出概率", percent(exitProbability), `IPO ${percent(journey.ipoProbability)} · 并购 ${percent(journey.acquisitionProbability)}`, "exit"],
      ];
  els.curveForecastLegend.hidden = journey.terminal;
  els.curveSubtitle.textContent = journey.terminal ? "展示历史融资与已完成退出" : "历史优先使用估值，缺失时参考融资金额";
  els.journeyKpis.innerHTML = primaryMetrics.map(([label, value, note, cls]) => `
    <div class="journey-kpi ${cls}"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong><small>${escapeHtml(note)}</small></div>
  `).join("");
  renderRandomForestTree(ctx, journey);
  renderFundingCurve(ctx, journey);
  renderHistoricalFinance(ctx);

  const outcomeText = journey.outcome?.listed
    ? "该公司在新数据中已有上市事实，因此 IPO 显示为事实状态。"
    : journey.outcome?.acquired
      ? "该公司在事件数据中已有并购退出事实。"
      : "当前退出记录不完整。IPO和并购概率根据历史总体水平及公司阶段估算，仅供筛选项目时参考。";
  const predictionSource = journey.modelPrediction
    ? "下一轮融资成功率、时间和金额根据历史融资数据测算，并使用时间外样本验证"
    : !journey.predictionReady
      ? "该公司缺少可验证的 A 轮及以后记录，当前结果仅参考同阶段公司的历史表现"
    : `下一轮融资成功率参考了 ${journey.cohortSize} 家处于相同阶段的历史公司`;
  els.journeyNote.textContent = `${outcomeText} ${predictionSource}。近一年记录 ${journey.recentEvents} 条，其中风险记录 ${journey.riskEvents} 条；尽调风险分为 ${journey.riskScore}/100。曲线优先采用已披露估值，缺失部分根据融资金额和对应轮次估算。样本经过分层抽取，不能直接代表全部企业。`;
}

function renderInvestorFinance(ctx) {
  if (state.persona !== "investor") return;
  const journey = financingJourney(ctx);
  const valuation = estimateValuation(ctx);
  const curve = fundingCurveData(ctx, journey);
  const nextRaise = Number(journey.amountStats?.median || 0);
  const expectedFinancing = journey.nextProbability * nextRaise;
  const preMoney = Number(valuation.median || curve[journey.currentIndex]?.valuation || 0);
  const probabilityAdjustedPostMoney = preMoney + expectedFinancing;
  const fullPostMoney = preMoney + nextRaise;
  const impliedDilution = fullPostMoney > 0 ? nextRaise / fullPostMoney : 0;
  const exitProbability = clampValue(journey.ipoProbability + journey.acquisitionProbability, 0, 1);
  const exitValue = Number(curve.at(-1)?.valuation || 0);
  const ticket = Number(els.ticketSize.value || 0);
  const ownership = Number(els.targetOwnership.value || 0) / 100;
  const expectedExitProceeds = exitValue * ownership * exitProbability;
  const expectedMoic = ticket > 0 ? expectedExitProceeds / ticket : 0;
  els.financeMetricGrid.innerHTML = [
    ["风险调整融资期望", formatMoney(expectedFinancing), `${percent(journey.nextProbability)} × ${formatMoney(nextRaise)}`],
    ["概率调整投后价值", formatMoney(probabilityAdjustedPostMoney), `当前估值 + 风险调整融资期望`],
    ["隐含本轮稀释", percent(impliedDilution), `${formatMoney(nextRaise)} ÷ ${formatMoney(fullPostMoney)}`],
    ["风险调整退出回款", formatMoney(expectedExitProceeds), `${percent(exitProbability)} × 退出价值 × ${percent(ownership)}`],
    ["预期毛 MOIC", `${expectedMoic.toFixed(2)}x`, `回款 ÷ ${formatMoney(ticket)} 投资本金`],
  ].map(([label, value, note]) => `<div class="finance-metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong><small>${escapeHtml(note)}</small></div>`).join("");
  els.financeFormula.innerHTML = `
    <strong>口径说明：</strong>融资期望 = 下一轮成功概率 × 预计融资金额；风险调整退出回款 = 成功退出概率 × 退出价值情景 × 目标持股。
    当前为未折现毛回报情景，尚未计入后续轮稀释、清算优先权、反稀释条款、管理费、carry、税费、汇率及退出时间折现，不构成投资建议。
  `;
}

function investorPoolContext(companyId) {
  const companyEvents = state.data.timeline_events.filter((event) => event.dataset === els.region.value && event.company_id === companyId);
  const frequency = (field) => {
    const counts = new Map();
    companyEvents.forEach((event) => { if (event[field]) counts.set(event[field], (counts.get(event[field]) || 0) + 1); });
    return [...counts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0];
  };
  const rounds = companyRecognizedRounds(els.region.value, companyId);
  return {
    persona: "investor",
    dataset: els.region.value,
    industry: frequency("industry") || els.industry.value,
    metro: frequency("metro") || els.metro.value,
    stage: rounds.at(-1)?.normalizedStage || "种子轮",
    companyId,
    employees: Number(els.employees.value),
    runway: Number(els.runway.value),
    roles: [...state.selectedRoles],
  };
}

function poolSparkline(values, positive = true) {
  const safe = values.length > 1 ? values : [values[0] || 0, values[0] || 0];
  const min = Math.min(...safe);
  const max = Math.max(...safe);
  const range = max - min || 1;
  const points = safe.map((value, index) => `${(index * 84 / Math.max(1, safe.length - 1)).toFixed(1)},${(25 - ((value - min) / range) * 21).toFixed(1)}`);
  const line = points.join(" ");
  return `<svg class="pool-sparkline ${positive ? "up" : "down"}" viewBox="0 0 84 29" aria-hidden="true"><polyline class="pool-spark-area" points="0,29 ${line} 84,29"/><polyline class="pool-spark-line" points="${line}"/><circle cx="${points.at(-1).split(',')[0]}" cy="${points.at(-1).split(',')[1]}" r="2.2"/></svg>`;
}

function renderInvestorPool() {
  const query = norm(els.investorPoolSearch.value);
  const allPoolRows = companyCandidates().map((candidate) => {
    const ctx = investorPoolContext(candidate.company_id);
    const journey = financingJourney(ctx);
    const valuation = estimateValuation(ctx);
    const diligence = (state.data.due_diligence_profiles || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
    const dossier = (state.data.company_dossiers || []).find((row) => row.dataset === ctx.dataset && row.company_id === ctx.companyId) || {};
    const outcome = journey.outcome || {};
    const terminal = Boolean(outcome.listed || outcome.acquired);
    const date = terminal || !journey.daysToNext ? null : addMonths(new Date(), Math.max(1, Math.round(journey.daysToNext / 30)));
    const exitProbability = clampValue(journey.ipoProbability + journey.acquisitionProbability, 0, 1);
    const financeHistory = companyFinancingNodes(ctx).sort((a, b) => dateValue(a.date) - dateValue(b.date));
    const disclosedTrend = financeHistory.map((event) => toMillions(event.amount_usd)).filter((value) => value > 0).slice(-8);
    const trend = disclosedTrend.length > 1 ? disclosedTrend : financeHistory.slice(-8).map((_event, index) => index + 1);
    return {
      companyId: ctx.companyId,
      company: companyDisplayName(ctx.dataset, ctx.companyId),
      stage: outcome.listed ? "已上市" : outcome.acquired ? "已并购" : recognizedStage(ctx.stage) || "轮次未披露",
      status: dossier.company_status || "状态未披露",
      probability: terminal ? 0 : journey.nextProbability,
      date,
      dateValue: date ? date.getTime() : 0,
      amount: Number(journey.amountStats?.median || 0),
      valuation: Number(valuation.median || 0),
      exit: terminal ? 1 : exitProbability,
      risk: Number(diligence.risk_score || 0),
      terminal,
      outcome: outcome.listed ? "IPO" : outcome.acquired ? "并购" : "",
      predictionReady: journey.predictionReady,
      trend,
      trendDisclosed: disclosedTrend.length > 1,
    };
  });
  const searchedRows = allPoolRows.filter((row) => !query || norm(`${row.company} ${row.stage} ${row.status}`).includes(query));
  const rows = searchedRows.filter((row) => state.investorPoolSegment === "strong" ? row.probability >= .6 && !row.terminal : state.investorPoolSegment === "predictable" ? row.predictionReady && !row.terminal : state.investorPoolSegment === "exited" ? row.terminal : true);
  const { key, direction } = state.investorPoolSort;
  const sign = direction === "asc" ? 1 : -1;
  rows.sort((a, b) => {
    const left = key === "company" ? a.company : key === "date" ? a.dateValue : Number(a[key] || 0);
    const right = key === "company" ? b.company : key === "date" ? b.dateValue : Number(b[key] || 0);
    return typeof left === "string" ? left.localeCompare(right, "zh-CN") * sign : (left - right) * sign;
  });
  const allRows = searchedRows;
  const predictable = allRows.filter((row) => row.predictionReady && !row.terminal).length;
  const strong = allRows.filter((row) => row.probability >= .6 && !row.terminal).length;
  const exited = allRows.filter((row) => row.terminal).length;
  els.investorPoolStats.innerHTML = [
    ["当前项目", allRows.length, "家公司"], ["具备预测条件", predictable, "A轮及以后"], ["高续融信号", strong, "24个月≥60%"], ["已成功退出", exited, "IPO或并购"],
  ].map(([label, value, note]) => `<div><span>${label}</span><strong>${value}</strong><small>${note}</small></div>`).join("");
  els.investorPoolEmpty.hidden = Boolean(rows.length);
  els.investorPoolBody.innerHTML = rows.map((row, index) => {
    const probabilityClass = row.probability >= .6 ? "up" : row.probability >= .3 ? "watch" : "low";
    const riskClass = row.risk >= 60 ? "high" : row.risk >= 30 ? "medium" : "low";
    const trendUp = row.trend.length < 2 || row.trend.at(-1) >= row.trend[0];
    return `<tr class="${row.terminal ? "terminal" : probabilityClass}" data-pool-company="${escapeHtml(row.companyId)}" tabindex="0">
      <td class="pool-rank">${String(index + 1).padStart(2, "0")}</td>
      <td><div class="pool-company"><i class="${row.terminal ? "terminal" : ""}">${escapeHtml(row.stage)}</i><div><strong>${escapeHtml(row.company)}</strong><small>${escapeHtml(row.status)}</small></div></div></td>
      <td>${row.terminal ? `<span class="pool-outcome">已${escapeHtml(row.outcome)}退出</span>` : `<div class="pool-probability ${probabilityClass}"><strong>${percent(row.probability)}</strong><i><b style="width:${Math.round(row.probability * 100)}%"></b></i><small>${row.predictionReady ? "模型预测" : "阶段参考"}</small></div>`}</td>
      <td><div class="pool-trend">${poolSparkline(row.trend, trendUp)}<small>${row.trendDisclosed ? "披露金额" : "融资活跃度"}</small></div></td>
      <td><strong class="pool-value">${row.date ? formatDate(row.date.toISOString()) : "—"}</strong><small class="pool-cell-note">${row.terminal ? "已完成退出" : row.date ? "预计融资窗口" : "暂无预测"}</small></td>
      <td><strong class="pool-value">${row.amount ? formatMoney(row.amount) : "—"}</strong><small class="pool-cell-note">中位数</small></td>
      <td><strong class="pool-value">${row.valuation ? formatMoney(row.valuation) : "—"}</strong><small class="pool-cell-note">估值参考</small></td>
      <td><strong class="pool-value ${row.exit >= .25 ? "positive" : ""}">${percent(row.exit)}</strong><small class="pool-cell-note">IPO＋并购</small></td>
      <td><span class="pool-risk ${riskClass}">${row.risk}</span><small class="pool-cell-note">风险分</small></td>
      <td><button class="pool-open" type="button" data-pool-company="${escapeHtml(row.companyId)}">查看分析</button></td>
    </tr>`;
  }).join("");
  els.investorPool.querySelectorAll("[data-pool-sort]").forEach((button) => {
    const active = button.dataset.poolSort === key;
    button.classList.toggle("active", active);
    button.dataset.direction = active ? direction : "";
  });
  els.investorPoolSegments.querySelectorAll("[data-pool-segment]").forEach((button) => button.classList.toggle("active", button.dataset.poolSegment === state.investorPoolSegment));
}

function openInvestorCompany(companyId) {
  if (!companyId || ![...els.company.options].some((option) => option.value === companyId)) return;
  els.company.value = companyId;
  syncStageFromCompany();
  state.investorPoolOpen = false;
  switchWorkspaceView("decision");
  deferRender(simulate, "正在打开公司分析");
}

function simulate() {
  if (!state.data) return;
  const ctx = selectedContext();
  renderPersona();
  if (state.persona === "investor" && state.investorPoolOpen) {
    renderInvestorPool();
    return;
  }
  renderJourney(ctx);
  renderValuation(ctx);
  renderInvestorFinance(ctx);
  renderInvestors(ctx);
  renderNetwork(ctx);
  renderDecisionPriorities(ctx);
  renderDossier(ctx);
  renderCompanyAssistant(ctx);
}

function showPageLoading(title = "正在切换数据") {
  if (!els.pageLoading) return;
  const titleEl = els.pageLoading.querySelector("strong");
  if (titleEl) titleEl.textContent = title;
  els.pageLoading.hidden = false;
}

function hidePageLoading() {
  if (!els.pageLoading) return;
  els.pageLoading.hidden = true;
}

function deferRender(work, title) {
  renderTicket += 1;
  const ticket = renderTicket;
  showPageLoading(title);
  requestAnimationFrame(() => {
    window.setTimeout(() => {
      try {
        work();
      } finally {
        if (ticket === renderTicket) hidePageLoading();
      }
    }, 30);
  });
}

function bindEvents() {
  els.modelTreePanel.addEventListener("toggle", () => {
    if (!els.modelTreePanel.open || !state.data) return;
    const ctx = selectedContext();
    renderRandomForestTree(ctx, financingJourney(ctx));
  });
  els.networkFilters.addEventListener("click", (event) => {
    const button = event.target.closest("[data-network-filter]");
    if (!button) return;
    state.networkFilter = button.dataset.networkFilter;
    state.networkNodeId = "company";
    renderNetwork(selectedContext());
  });
  els.networkControls.addEventListener("click", (event) => {
    const button = event.target.closest("[data-network-action]");
    const cy = state.networkCy;
    if (!button || !cy) return;
    const action = button.dataset.networkAction;
    if (action === "round-only") {
      state.networkRoundOnly = !state.networkRoundOnly;
      state.networkNodeId = "company";
      renderNetwork(selectedContext());
      return;
    }
    if (action === "zoom-in") cy.zoom({ level: Math.min(cy.maxZoom(), cy.zoom() * 1.2), renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
    if (action === "zoom-out") cy.zoom({ level: Math.max(cy.minZoom(), cy.zoom() / 1.2), renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
    if (action === "fit") cy.fit(cy.elements(), 36);
    if (action === "layout") cy.layout(networkLayoutOptions(cy.nodes(), true)).run();
    if (action === "fullscreen") {
      els.networkModule.classList.toggle("graph-expanded");
      button.textContent = els.networkModule.classList.contains("graph-expanded") ? "退出全屏" : "全屏";
      window.setTimeout(() => { cy.resize(); cy.fit(cy.elements(), 48); }, 80);
    }
  });
  els.networkDetail.addEventListener("click", (event) => {
    const investorButton = event.target.closest("[data-network-expand-investor]");
    if (investorButton) {
      const investorId = investorButton.dataset.networkExpandInvestor;
      if (state.networkExpandedInvestors.has(investorId)) state.networkExpandedInvestors.delete(investorId);
      else state.networkExpandedInvestors.add(investorId);
      state.networkNodeId = investorId;
      renderNetwork(selectedContext());
      return;
    }
    const button = event.target.closest("[data-network-detail-expand]");
    if (!button) return;
    els.networkModule.classList.toggle("detail-expanded");
    button.textContent = els.networkModule.classList.contains("detail-expanded") ? "收起" : "展开";
    window.setTimeout(() => { state.networkCy?.resize(); state.networkCy?.fit(state.networkCy.elements(":visible"), 50); }, 180);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || !els.networkModule.classList.contains("graph-expanded")) return;
    els.networkModule.classList.remove("graph-expanded");
    const button = els.networkControls.querySelector("[data-network-action='fullscreen']");
    if (button) button.textContent = "全屏";
    window.setTimeout(() => { state.networkCy?.resize(); state.networkCy?.fit(state.networkCy.elements(), 42); }, 80);
  });
  els.networkSearch.addEventListener("input", () => {
    const cy = state.networkCy;
    if (!cy) return;
    const query = norm(els.networkSearch.value);
    cy.elements().removeClass("search-match search-muted");
    if (!query) return;
    const matches = cy.nodes().filter((node) => norm(`${node.data("label")} ${node.data("sublabel")}`).includes(query));
    if (!matches.length) { cy.nodes().addClass("search-muted"); return; }
    cy.elements().addClass("search-muted");
    matches.union(matches.connectedEdges()).union(matches.neighborhood("node")).removeClass("search-muted").addClass("search-match");
    cy.animate({ fit: { eles: matches, padding: 90 }, duration: 300 });
  });
  els.assistantForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const question = els.assistantInput.value.trim();
    if (!question) return;
    els.assistantInput.value = "";
    submitAssistantQuestion(question);
  });
  els.assistantPrompts.addEventListener("click", (event) => {
    const button = event.target.closest("[data-assistant-question]");
    if (!button) return;
    const question = button.dataset.assistantQuestion;
    submitAssistantQuestion(question);
  });
  els.forecastTableBody.addEventListener("click", (event) => {
    const button = event.target.closest("[data-history-detail]");
    if (!button) return;
    const detail = document.getElementById(button.dataset.historyDetail);
    if (!detail) return;
    detail.hidden = !detail.hidden;
    button.setAttribute("aria-expanded", String(!detail.hidden));
    const indicator = button.querySelector("i");
    if (indicator) indicator.textContent = detail.hidden ? "查看" : "收起";
  });
  els.workspaceTabs.addEventListener("click", (event) => {
    const button = event.target.closest("[data-view]");
    if (!button || button.hidden) return;
    switchWorkspaceView(button.dataset.view);
  });
  els.personaSwitch.addEventListener("click", (event) => {
    const button = event.target.closest("[data-persona]");
    if (!button) return;
    state.persona = button.dataset.persona;
    state.investorPoolOpen = state.persona === "investor";
    deferRender(simulate, "正在切换使用角色");
  });
  els.investorPoolBody.addEventListener("click", (event) => {
    const target = event.target.closest("[data-pool-company]");
    if (target) openInvestorCompany(target.dataset.poolCompany);
  });
  els.investorPoolBody.addEventListener("keydown", (event) => {
    if (!['Enter', ' '].includes(event.key)) return;
    const row = event.target.closest("tr[data-pool-company]");
    if (row) { event.preventDefault(); openInvestorCompany(row.dataset.poolCompany); }
  });
  els.investorPoolSearch.addEventListener("input", renderInvestorPool);
  els.investorPool.addEventListener("click", (event) => {
    const segment = event.target.closest("[data-pool-segment]");
    if (segment) {
      state.investorPoolSegment = segment.dataset.poolSegment;
      renderInvestorPool();
      return;
    }
    const button = event.target.closest("[data-pool-sort]");
    if (!button) return;
    const key = button.dataset.poolSort;
    state.investorPoolSort = { key, direction: state.investorPoolSort.key === key && state.investorPoolSort.direction === "desc" ? "asc" : "desc" };
    renderInvestorPool();
  });
  els.backToInvestorPool.addEventListener("click", () => {
    state.investorPoolOpen = true;
    deferRender(simulate, "正在返回投资项目池");
  });
  els.region.addEventListener("change", () => {
    deferRender(() => {
      refreshFilters();
      simulate();
    }, "正在切换地区数据");
  });
  [els.industry, els.metro].forEach((select) => select.addEventListener("change", () => {
    deferRender(() => {
      refreshCompanySelect();
      simulate();
    }, "正在更新筛选结果");
  }));
  els.stage.addEventListener("change", () => {
    state.stageSource = "manual";
    els.stageDetection.textContent = "手动回拨切割点：该轮之前按事实展示，之后重新预测";
    deferRender(simulate, "正在回拨预测切割点");
  });
  els.company.addEventListener("change", () => {
    deferRender(() => {
      syncStageFromCompany();
      simulate();
    }, "正在识别公司当前轮次");
  });
  els.valuationTimelineBtn.addEventListener("click", openValuationTimeline);
  els.timelineCloseBtn.addEventListener("click", closeValuationTimeline);
  els.valuationTimelineModal.addEventListener("click", (event) => {
    if (event.target === els.valuationTimelineModal) closeValuationTimeline();
  });
  els.profileCloseBtn.addEventListener("click", closeProfileModal);
  els.profileModal.addEventListener("click", (event) => {
    if (event.target === els.profileModal) closeProfileModal();
  });
  [els.investorMatches].forEach((list) => {
    list.addEventListener("click", (event) => {
      const button = event.target.closest("[data-profile-type]");
      if (!button) return;
      openMatchProfile(button.dataset.profileType, button.dataset.profileId);
    });
  });
  els.employees.addEventListener("input", () => {
    els.employeesOut.value = els.employees.value;
    simulate();
  });
  els.runway.addEventListener("input", () => {
    els.runwayOut.value = els.runway.value;
    simulate();
  });
  els.ticketSize.addEventListener("input", () => {
    els.ticketSizeOut.value = els.ticketSize.value;
    simulate();
  });
  els.targetOwnership.addEventListener("input", () => {
    els.targetOwnershipOut.value = `${els.targetOwnership.value}%`;
    simulate();
  });
  els.simulateBtn.addEventListener("click", () => {
    deferRender(simulate, "正在生成推荐结果");
  });
}

async function init() {
  renderRoleControls();
  bindEvents();
  checkAssistantApi();
  try {
    if (window.ESCP_DEMO_DATA) {
      state.data = window.ESCP_DEMO_DATA;
    } else {
      const response = await fetch("../processed/demo_data.json");
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      state.data = await response.json();
    }
    els.dataStatus.textContent = "数据已更新";
    refreshFilters();
    simulate();
  } catch (error) {
    els.dataStatus.textContent = "数据加载失败";
    console.warn(error);
  }
}

init();

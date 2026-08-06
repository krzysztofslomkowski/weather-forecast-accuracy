"use strict";

const DATA_FILES = {
  forecasts: "data/forecasts.csv",
  actuals: "data/actuals.csv",
  detailed: "data/evaluation_detailed.csv",
  mae: "data/evaluation_mae.csv",
};

const COLORS = ["#2563eb", "#0891b2", "#7457d9", "#0f9f6e", "#dc4c64", "#d97706"];

const el = {
  status: document.querySelector("#data-status"),
  state: document.querySelector("#benchmark-state"),
  bestProvider: document.querySelector("#kpi-best-provider"),
  bestMae: document.querySelector("#kpi-best-mae"),
  leaderContext: document.querySelector("#leader-context"),
  comparisons: document.querySelector("#kpi-comparisons"),
  providers: document.querySelector("#kpi-providers"),
  dateRange: document.querySelector("#kpi-date-range"),
  lastUpdated: document.querySelector("#kpi-last-updated"),
  maeChart: document.querySelector("#mae-chart"),
  winsChart: document.querySelector("#wins-chart"),
  errorChart: document.querySelector("#error-chart"),
  rankingBody: document.querySelector("#ranking-body"),
  rankingEmpty: document.querySelector("#ranking-empty"),
  coverageBody: document.querySelector("#coverage-body"),
  readinessTitle: document.querySelector("#readiness-title"),
  readinessStatus: document.querySelector("#readiness-status"),
  readinessRatio: document.querySelector("#readiness-ratio"),
  readinessBar: document.querySelector("#readiness-bar"),
  forecastRows: document.querySelector("#stat-forecast-rows"),
  actualDays: document.querySelector("#stat-actual-days"),
  pendingRows: document.querySelector("#stat-pending-rows"),
  nextTarget: document.querySelector("#stat-next-target"),
  readinessMessage: document.querySelector("#readiness-message"),
};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  try {
    const [forecastRaw, actualRaw, detailedRaw, maeRaw] = await Promise.all([
      loadCsv(DATA_FILES.forecasts),
      loadCsv(DATA_FILES.actuals),
      loadCsv(DATA_FILES.detailed),
      loadCsv(DATA_FILES.mae),
    ]);

    const forecasts = normalizeForecasts(forecastRaw);
    const actuals = normalizeActuals(actualRaw);
    const detailed = normalizeDetailed(detailedRaw);
    const ranking = buildRanking(maeRaw, detailed);
    const providers = collectProviders(forecasts, detailed, maeRaw);
    const wins = buildDailyWins(detailed);
    const coverage = buildCoverage(providers, forecasts, detailed);
    const readiness = buildReadiness(forecasts, actuals, detailed, ranking, providers);

    renderSummary({ forecasts, actuals, detailed, ranking, providers });
    renderReadiness(readiness);
    renderRanking(ranking);
    renderCoverage(coverage);
    renderBars(el.maeChart, ranking, "maeC", (value) => `${number(value, 2)} °C`, "No MAE results yet");
    renderBars(el.winsChart, wins, "wins", (value) => number(value, 0), "No daily wins yet", true);
    renderTrend(el.errorChart, detailed);

    if (detailed.length === 0) {
      showNotice("Evaluation is not complete yet. The dashboard is showing live collection status from the forecast and actual CSV files.");
    }
  } catch (error) {
    console.error(error);
    renderFailure(error);
  }
}

async function loadCsv(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw new Error(`Could not load ${path} (HTTP ${response.status})`);
  return parseCsv(await response.text());
}

function parseCsv(text) {
  const source = text.replace(/^\uFEFF/, "");
  if (!source.trim()) return [];
  const records = [];
  let row = [];
  let field = "";
  let quoted = false;

  for (let i = 0; i < source.length; i += 1) {
    const char = source[i];
    const next = source[i + 1];
    if (char === '"') {
      if (quoted && next === '"') { field += '"'; i += 1; }
      else quoted = !quoted;
    } else if (char === "," && !quoted) {
      row.push(field); field = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && next === "\n") i += 1;
      row.push(field);
      if (row.some((value) => value.trim() !== "")) records.push(row);
      row = []; field = "";
    } else field += char;
  }
  row.push(field);
  if (row.some((value) => value.trim() !== "")) records.push(row);
  if (records.length < 2) return [];

  const headers = records[0].map((value) => value.trim());
  return records.slice(1).map((values) => Object.fromEntries(
    headers.map((header, index) => [header, (values[index] ?? "").trim()]),
  ));
}

function normalizeForecasts(rows) {
  return rows.map((row) => ({
    provider: cleanProvider(row.provider),
    runDate: isoDate(row.run_date),
    targetDate: isoDate(row.target_date),
    horizonDays: numeric(row.horizon_days),
    tmaxC: numeric(row.tmax_c),
  })).filter((row) => row.provider && row.targetDate && row.tmaxC !== null);
}

function normalizeActuals(rows) {
  return rows.map((row) => ({ date: isoDate(row.date), tmaxC: numeric(row.tmax_c) }))
    .filter((row) => row.date && row.tmaxC !== null);
}

function normalizeDetailed(rows) {
  return rows.map((row) => {
    const forecast = numeric(row.forecast_tmax_c);
    const actual = numeric(row.actual_tmax_c);
    return {
      provider: cleanProvider(row.provider),
      runDate: isoDate(row.run_date),
      targetDate: isoDate(row.target_date),
      forecastTmaxC: forecast,
      actualTmaxC: actual,
      absErrorC: numeric(row.abs_error_c) ?? (forecast !== null && actual !== null ? Math.abs(forecast - actual) : null),
    };
  }).filter((row) => row.provider && row.targetDate && row.forecastTmaxC !== null && row.actualTmaxC !== null && row.absErrorC !== null);
}

function buildRanking(maeRows, detailed) {
  const detailedGroups = groupBy(detailed, (row) => row.provider);
  const summaries = new Map();

  for (const row of maeRows) {
    const provider = cleanProvider(row.provider);
    const maeC = numeric(row.mae_c);
    if (!provider || maeC === null) continue;
    summaries.set(provider, {
      provider,
      maeC,
      observations: numeric(row.observations_count),
    });
  }

  if (summaries.size === 0) {
    for (const [provider, rows] of detailedGroups.entries()) {
      summaries.set(provider, { provider, maeC: mean(rows.map((row) => row.absErrorC)), observations: rows.length });
    }
  }

  return [...summaries.values()].map((summary) => {
    const rows = detailedGroups.get(summary.provider) ?? [];
    return {
      provider: summary.provider,
      observations: summary.observations ?? rows.length,
      maeC: summary.maeC,
      biasC: rows.length ? mean(rows.map((row) => row.forecastTmaxC - row.actualTmaxC)) : null,
    };
  }).sort((a, b) => a.maeC - b.maeC || a.provider.localeCompare(b.provider))
    .map((row, index) => ({ ...row, rank: index + 1 }));
}

function buildDailyWins(detailed) {
  const byDate = groupBy(detailed, (row) => row.targetDate);
  const wins = new Map();
  for (const rows of byDate.values()) {
    const minimum = Math.min(...rows.map((row) => row.absErrorC));
    for (const row of rows) {
      if (Math.abs(row.absErrorC - minimum) < 1e-9) wins.set(row.provider, (wins.get(row.provider) ?? 0) + 1);
    }
  }
  return [...wins.entries()].map(([provider, count]) => ({ provider, wins: count }))
    .sort((a, b) => b.wins - a.wins || a.provider.localeCompare(b.provider));
}

function collectProviders(forecasts, detailed, maeRows) {
  const providers = new Set();
  forecasts.forEach((row) => providers.add(row.provider));
  detailed.forEach((row) => providers.add(row.provider));
  maeRows.forEach((row) => { const provider = cleanProvider(row.provider); if (provider) providers.add(provider); });
  return [...providers].sort();
}

function buildCoverage(providers, forecasts, detailed) {
  return providers.map((provider) => {
    const providerForecasts = forecasts.filter((row) => row.provider === provider);
    const providerDetailed = detailed.filter((row) => row.provider === provider);
    const latestRun = maxDate(providerForecasts.map((row) => row.runDate));
    const latestTarget = maxDate(providerForecasts.map((row) => row.targetDate));
    return {
      provider,
      forecastRows: providerForecasts.length,
      latestRun,
      latestTarget,
      completed: providerDetailed.length,
      status: providerDetailed.length ? "Evaluated" : providerForecasts.length ? "Collecting" : "No data",
    };
  });
}

function buildReadiness(forecasts, actuals, detailed, ranking, providers) {
  const actualDates = new Set(actuals.map((row) => row.date));
  const pending = forecasts.filter((row) => !actualDates.has(row.targetDate));
  const evaluatedProviders = new Set(detailed.map((row) => row.provider));
  const nextTarget = minDate(pending.map((row) => row.targetDate));
  return {
    forecastRows: forecasts.length,
    actualDays: new Set(actuals.map((row) => row.date)).size,
    pendingRows: pending.length,
    nextTarget,
    evaluatedProviders: evaluatedProviders.size,
    providerCount: providers.length,
    ready: ranking.length > 0,
  };
}

function renderSummary({ forecasts, actuals, detailed, ranking, providers }) {
  const best = ranking[0] ?? null;
  el.bestProvider.textContent = best ? displayProvider(best.provider) : "Pending";
  el.bestMae.textContent = best ? `${number(best.maeC, 2)} °C` : "—";
  el.comparisons.textContent = number(detailed.length, 0);
  el.providers.textContent = number(providers.length, 0);

  const evaluatedDates = detailed.map((row) => row.targetDate).filter(Boolean).sort();
  el.dateRange.textContent = evaluatedDates.length
    ? `${shortDate(evaluatedDates[0])} — ${shortDate(evaluatedDates.at(-1))}`
    : "Not started";

  const latest = maxDate([
    ...forecasts.map((row) => row.runDate),
    ...forecasts.map((row) => row.targetDate),
    ...actuals.map((row) => row.date),
    ...detailed.map((row) => row.runDate),
  ]);
  el.lastUpdated.textContent = latest ? longDate(latest) : "No data";

  if (best) {
    el.state.textContent = "Benchmark active";
    el.state.className = "state-badge ready";
    el.leaderContext.textContent = `${number(best.observations, 0)} completed observations; ranking is specific to Torrevieja at D+3.`;
  } else {
    el.state.textContent = "Collecting observations";
    el.state.className = "state-badge collecting";
    el.leaderContext.textContent = forecasts.length
      ? `${forecasts.length} forecast rows collected; a leader will be shown after matching actual observations arrive.`
      : "No forecast rows have been collected yet.";
  }
}

function renderReadiness(data) {
  const denominator = Math.max(data.providerCount, 1);
  const percent = Math.round((data.evaluatedProviders / denominator) * 100);
  el.readinessRatio.textContent = `${data.evaluatedProviders} / ${data.providerCount}`;
  el.readinessBar.style.width = `${percent}%`;
  el.forecastRows.textContent = number(data.forecastRows, 0);
  el.actualDays.textContent = number(data.actualDays, 0);
  el.pendingRows.textContent = number(data.pendingRows, 0);
  el.nextTarget.textContent = data.nextTarget ? longDate(data.nextTarget) : "—";

  if (data.ready) {
    el.readinessTitle.textContent = "Evaluation coverage";
    el.readinessStatus.textContent = "Active";
    el.readinessStatus.className = "status-chip ready";
    el.readinessMessage.textContent = "The ranking is live and will be recalculated as new matched observations are committed.";
    el.readinessMessage.className = "readiness-message ready";
  } else {
    el.readinessTitle.textContent = "Collection status";
    el.readinessStatus.textContent = "Building sample";
    el.readinessStatus.className = "status-chip";
    el.readinessMessage.textContent = data.nextTarget
      ? `The earliest unmatched forecast targets ${longDate(data.nextTarget)}. Results appear after the corresponding Meteostat actual is available.`
      : "Waiting for forecast rows and matching Meteostat observations.";
    el.readinessMessage.className = "readiness-message";
  }
}

function renderRanking(ranking) {
  el.rankingBody.replaceChildren();
  el.rankingEmpty.hidden = ranking.length > 0;
  for (const row of ranking) {
    const tr = document.createElement("tr");
    tr.append(
      cellBadge(row.rank),
      textCell(displayProvider(row.provider), "provider-name"),
      textCell(number(row.observations, 0), "num"),
      textCell(`${number(row.maeC, 2)} °C`, `num${row.rank === 1 ? " best-value" : ""}`),
      textCell(row.biasC === null ? "—" : `${signed(row.biasC)} °C`, "num"),
    );
    el.rankingBody.append(tr);
  }
}

function renderCoverage(rows) {
  el.coverageBody.replaceChildren();
  for (const row of rows) {
    const tr = document.createElement("tr");
    const status = document.createElement("span");
    status.className = `provider-status${row.status === "Evaluated" ? " ready" : row.status === "No data" ? " no-data" : ""}`;
    status.textContent = row.status;
    const statusCell = document.createElement("td");
    statusCell.append(status);
    tr.append(
      textCell(displayProvider(row.provider), "provider-name"),
      textCell(number(row.forecastRows, 0), "num"),
      textCell(row.latestRun ? shortDate(row.latestRun) : "—"),
      textCell(row.latestTarget ? shortDate(row.latestTarget) : "—"),
      textCell(number(row.completed, 0), "num"),
      statusCell,
    );
    el.coverageBody.append(tr);
  }
  if (!rows.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 6;
    td.textContent = "No provider rows are available yet.";
    td.style.textAlign = "center";
    td.style.color = "#8d98aa";
    tr.append(td);
    el.coverageBody.append(tr);
  }
}

function renderBars(svg, rows, valueKey, formatValue, emptyLabel, integerTicks = false) {
  clearSvg(svg);
  if (!rows.length) return emptyChart(svg, emptyLabel);
  const width = svg.viewBox.baseVal.width || 900;
  const height = svg.viewBox.baseVal.height || 410;
  const margin = { top: 24, right: 100, bottom: 42, left: width > 700 ? 155 : 125 };
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;
  const max = Math.max(...rows.map((row) => row[valueKey]), 0);
  const domain = max > 0 ? max * 1.15 : 1;
  const slot = plotH / rows.length;
  const barH = Math.min(38, slot * .56);

  for (let i = 0; i <= 5; i += 1) {
    const value = (domain / 5) * i;
    const x = margin.left + (value / domain) * plotW;
    svg.append(svgNode("line", { x1: x, x2: x, y1: margin.top, y2: height - margin.bottom, class: "grid-line" }));
    const label = svgNode("text", { x, y: height - 15, "text-anchor": "middle" });
    label.textContent = integerTicks ? number(value, 0) : number(value, 1);
    svg.append(label);
  }

  rows.forEach((row, index) => {
    const y = margin.top + index * slot + (slot - barH) / 2;
    const barW = Math.max(2, (row[valueKey] / domain) * plotW);
    const label = svgNode("text", { x: margin.left - 14, y: y + barH / 2 + 4, "text-anchor": "end" });
    label.textContent = displayProvider(row.provider);
    const bar = svgNode("rect", { x: margin.left, y, width: barW, height: barH, rx: 7, fill: providerColor(row.provider) });
    const value = svgNode("text", { x: margin.left + barW + 10, y: y + barH / 2 + 4 });
    value.textContent = formatValue(row[valueKey]);
    svg.append(label, bar, value);
  });
}

function renderTrend(svg, detailed) {
  clearSvg(svg);
  if (!detailed.length) return emptyChart(svg, "No error history yet");
  const rows = aggregateErrors(detailed);
  const dates = [...new Set(rows.map((row) => row.targetDate))].sort();
  const providers = [...new Set(rows.map((row) => row.provider))].sort();
  const width = 1180;
  const height = 430;
  const margin = { top: 58, right: 32, bottom: 58, left: 64 };
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;
  const max = Math.max(...rows.map((row) => row.absErrorC), 0);
  const domain = max > 0 ? max * 1.12 : 1;
  const x = (date) => margin.left + (dates.length === 1 ? plotW / 2 : (dates.indexOf(date) / (dates.length - 1)) * plotW);
  const y = (value) => margin.top + plotH - (value / domain) * plotH;

  for (let i = 0; i <= 5; i += 1) {
    const value = (domain / 5) * i;
    const yy = y(value);
    svg.append(svgNode("line", { x1: margin.left, x2: width - margin.right, y1: yy, y2: yy, class: "grid-line" }));
    const label = svgNode("text", { x: margin.left - 10, y: yy + 4, "text-anchor": "end" });
    label.textContent = `${number(value, 1)}°`;
    svg.append(label);
  }

  tickIndexes(dates.length, 7).forEach((index) => {
    const label = svgNode("text", { x: x(dates[index]), y: height - 22, "text-anchor": "middle" });
    label.textContent = shortDate(dates[index]);
    svg.append(label);
  });

  providers.forEach((provider, index) => {
    const providerRows = rows.filter((row) => row.provider === provider).sort((a, b) => a.targetDate.localeCompare(b.targetDate));
    const points = providerRows.map((row) => `${x(row.targetDate)},${y(row.absErrorC)}`).join(" ");
    svg.append(svgNode("polyline", { points, fill: "none", stroke: providerColor(provider), "stroke-width": 3, "stroke-linejoin": "round", "stroke-linecap": "round" }));
    providerRows.forEach((row) => svg.append(svgNode("circle", { cx: x(row.targetDate), cy: y(row.absErrorC), r: 4, fill: providerColor(provider), stroke: "#fff", "stroke-width": 2 })));

    const legendX = margin.left + index * Math.min(170, plotW / Math.max(providers.length, 1));
    svg.append(svgNode("line", { x1: legendX, x2: legendX + 22, y1: 25, y2: 25, stroke: providerColor(provider), "stroke-width": 3 }));
    const legend = svgNode("text", { x: legendX + 29, y: 29 });
    legend.textContent = displayProvider(provider);
    svg.append(legend);
  });
}

function aggregateErrors(detailed) {
  const groups = groupBy(detailed, (row) => `${row.provider}|${row.targetDate}`);
  return [...groups.values()].map((rows) => ({
    provider: rows[0].provider,
    targetDate: rows[0].targetDate,
    absErrorC: mean(rows.map((row) => row.absErrorC)),
  }));
}

function emptyChart(svg, title) {
  const width = svg.viewBox.baseVal.width || 800;
  const height = svg.viewBox.baseVal.height || 360;
  const label = svgNode("text", { x: width / 2, y: height / 2 - 4, "text-anchor": "middle", class: "empty-label" });
  label.textContent = title;
  const subtitle = svgNode("text", { x: width / 2, y: height / 2 + 21, "text-anchor": "middle", class: "empty-subtitle" });
  subtitle.textContent = "The chart will populate from evaluation CSV data.";
  svg.append(label, subtitle);
}

function renderFailure(error) {
  showNotice(`Dashboard data could not be loaded: ${error.message}`, true);
  el.state.textContent = "Data unavailable";
  el.state.className = "state-badge";
  el.bestProvider.textContent = "Unavailable";
  emptyChart(el.maeChart, "Data unavailable");
  emptyChart(el.winsChart, "Data unavailable");
  emptyChart(el.errorChart, "Data unavailable");
}

function showNotice(message, error = false) {
  el.status.hidden = false;
  el.status.textContent = message;
  el.status.className = `notice${error ? " error" : ""}`;
}

function textCell(value, className = "") {
  const td = document.createElement("td");
  td.textContent = value;
  if (className) td.className = className;
  return td;
}

function cellBadge(rank) {
  const td = document.createElement("td");
  const span = document.createElement("span");
  span.className = `rank${rank === 1 ? " first" : ""}`;
  span.textContent = String(rank);
  td.append(span);
  return td;
}

function groupBy(rows, keyFn) {
  const groups = new Map();
  rows.forEach((row) => {
    const key = keyFn(row);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  });
  return groups;
}

function mean(values) { return values.reduce((sum, value) => sum + value, 0) / values.length; }
function numeric(value) { const parsed = Number.parseFloat(value); return Number.isFinite(parsed) ? parsed : null; }
function isoDate(value) { return /^\d{4}-\d{2}-\d{2}$/.test(String(value ?? "").trim()) ? String(value).trim() : null; }
function cleanProvider(value) { return String(value ?? "").trim().toLowerCase(); }
function displayProvider(value) { return String(value ?? "").split("-").map((part) => part ? part[0].toUpperCase() + part.slice(1) : "").join("-"); }
function number(value, digits = 0) { return Number(value).toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits }); }
function signed(value) { return `${value > 0 ? "+" : ""}${number(value, 2)}`; }
function shortDate(value) { return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short" }).format(new Date(`${value}T00:00:00Z`)); }
function longDate(value) { return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(`${value}T00:00:00Z`)); }
function maxDate(values) { const valid = values.filter(Boolean).sort(); return valid.length ? valid.at(-1) : null; }
function minDate(values) { const valid = values.filter(Boolean).sort(); return valid.length ? valid[0] : null; }
function providerColor(provider) { const providers = ["open-meteo", "openweathermap", "weatherapi", "visualcrossing", "tomorrow"]; const index = providers.indexOf(provider); return COLORS[index >= 0 ? index : hash(provider) % COLORS.length]; }
function hash(value) { return [...String(value)].reduce((acc, char) => ((acc << 5) - acc + char.charCodeAt(0)) >>> 0, 0); }
function clearSvg(svg) { while (svg.firstChild) svg.removeChild(svg.firstChild); }
function svgNode(name, attributes) { const node = document.createElementNS("http://www.w3.org/2000/svg", name); Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, String(value))); return node; }
function tickIndexes(length, maximum) { if (length <= maximum) return Array.from({ length }, (_, index) => index); const step = (length - 1) / (maximum - 1); return [...new Set(Array.from({ length: maximum }, (_, index) => Math.round(index * step)))]; }

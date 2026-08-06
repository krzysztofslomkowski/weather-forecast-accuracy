"use strict";

const DATA_FILES = {
  forecasts: "data/forecasts.csv",
  actuals: "data/actuals.csv",
  detailed: "data/evaluation_detailed.csv",
  mae: "data/evaluation_mae.csv",
};

const EMPTY_MESSAGE =
  "No completed comparisons yet. The dashboard will update automatically once D+3 forecasts have matching actual observations.";

const PROVIDER_COLORS = ["#176b87", "#d17b32", "#6f63b6", "#14785f", "#c44c67", "#687b86"];

const elements = {
  status: document.querySelector("#data-status"),
  rankingBody: document.querySelector("#ranking-body"),
  rankingEmpty: document.querySelector("#ranking-empty"),
  bestProvider: document.querySelector("#kpi-best-provider"),
  bestMae: document.querySelector("#kpi-best-mae"),
  providers: document.querySelector("#kpi-providers"),
  comparisons: document.querySelector("#kpi-comparisons"),
  dateRange: document.querySelector("#kpi-date-range"),
  lastUpdated: document.querySelector("#kpi-last-updated"),
  maeChart: document.querySelector("#mae-chart"),
  errorChart: document.querySelector("#error-chart"),
  winsChart: document.querySelector("#wins-chart"),
};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  try {
    const [forecasts, actuals, detailedRaw, maeRaw] = await Promise.all([
      loadCsv(DATA_FILES.forecasts),
      loadCsv(DATA_FILES.actuals),
      loadCsv(DATA_FILES.detailed),
      loadCsv(DATA_FILES.mae),
    ]);

    const detailed = normalizeDetailedRows(detailedRaw);
    const ranking = buildRanking(maeRaw, detailed);
    const dailyWins = buildDailyWins(detailed);
    const providers = collectProviders(forecasts, detailed, maeRaw);

    renderKpis({ forecasts, actuals, detailed, ranking, providers });
    renderRanking(ranking);
    renderHorizontalBars(elements.maeChart, ranking, {
      labelKey: "provider",
      valueKey: "maeC",
      valueFormatter: (value) => `${formatNumber(value, 2)} °C`,
      emptyTitle: "No MAE values available",
    });
    renderErrorLineChart(elements.errorChart, detailed);
    renderHorizontalBars(elements.winsChart, dailyWins, {
      labelKey: "provider",
      valueKey: "wins",
      valueFormatter: (value) => formatNumber(value, 0),
      emptyTitle: "No daily wins available",
      integerTicks: true,
    });

    if (detailed.length === 0) {
      showStatus(EMPTY_MESSAGE);
    }
  } catch (error) {
    console.error(error);
    renderFailureState();
  }
}

async function loadCsv(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Could not load ${path}: HTTP ${response.status}`);
  }
  return parseCsv(await response.text());
}

function parseCsv(text) {
  const source = text.replace(/^\uFEFF/, "");
  if (!source.trim()) return [];

  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;

  for (let index = 0; index < source.length; index += 1) {
    const char = source[index];
    const next = source[index + 1];

    if (char === '"') {
      if (inQuotes && next === '"') {
        field += '"';
        index += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (char === "," && !inQuotes) {
      row.push(field);
      field = "";
      continue;
    }

    if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && next === "\n") index += 1;
      row.push(field);
      if (row.some((value) => value.trim() !== "")) rows.push(row);
      row = [];
      field = "";
      continue;
    }

    field += char;
  }

  row.push(field);
  if (row.some((value) => value.trim() !== "")) rows.push(row);
  if (rows.length < 2) return [];

  const headers = rows[0].map((value) => value.trim());
  return rows.slice(1).map((values) =>
    Object.fromEntries(headers.map((header, index) => [header, (values[index] ?? "").trim()])),
  );
}

function normalizeDetailedRows(rows) {
  return rows
    .map((row) => {
      const forecast = toNumber(row.forecast_tmax_c);
      const actual = toNumber(row.actual_tmax_c);
      const suppliedAbsoluteError = toNumber(row.abs_error_c);
      const absoluteError =
        suppliedAbsoluteError ?? (forecast !== null && actual !== null ? Math.abs(forecast - actual) : null);

      return {
        provider: cleanProvider(row.provider),
        runDate: normalizeDate(row.run_date),
        targetDate: normalizeDate(row.target_date),
        forecastTmaxC: forecast,
        actualTmaxC: actual,
        absErrorC: absoluteError,
      };
    })
    .filter(
      (row) =>
        row.provider &&
        row.targetDate &&
        row.forecastTmaxC !== null &&
        row.actualTmaxC !== null &&
        row.absErrorC !== null,
    );
}

function buildRanking(maeRows, detailed) {
  const detailedByProvider = groupBy(detailed, (row) => row.provider);
  const summaryByProvider = new Map();

  for (const row of maeRows) {
    const provider = cleanProvider(row.provider);
    const maeC = toNumber(row.mae_c);
    if (!provider || maeC === null) continue;

    summaryByProvider.set(provider, {
      provider,
      maeC,
      observationsCount: toNumber(row.observations_count),
    });
  }

  if (summaryByProvider.size === 0 && detailed.length > 0) {
    for (const [provider, rows] of detailedByProvider.entries()) {
      summaryByProvider.set(provider, {
        provider,
        maeC: mean(rows.map((row) => row.absErrorC)),
        observationsCount: rows.length,
      });
    }
  }

  const ranking = [...summaryByProvider.values()]
    .map((summary) => {
      const providerRows = detailedByProvider.get(summary.provider) ?? [];
      const biasC = providerRows.length
        ? mean(providerRows.map((row) => row.forecastTmaxC - row.actualTmaxC))
        : null;

      return {
        provider: summary.provider,
        observationsCount: summary.observationsCount ?? providerRows.length,
        maeC: summary.maeC,
        biasC,
      };
    })
    .sort((left, right) => left.maeC - right.maeC || left.provider.localeCompare(right.provider));

  return ranking.map((row, index) => ({ ...row, rank: index + 1 }));
}

function buildDailyWins(detailed) {
  const byDate = groupBy(detailed, (row) => row.targetDate);
  const counts = new Map();

  for (const rows of byDate.values()) {
    const minimum = Math.min(...rows.map((row) => row.absErrorC));
    for (const row of rows) {
      if (Math.abs(row.absErrorC - minimum) < 1e-9) {
        counts.set(row.provider, (counts.get(row.provider) ?? 0) + 1);
      }
    }
  }

  return [...counts.entries()]
    .map(([provider, wins]) => ({ provider, wins }))
    .sort((left, right) => right.wins - left.wins || left.provider.localeCompare(right.provider));
}

function collectProviders(forecasts, detailed, maeRows) {
  const providers = new Set();

  for (const row of forecasts) {
    const provider = cleanProvider(row.provider);
    if (provider) providers.add(provider);
  }
  for (const row of detailed) providers.add(row.provider);
  for (const row of maeRows) {
    const provider = cleanProvider(row.provider);
    if (provider) providers.add(provider);
  }

  return providers;
}

function renderKpis({ forecasts, actuals, detailed, ranking, providers }) {
  const best = ranking[0] ?? null;
  elements.bestProvider.textContent = best?.provider ?? "—";
  elements.bestMae.textContent = best ? `${formatNumber(best.maeC, 2)} °C` : "—";
  elements.providers.textContent = formatNumber(providers.size, 0);
  elements.comparisons.textContent = formatNumber(detailed.length, 0);

  const targetDates = detailed.map((row) => row.targetDate).filter(Boolean).sort();
  elements.dateRange.textContent = targetDates.length
    ? `${formatDate(targetDates[0])} — ${formatDate(targetDates[targetDates.length - 1])}`
    : "—";

  const datedRecords = [
    ...forecasts.map((row) => normalizeDate(row.run_date)),
    ...actuals.map((row) => normalizeDate(row.date)),
    ...detailed.map((row) => row.runDate),
  ]
    .filter(Boolean)
    .sort();

  elements.lastUpdated.textContent = datedRecords.length
    ? formatDate(datedRecords[datedRecords.length - 1])
    : "—";
}

function renderRanking(ranking) {
  elements.rankingBody.replaceChildren();
  elements.rankingEmpty.hidden = ranking.length > 0;

  for (const row of ranking) {
    const tableRow = document.createElement("tr");

    const rank = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = "rank-badge";
    badge.textContent = String(row.rank);
    rank.append(badge);

    const provider = document.createElement("td");
    provider.className = "provider-cell";
    provider.textContent = row.provider;

    const observations = document.createElement("td");
    observations.className = "numeric";
    observations.textContent = formatNumber(row.observationsCount, 0);

    const mae = document.createElement("td");
    mae.className = `numeric${row.rank === 1 ? " metric-good" : ""}`;
    mae.textContent = `${formatNumber(row.maeC, 2)} °C`;

    const bias = document.createElement("td");
    bias.className = "numeric";
    bias.textContent = row.biasC === null ? "—" : `${formatSigned(row.biasC)} °C`;

    tableRow.append(rank, provider, observations, mae, bias);
    elements.rankingBody.append(tableRow);
  }
}

function renderHorizontalBars(svg, rows, options) {
  clearSvg(svg);
  if (rows.length === 0) {
    renderEmptyChart(svg, options.emptyTitle);
    return;
  }

  const width = 820;
  const height = 360;
  const margin = { top: 20, right: 92, bottom: 45, left: 160 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const maximumValue = Math.max(...rows.map((row) => row[options.valueKey]));
  const domainMaximum = maximumValue > 0 ? maximumValue * 1.12 : 1;
  const rowHeight = plotHeight / Math.max(rows.length, 1);
  const barHeight = Math.min(34, rowHeight * 0.58);
  const tickCount = 5;

  for (let tick = 0; tick <= tickCount; tick += 1) {
    const value = (domainMaximum / tickCount) * tick;
    const x = margin.left + (value / domainMaximum) * plotWidth;
    svg.append(
      svgElement("line", {
        x1: x,
        x2: x,
        y1: margin.top,
        y2: height - margin.bottom,
        class: "grid-line",
      }),
    );

    const label = svgElement("text", {
      x,
      y: height - 18,
      "text-anchor": "middle",
    });
    label.textContent = options.integerTicks ? formatNumber(value, 0) : formatNumber(value, 1);
    svg.append(label);
  }

  rows.forEach((row, index) => {
    const value = row[options.valueKey];
    const y = margin.top + index * rowHeight + (rowHeight - barHeight) / 2;
    const widthValue = Math.max(2, (value / domainMaximum) * plotWidth);

    const label = svgElement("text", {
      x: margin.left - 15,
      y: y + barHeight / 2 + 4,
      "text-anchor": "end",
    });
    label.textContent = row[options.labelKey];

    const bar = svgElement("rect", {
      x: margin.left,
      y,
      width: widthValue,
      height: barHeight,
      rx: 7,
      fill: colorForProvider(row.provider),
    });

    const valueLabel = svgElement("text", {
      x: margin.left + widthValue + 10,
      y: y + barHeight / 2 + 4,
      "text-anchor": "start",
    });
    valueLabel.textContent = options.valueFormatter(value);

    svg.append(label, bar, valueLabel);
  });
}

function renderErrorLineChart(svg, detailed) {
  clearSvg(svg);
  if (detailed.length === 0) {
    renderEmptyChart(svg, "No error observations available");
    return;
  }

  const aggregated = aggregateProviderDateErrors(detailed);
  const dates = [...new Set(aggregated.map((row) => row.targetDate))].sort();
  const providers = [...new Set(aggregated.map((row) => row.provider))].sort();

  if (dates.length === 0 || providers.length === 0) {
    renderEmptyChart(svg, "No error observations available");
    return;
  }

  const width = 1080;
  const height = 420;
  const margin = { top: 60, right: 40, bottom: 62, left: 68 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const maximumError = Math.max(...aggregated.map((row) => row.absErrorC));
  const domainMaximum = maximumError > 0 ? maximumError * 1.12 : 1;

  const xScale = (date) => {
    const index = dates.indexOf(date);
    return margin.left + (dates.length === 1 ? plotWidth / 2 : (index / (dates.length - 1)) * plotWidth);
  };
  const yScale = (value) => margin.top + plotHeight - (value / domainMaximum) * plotHeight;

  for (let tick = 0; tick <= 5; tick += 1) {
    const value = (domainMaximum / 5) * tick;
    const y = yScale(value);
    svg.append(
      svgElement("line", {
        x1: margin.left,
        x2: width - margin.right,
        y1: y,
        y2: y,
        class: "grid-line",
      }),
    );
    const label = svgElement("text", {
      x: margin.left - 12,
      y: y + 4,
      "text-anchor": "end",
    });
    label.textContent = `${formatNumber(value, 1)}°`;
    svg.append(label);
  }

  const visibleDateIndexes = chooseTickIndexes(dates.length, 7);
  for (const index of visibleDateIndexes) {
    const date = dates[index];
    const label = svgElement("text", {
      x: xScale(date),
      y: height - 28,
      "text-anchor": "middle",
    });
    label.textContent = formatShortDate(date);
    svg.append(label);
  }

  const legend = svgElement("g", { transform: `translate(${margin.left}, 21)` });
  let legendX = 0;
  providers.forEach((provider) => {
    const color = colorForProvider(provider);
    legend.append(svgElement("circle", { cx: legendX + 5, cy: 7, r: 5, fill: color }));
    const text = svgElement("text", { x: legendX + 16, y: 11 });
    text.textContent = provider;
    legend.append(text);
    legendX += Math.max(110, provider.length * 8 + 42);
  });
  svg.append(legend);

  const byProvider = groupBy(aggregated, (row) => row.provider);
  for (const provider of providers) {
    const rows = (byProvider.get(provider) ?? []).sort((a, b) => a.targetDate.localeCompare(b.targetDate));
    const points = rows.map((row) => `${xScale(row.targetDate)},${yScale(row.absErrorC)}`).join(" ");
    const color = colorForProvider(provider);

    if (rows.length > 1) {
      svg.append(
        svgElement("polyline", {
          points,
          fill: "none",
          stroke: color,
          "stroke-width": 3,
          "stroke-linejoin": "round",
          "stroke-linecap": "round",
        }),
      );
    }

    for (const row of rows) {
      const circle = svgElement("circle", {
        cx: xScale(row.targetDate),
        cy: yScale(row.absErrorC),
        r: 4.5,
        fill: color,
        stroke: "#ffffff",
        "stroke-width": 2,
      });
      const title = svgElement("title");
      title.textContent = `${provider}: ${formatNumber(row.absErrorC, 2)} °C on ${row.targetDate}`;
      circle.append(title);
      svg.append(circle);
    }
  }

  svg.append(
    svgElement("line", {
      x1: margin.left,
      x2: margin.left,
      y1: margin.top,
      y2: height - margin.bottom,
      class: "axis-line",
    }),
    svgElement("line", {
      x1: margin.left,
      x2: width - margin.right,
      y1: height - margin.bottom,
      y2: height - margin.bottom,
      class: "axis-line",
    }),
  );
}

function aggregateProviderDateErrors(detailed) {
  const groups = groupBy(detailed, (row) => `${row.provider}__${row.targetDate}`);
  return [...groups.values()].map((rows) => ({
    provider: rows[0].provider,
    targetDate: rows[0].targetDate,
    absErrorC: mean(rows.map((row) => row.absErrorC)),
  }));
}

function renderEmptyChart(svg, titleText) {
  const title = svgElement("text", {
    x: "50%",
    y: "47%",
    "text-anchor": "middle",
    class: "chart-empty-title",
  });
  title.textContent = titleText;

  const copy = svgElement("text", {
    x: "50%",
    y: "55%",
    "text-anchor": "middle",
    class: "chart-empty-copy",
  });
  copy.textContent = "Charts will render automatically when completed comparisons are available.";
  svg.append(title, copy);
}

function renderFailureState() {
  showStatus(
    "Dashboard data could not be loaded. Confirm that docs/data contains the four CSV files and that the site is served over HTTP.",
    true,
  );
  elements.rankingEmpty.hidden = false;
  renderEmptyChart(elements.maeChart, "Data could not be loaded");
  renderEmptyChart(elements.errorChart, "Data could not be loaded");
  renderEmptyChart(elements.winsChart, "Data could not be loaded");
}

function showStatus(message, isError = false) {
  elements.status.hidden = false;
  elements.status.textContent = message;
  elements.status.classList.toggle("is-error", isError);
}

function clearSvg(svg) {
  svg.replaceChildren();
}

function svgElement(tagName, attributes = {}) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", tagName);
  for (const [key, value] of Object.entries(attributes)) {
    element.setAttribute(key, String(value));
  }
  return element;
}

function groupBy(items, keySelector) {
  const groups = new Map();
  for (const item of items) {
    const key = keySelector(item);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(item);
  }
  return groups;
}

function mean(values) {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
}

function cleanProvider(value) {
  return typeof value === "string" ? value.trim() : "";
}

function toNumber(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function normalizeDate(value) {
  if (typeof value !== "string") return "";
  const match = value.trim().match(/^(\d{4}-\d{2}-\d{2})/);
  return match ? match[1] : "";
}

function formatNumber(value, digits = 2) {
  return new Intl.NumberFormat("en-GB", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

function formatSigned(value) {
  if (Math.abs(value) < 0.005) return formatNumber(0, 2);
  return `${value > 0 ? "+" : "−"}${formatNumber(Math.abs(value), 2)}`;
}

function formatDate(date) {
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${date}T00:00:00Z`));
}

function formatShortDate(date) {
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    timeZone: "UTC",
  }).format(new Date(`${date}T00:00:00Z`));
}

function colorForProvider(provider) {
  let hash = 0;
  for (const char of provider) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return PROVIDER_COLORS[hash % PROVIDER_COLORS.length];
}

function chooseTickIndexes(length, maximumTicks) {
  if (length <= maximumTicks) return Array.from({ length }, (_, index) => index);
  const result = new Set([0, length - 1]);
  const step = (length - 1) / (maximumTicks - 1);
  for (let index = 1; index < maximumTicks - 1; index += 1) {
    result.add(Math.round(index * step));
  }
  return [...result].sort((left, right) => left - right);
}

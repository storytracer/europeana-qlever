// Europeana Data Explorer — server-backed edition.
//
// All queries run server-side in Python DuckDB. The browser just sends JSON
// filter specs over fetch() and renders results with Chart.js.

const TOP_VALUES_PER_FACET = 200;
const DEBOUNCE_MS = 150;
const EUROPEANA_PORTAL = "https://www.europeana.eu/";
const EUROPEANA_DATA = "http://data.europeana.eu/";

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

const $ = (id) => document.getElementById(id);
const fmt = new Intl.NumberFormat();
const fmtN = (n) => (n == null ? "—" : fmt.format(Number(n)));

function debounce(fn, ms) {
  let t = null;
  return (...args) => {
    if (t) clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

function setLoading(show, text) {
  const el = $("loading");
  if (text) $("loading-text").textContent = text;
  el.classList.toggle("hidden", !show);
}

function showError(message) {
  const box = document.createElement("div");
  box.className = "error";
  box.textContent = message;
  document.body.appendChild(box);
  console.error(message);
}

async function api(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${path}: ${res.status} ${text}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let columns = [];          // [{name, type, category, min?, max?}]
let columnByName = new Map();
let totalCount = 0;
let chart = null;
let queryId = 0;
let labelColumns = new Set();   // columns whose values can be resolved to labels
const labelCache = new Map();   // iri → label (or "" when known to be unresolvable)

const state = {
  filters: {},              // { col: {kind, ...} }
  groupBy: null,
};

// ---------------------------------------------------------------------------
// Label lookup (lazy, server-resolved)
// ---------------------------------------------------------------------------

async function fetchLabels(values) {
  if (!labelColumns.size) return;
  const need = [];
  const seen = new Set();
  for (const v of values) {
    if (typeof v !== "string" || !v) continue;
    if (labelCache.has(v) || seen.has(v)) continue;
    seen.add(v);
    need.push(v);
  }
  if (!need.length) return;
  try {
    const res = await api("/api/labels", { values: need });
    const labels = res.labels || {};
    for (const v of need) {
      labelCache.set(v, labels[v] ?? "");
    }
  } catch (e) {
    // Mark as resolved-empty so we don't retry on every render.
    for (const v of need) labelCache.set(v, "");
    console.warn("label lookup failed", e);
  }
}

function labelFor(value) {
  if (typeof value !== "string") return "";
  return labelCache.get(value) || "";
}

// ---------------------------------------------------------------------------
// Facets
// ---------------------------------------------------------------------------

function renderFacets() {
  const list = $("facets-list");
  list.innerHTML = "";

  const groupBySelect = $("group-by");
  groupBySelect.innerHTML = "";

  for (const c of columns) {
    if (c.category === "skip") continue;
    const el = document.createElement("div");
    el.className = "facet";
    el.dataset.col = c.name;
    el.innerHTML = `
      <h4>${c.name}<span class="count"></span></h4>
      <div class="facet-body"></div>
    `;
    list.appendChild(el);
    buildFacetBody(c, el.querySelector(".facet-body"));

    if (c.category === "categorical" || c.category === "boolean") {
      const opt = document.createElement("option");
      opt.value = c.name;
      opt.textContent = c.name;
      groupBySelect.appendChild(opt);
    }
  }

  if (!state.groupBy && groupBySelect.options.length) {
    state.groupBy = groupBySelect.options[0].value;
  }
  if (state.groupBy) groupBySelect.value = state.groupBy;
}

function buildFacetBody(col, body) {
  if (col.category === "boolean") {
    const active = state.filters[col.name];
    const mark = (v) => (active && active.kind === "bool" && active.value === v) ? "active" : "";
    const anyMark = !active ? "active" : "";
    body.innerHTML = `
      <div class="toggle">
        <button data-v="any" class="${anyMark}">Any</button>
        <button data-v="true" class="${mark(true)}">True</button>
        <button data-v="false" class="${mark(false)}">False</button>
      </div>
    `;
    body.querySelectorAll("button").forEach((b) => {
      b.addEventListener("click", () => {
        body.querySelectorAll("button").forEach((x) => x.classList.remove("active"));
        b.classList.add("active");
        const v = b.dataset.v;
        if (v === "any") delete state.filters[col.name];
        else state.filters[col.name] = { kind: "bool", value: v === "true" };
        triggerUpdate();
      });
    });
  } else if (col.category === "numeric") {
    const active = state.filters[col.name];
    const lo = active?.min ?? col.min ?? 0;
    const hi = active?.max ?? col.max ?? 0;
    body.innerHTML = `
      <div class="range">
        <span class="muted">min</span>
        <input type="number" class="min" value="${lo}" />
        <span class="muted">max</span>
        <input type="number" class="max" value="${hi}" />
      </div>
      <div class="muted" style="margin-top:4px">Data range ${fmtN(col.min)}–${fmtN(col.max)}</div>
    `;
    const commit = () => {
      const min = body.querySelector(".min").value;
      const max = body.querySelector(".max").value;
      const minN = min === "" ? null : Number(min);
      const maxN = max === "" ? null : Number(max);
      if (minN == null && maxN == null) delete state.filters[col.name];
      else state.filters[col.name] = { kind: "range", min: minN, max: maxN };
      triggerUpdate();
    };
    body.querySelector(".min").addEventListener("change", commit);
    body.querySelector(".max").addEventListener("change", commit);
  } else {
    body.innerHTML = `
      <div class="facet-search-slot"></div>
      <div class="facet-values muted">Waiting…</div>
    `;
  }
}

async function loadFacetValues(col) {
  const facet = document.querySelector(`.facet[data-col="${col.name}"]`);
  if (!facet) return;
  const body = facet.querySelector(".facet-body");
  const container = body.querySelector(".facet-values");
  const searchSlot = body.querySelector(".facet-search-slot");
  const countEl = facet.querySelector("h4 .count");

  let cache = col._cache;
  if (!cache) {
    container.classList.add("muted");
    container.textContent = "Loading top values…";
    try {
      const res = await api("/api/top-values", { col: col.name, limit: TOP_VALUES_PER_FACET });
      cache = { rows: res.values, truncated: !!res.truncated };
      col._cache = cache;
    } catch (e) {
      container.innerHTML = `<span class="muted">Failed: ${e.message}</span>`;
      return;
    }
  }

  if (countEl) {
    countEl.textContent = cache.truncated
      ? `${fmt.format(cache.rows.length)}+ values`
      : `${fmt.format(cache.rows.length)} values`;
  }
  renderFacetValueList(col, container, cache.rows);

  const matches = labelColumns.has(col.name)
    ? (q, row) => {
        const v = String(row.value ?? "").toLowerCase();
        const l = labelFor(row.value).toLowerCase();
        return v.includes(q) || (l && l.includes(q));
      }
    : (q, row) => String(row.value ?? "").toLowerCase().includes(q);

  if (cache.truncated) {
    searchSlot.innerHTML = '<input type="search" placeholder="Search top values…" />';
    const searchInput = searchSlot.querySelector("input");
    searchInput.addEventListener("input", () => {
      const q = searchInput.value.toLowerCase();
      const filtered = cache.rows.filter((r) => matches(q, r));
      renderFacetValueList(col, container, filtered);
    });
  }

  // Lazy-resolve labels for the visible top values, then re-render.
  if (labelColumns.has(col.name)) {
    await fetchLabels(cache.rows.map((r) => r.value));
    // Re-render with the same currently-visible filter applied.
    const searchInput = searchSlot.querySelector("input");
    const q = searchInput ? searchInput.value.toLowerCase() : "";
    const visible = q
      ? cache.rows.filter((r) => matches(q, r))
      : cache.rows;
    renderFacetValueList(col, container, visible);
  }
}

function renderFacetValueList(col, container, rows) {
  container.innerHTML = "";
  container.classList.remove("muted");
  const selected = new Set(state.filters[col.name]?.values ?? []);
  if (rows.length === 0) {
    container.innerHTML = '<div class="muted">No values.</div>';
    return;
  }
  const resolveLabels = labelColumns.has(col.name);
  for (const r of rows) {
    const v = r.value;
    const raw = v == null ? "(null)" : String(v);
    const resolved = resolveLabels ? labelFor(v) : "";
    const display = resolved || raw;
    const row = document.createElement("label");
    row.className = "facet-value";
    const checked = selected.has(v);
    const title = resolved ? `${resolved}\n${raw}` : raw;
    row.innerHTML = `
      <input type="checkbox" ${checked ? "checked" : ""} />
      <span class="fv-label" title="${title.replace(/"/g, "&quot;")}">${display}</span>
      <span class="fv-count">${fmt.format(r.count)}</span>
    `;
    row.querySelector("input").addEventListener("change", (e) => {
      const current = state.filters[col.name]?.values ?? [];
      let next;
      if (e.target.checked) next = [...current, v];
      else next = current.filter((x) => x !== v);
      if (next.length === 0) delete state.filters[col.name];
      else state.filters[col.name] = { kind: "in", values: next };
      triggerUpdate();
    });
    container.appendChild(row);
  }
}

async function loadAllFacetValues() {
  for (const c of columns) {
    if (c.category === "categorical") {
      await loadFacetValues(c);
    }
  }
}

// ---------------------------------------------------------------------------
// Chart + summary
// ---------------------------------------------------------------------------

function renderChart(rows, groupBy) {
  const useLabels = labelColumns.has(groupBy);
  const labels = rows.map((r) => {
    const raw = r.value == null ? "(null)" : String(r.value);
    if (!useLabels) return raw;
    return labelFor(r.value) || raw;
  });
  const data = rows.map((r) => r.count);
  const ctx = $("chart").getContext("2d");

  const isDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const grid = isDark ? "#1f2937" : "#e5e7eb";
  const fg = isDark ? "#e5e7eb" : "#111418";
  const bar = isDark ? "#60a5fa" : "#3b82f6";

  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: `count by ${groupBy}`,
        data,
        backgroundColor: bar,
        borderWidth: 0,
      }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${fmt.format(ctx.parsed.x)} items`,
          },
        },
      },
      scales: {
        x: {
          ticks: { color: fg, callback: (v) => fmt.format(v) },
          grid: { color: grid },
        },
        y: {
          ticks: { color: fg, autoSkip: false },
          grid: { display: false },
        },
      },
      onClick: (_event, elements) => {
        if (!elements.length) return;
        const idx = elements[0].index;
        toggleDrillDown(groupBy, rows[idx].value);
      },
    },
  });
}

function toggleDrillDown(colName, rawValue) {
  const col = columnByName.get(colName);
  if (!col) return;
  if (col.category === "boolean") {
    state.filters[colName] = { kind: "bool", value: !!rawValue };
  } else {
    const current = state.filters[colName]?.values ?? [];
    const exists = current.some((v) => v === rawValue);
    const next = exists
      ? current.filter((v) => v !== rawValue)
      : [...current, rawValue];
    if (next.length === 0) delete state.filters[colName];
    else state.filters[colName] = { kind: "in", values: next };
  }
  renderFacets();
  loadAllFacetValues();
  triggerUpdate();
}

function renderSummary(filtered, countries, providers) {
  $("card-total").textContent = fmtN(totalCount);
  $("card-filtered").textContent = fmtN(filtered);
  if (totalCount > 0) {
    const pct = ((filtered / totalCount) * 100).toFixed(1);
    $("card-filtered-pct").textContent = `${pct}% of total`;
  } else {
    $("card-filtered-pct").textContent = "";
  }
  $("card-countries").textContent = fmtN(countries);
  $("card-providers").textContent = fmtN(providers);
}

// ---------------------------------------------------------------------------
// Sample table
// ---------------------------------------------------------------------------

function europeanaLinkFor(iri) {
  if (typeof iri !== "string") return null;
  if (!iri.startsWith(EUROPEANA_DATA)) return null;
  return EUROPEANA_PORTAL + iri.substring(EUROPEANA_DATA.length);
}

function renderSample(rows) {
  const host = $("sample-table");
  if (!rows.length) {
    host.textContent = "No rows matched the current filters.";
    host.classList.add("muted");
    return;
  }
  host.classList.remove("muted");
  const cols = Object.keys(rows[0]);
  const table = document.createElement("table");
  table.className = "sample";
  const thead = document.createElement("thead");
  const trh = document.createElement("tr");
  for (const c of cols) {
    const th = document.createElement("th");
    th.textContent = c;
    trh.appendChild(th);
  }
  thead.appendChild(trh);
  table.appendChild(thead);
  const tbody = document.createElement("tbody");
  for (const r of rows) {
    const tr = document.createElement("tr");
    for (const c of cols) {
      const td = document.createElement("td");
      const v = r[c];
      if (c === "k_iri") {
        const href = europeanaLinkFor(v);
        if (href) {
          const a = document.createElement("a");
          a.href = href;
          a.target = "_blank";
          a.rel = "noopener noreferrer";
          a.textContent = v;
          td.appendChild(a);
        } else {
          td.textContent = v == null ? "" : String(v);
        }
      } else {
        td.textContent = v == null ? "" : String(v);
      }
      td.title = v == null ? "" : String(v);
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  host.innerHTML = "";
  host.appendChild(table);
}

async function loadSample() {
  const btn = $("sample-btn");
  btn.disabled = true;
  const host = $("sample-table");
  host.textContent = "Loading sample…";
  host.classList.add("muted");
  try {
    const res = await api("/api/sample", { filters: state.filters, n: 10 });
    renderSample(res.rows);
  } catch (e) {
    host.textContent = `Sample failed: ${e.message}`;
  } finally {
    btn.disabled = false;
  }
}

// ---------------------------------------------------------------------------
// Orchestration
// ---------------------------------------------------------------------------

const triggerUpdate = debounce(update, DEBOUNCE_MS);

async function update() {
  const myId = ++queryId;
  try {
    const res = await api("/api/summary", {
      filters: state.filters,
      group_by: state.groupBy,
    });
    if (myId !== queryId) return;
    renderSummary(res.filtered, res.countries, res.providers);
    renderChart(res.chart, state.groupBy);
    // Lazy-resolve labels for the chart bars and re-render once they arrive.
    if (labelColumns.has(state.groupBy)) {
      await fetchLabels(res.chart.map((r) => r.value));
      if (myId !== queryId) return;
      renderChart(res.chart, state.groupBy);
    }
  } catch (e) {
    showError(`Query failed: ${e.message}`);
  }
}

function clearFilters() {
  for (const k of Object.keys(state.filters)) delete state.filters[k];
  renderFacets();
  loadAllFacetValues();
  triggerUpdate();
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

async function main() {
  try {
    setLoading(true, "Connecting to server…");
    const schema = await api("/api/schema");
    columns = schema.columns;
    columnByName = new Map(columns.map((c) => [c.name, c]));
    totalCount = schema.total;
    labelColumns = new Set(schema.label_columns || []);

    renderFacets();

    $("group-by").addEventListener("change", (e) => {
      state.groupBy = e.target.value;
      triggerUpdate();
    });
    $("sample-btn").addEventListener("click", loadSample);
    $("clear-filters").addEventListener("click", clearFilters);

    await update();
    setLoading(false);

    // Populate facet checklists in the background after the chart is up.
    loadAllFacetValues();
  } catch (e) {
    setLoading(false);
    showError(`Startup failed: ${e.message}`);
    console.error(e);
  }
}

main();

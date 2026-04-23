// Europeana Data Explorer — DuckDB-WASM single-page app.
//
// Loads DuckDB-WASM from jsDelivr, registers a Parquet file via httpfs
// (HTTP range requests), auto-discovers the schema, and renders a
// faceted bar-chart explorer over the rows.

import * as duckdb from "https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.28.0/+esm";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const DEFAULT_DATA_PATH = "/data/group_items.parquet";
const TOP_VALUES_PER_FACET = 200;
const BARS_IN_CHART = 30;
const DEBOUNCE_MS = 200;
const EUROPEANA_PORTAL = "https://www.europeana.eu/";
const EUROPEANA_DATA = "http://data.europeana.eu/";

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

const $ = (id) => document.getElementById(id);
const fmt = new Intl.NumberFormat();
const fmtN = (n) => (n == null ? "—" : fmt.format(Number(n)));

function escapeSQL(v) {
  if (v === null || v === undefined) return "NULL";
  return `'${String(v).replace(/'/g, "''")}'`;
}

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

// Convert a DuckDB Arrow result into an array of plain objects.
function rowsOf(result) {
  const out = [];
  for (const row of result) out.push(row.toJSON());
  return out;
}

function parquetUrl() {
  const params = new URLSearchParams(location.search);
  const raw = params.get("data") || DEFAULT_DATA_PATH;
  // Allow absolute URLs (e.g. HuggingFace) to pass through unchanged; resolve
  // relative paths against the current origin so the worker has a full URL.
  try { return new URL(raw).href; }
  catch { return new URL(raw, window.location.href).href; }
}

// ---------------------------------------------------------------------------
// DuckDB-WASM bootstrap
// ---------------------------------------------------------------------------

let db;          // AsyncDuckDB
let conn;        // AsyncDuckDBConnection
let columns;     // [{name, type, cardinality, category}]
let totalCount = 0;
let chart = null;

async function initDuckDB() {
  const bundles = duckdb.getJsDelivrBundles();
  const bundle = await duckdb.selectBundle(bundles);
  const workerUrl = URL.createObjectURL(
    new Blob([`importScripts("${bundle.mainWorker}");`], { type: "text/javascript" })
  );
  const worker = new Worker(workerUrl);
  const logger = new duckdb.ConsoleLogger();
  db = new duckdb.AsyncDuckDB(logger, worker);
  await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
  URL.revokeObjectURL(workerUrl);
  conn = await db.connect();
}

async function registerParquet(url) {
  // DuckDB-WASM has a built-in HTTP VFS that handles Range requests natively,
  // so we skip the httpfs extension (which isn't bundled in the +esm build).
  // registerFileURL maps a virtual file name to the real URL; queries then
  // reference the virtual name and DuckDB fetches the bytes it needs.
  await db.registerFileURL(
    "items.parquet",
    url,
    duckdb.DuckDBDataProtocol.HTTP,
    false,
  );
  await conn.query(`CREATE VIEW items AS SELECT * FROM 'items.parquet'`);
}

// ---------------------------------------------------------------------------
// Schema discovery
// ---------------------------------------------------------------------------

async function describeSchema() {
  const res = await conn.query(`DESCRIBE SELECT * FROM items LIMIT 0`);
  // DuckDB returns columns: column_name, column_type, null, key, default, extra
  return rowsOf(res).map((r) => ({
    name: r.column_name,
    type: String(r.column_type).toUpperCase(),
  }));
}

function categoryFor(col) {
  // Classification is by type + prefix only. We deliberately avoid probing
  // distinct counts at boot: each probe is a full-table scan and DuckDB-WASM
  // runs them serially on its worker, which adds tens of seconds over HTTP.
  // Instead, top-value loaders decide whether to show a search box based on
  // whether the limit is hit.
  const t = col.type;
  if (col.name.startsWith("k_")) return "skip";
  if (t === "BOOLEAN") return "boolean";
  if (t.includes("INT") || t === "DOUBLE" || t === "FLOAT" || t === "REAL" || t.startsWith("DECIMAL")) {
    return "numeric";
  }
  if (t.startsWith("VARCHAR") || t === "STRING" || t === "TEXT") {
    return "categorical";
  }
  return "skip";
}

async function probeRanges(cols) {
  // Batch MIN/MAX for every numeric column into one scan.
  const numerics = cols.filter((c) => c.category === "numeric");
  if (numerics.length === 0) return;
  const selects = numerics.flatMap((c, i) => [
    `MIN("${c.name}") AS mn${i}`,
    `MAX("${c.name}") AS mx${i}`,
  ]).join(", ");
  try {
    const res = await conn.query(`SELECT ${selects} FROM items`);
    const row = rowsOf(res)[0];
    numerics.forEach((c, i) => {
      c.min = row[`mn${i}`] != null ? Number(row[`mn${i}`]) : null;
      c.max = row[`mx${i}`] != null ? Number(row[`mx${i}`]) : null;
    });
  } catch (e) {
    console.warn("range probe failed:", e);
  }
}

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const state = {
  filters: {}, // { colName: { kind: 'in'|'bool'|'range', values: [...] | bool | {min,max} } }
  groupBy: null,
};

let queryId = 0;

function buildWhere() {
  const parts = [];
  for (const [name, f] of Object.entries(state.filters)) {
    if (f.kind === "in" && f.values.length > 0) {
      const list = f.values.map(escapeSQL).join(", ");
      parts.push(`"${name}" IN (${list})`);
    } else if (f.kind === "bool") {
      parts.push(`"${name}" = ${f.value ? "TRUE" : "FALSE"}`);
    } else if (f.kind === "range") {
      if (f.min != null) parts.push(`"${name}" >= ${Number(f.min)}`);
      if (f.max != null) parts.push(`"${name}" <= ${Number(f.max)}`);
    }
  }
  return parts.length ? `WHERE ${parts.join(" AND ")}` : "";
}

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

async function countTotal() {
  const res = await conn.query(`SELECT COUNT(*) AS n FROM items`);
  return Number(rowsOf(res)[0].n);
}

async function countFiltered(where) {
  const res = await conn.query(`SELECT COUNT(*) AS n FROM items ${where}`);
  return Number(rowsOf(res)[0].n);
}

async function topValues(colName, where, limit = TOP_VALUES_PER_FACET) {
  const res = await conn.query(`
    SELECT "${colName}" AS v, COUNT(*) AS n
    FROM items ${where}
    WHERE "${colName}" IS NOT NULL
    GROUP BY 1 ORDER BY 2 DESC LIMIT ${limit}
  `.replace(/\s+/g, " "));
  return rowsOf(res).map((r) => ({ value: r.v, count: Number(r.n) }));
}

async function groupByQuery(colName, where) {
  const res = await conn.query(`
    SELECT "${colName}" AS v, COUNT(*) AS n
    FROM items ${where}
    GROUP BY 1 ORDER BY 2 DESC LIMIT ${BARS_IN_CHART}
  `.replace(/\s+/g, " "));
  return rowsOf(res).map((r) => ({
    value: r.v == null ? "(null)" : String(r.v),
    count: Number(r.n),
    rawValue: r.v,
  }));
}

async function randomSample(where, n = 10) {
  // USING SAMPLE over the filtered set. With WHERE DuckDB applies SAMPLE
  // after the filter, which is what we want.
  const res = await conn.query(
    `SELECT * FROM items ${where} USING SAMPLE ${n} ROWS`
  );
  return rowsOf(res);
}

// ---------------------------------------------------------------------------
// Rendering: facets
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

    // Populate group-by select for categorical/boolean.
    if (c.category === "categorical" || c.category === "boolean") {
      const opt = document.createElement("option");
      opt.value = c.name;
      opt.textContent = c.name;
      groupBySelect.appendChild(opt);
    }
  }

  if (!state.groupBy && groupBySelect.options.length) {
    state.groupBy = groupBySelect.options[0].value;
    groupBySelect.value = state.groupBy;
  }
}

function buildFacetBody(col, body) {
  if (col.category === "boolean") {
    body.innerHTML = `
      <div class="toggle">
        <button data-v="any" class="active">Any</button>
        <button data-v="true">True</button>
        <button data-v="false">False</button>
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
    const lo = col.min ?? 0;
    const hi = col.max ?? 0;
    body.innerHTML = `
      <div class="range">
        <span class="muted">min</span>
        <input type="number" class="min" value="${lo}" />
        <span class="muted">max</span>
        <input type="number" class="max" value="${hi}" />
      </div>
      <div class="muted" style="margin-top:4px">Range ${fmtN(lo)}–${fmtN(hi)}</div>
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
    // categorical — skeleton only; values are loaded in a later pass.
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

  let rows = col._allValues;
  if (!rows) {
    container.classList.add("muted");
    container.textContent = "Loading top values…";
    try {
      rows = await topValues(col.name, "");
      col._allValues = rows;
    } catch (e) {
      container.innerHTML = `<span class="muted">Failed to load: ${e.message}</span>`;
      return;
    }
  }

  if (countEl) {
    countEl.textContent = rows.length >= TOP_VALUES_PER_FACET
      ? `${fmt.format(rows.length)}+ values`
      : `${fmt.format(rows.length)} values`;
  }
  renderFacetValueList(col, container, rows);

  // Only show a search box if we saturated the top-N (more values exist).
  if (rows.length >= TOP_VALUES_PER_FACET) {
    searchSlot.innerHTML = '<input type="search" placeholder="Search top values…" />';
    const searchInput = searchSlot.querySelector("input");
    searchInput.addEventListener("input", () => {
      const q = searchInput.value.toLowerCase();
      const filtered = rows.filter((r) =>
        String(r.value ?? "").toLowerCase().includes(q)
      );
      renderFacetValueList(col, container, filtered);
    });
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
  for (const r of rows) {
    const v = r.value;
    const label = v == null ? "(null)" : String(v);
    const row = document.createElement("label");
    row.className = "facet-value";
    const checked = selected.has(v);
    row.innerHTML = `
      <input type="checkbox" ${checked ? "checked" : ""} />
      <span class="fv-label" title="${label.replace(/"/g, "&quot;")}">${label}</span>
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

// ---------------------------------------------------------------------------
// Rendering: chart
// ---------------------------------------------------------------------------

function renderChart(rows, groupBy) {
  const labels = rows.map((r) => r.value);
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
        const raw = rows[idx].rawValue;
        toggleDrillDown(groupBy, raw);
      },
    },
  });
}

function toggleDrillDown(colName, rawValue) {
  const col = columns.find((c) => c.name === colName);
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
  // Refresh facet UI so checkboxes reflect the new state.
  renderFacets();
  loadAllFacetValues();
  triggerUpdate();
}

// ---------------------------------------------------------------------------
// Rendering: summary + sample
// ---------------------------------------------------------------------------

function renderSummary(filteredCount, countries, providers) {
  $("card-total").textContent = fmtN(totalCount);
  $("card-filtered").textContent = fmtN(filteredCount);
  if (totalCount > 0) {
    const pct = ((filteredCount / totalCount) * 100).toFixed(1);
    $("card-filtered-pct").textContent = `${pct}% of total`;
  } else {
    $("card-filtered-pct").textContent = "";
  }
  $("card-countries").textContent = fmtN(countries);
  $("card-providers").textContent = fmtN(providers);
}

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
      let v = r[c];
      if (v != null && typeof v === "bigint") v = v.toString();
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

// ---------------------------------------------------------------------------
// Orchestration
// ---------------------------------------------------------------------------

const triggerUpdate = debounce(update, DEBOUNCE_MS);

async function update() {
  const myId = ++queryId;
  const where = buildWhere();
  try {
    const [filteredCount, bars, countries, providers] = await Promise.all([
      countFiltered(where),
      groupByQuery(state.groupBy, where),
      distinctCount("v_edm_country", where),
      distinctCount("v_edm_dataProvider", where),
    ]);
    if (myId !== queryId) return; // stale — drop
    renderSummary(filteredCount, countries, providers);
    renderChart(bars, state.groupBy);
  } catch (e) {
    showError(`Query failed: ${e.message}`);
  }
}

async function distinctCount(colName, where) {
  // Tolerate absent columns (e.g. when pointed at a different Parquet).
  if (!columns.some((c) => c.name === colName)) return null;
  const res = await conn.query(
    `SELECT approx_count_distinct("${colName}") AS n FROM items ${where}`
  );
  return Number(rowsOf(res)[0].n);
}

async function loadAllFacetValues() {
  // Sequential so each facet's result appears as soon as it's ready instead
  // of all landing at the end. DuckDB-WASM's worker is single-threaded so
  // parallel submission would serialize anyway.
  for (const c of columns) {
    if (c.category === "categorical") {
      await loadFacetValues(c);
    }
  }
}

async function loadSample() {
  const btn = $("sample-btn");
  btn.disabled = true;
  const host = $("sample-table");
  host.textContent = "Loading sample…";
  host.classList.add("muted");
  try {
    const rows = await randomSample(buildWhere(), 10);
    renderSample(rows);
  } catch (e) {
    host.textContent = `Sample failed: ${e.message}`;
  } finally {
    btn.disabled = false;
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
    setLoading(true, "Initializing DuckDB-WASM…");
    await initDuckDB();

    setLoading(true, "Registering Parquet file…");
    const url = parquetUrl();
    await registerParquet(url);

    setLoading(true, "Reading schema…");
    columns = await describeSchema();
    for (const c of columns) c.category = categoryFor(c);

    setLoading(true, "Reading Parquet footer…");
    totalCount = await countTotal();
    await probeRanges(columns);

    setLoading(true, "Rendering UI…");
    renderFacets();

    $("group-by").addEventListener("change", (e) => {
      state.groupBy = e.target.value;
      triggerUpdate();
    });
    $("sample-btn").addEventListener("click", loadSample);
    $("clear-filters").addEventListener("click", clearFilters);

    await update();
    setLoading(false);

    // Facet top-values are loaded in the background after the chart is up
    // so the initial interaction isn't blocked on ~1 scan per facet column.
    loadAllFacetValues();
  } catch (e) {
    setLoading(false);
    showError(`Startup failed: ${e.message}`);
    console.error(e);
  }
}

main();

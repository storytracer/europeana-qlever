// Europeana Data Explorer — reactive Preact + htm app.
//
// State lives in the top-level <App>. Effects fetch from the JSON API and
// AbortController cancels stale requests. Labels for any Europeana IRI are
// resolved lazily via a shared, batched fetcher.

import { h, render } from "https://esm.sh/preact@10";
import {
  useState,
  useEffect,
  useRef,
  useMemo,
  useCallback,
} from "https://esm.sh/preact@10/hooks";
import htm from "https://esm.sh/htm@3";

const html = htm.bind(h);

const TOP_VALUES_PER_FACET = 200;
const SAMPLE_SIZE = 10;
const EUROPEANA_PORTAL = "https://www.europeana.eu/";
const EUROPEANA_DATA = "http://data.europeana.eu/";

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

const fmt = new Intl.NumberFormat();
const fmtN = (n) => (n == null ? "—" : fmt.format(Number(n)));

// In-flight request tracking. Every api() call bumps the counter and
// notifies subscribers; useInflight() exposes the count to components
// so they can show a spinner and disable interactive controls. The
// try/finally guarantees the counter stays balanced even when fetch
// rejects (incl. AbortError).
let _inflight = 0;
const _inflightListeners = new Set();
function _bumpInflight(delta) {
  _inflight += delta;
  for (const fn of _inflightListeners) fn(_inflight);
}

async function api(path, body, signal) {
  _bumpInflight(+1);
  try {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
      signal,
    });
    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText);
      throw new Error(`${path}: ${res.status} ${text}`);
    }
    return await res.json();
  } finally {
    _bumpInflight(-1);
  }
}

function useInflight() {
  const [count, setCount] = useState(_inflight);
  useEffect(() => {
    _inflightListeners.add(setCount);
    return () => {
      _inflightListeners.delete(setCount);
    };
  }, []);
  return count;
}

function europeanaLinkFor(iri) {
  if (typeof iri !== "string") return null;
  if (!iri.startsWith(EUROPEANA_DATA)) return null;
  return EUROPEANA_PORTAL + iri.substring(EUROPEANA_DATA.length);
}

function looksLikeEuropeanaIri(v) {
  return typeof v === "string" && v.startsWith(EUROPEANA_DATA);
}

// ---------------------------------------------------------------------------
// Shared label fetcher — batches IRI requests across components within a
// 30 ms window and dedupes against a known set.
// ---------------------------------------------------------------------------

function useLabelFetcher() {
  const [labels, setLabels] = useState({});
  const pendingRef = useRef(new Set());
  const knownRef = useRef(new Set());
  const timerRef = useRef(null);

  const requestLabels = useCallback((iris) => {
    if (!iris) return;
    let any = false;
    for (const iri of iris) {
      if (typeof iri !== "string" || !iri) continue;
      if (knownRef.current.has(iri)) continue;
      knownRef.current.add(iri);
      pendingRef.current.add(iri);
      any = true;
    }
    if (!any || timerRef.current) return;
    timerRef.current = setTimeout(async () => {
      timerRef.current = null;
      const batch = Array.from(pendingRef.current);
      pendingRef.current.clear();
      try {
        const res = await api("/api/labels", { values: batch });
        if (res.labels && Object.keys(res.labels).length) {
          setLabels((prev) => ({ ...prev, ...res.labels }));
        }
      } catch (e) {
        console.warn("label fetch failed", e);
      }
    }, 30);
  }, []);

  return [labels, requestLabels];
}

// ---------------------------------------------------------------------------
// Cards
// ---------------------------------------------------------------------------

function Cards({ total, summary }) {
  const filtered = summary ? summary.filtered : null;
  const pct =
    filtered != null && total > 0
      ? `${((filtered / total) * 100).toFixed(1)}% of total`
      : "";
  return html`
    <div class="cards">
      <div class="card">
        <div class="label">Total items</div>
        <div class="value">${fmtN(total)}</div>
      </div>
      <div class="card">
        <div class="label">Filtered</div>
        <div class="value">${fmtN(filtered)}</div>
        <div class="sub">${pct}</div>
      </div>
      <div class="card">
        <div class="label">Countries</div>
        <div class="value">${fmtN(summary?.countries)}</div>
      </div>
      <div class="card">
        <div class="label">Data providers</div>
        <div class="value">${fmtN(summary?.providers)}</div>
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Facets
// ---------------------------------------------------------------------------

function CategoricalFacet({ col, filters, setFilters, labels, requestLabels }) {
  const [data, setData] = useState(null); // {rows, truncated} | null
  const [search, setSearch] = useState("");
  const [error, setError] = useState(null);

  // Top values for this column should reflect every *other* facet's filter.
  const otherFilters = useMemo(() => {
    const o = {};
    for (const k of Object.keys(filters)) {
      if (k !== col.name) o[k] = filters[k];
    }
    return o;
  }, [filters, col.name]);

  useEffect(() => {
    const ctrl = new AbortController();
    setError(null);
    api(
      "/api/top-values",
      { col: col.name, filters: otherFilters, limit: TOP_VALUES_PER_FACET },
      ctrl.signal
    )
      .then((res) => setData({ rows: res.values, truncated: !!res.truncated }))
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => ctrl.abort();
  }, [col.name, otherFilters]);

  useEffect(() => {
    if (!data) return;
    // Synthetic facets (Topics/Agents/Places/Time periods) come back
    // with `label` inline — only async-fetch labels for rows that
    // don't already have one.
    const missing = data.rows.filter((r) => !r.label).map((r) => r.value);
    if (missing.length) requestLabels(missing);
  }, [data, requestLabels]);

  const selected = new Set(filters[col.name]?.values ?? []);

  const matches = (q, row) => {
    if (!q) return true;
    const v = String(row.value ?? "").toLowerCase();
    const lab = (row.label || labels[row.value] || "").toLowerCase();
    return v.includes(q) || (lab && lab.includes(q));
  };
  const visible = data
    ? data.rows.filter((r) => matches(search.toLowerCase(), r))
    : [];

  function toggle(value, checked) {
    const cur = filters[col.name]?.values ?? [];
    const next = checked ? [...cur, value] : cur.filter((v) => v !== value);
    const f = { ...filters };
    if (next.length === 0) delete f[col.name];
    else f[col.name] = { kind: "in", values: next };
    setFilters(f);
  }

  return html`
    <div class="facet">
      <h4>
        ${col.name}
        <span class="count">
          ${data
            ? data.truncated
              ? `${fmt.format(data.rows.length)}+ values`
              : `${fmt.format(data.rows.length)} values`
            : ""}
        </span>
      </h4>
      ${data && data.truncated
        ? html`<input
            type="search"
            placeholder="Search top values…"
            value=${search}
            onInput=${(e) => setSearch(e.target.value)}
          />`
        : null}
      <div class="facet-values">
        ${error
          ? html`<div class="muted">Failed: ${error}</div>`
          : !data
          ? html`<div class="muted">Loading…</div>`
          : visible.length === 0
          ? html`<div class="muted">No values.</div>`
          : visible.map((r) => {
              const lab = r.label || labels[r.value] || "";
              const raw = r.value == null ? "(null)" : String(r.value);
              const display = lab || raw;
              const title = lab ? `${lab}\n${raw}` : raw;
              return html`
                <label class="facet-value" key=${r.value}>
                  <input
                    type="checkbox"
                    checked=${selected.has(r.value)}
                    onChange=${(e) => toggle(r.value, e.target.checked)}
                  />
                  <span class="fv-label" title=${title}>${display}</span>
                  <span class="fv-count">${fmt.format(r.count)}</span>
                </label>
              `;
            })}
      </div>
    </div>
  `;
}

function FacetSidebar({ schema, filters, setFilters, labels, requestLabels }) {
  return html`
    <aside id="facets">
      <div class="facets-header">
        Filters
        <button class="subtle" onClick=${() => setFilters({})}>clear all</button>
      </div>
      ${schema.columns
        .filter((c) => c.category !== "skip")
        .map((col) => {
          // Every type — categorical, boolean, low-cardinality
          // numeric — renders as a count-list facet. High-cardinality
          // numerics fall through here too: their top-N values still
          // make a useful distribution view, and they're rare in
          // practice (group_items is scalar/categorical by design).
          return html`<${CategoricalFacet}
            key=${col.name}
            col=${col}
            filters=${filters}
            setFilters=${setFilters}
            labels=${labels}
            requestLabels=${requestLabels}
          />`;
        })}
    </aside>
  `;
}

// ---------------------------------------------------------------------------
// Chart
// ---------------------------------------------------------------------------

const DOUGHNUT_COLORS = [
  "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
  "#06b6d4", "#ec4899", "#84cc16", "#f97316", "#6366f1",
];

function ChartView({ summary, groupBy, lowCardinality, labels, onBarClick }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);
  const onClickRef = useRef(onBarClick);

  // Keep latest click handler reachable from the long-lived Chart.js instance.
  useEffect(() => {
    onClickRef.current = onBarClick;
  }, [onBarClick]);

  // Create / destroy when groupBy or chart-type flag changes.
  useEffect(() => {
    if (!canvasRef.current || !groupBy) return;
    const isDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const grid = isDark ? "#1f2937" : "#e5e7eb";
    const fg = isDark ? "#e5e7eb" : "#111418";
    const ctx = canvasRef.current.getContext("2d");

    const config = lowCardinality
      ? {
          type: "doughnut",
          data: {
            labels: [],
            datasets: [
              { data: [], backgroundColor: DOUGHNUT_COLORS, borderWidth: 0 },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "55%",
            plugins: {
              legend: {
                position: "right",
                labels: {
                  color: fg,
                  boxWidth: 12,
                  padding: 8,
                  font: { size: 12 },
                  generateLabels: (chart) => {
                    const ds = chart.data.datasets[0];
                    const total = ds.data.reduce(
                      (a, b) => a + (Number(b) || 0),
                      0
                    );
                    return chart.data.labels.map((label, i) => {
                      const value = Number(ds.data[i]) || 0;
                      const pct =
                        total > 0
                          ? ((value / total) * 100).toFixed(1)
                          : "0.0";
                      return {
                        text: `${label} — ${pct}% (${fmt.format(value)})`,
                        fillStyle:
                          DOUGHNUT_COLORS[i % DOUGHNUT_COLORS.length],
                        strokeStyle:
                          DOUGHNUT_COLORS[i % DOUGHNUT_COLORS.length],
                        index: i,
                      };
                    });
                  },
                },
              },
              tooltip: {
                callbacks: {
                  label: (c) => {
                    const total = c.dataset.data.reduce(
                      (a, b) => a + (Number(b) || 0),
                      0
                    );
                    const pct =
                      total > 0
                        ? ((c.parsed / total) * 100).toFixed(1)
                        : "0.0";
                    return ` ${fmt.format(c.parsed)} (${pct}%)`;
                  },
                },
              },
            },
            onClick: (_evt, els) => {
              if (els.length) onClickRef.current(els[0].index);
            },
          },
        }
      : {
          type: "bar",
          data: {
            labels: [],
            datasets: [
              {
                label: `count by ${groupBy}`,
                data: [],
                backgroundColor: isDark ? "#60a5fa" : "#3b82f6",
                borderWidth: 0,
              },
            ],
          },
          options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: false },
              tooltip: {
                callbacks: {
                  label: (c) => ` ${fmt.format(c.parsed.x)} items`,
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
            onClick: (_evt, els) => {
              if (els.length) onClickRef.current(els[0].index);
            },
          },
        };

    chartRef.current = new Chart(ctx, config);
    return () => {
      chartRef.current?.destroy();
      chartRef.current = null;
    };
  }, [groupBy, lowCardinality]);

  // Push new data when summary or labels change.
  useEffect(() => {
    if (!chartRef.current || !summary) return;
    chartRef.current.data.labels = summary.chart.map((r) => {
      const raw = r.value == null ? "(null)" : String(r.value);
      return labels[r.value] || raw;
    });
    chartRef.current.data.datasets[0].data = summary.chart.map((r) => r.count);
    chartRef.current.update();
  }, [summary, labels]);

  return html`<div class="chart-wrap"><canvas ref=${canvasRef}></canvas></div>`;
}

// ---------------------------------------------------------------------------
// Sample table
// ---------------------------------------------------------------------------

function SampleTable({ filters, labels, requestLabels }) {
  const [rows, setRows] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await api("/api/sample", { filters, n: SAMPLE_SIZE });
      setRows(res.rows);
      const iris = [];
      for (const row of res.rows) {
        for (const v of Object.values(row)) {
          if (looksLikeEuropeanaIri(v)) iris.push(v);
        }
      }
      requestLabels(iris);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  let body;
  if (error) body = html`<div class="muted">Sample failed: ${error}</div>`;
  else if (rows == null)
    body = html`<div class="muted">Click the button above to load samples.</div>`;
  else if (rows.length === 0)
    body = html`<div class="muted">No rows matched the current filters.</div>`;
  else body = html`<${SampleRows} rows=${rows} labels=${labels} />`;

  return html`
    <div class="sample-wrap">
      <div class="sample-header">
        <h3>Sample rows</h3>
        <button class="primary" onClick=${load} disabled=${loading}>
          ${loading ? "Loading…" : `Load ${SAMPLE_SIZE} random samples`}
        </button>
      </div>
      ${body}
    </div>
  `;
}

function SampleRows({ rows, labels }) {
  const cols = Object.keys(rows[0]);
  return html`
    <table class="sample">
      <thead>
        <tr>${cols.map((c) => html`<th key=${c}>${c}</th>`)}</tr>
      </thead>
      <tbody>
        ${rows.map(
          (r, i) => html`
            <tr key=${i}>
              ${cols.map((c) => {
                const v = r[c];
                const lab = (typeof v === "string" && labels[v]) || "";
                const display = lab || (v == null ? "" : String(v));
                const title = lab ? `${lab}\n${v}` : v == null ? "" : String(v);
                const href = c === "k_iri" ? europeanaLinkFor(v) : null;
                if (href) {
                  return html`<td key=${c} title=${title}>
                    <a href=${href} target="_blank" rel="noopener noreferrer">
                      ${display}
                    </a>
                  </td>`;
                }
                return html`<td key=${c} title=${title}>${display}</td>`;
              })}
            </tr>
          `
        )}
      </tbody>
    </table>
  `;
}

// ---------------------------------------------------------------------------
// View (toolbar + chart + sample)
// ---------------------------------------------------------------------------

function View({
  schema,
  summary,
  groupBy,
  setGroupBy,
  filters,
  setFilters,
  labels,
  requestLabels,
}) {
  const groupByOptions = useMemo(
    () =>
      schema.columns.filter(
        (c) =>
          (c.category === "categorical" || c.category === "boolean") &&
          !c.synthetic
      ),
    [schema]
  );

  const groupByCol = useMemo(
    () => schema.columns.find((c) => c.name === groupBy) || null,
    [schema, groupBy]
  );

  const onBarClick = useCallback(
    (idx) => {
      if (!summary || !summary.chart[idx]) return;
      const value = summary.chart[idx].value;
      const col = groupBy;
      const f = { ...filters };
      const cur = f[col]?.values ?? [];
      const exists = cur.some((x) => x === value);
      const next = exists
        ? cur.filter((x) => x !== value)
        : [...cur, value];
      if (next.length === 0) delete f[col];
      else f[col] = { kind: "in", values: next };
      setFilters(f);
    },
    [summary, groupBy, filters, setFilters]
  );

  return html`
    <section id="view">
      <div class="toolbar">
        <label>
          Group by
          <select
            value=${groupBy ?? ""}
            onChange=${(e) => setGroupBy(e.target.value)}
          >
            ${groupByOptions.map(
              (c) => html`<option key=${c.name} value=${c.name}>${c.name}</option>`
            )}
          </select>
        </label>
      </div>
      <${ChartView}
        summary=${summary}
        groupBy=${groupBy}
        lowCardinality=${!!groupByCol?.low_cardinality}
        labels=${labels}
        onBarClick=${onBarClick}
      />
      <${SampleTable}
        filters=${filters}
        labels=${labels}
        requestLabels=${requestLabels}
      />
    </section>
  `;
}

// ---------------------------------------------------------------------------
// App root
// ---------------------------------------------------------------------------

function App() {
  const [schema, setSchema] = useState(null);
  const [schemaError, setSchemaError] = useState(null);
  const [filters, setFilters] = useState({});
  const [groupBy, setGroupBy] = useState(null);
  const [summary, setSummary] = useState(null);
  const [labels, requestLabels] = useLabelFetcher();
  const inflight = useInflight();

  // Load schema once.
  useEffect(() => {
    let alive = true;
    api("/api/schema")
      .then((s) => {
        if (!alive) return;
        setSchema(s);
        const first = s.columns.find(
          (c) => c.category === "categorical" || c.category === "boolean"
        );
        if (first) setGroupBy(first.name);
      })
      .catch((e) => {
        if (alive) setSchemaError(e.message);
      });
    return () => {
      alive = false;
    };
  }, []);

  // Fetch summary when filters or groupBy change.
  useEffect(() => {
    if (!groupBy) return;
    const ctrl = new AbortController();
    api(
      "/api/summary",
      { filters, group_by: groupBy },
      ctrl.signal
    )
      .then((s) => setSummary(s))
      .catch((e) => {
        if (e.name !== "AbortError") console.error("summary failed", e);
      });
    return () => ctrl.abort();
  }, [filters, groupBy]);

  // Lazy-resolve labels for chart bars.
  useEffect(() => {
    if (summary?.chart) requestLabels(summary.chart.map((r) => r.value));
  }, [summary, requestLabels]);

  if (schemaError) {
    return html`<div class="error">Startup failed: ${schemaError}</div>`;
  }
  if (!schema) {
    return html`
      <div class="loading">
        <div class="loading-box">
          <div class="spinner"></div>
          <div>Connecting to server…</div>
          <div class="sub">
            Queries run server-side against DuckDB over the local Parquet file.
          </div>
        </div>
      </div>
    `;
  }

  const loading = inflight > 0;
  return html`
    <div class="app ${loading ? "app-loading" : ""}">
      <header>
        <div class="title">Europeana Data Explorer</div>
        <${Cards} total=${schema.total} summary=${summary} />
      </header>
      <main aria-busy=${loading ? "true" : "false"}>
        <${FacetSidebar}
          schema=${schema}
          filters=${filters}
          setFilters=${setFilters}
          labels=${labels}
          requestLabels=${requestLabels}
        />
        <${View}
          schema=${schema}
          summary=${summary}
          groupBy=${groupBy}
          setGroupBy=${setGroupBy}
          filters=${filters}
          setFilters=${setFilters}
          labels=${labels}
          requestLabels=${requestLabels}
        />
      </main>
      ${loading
        ? html`<div class="app-loading-overlay" role="status" aria-label="Loading">
            <div class="spinner-large"></div>
          </div>`
        : null}
    </div>
  `;
}

render(html`<${App} />`, document.getElementById("app"));

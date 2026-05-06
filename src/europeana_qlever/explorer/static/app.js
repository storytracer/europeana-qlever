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

async function api(path, body, signal) {
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
  return res.json();
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
    if (data) requestLabels(data.rows.map((r) => r.value));
  }, [data, requestLabels]);

  const selected = new Set(filters[col.name]?.values ?? []);

  const matches = (q, row) => {
    if (!q) return true;
    const v = String(row.value ?? "").toLowerCase();
    const lab = (labels[row.value] || "").toLowerCase();
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
              const lab = labels[r.value] || "";
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

function BooleanFacet({ col, filters, setFilters }) {
  const active = filters[col.name];
  const cls = (kind) => {
    if (kind === "any") return !active ? "active" : "";
    if (kind === "true") return active && active.value === true ? "active" : "";
    return active && active.value === false ? "active" : "";
  };
  function set(kind) {
    const f = { ...filters };
    if (kind === "any") delete f[col.name];
    else f[col.name] = { kind: "bool", value: kind === "true" };
    setFilters(f);
  }
  return html`
    <div class="facet">
      <h4>${col.name}</h4>
      <div class="toggle">
        <button class=${cls("any")} onClick=${() => set("any")}>Any</button>
        <button class=${cls("true")} onClick=${() => set("true")}>True</button>
        <button class=${cls("false")} onClick=${() => set("false")}>False</button>
      </div>
    </div>
  `;
}

function NumericFacet({ col, filters, setFilters }) {
  const active = filters[col.name];
  const [lo, setLo] = useState(active?.min ?? col.min ?? 0);
  const [hi, setHi] = useState(active?.max ?? col.max ?? 0);

  // Reset local inputs when the filter is cleared from outside.
  useEffect(() => {
    if (!active) {
      setLo(col.min ?? 0);
      setHi(col.max ?? 0);
    }
  }, [active, col.min, col.max]);

  function commit() {
    const min = lo === "" ? null : Number(lo);
    const max = hi === "" ? null : Number(hi);
    const f = { ...filters };
    if (min == null && max == null) delete f[col.name];
    else f[col.name] = { kind: "range", min, max };
    setFilters(f);
  }

  return html`
    <div class="facet">
      <h4>${col.name}</h4>
      <div class="range">
        <span class="muted">min</span>
        <input
          type="number"
          class="min"
          value=${lo}
          onInput=${(e) => setLo(e.target.value)}
          onChange=${commit}
        />
        <span class="muted">max</span>
        <input
          type="number"
          class="max"
          value=${hi}
          onInput=${(e) => setHi(e.target.value)}
          onChange=${commit}
        />
      </div>
      <div class="muted" style="margin-top:4px">
        Data range ${fmtN(col.min)}–${fmtN(col.max)}
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
          if (col.category === "categorical") {
            return html`<${CategoricalFacet}
              key=${col.name}
              col=${col}
              filters=${filters}
              setFilters=${setFilters}
              labels=${labels}
              requestLabels=${requestLabels}
            />`;
          }
          if (col.category === "boolean") {
            return html`<${BooleanFacet}
              key=${col.name}
              col=${col}
              filters=${filters}
              setFilters=${setFilters}
            />`;
          }
          if (col.category === "numeric") {
            return html`<${NumericFacet}
              key=${col.name}
              col=${col}
              filters=${filters}
              setFilters=${setFilters}
            />`;
          }
          return null;
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
      const colDef = schema.columns.find((c) => c.name === col);
      const f = { ...filters };
      if (colDef?.category === "boolean") {
        f[col] = { kind: "bool", value: !!value };
      } else {
        const cur = f[col]?.values ?? [];
        const exists = cur.some((x) => x === value);
        const next = exists
          ? cur.filter((x) => x !== value)
          : [...cur, value];
        if (next.length === 0) delete f[col];
        else f[col] = { kind: "in", values: next };
      }
      setFilters(f);
    },
    [summary, groupBy, filters, schema, setFilters]
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

  return html`
    <header>
      <div class="title">Europeana Data Explorer</div>
      <${Cards} total=${schema.total} summary=${summary} />
    </header>
    <main>
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
  `;
}

render(html`<${App} />`, document.getElementById("app"));

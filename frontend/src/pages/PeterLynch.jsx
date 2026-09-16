// src/pages/PeterLynch.jsx — Page: DR GILL · PETER LYNCH 100-POINT SYSTEM
//
// LAYER 1 — MACHINE FILTER   : the Screener.in queries (Elite / Lynch Hybrid) → candidate pool
// LAYER 2 — 100-POINT RANKING: Growth /40 · Valuation /20 · Quality /20 · Lynch Story /20
// LAYER 3 — HUMAN RESEARCH   : read the annual report and override the Story bucket by hand
//
// The ranking pool is the GURJAS 1 + GURJAS 2 result set of the last scan. Layer-1 filters are
// re-applied in the browser on top of it, so you can flip between Elite / Hybrid / Everything
// without running a new scan.
import { Fragment, useEffect, useMemo, useState } from 'react';
import { getGurjas1, getGurjas2, getScanStatus, triggerScan } from '../api';
import {
  SCREEN_DEFS, GRADE_BANDS, GROWTH_TESTS, PEG_BANDS, STORY_ITEMS,
  scoreLynch, applyScreen, stockSymbol, toCsv, topFiveText,
} from '../lynch';

const STORE_KEY = 'lynch_story_overrides_v1';
const QUESTIONS = [
  'What does the company actually sell?',
  'Why are sales growing?',
  'Why are profits growing faster/slower than sales?',
  'Is the growth sustainable?',
  'Is there a moat?',
  'Is debt increasing?',
  'Is cash flow genuine?',
  'Is management trustworthy?',
  'Is the industry cyclical?',
  'Why is the market giving me this stock at this valuation?',
];

function loadOverrides() {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch { return {}; }
}

function CopyBtn({ text, label = 'Copy', className = 'btn btn-sm btn-outline' }) {
  const [done, setDone] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = text; document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); } catch { /* ignore */ }
      document.body.removeChild(ta);
    }
    setDone(true);
    setTimeout(() => setDone(false), 1800);
  }
  return <button className={className} onClick={copy}>{done ? '✓ Copied' : label}</button>;
}

function ScoreBar({ value, max, tone }) {
  const pct = max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
  return (
    <div className="lynch-bar" title={`${value} / ${max}`}>
      <div className={`lynch-bar-fill ${tone || ''}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

const srcTag = (s) => (s === 'exact' ? null : (
  <span className={s === 'estimate' ? 'tag tag-est' : 'tag tag-unknown'}>
    {s === 'estimate' ? 'est' : 'n/a'}
  </span>
));

export default function PeterLynch() {
  // Deep links: /peter-lynch?screen=elite&stock=DIXON opens straight onto one score card.
  const params = new URLSearchParams(window.location.search);
  const startScreen = params.get('screen');
  const [pool, setPool]             = useState([]);
  const [scanStatus, setScanStatus] = useState(null);
  const [loading, setLoading]       = useState(true);
  const [scanning, setScanning]     = useState(false);
  const [error, setError]           = useState('');
  const [mode, setMode]             = useState(SCREEN_DEFS[startScreen] ? startScreen : 'hybrid');
  const [search, setSearch]         = useState('');
  const [minScore, setMinScore]     = useState('');
  const [topOnly, setTopOnly]       = useState(true);
  const [sortKey, setSortKey]       = useState('total');
  const [open, setOpen]             = useState(params.get('stock') || '');
  const [overrides, setOverrides]   = useState(loadOverrides);
  const [showRubric, setShowRubric] = useState(false);

  async function fetchData() {
    setLoading(true); setError('');
    try {
      // allSettled: if one screener list is unavailable the page still ranks the other one.
      const [r1, r2, s] = await Promise.allSettled([getGurjas1(), getGurjas2(), getScanStatus()]);
      const list = [];
      if (r2.status === 'fulfilled') list.push(...(r2.value.data.stocks || []));
      if (r1.status === 'fulfilled') list.push(...(r1.value.data.stocks || []));
      if (s.status === 'fulfilled') setScanStatus(s.value.data);

      const merged = new Map();
      for (const st of list) {
        const sym = stockSymbol(st);
        if (sym && !merged.has(sym)) merged.set(sym, st);
      }
      setPool([...merged.values()]);
      if (list.length === 0) {
        setError('No screener results available yet — run a scan (or press Refresh once the backend is awake).');
      }
    } catch {
      setError('Could not load screener results — the backend may be waking up. Try Refresh in a moment.');
    }
    setLoading(false);
  }

  useEffect(() => { fetchData(); }, []);

  useEffect(() => {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(overrides)); } catch { /* ignore */ }
  }, [overrides]);

  async function handleScan() {
    setScanning(true);
    try {
      await triggerScan(0);
      await new Promise((r) => setTimeout(r, 5000));
      await fetchData();
    } catch { setError('Scan trigger failed'); }
    setScanning(false);
  }

  // ── LAYER 1 + LAYER 2 ────────────────────────────────────────────────────
  const ranked = useMemo(() => {
    return pool
      .filter((st) => applyScreen(scoreLynch(st, overrides[stockSymbol(st)]).metrics, mode).pass)
      .map((st) => scoreLynch(st, overrides[stockSymbol(st)]))
      .sort((a, b) => b.total - a.total);
  }, [pool, mode, overrides]);

  const rows = useMemo(() => {
    let out = ranked.filter((r) => {
      const passSearch = !search
        || r.symbol.includes(search.toUpperCase())
        || (r.sector || '').toLowerCase().includes(search.toLowerCase())
        || (r.industry || '').toLowerCase().includes(search.toLowerCase());
      const passMin = minScore === '' || r.total >= parseFloat(minScore);
      return passSearch && passMin;
    });
    if (sortKey !== 'total') {
      const key = sortKey;
      out = [...out].sort((a, b) => {
        if (key === 'symbol') return a.symbol.localeCompare(b.symbol);
        if (key === 'peg') return (a.metrics.peg ?? 999) - (b.metrics.peg ?? 999);
        if (key === 'mcap') return (b.metrics.mcap ?? 0) - (a.metrics.mcap ?? 0);
        if (key === 'quality') return b.quality.points - a.quality.points || b.total - a.total;
        return b.total - a.total;
      });
    }
    return topOnly ? out.slice(0, 5) : out;
  }, [ranked, search, minScore, topOnly, sortKey]);

  const stats = useMemo(() => {
    const n = ranked.length;
    const avg = n ? ranked.reduce((s, r) => s + r.total, 0) / n : 0;
    return {
      count: n,
      top: n ? ranked[0].total : 0,
      avg: Math.round(avg * 10) / 10,
      aPlus: ranked.filter((r) => r.grade === 'A+' || r.grade === 'A').length,
      unverified: [...new Set(ranked.flatMap((r) => applyScreen(r.metrics, mode).unverified))],
    };
  }, [ranked, mode]);

  function setStory(symbol, itemKey, value) {
    setOverrides((prev) => {
      const next = { ...prev, [symbol]: { ...(prev[symbol] || {}) } };
      if (value === '' || value === null) delete next[symbol][itemKey];
      else next[symbol][itemKey] = Number(value);
      if (Object.keys(next[symbol]).length === 0) delete next[symbol];
      return next;
    });
  }

  function resetStory(symbol) {
    setOverrides((prev) => { const next = { ...prev }; delete next[symbol]; return next; });
  }

  function downloadCsv() {
    const blob = new Blob([toCsv(rows)], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `lynch-100-score-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const screen = SCREEN_DEFS[mode];

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title-glow">🏆 Peter Lynch — 100-Point System</h1>
          <div className="page-subtitle">
            Screener → 100-point score → Top 5 → deep research · Growth /40 · Valuation /20 · Quality /20 · Lynch Story /20
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          {scanStatus?.scan_running && (
            <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--blue)' }}>
              <span className="spinner" style={{ width: 14, height: 14 }} /> Scan running...
            </span>
          )}
          <button className="btn btn-outline" onClick={fetchData} disabled={loading}>↻ Refresh</button>
          <button className="btn btn-primary" onClick={handleScan} disabled={scanning || scanStatus?.scan_running}>
            {scanning ? 'Starting...' : '▶ Run Scan'}
          </button>
        </div>
      </div>

      <div className="page-body">
        {error && (
          <div className="scan-banner warning">
            ⚠️ {error}
            <button className="btn btn-sm btn-outline" onClick={() => setError('')}>✕</button>
          </div>
        )}

        {/* ── THREE LAYERS ───────────────────────────────────────────── */}
        <div className="metrics-grid" style={{ marginBottom: 20 }}>
          <div className="metric-card blue">
            <div className="metric-label">Layer 1 — Machine Filter</div>
            <div className="metric-value">{pool.length}</div>
            <div className="metric-sub">GURJAS results in the pool · {stats.count} pass “{screen.name}”</div>
          </div>
          <div className="metric-card gold">
            <div className="metric-label">Layer 2 — Top Score</div>
            <div className="metric-value">{stats.top}<span style={{ fontSize: 16, color: 'var(--text-muted)' }}>/100</span></div>
            <div className="metric-sub">Average {stats.avg}/100 · {stats.aPlus} graded A / A+</div>
          </div>
          <div className="metric-card green">
            <div className="metric-label">Layer 3 — Deep Research</div>
            <div className="metric-value">Top 5</div>
            <div className="metric-sub">Only after the questions below are answered</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Last Scan</div>
            <div className="metric-value" style={{ fontSize: 18 }}>
              {scanStatus?.last_scan_time ? new Date(scanStatus.last_scan_time).toLocaleDateString('en-IN') : '—'}
            </div>
            <div className="metric-sub">
              {scanStatus?.total_stocks ? `${scanStatus.total_stocks.toLocaleString('en-IN')} stocks analysed` : 'No scan yet'}
            </div>
          </div>
        </div>

        {/* ── LAYER 1 QUERIES ────────────────────────────────────────── */}
        <div className="grid-2" style={{ marginBottom: 20 }}>
          {['elite', 'hybrid'].map((id) => {
            const s = SCREEN_DEFS[id];
            const count = pool.filter((st) => applyScreen(scoreLynch(st, overrides[stockSymbol(st)]).metrics, id).pass).length;
            return (
              <div className="card" key={id}>
                <div className="lynch-card-head">
                  <div className="card-title" style={{ margin: 0 }}>{s.icon} {s.name}</div>
                  <span className={`badge ${id === 'elite' ? 'badge-red' : 'badge-gold'}`}>{count} stocks</span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 10 }}>{s.blurb}</div>
                <pre className="lynch-query">{s.query}</pre>
                <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                  <CopyBtn text={s.query} label="Copy query" />
                  <a className="btn btn-sm btn-outline" href="https://www.screener.in/screens/new/" target="_blank" rel="noreferrer">
                    Open Screener.in ↗
                  </a>
                  <button className="btn btn-sm btn-primary" onClick={() => { setMode(id); setTopOnly(true); }}>
                    {mode === id ? '✓ Active' : 'Use this pool'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        <div className="scan-banner" style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 11.5, color: 'var(--text-secondary)' }}>
            <strong style={{ color: 'var(--gold)' }}>Note on the queries:</strong> Screener.in has no
            “TTM Result Date” field — for current growth use <code>Profit growth &gt; 20</code> and
            <code> YOY Quarterly profit growth &gt; 20</code> (both are in the queries above).
            The two baskets: <strong>🔥 Elite</strong> finds exceptional bargains (&gt;20% / PEG &lt;0.6),
            <strong> ⭐ Lynch Hybrid</strong> gives the wider opportunity set (&gt;15% / PEG &lt;1).
            Strict is for conviction, Hybrid is for ranking.
          </div>
        </div>

        <div className="card" style={{ marginBottom: 20 }}>
          <div className="lynch-card-head">
            <div className="card-title" style={{ margin: 0 }}>Candidate pool</div>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {pool.length} stocks from the last scan · {stats.count} pass the current screen
            </span>
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
            {Object.values(SCREEN_DEFS).map((s) => (
              <button
                key={s.id}
                className={`lynch-chip${mode === s.id ? ' active' : ''}`}
                onClick={() => setMode(s.id)}
              >
                {s.icon} {s.name}
              </button>
            ))}
            <span style={{ flex: 1 }} />
            <input className="input" style={{ maxWidth: 220 }} placeholder="Search symbol / sector..."
              value={search} onChange={(e) => setSearch(e.target.value)} />
            <input className="input" style={{ maxWidth: 140 }} type="number" placeholder="Min score"
              value={minScore} onChange={(e) => setMinScore(e.target.value)} />
            <select className="input" style={{ maxWidth: 170 }} value={sortKey} onChange={(e) => setSortKey(e.target.value)}>
              <option value="total">Sort: Total score</option>
              <option value="quality">Sort: Quality /20</option>
              <option value="peg">Sort: Lowest PEG</option>
              <option value="mcap">Sort: Market cap</option>
              <option value="symbol">Sort: Symbol A–Z</option>
            </select>
            <button className={`btn btn-sm ${topOnly ? 'btn-primary' : 'btn-outline'}`} onClick={() => setTopOnly((v) => !v)}>
              {topOnly ? '✓ Top 5 only' : 'Show all'}
            </button>
          </div>
          {stats.count === 0 && !loading && (
            <div className="scan-banner warning" style={{ marginTop: 12 }}>
              No stock in the pool passes <strong>{screen.name}</strong> right now — switch to{' '}
              <em>Everything scanned</em> to see the full ranking, or run a fresh scan.
            </div>
          )}
          {stats.unverified.length > 0 && (
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 10 }}>
              ⚠️ Not verifiable from scan data (kept, not failed): {stats.unverified.join(' · ')} — confirm on Screener.in.
            </div>
          )}
        </div>

        {/* ── LAYER 2 : RANKING TABLE ───────────────────────────────── */}
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="lynch-card-head">
            <div className="card-title" style={{ margin: 0 }}>🏆 100-point ranking — {rows.length} shown</div>
            <div style={{ display: 'flex', gap: 8 }}>
              <CopyBtn text={topFiveText(rows, 5)} label="Copy Top 5" />
              <button className="btn btn-sm btn-outline" onClick={downloadCsv}>⬇ CSV</button>
            </div>
          </div>

          {loading ? (
            <div className="loading-state"><span className="spinner" /><span>Loading candidates...</span></div>
          ) : rows.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">🏆</div>
              <p>Nothing to rank yet. Run a scan, or relax the Layer-1 pool.</p>
            </div>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Stock</th>
                    <th>Growth /40</th>
                    <th>Valuation /20</th>
                    <th>Quality /20</th>
                    <th>Story /20</th>
                    <th>TOTAL /100</th>
                    <th>Grade</th>
                    <th>Decision</th>
                    <th>PEG</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => {
                    const isOpen = open === r.symbol;
                    return (
                      <Fragment key={r.symbol}>
                        <tr className={i < 3 && !search && !minScore ? 'lynch-medal' : ''}>
                          <td style={{ color: 'var(--text-muted)', fontSize: 11 }}>{i + 1}</td>
                          <td>
                            <div style={{ fontWeight: 600 }}>{r.symbol} {r.storyOverridden && <span className="tag tag-manual">manual story</span>}</div>
                            <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{r.sector} · {r.industry}</div>
                          </td>
                          <td><div className="lynch-cell"><span>{r.growth.points}</span><ScoreBar value={r.growth.points} max={40} tone="blue" /></div></td>
                          <td><div className="lynch-cell"><span>{r.valuation.points}</span><ScoreBar value={r.valuation.points} max={20} tone="gold" /></div></td>
                          <td><div className="lynch-cell"><span>{r.quality.points}</span><ScoreBar value={r.quality.points} max={20} tone="green" /></div></td>
                          <td><div className="lynch-cell"><span>{r.story.points}</span><ScoreBar value={r.story.points} max={20} tone="orange" /></div></td>
                          <td>
                            <span className={`lynch-total ${r.tone}`}>{r.total}</span>
                            {r.warnings.length > 0 && <span title={r.warnings.join(' · ')} style={{ marginLeft: 6, cursor: 'help' }}>⚠️</span>}
                          </td>
                          <td><span className={`lynch-grade ${r.tone}`}>{r.grade}</span></td>
                          <td style={{ fontSize: 12 }}>{r.decision}</td>
                          <td>{r.metrics.peg === null ? '—' : <span className={`badge ${r.metrics.peg < 1 ? 'badge-green' : 'badge-orange'}`}>{r.metrics.peg.toFixed(2)}</span>}</td>
                          <td>
                            <button className="btn btn-sm btn-outline" onClick={() => setOpen(isOpen ? '' : r.symbol)}>
                              {isOpen ? '▲ Hide' : '▼ Score'}
                            </button>
                          </td>
                        </tr>
                        {isOpen && (
                          <tr key={`${r.symbol}-detail`}>
                            <td colSpan={11} style={{ background: 'var(--bg-secondary)' }}>
                              <ScoreDetail
                                row={r}
                                mode={mode}
                                override={overrides[r.symbol] || {}}
                                onStory={setStory}
                                onReset={resetStory}
                              />
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* ── RUBRIC + QUESTIONS ────────────────────────────────────── */}
        <div className="grid-2">
          <div className="card">
            <div className="lynch-card-head">
              <div className="card-title" style={{ margin: 0 }}>📊 The scoring table</div>
              <button className="btn btn-sm btn-outline" onClick={() => setShowRubric((v) => !v)}>
                {showRubric ? 'Hide' : 'Show'}
              </button>
            </div>
            {showRubric ? (
              <div className="lynch-rubric">
                <div className="lynch-rubric-head">GROWTH — 40 marks</div>
                {GROWTH_TESTS.map((t) => (
                  <div className="lynch-rubric-row" key={t.key}><span>{t.label}</span><b>{t.max}</b></div>
                ))}
                <div className="lynch-rubric-head">VALUATION — 20 marks (PEG ladder)</div>
                {PEG_BANDS.map((b) => (
                  <div className="lynch-rubric-row" key={b.label}><span>{b.label}</span><b>{b.points}</b></div>
                ))}
                <div className="lynch-rubric-head">QUALITY — 20 marks</div>
                {[['ROCE > 20%', 5], ['ROE > 20%', 4], ['Positive / healthy cash flow', 4], ['CFO reasonably tracks PAT', 3], ['Debt/Equity < 0.5', 2], ['Promoter pledge = 0', 2]].map(([l, p]) => (
                  <div className="lynch-rubric-row" key={l}><span>{l}</span><b>{p}</b></div>
                ))}
                <div className="lynch-rubric-head">LYNCH STORY — 20 marks</div>
                {STORY_ITEMS.map((t) => (
                  <div className="lynch-rubric-row" key={t.key}><span>{t.label}</span><b>{t.max}</b></div>
                ))}
                <div className="lynch-rubric-head">GRADE</div>
                {GRADE_BANDS.map((b, i) => (
                  <div className="lynch-rubric-row" key={b.grade}>
                    <span>{i === 0 ? '90–100' : i === 1 ? '80–89' : i === 2 ? '70–79' : i === 3 ? '60–69' : 'below 60'}</span>
                    <b>{b.grade} · {b.decision}</b>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                Growth 40 · Valuation 20 · Quality 20 · Story 20 = <strong style={{ color: 'var(--gold)' }}>100</strong>.
                Open the table to see every mark and how it is awarded.
              </div>
            )}
            <div className="lynch-legend">
              <span><span className="tag tag-est">est</span> derived from Market Cap ÷ PE and Reserves — verify on Screener.in</span>
              <span><span className="tag tag-unknown">n/a</span> not present in scan — scored 0, never invented</span>
              <span><span className="tag tag-manual">manual</span> your own Layer-3 judgement, saved in this browser</span>
            </div>
          </div>

          <div className="card">
            <div className="card-title">🔎 Layer 3 — ask these 10 questions</div>
            <ol style={{ paddingLeft: 18, fontSize: 12.5, lineHeight: 1.9, color: 'var(--text-secondary)' }}>
              {QUESTIONS.map((q) => <li key={q}>{q}</li>)}
            </ol>
            <div className="scan-banner" style={{ marginTop: 8 }}>
              <div style={{ fontSize: 11.5, color: 'var(--text-secondary)' }}>
                Nothing enters the portfolio from this page. Layer 2 tells you <em>where to spend research time</em> —
                the last question (“why is the market giving me this stock at this valuation?”) is the one that
                decides whether the score is an opportunity or a warning.
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

// ── Per-stock score card + Story overrides (Layer 3) ────────────────────────
function ScoreDetail({ row, mode, override, onStory, onReset }) {
  const m = row.metrics;
  const screen = applyScreen(m, mode);
  const groups = [
    { key: 'growth', title: 'Growth', max: 40, data: row.growth },
    { key: 'valuation', title: 'Valuation', max: 20, data: row.valuation },
    { key: 'quality', title: 'Quality', max: 20, data: row.quality },
    { key: 'story', title: 'Lynch Story', max: 20, data: row.story },
  ];
  const fmt = (v, suffix = '%') => (v === null || v === undefined ? '—' : `${v}${suffix}`);

  return (
    <div className="lynch-detail">
      <div className="lynch-detail-facts">
        <span>Sales 3Y <b>{fmt(m.sales3y)}</b></span>
        <span>Sales 5Y <b>{fmt(m.sales5y)}</b></span>
        <span>Profit 3Y <b>{fmt(m.profit3y)}</b></span>
        <span>Profit 5Y <b>{fmt(m.profit5y)}</b></span>
        <span>Latest sales <b>{fmt(m.salesGrowth)}</b></span>
        <span>Latest profit <b>{fmt(m.profitGrowth)}</b></span>
        <span>PEG <b>{fmt(m.peg, '')}</b></span>
        <span>PE <b>{fmt(m.pe, '')}</b></span>
        <span>MCap <b>{m.mcap === null ? '—' : `₹${m.mcap.toLocaleString('en-IN')}Cr`}</b></span>
        <span>ROCE <b>{fmt(m.roce)}</b> {srcTag(m.source.roce)}</span>
        <span>ROE <b>{fmt(m.roe)}</b> {srcTag(m.source.roe)}</span>
        <span>Debt/Equity <b>{m.deRatio === null ? '—' : m.deRatio.toFixed(2)}</b></span>
        <span>Promoter <b>{fmt(m.promoter)}</b></span>
        <span>Pledge <b>{m.pledged === null ? 'not in scan' : `${m.pledged}%`}</b> {srcTag(m.source.pledge)}</span>
      </div>

      <div className="lynch-detail-grid">
        {groups.map((g) => (
          <div key={g.key} className="lynch-detail-col">
            <div className="lynch-detail-title">{g.title} <span>{g.data.points}/{g.max}</span></div>
            {g.data.items.map((it) => (
              <div className="lynch-test" key={it.key}>
                <span className={`lynch-dot ${it.status}`} />
                <span className="lynch-test-label">
                  {it.label}
                  {it.valueText && <em> · {it.valueText}</em>}
                </span>
                <b>{it.points}</b>
                {it.note && it.status !== 'manual' && <div className="lynch-note">{it.note}</div>}
              </div>
            ))}
            {g.key === 'story' && (
              <div className="lynch-override">
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>
                  Auto-proxy filled this bucket. Your own Layer-3 judgement overrides it:
                </div>
                <div className="lynch-override-grid">
                  {STORY_ITEMS.map((t) => (
                    <label key={t.key}>
                      <span>{t.label}</span>
                      <input
                        className="input"
                        type="number" min="0" max={t.max} step="0.5"
                        value={override[t.key] !== undefined ? override[t.key] : ''}
                        placeholder={String(row.story.auto[t.key])}
                        onChange={(e) => onStory(row.symbol, t.key, e.target.value)}
                      />
                    </label>
                  ))}
                </div>
                <button className="btn btn-sm btn-outline" style={{ marginTop: 8 }} onClick={() => onReset(row.symbol)}>
                  ↺ Reset to auto
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="lynch-detail-foot">
        <div style={{ fontSize: 11.5, color: 'var(--text-secondary)' }}>
          <strong style={{ color: 'var(--gold)' }}>Layer-1 check:</strong>{' '}
          {screen.pass ? '✅ passes the filter' : `❌ fails — ${(screen.failed || []).slice(0, 4).join(' · ')}`}
          {screen.unverified.length > 0 && ` · unverified: ${screen.unverified.join(' · ')}`}
        </div>
        {row.warnings.length > 0 && (
          <div style={{ fontSize: 11.5, color: 'var(--orange)', marginTop: 4 }}>
            ⚠️ {row.warnings.join(' · ')}
          </div>
        )}
        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          <a className="btn btn-sm btn-outline" target="_blank" rel="noreferrer"
            href={`https://www.screener.in/company/${row.symbol}/consolidated/`}>Screener.in ↗</a>
          <a className="btn btn-sm btn-outline" target="_blank" rel="noreferrer"
            href={`https://www.google.com/search?q=${encodeURIComponent(row.symbol + ' annual report investor presentation')}`}>
            Annual report ↗
          </a>
          <CopyBtn text={topFiveText([row], 1)} label="Copy score card" />
        </div>
      </div>
    </div>
  );
}

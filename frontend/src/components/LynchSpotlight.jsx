// src/components/LynchSpotlight.jsx — the Peter Lynch Top 5, ON the front page.
//
// Why: the 100-point system is the page that answers "what do I research next?", so the fund
// manager should not have to click away from the dashboard to see it. This card ranks the same
// GURJAS 1 + GURJAS 2 pool through the same engine (src/lynch.js) as the full page, so the Top 5
// here and the Top 5 there are the same five stocks with the same marks. It links through to
// /peter-lynch for the full ranking, the score cards and the NPA entry.
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { getGurjas1, getGurjas2, getScanStatus } from '../api';
import { SCREEN_DEFS, scoreLynch, applyScreen, dedupeBySymbol } from '../lynch';

const POOL = 'hybrid';

function TinyBar({ value, max, tone }) {
  const pct = max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
  return (
    <div className="lynch-bar" style={{ height: 4 }}>
      <div className={`lynch-bar-fill ${tone || ''}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

export default function LynchSpotlight() {
  const [pool, setPool] = useState([]);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    // allSettled: if one screener list is unavailable the card still ranks the other one.
    Promise.allSettled([getGurjas1(), getGurjas2(), getScanStatus()]).then(([r1, r2, s]) => {
      if (!alive) return;
      const list = [];
      if (r2.status === 'fulfilled') list.push(...(r2.value.data.stocks || []));
      if (r1.status === 'fulfilled') list.push(...(r1.value.data.stocks || []));
      if (s.status === 'fulfilled') setStatus(s.value.data);
      setPool(dedupeBySymbol(list));
      setLoading(false);
    }).catch(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  const { top, stats } = useMemo(() => {
    const ranked = pool
      .filter((st) => applyScreen(scoreLynch(st).metrics, POOL).pass)
      .map((st) => scoreLynch(st))
      .sort((a, b) => b.total - a.total);
    const lenders = ranked.filter((r) => r.metrics.isLender).length;
    return {
      top: ranked.slice(0, 5),
      stats: { count: ranked.length, lenders, topScore: ranked.length ? ranked[0].total : 0 },
    };
  }, [pool]);

  const screen = SCREEN_DEFS[POOL];

  return (
    <div className="card section" style={{ marginBottom: 20 }}>
      <div className="lynch-card-head">
        <div className="card-title" style={{ margin: 0 }}>🏆 Peter Lynch 100-Point — Top 5</div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            {stats.count} of {pool.length} pass {screen.icon} {screen.name}
            {stats.lenders > 0 && ` · ${stats.lenders} bank/NBFC`}
          </span>
          <Link className="btn btn-sm btn-primary" to="/peter-lynch">Open full ranking ↗</Link>
        </div>
      </div>

      {loading ? (
        <div className="loading-state"><span className="spinner" /><span>Scoring the universe…</span></div>
      ) : top.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">🏆</div>
          <p>
            No stock passes {screen.name} in the last scan. Open the page and switch the pool to
            “Everything scanned”, or run a fresh scan.
          </p>
        </div>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Stock</th>
                <th>MCap ₹Cr</th>
                <th>Grade</th>
                <th>TOTAL /100</th>
                <th>Growth /40</th>
                <th>Valuation /20</th>
                <th>Quality /20</th>
                <th>Story /20</th>
                {/* A lender is read on ROA, not ROCE — show the number that actually matters. */}
                <th>ROA %</th>
                <th>PEG</th>
                <th>Decision</th>
              </tr>
            </thead>
            <tbody>
              {top.map((r, i) => {
                const m = r.metrics;
                const ld = m.lender || {};
                return (
                  <tr key={r.symbol} className={i === 0 ? 'lynch-medal' : ''}>
                    <td style={{ color: 'var(--text-muted)', fontSize: 11 }}>{i + 1}</td>
                    <td>
                      <div style={{ fontWeight: 600 }}>
                        {r.symbol}
                        {m.isLender && <span className="tag tag-manual" style={{ marginLeft: 6 }}>🏦 {ld.kindLabel.split(' /')[0]}</span>}
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{r.sector} · {r.industry}</div>
                    </td>
                    <td>{m.mcap === null ? '—' : `₹${Math.round(m.mcap).toLocaleString('en-IN')}`}</td>
                    <td><span className={`lynch-grade ${r.tone}`}>{r.grade}</span></td>
                    <td><span className={`lynch-total ${r.tone}`}>{r.total}</span></td>
                    <td><div className="lynch-cell"><span>{r.growth.points}</span><TinyBar value={r.growth.points} max={40} tone="blue" /></div></td>
                    <td><div className="lynch-cell"><span>{r.valuation.points}</span><TinyBar value={r.valuation.points} max={20} tone="gold" /></div></td>
                    <td><div className="lynch-cell"><span>{r.quality.points}</span><TinyBar value={r.quality.points} max={20} tone="green" /></div></td>
                    <td><div className="lynch-cell"><span>{r.story.points}</span><TinyBar value={r.story.points} max={20} tone="orange" /></div></td>
                    <td>
                      {m.isLender && ld.roa !== null
                        ? <span className={`badge ${ld.roa > 1 ? 'badge-green' : 'badge-red'}`}>{ld.roa}%</span>
                        : m.roce !== null
                          ? <span className={`badge ${m.roce > 20 ? 'badge-green' : 'badge-orange'}`}>{m.roce}%</span>
                          : <span style={{ color: 'var(--text-muted)' }}>—</span>}
                    </td>
                    <td>{m.peg === null ? '—' : <span className={`badge ${m.peg < 1 ? 'badge-green' : 'badge-orange'}`}>{m.peg.toFixed(2)}</span>}</td>
                    <td style={{ fontSize: 12 }}>{r.decision}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div style={{ fontSize: 10.5, color: 'var(--text-muted)', marginTop: 8 }}>
            {status?.total_stocks
              ? `${status.total_stocks.toLocaleString('en-IN')} stocks in the last scan`
              : 'No scan yet'}
            {' · '}a bank or NBFC is judged on ROA and its capital cushion, never on Debt/Equity —
            borrowing is what a lender does for a living.
          </div>
        </div>
      )}
    </div>
  );
}

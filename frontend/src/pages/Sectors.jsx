// src/pages/Sectors.jsx — Page 5: Sectors & Industries
import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import api from '../api';

function getCol(s, keys) {
  for (const k of keys) if (s[k] !== undefined && s[k] !== null) return s[k];
  return null;
}

const COLORS = ['#00D4FF', '#FFD700', '#00E676', '#FF9F43', '#A29BFE', '#FF4757', '#FD79A8', '#74B9FF', '#55EFC4', '#FDCB6E'];

export default function Sectors() {
  const [stocks, setStocks]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [viewBy, setViewBy]   = useState('sector');
  const [selected, setSelected] = useState(null);
  const [error, setError]     = useState('');

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const [g1, g2] = await Promise.all([
          api.get('/api/scan/results/gurjas1'),
          api.get('/api/scan/results/gurjas2'),
        ]);
        const all = [...(g1.data.stocks || []), ...(g2.data.stocks || [])];
        // Deduplicate by symbol
        const seen = new Set();
        const deduped = all.filter(s => {
          const sym = s.symbol || s.ticker || s.Symbol || s.Ticker || '';
          if (!sym || seen.has(sym)) return false;
          seen.add(sym);
          return true;
        });
        setStocks(deduped);
      } catch {
        setError('Could not load sector data');
      }
      setLoading(false);
    }
    fetchData();
  }, []);

  // Group by sector or industry
  const grouped = {};
  stocks.forEach(s => {
    const key = getCol(s, viewBy === 'sector'
      ? ['sector', 'Sector', 'industry_sector']
      : ['industry', 'Industry', 'industry_name']
    ) || 'Other';

    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(s);
  });

  const chartData = Object.entries(grouped)
    .map(([name, items]) => ({
      name: name.length > 18 ? name.slice(0, 18) + '…' : name,
      fullName: name,
      count: items.length,
      avgStars: (items.reduce((s, x) => s + (parseInt(getCol(x, ['Grand Total Stars', 'total_stars', 'Stars (Total)'])) || 0), 0) / items.length).toFixed(1),
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 15);

  const selectedStocks = selected
    ? stocks.filter(s => {
        const key = getCol(s, viewBy === 'sector'
          ? ['sector', 'Sector', 'industry_sector']
          : ['industry', 'Industry', 'industry_name']
        ) || 'Other';
        return key === selected;
      })
    : [];

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title-glow">🏭 Sectors & Industries</h1>
          <div className="page-subtitle">Sector distribution of GURJAS 1+2 screener results</div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className={`btn btn-sm ${viewBy === 'sector' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => { setViewBy('sector'); setSelected(null); }}>By Sector</button>
          <button className={`btn btn-sm ${viewBy === 'industry' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => { setViewBy('industry'); setSelected(null); }}>By Industry</button>
        </div>
      </div>

      <div className="page-body">
        {error && <div className="scan-banner warning">⚠️ {error}</div>}

        <div className="metrics-grid" style={{ marginBottom: 24 }}>
          <div className="metric-card blue"><div className="metric-label">Total Stocks</div><div className="metric-value">{stocks.length}</div><div className="metric-sub">Across all sectors</div></div>
          <div className="metric-card gold"><div className="metric-label">Sectors</div><div className="metric-value">{Object.keys(grouped).length}</div><div className="metric-sub">Unique sectors</div></div>
          <div className="metric-card green"><div className="metric-label">Top Sector</div>
            <div className="metric-value" style={{ fontSize: 14 }}>{chartData[0]?.fullName?.slice(0, 12) || '—'}</div>
            <div className="metric-sub">{chartData[0]?.count || 0} stocks</div>
          </div>
        </div>

        {loading ? (
          <div className="loading-state"><span className="spinner" /><span>Loading sector data...</span></div>
        ) : (
          <div className="grid-2 section">
            {/* Bar Chart */}
            <div className="card">
              <div className="card-title">📊 {viewBy === 'sector' ? 'Sector' : 'Industry'} Distribution (click to drill down)</div>
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={chartData} layout="vertical" margin={{ left: 0, right: 20 }}
                  onClick={d => d?.activePayload?.[0] && setSelected(d.activePayload[0].payload.fullName)}>
                  <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" width={130} tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ background: '#0E1E3A', border: '1px solid rgba(0,212,255,0.2)', borderRadius: 8, fontSize: 12 }}
                    formatter={(v, n, p) => [`${v} stocks (avg ${p.payload.avgStars}⭐)`, 'Count']}
                  />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]} cursor="pointer">
                    {chartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Sector Detail or Summary Table */}
            <div className="card">
              {selected ? (
                <>
                  <div className="card-title" style={{ justifyContent: 'space-between' }}>
                    <span>🔎 {selected} ({selectedStocks.length} stocks)</span>
                    <button className="btn btn-sm btn-outline" onClick={() => setSelected(null)}>✕ Close</button>
                  </div>
                  <div className="table-wrapper">
                    <table>
                      <thead>
                        <tr>
                          <th>Symbol</th>
                          <th>Sales 3Y</th>
                          <th>Profit 3Y</th>
                          <th>PEG</th>
                          <th>Stars</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedStocks.map(s => {
                          const rawSym = getCol(s, ['symbol', 'ticker', 'Symbol', 'Ticker', 'symbol_name']) || '';
                          const sym = rawSym.replace('.NS', '');
                          const s3   = parseFloat(getCol(s, ['sales_cagr_3y', 'Sales CAGR 3Y']));
                          const p3   = parseFloat(getCol(s, ['profit_cagr_3y', 'Profit CAGR 3Y']));
                          const peg  = parseFloat(getCol(s, ['peg', 'PEG Ratio']));
                          const stars = parseInt(getCol(s, ['Grand Total Stars', 'grand_total_stars', 'total_stars', 'Stars (Total)'])) || 0;
                          return (
                            <tr key={sym}>
                              <td>{sym}</td>
                              <td className={!isNaN(s3) && s3 >= 20 ? 'positive' : 'neutral'}>{isNaN(s3) ? '—' : `${s3.toFixed(1)}%`}</td>
                              <td className={!isNaN(p3) && p3 >= 20 ? 'positive' : 'neutral'}>{isNaN(p3) ? '—' : `${p3.toFixed(1)}%`}</td>
                              <td>{isNaN(peg) ? '—' : <span className={`badge ${peg < 1.5 ? 'badge-green' : 'badge-red'}`}>{peg.toFixed(2)}</span>}</td>
                              <td className="stars">{'⭐'.repeat(Math.min(stars, 5))}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </>
              ) : (
                <>
                  <div className="card-title">📋 Summary Table</div>
                  <div className="table-wrapper">
                    <table>
                      <thead>
                        <tr>
                          <th>{viewBy === 'sector' ? 'Sector' : 'Industry'}</th>
                          <th>Stocks</th>
                          <th>Avg Stars</th>
                        </tr>
                      </thead>
                      <tbody>
                        {chartData.map((row, i) => (
                          <tr key={row.fullName} onClick={() => setSelected(row.fullName)} style={{ cursor: 'pointer' }}>
                            <td style={{ color: COLORS[i % COLORS.length] }}>{row.fullName}</td>
                            <td><span className="badge badge-blue">{row.count}</span></td>
                            <td className="stars">{'⭐'.repeat(Math.min(Math.round(parseFloat(row.avgStars)), 5))} {row.avgStars}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 10 }}>
                    👆 Click a row or bar to drill down into that sector
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </>
  );
}

// src/pages/Gurjas2.jsx — Page 3: GURJAS 2 Screener
// Query: Sales/Profit 3Y > 10% + Sales/Profit Overall > 20% + MCap > 1000Cr + PEG < 1.5
import { useState, useEffect } from 'react';
import { getGurjas2, getScanStatus, triggerScan } from '../api';

// ── Key mappings for each sortable column ───────────────────
const COL_KEYS = {
  symbol:           ['symbol', 'ticker', 'Symbol', 'Ticker', 'symbol_name'],
  sales_cagr_3y:    ['sales_cagr_3y', 'Sales CAGR 3Y', 'sales_3y'],
  sales_cagr_5y:    ['sales_cagr_5y', 'Sales CAGR 5Y', 'sales_5y'],
  sales_cagr_all:   ['sales_cagr_all', 'Sales CAGR', 'sales_all'],
  profit_cagr_3y:   ['profit_cagr_3y', 'Profit CAGR 3Y', 'profit_3y'],
  profit_cagr_all:  ['profit_cagr_all', 'Profit CAGR', 'profit_all'],
  peg:              ['peg', 'PEG Ratio', 'peg_ratio'],
  mcap:             ['mcap', 'MCap', 'market_cap', 'Market Cap (Cr)'],
  ltp:              ['ltp', 'LTP', 'current_price', 'Price'],
};

function getCol(s, keys) {
  for (const k of keys) if (s[k] !== undefined && s[k] !== null) return s[k];
  return null;
}

function getSortVal(s, sortKey) {
  if (sortKey === 'symbol') {
    const v = getCol(s, COL_KEYS.symbol) || '';
    return v.toUpperCase();
  }
  const keys = COL_KEYS[sortKey] || [sortKey];
  return parseFloat(getCol(s, keys)) || 0;
}

export default function Gurjas2() {
  const [stocks, setStocks]     = useState([]);
  const [loading, setLoading]   = useState(true);
  const [scanning, setScanning] = useState(false);
  const [scanStatus, setScanStatus] = useState(null);
  const [search, setSearch]     = useState('');
  const [sortKey, setSortKey]   = useState('');
  const [sortDir, setSortDir]   = useState('desc');
  const [minMcap, setMinMcap]   = useState('');
  const [error, setError]       = useState('');

  async function fetchData() {
    setLoading(true);
    try {
      const [r, s] = await Promise.all([getGurjas2(), getScanStatus()]);
      setStocks(r.data.stocks || []);
      setScanStatus(s.data);
    } catch { setError('Could not load GURJAS 2 data'); }
    setLoading(false);
  }

  useEffect(() => { fetchData(); }, []);

  async function handleScan() {
    setScanning(true);
    try {
      await triggerScan(0);
      await new Promise(r => setTimeout(r, 5000));
      await fetchData();
    } catch { setError('Scan trigger failed'); }
    setScanning(false);
  }

  function handleSort(key) {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('desc'); }
  }

  const filtered = stocks
    .filter(s => {
      const sym = getCol(s, COL_KEYS.symbol) || '';
      const mcap = parseFloat(getCol(s, COL_KEYS.mcap));
      const passSearch = sym.toUpperCase().includes(search.toUpperCase());
      const passMcap = minMcap ? (!isNaN(mcap) && mcap >= parseFloat(minMcap)) : true;
      return passSearch && passMcap;
    })
    .sort((a, b) => {
      if (!sortKey) return 0;
      const av = getSortVal(a, sortKey);
      const bv = getSortVal(b, sortKey);
      if (typeof av === 'string') {
        return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      return sortDir === 'asc' ? av - bv : bv - av;
    });

  const Th = ({ k, label }) => (
    <th onClick={() => handleSort(k)} style={{ cursor: 'pointer', userSelect: 'none' }}>
      {label} {sortKey === k ? (sortDir === 'asc' ? ' ↑' : ' ↓') : ' ↕'}
    </th>
  );

  // MCap distribution stats
  const largeCap  = stocks.filter(s => parseFloat(getCol(s, COL_KEYS.mcap)) >= 20000).length;
  const midCap    = stocks.filter(s => { const m = parseFloat(getCol(s, COL_KEYS.mcap)); return m >= 5000 && m < 20000; }).length;
  const smallCap  = stocks.filter(s => parseFloat(getCol(s, COL_KEYS.mcap)) < 5000).length;

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title-glow">🎯 GURJAS 2 Screener</h1>
          <div className="page-subtitle">
            Sales/Profit 3Y &gt; 10% · Overall &gt; 20% · MCap &gt; 1000Cr · PEG &lt; 1.5
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn btn-outline" onClick={fetchData} disabled={loading}>↻ Refresh</button>
          <button className="btn btn-primary" onClick={handleScan} disabled={scanning || scanStatus?.scan_running}>
            {scanning ? 'Starting...' : '▶ Run Scan'}
          </button>
        </div>
      </div>

      <div className="page-body">
        {error && (
          <div className="scan-banner warning">⚠️ {error}
            <button className="btn btn-sm btn-outline" onClick={() => setError('')}>✕</button>
          </div>
        )}

        {/* Scan Info Banner */}
        {scanStatus && (
          <div className="scan-banner" style={{ marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              <strong style={{ color: 'var(--gold)' }}>📡 Scan Status</strong>
              {' · '}
              <span>{scanStatus.total_stocks?.toLocaleString() || 0} stocks analysed</span>
              {scanStatus.scan_mode && <span> · Mode: {scanStatus.scan_mode}</span>}
              {scanStatus.last_scan_time && (
                <span> · Refresh: {new Date(scanStatus.last_scan_time).toLocaleString('en-IN')}</span>
              )}
              {scanStatus.scan_running && (
                <span style={{ color: 'var(--gold)', marginLeft: 8 }}>
                  <span className="spinner" style={{ width: 10, height: 10, display: 'inline-block' }} /> Scan running...
                </span>
              )}
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
              Data: yfinance + screener.in
            </div>
          </div>
        )}

        {/* Stats */}
        <div className="metrics-grid" style={{ marginBottom: 20 }}>
          <div className="metric-card blue">
            <div className="metric-label">Total Matches</div>
            <div className="metric-value">{stocks.length}</div>
            <div className="metric-sub">GURJAS 2 stocks</div>
          </div>
          <div className="metric-card gold">
            <div className="metric-label">Large Cap</div>
            <div className="metric-value">{largeCap}</div>
            <div className="metric-sub">&gt; ₹20,000Cr</div>
          </div>
          <div className="metric-card green">
            <div className="metric-label">Mid Cap</div>
            <div className="metric-value">{midCap}</div>
            <div className="metric-sub">₹5,000–20,000Cr</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Small Cap</div>
            <div className="metric-value">{smallCap}</div>
            <div className="metric-sub">&lt; ₹5,000Cr</div>
          </div>
        </div>

        {/* Conditions */}
        <div className="scan-banner" style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
            <strong style={{ color: 'var(--gold)' }}>GURJAS 2 Conditions:</strong>
            {' '}Sales 3Y/5Y &gt; 10% · Sales Overall &gt; 20% · Profit 3Y &gt; 10% · Profit Overall &gt; 20% · MCap &gt; 1000Cr · PEG &lt; 1.5
          </div>
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
          <input className="input" style={{ maxWidth: 220 }} placeholder="Search symbol..."
            value={search} onChange={e => setSearch(e.target.value)} />
          <input className="input" style={{ maxWidth: 180 }} placeholder="Min MCap (Cr)..."
            type="number" value={minMcap} onChange={e => setMinMcap(e.target.value)} />
        </div>

        {/* Table */}
        <div className="card">
          {loading ? (
            <div className="loading-state">
              <span className="spinner" />
              <span>Loading GURJAS 2 results...</span>
            </div>
          ) : filtered.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">🎯</div>
              <p>No results. Click "Run Scan" to get latest GURJAS 2 data.</p>
            </div>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <Th k="symbol" label="Symbol" />
                    <Th k="sales_cagr_3y" label="Sales 3Y %" />
                    <Th k="sales_cagr_5y" label="Sales 5Y %" />
                    <Th k="sales_cagr_all" label="Sales All %" />
                    <Th k="profit_cagr_3y" label="Profit 3Y %" />
                    <Th k="profit_cagr_all" label="Profit All %" />
                    <Th k="peg" label="PEG" />
                    <Th k="mcap" label="MCap Cr" />
                    <Th k="ltp" label="LTP ₹" />
                    <th>Stars ⭐</th>
                    <th>Above DMA?</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((s, i) => {
                    const rawSym = getCol(s, COL_KEYS.symbol) || '';
                    const sym = rawSym.replace('.NS', '');
                    const s3  = parseFloat(getCol(s, COL_KEYS.sales_cagr_3y));
                    const s5  = parseFloat(getCol(s, COL_KEYS.sales_cagr_5y));
                    const sa  = parseFloat(getCol(s, COL_KEYS.sales_cagr_all));
                    const p3  = parseFloat(getCol(s, COL_KEYS.profit_cagr_3y));
                    const pa  = parseFloat(getCol(s, COL_KEYS.profit_cagr_all));
                    const peg = parseFloat(getCol(s, COL_KEYS.peg));
                    const mc  = parseFloat(getCol(s, COL_KEYS.mcap));
                    const ltp = parseFloat(getCol(s, COL_KEYS.ltp));
                    const stars = parseInt(getCol(s, ['Grand Total Stars', 'grand_total_stars', 'total_stars', 'Stars (Total)'])) || 0;
                    const aboveDma = getCol(s, ['above_200dma', 'above_sma', 'price_above_dma', 'Is Above 200 SMA']);

                    const pct = v => isNaN(v) ? '—' : <span className={v >= 20 ? 'positive' : v >= 10 ? 'neutral' : ''}>{v.toFixed(1)}%</span>;

                    return (
                      <tr key={sym + i}>
                        <td style={{ color: 'var(--text-muted)', fontSize: 11 }}>{i + 1}</td>
                        <td>
                          <div>{sym}</div>
                          {getCol(s, ['sector', 'Sector']) && (
                            <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{getCol(s, ['sector', 'Sector'])}</div>
                          )}
                        </td>
                        <td>{pct(s3)}</td>
                        <td>{pct(s5)}</td>
                        <td>{pct(sa)}</td>
                        <td>{pct(p3)}</td>
                        <td>{pct(pa)}</td>
                        <td>
                          {!isNaN(peg) ? (
                            <span className={`badge ${peg < 1.5 ? 'badge-green' : 'badge-red'}`}>{peg.toFixed(2)}</span>
                          ) : '—'}
                        </td>
                        <td>
                          {!isNaN(mc) ? (
                            <span className={`badge ${mc >= 20000 ? 'badge-gold' : mc >= 5000 ? 'badge-blue' : 'badge-orange'}`}>
                              ₹{mc.toFixed(0)}Cr
                            </span>
                          ) : '—'}
                        </td>
                        <td>₹{isNaN(ltp) ? '—' : ltp.toLocaleString('en-IN')}</td>
                        <td className="stars">{'⭐'.repeat(Math.min(stars, 5))}{stars > 0 ? ` ${stars}` : '—'}</td>
                        <td>
                          {aboveDma !== null ? (
                            <span className={`badge ${aboveDma ? 'badge-green' : 'badge-red'}`}>
                              {aboveDma ? '✓ Yes' : '✗ No'}
                            </span>
                          ) : <span className="badge badge-blue">N/A</span>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

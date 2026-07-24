// src/pages/Momentum.jsx — Page 4: Momentum & Breakout
import { useState, useEffect } from 'react';
import { getScanStatus, triggerScan } from '../api';
import api from '../api';

export default function Momentum() {
  const [stocks, setStocks]     = useState([]);
  const [loading, setLoading]   = useState(true);
  const [scanning, setScanning] = useState(false);
  const [scanStatus, setScanStatus] = useState(null);
  const [filter, setFilter]     = useState('all');
  const [search, setSearch]     = useState('');
  const [sortKey, setSortKey]   = useState('momentum_score');
  const [sortDir, setSortDir]   = useState('desc');
  const [error, setError]       = useState('');

  async function fetchData() {
    setLoading(true);
    try {
      // Fetch all scan cache and filter for momentum stocks
      const s = await getScanStatus();
      setScanStatus(s.data);
      // Load raw scored results from gurjas endpoints and derive momentum
      const [g1, g2] = await Promise.all([
        api.get('/api/scan/results/gurjas1'),
        api.get('/api/scan/results/gurjas2'),
      ]);

      // Merge GURJAS 1 & 2 stocks — mark which screener they appear in
      const g1Map = {};
      (g1.data.stocks || []).forEach(s => {
        const sym = s.symbol || s.ticker || s.Symbol || s.Ticker || '';
        g1Map[sym] = { ...s, in_gurjas1: true };
      });

      const all = [...(g1.data.stocks || [])];
      (g2.data.stocks || []).forEach(s => {
        const sym = s.symbol || s.ticker || s.Symbol || s.Ticker || '';
        if (g1Map[sym]) g1Map[sym].in_gurjas2 = true;
        else all.push({ ...s, in_gurjas2: true });
      });

      // Tag gurjas2 on existing
      const merged = all.map(s => {
        const sym = s.symbol || s.ticker || s.Symbol || s.Ticker || '';
        return { ...s, in_gurjas1: !!g1Map[sym]?.in_gurjas1, in_gurjas2: !!g1Map[sym]?.in_gurjas2 };
      });

      setStocks(merged);
    } catch {
      setError('Could not load momentum data — backend may be starting up');
    }
    setLoading(false);
  }

  useEffect(() => { fetchData(); }, []);

  async function handleScan() {
    setScanning(true);
    try {
      await triggerScan(0);
      await new Promise(r => setTimeout(r, 5000));
      await fetchData();
    } catch { setError('Scan failed'); }
    setScanning(false);
  }

  function getCol(s, keys) {
    for (const k of keys) if (s[k] !== undefined && s[k] !== null) return s[k];
    return null;
  }

  function handleSort(key) {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('desc'); }
  }

  const filtered = stocks
    .filter(s => {
      const sym = (s.symbol || s.ticker || s.Symbol || s.Ticker || '').toUpperCase();
      const aboveDma = getCol(s, ['above_200dma', 'above_sma', 'price_above_dma', 'Is Above 200 SMA']);
      if (filter === 'above_dma' && !aboveDma) return false;
      if (filter === 'gurjas1' && !s.in_gurjas1) return false;
      if (filter === 'gurjas2' && !s.in_gurjas2) return false;
      if (filter === 'both' && (!s.in_gurjas1 || !s.in_gurjas2)) return false;
      return sym.includes(search.toUpperCase());
    })
    .sort((a, b) => {
      const getVal = (s) => {
        if (sortKey === 'momentum_score') {
          const stars = parseInt(getCol(s, ['Grand Total Stars', 'grand_total_stars', 'total_stars', 'Stars (Total)'])) || 0;
          const peg   = parseFloat(getCol(s, ['peg', 'PEG Ratio'])) || 99;
          return stars - peg;
        }
        return parseFloat(s[sortKey]) || 0;
      };
      const av = getVal(a), bv = getVal(b);
      return sortDir === 'asc' ? av - bv : bv - av;
    });

  const aboveDmaCount = stocks.filter(s => getCol(s, ['above_200dma', 'above_sma', 'price_above_dma', 'Is Above 200 SMA'])).length;
  const bothCount     = stocks.filter(s => s.in_gurjas1 && s.in_gurjas2).length;

  const Th = ({ k, label }) => (
    <th onClick={() => handleSort(k)} style={{ cursor: 'pointer', userSelect: 'none' }}>
      {label} {sortKey === k ? (sortDir === 'asc' ? '↑' : '↓') : ''}
    </th>
  );

  const FILTERS = [
    { k: 'all',       label: 'All Stocks' },
    { k: 'above_dma', label: 'Above 200 DMA' },
    { k: 'gurjas1',   label: 'GURJAS 1 Only' },
    { k: 'gurjas2',   label: 'GURJAS 2 Only' },
    { k: 'both',      label: 'In Both Screeners' },
  ];

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title-glow">⚡ Momentum & Breakout</h1>
          <div className="page-subtitle">Stocks above 200 DMA with strong growth — combined GURJAS view</div>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn btn-outline" onClick={fetchData} disabled={loading}>↻ Refresh</button>
          <button className="btn btn-primary" onClick={handleScan} disabled={scanning}>
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

        {/* Scan Info */}
        {scanStatus && (
          <div className="scan-banner" style={{ marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              <strong style={{ color: 'var(--blue)' }}>📡 Scan</strong>
              {' · '}
              <span>{scanStatus.total_stocks?.toLocaleString() || 0} stocks</span>
              {scanStatus.last_scan_time && (
                <span> · {new Date(scanStatus.last_scan_time).toLocaleString('en-IN')}</span>
              )}
              {scanStatus.scan_running && (
                <span style={{ color: 'var(--gold)', marginLeft: 8 }}>
                  <span className="spinner" style={{ width: 10, height: 10, display: 'inline-block' }} /> Running...
                </span>
              )}
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>yfinance + screener.in</div>
          </div>
        )}

        <div className="metrics-grid" style={{ marginBottom: 20 }}>
          <div className="metric-card gold"><div className="metric-label">Total Universe</div><div className="metric-value">{stocks.length}</div><div className="metric-sub">Across GURJAS 1+2</div></div>
          <div className="metric-card green"><div className="metric-label">Above 200 DMA</div><div className="metric-value">{aboveDmaCount}</div><div className="metric-sub">Uptrend confirmed</div></div>
          <div className="metric-card blue"><div className="metric-label">In Both Screeners</div><div className="metric-value">{bothCount}</div><div className="metric-sub">Strongest picks</div></div>
          <div className="metric-card"><div className="metric-label">Showing</div><div className="metric-value">{filtered.length}</div><div className="metric-sub">After filter</div></div>
        </div>

        {/* Filter chips */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
          {FILTERS.map(f => (
            <button key={f.k}
              className={`btn btn-sm ${filter === f.k ? 'btn-primary' : 'btn-outline'}`}
              onClick={() => setFilter(f.k)}>
              {f.label}
            </button>
          ))}
          <input className="input" style={{ maxWidth: 200 }} placeholder="Search..."
            value={search} onChange={e => setSearch(e.target.value)} />
        </div>

        <div className="card">
          {loading ? (
            <div className="loading-state"><span className="spinner" /><span>Loading momentum data...</span></div>
          ) : filtered.length === 0 ? (
            <div className="empty-state"><div className="empty-icon">⚡</div><p>No stocks match current filter. Try "All Stocks".</p></div>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <Th k="symbol" label="Symbol" />
                    <th>Screener</th>
                    <Th k="ltp" label="LTP ₹" />
                    <Th k="sma_200" label="200 DMA" />
                    <th>DMA Signal</th>
                    <Th k="sales_cagr_3y" label="Sales 3Y" />
                    <Th k="profit_cagr_3y" label="Profit 3Y" />
                    <Th k="peg" label="PEG" />
                    <th>Stars ⭐</th>
                    <Th k="mcap" label="MCap Cr" />
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((s, i) => {
                    const rawSym = getCol(s, ['symbol', 'ticker', 'Symbol', 'Ticker', 'symbol_name']) || '';
                    const sym = rawSym.replace('.NS', '');
                    const ltp = parseFloat(getCol(s, ['ltp', 'LTP', 'current_price', 'Price']));
                    const sma = parseFloat(getCol(s, ['sma_200', '200 DMA', 'sma200', '200 SMA']));
                    const s3  = parseFloat(getCol(s, ['sales_cagr_3y', 'Sales CAGR 3Y']));
                    const p3  = parseFloat(getCol(s, ['profit_cagr_3y', 'Profit CAGR 3Y']));
                    const peg = parseFloat(getCol(s, ['peg', 'PEG Ratio']));
                    const mc  = parseFloat(getCol(s, ['mcap', 'MCap', 'market_cap', 'Market Cap (Cr)']));
                    const aboveDma = getCol(s, ['above_200dma', 'above_sma', 'price_above_dma', 'Is Above 200 SMA']);
                    const stars = parseInt(getCol(s, ['Grand Total Stars', 'grand_total_stars', 'total_stars', 'Stars (Total)'])) || 0;

                    return (
                      <tr key={sym + i}>
                        <td style={{ color: 'var(--text-muted)', fontSize: 11 }}>{i + 1}</td>
                        <td>{sym}</td>
                        <td>
                          {s.in_gurjas1 && <span className="badge badge-blue" style={{ marginRight: 4 }}>G1</span>}
                          {s.in_gurjas2 && <span className="badge badge-gold">G2</span>}
                        </td>
                        <td>₹{isNaN(ltp) ? '—' : ltp.toLocaleString('en-IN')}</td>
                        <td>₹{isNaN(sma) ? '—' : sma.toFixed(0)}</td>
                        <td>
                          {aboveDma !== null ? (
                            <span className={`badge ${aboveDma ? 'badge-green' : 'badge-red'}`}>
                              {aboveDma ? '▲ Above' : '▼ Below'}
                            </span>
                          ) : <span className="badge badge-blue">—</span>}
                        </td>
                        <td className={!isNaN(s3) && s3 >= 20 ? 'positive' : 'neutral'}>{isNaN(s3) ? '—' : `${s3.toFixed(1)}%`}</td>
                        <td className={!isNaN(p3) && p3 >= 20 ? 'positive' : 'neutral'}>{isNaN(p3) ? '—' : `${p3.toFixed(1)}%`}</td>
                        <td>{isNaN(peg) ? '—' : <span className={`badge ${peg < 1.5 ? 'badge-green' : 'badge-red'}`}>{peg.toFixed(2)}</span>}</td>
                        <td className="stars">{'⭐'.repeat(Math.min(stars, 5))}</td>
                        <td style={{ fontSize: 11, color: 'var(--text-muted)' }}>{isNaN(mc) ? '—' : `₹${mc.toFixed(0)}Cr`}</td>
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

// src/pages/Gurjas1.jsx — Page 2: GURJAS 1 Screener
// Query: Sales/Profit 3Y+5Y+Overall > 20% + Price > 200 DMA + PEG < 1.2
import { useState, useEffect } from 'react';
import { getGurjas1, getScanStatus, triggerScan } from '../api';

export default function Gurjas1() {
  const [stocks, setStocks]       = useState([]);
  const [loading, setLoading]     = useState(true);
  const [scanning, setScanning]   = useState(false);
  const [scanStatus, setScanStatus] = useState(null);
  const [search, setSearch]       = useState('');
  const [sortKey, setSortKey]     = useState('');
  const [sortDir, setSortDir]     = useState('desc');
  const [error, setError]         = useState('');

  async function fetchData() {
    setLoading(true);
    try {
      const [r, s] = await Promise.all([getGurjas1(), getScanStatus()]);
      setStocks(r.data.stocks || []);
      setScanStatus(s.data);
    } catch {
      setError('Could not load GURJAS 1 data — backend may be waking up');
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
    } catch { setError('Scan trigger failed'); }
    setScanning(false);
  }

  function handleSort(key) {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('desc'); }
  }

  const filtered = stocks
    .filter(s => {
      const sym = (s.symbol || s.ticker || s.Symbol || '').toUpperCase();
      return sym.includes(search.toUpperCase());
    })
    .sort((a, b) => {
      if (!sortKey) return 0;
      const av = parseFloat(a[sortKey]) || 0;
      const bv = parseFloat(b[sortKey]) || 0;
      return sortDir === 'asc' ? av - bv : bv - av;
    });

  const Th = ({ k, label }) => (
    <th onClick={() => handleSort(k)} style={{ cursor: 'pointer', userSelect: 'none' }}>
      {label} {sortKey === k ? (sortDir === 'asc' ? '↑' : '↓') : ''}
    </th>
  );

  function getCol(s, keys) {
    for (const k of keys) if (s[k] !== undefined && s[k] !== null) return s[k];
    return null;
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title-glow">🔍 GURJAS 1 Screener</h1>
          <div className="page-subtitle">
            Sales/Profit Growth 3Y+5Y+Overall &gt; 20% · Price &gt; 200 DMA · PEG &lt; 1.2
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

        {/* Stats row */}
        <div className="metrics-grid" style={{ marginBottom: 20 }}>
          <div className="metric-card gold">
            <div className="metric-label">Stocks Found</div>
            <div className="metric-value">{stocks.length}</div>
            <div className="metric-sub">GURJAS 1 matches</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Last Scan</div>
            <div className="metric-value" style={{ fontSize: 14 }}>
              {scanStatus?.last_scan_time
                ? new Date(scanStatus.last_scan_time).toLocaleDateString('en-IN')
                : '—'}
            </div>
            <div className="metric-sub">{scanStatus?.total_stocks || 0} stocks scanned</div>
          </div>
          <div className="metric-card green">
            <div className="metric-label">Showing</div>
            <div className="metric-value">{filtered.length}</div>
            <div className="metric-sub">after filter</div>
          </div>
        </div>

        {/* Conditions reminder */}
        <div className="scan-banner" style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
            <strong style={{ color: 'var(--blue)' }}>GURJAS 1 Conditions:</strong>
            {' '}Sales CAGR 3Y/5Y/Overall &gt; 20% · Profit CAGR 3Y/5Y/Overall &gt; 20% · Current Price &gt; 200 DMA · PEG Ratio &lt; 1.2
          </div>
        </div>

        {/* Search */}
        <div style={{ marginBottom: 16 }}>
          <input
            className="input"
            style={{ maxWidth: 280 }}
            placeholder="Search symbol..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        {/* Table */}
        <div className="card">
          {loading ? (
            <div className="loading-state">
              <span className="spinner" />
              <span>Loading GURJAS 1 results...</span>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                If backend is waking up, this may take 30-60 seconds
              </span>
            </div>
          ) : filtered.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">🔍</div>
              <p>No results yet. Click "Run Scan" to fetch latest data.</p>
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
                    <Th k="profit_cagr_5y" label="Profit 5Y %" />
                    <Th k="profit_cagr_all" label="Profit All %" />
                    <Th k="peg" label="PEG" />
                    <Th k="ltp" label="LTP ₹" />
                    <Th k="sma_200" label="200 DMA ₹" />
                    <th>Stars ⭐</th>
                    <th>MCap</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((s, i) => {
                    const sym = (s.symbol || s.ticker || s.Symbol || '').replace('.NS', '');
                    const s3  = parseFloat(getCol(s, ['sales_cagr_3y', 'Sales CAGR 3Y', 'sales_3y']));
                    const s5  = parseFloat(getCol(s, ['sales_cagr_5y', 'Sales CAGR 5Y', 'sales_5y']));
                    const sa  = parseFloat(getCol(s, ['sales_cagr_all', 'Sales CAGR', 'sales_all']));
                    const p3  = parseFloat(getCol(s, ['profit_cagr_3y', 'Profit CAGR 3Y', 'profit_3y']));
                    const p5  = parseFloat(getCol(s, ['profit_cagr_5y', 'Profit CAGR 5Y', 'profit_5y']));
                    const pa  = parseFloat(getCol(s, ['profit_cagr_all', 'Profit CAGR', 'profit_all']));
                    const peg = parseFloat(getCol(s, ['peg', 'PEG Ratio', 'peg_ratio']));
                    const ltp = parseFloat(getCol(s, ['ltp', 'LTP', 'current_price']));
                    const sma = parseFloat(getCol(s, ['sma_200', '200 DMA', 'sma200']));
                    const stars = parseInt(getCol(s, ['Grand Total Stars', 'grand_total_stars', 'total_stars'])) || 0;
                    const mcap  = getCol(s, ['mcap', 'MCap', 'market_cap']);

                    const fmt = v => isNaN(v) ? '—' : v.toFixed(1);
                    const pct = v => isNaN(v) ? '—' : <span className={v >= 20 ? 'positive' : 'neutral'}>{v.toFixed(1)}%</span>;

                    return (
                      <tr key={sym + i}>
                        <td style={{ color: 'var(--text-muted)', fontSize: 11 }}>{i + 1}</td>
                        <td>
                          <div>{sym}</div>
                          {getCol(s, ['sector', 'Sector']) && (
                            <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                              {getCol(s, ['sector', 'Sector'])}
                            </div>
                          )}
                        </td>
                        <td>{pct(s3)}</td>
                        <td>{pct(s5)}</td>
                        <td>{pct(sa)}</td>
                        <td>{pct(p3)}</td>
                        <td>{pct(p5)}</td>
                        <td>{pct(pa)}</td>
                        <td>
                          {!isNaN(peg) ? (
                            <span className={`badge ${peg < 1.2 ? 'badge-green' : 'badge-red'}`}>
                              {peg.toFixed(2)}
                            </span>
                          ) : '—'}
                        </td>
                        <td>₹{isNaN(ltp) ? '—' : ltp.toLocaleString('en-IN')}</td>
                        <td>₹{isNaN(sma) ? '—' : sma.toFixed(0)}</td>
                        <td className="stars">{'⭐'.repeat(Math.min(stars, 5))}{stars > 0 ? ` ${stars}` : '—'}</td>
                        <td style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                          {mcap ? `₹${parseFloat(mcap).toFixed(0)}Cr` : '—'}
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

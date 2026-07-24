// src/pages/Dashboard.jsx — Page 1: Portfolio Dashboard
import { useState, useEffect, useCallback, useRef } from 'react';
import { getPortfolio, addHolding, removeHolding, syncPortfolios, getAnalysis, getScanStatus, getStocks } from '../api';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';

const COLORS = ['#00D4FF', '#FFD700', '#00E676', '#FF9F43', '#FF4757', '#A29BFE', '#FD79A8', '#74BFF9'];

function plPct(h) {
  if (!h.buy_price || !h.ltp) return 0;
  return ((h.ltp - h.buy_price) / h.buy_price * 100).toFixed(2);
}

function totalValue(holdings) {
  return holdings.reduce((s, h) => s + (h.ltp || h.buy_price) * h.quantity, 0);
}

function totalCost(holdings) {
  return holdings.reduce((s, h) => s + h.buy_price * h.quantity, 0);
}

export default function Dashboard({ userId = 1 }) {
  const [holdings, setHoldings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [scanStatus, setScanStatus] = useState(null);
  const [form, setForm] = useState({ symbol: '', buy_price: '', quantity: '' });
  const [adding, setAdding] = useState(false);
  const [analysis, setAnalysis] = useState({});
  const [analysisLoading, setAnalysisLoading] = useState({});
  const [error, setError] = useState('');

  // Auto-complete state
  const [allStocks, setAllStocks] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [stocksLoaded, setStocksLoaded] = useState(false);
  const inputRef = useRef(null);
  const suggestRef = useRef(null);

  const fetchPortfolio = useCallback(async () => {
    try {
      const r = await getPortfolio(userId);
      setHoldings(r.data.holdings || []);
    } catch {
      setError('Could not load portfolio — check backend connection');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  // Fetch stock list for auto-complete
  useEffect(() => {
    getStocks().then(r => {
      setAllStocks(r.data.symbols || []);
      setStocksLoaded(true);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    fetchPortfolio();
    getScanStatus().then(r => setScanStatus(r.data)).catch(() => {});
  }, [fetchPortfolio]);

  // Close suggestions when clicking outside
  useEffect(() => {
    function handleClick(e) {
      if (suggestRef.current && !suggestRef.current.contains(e.target) &&
          inputRef.current && !inputRef.current.contains(e.target)) {
        setShowSuggestions(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  function handleSymbolChange(value) {
    const upper = value.toUpperCase();
    setForm(p => ({ ...p, symbol: upper }));

    if (upper.length < 1) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    const matches = allStocks
      .filter(s => s.includes(upper))
      .slice(0, 20);
    setSuggestions(matches);
    setShowSuggestions(matches.length > 0);
  }

  function selectSymbol(sym) {
    setForm(p => ({ ...p, symbol: sym }));
    setShowSuggestions(false);
  }

  async function handleAdd(e) {
    e.preventDefault();
    if (!form.symbol || !form.buy_price || !form.quantity) return;
    setAdding(true);
    setError('');
    try {
      const r = await addHolding(userId, form.symbol, parseFloat(form.buy_price), parseInt(form.quantity));
      setHoldings(r.data.holdings || []);
      setForm({ symbol: '', buy_price: '', quantity: '' });
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to add holding');
    }
    setAdding(false);
  }

  async function handleRemove(symbol) {
    if (!confirm(`Remove ${symbol}?`)) return;
    setError('');
    try {
      const r = await removeHolding(userId, symbol);
      setHoldings(r.data.holdings || []);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to remove holding');
    }
  }

  async function handleSync() {
    setSyncing(true);
    try {
      await syncPortfolios();
      await new Promise(r => setTimeout(r, 3000));
      await fetchPortfolio();
    } catch { setError('Sync failed'); }
    setSyncing(false);
  }

  async function handleAnalysis(symbol) {
    setAnalysisLoading(p => ({ ...p, [symbol]: true }));
    try {
      const r = await getAnalysis(symbol.replace('.NS', ''));
      setAnalysis(p => ({ ...p, [symbol]: r.data.analysis }));
    } catch {
      setAnalysis(p => ({ ...p, [symbol]: 'AI analysis unavailable. Configure API keys in backend.' }));
    }
    setAnalysisLoading(p => ({ ...p, [symbol]: false }));
  }

  const value  = totalValue(holdings);
  const cost   = totalCost(holdings);
  const totalPL = value - cost;
  const totalPLPct = cost > 0 ? (totalPL / cost * 100).toFixed(2) : 0;
  const aboveSMA = holdings.filter(h => h.above_sma).length;
  const belowSMA = holdings.filter(h => !h.above_sma && h.sma_200 > 0).length;

  const pieData = holdings.map(h => ({
    name: h.symbol.replace('.NS', ''),
    value: (h.ltp || h.buy_price) * h.quantity,
  }));

  return (
    <>
      <div className="page-header">
        <div>
          <h1>📊 Portfolio Dashboard</h1>
          <div className="page-subtitle">
            {scanStatus?.last_scan
              ? `Last scan: ${new Date(scanStatus.last_scan).toLocaleString('en-IN')}`
              : 'No scan data yet'}
          </div>
        </div>
        <button className="btn btn-primary" onClick={handleSync} disabled={syncing}>
          {syncing ? <><span className="spinner" style={{ width: 14, height: 14 }} /> Syncing...</> : '↻ Sync Prices'}
        </button>
      </div>

      <div className="page-body">
        {error && (
          <div className="scan-banner warning" style={{ marginBottom: 20 }}>
            ⚠️ {error}
            <button className="btn btn-sm btn-outline" onClick={() => setError('')}>Dismiss</button>
          </div>
        )}

        {/* Scan Info Banner */}
        {scanStatus && (
          <div className="scan-banner" style={{ marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              <strong style={{ color: 'var(--blue)' }}>📡 Scan Status</strong>
              {' · '}
              <span>{scanStatus.total_stocks?.toLocaleString() || 0} stocks scanned</span>
              {scanStatus.scan_mode && <span> · Mode: {scanStatus.scan_mode}</span>}
              {scanStatus.last_scan_time && (
                <span> · Last: {new Date(scanStatus.last_scan_time).toLocaleString('en-IN')}</span>
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

        {/* Metrics */}
        <div className="metrics-grid">
          <div className="metric-card">
            <div className="metric-label">Holdings</div>
            <div className="metric-value">{holdings.length}</div>
            <div className="metric-sub">Active positions</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Portfolio Value</div>
            <div className="metric-value">₹{(value / 100000).toFixed(1)}L</div>
            <div className="metric-sub">Current market value</div>
          </div>
          <div className={`metric-card ${totalPL >= 0 ? 'green' : 'red'}`}>
            <div className="metric-label">Total P&L</div>
            <div className="metric-value">
              {totalPL >= 0 ? '+' : ''}₹{Math.abs(totalPL).toFixed(0)}
            </div>
            <div className="metric-sub">{totalPLPct}% overall</div>
          </div>
          <div className="metric-card green">
            <div className="metric-label">Above 200 SMA</div>
            <div className="metric-value">{aboveSMA}</div>
            <div className="metric-sub" style={{ color: 'var(--red)' }}>{belowSMA} below SMA ⚠️</div>
          </div>
        </div>

        <div className="grid-2 section">
          {/* Add Holding Form */}
          <div className="card">
            <div className="card-title">➕ Add Holding</div>
            <form onSubmit={handleAdd}>
              <div style={{ marginBottom: 10, position: 'relative' }}>
                <div className="input-label">Stock Symbol</div>
                <input
                  ref={inputRef}
                  className="input"
                  placeholder="Type symbol — RELIANCE, TCS, HDFCBANK..."
                  value={form.symbol}
                  onChange={e => handleSymbolChange(e.target.value)}
                  onFocus={() => form.symbol.length >= 1 && suggestions.length > 0 && setShowSuggestions(true)}
                  required
                  autoComplete="off"
                />
                {showSuggestions && (
                  <div ref={suggestRef} style={{
                    position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100,
                    background: 'var(--bg-card)', border: '1px solid var(--border-bright)',
                    borderRadius: 'var(--radius-sm)', maxHeight: 250, overflowY: 'auto',
                    marginTop: 2, boxShadow: '0 8px 24px rgba(0,0,0,0.4)'
                  }}>
                    {suggestions.map(s => (
                      <div key={s} onClick={() => selectSymbol(s)} style={{
                        padding: '8px 12px', cursor: 'pointer', fontSize: 13,
                        borderBottom: '1px solid var(--border)', color: 'var(--text-primary)',
                        transition: 'background 0.15s'
                      }}
                        onMouseEnter={e => e.target.style.background = 'var(--bg-card-hover)'}
                        onMouseLeave={e => e.target.style.background = 'transparent'}
                      >
                        {s}
                      </div>
                    ))}
                    {!stocksLoaded && (
                      <div style={{ padding: '8px 12px', fontSize: 11, color: 'var(--text-muted)' }}>
                        Loading stock list...
                      </div>
                    )}
                  </div>
                )}
              </div>
              <div className="input-group">
                <div style={{ flex: 1 }}>
                  <div className="input-label">Buy Price (₹)</div>
                  <input className="input" type="number" placeholder="2500" value={form.buy_price}
                    onChange={e => setForm(p => ({ ...p, buy_price: e.target.value }))} required />
                </div>
                <div style={{ flex: 1 }}>
                  <div className="input-label">Quantity</div>
                  <input className="input" type="number" placeholder="10" value={form.quantity}
                    onChange={e => setForm(p => ({ ...p, quantity: e.target.value }))} required />
                </div>
              </div>
              <button className="btn btn-primary" type="submit" disabled={adding} style={{ width: '100%' }}>
                {adding ? 'Adding...' : '+ Add to Portfolio'}
              </button>
            </form>
          </div>

          {/* Pie Chart */}
          <div className="card">
            <div className="card-title">🥧 Allocation</div>
            {pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80}
                    dataKey="value" nameKey="name">
                    {pieData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v) => `₹${v.toLocaleString('en-IN')}`}
                    contentStyle={{ background: '#0E1E3A', border: '1px solid rgba(0,212,255,0.2)', borderRadius: 8 }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-state"><div className="empty-icon">🥧</div><p>Add holdings to see allocation</p></div>
            )}
          </div>
        </div>

        {/* Holdings Table */}
        <div className="card section">
          <div className="card-title">📋 Holdings</div>
          {loading ? (
            <div className="loading-state"><span className="spinner" /><span>Loading portfolio...</span></div>
          ) : holdings.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">📂</div>
              <p>No holdings yet. Add your first stock above.</p>
            </div>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Buy ₹</th>
                    <th>Qty</th>
                    <th>LTP ₹</th>
                    <th>200 SMA ₹</th>
                    <th>SMA Signal</th>
                    <th>P&L %</th>
                    <th>Signal</th>
                    <th>AI</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {holdings.map(h => {
                    const pl = plPct(h);
                    const sym = h.symbol.replace('.NS', '');
                    return (
                      <>
                        <tr key={h.symbol}>
                          <td>{sym}</td>
                          <td>₹{h.buy_price?.toLocaleString('en-IN')}</td>
                          <td>{h.quantity}</td>
                          <td>₹{h.ltp?.toLocaleString('en-IN') || '—'}</td>
                          <td>₹{h.sma_200?.toFixed(0) || '—'}</td>
                          <td>
                            {h.sma_200 > 0 ? (
                              <span className={`badge ${h.above_sma ? 'badge-green' : 'badge-red'}`}>
                                {h.above_sma ? '✓ Above' : '⚠ Below'}
                              </span>
                            ) : <span className="badge badge-blue">Pending</span>}
                          </td>
                          <td className={parseFloat(pl) >= 0 ? 'positive' : 'negative'}>
                            {pl >= 0 ? '+' : ''}{pl}%
                          </td>
                          <td>
                            <span className={`badge ${h.signal === 'BUY' ? 'badge-green' : h.signal === 'SELL' ? 'badge-red' : 'badge-blue'}`}>
                              {h.signal || 'WAIT'}
                            </span>
                          </td>
                          <td>
                            <button className="btn btn-sm btn-outline"
                              onClick={() => handleAnalysis(h.symbol)}
                              disabled={analysisLoading[h.symbol]}>
                              {analysisLoading[h.symbol] ? '...' : '🤖 Ask'}
                            </button>
                          </td>
                          <td>
                            <button className="btn btn-sm btn-danger" onClick={() => handleRemove(h.symbol)}>
                              ✕
                            </button>
                          </td>
                        </tr>
                        {analysis[h.symbol] && (
                          <tr key={`${h.symbol}-analysis`}>
                            <td colSpan={10} style={{ background: 'rgba(0,212,255,0.04)', padding: '12px 16px' }}>
                              <div style={{ fontSize: 12, lineHeight: 1.6, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap' }}>
                                <strong style={{ color: 'var(--blue)' }}>JARVIS on {sym}:</strong><br />
                                {analysis[h.symbol]}
                              </div>
                            </td>
                          </tr>
                        )}
                      </>
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

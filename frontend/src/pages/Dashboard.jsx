// src/pages/Dashboard.jsx — Page 1: Portfolio Dashboard
import { useState, useEffect, useCallback } from 'react';
import { getPortfolio, addHolding, removeHolding, syncPortfolios, getAnalysis, getScanStatus } from '../api';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';

const COLORS = ['#00D4FF', '#FFD700', '#00E676', '#FF9F43', '#FF4757', '#A29BFE', '#FD79A8', '#74B9FF'];

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

  useEffect(() => {
    fetchPortfolio();
    getScanStatus().then(r => setScanStatus(r.data)).catch(() => {});
  }, [fetchPortfolio]);

  async function handleAdd(e) {
    e.preventDefault();
    if (!form.symbol || !form.buy_price || !form.quantity) return;
    setAdding(true);
    try {
      const r = await addHolding(userId, form.symbol, parseFloat(form.buy_price), parseInt(form.quantity));
      setHoldings(r.data.holdings || []);
      setForm({ symbol: '', buy_price: '', quantity: '' });
    } catch { setError('Failed to add holding'); }
    setAdding(false);
  }

  async function handleRemove(symbol) {
    if (!confirm(`Remove ${symbol}?`)) return;
    try {
      const r = await removeHolding(userId, symbol);
      setHoldings(r.data.holdings || []);
    } catch { setError('Failed to remove holding'); }
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
            {scanStatus?.last_scan ? `Last scan: ${new Date(scanStatus.last_scan).toLocaleString('en-IN')}` : 'No scan data yet'}
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
              <div style={{ marginBottom: 10 }}>
                <div className="input-label">Stock Symbol (e.g. RELIANCE)</div>
                <input
                  className="input"
                  placeholder="RELIANCE"
                  value={form.symbol}
                  onChange={e => setForm(p => ({ ...p, symbol: e.target.value.toUpperCase() }))}
                  required
                />
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

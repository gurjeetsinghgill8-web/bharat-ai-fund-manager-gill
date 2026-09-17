// src/lynch.js — DR GILL · PETER LYNCH 100-POINT RANKING ENGINE
//
// The Lynch system has three layers:
//   LAYER 1 — MACHINE FILTER   : growth + PEG + ROCE/ROE + debt + pledge  (Screener.in queries)
//   LAYER 2 — 100-POINT RANKING: Growth /40 · Valuation /20 · Quality /20 · Lynch Story /20  (this file)
//   LAYER 3 — HUMAN RESEARCH   : read the annual report, then override the Story bucket by hand
//
// Everything here is PURE JavaScript (no React, no DOM) so it can be unit-tested and reused.
//
// LENDER PATH — see src/lender.js
// A bank or an NBFC can never satisfy `ROCE > 15%` or `Debt/Equity < 0.5`: borrowing IS the raw
// material of a lender, and ROCE is meaningless when the "capital employed" IS the loan book. So
// lenders used to score 0/20 on Quality and be filtered out of the ranking entirely. They are
// now detected from sector + industry and judged on ROA, the capital cushion and NPA instead.
//
// DATA HONESTY RULE
// The scan provides: Sales/Profit CAGR 3Y/5Y/Overall, latest YoY growth, PEG, PE, Market Cap,
// Debt/Equity, Reserves, Promoter %, Institution %, Sector, Industry, Red-Alert flags.
// It does NOT (yet) carry ROCE, ROE, cash-flow-from-operations or promoter pledge from Screener.in.
// Whenever an exact field is missing we either derive a clearly-labelled ESTIMATE from fields we do
// have, or mark the line "unknown" and score it 0. Every line carries a `source` so the UI can show
// "exact" / "estimate" / "unknown". Never silently invent a number.

import {
  applyLenderScreen,
  isLender,
  lenderFlags,
  lenderMetrics,
  lenderQualityItems,
  LENDER_FACT_KEYS,
  LENDER_QUERY,
  LENDER_QUERY_NOTE,
} from './lender.js';


// ── Grade bands (from the spec) ─────────────────────────────────────────────
export const GRADE_BANDS = [
  { min: 90, grade: 'A+', decision: '⭐ Deep study',  tone: 'gold'   },
  { min: 80, grade: 'A',  decision: '⭐ Deep study',  tone: 'green'  },
  { min: 70, grade: 'B',  decision: '🟢 Study',        tone: 'blue'   },
  { min: 60, grade: 'C',  decision: '🟡 Watch',        tone: 'orange' },
  { min: -1, grade: 'D',  decision: "🔴 Don't bother", tone: 'red'    },
];

export function gradeOf(total) {
  return GRADE_BANDS.find((b) => total >= b.min) || GRADE_BANDS[GRADE_BANDS.length - 1];
}

// ── Rubric weights (single source of truth for both scoring and the UI table) ──
export const GROWTH_MAX = 40;
export const VALUATION_MAX = 20;
export const QUALITY_MAX = 20;
export const STORY_MAX = 20;

export const GROWTH_TESTS = [
  { key: 'sales3y',      label: 'Sales growth 3Y > 20%',    max: 8, threshold: 20 },
  { key: 'sales5y',      label: 'Sales growth 5Y > 20%',    max: 8, threshold: 20 },
  { key: 'profit3y',     label: 'Profit growth 3Y > 20%',   max: 8, threshold: 20 },
  { key: 'profit5y',     label: 'Profit growth 5Y > 20%',   max: 8, threshold: 20 },
  { key: 'salesGrowth',  label: 'Current sales growth > 20% (TTM)',  max: 4, threshold: 20 },
  { key: 'profitGrowth', label: 'Current profit growth > 20% (TTM)', max: 4, threshold: 20 },
];

export const PEG_BANDS = [
  { max: 0.6,       points: 10, label: 'PEG < 0.60' },
  { max: 0.8,       points: 8,  label: 'PEG 0.60 – 0.80' },
  { max: 1.0,       points: 6,  label: 'PEG 0.80 – 1.00' },
  { max: 1.25,      points: 3,  label: 'PEG 1.00 – 1.25' },
  { max: Infinity,  points: 0,  label: 'PEG > 1.25' },
];

export const STORY_ITEMS = [
  { key: 'simple',      label: 'Simple business',              max: 4 },
  { key: 'runway',      label: 'Large growth runway',          max: 4 },
  { key: 'share',       label: 'Market-share opportunity',     max: 3 },
  { key: 'nonCyclical', label: 'Growth not purely cyclical',   max: 3 },
  { key: 'cleanBooks',  label: 'No obvious accounting red flags', max: 3 },
  { key: 'management',  label: 'Management / promoter quality',   max: 3 },
];

// ── Layer-1 screens (the two Screener.in queries + an "everything scanned" pool) ──
export const SCREEN_DEFS = {
  hybrid: {
    id: 'hybrid',
    icon: '⭐',
    name: 'Lynch Hybrid',
    blurb: '>15% growth · PEG < 1 · ROCE/ROE > 15 · D/E < 0.75 · no pledge',
    query: [
      'Market Capitalization > 500',
      'AND Sales growth 3Years > 15',
      'AND Sales growth 5Years > 15',
      'AND Profit growth 3Years > 15',
      'AND Profit growth 5Years > 15',
      'AND Sales growth > 15',
      'AND Profit growth > 15',
      'AND YOY Quarterly sales growth > 10',
      'AND YOY Quarterly profit growth > 10',
      'AND PEG Ratio > 0',
      'AND PEG Ratio < 1',
      'AND Return on capital employed > 15',
      'AND Return on equity > 15',
      'AND Debt to equity < 0.75',
      'AND Pledged percentage = 0',
    ].join('\n'),
  },
  elite: {
    id: 'elite',
    icon: '🔥',
    name: 'Elite Mode',
    blurb: '>20% growth · PEG < 0.60 · ROCE > 20% · ROE > 15% · D/E < 0.5 · no pledge',
    query: [
      'Market Capitalization > 500',
      'AND Sales growth 3Years > 20',
      'AND Sales growth 5Years > 20',
      'AND Profit growth 3Years > 20',
      'AND Profit growth 5Years > 20',
      'AND Sales growth > 20',
      'AND Profit growth > 20',
      'AND YOY Quarterly sales growth > 20',
      'AND YOY Quarterly profit growth > 20',
      'AND PEG Ratio > 0',
      'AND PEG Ratio < 0.6',
      'AND Return on capital employed > 20',
      'AND Return on equity > 15',
      'AND Debt to equity < 0.5',
      'AND Pledged percentage = 0',
    ].join('\n'),
  },
  // ── 🏦 BANKS & NBFC — the lender basket ──────────────────────────────────
  // A bank or an NBFC can never pass the two baskets above: D/E < 0.75 is impossible when
  // borrowing is the raw material, and ROCE is meaningless when the "capital employed" IS the
  // loan book. Rather than let lenders fall out of the scan, they get their own basket and their
  // own rubric — ROA, the capital cushion, and NPA. Selecting this chip shows lenders ONLY; the
  // Elite / Hybrid chips judge a lender with its own rubric rather than dropping it.
  financials: {
    id: 'financials',
    icon: '🏦',
    name: 'Banks & NBFC',
    blurb: '>15% growth · PEG < 1.2 · ROA > 1% · ROE > 15% · capital cushion · NPA when known',
    query: LENDER_QUERY,
    note: LENDER_QUERY_NOTE,
  },
  all: {
    id: 'all',
    icon: '📚',
    name: 'Everything scanned',
    blurb: 'Every GURJAS result from the last scan — no Layer-1 filter applied',
    query: null,
  },
};

// ── Field aliases (the scan has used several spellings over time) ───────────
const ALIASES = {
  symbol:       ['symbol', 'Ticker', 'ticker', 'Symbol'],
  sales3y:      ['Sales CAGR 3Y', 'sales_cagr_3y', 'sales_3y'],
  sales5y:      ['Sales CAGR 5Y', 'sales_cagr_5y', 'sales_5y'],
  profit3y:     ['Profit CAGR 3Y', 'profit_cagr_3y', 'profit_3y'],
  profit5y:     ['Profit CAGR 5Y', 'profit_cagr_5y', 'profit_5y'],
  salesGrowth:  ['Sales Growth', 'sales_growth'],
  profitGrowth: ['Profit Growth', 'profit_growth'],
  peg:          ['PEG Ratio', 'peg', 'peg_ratio'],
  pe:           ['PE', 'pe'],
  mcap:         ['Market Cap (Cr)', 'mcap', 'market_cap_cr'],
  de:           ['Debt/Equity', 'debt_to_equity'],
  reserves:     ['Reserves', 'reserves'],
  promoter:     ['Promoter %', 'promoter_share'],
  institution:  ['Institution %', 'inst_share'],
  roce:         ['ROCE %', 'roce', 'Return on capital employed'],
  roe:          ['ROE %', 'roe', 'Return on equity'],
  cfoPat:       ['CFO/PAT', 'cfo_to_pat', 'ocf_to_pat'],
  pledged:      ['Pledged %', 'pledged_percent', 'pledge_percent'],
  redAlert:     ['Red Alert', 'red_alert'],
  redReasons:   ['Red Reasons', 'red_reasons'],
  sector:       ['Sector', 'sector'],
  industry:     ['Industry', 'industry'],
  category:     ['Category', 'category'],
  turnaround:   ['Turn Around', 'turn_around'],
  aboveSma:     ['Is Above 200 SMA', 'above_200dma'],
};

// ── Small helpers ───────────────────────────────────────────────────────────
export function num(stock, keys) {
  for (const k of keys) {
    const v = stock?.[k];
    if (v === undefined || v === null || v === '') continue;
    const n = typeof v === 'number' ? v : parseFloat(String(v).replace(/[,%₹]/g, ''));
    if (Number.isFinite(n)) return n;
  }
  return null;
}

export function stockSymbol(stock) {
  const raw = stock?.['symbol'] || stock?.['Ticker'] || stock?.['ticker'] || '';
  return String(raw).replace(/\.(NS|BO)$/i, '').toUpperCase();
}

export function boolOf(stock, keys) {
  for (const k of keys) {
    const v = stock?.[k];
    if (v === undefined || v === null) continue;
    if (typeof v === 'boolean') return v;
    const s = String(v).trim().toLowerCase();
    if (s === 'true' || s === 'yes' || s === '1') return true;
    if (s === 'false' || s === 'no' || s === '0') return false;
  }
  return null;
}

const round1 = (x) => Math.round(x * 10) / 10;
const half = (x) => Math.round(x * 2) / 2;          // round to nearest 0.5
const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));

// CAGR columns arrive as 0.0 when the scan could not compute them.
function withFallback(primary, fallback) {
  if (primary !== null && primary !== 0) return { value: primary, fallback: false };
  if (fallback !== null && fallback !== 0) return { value: fallback, fallback: true };
  return { value: null, fallback: false };
}

// ── METRICS: normalise one scan record into the numbers the rubric needs ────
// `facts` = the manual lender numbers typed into the score card (GNPA / NNPA / PCR / CAR).
// NPA is login-walled on Screener.in, so this is how the NPA lens actually gets switched on.
export function lynchMetrics(stock, facts) {
  if (facts) {
    const patched = { ...stock };
    for (const [k, col] of Object.entries(LENDER_FACT_KEYS)) {
      if (facts[k] !== undefined && facts[k] !== null && facts[k] !== '') patched[col] = facts[k];
    }
    stock = patched;
  }

  const sales3yRaw = num(stock, ALIASES.sales3y);
  const sales5yRaw = num(stock, ALIASES.sales5y);
  const profit3yRaw = num(stock, ALIASES.profit3y);
  const profit5yRaw = num(stock, ALIASES.profit5y);

  const sales5 = withFallback(sales5yRaw, sales3yRaw);     // Screener-style: fall back to 3Y
  const profit5 = withFallback(profit5yRaw, profit3yRaw);

  const peg = num(stock, ALIASES.peg);
  const pe = num(stock, ALIASES.pe);
  const mcap = num(stock, ALIASES.mcap);
  const deRaw = num(stock, ALIASES.de);
  const reserves = num(stock, ALIASES.reserves);
  const promoter = num(stock, ALIASES.promoter);
  const institution = num(stock, ALIASES.institution);

  // yfinance returns debtToEquity either as a ratio (0.45) or as a percentage (45.0).
  const deRatio = deRaw === null ? null : deRaw > 5 ? deRaw / 100 : deRaw;

  // PAT in ₹ Cr — Market Cap ÷ PE is the earnings the market is capitalising.
  const patCr = mcap !== null && pe !== null && pe > 0 ? mcap / pe : null;

  // Debt in ₹ Cr — implied from Reserves (= equity proxy) × Debt/Equity.
  const debtCr = reserves !== null && reserves > 0 && deRatio !== null ? reserves * deRatio : null;
  const capitalEmployed = reserves !== null && reserves > 0 ? reserves + (debtCr || 0) : null;

  // ROCE / ROE — exact when the scan carries them, else a clearly-labelled estimate.
  const roceExact = num(stock, ALIASES.roce);
  const roeExact = num(stock, ALIASES.roe);
  const roceEst = patCr !== null && capitalEmployed ? (patCr / capitalEmployed) * 100 : null;
  const roeEst = patCr !== null && reserves !== null && reserves > 0 ? (patCr / reserves) * 100 : null;

  const roce = roceExact !== null && roceExact !== 0 ? roceExact : roceEst;
  const roe = roeExact !== null && roeExact !== 0 ? roeExact : roeEst;

  const cfoPat = num(stock, ALIASES.cfoPat);
  const pledged = num(stock, ALIASES.pledged);
  const redAlert = boolOf(stock, ALIASES.redAlert);

  // ── LENDER PATH ─────────────────────────────────────────────────────────
  // For a bank / NBFC, ROCE is meaningless and Debt/Equity < 0.5 is impossible, so the ordinary
  // Quality bucket would hand a perfectly good lender 0/20 and Layer-1 would then drop it from
  // the ranking entirely. Lenders get their own metrics (ROA, capital cushion, NPA, P/B) and
  // their own Quality bucket — see lender.js.
  const lender = isLender(stock) ? lenderMetrics(stock, { patCr, mcap, pe }) : null;
  let roceFinal = roce;
  let roeFinal = roe;
  if (lender) {
    roceFinal = null;                       // not a lender metric — never score it
    if (lender.roe !== null) roeFinal = lender.roe;
  }

  return {
    symbol: stockSymbol(stock),
    sector: stock?.['Sector'] || stock?.['sector'] || 'Unknown',
    industry: stock?.['Industry'] || stock?.['industry'] || 'Unknown',
    category: stock?.['Category'] || '',
    isLender: lender !== null,
    lender,

    sales3y: sales3yRaw,
    sales5y: sales5.value,
    sales5yFallback: sales5.fallback,
    profit3y: profit3yRaw,
    profit5y: profit5.value,
    profit5yFallback: profit5.fallback,
    salesGrowth: num(stock, ALIASES.salesGrowth),
    profitGrowth: num(stock, ALIASES.profitGrowth),

    peg, pe, mcap,
    deRatio,
    reserves, promoter, institution,
    patCr: patCr === null ? null : round1(patCr),
    debtCr: debtCr === null ? null : round1(debtCr),

    roce: roceFinal === null ? null : round1(roceFinal),
    roe: roeFinal === null ? null : round1(roeFinal),
    cfoPat,
    pledged,
    redAlert,
    redReasons: stock?.['Red Reasons'] || stock?.['red_reasons'] || '',
    turnaround: boolOf(stock, ALIASES.turnaround),
    aboveSma: boolOf(stock, ALIASES.aboveSma),

    source: {
      roce: roceExact ? 'exact' : roceEst !== null ? 'estimate' : 'unknown',
      roe: roeExact ? 'exact' : roeEst !== null ? 'estimate' : 'unknown',
      cashflow: cfoPat !== null ? 'exact' : 'estimate',
      pledge: pledged !== null ? 'exact' : 'estimate',
      debt: deRatio !== null ? 'exact' : 'unknown',
    },
  };
}

// ── GROWTH /40 ──────────────────────────────────────────────────────────────
function scoreGrowth(m) {
  const values = {
    sales3y: m.sales3y, sales5y: m.sales5y,
    profit3y: m.profit3y, profit5y: m.profit5y,
    salesGrowth: m.salesGrowth, profitGrowth: m.profitGrowth,
  };
  const items = GROWTH_TESTS.map((t) => {
    const v = values[t.key];
    const known = v !== null && v !== undefined;
    const fallback = (t.key === 'sales5y' && m.sales5yFallback) || (t.key === 'profit5y' && m.profit5yFallback);
    const points = known && v > t.threshold ? t.max : 0;
    return {
      key: t.key,
      label: t.label,
      max: t.max,
      points,
      value: v,
      valueText: known ? `${round1(v)}%` : 'n/a',
      status: !known ? 'unknown' : points === t.max ? 'pass' : 'fail',
      note: fallback ? '5Y unavailable in scan — 3Y CAGR used' : '',
    };
  });
  return { points: items.reduce((s, i) => s + i.points, 0), max: GROWTH_MAX, items };
}

// ── VALUATION /20 (PEG ladder, exactly as specified) ───────────────────────
function scoreValuation(m) {
  const peg = m.peg;
  let band = null;
  let points = 0;
  if (peg !== null && peg > 0) {
    band = PEG_BANDS.find((b) => peg < b.max) || PEG_BANDS[PEG_BANDS.length - 1];
    points = band.points;
  }
  const items = PEG_BANDS.map((b) => ({
    key: `peg_${b.max}`,
    label: b.label,
    max: b.points,
    points: band && band.label === b.label ? b.points : 0,
    status: band && band.label === b.label ? 'pass' : 'fail',
  }));
  return {
    points,
    max: VALUATION_MAX,
    peg,
    bandLabel: band ? band.label : 'PEG unavailable',
    items,
    warnings: peg !== null && peg > 1.5 ? ['PEG > 1.5 — market is already paying up for this growth'] : [],
  };
}

// ── QUALITY /20 ─────────────────────────────────────────────────────────────
function scoreQuality(m) {
  // A lender's 20 marks come from ROA, the capital cushion and asset quality — not from ROCE and
  // D/E. Same total, same ✅/❌/➖ shape, so the score card renders identically.
  if (m.isLender) {
    const lenderItems = lenderQualityItems(m.lender);
    return { points: lenderItems.reduce((s, i) => s + i.points, 0), max: QUALITY_MAX, items: lenderItems };
  }

  const items = [];

  // 1) ROCE > 20% — 5 marks
  items.push({
    key: 'roce', label: 'ROCE > 20%', max: 5,
    value: m.roce, valueText: m.roce === null ? 'n/a' : `${round1(m.roce)}%`,
    points: m.roce !== null && m.roce > 20 ? 5 : 0,
    status: m.roce === null ? 'unknown' : m.roce > 20 ? 'pass' : 'fail',
    source: m.source.roce,
    note: m.source.roce === 'estimate' ? 'Estimated: PAT ÷ (Reserves + implied debt). Verify on Screener.in' : '',
  });

  // 2) ROE > 20% — 4 marks
  items.push({
    key: 'roe', label: 'ROE > 20%', max: 4,
    value: m.roe, valueText: m.roe === null ? 'n/a' : `${round1(m.roe)}%`,
    points: m.roe !== null && m.roe > 20 ? 4 : 0,
    status: m.roe === null ? 'unknown' : m.roe > 20 ? 'pass' : 'fail',
    source: m.source.roe,
    note: m.source.roe === 'estimate' ? 'Estimated: PAT ÷ Reserves (equity proxy)' : '',
  });

  // 3) Positive / healthy cash flow — 4 marks
  const cashPass = m.cfoPat !== null
    ? m.cfoPat > 0
    : (m.profitGrowth !== null && m.profitGrowth > 0) && m.redAlert !== true && m.profit3y !== null && m.profit3y > 0;
  items.push({
    key: 'cash', label: 'Positive / healthy cash flow', max: 4,
    value: m.cfoPat, valueText: m.cfoPat !== null ? `CFO/PAT ${round1(m.cfoPat)}` : cashPass ? 'Profits growing, no red flag' : 'n/a',
    points: cashPass ? 4 : 0,
    status: cashPass ? 'pass' : 'fail',
    source: m.source.cashflow,
    note: m.cfoPat === null ? 'Cash-flow statement not in scan — proxy: positive & rising profits, no red alert' : '',
  });

  // 4) CFO reasonably tracks PAT — 3 marks
  let cfoTracksPass;
  if (m.cfoPat !== null) {
    cfoTracksPass = m.cfoPat >= 0.7;
  } else {
    const s = m.sales3y, p = m.profit3y;
    cfoTracksPass = s !== null && p !== null && s > 0 && p >= s * 0.8 && m.redAlert !== true;
  }
  items.push({
    key: 'cfoTracks', label: 'CFO reasonably tracks PAT', max: 3,
    valueText: m.cfoPat !== null ? `${round1(m.cfoPat)}×` : cfoTracksPass ? 'Profit grows with Sales' : 'n/a',
    points: cfoTracksPass ? 3 : 0,
    status: cfoTracksPass ? 'pass' : 'fail',
    source: m.source.cashflow,
    note: m.cfoPat === null ? 'Proxy: 3Y profit CAGR grows at least 0.8× the sales CAGR' : '',
  });

  // 5) Debt / Equity < 0.5 — 2 marks
  items.push({
    key: 'debt', label: 'Debt/Equity < 0.5', max: 2,
    value: m.deRatio, valueText: m.deRatio === null ? 'n/a' : m.deRatio.toFixed(2),
    points: m.deRatio !== null && m.deRatio < 0.5 ? 2 : 0,
    status: m.deRatio === null ? 'unknown' : m.deRatio < 0.5 ? 'pass' : 'fail',
    source: m.source.debt,
  });

  // 6) Promoter pledge = 0 — 2 marks
  const pledgeKnown = m.pledged !== null;
  const pledgePass = pledgeKnown
    ? m.pledged === 0
    : (m.promoter !== null && m.promoter >= 40 && m.promoter <= 75 && m.redAlert !== true);
  items.push({
    key: 'pledge', label: 'Promoter pledge = 0', max: 2,
    valueText: pledgeKnown ? `${m.pledged}%` : m.promoter !== null ? `promoter ${round1(m.promoter)}%` : 'n/a',
    points: pledgePass ? 2 : 0,
    status: pledgePass ? 'pass' : 'fail',
    source: m.source.pledge,
    note: pledgeKnown ? '' : 'Pledge data not in scan — proxy: healthy promoter holding, no red flag. Confirm pledge on Screener.in',
  });

  return { points: items.reduce((s, i) => s + i.points, 0), max: QUALITY_MAX, items };
}

// ── LYNCH STORY /20 (auto-proxy, Layer-3 overridable) ──────────────────────
const CYCLICALITY = {
  3: ['Technology', 'Healthcare', 'Consumer Defensive', 'Communication Services'],
  2: ['Consumer Cyclical', 'Industrials', 'Financial Services'],
  1: ['Basic Materials', 'Energy', 'Real Estate', 'Utilities'],
};
const COMPLEX_SECTORS = ['Financial Services', 'Real Estate', 'Utilities', 'Energy'];
const COMPLEX_WORDS = ['diversified', 'conglomerate', 'holding'];

export function autoStory(m) {
  const sector = m.sector || 'Unknown';
  const industry = (m.industry || '').toLowerCase();

  // Simple business: penalise opaque capital structures and conglomerates.
  let simple = 4;
  if (COMPLEX_SECTORS.includes(sector)) simple = 2;
  if (COMPLEX_WORDS.some((w) => industry.includes(w))) simple = Math.min(simple, 2);
  if (sector === 'Unknown') simple = 3;

  // Large growth runway: small/mid caps simply have more room; needs real growth.
  let runway = m.mcap === null ? 2 : m.mcap < 5000 ? 4 : m.mcap < 20000 ? 3 : m.mcap < 50000 ? 2 : 1;
  if (!(m.sales3y !== null && m.sales3y >= 15)) runway = Math.max(1, runway - 1);

  // Market-share opportunity: 3Y growth outrunning the 5Y trend = share gains.
  let share = 0;
  if (m.sales3y !== null && m.sales5y !== null) {
    if (m.sales3y > m.sales5y + 2) share = 3;
    else if (m.sales3y > m.sales5y) share = 2;
    else if (m.sales3y >= 15) share = 1;
  } else if (m.sales3y !== null && m.sales3y >= 20) {
    share = 2;
  }
  if (m.turnaround === true) share = Math.min(3, share + 1);

  // Growth not purely cyclical.
  let nonCyclical = 2;
  for (const [pts, list] of Object.entries(CYCLICALITY)) {
    if (list.includes(sector)) nonCyclical = Number(pts);
  }
  if (sector === 'Unknown') nonCyclical = 2;
  // Profit growth wildly ahead of sales in a cyclical sector = commodity-cycle windfall.
  if (nonCyclical <= 1 && m.profit3y !== null && m.sales3y !== null && m.profit3y > m.sales3y * 3) {
    nonCyclical = 1;
  }

  // No obvious accounting red flags.
  let cleanBooks = m.redAlert === false ? 3 : m.redAlert === true ? 0 : 1.5;
  if (cleanBooks === 3 && m.profitGrowth !== null && m.salesGrowth !== null
      && m.salesGrowth > 0 && m.profitGrowth > m.salesGrowth * 4 + 100) {
    cleanBooks = 1.5; // profit explosion far beyond sales — check one-offs
  }

  // Management / promoter quality.
  let management = 1;
  if (m.promoter !== null && m.promoter >= 40 && m.promoter <= 75) management += 1;
  if (m.institution !== null && m.institution >= 10) management += 1;
  if (m.promoter !== null && m.promoter < 25) management = Math.min(management, 1);

  return {
    simple: clamp(half(simple), 0, 4),
    runway: clamp(half(runway), 0, 4),
    share: clamp(half(share), 0, 3),
    nonCyclical: clamp(half(nonCyclical), 0, 3),
    cleanBooks: clamp(half(cleanBooks), 0, 3),
    management: clamp(half(management), 0, 3),
  };
}

export function scoreStory(m, override) {
  const auto = autoStory(m);
  const items = STORY_ITEMS.map((t) => {
    const hasOverride = override && override[t.key] !== undefined && override[t.key] !== null && override[t.key] !== '';
    const value = hasOverride ? clamp(Number(override[t.key]) || 0, 0, t.max) : auto[t.key];
    return {
      key: t.key,
      label: t.label,
      max: t.max,
      points: value,
      auto: auto[t.key],
      overridden: Boolean(hasOverride),
      status: hasOverride ? 'manual' : 'estimate',
    };
  });
  return {
    points: half(items.reduce((s, i) => s + i.points, 0)),
    max: STORY_MAX,
    items,
    auto,
    overridden: items.some((i) => i.overridden),
  };
}

// ── THE 100-POINT SCORE ─────────────────────────────────────────────────────
export function scoreLynch(stock, storyOverride, facts) {
  const m = lynchMetrics(stock, facts);
  const growth = scoreGrowth(m);
  const valuation = scoreValuation(m);
  const quality = scoreQuality(m);
  const story = scoreStory(m, storyOverride);

  const total = round1(growth.points + valuation.points + quality.points + story.points);
  const band = gradeOf(total);

  const warnings = [...valuation.warnings];
  if (m.redAlert === true) warnings.push(`Red alert: ${m.redReasons || 'see scan'}`);
  if (m.isLender) {
    // A lender is not "debt-heavy" — it IS debt. Flag what actually breaks a lender instead:
    // weak ROA, a thin capital cushion, and asset-quality stress.
    warnings.push(...lenderFlags(m.lender));
  } else if (m.deRatio !== null && m.deRatio > 1) {
    warnings.push(`High leverage (D/E ${m.deRatio.toFixed(2)}) — Lynch disliked debt-heavy growth`);
  }
  if (growth.items.some((i) => i.key === 'profit3y' && i.status === 'fail')
      && growth.items.some((i) => i.key === 'sales3y' && i.status === 'pass')) {
    warnings.push('Sales growing but profits are not — margin pressure');
  }

  return {
    symbol: m.symbol,
    sector: m.sector,
    industry: m.industry,
    category: m.category,
    metrics: m,
    growth,
    valuation,
    quality,
    story,
    total,
    grade: band.grade,
    decision: band.decision,
    tone: band.tone,
    warnings,
    storyOverridden: story.overridden,
  };
}

// ── LAYER-1 FILTERS (run on the metrics, mirroring the Screener.in queries) ──
// `required: true`  → the metric must exist AND pass (core of the query).
// `required: false` → if the metric is missing we cannot verify it; the stock stays in the
//                     basket but the criterion is reported as "unverified" instead of failing,
//                     so a missing pledge/ROCE column never silently empties the screen.
//
// LENDER ROUTING — the fix for "why did CHOLAFIN never appear?". Selecting 🔥 Elite or
// ⭐ Lynch Hybrid used to judge a bank/NBFC by ROCE and Debt/Equity, which no lender can ever
// satisfy, so every bank and NBFC was filtered out of the ranking. A lender is now judged by the
// lender rubric (ROA · capital cushion · NPA), and 🏦 Banks & NBFC shows the lenders on their own.
// Either way a lender is RANKED, never silently dropped.
export function applyScreen(metrics, screenId) {
  const m = metrics;
  const unverified = [];
  if (screenId === 'all' || !SCREEN_DEFS[screenId]) return { pass: true, unverified, failed: [], rubric: 'standard' };

  if (screenId === 'financials') {
    if (!m.isLender) return { pass: false, unverified: [], failed: ['Not a bank / NBFC'], rubric: 'lender' };
    return applyLenderScreen(m.lender, 'financials');
  }

  if (m.isLender) {
    return applyLenderScreen(m.lender, screenId === 'elite' ? 'elite' : 'hybrid');
  }

  const strict = screenId === 'elite';
  const g = strict ? 20 : 15;
  const deMax = strict ? 0.5 : 0.75;
  const pegMax = strict ? 0.6 : 1.0;
  const roceMin = strict ? 20 : 15;
  const latestMin = strict ? 20 : 15;

  const criteria = [
    { label: `Sales growth 3Y > ${g}%`,           value: m.sales3y,      ok: m.sales3y > g,      required: true },
    { label: `Sales growth 5Y > ${g}%`,           value: m.sales5y,      ok: m.sales5y > g,      required: true },
    { label: `Profit growth 3Y > ${g}%`,          value: m.profit3y,     ok: m.profit3y > g,     required: true },
    { label: `Profit growth 5Y > ${g}%`,          value: m.profit5y,     ok: m.profit5y > g,     required: true },
    { label: `PEG between 0 and ${pegMax}`,       value: m.peg,          ok: m.peg > 0 && m.peg < pegMax, required: true },
    { label: `Latest sales growth > ${latestMin}%`,  value: m.salesGrowth,  ok: m.salesGrowth > latestMin,  required: false },
    { label: `Latest profit growth > ${latestMin}%`, value: m.profitGrowth, ok: m.profitGrowth > latestMin, required: false },
    { label: `ROCE > ${roceMin}%`,                value: m.roce,         ok: m.roce > roceMin,   required: false },
    { label: 'ROE > 15%',                         value: m.roe,          ok: m.roe > 15,         required: false },
    { label: `Debt/Equity < ${deMax}`,            value: m.deRatio,      ok: m.deRatio < deMax,  required: false },
    { label: 'Promoter pledge = 0%',              value: m.pledged,      ok: m.pledged === 0,    required: false },
  ];

  let pass = true;
  const failed = [];
  for (const c of criteria) {
    if (c.value === null || c.value === undefined) {
      if (c.required) { pass = false; failed.push(`${c.label} — data missing`); }
      else unverified.push(c.label);
      continue;
    }
    if (!c.ok) { pass = false; failed.push(c.label); }
  }
  return { pass, unverified, failed, rubric: 'standard' };
}

// ── Output helpers ──────────────────────────────────────────────────────────
// One row per company, NSE winning over BSE.
//
// 89 names in the scan are listed on BOTH exchanges (CHOLAFIN.NS and CHOLAFIN.BO), and
// `stockSymbol()` strips the .NS / .BO suffix — so an undeduplicated list ranks CHOLAFIN twice
// with two different scores and makes a stock search return the same name twice. NSE is the
// primary listing that the Screener.in queries match, so it is the one kept. The Sectors page
// still sees both, because there the NSE-vs-BSE split is wanted.
// (Twin: `dedupe_by_symbol` in lynch_engine.py.)
export function dedupeBySymbol(records) {
  const best = new Map();
  for (const rec of records) {
    const sym = stockSymbol(rec);
    if (!sym) continue;
    const exch = String(rec?.['Exchange'] || rec?.['exchange'] || '').toUpperCase();
    const current = best.get(sym);
    if (!current || (exch === 'NSE' && current.exch !== 'NSE')) best.set(sym, { exch, rec });
  }
  return [...best.values()].map((v) => v.rec);
}

export function toCsv(rows) {
  // Column order here is the on-screen order too: Market Cap and Decision come first.
  const head = [
    'Rank', 'Symbol', 'Type', 'MCap(Cr)', 'Decision', 'Grade', 'Total/100', 'Sector',
    'Growth/40', 'Valuation/20', 'Quality/20', 'Story/20',
    'PEG', 'Sales3Y%', 'Sales5Y%', 'Profit3Y%', 'Profit5Y%',
    'ROCE%', 'ROE%', 'Debt/Equity', 'Promoter%',
    'ROA%', 'NetWorth(Cr)', 'Capital%Assets', 'P/B', 'GNPA%', 'NNPA%',
  ];
  const esc = (v) => {
    const s = v === null || v === undefined ? '' : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = rows.map((r, i) => {
    const m = r.metrics;
    const ld = m.lender || {};
    return [
      i + 1, r.symbol, ld.kindLabel ? ld.kindLabel.split(' /')[0] : '',
      m.mcap === null ? '' : Math.round(m.mcap), r.decision, r.grade, r.total, r.sector,
      r.growth.points, r.valuation.points, r.quality.points, r.story.points,
      m.peg, m.sales3y, m.sales5y, m.profit3y, m.profit5y,
      m.roce, m.roe,
      m.deRatio === null ? '' : m.deRatio.toFixed(2), m.promoter,
      ld.roa ?? '', ld.netWorthCr ?? '', ld.capitalPct ?? '', ld.pb ?? '', ld.gnpa ?? '', ld.nnpa ?? '',
    ].map(esc).join(',');
  });
  return [head.join(','), ...lines].join('\n');
}

export function topFiveText(rows, limit = 5) {
  const stamp = new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  const lines = [`🏆 DR GILL — LYNCH ${limit}  (${stamp})`, ''];
  rows.slice(0, limit).forEach((r, i) => {
    const m = r.metrics;
    lines.push(
      `${i + 1}. ${r.symbol} — ${r.total}/100 (${r.grade}) ${r.decision}`,
      `   PEG ${m.peg ?? '—'} · Sales 3Y ${m.sales3y ?? '—'}% / 5Y ${m.sales5y ?? '—'}% · Profit 3Y ${m.profit3y ?? '—'}%`,
    );
    if (m.isLender && m.lender) {
      const ld = m.lender;
      const npa = ld.gnpa !== null ? `GNPA ${ld.gnpa}% / NNPA ${ld.nnpa ?? '—'}%` : 'NPA not in scan — check Screener.in';
      lines.push(`   ${ld.kindLabel} · ROA ${ld.roa ?? '—'}% · ROE ${ld.roe ?? '—'}% · capital ${ld.capitalPct ?? '—'}% of assets · ${npa}`);
    }
    lines.push(
      `   Growth ${r.growth.points}/40 · Valuation ${r.valuation.points}/20 · Quality ${r.quality.points}/20 · Story ${r.story.points}/20`,
    );
  });
  lines.push('', 'Screener → 100-point score → Top 5 → deep research');
  return lines.join('\n');
}

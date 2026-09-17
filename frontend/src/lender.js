// src/lender.js — LENDER-AWARE ANALYTICS (Banks · NBFC · Housing finance)
//
// The JavaScript twin of `financial_engine.py`. Both must stay in step, because the Streamlit
// page (lynch_engine.py) and this React dashboard (lynch.js) promise the SAME score for the
// same stock — see PETER_LYNCH_SYSTEM.md.
//
// WHY THIS FILE EXISTS
// --------------------
// A lender is not a manufacturer, and the 100-point rubric was written for manufacturers:
//
//   1. `Debt/Equity < 0.5` and `ROCE > 15%` are impossible for a lender. Borrowing IS the raw
//      material of a bank or an NBFC — CHOLAFIN runs at D/E ≈ 6.9, HDFCBANK at roughly 12×
//      assets/net-worth — and ROCE is meaningless when the "capital employed" IS the loan book.
//      The ordinary Quality bucket therefore handed a good NBFC 0/20 and Layer-1 then dropped
//      it out of the ranking entirely. That is exactly how CHOLAFIN got "missed".
//
//   2. scoring_engine.py raised a RED ALERT at D/E > 2.0, which every Indian NBFC trips. That
//      is fixed on the Python side too (`is_financial()` gate) and the flag reaches this page
//      inside the scan record.
//
// WHAT A LENDER IS JUDGED ON INSTEAD
// ----------------------------------
//   ROCE                 →  ROA (Return on Assets)          — 1.0%+ is respectable
//   Debt/Equity < 0.5    →  Net worth ÷ total assets        — the capital cushion
//   Operating cash flow  →  Financing margin (NIM proxy)    — the earnings engine
//   (nothing)            →  Gross NPA / Net NPA / PCR / CAR — asset quality
//   (nothing)            →  P/B                             — the valuation read
//
// DATA HONESTY — same rule as lynch.js. Every value carries a `source`:
//   exact     — read from the balance sheet / P&L (screeners_scraper.py pulls Equity Capital,
//               Reserves, Deposits, Borrowing, Total Assets and Financing Margin % for free)
//   estimate  — derived (Net worth ≈ Reserves, PAT ≈ Market Cap ÷ PE, Borrowings ≈ Net worth × D/E)
//   unknown   — absent. Scores 0 and is NEVER invented.
//
// NPA IS `unknown` BY DEFAULT ON PURPOSE. Screener.in prints the Gross NPA / Net NPA / CAR
// rows on a lender page but BLANKS THE VALUES behind a login. We do not guess an NPA; the score
// card takes it as a manual entry, which is the lens the fund manager asked for by name.

// ── Which industries are lenders ────────────────────────────────────────────
const LENDER_MARKERS = [
  'bank', 'credit services', 'mortgage finance', 'consumer finance',
  'housing finance', 'financial conglomerates', 'micro finance', 'nbfc', 'thrift',
];

// A broker, an AMC, an insurer or an exchange is "Financial Services" but is NOT a lender: it
// keeps the capital-employed logic, with only the leverage red-alert relaxed.
const NON_LENDER_FIN = [
  'capital markets', 'asset management', 'insurance',
  'financial data & stock exchanges', 'shell companies',
  'closed-end fund', 'exchange traded fund',
];

const FIN_SECTORS = ['financial services', 'financial', 'financials', 'banking'];

// ── Leverage comfort bands ──────────────────────────────────────────────────
// Expressed as net-worth-to-total-assets, the way a regulator looks at it (Basel Tier-1 for a
// bank, "net owned funds" for an NBFC), which avoids arguing about whether 7× or 9× leverage is
// "too much" for one particular lender.
const CAPITAL_BANDS = {
  bank: { ok: 6, warn: 5 },
  nbfc: { ok: 10, warn: 8 },
};

export const ROA_OK = 1.0;
export const LENDER_GROWTH_MIN = 15;
export const LENDER_PEG_MAX = 1.2;
export const LENDER_ROE_MIN = 15;

export const CAPITAL_BANDS_EXPORT = CAPITAL_BANDS;

// ── The lender Screener.in query ────────────────────────────────────────────
// Screener.in exposes "Return on assets", so a lender basket CAN be screened — but it has no
// public Gross/Net NPA filter. NPA is a per-stock check, never a silent filter.
export const LENDER_QUERY = [
  'Market Capitalization > 500',
  'AND Sales growth 3Years > 15',
  'AND Sales growth 5Years > 15',
  'AND Profit growth 3Years > 15',
  'AND Profit growth 5Years > 15',
  'AND Sales growth > 15',
  'AND Profit growth > 15',
  'AND PEG Ratio > 0',
  'AND PEG Ratio < 1.2',
  'AND Return on equity > 15',
  'AND Return on assets > 1',
  'AND Pledged percentage = 0',
].join('\n');

export const LENDER_QUERY_NOTE =
  'Screener.in has no public Gross/Net NPA filter, so NPA is NOT part of this query. Open each ' +
  'name’s page for Gross NPA %, Net NPA % and CAR, then type them into the score card’s NPA box. ' +
  'The ranking never drops a lender just because NPA is missing — it labels the line “not in ' +
  'scan” and scores that single line 0.';

// ── Field aliases ───────────────────────────────────────────────────────────
const F = {
  sector: ['Sector', 'sector'],
  industry: ['Industry', 'industry'],
  mcap: ['Market Cap (Cr)', 'mcap', 'market_cap_cr'],
  pe: ['PE', 'pe'],
  peg: ['PEG Ratio', 'peg', 'peg_ratio'],
  reserves: ['Reserves', 'reserves'],
  de: ['Debt/Equity', 'debt_to_equity'],
  sales3y: ['Sales CAGR 3Y', 'sales_cagr_3y'],
  sales5y: ['Sales CAGR 5Y', 'sales_cagr_5y'],
  profit3y: ['Profit CAGR 3Y', 'profit_cagr_3y'],
  profit5y: ['Profit CAGR 5Y', 'profit_cagr_5y'],
  salesGrowth: ['Sales Growth', 'sales_growth'],
  profitGrowth: ['Profit Growth', 'profit_growth'],
  pledged: ['Pledged %', 'pledged_percent'],
  promoter: ['Promoter %', 'promoter_share'],
  netWorth: ['Net Worth (Cr)', 'net_worth_cr'],
  borrowings: ['Borrowings (Cr)', 'borrowings_cr'],
  deposits: ['Deposits (Cr)', 'deposits_cr'],
  totalAssets: ['Total Assets (Cr)', 'total_assets_cr'],
  financingMargin: ['Financing Margin %', 'financing_margin_pct'],
  patCr: ['PAT (Cr)', 'pat_cr'],
  gnpa: ['Gross NPA %', 'gnpa_pct', 'gnpa'],
  nnpa: ['Net NPA %', 'nnpa_pct', 'nnpa'],
  pcr: ['Provision Coverage %', 'pcr_pct', 'pcr'],
  car: ['Capital Adequacy %', 'car_pct', 'car'],
};

function num(stock, keys) {
  for (const k of keys) {
    const v = stock?.[k];
    if (v === undefined || v === null || v === '') continue;
    const n = typeof v === 'number' ? v : parseFloat(String(v).replace(/[,%₹]/g, ''));
    if (Number.isFinite(n)) return n;
  }
  return null;
}

const r = (x, n = 2) => (x === null || x === undefined ? null : Math.round(x * 10 ** n) / 10 ** n);

// ── CLASSIFICATION ──────────────────────────────────────────────────────────
export function lenderKind(stock) {
  const sector = String(stock?.['Sector'] || stock?.['sector'] || '').trim().toLowerCase();
  const industry = String(stock?.['Industry'] || stock?.['industry'] || '').trim().toLowerCase();
  if (!sector && !industry) return null;
  if (NON_LENDER_FIN.includes(industry)) return null;
  const isFinSector = FIN_SECTORS.includes(sector) || sector.includes('financ') || sector.includes('bank');
  if (!isFinSector) return null;
  if (industry.includes('bank')) return 'bank';
  return LENDER_MARKERS.some((m) => industry.includes(m)) ? 'nbfc' : null;
}

export const isLender = (stock) => lenderKind(stock) !== null;

// Broader than isLender: brokers, AMCs and insurers too. They are not judged on NPA, but their
// leverage is part of doing business rather than a red flag.
export function isFinancial(stock) {
  const sector = String(stock?.['Sector'] || stock?.['sector'] || '').trim().toLowerCase();
  return isLender(stock) || FIN_SECTORS.includes(sector) || sector.includes('financ');
}

// ── METRICS ─────────────────────────────────────────────────────────────────
// Manual lender facts typed into the score card → the column names this module reads.
export const LENDER_FACT_KEYS = {
  gnpa: 'Gross NPA %',
  nnpa: 'Net NPA %',
  pcr: 'Provision Coverage %',
  car: 'Capital Adequacy %',
};

export function lenderMetrics(stock, opts = {}) {
  const kind = lenderKind(stock) || 'nbfc';
  const band = CAPITAL_BANDS[kind];

  const sales3y = num(stock, F.sales3y);
  const sales5y = num(stock, F.sales5y);
  const profit3y = num(stock, F.profit3y);
  const profit5y = num(stock, F.profit5y);
  const peg = num(stock, F.peg);
  const pledged = num(stock, F.pledged);
  const promoter = num(stock, F.promoter);

  let mcap = opts.mcap !== undefined && opts.mcap !== null ? Number(opts.mcap) : num(stock, F.mcap);
  if (!Number.isFinite(mcap)) mcap = null;
  let pe = opts.pe !== undefined && opts.pe !== null ? Number(opts.pe) : num(stock, F.pe);
  if (!Number.isFinite(pe)) pe = null;

  // ── earnings: PAT in ₹ Cr ──
  let patCr = opts.patCr !== undefined && opts.patCr !== null ? Number(opts.patCr) : null;
  if (!Number.isFinite(patCr)) patCr = null;
  const patExact = num(stock, F.patCr) !== null;
  if (patCr === null) {
    patCr = num(stock, F.patCr);
    if (patCr === null && mcap !== null && pe !== null && pe > 0) patCr = mcap / pe;
  }
  const patSrc = patExact ? 'exact' : patCr !== null ? 'estimate' : 'unknown';

  // yfinance reports debtToEquity sometimes as a ratio (0.45), sometimes as a percent (45.0),
  // and returns exactly 0 for most banks — which means "not published", never "no borrowings".
  const deRaw = num(stock, F.de);
  const de = deRaw === null || deRaw === 0 ? null : deRaw > 5 ? deRaw / 100 : deRaw;

  // ── net worth ──
  // UNIT NOTE: the scan stores yfinance `reserves` in ABSOLUTE RUPEES while every money column
  // here is ₹ Cr. Anything above ₹50 lakh crore is certainly rupees, so convert rather than
  // report a net worth 10⁷× too large.
  let netWorth = num(stock, F.netWorth);
  let reserves = num(stock, F.reserves);
  if (netWorth !== null && netWorth > 5e6) netWorth /= 1e7;
  if (reserves !== null && reserves > 5e6) reserves /= 1e7;

  let netWorthSrc;
  if (netWorth !== null && netWorth > 0) netWorthSrc = 'exact';
  else if (reserves !== null && reserves > 0) { netWorth = reserves; netWorthSrc = 'estimate'; }
  else { netWorth = null; netWorthSrc = 'unknown'; }

  // Self-check: a bank or NBFC never trades at 2% of book. If the equity we derived would imply
  // P/B < 0.02 the inputs are in the wrong units — report "unknown" rather than a fake ratio.
  const mcapCheck = mcap !== null ? mcap : num(stock, F.mcap);
  if (netWorth !== null && mcapCheck && netWorth > mcapCheck * 50) {
    netWorth = null; netWorthSrc = 'unknown';
  }

  // ── borrowings ──
  let borrowings = num(stock, F.borrowings);
  if (borrowings !== null && borrowings > 5e6) borrowings /= 1e7;
  let borrowingsSrc;
  if (borrowings !== null && borrowings > 0) borrowingsSrc = 'exact';
  else if (netWorth !== null && de !== null && netWorth * de > 0) { borrowings = netWorth * de; borrowingsSrc = 'estimate'; }
  else { borrowings = null; borrowingsSrc = 'unknown'; }

  let deposits = num(stock, F.deposits);
  if (deposits !== null && deposits > 5e6) deposits /= 1e7;

  // ── total assets ──
  let totalAssets = num(stock, F.totalAssets);
  if (totalAssets !== null && totalAssets > 5e6) totalAssets /= 1e7;
  let assetsSrc;
  if (totalAssets !== null && totalAssets > 0) assetsSrc = 'exact';
  else {
    const funding = (borrowings || 0) + (deposits || 0);
    if (netWorth !== null && funding > 0) { totalAssets = netWorth + funding; assetsSrc = 'estimate'; }
    else { totalAssets = null; assetsSrc = 'unknown'; }
  }

  const roa = patCr !== null && totalAssets ? (patCr / totalAssets) * 100 : null;
  const roe = patCr !== null && netWorth ? (patCr / netWorth) * 100 : null;
  const capitalPct = netWorth !== null && totalAssets ? (netWorth / totalAssets) * 100 : null;
  const leverageX = borrowings && netWorth ? borrowings / netWorth : null;
  const fundingX = netWorth && (borrowings || deposits) ? ((borrowings || 0) + (deposits || 0)) / netWorth : null;
  const pb = mcap && netWorth ? mcap / netWorth : null;

  // Screener.in's "Financing Margin %" is Financing Profit ÷ Revenue. On its BANK template the
  // Interest row is treated as an expense while interest income already sits in Revenue, so the
  // figure comes out negative for perfectly healthy banks (HDFCBANK reports -10%). It is reliable
  // for NBFCs (CHOLAFIN 23%, MUTHOOTFIN 46%) and useless for banks, so it is dropped for banks
  // rather than allowed to raise a false "thin margin" flag.
  const financingMargin = kind === 'bank' ? null : num(stock, F.financingMargin);
  const gnpa = num(stock, F.gnpa);
  const nnpa = num(stock, F.nnpa);
  const pcr = num(stock, F.pcr);
  const car = num(stock, F.car);

  return {
    kind,
    kindLabel: kind === 'bank' ? 'Bank' : 'NBFC / Housing finance',
    capitalOk: band.ok,
    capitalWarn: band.warn,

    sales3y, sales5y, profit3y, profit5y,
    salesGrowth: num(stock, F.salesGrowth),
    profitGrowth: num(stock, F.profitGrowth),
    peg, mcap, pe, pledged, promoter,

    netWorthCr: r(netWorth, 1),
    borrowingsCr: r(borrowings, 1),
    depositsCr: r(deposits, 1),
    totalAssetsCr: r(totalAssets, 1),
    patCr: r(patCr, 1),
    deRatio: r(de, 2),

    roa: r(roa, 1),
    roe: r(roe, 1),
    capitalPct: r(capitalPct, 1),
    leverageX: r(leverageX, 2),
    fundingX: r(fundingX, 2),
    pb: r(pb, 2),
    financingMargin,

    gnpa, nnpa, pcr, car,

    // A ratio is only "exact" when BOTH inputs are exact — a ROE built on the yfinance
    // retained-earnings proxy is an estimate and must say so.
    source: {
      pat: patSrc,
      netWorth: netWorthSrc,
      borrowings: borrowingsSrc,
      totalAssets: assetsSrc,
      roa: patCr === null || totalAssets === null ? 'unknown' : patSrc === 'exact' && assetsSrc === 'exact' ? 'exact' : 'estimate',
      roe: patCr === null || netWorth === null ? 'unknown' : patSrc === 'exact' && netWorthSrc === 'exact' ? 'exact' : 'estimate',
      capital: capitalPct === null ? 'unknown' : netWorthSrc === 'exact' && assetsSrc === 'exact' ? 'exact' : 'estimate',
      financingMargin: financingMargin !== null ? 'exact' : 'unknown',
      npa: gnpa !== null ? 'exact' : 'unknown',
      car: car !== null ? 'exact' : 'unknown',
    },
  };
}

// ── QUALITY /20 for a lender ────────────────────────────────────────────────
// Same 20 marks and the same ✅/❌/➖ shape as the ordinary rubric, so the score card needs no
// second renderer — only the six lines change.
export function lenderQualityItems(m) {
  const items = [];

  // 1) ROA — 5 marks (was "ROCE > 20%")
  items.push({
    key: 'roa', label: `Return on Assets > ${ROA_OK.toFixed(0)}%`, max: 5,
    value: m.roa, valueText: m.roa === null ? 'n/a' : `${m.roa}%`,
    points: m.roa !== null && m.roa > ROA_OK ? 5 : 0,
    status: m.roa === null ? 'unknown' : m.roa > ROA_OK ? 'pass' : 'fail',
    source: m.source.roa,
    note: m.roa === null
      ? 'Total assets not in scan — ROA cannot be computed.'
      : `ROA ${m.roa}% on assets of ₹${Math.round(m.totalAssetsCr).toLocaleString('en-IN')}Cr.`,
  });

  // 2) ROE — 4 marks
  items.push({
    key: 'roe', label: 'Return on equity > 15%', max: 4,
    value: m.roe, valueText: m.roe === null ? 'n/a' : `${m.roe}%`,
    points: m.roe !== null && m.roe > 15 ? 4 : 0,
    status: m.roe === null ? 'unknown' : m.roe > 15 ? 'pass' : 'fail',
    source: m.source.roe,
    note: m.source.netWorth === 'exact'
      ? 'PAT ÷ net worth (equity capital + reserves).'
      : 'Net worth estimated from reserves — verify on Screener.in.',
  });

  // 3) Capital cushion — 2 marks (was "Debt/Equity < 0.5")
  items.push({
    key: 'capital', label: `Net worth ≥ ${m.capitalOk}% of assets (${m.kindLabel} norm)`, max: 2,
    value: m.capitalPct, valueText: m.capitalPct === null ? 'n/a' : `${m.capitalPct}% of assets`,
    points: m.capitalPct !== null && m.capitalPct >= m.capitalOk ? 2 : 0,
    status: m.capitalPct === null ? 'unknown' : m.capitalPct >= m.capitalOk ? 'pass' : 'fail',
    source: m.source.capital,
    note: 'Replaces Debt/Equity < 0.5 — borrowing is a lender’s raw material, so this checks the '
        + 'capital cushion instead.' + (m.fundingX ? ` Funding ${m.fundingX}× net worth.` : ''),
  });

  // 4) Asset quality — 4 marks (was "positive / healthy cash flow")
  let npaPass, npaText, npaStatus;
  if (m.gnpa === null && m.nnpa === null) {
    npaPass = false; npaText = 'not in scan'; npaStatus = 'unknown';
  } else {
    npaPass = (m.gnpa === null || m.gnpa < 3.0) && (m.nnpa === null || m.nnpa < 1.5);
    npaText = [m.gnpa !== null ? `GNPA ${m.gnpa}%` : null, m.nnpa !== null ? `NNPA ${m.nnpa}%` : null]
      .filter(Boolean).join(' · ');
    npaStatus = npaPass ? 'pass' : 'fail';
  }
  items.push({
    key: 'npa', label: 'Gross NPA < 3% and Net NPA < 1.5%', max: 4,
    value: m.gnpa, valueText: npaText,
    points: npaPass ? 4 : 0,
    status: npaStatus,
    source: m.source.npa,
    note: 'THE number for a lender — the equivalent of asking a manufacturer whether its cash '
        + 'flow is real. Screener.in blanks it behind a login; type it into the NPA box to switch '
        + 'this line on.',
  });

  // 5) Buffers — 3 marks (was "CFO reasonably tracks PAT")
  let bufPass, bufText, bufStatus;
  if (m.pcr === null && m.car === null) {
    bufPass = false; bufText = 'not in scan'; bufStatus = 'unknown';
  } else {
    bufPass = (m.pcr !== null && m.pcr >= 70) || (m.car !== null && m.car >= 15);
    bufText = [m.pcr !== null ? `PCR ${m.pcr}%` : null, m.car !== null ? `CAR ${m.car}%` : null]
      .filter(Boolean).join(' · ');
    bufStatus = bufPass ? 'pass' : 'fail';
  }
  items.push({
    key: 'buffer', label: 'Provision coverage ≥ 70% or CAR ≥ 15%', max: 3,
    valueText: bufText,
    points: bufPass ? 3 : 0,
    status: bufStatus,
    source: m.source.car,
    note: 'A cushion is what lets a lender absorb a bad year without a rights issue.',
  });

  // 6) Promoter pledge = 0 — 2 marks (unchanged)
  const pledgePass = m.pledged === 0;
  items.push({
    key: 'pledge', label: 'Promoter pledge = 0', max: 2,
    valueText: m.pledged !== null ? `${m.pledged}%` : 'not in scan',
    points: pledgePass ? 2 : 0,
    status: pledgePass ? 'pass' : 'unknown',
    source: m.pledged !== null ? 'exact' : 'unknown',
    note: m.pledged !== null ? '' : 'Pledge % not in this scan — confirm on Screener.in.',
  });

  return items;
}

// ── RED FLAGS for a lender ──────────────────────────────────────────────────
export function lenderFlags(m) {
  const out = [];
  if (m.roa !== null && m.roa < 0.6) out.push(`Weak return on assets (${m.roa}%) — thin cover for credit cost`);
  if (m.roe !== null && m.roe < 10) out.push(`ROE ${m.roe}% is below the cost of equity for a lender`);
  if (m.capitalPct !== null && m.capitalPct < m.capitalWarn) {
    out.push(`Thin capital cushion (net worth ${m.capitalPct}% of assets) — watch for dilution`);
  }
  if (m.gnpa !== null && m.gnpa > 5) out.push(`Elevated Gross NPA (${m.gnpa}%) — asset-quality stress`);
  if (m.nnpa !== null && m.nnpa > 2) out.push(`Elevated Net NPA (${m.nnpa}%)`);
  if (m.car !== null && m.car < 12) out.push(`Capital adequacy ${m.car}% is below the regulatory comfort line`);
  if (m.pcr !== null && m.pcr < 60) out.push(`Low provision coverage (${m.pcr}%) — little cushion against slippage`);
  if (m.financingMargin !== null && m.financingMargin < 2) {
    out.push(`Thin financing margin (${m.financingMargin}%) — no room for a credit-cost cycle`);
  }
  return out;
}

// ── LAYER-1 FILTER for a lender ─────────────────────────────────────────────
// `tier` mirrors the standard baskets so a chip means the same thing for a lender:
//   elite      → "exceptional": >20% growth, PEG < 0.8, ROA > 1.2%, ROE > 18%
//   hybrid     → the wider opportunity set: >15% growth, PEG < 1.2, ROA > 1%, ROE > 15%
//   financials → the lender basket proper
export const LENDER_TIERS = {
  elite: { growth: 20, peg: 0.8, roa: 1.2, roe: 18 },
  hybrid: { growth: 15, peg: 1.2, roa: 1.0, roe: 15 },
  financials: { growth: 15, peg: 1.2, roa: 1.0, roe: 15 },
};

export function applyLenderScreen(m, tier = 'hybrid') {
  const t = LENDER_TIERS[tier] || LENDER_TIERS.hybrid;
  const gt = (key, threshold) => m[key] !== null && m[key] !== undefined && m[key] > threshold;

  const criteria = [
    { label: `Sales growth 3Y > ${t.growth}%`, value: m.sales3y, ok: gt('sales3y', t.growth), required: true },
    { label: `Sales growth 5Y > ${t.growth}%`, value: m.sales5y, ok: gt('sales5y', t.growth), required: true },
    { label: `Profit growth 3Y > ${t.growth}%`, value: m.profit3y, ok: gt('profit3y', t.growth), required: true },
    { label: `Profit growth 5Y > ${t.growth}%`, value: m.profit5y, ok: gt('profit5y', t.growth), required: true },
    { label: `PEG between 0 and ${t.peg}`, value: m.peg, ok: m.peg !== null && m.peg > 0 && m.peg < t.peg, required: true },
    { label: `Latest sales growth > ${t.growth}%`, value: m.salesGrowth, ok: gt('salesGrowth', t.growth), required: false },
    { label: `Latest profit growth > ${t.growth}%`, value: m.profitGrowth, ok: gt('profitGrowth', t.growth), required: false },
    { label: `ROA > ${t.roa}%`, value: m.roa, ok: gt('roa', t.roa), required: false },
    { label: `ROE > ${t.roe}%`, value: m.roe, ok: gt('roe', t.roe), required: false },
    { label: `Net worth ≥ ${m.capitalOk}% of assets`, value: m.capitalPct, ok: m.capitalPct !== null && m.capitalPct >= m.capitalOk, required: false },
    { label: 'Gross NPA < 3%', value: m.gnpa, ok: m.gnpa !== null && m.gnpa < 3.0, required: false },
    { label: 'Promoter pledge = 0%', value: m.pledged, ok: m.pledged === 0, required: false },
  ];

  let pass = true;
  const failed = [];
  const unverified = [];
  for (const c of criteria) {
    if (c.value === null || c.value === undefined) {
      if (c.required) { pass = false; failed.push(`${c.label} — data missing`); }
      else unverified.push(c.label);
      continue;
    }
    if (!c.ok) { pass = false; failed.push(c.label); }
  }
  return { pass, unverified, failed, rubric: 'lender' };
}

"""
financial_engine.py — LENDER-AWARE ANALYTICS (Banks · NBFC · Housing Finance)

WHY THIS FILE EXISTS
--------------------
A lender is not a manufacturer, and the Peter Lynch 100-point rubric was written for
manufacturers. When a bank or an NBFC is fed through that rubric two things go wrong:

  1. `Debt/Equity < 0.5` and `ROCE > 15%` are impossible for a lender.
     Borrowing IS the raw material of a lender — CHOLAFIN runs at D/E ≈ 6.9, HDFCBANK at
     roughly 12x assets/net-worth. ROCE ("return on capital employed") is meaningless when
     the "capital employed" is a loan book funded by deposits and borrowings. So the
     ordinary rubric scores a perfectly good NBFC 0/20 on Quality and Layer-1 then throws
     it out of the scan entirely — which is exactly how CHOLAFIN got "missed".

  2. `score_stock()` in scoring_engine.py raises a RED ALERT when D/E > 2.0.
     Every NBFC in India trips that wire. A company with a ~19% ROE, 2.3% ROA and 12% net
     worth/assets was being flagged as a red alert purely for doing its job.

WHAT A LENDER IS JUDGED ON INSTEAD
----------------------------------
    ROCE                 →  ROA (Return on Assets)        — 1.0%+ is respectable
    Debt/Equity < 0.5    →  Net worth / total assets      — the capital cushion
    Operating cash flow  →  Financing margin (NIM proxy)  — the earnings engine
    (nothing)            →  Gross NPA / Net NPA / PCR/CAR — asset quality
    (nothing)            →  P/B for the valuation read    — leverage amplifies ROE

DATA SOURCES — exact vs estimate vs unknown
-------------------------------------------
Same honesty rule as lynch_engine.py: every value reports a `source`.

    exact     — read from the balance sheet / P&L. `screeners_scraper.py` now pulls
                Equity Capital, Reserves, Deposits, Borrowing, Total Assets and
                Financing Margin % off lender pages for free.
    estimate  — derived from fields the scan already had (Net worth ≈ Reserves,
                PAT ≈ Market Cap ÷ PE, Borrowings ≈ Reserves × D/E).
    unknown   — not present. Scores 0 and is NEVER invented, so the UI can say
                "confirm on Screener.in" instead of printing a made-up number.

NPA IS DELIBERATELY `unknown` BY DEFAULT
----------------------------------------
Screener.in prints the "Gross NPA %" / "Net NPA %" / "Capital Adequacy Ratio" ROWS on a
lender page but BLANKS THE VALUES behind a login wall. We will not guess them. The score
card therefore accepts a MANUAL NPA entry (the same mechanism as the Story overrides) —
which is the lens the fund manager asked for by name. Until it is filled in, the line reads
"not in scan · verify on Screener.in" and scores 0, and the stock is still RANKED rather
than silently dropped from the scan.
"""

from __future__ import annotations

# ── Which industries are lenders ────────────────────────────────────────────
LENDER_INDUSTRY_MARKERS = [
    "bank",
    "credit services",
    "mortgage finance",
    "consumer finance",
    "housing finance",
    "financial conglomerates",
    "micro finance",
    "nbfc",
    "thrift",
]

# A broker, an AMC, an insurer or an exchange is "Financial Services" but is NOT a lender:
# it keeps the capital-employed logic, with only the leverage red-alert relaxed.
NON_LENDER_FIN_INDUSTRIES = [
    "capital markets",
    "asset management",
    "insurance",
    "financial data & stock exchanges",
    "shell companies",
    "closed-end fund",
    "exchange traded fund",
]

FINANCIAL_SECTOR_NAMES = ("financial services", "financial", "financials", "banking")

# ── Leverage comfort bands ──────────────────────────────────────────────────
# Expressed as net-worth-to-total-assets, the way a regulator looks at it (Basel Tier-1
# for a bank, "net owned funds" for an NBFC). This avoids arguing about whether 7× or 9×
# leverage is "too much" for one particular lender.
#
#   NBFC : net worth ≥ 10% of assets → comfortable;  < 8% → flag
#   Bank : net worth ≥  6% of assets → comfortable;  < 5% → flag
CAPITAL_BANDS = {
    "bank": {"ok": 6.0, "warn": 5.0},
    "nbfc": {"ok": 10.0, "warn": 8.0},
}

ROA_OK = 1.0          # Return on assets that counts as "good" for a lender
LENDER_GROWTH_MIN = 15.0
LENDER_PEG_MAX = 1.2
LENDER_ROE_MIN = 15.0


# ── The lender Screener.in query ────────────────────────────────────────────
# Screener.in exposes "Return on assets", so a lender basket CAN be screened — but it does
# NOT expose Gross/Net NPA as a screenable field on the public plan. NPA is therefore a
# per-stock check (or a manual entry on the score card), never a silent filter.
LENDER_QUERY = "\n".join([
    "Market Capitalization > 500",
    "AND Sales growth 3Years > 15",
    "AND Sales growth 5Years > 15",
    "AND Profit growth 3Years > 15",
    "AND Profit growth 5Years > 15",
    "AND Sales growth > 15",
    "AND Profit growth > 15",
    "AND PEG Ratio > 0",
    "AND PEG Ratio < 1.2",
    "AND Return on equity > 15",
    "AND Return on assets > 1",
    "AND Pledged percentage = 0",
])

LENDER_QUERY_NOTE = (
    "Screener.in has no public Gross/Net NPA filter, so NPA is NOT part of this query. "
    "Open each name's page for Gross NPA %, Net NPA % and CAR, then type them into the score "
    "card's NPA box. The ranking never drops a lender just because NPA is missing — it labels "
    "the line “not in scan” and scores that single line 0."
)

# ── Field aliases (new screener fields + values that may already be in the scan) ──
FIELDS = {
    "symbol": ["symbol", "Ticker", "ticker", "Symbol"],
    "sector": ["Sector", "sector"],
    "industry": ["Industry", "industry"],
    "mcap": ["Market Cap (Cr)", "mcap", "market_cap_cr"],
    "pe": ["PE", "pe"],
    "peg": ["PEG Ratio", "peg", "peg_ratio"],
    "reserves": ["Reserves", "reserves"],
    "de": ["Debt/Equity", "debt_to_equity"],
    "sales3y": ["Sales CAGR 3Y", "sales_cagr_3y"],
    "sales5y": ["Sales CAGR 5Y", "sales_cagr_5y"],
    "profit3y": ["Profit CAGR 3Y", "profit_cagr_3y"],
    "profit5y": ["Profit CAGR 5Y", "profit_cagr_5y"],
    "salesGrowth": ["Sales Growth", "sales_growth"],
    "profitGrowth": ["Profit Growth", "profit_growth"],
    "pledged": ["Pledged %", "pledged_percent"],
    "promoter": ["Promoter %", "promoter_share"],
    # exact lender fields written by data_fetcher.py / screeners_scraper.py
    "netWorth": ["Net Worth (Cr)", "net_worth_cr"],
    "borrowings": ["Borrowings (Cr)", "borrowings_cr"],
    "deposits": ["Deposits (Cr)", "deposits_cr"],
    "totalAssets": ["Total Assets (Cr)", "total_assets_cr"],
    "financingMargin": ["Financing Margin %", "financing_margin_pct"],
    "patCr": ["PAT (Cr)", "pat_cr"],
    # asset quality — login-walled on screener.in, so normally filled in by hand
    "gnpa": ["Gross NPA %", "gnpa_pct", "gnpa"],
    "nnpa": ["Net NPA %", "nnpa_pct", "nnpa"],
    "pcr": ["Provision Coverage %", "pcr_pct", "pcr"],
    "car": ["Capital Adequacy %", "car_pct", "car"],
}


def _num(stock, keys):
    """First readable number for any of `keys`, else None. Mirrors lynch_engine._num."""
    for k in keys:
        if k not in stock:
            continue
        v = stock[k]
        if v is None or v == "":
            continue
        if isinstance(v, str):
            v = v.replace(",", "").replace("%", "").replace("₹", "").strip()
            if v == "":
                continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if f != f:                      # NaN
            continue
        return f
    return None


def _r(x, n=2):
    return None if x is None else round(x, n)


def _safe_float(v):
    """Coerce a caller-supplied value that may be a string ('N/A', '-', '28.4') or None."""
    if v is None:
        return None
    if isinstance(v, str):
        v = v.replace(",", "").replace("%", "").strip()
        if v in ("", "-", "--", "N/A", "None"):
            return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f           # NaN


def symbol_of(stock) -> str:
    raw = str(stock.get("symbol") or stock.get("Ticker") or stock.get("ticker") or "").upper()
    return raw[:-3] if raw.endswith((".NS", ".BO")) else raw


# ── CLASSIFICATION ──────────────────────────────────────────────────────────
def lender_kind(stock):
    """'bank' | 'nbfc' | None — the sort of lender this record is (None = not a lender)."""
    sector = str(stock.get("Sector") or stock.get("sector") or "").strip().lower()
    industry = str(stock.get("Industry") or stock.get("industry") or "").strip().lower()
    if not sector and not industry:
        return None
    if industry in NON_LENDER_FIN_INDUSTRIES:
        return None
    if not (sector in FINANCIAL_SECTOR_NAMES or "financ" in sector or "bank" in sector):
        return None
    if "bank" in industry:
        return "bank"
    for marker in LENDER_INDUSTRY_MARKERS:
        if marker in industry:
            return "nbfc"
    return None


def is_lender(stock) -> bool:
    return lender_kind(stock) is not None


def is_financial(stock) -> bool:
    """Broader than is_lender: brokers, AMCs and insurers too. They are not judged on NPA,
    but their leverage is part of doing business rather than a red flag."""
    sector = str(stock.get("Sector") or stock.get("sector") or "").strip().lower()
    return is_lender(stock) or sector in FINANCIAL_SECTOR_NAMES or "financ" in sector


# ── METRICS ─────────────────────────────────────────────────────────────────
def lender_metrics(stock, pat_cr=None, mcap=None, pe=None) -> dict:
    """Normalise one record into everything a lender is judged on.

    Self-contained on purpose: it carries the growth/valuation pass-through values as well
    as the lender-specific ratios, so `apply_lender_screen` and the Quality bucket need no
    second lookup. Callers may pass an already-computed PAT / mcap / PE so lynch_engine and
    scoring_engine agree to the rupee.
    """
    kind = lender_kind(stock) or "nbfc"
    band = CAPITAL_BANDS[kind]

    # ── pass-through growth / valuation ──
    sales3y = _num(stock, FIELDS["sales3y"])
    sales5y = _num(stock, FIELDS["sales5y"])
    profit3y = _num(stock, FIELDS["profit3y"])
    profit5y = _num(stock, FIELDS["profit5y"])
    peg = _num(stock, FIELDS["peg"])
    pledged = _num(stock, FIELDS["pledged"])
    promoter = _num(stock, FIELDS["promoter"])

    mcap = _safe_float(mcap)
    if mcap is None:
        mcap = _num(stock, FIELDS["mcap"])
    pe = _safe_float(pe)
    if pe is None:
        pe = _num(stock, FIELDS["pe"])
    pat_cr = _safe_float(pat_cr)
    if pat_cr is None:
        pat_cr = _num(stock, FIELDS["patCr"])
        if pat_cr is None and mcap is not None and pe is not None and pe > 0:
            pat_cr = mcap / pe
    pat_src = "exact" if _num(stock, FIELDS["patCr"]) is not None else ("estimate" if pat_cr is not None else "unknown")

    de_raw = _num(stock, FIELDS["de"])
    # yfinance reports debtToEquity sometimes as a ratio (0.45) and sometimes as a percent
    # (45.0). It also returns exactly 0 for most banks, which means "not published" — never
    # treat that as "a lender with no borrowings".
    if de_raw is None or de_raw == 0:
        de = None
    else:
        de = de_raw / 100.0 if de_raw > 5 else de_raw

    # Net worth: exact balance sheet (Equity Capital + Reserves) → else Reserves (proxy).
    #
    # UNIT NOTE: the scan cache stores yfinance `reserves` in ABSOLUTE RUPEES, while every
    # other money column here is ₹ Cr. `net_worth_cr` from the screener scraper is already
    # in crores. Anything above ₹50 lakh crore is certainly absolute rupees, so convert it
    # rather than produce a net worth that is 10⁷× too large.
    net_worth = _num(stock, FIELDS["netWorth"])
    reserves = _num(stock, FIELDS["reserves"])
    if net_worth is not None and net_worth > 5e6:
        net_worth = net_worth / 1e7
    if reserves is not None and reserves > 5e6:
        reserves = reserves / 1e7
    if net_worth is not None and net_worth > 0:
        net_worth_src = "exact"
    elif reserves is not None and reserves > 0:
        net_worth, net_worth_src = reserves, "estimate"
    else:
        net_worth, net_worth_src = None, "unknown"

    mcap_check = mcap if mcap is not None else _num(stock, FIELDS["mcap"])
    # Self-check: a bank or NBFC never trades at 2% of book. If the equity we derived would
    # imply P/B < 0.02 the input units are wrong, so report "unknown" instead of a fake ratio.
    if net_worth is not None and mcap_check and net_worth > mcap_check * 50:
        net_worth, net_worth_src = None, "unknown"

    # Borrowings: exact → else Net worth × D/E.
    borrowings = _num(stock, FIELDS["borrowings"])
    if borrowings is not None and borrowings > 5e6:
        borrowings = borrowings / 1e7
    if borrowings is not None and borrowings > 0:
        borrowings_src = "exact"
    elif net_worth is not None and de is not None and net_worth * de > 0:
        borrowings, borrowings_src = net_worth * de, "estimate"
    else:
        borrowings, borrowings_src = None, "unknown"

    deposits = _num(stock, FIELDS["deposits"])
    if deposits is not None and deposits > 5e6:
        deposits = deposits / 1e7

    total_assets = _num(stock, FIELDS["totalAssets"])
    if total_assets is not None and total_assets > 5e6:
        total_assets = total_assets / 1e7
    if total_assets is not None and total_assets > 0:
        assets_src = "exact"
    else:
        funding = (borrowings or 0) + (deposits or 0)
        if net_worth is not None and funding > 0:
            total_assets, assets_src = net_worth + funding, "estimate"
        else:
            total_assets, assets_src = None, "unknown"

    roa = (pat_cr / total_assets * 100.0) if (pat_cr is not None and total_assets) else None
    roe = (pat_cr / net_worth * 100.0) if (pat_cr is not None and net_worth) else None
    capital_pct = (net_worth / total_assets * 100.0) if (net_worth is not None and total_assets) else None
    leverage_x = (borrowings / net_worth) if (borrowings and net_worth) else None
    funding_x = (((borrowings or 0) + (deposits or 0)) / net_worth) if (net_worth and (borrowings or deposits)) else None
    pb = (mcap / net_worth) if (mcap and net_worth) else None

    financing_margin = _num(stock, FIELDS["financingMargin"])
    # Screener.in's "Financing Margin %" is computed as Financing Profit ÷ Revenue. On its BANK
    # template the Interest row is treated as an expense while interest income already sits in
    # Revenue, so the figure comes out negative for perfectly healthy banks (HDFCBANK reports
    # -10%). It is reliable for NBFCs (CHOLAFIN 23%, MUTHOOTFIN 46%) and useless for banks, so
    # it is dropped for banks rather than allowed to raise a false "thin margin" flag.
    if kind == "bank":
        financing_margin = None
    gnpa = _num(stock, FIELDS["gnpa"])
    nnpa = _num(stock, FIELDS["nnpa"])
    pcr = _num(stock, FIELDS["pcr"])
    car = _num(stock, FIELDS["car"])

    return {
        "kind": kind,
        "kindLabel": "Bank" if kind == "bank" else "NBFC / Housing finance",
        "capitalOk": band["ok"],
        "capitalWarn": band["warn"],

        # pass-through — so the lender screen is self-contained
        "sales3y": sales3y, "sales5y": sales5y,
        "profit3y": profit3y, "profit5y": profit5y,
        "salesGrowth": _num(stock, FIELDS["salesGrowth"]),
        "profitGrowth": _num(stock, FIELDS["profitGrowth"]),
        "peg": peg, "mcap": mcap, "pe": pe,
        "pledged": pledged, "promoter": promoter,

        # lender balance sheet
        "netWorthCr": _r(net_worth, 1),
        "borrowingsCr": _r(borrowings, 1),
        "depositsCr": _r(deposits, 1),
        "totalAssetsCr": _r(total_assets, 1),
        "patCr": _r(pat_cr, 1),
        "deRatio": _r(de, 2),

        # lender ratios
        "roa": _r(roa, 1),
        "roe": _r(roe, 1),
        "capitalPct": _r(capital_pct, 1),
        "leverageX": _r(leverage_x, 2),
        "fundingX": _r(funding_x, 2),
        "pb": _r(pb, 2),
        "financingMargin": financing_margin,

        # asset quality — login-walled on screener.in, so normally None until typed in
        "gnpa": gnpa, "nnpa": nnpa, "pcr": pcr, "car": car,

        "source": {
            "pat": pat_src,
            "netWorth": net_worth_src,
            "borrowings": borrowings_src,
            "totalAssets": assets_src,
            # A ratio is only "exact" when BOTH of its inputs are exact — a ROE built on the
            # yfinance retained-earnings proxy is an estimate and must say so.
            "roa": ("unknown" if (pat_cr is None or total_assets is None)
                    else "exact" if (pat_src == "exact" and assets_src == "exact") else "estimate"),
            "roe": ("unknown" if (pat_cr is None or net_worth is None)
                    else "exact" if (pat_src == "exact" and net_worth_src == "exact") else "estimate"),
            "capital": ("unknown" if capital_pct is None
                        else "exact" if (net_worth_src == "exact" and assets_src == "exact") else "estimate"),
            "financingMargin": "exact" if financing_margin is not None else "unknown",
            "npa": "exact" if gnpa is not None else "unknown",
            "car": "exact" if car is not None else "unknown",
        },
    }


# ── QUALITY /20 for a lender ────────────────────────────────────────────────
# Same 20 marks and the same ✅/❌/➖ shape as the ordinary rubric, so the score card UI
# needs no second renderer — only the six lines change.
def lender_quality_items(m) -> list:
    items = []

    # 1) ROA — 5 marks (was "ROCE > 20%")
    roa = m["roa"]
    items.append({
        "key": "roa", "label": f"Return on Assets > {ROA_OK:.0f}%", "max": 5,
        "value": roa, "valueText": f"{roa}%" if roa is not None else "n/a",
        "points": 5 if (roa is not None and roa > ROA_OK) else 0,
        "status": "unknown" if roa is None else ("pass" if roa > ROA_OK else "fail"),
        "source": m["source"]["roa"],
        "note": (f"ROA {roa}% on assets of ₹{m['totalAssetsCr']:,.0f}Cr."
                 if roa is not None else "Total assets not in scan — ROA cannot be computed."),
    })

    # 2) ROE — 4 marks
    roe = m["roe"]
    items.append({
        "key": "roe", "label": "Return on equity > 15%", "max": 4,
        "value": roe, "valueText": f"{roe}%" if roe is not None else "n/a",
        "points": 4 if (roe is not None and roe > 15) else 0,
        "status": "unknown" if roe is None else ("pass" if roe > 15 else "fail"),
        "source": m["source"]["roe"],
        "note": ("PAT ÷ net worth (equity capital + reserves)." if m["source"]["netWorth"] == "exact"
                 else "Net worth estimated from reserves — verify on Screener.in."),
    })

    # 3) Capital cushion — 2 marks (was "Debt/Equity < 0.5")
    cap, ok = m["capitalPct"], m["capitalOk"]
    items.append({
        "key": "capital", "label": f"Net worth ≥ {ok:.0f}% of assets ({m['kindLabel']} norm)", "max": 2,
        "value": cap, "valueText": f"{cap}% of assets" if cap is not None else "n/a",
        "points": 2 if (cap is not None and cap >= ok) else 0,
        "status": "unknown" if cap is None else ("pass" if cap >= ok else "fail"),
        "source": m["source"]["capital"],
        "note": ("Replaces Debt/Equity < 0.5 — borrowing is a lender's raw material, so this "
                 "checks the capital cushion instead."
                 + (f" Funding {m['fundingX']}× net worth." if m["fundingX"] else "")),
    })

    # 4) Asset quality — 4 marks (was "positive / healthy cash flow")
    gnpa, nnpa = m["gnpa"], m["nnpa"]
    if gnpa is None and nnpa is None:
        npa_pass, npa_text, npa_status = False, "not in scan", "unknown"
    else:
        npa_pass = (gnpa is None or gnpa < 3.0) and (nnpa is None or nnpa < 1.5)
        npa_text = " · ".join(t for t in [
            f"GNPA {gnpa}%" if gnpa is not None else None,
            f"NNPA {nnpa}%" if nnpa is not None else None,
        ] if t)
        npa_status = "pass" if npa_pass else "fail"
    items.append({
        "key": "npa", "label": "Gross NPA < 3% and Net NPA < 1.5%", "max": 4,
        "value": gnpa, "valueText": npa_text,
        "points": 4 if npa_pass else 0,
        "status": npa_status,
        "source": m["source"]["npa"],
        "note": ("THE number for a lender — the equivalent of asking a manufacturer whether its "
                 "cash flow is real. Screener.in blanks it behind a login; type it into the NPA "
                 "box (quarterly result / investor presentation) to switch this line on."),
    })

    # 5) Buffers — 3 marks (was "CFO reasonably tracks PAT")
    pcr, car = m["pcr"], m["car"]
    if pcr is None and car is None:
        buf_pass, buf_text, buf_status = False, "not in scan", "unknown"
    else:
        buf_pass = (pcr is not None and pcr >= 70) or (car is not None and car >= 15)
        buf_text = " · ".join(t for t in [
            f"PCR {pcr}%" if pcr is not None else None,
            f"CAR {car}%" if car is not None else None,
        ] if t)
        buf_status = "pass" if buf_pass else "fail"
    items.append({
        "key": "buffer", "label": "Provision coverage ≥ 70% or CAR ≥ 15%", "max": 3,
        "valueText": buf_text,
        "points": 3 if buf_pass else 0,
        "status": buf_status,
        "source": m["source"]["car"],
        "note": "A cushion is what lets a lender absorb a bad year without a rights issue.",
    })

    # 6) Promoter pledge = 0 — 2 marks (unchanged)
    pledged = m["pledged"]
    if pledged is not None:
        pledge_pass, pledge_text = pledged == 0, f"{pledged}%"
    else:
        pledge_pass, pledge_text = False, "not in scan"
    items.append({
        "key": "pledge", "label": "Promoter pledge = 0", "max": 2,
        "valueText": pledge_text,
        "points": 2 if pledge_pass else 0,
        "status": "pass" if pledge_pass else "unknown",
        "source": "exact" if pledged is not None else "unknown",
        "note": "" if pledged is not None else "Pledge % not in this scan — confirm on Screener.in.",
    })

    return items


# ── RED FLAGS for a lender ──────────────────────────────────────────────────
def lender_flags(m) -> list:
    out = []
    if m["roa"] is not None and m["roa"] < 0.6:
        out.append(f"Weak return on assets ({m['roa']}%) — thin cover for credit cost")
    if m["roe"] is not None and m["roe"] < 10:
        out.append(f"ROE {m['roe']}% is below the cost of equity for a lender")
    if m["capitalPct"] is not None and m["capitalPct"] < m["capitalWarn"]:
        out.append(f"Thin capital cushion (net worth {m['capitalPct']}% of assets) — watch for dilution")
    if m["gnpa"] is not None and m["gnpa"] > 5:
        out.append(f"Elevated Gross NPA ({m['gnpa']}%) — asset-quality stress")
    if m["nnpa"] is not None and m["nnpa"] > 2:
        out.append(f"Elevated Net NPA ({m['nnpa']}%)")
    if m["car"] is not None and m["car"] < 12:
        out.append(f"Capital adequacy {m['car']}% is below the regulatory comfort line")
    if m["pcr"] is not None and m["pcr"] < 60:
        out.append(f"Low provision coverage ({m['pcr']}%) — little cushion against slippage")
    if m["financingMargin"] is not None and m["financingMargin"] < 2:
        out.append(f"Thin financing margin ({m['financingMargin']:g}%) — no room for a credit-cost cycle")
    return out


# ── LAYER-1 FILTER for a lender ─────────────────────────────────────────────
# `tier` mirrors the standard baskets so the chips mean the same thing for a lender:
#   elite   → "exceptional": >20% growth, PEG < 0.8, ROA > 1.2%, ROE > 18%
#   hybrid  → the wider opportunity set: >15% growth, PEG < 1.2, ROA > 1%, ROE > 15%
LENDER_TIERS = {
    "elite": {"growth": 20.0, "peg": 0.8, "roa": 1.2, "roe": 18.0},
    "hybrid": {"growth": 15.0, "peg": 1.2, "roa": 1.0, "roe": 15.0},
    "financials": {"growth": 15.0, "peg": 1.2, "roa": 1.0, "roe": 15.0},
}


def apply_lender_screen(m, tier="hybrid") -> dict:
    """The lender version of the Lynch Layer-1 filter.

    Same growth and PEG spine as the standard baskets, but ROCE and Debt/Equity are replaced
    by ROA and the capital cushion — so a good NBFC can actually pass. NPA is checked ONLY
    when it is known; otherwise it is reported as unverified, never a silent rejection.
    """
    t = LENDER_TIERS.get(tier, LENDER_TIERS["hybrid"])
    g, peg_max, roa_min, roe_min = t["growth"], t["peg"], t["roa"], t["roe"]

    def gt(key, threshold):
        v = m.get(key)
        return v is not None and v > threshold

    criteria = [
        (f"Sales growth 3Y > {g:.0f}%", m.get("sales3y"), gt("sales3y", g), True),
        (f"Sales growth 5Y > {g:.0f}%", m.get("sales5y"), gt("sales5y", g), True),
        (f"Profit growth 3Y > {g:.0f}%", m.get("profit3y"), gt("profit3y", g), True),
        (f"Profit growth 5Y > {g:.0f}%", m.get("profit5y"), gt("profit5y", g), True),
        (f"PEG between 0 and {peg_max}", m.get("peg"),
         m.get("peg") is not None and 0 < m["peg"] < peg_max, True),
        (f"Latest sales growth > {g:.0f}%", m.get("salesGrowth"), gt("salesGrowth", g), False),
        (f"Latest profit growth > {g:.0f}%", m.get("profitGrowth"), gt("profitGrowth", g), False),
        (f"ROA > {roa_min}%", m.get("roa"), gt("roa", roa_min), False),
        (f"ROE > {roe_min:.0f}%", m.get("roe"), gt("roe", roe_min), False),
        (f"Net worth ≥ {m.get('capitalOk', 10):.0f}% of assets", m.get("capitalPct"),
         m.get("capitalPct") is not None and m["capitalPct"] >= (m.get("capitalOk") or 10), False),
        ("Gross NPA < 3%", m.get("gnpa"), m.get("gnpa") is not None and m["gnpa"] < 3.0, False),
        ("Promoter pledge = 0%", m.get("pledged"), m.get("pledged") == 0, False),
    ]

    passed, unverified, failed = True, [], []
    for label, value, ok, required in criteria:
        if value is None:
            if required:
                passed = False
                failed.append(f"{label} — data missing")
            else:
                unverified.append(label)
            continue
        if not ok:
            passed = False
            failed.append(label)
    return {"pass": passed, "unverified": unverified, "failed": failed, "rubric": "lender"}


if __name__ == "__main__":
    # Quick check on real lenders from the cached scan: python financial_engine.py CHOLAFIN
    import sys
    from data_fetcher import load_cached_scan_from_db

    cache = load_cached_scan_from_db()
    if not cache:
        print("No cached scan found — run a System Scan first.")
        raise SystemExit(1)

    targets = [t.upper() for t in sys.argv[1:]] or ["CHOLAFIN", "HDFCBANK", "BAJFINANCE", "AUBANK"]
    resolved = {symbol_of({"symbol": k}): v for k, v in cache.items()}
    for t in targets:
        rec = resolved.get(t)
        if not rec:
            print(f"\n{t}: not in the cached scan")
            continue
        if not is_lender(rec):
            print(f"\n{t}: not a lender (sector={rec.get('sector')}, industry={rec.get('industry')})")
            continue
        m = lender_metrics(rec)
        print(f"\n=== {t} · {m['kindLabel']} ===")
        for k in ("netWorthCr", "borrowingsCr", "depositsCr", "totalAssetsCr", "patCr",
                  "roa", "roe", "capitalPct", "leverageX", "fundingX", "pb",
                  "financingMargin", "gnpa", "nnpa", "car", "pcr", "peg"):
            print(f"  {k:<17} {m[k]}")
        print(f"  sources: {m['source']}")
        q = lender_quality_items(m)
        print(f"  quality: {sum(i['points'] for i in q)}/20")
        for i in q:
            print(f"    [{i['status']:<7}] {i['label']:<45} {i['points']:>4}   {i['valueText']}")
        sc = apply_lender_screen(m)
        print(f"  layer-1: pass={sc['pass']} failed={sc['failed']} unverified={sc['unverified']}")
        for f in lender_flags(m):
            print(f"  ⚠️  {f}")

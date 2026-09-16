"""
lynch_engine.py — DR GILL · PETER LYNCH 100-POINT SYSTEM (Python engine)

Faithful Python port of `frontend/src/lynch.js`, so the React dashboard and the Streamlit app
always produce the SAME score for the same stock.

    LAYER 1 — MACHINE FILTER   : Screener.in queries (Elite / Lynch Hybrid) → candidate pool
    LAYER 2 — 100-POINT RANKING: Growth /40 · Valuation /20 · Quality /20 · Lynch Story /20
    LAYER 3 — HUMAN RESEARCH   : read the annual report, then override the Story bucket by hand

Input: one dict per stock — either a raw scan-cache entry or a scored row from
`scoring_engine.run_scoring` (the page uses the latter, since it already carries
"Sales CAGR 3Y", "PEG Ratio", "Debt/Equity", "Reserves", "Promoter %", "Red Alert", "ROE %",
"ROCE %" and "CFO/PAT").

DATA HONESTY RULE
Every mark carries a `source`: "exact" (straight from the scan), "estimate" (derived from
Market Cap ÷ PE and Reserves), "unknown" (fixed at 0 — never invented) or "manual"
(your own Layer-3 judgement).
"""

from __future__ import annotations

# ── Grade bands ─────────────────────────────────────────────────────────────
GRADE_BANDS = [
    {"min": 90, "grade": "A+", "decision": "⭐ Deep study", "tone": "gold"},
    {"min": 80, "grade": "A", "decision": "⭐ Deep study", "tone": "green"},
    {"min": 70, "grade": "B", "decision": "🟢 Study", "tone": "blue"},
    {"min": 60, "grade": "C", "decision": "🟡 Watch", "tone": "orange"},
    {"min": -1, "grade": "D", "decision": "🔴 Don't bother", "tone": "red"},
]

GROWTH_MAX, VALUATION_MAX, QUALITY_MAX, STORY_MAX = 40, 20, 20, 20

GROWTH_TESTS = [
    {"key": "sales3y", "label": "Sales growth 3Y > 20%", "max": 8, "threshold": 20},
    {"key": "sales5y", "label": "Sales growth 5Y > 20%", "max": 8, "threshold": 20},
    {"key": "profit3y", "label": "Profit growth 3Y > 20%", "max": 8, "threshold": 20},
    {"key": "profit5y", "label": "Profit growth 5Y > 20%", "max": 8, "threshold": 20},
    {"key": "salesGrowth", "label": "Current sales growth > 20% (TTM)", "max": 4, "threshold": 20},
    {"key": "profitGrowth", "label": "Current profit growth > 20% (TTM)", "max": 4, "threshold": 20},
]

PEG_BANDS = [
    {"max": 0.6, "points": 10, "label": "PEG < 0.60"},
    {"max": 0.8, "points": 8, "label": "PEG 0.60 – 0.80"},
    {"max": 1.0, "points": 6, "label": "PEG 0.80 – 1.00"},
    {"max": 1.25, "points": 3, "label": "PEG 1.00 – 1.25"},
    {"max": float("inf"), "points": 0, "label": "PEG > 1.25"},
]

STORY_ITEMS = [
    {"key": "simple", "label": "Simple business", "max": 4},
    {"key": "runway", "label": "Large growth runway", "max": 4},
    {"key": "share", "label": "Market-share opportunity", "max": 3},
    {"key": "nonCyclical", "label": "Growth not purely cyclical", "max": 3},
    {"key": "cleanBooks", "label": "No obvious accounting red flags", "max": 3},
    {"key": "management", "label": "Management / promoter quality", "max": 3},
]

ELITE_QUERY = "\n".join([
    "Market Capitalization > 500",
    "AND Sales growth 3Years > 20",
    "AND Sales growth 5Years > 20",
    "AND Profit growth 3Years > 20",
    "AND Profit growth 5Years > 20",
    "AND Sales growth > 20",
    "AND Profit growth > 20",
    "AND YOY Quarterly sales growth > 20",
    "AND YOY Quarterly profit growth > 20",
    "AND PEG Ratio > 0",
    "AND PEG Ratio < 0.6",
    "AND Return on capital employed > 20",
    "AND Return on equity > 15",
    "AND Debt to equity < 0.5",
    "AND Pledged percentage = 0",
])

HYBRID_QUERY = "\n".join([
    "Market Capitalization > 500",
    "AND Sales growth 3Years > 15",
    "AND Sales growth 5Years > 15",
    "AND Profit growth 3Years > 15",
    "AND Profit growth 5Years > 15",
    "AND Sales growth > 15",
    "AND Profit growth > 15",
    "AND YOY Quarterly sales growth > 10",
    "AND YOY Quarterly profit growth > 10",
    "AND PEG Ratio > 0",
    "AND PEG Ratio < 1",
    "AND Return on capital employed > 15",
    "AND Return on equity > 15",
    "AND Debt to equity < 0.75",
    "AND Pledged percentage = 0",
])

SCREEN_DEFS = {
    "elite": {
        "id": "elite", "icon": "🔥", "name": "Elite Mode",
        "blurb": ">20% growth · PEG < 0.60 · ROCE > 20% · ROE > 15% · D/E < 0.5 · no pledge",
        "query": ELITE_QUERY,
    },
    "hybrid": {
        "id": "hybrid", "icon": "⭐", "name": "Lynch Hybrid",
        "blurb": ">15% growth · PEG < 1 · ROCE/ROE > 15 · D/E < 0.75 · no pledge",
        "query": HYBRID_QUERY,
    },
    "all": {
        "id": "all", "icon": "📚", "name": "Everything scanned",
        "blurb": "Every scored stock from the last scan — no Layer-1 filter applied",
        "query": None,
    },
}

STEP_QUESTIONS = [
    "What does the company actually sell?",
    "Why are sales growing?",
    "Why are profits growing faster/slower than sales?",
    "Is the growth sustainable?",
    "Is there a moat?",
    "Is debt increasing?",
    "Is cash flow genuine?",
    "Is management trustworthy?",
    "Is the industry cyclical?",
    "Why is the market giving me this stock at this valuation?",
]

ALIASES = {
    "symbol": ["symbol", "Ticker", "ticker"],
    "sales3y": ["Sales CAGR 3Y", "sales_cagr_3y"],
    "sales5y": ["Sales CAGR 5Y", "sales_cagr_5y"],
    "profit3y": ["Profit CAGR 3Y", "profit_cagr_3y"],
    "profit5y": ["Profit CAGR 5Y", "profit_cagr_5y"],
    "salesGrowth": ["Sales Growth", "sales_growth"],
    "profitGrowth": ["Profit Growth", "profit_growth"],
    "peg": ["PEG Ratio", "peg", "peg_ratio"],
    "pe": ["PE", "pe"],
    "mcap": ["Market Cap (Cr)", "mcap", "market_cap_cr"],
    "de": ["Debt/Equity", "debt_to_equity"],
    "reserves": ["Reserves", "reserves"],
    "promoter": ["Promoter %", "promoter_share"],
    "institution": ["Institution %", "inst_share"],
    "roce": ["ROCE %", "roce"],
    "roe": ["ROE %", "roe"],
    "cfoPat": ["CFO/PAT", "cfo_to_pat"],
    "pledged": ["Pledged %", "pledged_percent"],
    "redAlert": ["Red Alert", "red_alert"],
    "redReasons": ["Red Reasons", "red_reasons"],
    "sector": ["Sector", "sector"],
    "industry": ["Industry", "industry"],
    "category": ["Category", "category"],
    "turnaround": ["Turn Around", "turn_around"],
    "aboveSma": ["Is Above 200 SMA", "above_200dma"],
}


# ── Helpers ─────────────────────────────────────────────────────────────────
def _num(stock, keys):
    """First readable number in `stock` for any of `keys`, else None (NaN/''/None → None)."""
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
        if f != f:              # NaN
            continue
        return f
    return None


def _bool(stock, keys):
    for k in keys:
        if k not in stock:
            continue
        v = stock[k]
        if v is None:
            continue
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        if s in ("true", "yes", "1"):
            return True
        if s in ("false", "no", "0"):
            return False
    return None


def stock_symbol(stock) -> str:
    raw = stock.get("symbol") or stock.get("Ticker") or stock.get("ticker") or ""
    raw = str(raw).upper()
    return raw[:-3] if raw.endswith(".NS") else (raw[:-3] if raw.endswith(".BO") else raw)


def _r1(x):
    return round(x, 1)


def _half(x):
    return round(x * 2) / 2


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def _with_fallback(primary, fallback):
    if primary is not None and primary != 0:
        return primary, False
    if fallback is not None and fallback != 0:
        return fallback, True
    return None, False


def grade_of(total: float) -> dict:
    for band in GRADE_BANDS:
        if total >= band["min"]:
            return band
    return GRADE_BANDS[-1]


# ── METRICS ─────────────────────────────────────────────────────────────────
def lynch_metrics(stock) -> dict:
    sales3y = _num(stock, ALIASES["sales3y"])
    sales5y_raw = _num(stock, ALIASES["sales5y"])
    profit3y = _num(stock, ALIASES["profit3y"])
    profit5y_raw = _num(stock, ALIASES["profit5y"])

    sales5y, sales5y_fb = _with_fallback(sales5y_raw, sales3y)
    profit5y, profit5y_fb = _with_fallback(profit5y_raw, profit3y)

    peg = _num(stock, ALIASES["peg"])
    pe = _num(stock, ALIASES["pe"])
    mcap = _num(stock, ALIASES["mcap"])
    de_raw = _num(stock, ALIASES["de"])
    reserves = _num(stock, ALIASES["reserves"])
    promoter = _num(stock, ALIASES["promoter"])
    institution = _num(stock, ALIASES["institution"])

    # yfinance reports debtToEquity either as a ratio (0.45) or as a percentage (45.0).
    de_ratio = None if de_raw is None else (de_raw / 100.0 if de_raw > 5 else de_raw)

    # PAT in ₹ Cr = Market Cap ÷ PE (the earnings the market is capitalising).
    pat_cr = mcap / pe if (mcap is not None and pe not in (None, 0) and pe > 0) else None
    debt_cr = reserves * de_ratio if (reserves is not None and reserves > 0 and de_ratio is not None) else None
    capital_employed = (reserves + (debt_cr or 0)) if (reserves is not None and reserves > 0) else None

    roce_exact = _num(stock, ALIASES["roce"])
    roe_exact = _num(stock, ALIASES["roe"])
    roce_est = (pat_cr / capital_employed * 100.0) if (pat_cr is not None and capital_employed) else None
    roe_est = (pat_cr / reserves * 100.0) if (pat_cr is not None and reserves not in (None, 0) and reserves > 0) else None

    roce = roce_exact if roce_exact not in (None, 0) else roce_est
    roe = roe_exact if roe_exact not in (None, 0) else roe_est

    cfo_pat = _num(stock, ALIASES["cfoPat"])
    pledged = _num(stock, ALIASES["pledged"])
    red_alert = _bool(stock, ALIASES["redAlert"])

    return {
        "symbol": stock_symbol(stock),
        "sector": stock.get("Sector") or stock.get("sector") or "Unknown",
        "industry": stock.get("Industry") or stock.get("industry") or "Unknown",
        "category": stock.get("Category") or stock.get("category") or "",

        "sales3y": sales3y,
        "sales5y": sales5y,
        "sales5y_fallback": sales5y_fb,
        "profit3y": profit3y,
        "profit5y": profit5y,
        "profit5y_fallback": profit5y_fb,
        "salesGrowth": _num(stock, ALIASES["salesGrowth"]),
        "profitGrowth": _num(stock, ALIASES["profitGrowth"]),

        "peg": peg, "pe": pe, "mcap": mcap,
        "deRatio": de_ratio,
        "reserves": reserves, "promoter": promoter, "institution": institution,
        "patCr": _r1(pat_cr) if pat_cr is not None else None,
        "debtCr": _r1(debt_cr) if debt_cr is not None else None,

        "roce": _r1(roce) if roce is not None else None,
        "roe": _r1(roe) if roe is not None else None,
        "cfoPat": cfo_pat,
        "pledged": pledged,
        "redAlert": red_alert,
        "redReasons": stock.get("Red Reasons") or stock.get("red_reasons") or "",
        "turnaround": _bool(stock, ALIASES["turnaround"]),
        "aboveSma": _bool(stock, ALIASES["aboveSma"]),

        "source": {
            "roce": "exact" if roce_exact else ("estimate" if roce_est is not None else "unknown"),
            "roe": "exact" if roe_exact else ("estimate" if roe_est is not None else "unknown"),
            "cashflow": "exact" if cfo_pat is not None else "estimate",
            "pledge": "exact" if pledged is not None else "estimate",
            "debt": "exact" if de_ratio is not None else "unknown",
        },
    }


# ── GROWTH /40 ──────────────────────────────────────────────────────────────
def _score_growth(m):
    values = {
        "sales3y": m["sales3y"], "sales5y": m["sales5y"],
        "profit3y": m["profit3y"], "profit5y": m["profit5y"],
        "salesGrowth": m["salesGrowth"], "profitGrowth": m["profitGrowth"],
    }
    items = []
    for t in GROWTH_TESTS:
        v = values[t["key"]]
        known = v is not None
        fallback = (t["key"] == "sales5y" and m["sales5y_fallback"]) or (t["key"] == "profit5y" and m["profit5y_fallback"])
        points = t["max"] if (known and v > t["threshold"]) else 0
        items.append({
            "key": t["key"], "label": t["label"], "max": t["max"], "points": points,
            "value": v, "valueText": f"{_r1(v)}%" if known else "n/a",
            "status": "unknown" if not known else ("pass" if points == t["max"] else "fail"),
            "note": "5Y unavailable in scan — 3Y CAGR used" if fallback else "",
        })
    return {"points": sum(i["points"] for i in items), "max": GROWTH_MAX, "items": items}


# ── VALUATION /20 ───────────────────────────────────────────────────────────
def _score_valuation(m):
    peg = m["peg"]
    band = None
    if peg is not None and peg > 0:
        band = next((b for b in PEG_BANDS if peg < b["max"]), PEG_BANDS[-1])
    items = [{
        "key": f"peg_{b['max']}", "label": b["label"], "max": b["points"],
        "points": b["points"] if (band and band["label"] == b["label"]) else 0,
        "status": "pass" if (band and band["label"] == b["label"]) else "fail",
    } for b in PEG_BANDS]
    return {
        "points": band["points"] if band else 0,
        "max": VALUATION_MAX,
        "peg": peg,
        "bandLabel": band["label"] if band else "PEG unavailable",
        "items": items,
        "warnings": ["PEG > 1.5 — market is already paying up for this growth"] if (peg is not None and peg > 1.5) else [],
    }


# ── QUALITY /20 ─────────────────────────────────────────────────────────────
def _score_quality(m):
    items = []

    items.append({
        "key": "roce", "label": "ROCE > 20%", "max": 5,
        "value": m["roce"], "valueText": f"{_r1(m['roce'])}%" if m["roce"] is not None else "n/a",
        "points": 5 if (m["roce"] is not None and m["roce"] > 20) else 0,
        "status": "unknown" if m["roce"] is None else ("pass" if m["roce"] > 20 else "fail"),
        "source": m["source"]["roce"],
        "note": "Estimated: PAT ÷ (Reserves + implied debt). Verify on Screener.in" if m["source"]["roce"] == "estimate" else "",
    })
    items.append({
        "key": "roe", "label": "ROE > 20%", "max": 4,
        "value": m["roe"], "valueText": f"{_r1(m['roe'])}%" if m["roe"] is not None else "n/a",
        "points": 4 if (m["roe"] is not None and m["roe"] > 20) else 0,
        "status": "unknown" if m["roe"] is None else ("pass" if m["roe"] > 20 else "fail"),
        "source": m["source"]["roe"],
        "note": "Estimated: PAT ÷ Reserves (equity proxy)" if m["source"]["roe"] == "estimate" else "",
    })

    if m["cfoPat"] is not None:
        cash_pass = m["cfoPat"] > 0
        cash_text = f"CFO/PAT {_r1(m['cfoPat'])}"
    else:
        cash_pass = bool(m["profitGrowth"] is not None and m["profitGrowth"] > 0
                         and m["redAlert"] is not True
                         and m["profit3y"] is not None and m["profit3y"] > 0)
        cash_text = "Profits growing, no red flag" if cash_pass else "n/a"
    items.append({
        "key": "cash", "label": "Positive / healthy cash flow", "max": 4,
        "value": m["cfoPat"], "valueText": cash_text,
        "points": 4 if cash_pass else 0,
        "status": "pass" if cash_pass else "fail",
        "source": m["source"]["cashflow"],
        "note": "Cash-flow statement not in scan — proxy: positive & rising profits, no red alert" if m["cfoPat"] is None else "",
    })

    if m["cfoPat"] is not None:
        cfo_ok = m["cfoPat"] >= 0.7
        cfo_text = f"{_r1(m['cfoPat'])}×"
    else:
        s, p = m["sales3y"], m["profit3y"]
        cfo_ok = bool(s is not None and p is not None and s > 0 and p >= s * 0.8 and m["redAlert"] is not True)
        cfo_text = "Profit grows with Sales" if cfo_ok else "n/a"
    items.append({
        "key": "cfoTracks", "label": "CFO reasonably tracks PAT", "max": 3,
        "valueText": cfo_text,
        "points": 3 if cfo_ok else 0,
        "status": "pass" if cfo_ok else "fail",
        "source": m["source"]["cashflow"],
        "note": "Proxy: 3Y profit CAGR grows at least 0.8× the sales CAGR" if m["cfoPat"] is None else "",
    })

    items.append({
        "key": "debt", "label": "Debt/Equity < 0.5", "max": 2,
        "value": m["deRatio"], "valueText": f"{m['deRatio']:.2f}" if m["deRatio"] is not None else "n/a",
        "points": 2 if (m["deRatio"] is not None and m["deRatio"] < 0.5) else 0,
        "status": "unknown" if m["deRatio"] is None else ("pass" if m["deRatio"] < 0.5 else "fail"),
        "source": m["source"]["debt"], "note": "",
    })

    pledge_known = m["pledged"] is not None
    if pledge_known:
        pledge_pass = m["pledged"] == 0
        pledge_text = f"{m['pledged']}%"
    else:
        pledge_pass = bool(m["promoter"] is not None and 40 <= m["promoter"] <= 75 and m["redAlert"] is not True)
        pledge_text = f"promoter {_r1(m['promoter'])}%" if m["promoter"] is not None else "n/a"
    items.append({
        "key": "pledge", "label": "Promoter pledge = 0", "max": 2,
        "valueText": pledge_text,
        "points": 2 if pledge_pass else 0,
        "status": "pass" if pledge_pass else "fail",
        "source": m["source"]["pledge"],
        "note": "" if pledge_known else "Pledge data not in scan — proxy: healthy promoter holding, no red flag. Confirm on Screener.in",
    })

    return {"points": sum(i["points"] for i in items), "max": QUALITY_MAX, "items": items}


# ── LYNCH STORY /20 (auto-proxy, Layer-3 overridable) ───────────────────────
CYCLICALITY = {
    3: ["Technology", "Healthcare", "Consumer Defensive", "Communication Services"],
    2: ["Consumer Cyclical", "Industrials", "Financial Services"],
    1: ["Basic Materials", "Energy", "Real Estate", "Utilities"],
}
COMPLEX_SECTORS = ["Financial Services", "Real Estate", "Utilities", "Energy"]
COMPLEX_WORDS = ["diversified", "conglomerate", "holding"]


def auto_story(m) -> dict:
    sector = m["sector"] or "Unknown"
    industry = (m["industry"] or "").lower()

    simple = 4
    if sector in COMPLEX_SECTORS:
        simple = 2
    if any(w in industry for w in COMPLEX_WORDS):
        simple = min(simple, 2)
    if sector == "Unknown":
        simple = 3

    if m["mcap"] is None:
        runway = 2
    elif m["mcap"] < 5000:
        runway = 4
    elif m["mcap"] < 20000:
        runway = 3
    elif m["mcap"] < 50000:
        runway = 2
    else:
        runway = 1
    if not (m["sales3y"] is not None and m["sales3y"] >= 15):
        runway = max(1, runway - 1)

    share = 0
    if m["sales3y"] is not None and m["sales5y"] is not None:
        if m["sales3y"] > m["sales5y"] + 2:
            share = 3
        elif m["sales3y"] > m["sales5y"]:
            share = 2
        elif m["sales3y"] >= 15:
            share = 1
    elif m["sales3y"] is not None and m["sales3y"] >= 20:
        share = 2
    if m["turnaround"] is True:
        share = min(3, share + 1)

    non_cyclical = 2
    for pts, sectors in CYCLICALITY.items():
        if sector in sectors:
            non_cyclical = pts
    if sector == "Unknown":
        non_cyclical = 2
    if non_cyclical <= 1 and m["profit3y"] is not None and m["sales3y"] is not None and m["profit3y"] > m["sales3y"] * 3:
        non_cyclical = 1

    if m["redAlert"] is False:
        clean_books = 3
    elif m["redAlert"] is True:
        clean_books = 0
    else:
        clean_books = 1.5
    if (clean_books == 3 and m["profitGrowth"] is not None and m["salesGrowth"] is not None
            and m["salesGrowth"] > 0 and m["profitGrowth"] > m["salesGrowth"] * 4 + 100):
        clean_books = 1.5      # profit explosion far beyond sales — check one-offs

    management = 1
    if m["promoter"] is not None and 40 <= m["promoter"] <= 75:
        management += 1
    if m["institution"] is not None and m["institution"] >= 10:
        management += 1
    if m["promoter"] is not None and m["promoter"] < 25:
        management = min(management, 1)

    return {
        "simple": _clamp(_half(simple), 0, 4),
        "runway": _clamp(_half(runway), 0, 4),
        "share": _clamp(_half(share), 0, 3),
        "nonCyclical": _clamp(_half(non_cyclical), 0, 3),
        "cleanBooks": _clamp(_half(clean_books), 0, 3),
        "management": _clamp(_half(management), 0, 3),
    }


def score_story(m, override=None) -> dict:
    auto = auto_story(m)
    override = override or {}
    items = []
    for t in STORY_ITEMS:
        raw = override.get(t["key"])
        has_override = raw is not None and raw != ""
        try:
            value = _clamp(float(raw), 0, t["max"]) if has_override else auto[t["key"]]
        except (TypeError, ValueError):
            value, has_override = auto[t["key"]], False
        items.append({
            "key": t["key"], "label": t["label"], "max": t["max"],
            "points": value, "auto": auto[t["key"]], "overridden": has_override,
            "status": "manual" if has_override else "estimate",
        })
    return {
        "points": _half(sum(i["points"] for i in items)),
        "max": STORY_MAX,
        "items": items,
        "auto": auto,
        "overridden": any(i["overridden"] for i in items),
    }


# ── THE 100-POINT SCORE ─────────────────────────────────────────────────────
def score_lynch(stock, story_override=None) -> dict:
    m = lynch_metrics(stock)
    growth = _score_growth(m)
    valuation = _score_valuation(m)
    quality = _score_quality(m)
    story = score_story(m, story_override)

    total = _r1(growth["points"] + valuation["points"] + quality["points"] + story["points"])
    band = grade_of(total)

    warnings = list(valuation["warnings"])
    if m["redAlert"] is True:
        warnings.append(f"Red alert: {m['redReasons'] or 'see scan'}")
    if m["deRatio"] is not None and m["deRatio"] > 1:
        warnings.append(f"High leverage (D/E {m['deRatio']:.2f}) — Lynch disliked debt-heavy growth")
    if any(i["key"] == "profit3y" and i["status"] == "fail" for i in growth["items"]) and \
       any(i["key"] == "sales3y" and i["status"] == "pass" for i in growth["items"]):
        warnings.append("Sales growing but profits are not — margin pressure")

    return {
        "symbol": m["symbol"], "sector": m["sector"], "industry": m["industry"], "category": m["category"],
        "metrics": m, "growth": growth, "valuation": valuation, "quality": quality, "story": story,
        "total": total, "grade": band["grade"], "decision": band["decision"], "tone": band["tone"],
        "warnings": warnings, "storyOverridden": story["overridden"],
    }


# ── LAYER-1 FILTERS ─────────────────────────────────────────────────────────
def apply_screen(m, screen_id="hybrid") -> dict:
    """`required` checks must exist and pass; optional ones that are missing are reported as
    unverified instead of silently rejecting the stock."""
    if screen_id not in SCREEN_DEFS or screen_id == "all":
        return {"pass": True, "unverified": [], "failed": []}

    strict = screen_id == "elite"
    g = 20 if strict else 15
    de_max = 0.5 if strict else 0.75
    peg_max = 0.6 if strict else 1.0
    roce_min = 20 if strict else 15
    latest_min = 20 if strict else 15

    criteria = [
        (f"Sales growth 3Y > {g}%", m["sales3y"], m["sales3y"] is not None and m["sales3y"] > g, True),
        (f"Sales growth 5Y > {g}%", m["sales5y"], m["sales5y"] is not None and m["sales5y"] > g, True),
        (f"Profit growth 3Y > {g}%", m["profit3y"], m["profit3y"] is not None and m["profit3y"] > g, True),
        (f"Profit growth 5Y > {g}%", m["profit5y"], m["profit5y"] is not None and m["profit5y"] > g, True),
        (f"PEG between 0 and {peg_max}", m["peg"], m["peg"] is not None and 0 < m["peg"] < peg_max, True),
        (f"Latest sales growth > {latest_min}%", m["salesGrowth"], m["salesGrowth"] is not None and m["salesGrowth"] > latest_min, False),
        (f"Latest profit growth > {latest_min}%", m["profitGrowth"], m["profitGrowth"] is not None and m["profitGrowth"] > latest_min, False),
        (f"ROCE > {roce_min}%", m["roce"], m["roce"] is not None and m["roce"] > roce_min, False),
        ("ROE > 15%", m["roe"], m["roe"] is not None and m["roe"] > 15, False),
        (f"Debt/Equity < {de_max}", m["deRatio"], m["deRatio"] is not None and m["deRatio"] < de_max, False),
        ("Promoter pledge = 0%", m["pledged"], m["pledged"] == 0, False),
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
    return {"pass": passed, "unverified": unverified, "failed": failed}


# ── Ranking helpers used by both the Streamlit page and the CLI ─────────────
def rank_rows(records, overrides=None, screen_id="hybrid"):
    """Score every record, keep the ones that pass the Layer-1 screen, sort by total desc."""
    overrides = overrides or {}
    rows = []
    for rec in records:
        sym = stock_symbol(rec)
        scored = score_lynch(rec, overrides.get(sym))
        scored["screen"] = apply_screen(scored["metrics"], screen_id)
        if scored["screen"]["pass"]:
            rows.append(scored)
    rows.sort(key=lambda r: r["total"], reverse=True)
    return rows


def rows_to_records(rows):
    """Flat dicts, ready for pandas.DataFrame / st.dataframe."""
    out = []
    for i, r in enumerate(rows, start=1):
        m = r["metrics"]
        out.append({
            "Rank": i,
            "Stock": r["symbol"],
            "Sector": r["sector"],
            "Growth /40": r["growth"]["points"],
            "Valuation /20": r["valuation"]["points"],
            "Quality /20": r["quality"]["points"],
            "Story /20": r["story"]["points"],
            "TOTAL /100": r["total"],
            "Grade": r["grade"],
            "Decision": r["decision"],
            "PEG": m["peg"] if m["peg"] is not None else "",
            "Sales 3Y %": m["sales3y"] if m["sales3y"] is not None else "",
            "Sales 5Y %": m["sales5y"] if m["sales5y"] is not None else "",
            "Profit 3Y %": m["profit3y"] if m["profit3y"] is not None else "",
            "Profit 5Y %": m["profit5y"] if m["profit5y"] is not None else "",
            "ROCE %": m["roce"] if m["roce"] is not None else "",
            "ROE %": m["roe"] if m["roe"] is not None else "",
            "Debt/Equity": round(m["deRatio"], 2) if m["deRatio"] is not None else "",
            "MCap (Cr)": m["mcap"] if m["mcap"] is not None else "",
            "Story (manual)": "yes" if r["storyOverridden"] else "",
        })
    return out


CSV_COLUMNS = [
    "Rank", "Stock", "Sector", "Growth /40", "Valuation /20", "Quality /20", "Story /20", "TOTAL /100",
    "Grade", "Decision", "PEG", "Sales 3Y %", "Sales 5Y %", "Profit 3Y %", "Profit 5Y %",
    "ROCE %", "ROE %", "Debt/Equity", "MCap (Cr)", "Story (manual)",
]


def rows_to_csv(rows) -> str:
    import csv
    import io

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for rec in rows_to_records(rows):
        writer.writerow(rec)
    return buf.getvalue()


def top_five_text(rows, limit=5) -> str:
    """WhatsApp-ready summary."""
    import datetime as _dt

    lines = [f"🏆 DR GILL — LYNCH {limit}  ({_dt.date.today().strftime('%d %b %Y')})", ""]
    for i, r in enumerate(rows[:limit], start=1):
        m = r["metrics"]
        peg = m["peg"] if m["peg"] is not None else "—"
        lines.append(f"{i}. {r['symbol']} — {r['total']}/100 ({r['grade']}) {r['decision']}")
        lines.append(f"   PEG {peg} · Sales 3Y {m['sales3y'] or '—'}% / 5Y {m['sales5y'] or '—'}% · Profit 3Y {m['profit3y'] or '—'}%")
        lines.append(f"   Growth {r['growth']['points']}/40 · Valuation {r['valuation']['points']}/20 · "
                     f"Quality {r['quality']['points']}/20 · Story {r['story']['points']}/20")
    lines += ["", "Screener → 100-point score → Top 5 → deep research"]
    return "\n".join(lines)


if __name__ == "__main__":
    # Quick CLI check: python lynch_engine.py
    from data_fetcher import load_cached_scan_from_db
    from scoring_engine import run_scoring

    cache = load_cached_scan_from_db()
    if not cache:
        print("No cached scan found — run a System Scan first.")
    else:
        df, *_ = run_scoring(cache)
        records = df.to_dict("records")
        for screen_id in ("hybrid", "elite", "all"):
            rows = rank_rows(records, screen_id=screen_id)
            print(f"\n=== {SCREEN_DEFS[screen_id]['name']}: {len(rows)} stocks ===")
            for r in rows[:10]:
                m = r["metrics"]
                print(f"{r['total']:>5} {r['grade']:<2} {r['symbol']:<12} "
                      f"G{r['growth']['points']:>2} V{r['valuation']['points']:>2} "
                      f"Q{r['quality']['points']:>2} S{r['story']['points']:>2}  PEG={m['peg']}")
        print("\n" + top_five_text(rank_rows(records, screen_id="hybrid")))

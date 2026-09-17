"""
verify_engine_parity.py — do the Streamlit engine and the React engine agree?

`lynch_engine.py` (Streamlit) and `frontend/src/lynch.js` (React) must produce the SAME score for
the same stock, or the fund sees two different answers depending on which app is open. The lender
logic lives in a matched pair too: `financial_engine.py` and `frontend/src/lender.js`.

This script is the Python half. It scores a handful of real records — deliberately including
lenders (CHOLAFIN, MUTHOOTFIN, HDFCBANK) and a manufacturer (AUROPHARMA, DIXON) — across every
basket and writes the result to `_parity_expected.json`, along with the raw scored records.

Then run the JavaScript half, which re-scores the SAME records with `lynch.js` and diffs:

    python verify_engine_parity.py
    cd frontend && node verify_engine_parity.mjs

Exit code 0 means the two engines agree. Any mismatch prints the stock, the basket, and which
number differs.

The first run fetches from yfinance / screener.in and writes to the local cache; after that it is
offline and fast.
"""

import io
import json
import sys

# The scan loader prints emoji, which a cp1252 console cannot encode.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from data_fetcher import get_stock_data          # noqa: E402
from scoring_engine import run_scoring           # noqa: E402
import lynch_engine as L                         # noqa: E402

TICKERS = ["CHOLAFIN.NS", "MUTHOOTFIN.NS", "HDFCBANK.NS", "AUROPHARMA.NS", "DIXON.NS"]
SCREENS = ("hybrid", "elite", "financials", "all")
OUT_PATH = "_parity_expected.json"


def _clean(o):
    """pandas turns a mixed None column into NaN, which is not valid JSON."""
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_clean(v) for v in o]
    if isinstance(o, float) and o != o:
        return None
    return o


def main():
    cache = {}
    for t in TICKERS:
        try:
            d = get_stock_data(t)
        except Exception as e:                       # network hiccup on one name is not fatal
            print(f"  {t}: fetch failed ({e})")
            d = None
        if d:
            cache[t] = d

    if not cache:
        print("No data available — check the network and the local caches.")
        return 1

    df, *_ = run_scoring(cache)
    records = _clean(df.to_dict("records"))

    rows = []
    for rec in records:
        sym = L.stock_symbol(rec)
        for screen in SCREENS:
            s = L.score_lynch(rec)
            sc = L.apply_screen(s["metrics"], screen)
            rows.append({
                "symbol": sym,
                "screen": screen,
                "total": s["total"],
                "grade": s["grade"],
                "growth": s["growth"]["points"],
                "valuation": s["valuation"]["points"],
                "quality": s["quality"]["points"],
                "story": s["story"]["points"],
                "pass": sc["pass"],
                "rubric": sc["rubric"],
                "warnings": s["warnings"],
                "isLender": s["metrics"]["isLender"],
            })

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"python": rows, "records": records}, f, indent=1, default=str)

    print(f"wrote {len(rows)} (stock x basket) rows and {len(records)} records to {OUT_PATH}\n")
    for r in rows:
        if r["screen"] == "hybrid":
            print(f"  {r['symbol']:<12} {r['total']:>5} {r['grade']:<2} "
                  f"G{r['growth']} V{r['valuation']} Q{r['quality']} S{r['story']} "
                  f"pass={str(r['pass']):<5} lender={r['isLender']}")
    print("\nnow run:  cd frontend && node verify_engine_parity.mjs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

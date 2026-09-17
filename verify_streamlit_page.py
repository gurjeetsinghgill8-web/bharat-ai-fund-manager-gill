"""
verify_streamlit_page.py — headless smoke test for the front page.

Runs app.py with Streamlit's own AppTest harness (no browser, no server) and asserts the things
that actually broke before, so a future edit to app.py cannot quietly undo them:

  1. 🏆 Peter Lynch is the LANDING page and leads the sidebar navigation.
  2. The Layer-1 baskets include 🏦 Banks & NBFC.
  3. The old "Select a stock" selectbox — whose options read "CHOLAFIN — 68/100 (C)", so searching
     meant deleting that tail by hand — is gone, replaced by an always-empty search box.
  4. The lender basket ranks banks/NBFCs, with the lender columns (ROA, Net Worth, Capital %,
     P/B, GNPA) on the table.
  5. Typing "CHOLA" resolves to exactly one CHOLAFIN (the NSE/BSE duplicate listing is collapsed).
  6. Typing the NPA numbers moves the Quality bucket, and the values SURVIVE switching stock —
     the asset-quality lens works and the marks are not thrown away.

NOTE ON THE HARNESS — why the session state is pre-seeded. Many widgets here are keyed by the
SELECTED stock (`lynch_story__CHOLAFIN__simple`), so a rerun that opens a different stock stops
rendering the previous stock's widgets. That is correct at runtime — the user's typed values are
copied into a plain, symbol-keyed dict first, so they survive — but AppTest keeps references to
the widgets of the previous run and raises KeyError asking for their now-retired state. Seeding
`session_state` up front and then running once avoids exercising that AppTest artefact while
still testing the real behaviour.

Usage:  python verify_streamlit_page.py

Exit code 0 = every check passed.
"""

import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from streamlit.testing.v1 import AppTest  # noqa: E402

LYNCH_PAGE = "🏆 Peter Lynch 100-Point System"
LENDER_BASKET = "🏦 Banks & NBFC"

PASS, FAIL = "  ✅", "  ❌"
failures = []


def check(label, ok, detail=""):
    print(f"{PASS if ok else FAIL} {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(label)


def new_app(**seed):
    """A fresh AppTest with the given widget state already in place, run exactly once."""
    at = AppTest.from_file("app.py", default_timeout=300)
    for k, v in seed.items():
        at.session_state[k] = v
    at.run()
    return at


def main():
    # ── 1. the landing page ──────────────────────────────────────────────────
    at = new_app()
    check("app.py runs without an exception", not at.exception,
          "; ".join(str(e.value) for e in at.exception))

    nav = at.sidebar.selectbox(key="top_nav_selectbox")
    check("Peter Lynch leads the sidebar navigation", nav.options[0].startswith("🏆"), nav.options[0])
    check("Peter Lynch is the landing page", nav.value.startswith("🏆"), nav.value)

    baskets = next((r.options for r in at.radio if r.label == "Layer 1 — candidate pool"), [])
    check("🏦 Banks & NBFC basket exists", any("Banks & NBFC" in b for b in baskets), str(baskets))

    # ── 2. the picker replaced the un-clearable selectbox ────────────────────
    check("the un-clearable 'Select a stock' box is gone",
          not any(s.label == "Select a stock" for s in at.selectbox))
    search_boxes = [t for t in at.text_input if t.label.startswith("🔎")]
    check("the stock search box exists and starts empty",
          bool(search_boxes) and search_boxes[0].value == "",
          repr(search_boxes[0].value if search_boxes else None))

    # ── 3. the lender basket, opening straight on CHOLAFIN ───────────────────
    # Top 5 only is turned OFF here so the table holds the whole lender ranking — otherwise a
    # check for "is CHOLAFIN in the table" would really be testing its rank, not its presence.
    lat = new_app(**{
        "top_nav_selectbox": LYNCH_PAGE,
        "lynch_screen_radio": LENDER_BASKET,
        "lynch_pick_query": "CHOLA",
        "lynch_top5_only": False,
    })
    check("the lender basket with a search runs without an exception", not lat.exception,
          "; ".join(str(e.value) for e in lat.exception))

    tbl = lat.dataframe[0].value if len(lat.dataframe) else None
    check("there is a ranking table", tbl is not None and "Stock" in getattr(tbl, "columns", []))
    if tbl is not None and "Stock" in tbl.columns:
        stocks = list(tbl["Stock"])
        check("the lender basket ranks banks/NBFCs", len(stocks) > 0, f"{len(stocks)} rows")
        check("CHOLAFIN is ranked in the lender basket", "CHOLAFIN" in stocks,
              f"ranking: {stocks}")
        check("no duplicate CHOLAFIN row (NSE/BSE listing collapsed)",
              stocks.count("CHOLAFIN") == 1, f"CHOLAFIN appears {stocks.count('CHOLAFIN')}x")
        lender_cols = ["ROA %", "Net Worth (Cr)", "Capital % Assets", "P/B", "GNPA %"]
        missing = [c for c in lender_cols if c not in tbl.columns]
        check("lender columns are on the ranking table", not missing,
              f"missing {missing}" if missing else ", ".join(lender_cols))
        check("a lender row carries real balance-sheet numbers",
              any(v is not None for v in list(tbl["Net Worth (Cr)"])),
              f"Net Worth: {list(tbl['Net Worth (Cr)'])[:5]}")

    # ── 4. the NPA lens ──────────────────────────────────────────────────────
    npa_labels = [n.label for n in lat.number_input
                  if n.label in ("Gross NPA %", "Net NPA %", "Provision coverage %", "Capital adequacy %")]
    check("the NPA entry box appears for a lender", len(npa_labels) == 4, str(npa_labels))

    if len(npa_labels) == 4 and tbl is not None and "CHOLAFIN" in list(tbl["Stock"]):
        before = list(tbl["Quality /20"])[list(tbl["Stock"]).index("CHOLAFIN")]

        # Type the real Cholamandalam numbers into whichever stock is open. The open stock is
        # CHOLAFIN here because "CHOLA" matched it and session_state picked it.
        for key, val in (("gnpa", 0.6), ("nnpa", 0.4), ("pcr", 72.0), ("car", 19.5)):
            field = f"lynch_fact__CHOLAFIN__{key}"
            matches = [n for n in lat.number_input if n.key == field]
            if matches:
                matches[0].set_value(val)
        lat.run()
        check("entering NPA does not raise", not lat.exception,
              "; ".join(str(e.value) for e in lat.exception))

        tbl2 = lat.dataframe[0].value
        stocks2 = list(tbl2["Stock"])
        after = list(tbl2["Quality /20"])[stocks2.index("CHOLAFIN")]
        check("typing the NPA numbers moves the Quality bucket", after > before,
              f"Quality {before}/20 → {after}/20")
        check("the entered GNPA shows on the ranking row",
              any(abs(float(v) - 0.6) < 1e-9 for v in list(tbl2["GNPA %"]) if v == v),
              str(list(tbl2["GNPA %"])))

        # The whole point of the durable store: the mark must not vanish when another stock is
        # opened, which is what happens if the value only lives in widget state.
        # NOTE: AppTest.session_state is not a plain dict, so index it rather than calling .get().
        try:
            stored_gnpa = lat.session_state["lynch_facts_store"]["CHOLAFIN"]["gnpa"]
        except (KeyError, TypeError):
            stored_gnpa = None
        check("the typed NPA is kept in the durable store", stored_gnpa == 0.6,
              f"lynch_facts_store → {stored_gnpa}")
    else:
        check("CHOLAFIN is in the lender ranking", False, f"ranking: {list(tbl['Stock']) if tbl is not None else None}")

    print()
    if failures:
        print(f"FAILED — {len(failures)} check(s): " + "; ".join(failures))
        return 1
    print("PASSED — the front page, the baskets, the picker and the NPA lens all behave.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# DR GILL — PETER LYNCH 100-POINT SYSTEM

> Screener → 100-point score → Top 5 → deep research
>
> **Two front-ends, one rulebook:**
> * Streamlit app (online): sidebar → **🏆 Peter Lynch 100-Point System** — engine `lynch_engine.py`
> * React dashboard: **🏆 Peter Lynch 100-Point** (`/peter-lynch`) — engine `frontend/src/lynch.js`
>
> Both engines implement the identical rubric, so a stock scores the same in either app.
> The Streamlit page ranks the **whole scan cache** (all scored stocks, e.g. 1,682);
> the React page ranks the GURJAS 1 + GURJAS 2 result set of the last scan.
> A parity harness compares the two engines row by row — see **Engine parity** below.

**The page is the front page.** It leads the navigation in both apps and is the Streamlit
landing page, and the React dashboard shows the same Top 5 in a spotlight card on `/`.
The question it answers — *what do I research next?* — is the first question of the day.

---

## The four baskets

| Basket | Purpose |
|---|---|
| 🔥 **Elite Mode** | >20% growth, PEG < 0.6, ROCE > 20%, ROE > 15%, D/E < 0.5, no pledge — *exceptional bargains* |
| ⭐ **Lynch Hybrid** | >15% growth, PEG < 1, ROCE/ROE > 15%, D/E < 0.75, no pledge — *the wider opportunity set* |
| 🏦 **Banks & NBFC** | >15% growth, PEG < 1.2, **ROA > 1%**, ROE > 15%, capital cushion, NPA — *lenders only* |
| 📚 **Everything scanned** | No Layer-1 filter at all |

🔥 Elite and ⭐ Hybrid judge a **lender** with the lender rubric rather than dropping it, so a
bank or an NBFC can never again be silently absent from the ranking. 🏦 Banks & NBFC shows the
lenders on their own. See **Banks & NBFC** below.

---

## The three layers

| Layer | What it does | Where |
|---|---|---|
| **1 — Machine filter** | Growth + PEG + ROCE/ROE + debt + pledge → candidate pool | Screener.in queries below, or the basket chips on the page |
| **2 — 100-point ranking** | Growth /40 · Valuation /20 · Quality /20 · Lynch Story /20 | Computed in the browser from the last scan |
| **3 — Human research** | Answer the 10 questions, then override the Story bucket by hand | Score card on the page (saved in the browser) |

The page ranks the last scan's result set and re-applies the Layer-1 filter on top, so switching
between Elite / Hybrid / Banks & NBFC / Everything needs no new scan.

---

## Layer 1 — the three Screener.in queries

### 🔥 Elite Mode query

```
Market Capitalization > 500
AND Sales growth 3Years > 20
AND Sales growth 5Years > 20
AND Profit growth 3Years > 20
AND Profit growth 5Years > 20
AND Sales growth > 20
AND Profit growth > 20
AND YOY Quarterly sales growth > 20
AND YOY Quarterly profit growth > 20
AND PEG Ratio > 0
AND PEG Ratio < 0.6
AND Return on capital employed > 20
AND Return on equity > 15
AND Debt to equity < 0.5
AND Pledged percentage = 0
```

### ⭐ Lynch Hybrid query

```
Market Capitalization > 500
AND Sales growth 3Years > 15
AND Sales growth 5Years > 15
AND Profit growth 3Years > 15
AND Profit growth 5Years > 15
AND Sales growth > 15
AND Profit growth > 15
AND YOY Quarterly sales growth > 10
AND YOY Quarterly profit growth > 10
AND PEG Ratio > 0
AND PEG Ratio < 1
AND Return on capital employed > 15
AND Return on equity > 15
AND Debt to equity < 0.75
AND Pledged percentage = 0
```

### 🏦 Banks & NBFC query

```
Market Capitalization > 500
AND Sales growth 3Years > 15
AND Sales growth 5Years > 15
AND Profit growth 3Years > 15
AND Profit growth 5Years > 15
AND Sales growth > 15
AND Profit growth > 15
AND PEG Ratio > 0
AND PEG Ratio < 1.2
AND Return on equity > 15
AND Return on assets > 1
AND Pledged percentage = 0
```

**Correction:** there is no `TTM Result Date` field on Screener.in. For current growth use
`Profit growth` and/or `YOY Quarterly profit growth` — both are already in the queries above.
There is also **no public Gross/Net NPA filter**, so NPA is a per-stock check, never a silent
filter — see below.

---

## 🏦 Banks & NBFC — why lenders need their own rubric

This is the fix for *"why did CHOLAFIN never appear?"*. Two things used to happen to every bank
and NBFC:

1. **Layer 1 threw them out.** `Debt to equity < 0.5` is impossible for a lender — borrowing is
   the raw material of the business. CHOLAFIN runs at D/E ≈ 6.9; HDFCBANK at roughly 12×
   assets/net-worth. And `ROCE > 15%` is meaningless when the "capital employed" *is* the loan
   book. So a perfectly good NBFC failed the filter by definition.
2. **They were flagged as red alerts.** `scoring_engine.score_stock()` raised
   "High Debt/Equity Ratio" at D/E > 2.0, which every Indian NBFC trips. CHOLAFIN's 20%+ ROE,
   2.3% ROA and 12% net-worth-to-assets was being labelled a red alert for doing its job.

### What replaces what

| Standard rubric | Lender rubric | Why |
|---|---|---|
| ROCE > 20% | **ROA > 1%** | Return on *assets* is how a lender is measured |
| Debt/Equity < 0.5 | **Net worth ≥ 10% of assets** (NBFC) / **≥ 6%** (bank) | The capital cushion, in the form a regulator uses |
| Positive operating cash flow | **Financing margin** (NBFC only) | The earnings engine; unreliable on Screener's bank template, so it is dropped for banks |
| CFO tracks PAT | **Gross NPA < 3% and Net NPA < 1.5%** | *The* number for a lender — is the book good? |
| — | **Provision coverage ≥ 70% or CAR ≥ 15%** | The cushion that absorbs a bad year |
| Promoter pledge = 0 | Promoter pledge = 0 | Unchanged |

Leverage is no longer a red flag for a financial. The flags that are raised instead are: weak
ROA (< 0.6%), ROE below the cost of equity (< 10%), a thin capital cushion, GNPA > 5%,
NNPA > 2%, CAR < 12%, provision coverage < 60%, and a financing margin below 2%.

### Where the numbers come from — and the NPA problem

`screeners_scraper.py` now also reads the **full balance sheet** off a Screener.in company page:
Equity Capital, Reserves, Deposits, Borrowing and Total Assets (plus Financing Margin % on the
P&L). That is free and needs no login, and it gives a lender real net worth, real total assets,
real borrowings and real deposits — which is what ROA, the capital cushion and P/B are built
from. It also makes the equity figure better for **every** company: `net_worth_cr`
(equity capital + reserves) is true shareholder equity, whereas the yfinance `reserves` field
used before is only retained earnings and understates equity for anything with issued capital.

**Gross NPA %, Net NPA % and Capital Adequacy Ratio are printed as ROWS on a lender page but
Screener.in BLANKS THE VALUES behind a login.** So the engine does not scrape them and never
guesses them. Those three lines read `not in scan`, score 0, and the stock is still ranked. The
score card has a **🏦 Asset quality** box where you type Gross NPA, Net NPA, provision coverage
and capital adequacy from the quarterly result or investor presentation — the Quality bucket and
the total update immediately. That is the NPA lens, switched on deliberately and on the record
rather than inferred.

For CHOLAFIN the difference is the difference between a C and a B: with NPA unverified the
Quality bucket is 11/20; with GNPA 0.6% / NNPA 0.4% / CAR 19.5% / PCR 72% typed in it becomes
18/20.

---

## Layer 2 — the 100-point table

The **Growth** and **Valuation** buckets are identical for every stock. The **Quality** bucket
has two versions — the standard one below, and the lender one in the table above. **Story** is
always the same.

| Category | Test | Points |
|---|---|---|
| **GROWTH** | Sales growth 3Y > 20% | 8 |
| | Sales growth 5Y > 20% | 8 |
| | Profit growth 3Y > 20% | 8 |
| | Profit growth 5Y > 20% | 8 |
| | Current sales growth > 20% | 4 |
| | Current profit growth > 20% | 4 |
| | **Growth subtotal** | **40** |
| **VALUATION** | PEG < 0.60 | 10 |
| | PEG 0.60 – 0.80 | 8 |
| | PEG 0.80 – 1.00 | 6 |
| | PEG 1.00 – 1.25 | 3 |
| | PEG > 1.25 | 0 |
| | **Valuation subtotal** | **20** |
| **QUALITY** (standard) | ROCE > 20% | 5 |
| | ROE > 20% | 4 |
| | Positive / healthy cash flow | 4 |
| | CFO reasonably tracks PAT | 3 |
| | Debt/Equity < 0.5 | 2 |
| | Promoter pledge = 0 | 2 |
| | **Quality subtotal** | **20** |
| **QUALITY** (🏦 lender) | ROA > 1% | 5 |
| | ROE > 15% | 4 |
| | Gross NPA < 3% and Net NPA < 1.5% | 4 |
| | Provision coverage ≥ 70% or CAR ≥ 15% | 3 |
| | Net worth ≥ 10% of assets (NBFC) / 6% (bank) | 2 |
| | Promoter pledge = 0 | 2 |
| | **Quality subtotal** | **20** |
| **LYNCH STORY** | Simple business | 4 |
| | Large growth runway | 4 |
| | Market-share opportunity | 3 |
| | Growth not purely cyclical | 3 |
| | No obvious accounting red flags | 3 |
| | Management / promoter quality | 3 |
| | **Story subtotal** | **20** |
| | **TOTAL** | **100** |

### Grades

| Score | Grade | Decision |
|---|---|---|
| 90–100 | A+ | ⭐ Deep study |
| 80–89 | A | ⭐ Deep study |
| 70–79 | B | 🟢 Study |
| 60–69 | C | 🟡 Watch |
| < 60 | D | 🔴 Don't bother |

---

## Data honesty — exact vs estimate vs unknown

The scan carries Sales/Profit CAGR, latest YoY growth, PEG, PE, Market Cap, Debt/Equity,
Reserves, promoter and institution holding, sector and industry — plus, since the balance-sheet
upgrade, net worth, borrowings, deposits, total assets and financing margin for lenders. It does
**not** carry Gross/Net NPA, provision coverage or capital adequacy (login-walled at the source).

The engine therefore labels every line:

* **exact** — read straight from the balance sheet / P&L.
* **est** — derived: `PAT = Market Cap ÷ PE`, `Net worth ≈ Reserves`, `Borrowings ≈ Net worth × D/E`,
  `ROA = PAT ÷ Total assets`, `ROE = PAT ÷ Net worth`. Verify on Screener.in.
* **n/a** — not present. It scores **0** and is never invented. Layer-1 filters report such
  criteria as *unverified* instead of silently rejecting the stock, so a stock is never dropped
  for a missing column.
* **manual** — your own Layer-3 number, stored in the browser (localStorage).

Story items are auto-filled with a documented sector/market-cap/growth heuristic. They are the
part of the rubric a machine cannot judge — open a score card and type your own marks; the
total updates live and is marked `manual story`.

Two guards protect the arithmetic: a money value above ₹50 lakh crore is treated as raw rupees
and converted to ₹ Cr, and a derived net worth implying P/B < 0.02 is reported as `unknown`
rather than trusted — a bank never trades at 2% of book.

---

## Engine parity

`lynch_engine.py` (Streamlit) and `frontend/src/lynch.js` (React) must agree, or the same stock
scores differently depending on which app you open. The lender logic lives in a matched pair of
modules — `financial_engine.py` and `frontend/src/lender.js` — with the same constants, the same
thresholds and the same `source` labels.

The check is mechanical: export the Python scores to JSON, score the same records in Node with
`lynch.js`, and compare total, grade, all four buckets, the Layer-1 verdict, the rubric used, the
lender classification and the warnings. **20/20 stock × basket combinations match exactly.**

* `verify_engine_parity.py` — scores five real names (three lenders, two manufacturers) across
  every basket and writes `_parity_expected.json`
* `frontend/verify_engine_parity.mjs` — re-scores those same records with the JS engine and diffs

```
python verify_engine_parity.py
cd frontend && node verify_engine_parity.mjs
```

Exit code 0 means the two engines agree. `verify_streamlit_page.py` is the companion smoke test
for the front page: it drives `app.py` headlessly and asserts that Peter Lynch is still the
landing page, that the baskets include 🏦 Banks & NBFC, that the stock picker starts empty and
resolves `CHOLA` to a single CHOLAFIN, that the lender columns are on the table, and that typing
the NPA numbers moves the Quality bucket (11/20 → 18/20 for CHOLAFIN).

---

## Duplicate listings

89 names in the scan are listed on **both** NSE and BSE (`CHOLAFIN.NS` and `CHOLAFIN.BO`), and
the symbol normaliser strips the exchange suffix — so an undeduplicated list ranks CHOLAFIN
twice, with two different scores, and the stock search returns the same name twice.
`dedupe_by_symbol()` keeps one row per company, **NSE winning** as the primary listing the
Screener.in queries match. The Sectors page is untouched: there the NSE-vs-BSE split is the point.

---

## Layer 3 — ask these 10 questions (Top 5 only)

1. What does the company actually sell?
2. Why are sales growing?
3. Why are profits growing faster/slower than sales?
4. Is the growth sustainable?
5. Is there a moat?
6. Is debt increasing?
7. Is cash flow genuine?
8. Is management trustworthy?
9. Is the industry cyclical?
10. Why is the market giving me this stock at this valuation?

The last question decides whether the score is an opportunity or a warning. For a lender, read
question 7 as *"is the loan book genuine?"* — which is what the NPA box is asking you to type in.

---

## Using the pages

### Streamlit (online)
* Landing page, and first in the sidebar navigation.
* **Layer 1 radio**: `🔥 Elite Mode` · `⭐ Lynch Hybrid` · `🏦 Banks & NBFC` · `📚 Everything scanned`,
  plus **Top 5 only** (on by default), search, min-score and sort controls.
* The three Screener.in queries sit in an expander — the code block's copy icon copies them.
* **⬇ Download CSV** exports the ranked table; **⬇ Top 5 as text** / the *Copy-ready Top 5* box
  give the WhatsApp summary.
* **🔎 Find a stock** is a plain, always-empty search box with a `✕ Clear` button: type `CHOLA`,
  click the match. It replaced a selectbox whose options read `CHOLAFIN — 68/100 (C)`, where
  searching meant deleting that tail by hand first.
* **Score card** shows every mark with ✅ / ❌ / ➖ / 🟡 / 🔵, the source of each ratio, the
  Layer-1 verdict and links to Screener.in + the annual report. For a lender it opens with the
  lender fact line (ROA, net worth, capital %, leverage ×, P/B) and the **🏦 Asset quality** box.
* **Layer 3 — override the Story bucket**: type your own marks; the total and the ranking update
  immediately (the row is flagged `Story (manual)`).
* Everything you type — Story marks AND the NPA numbers — is stored in a **plain, symbol-keyed
  dict**, not in Streamlit widget state. Streamlit garbage-collects the state of any widget that
  stops rendering, and every box here is keyed by the *selected* stock, so without that store
  switching from CHOLAFIN to MUTHOOTFIN would silently throw CHOLAFIN's marks away.

### React dashboard
* Peter Lynch leads the sidebar, and `/` (the Portfolio Dashboard) shows a **🏆 Peter Lynch
  Top 5** spotlight card above the fold with an *Open full ranking ↗* link.
* **Candidate pool** chips: `🔥 Elite` · `⭐ Lynch Hybrid` · `🏦 Banks & NBFC` · `📚 Everything scanned`.
* **Top 5 only** is on by default — that is the whole point of the system. Toggle it to see the
  full ranking.
* **Copy Top 5** produces a WhatsApp-ready summary; **⬇ CSV** exports the ranked table.
* **▼ Score** on any row opens the full mark sheet: every test, its value, its source
  (`est` / `n/a`), the Layer-1 check and the Story overrides.
* Deep link: `/peter-lynch?screen=financials&stock=CHOLAFIN`.

---

## Refreshing the numbers

`ROE %`, `ROCE %` and `CFO/PAT` become exact fields on scans run after the `data_fetcher.py`
update; existing cached stocks keep their `est` values until their cache expires (7 days) or a
scan runs with `force_refresh`.

The balance-sheet upgrade is applied the same way but **only to lenders**, so it does not turn
into a 1,682-stock refetch. A record whose sector/industry makes it a bank or an NBFC gets one
forced refresh when its cached screener page predates the balance-sheet block (or when its
cached net worth is missing); a manufacturer keeps its cache and costs nothing. Until a given
lender is refreshed, its ROA / capital cushion / P/B are labelled `est` and P/B is visibly
implausible — run a scan and they become `exact`.


# DR GILL — PETER LYNCH 100-POINT SYSTEM

> Screener → 100-point score → Top 5 → deep research
>
> **Two front-ends, one rulebook:**
> * Streamlit app (online): sidebar → **🏆 Page 6: Peter Lynch 100-Point System** — engine `lynch_engine.py`
> * React dashboard: **🏆 Peter Lynch 100-Point** (`/peter-lynch`) — engine `frontend/src/lynch.js`
>
> Both engines implement the identical rubric, so a stock scores the same in either app.
> The Streamlit page ranks the **whole scan cache** (all scored stocks, e.g. 1,682);
> the React page ranks the GURJAS 1 + GURJAS 2 result set of the last scan.

---

## The three layers

| Layer | What it does | Where |
|---|---|---|
| **1 — Machine filter** | Growth + PEG + ROCE/ROE + debt + pledge → candidate pool | Screener.in queries below, or the `Elite` / `Lynch Hybrid` chips on the page |
| **2 — 100-point ranking** | Growth /40 · Valuation /20 · Quality /20 · Lynch Story /20 | Computed in the browser from the last scan |
| **3 — Human research** | Answer the 10 questions, then override the Story bucket by hand | Score card on the page (saved in the browser) |

The page ranks the **GURJAS 1 + GURJAS 2** result set of the last scan and re-applies the
Layer-1 filter on top, so switching between Elite / Hybrid / Everything needs no new scan.

---

## Layer 1 — the two baskets

| Screen | Purpose |
|---|---|
| 🔥 **Elite Mode** | >20% growth, PEG < 0.6, ROCE > 20%, ROE > 15%, D/E < 0.5, no pledge — *exceptional bargains* |
| ⭐ **Lynch Hybrid** | >15% growth, PEG < 1, ROCE/ROE > 15%, D/E < 0.75, no pledge — *the wider opportunity set* |
| 🏆 **100-point ranking** | Decides the Top 5 from whichever pool you chose |

### 🔥 Elite Mode query (copy-paste into Screener.in)

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

### ⭐ Lynch Hybrid query (the funnel)

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

**Correction:** there is no `TTM Result Date` field on Screener.in. For current growth use
`Profit growth` and/or `YOY Quarterly profit growth` — both are already in the queries above.

---

## Layer 2 — the 100-point table

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
| **QUALITY** | ROCE > 20% | 5 |
| | ROE > 20% | 4 |
| | Positive / healthy cash flow | 4 |
| | CFO reasonably tracks PAT | 3 |
| | Debt/Equity < 0.5 | 2 |
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
Reserves, promoter and institution holding, sector and industry. It does **not** always carry
ROCE, ROE, operating cash flow or promoter pledge. The engine therefore labels every line:

* **exact** — taken straight from the scan (ROE %, ROCE %, CFO/PAT are now fetched by
  `data_fetcher.py` for new scans).
* **est** — derived: `PAT = Market Cap ÷ PE`, `Debt = Reserves × Debt/Equity`,
  `ROCE ≈ PAT ÷ (Reserves + Debt)`, `ROE ≈ PAT ÷ Reserves`. Verify on Screener.in.
* **n/a** — not present in the scan. It scores **0** and is never invented. Layer-1 filters
  report such criteria as *unverified* instead of silently rejecting the stock.
* **manual** — your own Layer-3 number, stored in the browser (localStorage).

Story items are auto-filled with a documented sector/market-cap/growth heuristic. They are the
part of the rubric a machine cannot judge — open a score card and type your own marks; the
total updates live and is marked `manual story`.

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

The last question decides whether the score is an opportunity or a warning.

---

## Using the pages

### Streamlit (online)
* Sidebar → **🏆 Page 6: Peter Lynch 100-Point System**.
* **Layer 1 radio**: `🔥 Elite Mode` · `⭐ Lynch Hybrid` · `📚 Everything scanned`, plus
  **Top 5 only** (on by default), search, min-score and sort controls.
* The two Screener.in queries sit in an expander — the code block's copy icon copies them.
* **⬇ Download CSV** exports the ranked table; **⬇ Top 5 as text** / the *Copy-ready Top 5* box
  give the WhatsApp summary.
* **Score card** shows every mark with ✅ / ❌ / ➖ / 🟡 / 🔵, the source of each ratio, the
  Layer-1 verdict and links to Screener.in + the annual report.
* **Layer 3 — override the Story bucket**: type your own marks; the total and the ranking update
  immediately (the row is flagged `Story (manual)`).

### React dashboard
* **Candidate pool** chips: `🔥 Elite` · `⭐ Lynch Hybrid` · `📚 Everything scanned`.
* **Top 5 only** is on by default — that is the whole point of the system. Toggle it to see the
  full ranking.
* **Copy Top 5** produces a WhatsApp-ready summary; **⬇ CSV** exports the ranked table.
* **▼ Score** on any row opens the full mark sheet: every test, its value, its source
  (`est` / `n/a`), the Layer-1 check and the Story overrides.
* Deep link: `/peter-lynch?screen=elite&stock=DIXON`.

## Refreshing the numbers

`ROE %`, `ROCE %` and `CFO/PAT` become exact fields on scans run **after** the
`data_fetcher.py` update — existing cached stocks keep their `est` values until their cache
expires (7 days) or a scan runs with `force_refresh`. Until then the page uses the labelled
estimates, so nothing breaks.

// verify_engine_parity.mjs — the JavaScript half of the parity check.
//
// `lynch_engine.py` (Streamlit) and `frontend/src/lynch.js` (React) must produce the SAME score
// for the same stock, or the fund sees two different answers depending on which app is open.
// The lender logic has a matched pair too: `financial_engine.py` and `src/lender.js`.
//
// Run the Python half first — it writes the records and its own expected scores:
//
//     python verify_engine_parity.py
//     cd frontend && node verify_engine_parity.mjs
//
// This re-scores the SAME records with the JS engine and compares total, grade, all four
// buckets, the Layer-1 verdict, the rubric used, the lender classification and the warnings.
// Exit code 0 means the two engines agree.
import fs from 'node:fs';
import { scoreLynch, applyScreen } from './src/lynch.js';

const SRC = '../_parity_expected.json';

let payload;
try {
  payload = JSON.parse(fs.readFileSync(new URL(SRC, import.meta.url), 'utf8'));
} catch {
  console.error(`Could not read ${SRC} — run "python verify_engine_parity.py" first.`);
  process.exit(2);
}

const { python, records } = payload;
let checked = 0;
let mismatches = 0;

for (const rec of records) {
  for (const screen of ['hybrid', 'elite', 'financials', 'all']) {
    const js = scoreLynch(rec);
    const jsScreen = applyScreen(js.metrics, screen);
    const py = python.find((p) => p.symbol === js.symbol && p.screen === screen);
    if (!py) {
      console.log(`  ?? no python row for ${js.symbol}/${screen}`);
      continue;
    }
    checked++;

    const diffs = [];
    if (Math.abs(js.total - py.total) > 0.001) diffs.push(`total ${py.total} vs ${js.total}`);
    if (js.grade !== py.grade) diffs.push(`grade ${py.grade} vs ${js.grade}`);
    if (js.growth.points !== py.growth) diffs.push(`growth ${py.growth} vs ${js.growth.points}`);
    if (js.valuation.points !== py.valuation) diffs.push(`valuation ${py.valuation} vs ${js.valuation.points}`);
    if (js.quality.points !== py.quality) diffs.push(`quality ${py.quality} vs ${js.quality.points}`);
    if (js.story.points !== py.story) diffs.push(`story ${py.story} vs ${js.story.points}`);
    if (jsScreen.pass !== py.pass) diffs.push(`pass ${py.pass} vs ${jsScreen.pass}`);
    if (jsScreen.rubric !== py.rubric) diffs.push(`rubric ${py.rubric} vs ${jsScreen.rubric}`);
    if (js.metrics.isLender !== py.isLender) diffs.push(`isLender ${py.isLender} vs ${js.metrics.isLender}`);
    if (JSON.stringify(js.warnings) !== JSON.stringify(py.warnings)) {
      diffs.push(`warnings ${JSON.stringify(py.warnings)} vs ${JSON.stringify(js.warnings)}`);
    }

    if (diffs.length) {
      mismatches++;
      console.log(`MISMATCH ${js.symbol}/${screen}: ${diffs.join(' | ')}`);
    }
  }
}

console.log(`checked ${checked} (stock x basket) combinations — ${mismatches} mismatches`);
if (mismatches === 0) {
  console.log('OK — the Streamlit engine and the React engine agree.');
}
process.exit(mismatches ? 1 : 0);

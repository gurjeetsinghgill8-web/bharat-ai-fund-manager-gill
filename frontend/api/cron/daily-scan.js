// api/cron/daily-scan.js — Vercel Serverless Function
// Phase 4 / Brick 4.2
//
// Called by Vercel Cron at 10:05 AM IST (4:35 AM UTC) Mon-Fri
// Triggers the daily GURJAS scan + portfolio sync on HF Space backend.
// Backend does the heavy work — this is just the trigger.

export default async function handler(req, res) {
  const HF_URL  = process.env.HF_BACKEND_URL;
  const API_KEY = process.env.BACKEND_API_KEY || 'bharat-ai-secret-2026';

  if (!HF_URL) {
    return res.status(500).json({ error: 'HF_BACKEND_URL not set' });
  }

  const results = {};

  // 1. Trigger full scan
  try {
    const scanRes = await fetch(`${HF_URL}/api/scan/run?universe=0`, {
      method: 'POST',
      headers: { 'x-api-key': API_KEY, 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(30000),
    });
    results.scan = { status: scanRes.status, data: await scanRes.json().catch(() => ({})) };
  } catch (e) {
    results.scan = { error: e.message };
  }

  // 2. Trigger portfolio sync
  try {
    const syncRes = await fetch(`${HF_URL}/api/portfolio/sync`, {
      method: 'POST',
      headers: { 'x-api-key': API_KEY, 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(30000),
    });
    results.portfolio_sync = { status: syncRes.status, data: await syncRes.json().catch(() => ({})) };
  } catch (e) {
    results.portfolio_sync = { error: e.message };
  }

  console.log(`[Cron/DailyScan] Results:`, JSON.stringify(results));

  return res.status(200).json({
    success: true,
    triggered_at: new Date().toISOString(),
    results,
  });
}

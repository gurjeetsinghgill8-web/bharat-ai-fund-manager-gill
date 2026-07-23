// api/cron/wake.js — Vercel Serverless Function
// Phase 4 / Brick 4.2
//
// Called by Vercel Cron to keep Hugging Face Space warm.
// HF Spaces sleep after ~15 min inactivity — this ping wakes it up
// before market hours so users don't experience cold-start delay.
//
// Schedule (in vercel.json):
//   Mon-Fri 9:30 AM IST (4:00 AM UTC)   — pre-market warm-up
//   Mon-Fri 10:00 AM IST (4:30 AM UTC)  — market open scan trigger

export default async function handler(req, res) {
  const HF_URL = process.env.HF_BACKEND_URL;
  const API_KEY = process.env.BACKEND_API_KEY || 'bharat-ai-secret-2026';

  if (!HF_URL) {
    return res.status(500).json({ error: 'HF_BACKEND_URL not set in Vercel env vars' });
  }

  try {
    const start = Date.now();

    // Ping the /api/wake endpoint
    const response = await fetch(`${HF_URL}/api/wake`, {
      method: 'GET',
      headers: { 'x-api-key': API_KEY },
      signal: AbortSignal.timeout(30000), // 30s timeout
    });

    const elapsed = Date.now() - start;
    const data = await response.json().catch(() => ({}));

    console.log(`[Cron/Wake] HF Space responded in ${elapsed}ms — status: ${response.status}`);

    return res.status(200).json({
      success: true,
      hf_status: response.status,
      hf_response: data,
      ping_ms: elapsed,
      cron_time: new Date().toISOString(),
    });

  } catch (err) {
    console.error(`[Cron/Wake] Failed to ping HF Space: ${err.message}`);
    return res.status(500).json({
      success: false,
      error: err.message,
      cron_time: new Date().toISOString(),
    });
  }
}

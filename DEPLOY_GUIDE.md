# 🚀 BHARAT AI FUND MANAGER GILL — DEPLOYMENT GUIDE
**Version:** 2.0 (Decoupled Architecture)
**Date:** July 2026
**Stack:** Supabase · FastAPI (HF Spaces) · React (Vercel)

---

## 📋 PRE-FLIGHT CHECKLIST

Before you start, have these accounts ready (all free):

| Service | URL | Cost |
|---|---|---|
| GitHub | github.com | FREE |
| Supabase | supabase.com | FREE (500MB) |
| Hugging Face | huggingface.co | FREE |
| Vercel | vercel.com | FREE |

> **Time needed:** ~45 minutes total for first deployment.

---

## PHASE 1 — SUPABASE (Database) ⏱ ~10 min

### Step 1.1 — Create Project

1. Go to **[supabase.com](https://supabase.com)** → Sign Up → New Project
2. Fill in:
   - **Project name:** `bharat-ai-fund-manager`
   - **Database password:** (save this somewhere safe!)
   - **Region:** `South Asia (Singapore)` — closest to India
3. Wait 2 minutes for project to spin up

### Step 1.2 — Run the Schema

1. In Supabase dashboard → left sidebar → **SQL Editor**
2. Click **New Query**
3. Open the file `supabase_schema.sql` from your project folder
4. Copy the **entire contents** → paste into SQL Editor → click **Run**
5. You should see: `Success. No rows returned`

### Step 1.3 — Get Your Credentials

1. Left sidebar → **Settings** → **API**
2. Copy two values:

```
Project URL:    https://xxxxxxxxxxxx.supabase.co
Service Role Key:  eyJhbGci...  (the LONG one under "service_role")
```

> ⚠️ Use the **service_role** key — NOT the anon key. The service key bypasses RLS and is needed for backend writes.

### Step 1.4 — Update Your .env File

Open `c:\Users\pc\Desktop\BHARAT-SYSTEMS\BHARAT AI FUND MANAGER GILL\.env`

Replace the placeholder lines:

```env
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Step 1.5 — Run Migration Script

Open a terminal in your project folder and run:

```bash
python migrate_sqlite_to_supabase.py
```

Expected output:
```
[Supabase] Connection OK
Migrating users...
  Created user: Gurjas
Migrating portfolios...
  Migrated X holdings for 'Gurjas'
Migration complete!
```

### Step 1.6 — Verify in Supabase

Supabase dashboard → **Table Editor** → check these tables have data:
- `users` — should have at least 1 row (Gurjas)
- `portfolios` — should have your holdings
- `scan_cache` — will be empty until first scan (that's OK)

✅ **Supabase DONE**

---

## PHASE 2 — HUGGING FACE SPACES (Backend API) ⏱ ~15 min

### Step 2.1 — Create a New HF Space

1. Go to **[huggingface.co](https://huggingface.co)** → Sign in
2. Click your profile → **New Space**
3. Fill in:
   - **Space name:** `bharat-ai-backend`
   - **SDK:** Select **Docker**
   - **Visibility:** Private (recommended) or Public
4. Click **Create Space**

### Step 2.2 — Prepare Files to Upload

You need to upload these files to HF Space (NOT your entire project — just these):

```
📁 Files to upload to HF Space:
├── Dockerfile                    ✅ Already created
├── requirements_fastapi.txt      ✅ Already created
├── fastapi_app/
│   └── main.py                   ✅ Already created
├── supabase_db.py                ✅ Already created
├── db.py                         (existing file)
├── data_fetcher.py               (existing file)
├── scoring_engine.py             (existing file)
├── portfolio_manager.py          (existing file)
├── llm_harness.py                (existing file)
├── email_dispatcher.py           (existing file)
├── report_generator.py           (existing file)
├── symbols.py                    (existing file)
├── sector_industry.py            (existing file)
└── jarvis_keys.txt               (existing file — your API keys)
```

### Step 2.3 — Upload Files to HF Space

**Option A: Via HF Web UI (easiest)**

1. In your new HF Space → click **Files** tab → **Add file** → **Upload files**
2. Upload all files listed above one-by-one or drag-drop multiple
3. For the `fastapi_app/` folder: upload `main.py` and it will create the subfolder

**Option B: Via Git (recommended for updates)**

```bash
# In your project folder terminal:
git clone https://huggingface.co/spaces/YOUR_HF_USERNAME/bharat-ai-backend
cd bharat-ai-backend

# Copy all required files into this folder
# Then:
git add .
git commit -m "Initial FastAPI deployment"
git push
```

> Replace `YOUR_HF_USERNAME` with your actual HF username.

### Step 2.4 — Set Secret Environment Variables

1. HF Space → **Settings** tab → **Variables and secrets** section
2. Click **New secret** for each:

| Secret Name | Value |
|---|---|
| `SUPABASE_URL` | `https://xxxxxxxxxxxx.supabase.co` |
| `SUPABASE_SERVICE_KEY` | `eyJhbGci...` (service role key) |
| `FASTAPI_SECRET_KEY` | `bharat-ai-secret-2026` (or change it) |
| `GEMINI_API_KEY` | Your Google Gemini API key |
| `SMTP_USER` | `gurjeetsinghgill8@gmail.com` |
| `SMTP_PASSWORD` | Your Gmail app password |

> 🔐 Use the **Secrets** section (not Variables) — secrets are never exposed in logs.

### Step 2.5 — Wait for Build

1. HF Space → **App** tab — watch the build logs
2. Build takes 3-5 minutes (installing Python deps)
3. When you see `Application startup complete.` — it's live!

### Step 2.6 — Test the API

Your HF Space URL format is:
```
https://YOUR_HF_USERNAME-bharat-ai-backend.hf.space
```

Test in browser:
```
https://YOUR_HF_USERNAME-bharat-ai-backend.hf.space/health
```

Expected response:
```json
{
  "status": "healthy",
  "supabase": "connected",
  "last_scan": null,
  "version": "2.0"
}
```

Also test the interactive API docs:
```
https://YOUR_HF_USERNAME-bharat-ai-backend.hf.space/docs
```

✅ **Hugging Face DONE**

---

## PHASE 3 — VERCEL (React Frontend) ⏱ ~10 min

### Step 3.1 — Update Frontend Environment

Open `frontend\.env` and update the production URL:

```env
VITE_API_BASE_URL=https://YOUR_HF_USERNAME-bharat-ai-backend.hf.space
VITE_API_KEY=bharat-ai-secret-2026
```

> Replace `YOUR_HF_USERNAME` with your actual HF username.

### Step 3.2 — Push Frontend to GitHub

```bash
# From your project folder:
cd frontend

# Initialize git (if not done)
git init
git add .
git commit -m "Bharat AI Fund Manager - React Frontend v2.0"

# Create new repo on github.com named: bharat-ai-frontend
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/bharat-ai-frontend.git
git push -u origin main
```

### Step 3.3 — Deploy to Vercel

**Option A: Vercel CLI (easiest)**

```bash
# In the frontend/ folder:
npx vercel

# When prompted:
# ? Set up and deploy? Yes
# ? Which scope? (your account)
# ? Link to existing project? No
# ? Project name? bharat-ai-frontend
# ? Directory? ./  (current directory)
```

**Option B: Vercel Website**

1. Go to **[vercel.com](https://vercel.com)** → Sign in → **New Project**
2. Import from GitHub → select `bharat-ai-frontend`
3. Framework Preset: **Vite**
4. Root Directory: `frontend` (if deploying from main repo)
5. Click **Deploy**

### Step 3.4 — Set Vercel Environment Variables

1. Vercel dashboard → your project → **Settings** → **Environment Variables**
2. Add these:

| Name | Value | Environment |
|---|---|---|
| `VITE_API_BASE_URL` | `https://YOUR_HF_USERNAME-bharat-ai-backend.hf.space` | All |
| `VITE_API_KEY` | `bharat-ai-secret-2026` | All |
| `HF_BACKEND_URL` | `https://YOUR_HF_USERNAME-bharat-ai-backend.hf.space` | All |
| `BACKEND_API_KEY` | `bharat-ai-secret-2026` | All |

3. Click **Redeploy** after adding env vars

### Step 3.5 — Verify Cron Jobs

1. Vercel dashboard → project → **Settings** → **Cron Jobs**
2. You should see 4 cron jobs listed:
   - Wake (9:30 AM IST Mon-Fri)
   - Wake (10:00 AM IST Mon-Fri)
   - Daily Scan (10:05 AM IST Mon-Fri)
   - Wake (4:00 PM Mon-Fri)

> ⚠️ Vercel Cron Jobs require the **Hobby plan** (free) — make sure you're on it.

### Step 3.6 — Test Your Live Frontend

Your Vercel URL will be:
```
https://bharat-ai-frontend.vercel.app
```

Open it in browser — you should see the premium dark dashboard!

✅ **Vercel DONE**

---

## PHASE 4 — POST-DEPLOYMENT VERIFICATION ⏱ ~5 min

Run through this checklist after deployment:

### ✅ Backend Health Check
```
GET https://YOUR_HF_USERNAME-bharat-ai-backend.hf.space/health
```
Expected: `{"status": "healthy", "supabase": "connected"}`

### ✅ Frontend Loads
Open your Vercel URL — sidebar shows 5 pages, dark theme loads.

### ✅ Portfolio Page
- Add a test stock (e.g., `RELIANCE`, buy price `2500`, qty `5`)
- It should appear in the table
- Click **Sync Prices** — LTP should update

### ✅ Scan Test
- Go to GURJAS 1 page → click **Run Scan**
- Should show: "Scan triggered — running in background"
- Wait 30-60 seconds → click Refresh → results appear

### ✅ AI Analysis Test
- Go to Portfolio page → click **Ask** next to any stock
- Should return JARVIS AI analysis within 10 seconds

---

## 🔄 HOW TO UPDATE THE APP LATER

### Update Backend (Python code changes):
```bash
cd bharat-ai-backend  # your HF Space git clone
# copy updated files
git add .
git commit -m "Update: description"
git push
# HF Space auto-rebuilds in ~3 min
```

### Update Frontend (React code changes):
```bash
cd frontend
git add .
git commit -m "Update: description"
git push
# Vercel auto-deploys in ~1 min
```

---

## 🛠️ TROUBLESHOOTING

### "Backend not responding" / 503 error
- HF Space may be sleeping (cold start takes 30-60 seconds)
- Visit `https://YOUR_HF_USERNAME-bharat-ai-backend.hf.space/health` directly to wake it
- Cron jobs run every morning to prevent this

### "Invalid API key" from Supabase
- Double-check you used the **service_role** key, not the **anon** key
- Re-check there are no spaces before/after the key value

### Scan shows 0 results
- First scan on fresh Supabase takes 10-20 minutes (4000+ stocks)
- Check HF Space logs for errors
- Verify GEMINI_API_KEY is set (used for scoring)

### CORS error in browser console
- The FastAPI backend already has CORS configured for `*`
- If using a custom domain on Vercel, add it to `ALLOWED_ORIGINS` in `fastapi_app/main.py`

### Portfolio sync fails
- Check that `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are set in HF Spaces secrets
- Verify the `supabase_schema.sql` was run successfully

---

## 📁 COMPLETE FILE MAP

```
BHARAT AI FUND MANAGER GILL/
│
├── 🐍 PYTHON BACKEND (uploaded to HF Spaces)
│   ├── fastapi_app/
│   │   └── main.py              ← FastAPI app (20 endpoints)
│   ├── supabase_db.py           ← Supabase REST client
│   ├── db.py                    ← SQLite (legacy, kept for Streamlit)
│   ├── data_fetcher.py          ← yfinance data engine
│   ├── scoring_engine.py        ← GURJAS 1/2 scoring logic
│   ├── portfolio_manager.py     ← Portfolio CRUD + alerts
│   ├── llm_harness.py           ← Gemini/Groq/xAI AI engine
│   ├── email_dispatcher.py      ← Email alerts
│   ├── report_generator.py      ← Excel/PDF reports
│   ├── sector_industry.py       ← Sector mapping
│   ├── symbols.py               ← NSE ticker universe
│   ├── Dockerfile               ← HF Spaces Docker config
│   └── requirements_fastapi.txt ← Backend dependencies
│
├── ⚛️  REACT FRONTEND (deployed to Vercel)
│   └── frontend/
│       ├── src/
│       │   ├── App.jsx          ← Sidebar + routing
│       │   ├── api.js           ← All API calls
│       │   ├── index.css        ← Design system
│       │   └── pages/
│       │       ├── Dashboard.jsx  ← Page 1: Portfolio
│       │       ├── Gurjas1.jsx    ← Page 2: GURJAS 1
│       │       ├── Gurjas2.jsx    ← Page 3: GURJAS 2
│       │       ├── Momentum.jsx   ← Page 4: Momentum
│       │       └── Sectors.jsx    ← Page 5: Sectors
│       ├── api/cron/
│       │   ├── wake.js          ← Vercel cron: HF wake-up
│       │   └── daily-scan.js    ← Vercel cron: scan trigger
│       ├── vercel.json          ← Vercel config + cron schedule
│       └── .env                 ← API URL (not committed to git)
│
├── 🗄️  DATABASE
│   ├── supabase_schema.sql      ← Run this in Supabase SQL editor
│   └── migrate_sqlite_to_supabase.py ← One-time migration script
│
└── 📱 LEGACY STREAMLIT (keep running until migration verified)
    └── app.py                   ← Original Streamlit app
```

---

## 🎯 ARCHITECTURE DIAGRAM

```
┌─────────────────────────────────────────────────────────────┐
│                    USER'S BROWSER                           │
│            https://bharat-ai-frontend.vercel.app            │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTPS API calls
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              FASTAPI BACKEND (Hugging Face Spaces)           │
│    https://YOUR_HF_USERNAME-bharat-ai-backend.hf.space       │
│                                                             │
│  Endpoints: /health /api/scan/* /api/portfolio/* /api/users  │
│  Startup:   catch-up scan runs on every cold start           │
└──────────────┬──────────────────────────┬───────────────────┘
               │ SQL REST API             │ yfinance / Gemini
               ▼                          ▼
┌──────────────────────────┐   ┌─────────────────────────────┐
│  SUPABASE (PostgreSQL)   │   │  EXTERNAL APIS               │
│  supabase.com            │   │  • Yahoo Finance (prices)    │
│                          │   │  • Google Gemini (AI)        │
│  Tables:                 │   │  • Screener.in (financials)  │
│  • users                 │   │  • SMTP Gmail (alerts)       │
│  • portfolios            │   └─────────────────────────────┘
│  • scan_cache            │
│  • gurjas_results        │
│  • scan_meta             │
└──────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│               VERCEL CRON JOBS (Free)                        │
│  Mon-Fri 9:30 AM IST  → Wake HF Space (pre-market)         │
│  Mon-Fri 10:00 AM IST → Wake HF Space (at open)            │
│  Mon-Fri 10:05 AM IST → Trigger scan + portfolio sync       │
│  Mon-Fri 4:00 PM IST  → Wake HF Space (pre-close)          │
└─────────────────────────────────────────────────────────────┘
```

---

*Bharat AI Fund Manager Gill — Built by Gurjas × Antigravity AI*
*Total cost to run: ₹0/month*

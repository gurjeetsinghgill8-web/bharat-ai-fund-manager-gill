---
title: Bharat AI Fund Manager Gill — Backend API
emoji: 📈
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: true
license: mit
app_port: 7860
---

# Bharat AI Fund Manager Gill — FastAPI Backend

**FastAPI + Python backend for the Bharat AI Fund Manager.**

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check + last scan info |
| GET | `/api/wake` | Vercel cron wake-up ping |
| POST | `/api/scan/run` | Trigger full GURJAS stock scan |
| GET | `/api/scan/status` | Scan running state + metadata |
| GET | `/api/scan/results/gurjas1` | GURJAS 1 screener results |
| GET | `/api/scan/results/gurjas2` | GURJAS 2 screener results |
| GET | `/api/portfolio/{user_id}` | Fetch user portfolio |
| POST | `/api/portfolio/{user_id}/add` | Add holding |
| DELETE | `/api/portfolio/{user_id}/{symbol}` | Remove holding |
| POST | `/api/portfolio/sync` | Sync all portfolio prices |
| GET | `/api/users` | List all users |
| POST | `/api/users` | Create user |
| GET | `/api/analysis/{symbol}` | JARVIS AI stock analysis |

## Architecture

```
React Frontend (Vercel) → FastAPI (Here) → Supabase (PostgreSQL)
```

## Environment Variables (Set in HF Spaces Secrets)

- `SUPABASE_URL` — Your Supabase project URL
- `SUPABASE_SERVICE_KEY` — Supabase service role key
- `FASTAPI_SECRET_KEY` — API key for protected endpoints
- `GEMINI_API_KEY` — Google Gemini API key
- `SMTP_USER`, `SMTP_PASSWORD` — Gmail for email alerts

-- ============================================================
-- BHARAT AI FUND MANAGER GILL — Supabase PostgreSQL Schema
-- Phase 1 / Brick 1.2
-- Run this ONCE in Supabase SQL Editor (Dashboard > SQL Editor > New Query)
-- ============================================================

-- TABLE: users
CREATE TABLE IF NOT EXISTS users (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT UNIQUE NOT NULL,
    email       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- TABLE: portfolios
CREATE TABLE IF NOT EXISTS portfolios (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol              TEXT NOT NULL,
    buy_price           REAL NOT NULL DEFAULT 0.0,
    quantity            INTEGER NOT NULL DEFAULT 0,
    ltp                 REAL NOT NULL DEFAULT 0.0,
    sma_200             REAL NOT NULL DEFAULT 0.0,
    dist_pct            REAL NOT NULL DEFAULT 0.0,
    above_sma           BOOLEAN NOT NULL DEFAULT FALSE,
    signal              TEXT NOT NULL DEFAULT 'WAIT',
    signal_strength     INTEGER NOT NULL DEFAULT 0,
    last_updated        TIMESTAMPTZ,
    alert_emailed_date  DATE,
    UNIQUE(user_id, symbol)
);

CREATE INDEX IF NOT EXISTS idx_portfolios_user_id ON portfolios(user_id);

-- TABLE: scan_cache (stores full 10-year financial data per ticker as JSONB)
CREATE TABLE IF NOT EXISTS scan_cache (
    ticker      TEXT PRIMARY KEY,
    data        JSONB NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- TABLE: scan_meta (single row — last scan timestamp)
CREATE TABLE IF NOT EXISTS scan_meta (
    id              INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    last_scan_time  TIMESTAMPTZ,
    total_stocks    INTEGER DEFAULT 0,
    scan_mode       TEXT DEFAULT 'Core 127'
);

-- Insert default scan_meta row
INSERT INTO scan_meta (id) VALUES (1)
ON CONFLICT (id) DO NOTHING;

-- TABLE: gurjas_results (latest GURJAS 1 & 2 screener results)
CREATE TABLE IF NOT EXISTS gurjas_results (
    id          BIGSERIAL PRIMARY KEY,
    screener    TEXT NOT NULL CHECK (screener IN ('GURJAS1', 'GURJAS2')),
    symbol      TEXT NOT NULL,
    data        JSONB NOT NULL,
    scanned_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gurjas_screener ON gurjas_results(screener, scanned_at DESC);

-- ============================================================
-- ROW LEVEL SECURITY (RLS) — Enable for security
-- ============================================================
ALTER TABLE users        ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolios   ENABLE ROW LEVEL SECURITY;
ALTER TABLE scan_cache   ENABLE ROW LEVEL SECURITY;
ALTER TABLE scan_meta    ENABLE ROW LEVEL SECURITY;
ALTER TABLE gurjas_results ENABLE ROW LEVEL SECURITY;

-- Service role bypass policy (FastAPI backend uses service_role key — full access)
CREATE POLICY "Service role full access - users"
    ON users FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access - portfolios"
    ON portfolios FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access - scan_cache"
    ON scan_cache FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access - scan_meta"
    ON scan_meta FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access - gurjas_results"
    ON gurjas_results FOR ALL USING (true) WITH CHECK (true);

-- ============================================================
-- Done! Verify with:
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
-- ============================================================

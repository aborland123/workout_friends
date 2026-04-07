-- ─── Squad Sweat — Supabase Setup ───────────────────────────────────────────
-- Run this in the Supabase SQL Editor (supabase.com → your project → SQL Editor)

-- 1. Workouts table
CREATE TABLE IF NOT EXISTS workouts (
    id            TEXT PRIMARY KEY,
    date          DATE NOT NULL,
    participants  TEXT NOT NULL,   -- stored as JSON array string, e.g. '["Alli","Liv"]'
    workout_type  TEXT,
    intensity     TEXT,            -- 'rest' | 'easy' | 'moderate' | 'hard' | 'beast'
    duration      INTEGER,         -- minutes
    notes         TEXT,
    photo         TEXT,            -- filename in workout-photos storage bucket
    logged_by     TEXT,
    points        INTEGER DEFAULT 0,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast per-person queries
CREATE INDEX IF NOT EXISTS idx_workouts_date ON workouts (date DESC);

-- 2. Row-level security (optional but recommended — allows public read)
ALTER TABLE workouts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read" ON workouts
    FOR SELECT USING (true);

CREATE POLICY "Allow public insert" ON workouts
    FOR INSERT WITH CHECK (true);

-- 3. Storage bucket for photos
-- Do this in the Supabase Dashboard → Storage → New Bucket:
--   Name:   workout-photos
--   Public: YES (so photos display in the feed without auth)
--
-- Or run via SQL (requires pg_storage extension, easier to do in the dashboard):
-- INSERT INTO storage.buckets (id, name, public) VALUES ('workout-photos', 'workout-photos', true);

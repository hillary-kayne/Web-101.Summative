CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tracker_entries (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    description VARCHAR(200) NOT NULL,
    category VARCHAR(50) NOT NULL,
    weight_kg NUMERIC(6, 2) NOT NULL,
    method VARCHAR(10) NOT NULL CHECK (method IN ('resold', 'recycled')),
    amount_earned NUMERIC(8, 2) NOT NULL DEFAULT 0,
    payer_name VARCHAR(100),
    water_saved_l NUMERIC(10, 1) NOT NULL,
    co2_saved_kg NUMERIC(8, 2) NOT NULL,
    entry_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tracker_entries_user ON tracker_entries (user_id);
CREATE INDEX IF NOT EXISTS idx_tracker_entries_date ON tracker_entries (entry_date);

-- Caches Geoapify geocode + places responses per query so repeat lookups for the
-- same city don't burn free-tier rate limits, and so a Geoapify outage can fall
-- back to the last good result instead of a blank screen.
CREATE TABLE IF NOT EXISTS geoapify_cache (
    cache_key VARCHAR(255) PRIMARY KEY,
    label VARCHAR(200),
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    response_json JSONB NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

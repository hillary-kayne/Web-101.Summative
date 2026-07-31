import json
import time

from db import get_cursor


def cache_get(cache_key, max_age_seconds=None):
    with get_cursor() as cur:
        cur.execute("SELECT * FROM geoapify_cache WHERE cache_key = %s", (cache_key,))
        row = cur.fetchone()
    if not row:
        return None
    age = time.time() - row["fetched_at"].timestamp()
    if max_age_seconds is not None and age > max_age_seconds:
        return None
    return row


def cache_put(cache_key, label, lat, lon, payload):
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO geoapify_cache (cache_key, label, lat, lon, response_json, fetched_at)
            VALUES (%s, %s, %s, %s, %s, now())
            ON CONFLICT (cache_key) DO UPDATE SET
                label = EXCLUDED.label, lat = EXCLUDED.lat, lon = EXCLUDED.lon,
                response_json = EXCLUDED.response_json, fetched_at = now()
            """,
            (cache_key, label, lat, lon, json.dumps(payload)),
        )

import math

import requests

from config import config
from errors import ApiError
from locator.queries import cache_get, cache_put

GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"
PLACES_URL = "https://api.geoapify.com/v2/places"

# Geoapify's OSM-backed places data has no single category that separates
# charity shops from other second-hand/consignment stores, so both come back
# under commercial.second_hand. I bucket by name after the fact instead (see
# _classify below). Drop-off points come back under service.recycling
# (bins, containers, and staffed recycling centres alike).
PLACES_CATEGORIES = "commercial.second_hand,service.recycling"

CHARITY_KEYWORDS = (
    "charity", "hospice", "oxfam", "goodwill", "salvation army", "cancer research",
    "british heart foundation", "barnardo", "st vincent de paul", "red cross",
    "thrift store", "sue ryder", "shelter shop", "scope shop", "mind shop",
)

REQUEST_TIMEOUT = 8


def _haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


def _classify(name, categories):
    name_l = (name or "").lower()
    if any(cat.startswith("service.recycling") for cat in categories):
        return "bin"
    if any(k in name_l for k in CHARITY_KEYWORDS):
        return "charity_shop"
    return "secondhand_store"


def geocode_suggestions(query):
    if not config.GEOAPIFY_API_KEY:
        raise ApiError("Geocoding is not configured on the server", 502)
    cache_key = f"geocode:{query.strip().lower()}"
    try:
        resp = requests.get(
            GEOCODE_URL,
            params={"text": query, "apiKey": config.GEOAPIFY_API_KEY, "limit": 5, "format": "json"},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        suggestions = [
            {
                "label": r.get("formatted"),
                "lat": r.get("lat"),
                "lon": r.get("lon"),
            }
            for r in results
            if r.get("lat") is not None and r.get("lon") is not None
        ]
        cache_put(cache_key, query, None, None, suggestions)
        return suggestions, False
    except requests.RequestException:
        cached = cache_get(cache_key)
        if cached:
            return cached["response_json"], True
        raise ApiError("Location search is temporarily unavailable. Please try again shortly.", 502)


def search_places(lat, lon, radius_km, label=None):
    cache_key = f"places:{round(lat, 3)}:{round(lon, 3)}:{radius_km}"

    cached_fresh = cache_get(cache_key, max_age_seconds=config.GEOAPIFY_CACHE_TTL_SECONDS)
    if cached_fresh:
        return cached_fresh["response_json"], False

    if not config.GEOAPIFY_API_KEY:
        raise ApiError("Locator is not configured on the server", 502)

    try:
        resp = requests.get(
            PLACES_URL,
            params={
                "categories": PLACES_CATEGORIES,
                "filter": f"circle:{lon},{lat},{int(radius_km * 1000)}",
                "bias": f"proximity:{lon},{lat}",
                "limit": 100,
                "apiKey": config.GEOAPIFY_API_KEY,
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        features = resp.json().get("features", [])
        results = []
        for f in features:
            props = f.get("properties", {})
            p_lat, p_lon = props.get("lat"), props.get("lon")
            if p_lat is None or p_lon is None:
                continue
            categories = props.get("categories", [])
            results.append({
                "id": props.get("place_id"),
                "name": props.get("name") or "Unnamed location",
                "type": _classify(props.get("name"), categories),
                "address": props.get("formatted"),
                "lat": p_lat,
                "lon": p_lon,
                "distance_km": round(_haversine_km(lat, lon, p_lat, p_lon), 2),
                "rating": props.get("rating"),
            })
        results.sort(key=lambda r: r["distance_km"])
        cache_put(cache_key, label, lat, lon, results)
        return results, False
    except requests.RequestException:
        stale = cache_get(cache_key)
        if stale:
            return stale["response_json"], True
        raise ApiError("Geoapify is temporarily unavailable and no cached results exist for this area.", 502)

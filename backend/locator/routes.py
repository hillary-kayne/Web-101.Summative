from flask import Blueprint, jsonify, request

from errors import ApiError
from locator.service import geocode_suggestions, search_places

bp = Blueprint("locator", __name__, url_prefix="/api/locator")

VALID_TYPES = {"bin", "charity_shop", "secondhand_store"}


@bp.get("/geocode")
def geocode():
    query = (request.args.get("q") or "").strip()
    if len(query) < 2:
        raise ApiError("Enter at least 2 characters to search for a city", 400)
    # geoapify_cache.cache_key is VARCHAR(255) and includes this query text
    # ("geocode:" + query), so I cap it here rather than letting an overlong
    # query fail at the DB layer with a confusing error.
    if len(query) > 200:
        raise ApiError("Search text must be 200 characters or fewer", 400)
    suggestions, stale = geocode_suggestions(query)
    if not suggestions:
        raise ApiError(f'No locations found matching "{query}". Try a different spelling or add a country.', 404)
    return jsonify({"suggestions": suggestions, "stale": stale}), 200


@bp.get("/search")
def search():
    try:
        lat = float(request.args["lat"])
        lon = float(request.args["lon"])
    except (KeyError, ValueError):
        raise ApiError("lat and lon query parameters are required and must be numeric", 400)
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise ApiError("lat must be between -90 and 90, lon between -180 and 180", 400)

    label = request.args.get("label")
    if label and len(label) > 200:
        raise ApiError("label must be 200 characters or fewer", 400)

    radius_km = request.args.get("radius_km", "10")
    try:
        radius_km = max(1, min(50, float(radius_km)))
    except ValueError:
        raise ApiError("radius_km must be numeric", 400)

    types_param = request.args.get("types")
    types = None
    if types_param:
        types = {t.strip() for t in types_param.split(",") if t.strip()}
        if not types.issubset(VALID_TYPES):
            raise ApiError(f"types must be a subset of {sorted(VALID_TYPES)}", 400)

    sort_by = request.args.get("sort", "distance")
    if sort_by not in ("distance", "rating"):
        raise ApiError("sort must be 'distance' or 'rating'", 400)

    results, stale = search_places(lat, lon, radius_km, label=label)

    if types:
        results = [r for r in results if r["type"] in types]

    if sort_by == "rating":
        results = sorted(results, key=lambda r: (r["rating"] is None, -(r["rating"] or 0)))

    message = None
    if not results:
        message = f"No drop-off points found within {radius_km:.0f} km. Try widening the radius."

    return jsonify({
        "results": results,
        "count": len(results),
        "radius_km": radius_km,
        "stale": stale,
        "message": message,
    }), 200

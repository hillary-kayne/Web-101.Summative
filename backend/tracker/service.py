from datetime import date, datetime

from errors import ApiError
from tracker import queries
from tracker.impact_factors import (
    AVG_DAILY_DRINKING_WATER_L,
    calc_impact,
    default_weight_for_category,
)

MAX_REASONABLE_EARNED = 100000
MAX_REASONABLE_WEIGHT_KG = 50


def _parse_number(value, field_name, min_value=None, max_value=None, allow_none=False):
    if value is None or value == "":
        if allow_none:
            return None
        raise ApiError(f"{field_name} is required", 400)
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ApiError(f"{field_name} must be a number", 400)
    if number != number:  # NaN
        raise ApiError(f"{field_name} must be a number", 400)
    if min_value is not None and number < min_value:
        raise ApiError(f"{field_name} cannot be less than {min_value}", 400)
    if max_value is not None and number > max_value:
        raise ApiError(f"{field_name} is unrealistically large", 400)
    return number


def _parse_date(value):
    if not value:
        return date.today()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ApiError("entry_date must be in YYYY-MM-DD format", 400)


def create_entry(user_id, data):
    description = (data.get("description") or "").strip()
    if not description:
        raise ApiError("description is required", 400)
    if len(description) > 200:
        raise ApiError("description must be 200 characters or fewer", 400)

    category = (data.get("category") or "other").strip().lower().replace(" ", "_")
    if len(category) > 50:
        raise ApiError("category must be 50 characters or fewer", 400)

    method = (data.get("method") or "").strip().lower()
    if method not in ("resold", "recycled"):
        raise ApiError("method must be 'resold' or 'recycled'", 400)

    weight_kg = _parse_number(
        data.get("weight_kg"), "weight_kg", min_value=0.01, max_value=MAX_REASONABLE_WEIGHT_KG, allow_none=True
    )
    if weight_kg is None:
        weight_kg = default_weight_for_category(category)

    amount_earned = _parse_number(
        data.get("amount_earned"), "amount_earned", min_value=0, max_value=MAX_REASONABLE_EARNED, allow_none=True
    )
    if amount_earned is None:
        amount_earned = 0.0

    payer_name = (data.get("payer_name") or "").strip() or None
    if payer_name and len(payer_name) > 100:
        raise ApiError("payer_name must be 100 characters or fewer", 400)
    entry_date = _parse_date(data.get("entry_date"))

    water_saved_l, co2_saved_kg = calc_impact(weight_kg, method)

    row = queries.insert_entry({
        "user_id": user_id,
        "description": description,
        "category": category,
        "weight_kg": weight_kg,
        "method": method,
        "amount_earned": amount_earned,
        "payer_name": payer_name,
        "water_saved_l": water_saved_l,
        "co2_saved_kg": co2_saved_kg,
        "entry_date": entry_date,
    })
    return row


def get_entries(user_id, args):
    sort = args.get("sort", "date")
    order = args.get("order", "desc")
    return queries.list_entries(
        user_id,
        category=args.get("category"),
        method=args.get("method") if args.get("method") in ("resold", "recycled") else None,
        date_from=args.get("date_from"),
        date_to=args.get("date_to"),
        q=args.get("q"),
        sort=sort if sort in ("date", "amount_earned", "amount_saved") else "date",
        order=order if order in ("asc", "desc") else "desc",
    )


def remove_entry(user_id, entry_id):
    deleted = queries.delete_entry(user_id, entry_id)
    if not deleted:
        raise ApiError("Entry not found", 404)


def get_summary(user_id):
    totals = queries.get_totals(user_id)
    trend_week = queries.get_trend(user_id, "week")
    trend_month = queries.get_trend(user_id, "month")
    total_water_l = float(totals["total_water_l"])
    return {
        "total_earned": float(totals["total_earned"]),
        "total_water_l": total_water_l,
        "total_co2_kg": float(totals["total_co2_kg"]),
        "total_items": totals["total_items"],
        "drinking_water_days_equivalent": round(total_water_l / AVG_DAILY_DRINKING_WATER_L, 1),
        "trend_week": [
            {"period": str(r["period"]), "earned": float(r["earned"]),
             "water_l": float(r["water_l"]), "co2_kg": float(r["co2_kg"])}
            for r in trend_week
        ],
        "trend_month": [
            {"period": str(r["period"]), "earned": float(r["earned"]),
             "water_l": float(r["water_l"]), "co2_kg": float(r["co2_kg"])}
            for r in trend_month
        ],
    }

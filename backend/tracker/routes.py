from flask import Blueprint, g, jsonify, request

from auth.service import require_auth
from tracker.service import create_entry, get_entries, get_summary, remove_entry

bp = Blueprint("tracker", __name__, url_prefix="/api/tracker")


def _serialize(row):
    return {
        "id": row["id"],
        "description": row["description"],
        "category": row["category"],
        "weight_kg": float(row["weight_kg"]),
        "method": row["method"],
        "amount_earned": float(row["amount_earned"]),
        "payer_name": row["payer_name"],
        "water_saved_l": float(row["water_saved_l"]),
        "co2_saved_kg": float(row["co2_saved_kg"]),
        "entry_date": str(row["entry_date"]),
        "created_at": row["created_at"].isoformat(),
    }


@bp.get("/entries")
@require_auth
def list_entries_route():
    rows = get_entries(g.user_id, request.args)
    return jsonify({"entries": [_serialize(r) for r in rows]}), 200


@bp.post("/entries")
@require_auth
def create_entry_route():
    data = request.get_json(silent=True) or {}
    row = create_entry(g.user_id, data)
    return jsonify(_serialize(row)), 201


@bp.delete("/entries/<int:entry_id>")
@require_auth
def delete_entry_route(entry_id):
    remove_entry(g.user_id, entry_id)
    return "", 204


@bp.get("/summary")
@require_auth
def summary_route():
    return jsonify(get_summary(g.user_id)), 200

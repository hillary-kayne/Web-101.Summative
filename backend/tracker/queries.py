from db import get_cursor

SORT_COLUMNS = {
    "date": "entry_date",
    "amount_earned": "amount_earned",
    "amount_saved": "co2_saved_kg",
}


def insert_entry(fields):
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO tracker_entries
                (user_id, description, category, weight_kg, method, amount_earned,
                 payer_name, water_saved_l, co2_saved_kg, entry_date)
            VALUES (%(user_id)s, %(description)s, %(category)s, %(weight_kg)s, %(method)s,
                    %(amount_earned)s, %(payer_name)s, %(water_saved_l)s, %(co2_saved_kg)s,
                    %(entry_date)s)
            RETURNING *
            """,
            fields,
        )
        return cur.fetchone()


def list_entries(user_id, category=None, method=None, date_from=None, date_to=None,
                  q=None, sort="date", order="desc"):
    clauses = ["user_id = %(user_id)s"]
    params = {"user_id": user_id}

    if category:
        clauses.append("category = %(category)s")
        params["category"] = category
    if method:
        clauses.append("method = %(method)s")
        params["method"] = method
    if date_from:
        clauses.append("entry_date >= %(date_from)s")
        params["date_from"] = date_from
    if date_to:
        clauses.append("entry_date <= %(date_to)s")
        params["date_to"] = date_to
    if q:
        clauses.append("(description ILIKE %(q)s OR payer_name ILIKE %(q)s)")
        params["q"] = f"%{q}%"

    # sort_col/order_sql are interpolated directly rather than passed as query
    # params because column/direction names can't be bound placeholders in
    # psycopg2. Safe here only because both come from the fixed whitelists
    # above (SORT_COLUMNS, the asc/desc check), never from raw user input.
    sort_col = SORT_COLUMNS.get(sort, "entry_date")
    order_sql = "ASC" if order == "asc" else "DESC"

    sql = f"""
        SELECT * FROM tracker_entries
        WHERE {' AND '.join(clauses)}
        ORDER BY {sort_col} {order_sql}, id {order_sql}
    """
    with get_cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def delete_entry(user_id, entry_id):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM tracker_entries WHERE id = %s AND user_id = %s RETURNING id",
            (entry_id, user_id),
        )
        return cur.fetchone() is not None


def get_totals(user_id):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT
                COALESCE(SUM(amount_earned), 0) AS total_earned,
                COALESCE(SUM(water_saved_l), 0) AS total_water_l,
                COALESCE(SUM(co2_saved_kg), 0) AS total_co2_kg,
                COUNT(*) AS total_items
            FROM tracker_entries WHERE user_id = %s
            """,
            (user_id,),
        )
        return cur.fetchone()


def get_trend(user_id, granularity):
    bucket = "week" if granularity == "week" else "month"
    with get_cursor() as cur:
        cur.execute(
            f"""
            SELECT
                date_trunc(%s, entry_date)::date AS period,
                COALESCE(SUM(amount_earned), 0) AS earned,
                COALESCE(SUM(water_saved_l), 0) AS water_l,
                COALESCE(SUM(co2_saved_kg), 0) AS co2_kg
            FROM tracker_entries
            WHERE user_id = %s
            GROUP BY period
            ORDER BY period ASC
            """,
            (bucket, user_id),
        )
        return cur.fetchall()

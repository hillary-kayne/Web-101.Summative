import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool

from config import config

_pool = None


def get_pool():
    global _pool
    if _pool is None:
        # 20 is comfortably above gunicorn's worker count (3, see
        # deploy/rethread.service), so workers never starve each other for a
        # connection under normal load.
        _pool = SimpleConnectionPool(1, 20, dsn=config.DATABASE_URL)
    return _pool


@contextmanager
def get_cursor(commit=False):
    pool = get_pool()
    conn = pool.getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            yield cur
            if commit:
                conn.commit()
        finally:
            cur.close()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def init_db():
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path) as f:
        schema_sql = f.read()
    with get_cursor(commit=True) as cur:
        cur.execute(schema_sql)

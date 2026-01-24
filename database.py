import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "caddymate_store.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def get_categories():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM categories ORDER BY name ASC")
        return cur.fetchall()

def get_items_for_category(category_id):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT name, aisle
            FROM items
            WHERE category_id = ?
            ORDER BY name ASC
            """,
            (category_id,)
        )
        return cur.fetchall()

def get_all_items():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT name, aisle
            FROM items
            ORDER BY name ASC
            """
        )
        return cur.fetchall()

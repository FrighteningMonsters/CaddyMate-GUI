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

def get_max_aisle():
    with get_connection() as conn:
        cur = conn.cursor()
        # Cast aisle to integer to find the maximum
        cur.execute("SELECT MAX(CAST(aisle AS INTEGER)) FROM items")
        result = cur.fetchone()
        # Default to 16 if database is empty or returns None
        return result[0] if result and result[0] else 16

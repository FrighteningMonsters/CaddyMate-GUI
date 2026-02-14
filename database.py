import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "caddymate_store.db"

def get_connection():
    """
    Establishes a connection to the SQLite database.

    Returns:
        sqlite3.Connection: A connection object to the store database.
    """
    return sqlite3.connect(DB_PATH)

def get_categories():
    """
    Retrieves all categories from the database.

    Returns:
        list: A list of tuples containing (id, name) for each category, sorted by name.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM categories ORDER BY name ASC")
        return cur.fetchall()

def get_items_for_category(category_id):
    """
    Retrieves all items belonging to a specific category.

    Returns:
        list: A list of tuples containing (name, aisle) for items in the category.
    """
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
    """
    Retrieves all items in the store.

    Returns:
        list: A list of tuples containing (name, aisle) for all items.
    """
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
    """
    Determines the highest aisle number currently in the database.

    Returns:
        int: The maximum aisle number found, or 16 if the database is empty.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        # Cast aisle to integer to find the maximum
        cur.execute("SELECT MAX(CAST(aisle AS INTEGER)) FROM items")
        result = cur.fetchone()
        # Default to 16 if database is empty or returns None
        return result[0] if result and result[0] else 16

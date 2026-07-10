import sqlite3
import os
import sys
from models import Transaction, Debt

if sys.platform == "win32":
    DB_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "gbudget")
else:
    DB_DIR = os.path.expanduser("~/.local/share/gbudget")
DB_PATH = os.path.join(DB_DIR, "budget.db")

def get_connection():
    """open a conenction to the database."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # access columns by names
    return conn

def init_db():
    """create the transactions table if it doesn't exist."""
    conn = get_connection()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL CHECK(amount > 0),
        description TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'General',
        date TEXT NOT NULL,
        type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
        status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'cleared')),
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS recurring (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL CHECK(amount > 0),
        description TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'General',
        type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
        day INTEGER NOT NULL CHECK(day BETWEEN 1 AND 28),
        last_generated TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS debts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        initial_amount REAL NOT NULL CHECK(initial_amount > 0),
        annual_rate REAL NOT NULL DEFAULT 0 CHECK(annual_rate >= 0),
        start_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'paid_off')),
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS debt_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        debt_id INTEGER NOT NULL,
        amount REAL NOT NULL CHECK(amount > 0),
        fee REAL NOT NULL DEFAULT 0 CHECK(fee >= 0),
        date TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (debt_id) REFERENCES debts(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

def add_transaction(amount, description, category, date, type_, status):
    """insert a new transaction, return the new ID."""
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO transactions (amount, description, category, date, type, status) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (amount, description, category, date, type_, status)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def get_transactions(month=None, category=None, status=None):
    """Return list of Transactions objects, optionally filtered."""
    conn = get_connection()
    query = "SELECT * FROM transactions WHERE 1=1"
    params = []

    if month:
        query += " AND strftime('%Y-%m', date) = ?"
        params.append(month)
    if category:
        query += " AND category = ?"
        params.append(category)
    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY date DESC"
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [Transaction(**dict(row)) for row in rows]

def update_transaction(id_, **kwargs):
    """Update fields of a transaction by ID."""
    if not kwargs:
        return
    conn = get_connection()
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [id_]
    conn.execute(f"UPDATE transactions SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()

def delete_transaction(id_):
    """Delete a transaction by ID."""
    conn = get_connection()
    conn.execute("DELETE FROM transactions WHERE id = ?", (id_,))
    conn.commit()
    conn.close()

def mark_cleared(ids):
    """Mark one or more transactions as cleared."""
    conn = get_connection()
    placeholders = ", ".join("?" for _ in ids)
    conn.execute(f"UPDATE transactions SET status = 'cleared' WHERE id IN ({placeholders})", ids)
    conn.commit()
    conn.close()


def add_recurring(amount, description, category, type_, day):
    """Create a recurring template, return the new ID."""
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO recurring (amount, description, category, type, day) VALUES (?, ?, ?, ?, ?)",
        (amount, description, category, type_, day)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def get_recurring():
    """Return all recurring templates."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM recurring ORDER BY day").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_recurring(id_):
    """Delete a recurring template by ID."""
    conn = get_connection()
    conn.execute("DELETE FROM recurring WHERE id = ?", (id_,))
    conn.commit()
    conn.close()


def transaction_exists_in_month(amount, description, month):
    """Check if a transaction with same amount/desc already exists in a given month."""
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE amount = ? AND description = ? AND strftime('%Y-%m', date) = ?",
        (amount, description, month)
    ).fetchone()
    conn.close()
    return row[0] > 0


# --- Debt functions ---

def add_debt(name, initial_amount, annual_rate, start_date):
    """Create a new debt, return the new ID."""
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO debts (name, initial_amount, annual_rate, start_date) VALUES (?, ?, ?, ?)",
        (name, initial_amount, annual_rate, start_date)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def get_debts(status=None):
    """Return list of Debt objects, optionally filtered by status."""
    conn = get_connection()
    if status:
        rows = conn.execute("SELECT * FROM debts WHERE status = ? ORDER BY created_at", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM debts ORDER BY created_at").fetchall()
    conn.close()
    return [Debt(**dict(row)) for row in rows]


def get_debt_by_id(debt_id):
    """Return a single Debt by ID."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM debts WHERE id = ?", (debt_id,)).fetchone()
    conn.close()
    if row:
        return Debt(**dict(row))
    return None


def update_debt_status(debt_id, status):
    """Update a debt's status (active/paid_off)."""
    conn = get_connection()
    conn.execute("UPDATE debts SET status = ? WHERE id = ?", (status, debt_id))
    conn.commit()
    conn.close()


def delete_debt(debt_id):
    """Delete a debt and its payments."""
    conn = get_connection()
    conn.execute("DELETE FROM debt_payments WHERE debt_id = ?", (debt_id,))
    conn.execute("DELETE FROM debts WHERE id = ?", (debt_id,))
    conn.commit()
    conn.close()


def add_debt_payment(debt_id, amount, fee, date):
    """Record a payment against a debt, return the new ID."""
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO debt_payments (debt_id, amount, fee, date) VALUES (?, ?, ?, ?)",
        (debt_id, amount, fee, date)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def get_debt_payments(debt_id=None, month=None):
    """Return debt payments, optionally filtered by debt_id and/or month."""
    conn = get_connection()
    query = "SELECT * FROM debt_payments WHERE 1=1"
    params = []
    if debt_id:
        query += " AND debt_id = ?"
        params.append(debt_id)
    if month:
        query += " AND strftime('%Y-%m', date) = ?"
        params.append(month)
    query += " ORDER BY date DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_total_payments(debt_id):
    """Return total amount paid towards a debt."""
    conn = get_connection()
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM debt_payments WHERE debt_id = ?",
        (debt_id,)
    ).fetchone()
    conn.close()
    return row[0]


def calculate_debt_balance(debt):
    """Calculate current balance: initial + accrued interest - total payments."""
    from datetime import datetime
    start = datetime.strptime(debt.start_date, "%Y-%m-%d")
    now = datetime.today()
    months_elapsed = (now.year - start.year) * 12 + (now.month - start.month)
    monthly_rate = debt.annual_rate / 12 / 100
    accrued_interest = debt.initial_amount * monthly_rate * months_elapsed
    total_payments = get_total_payments(debt.id)
    balance = debt.initial_amount + accrued_interest - total_payments
    return max(balance, 0.0)

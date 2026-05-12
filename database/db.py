import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash


def get_db():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'spendly.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    conn.commit()
    conn.close()


def seed_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    password_hash = generate_password_hash('demo123')
    cursor.execute(
        'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
        ('Demo User', 'demo@spendly.com', password_hash)
    )

    user_id = cursor.lastrowid

    expenses = [
        (user_id, 12.50, 'Food', '2026-05-01', 'Lunch at cafe'),
        (user_id, 45.00, 'Transport', '2026-05-03', 'Monthly bus pass'),
        (user_id, 85.00, 'Bills', '2026-05-05', 'Electricity bill'),
        (user_id, 23.75, 'Health', '2026-05-08', 'Pharmacy'),
        (user_id, 30.00, 'Entertainment', '2026-05-10', 'Movie tickets'),
        (user_id, 67.50, 'Shopping', '2026-05-15', 'Groceries'),
        (user_id, 15.25, 'Other', '2026-05-18', 'Office supplies'),
        (user_id, 48.00, 'Food', '2026-05-20', 'Dinner with friends'),
    ]

    cursor.executemany(
        'INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)',
        expenses
    )

    conn.commit()
    conn.close()


def get_user_by_email(email):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    return user


def get_user_by_id(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user


def get_user_expenses(user_id, start_date=None, end_date=None):
    conn = get_db()
    cursor = conn.cursor()
    query = 'SELECT date, description, category, amount FROM expenses WHERE user_id = ?'
    params = [user_id]
    if start_date:
        query += ' AND date >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND date <= ?'
        params.append(end_date)
    query += ' ORDER BY date DESC'
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_category_stats(user_id, start_date=None, end_date=None):
    conn = get_db()
    cursor = conn.cursor()
    query = 'SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ?'
    params = [user_id]
    if start_date:
        query += ' AND date >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND date <= ?'
        params.append(end_date)
    query += ' GROUP BY category ORDER BY total DESC'
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    grand_total = sum(row["total"] for row in rows)
    return [
        {
            "name": row["category"],
            "amount": f"₹{row['total']:,.2f}",
            "percent": round((row["total"] / grand_total) * 100) if grand_total else 0,
        }
        for row in rows
    ]


def insert_expense(user_id, amount, category, date, description=None):
    conn = get_db()
    conn.execute(
        'INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)',
        (user_id, amount, category, date, description),
    )
    conn.commit()
    conn.close()

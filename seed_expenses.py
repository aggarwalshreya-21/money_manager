import sqlite3
import os
import random
from datetime import datetime, timedelta

# Use the same db connection pattern as db.py
def get_db():
    db_path = os.path.join(os.path.dirname(__file__), 'spendly.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

# Parse arguments
user_id = 2
count = 3
months = 6

# Verify user exists
conn = get_db()
cursor = conn.cursor()
cursor.execute('SELECT id, name FROM users WHERE id = ?', (user_id,))
user = cursor.fetchone()

if not user:
    print(f"No user found with id {user_id}.")
    conn.close()
    exit(1)

print(f"Found user: {user['name']} (ID: {user_id})")

# Category configuration with realistic Indian amounts (₹)
categories = {
    'Food': {'min': 50, 'max': 800, 'weight': 30},
    'Transport': {'min': 20, 'max': 500, 'weight': 20},
    'Bills': {'min': 200, 'max': 3000, 'weight': 15},
    'Health': {'min': 100, 'max': 2000, 'weight': 10},
    'Entertainment': {'min': 100, 'max': 1500, 'weight': 10},
    'Shopping': {'min': 200, 'max': 5000, 'weight': 10},
    'Other': {'min': 50, 'max': 1000, 'weight': 5},
}

# Generate weighted category list
weighted_categories = []
for category, config in categories.items():
    weighted_categories.extend([category] * config['weight'])

# Generate expenses spread across past months
today = datetime.now()
expenses = []
inserted_records = []

try:
    conn.execute('BEGIN TRANSACTION')

    for _ in range(count):
        # Random date within the past N months
        days_back = random.randint(0, months * 30)
        expense_date = today - timedelta(days=days_back)
        expense_date_str = expense_date.strftime('%Y-%m-%d')

        # Select category with weighted distribution
        category = random.choice(weighted_categories)
        config = categories[category]

        # Generate realistic amount
        amount = round(random.uniform(config['min'], config['max']), 2)

        # Sample descriptions
        descriptions = {
            'Food': ['Lunch', 'Dinner', 'Breakfast', 'Snacks', 'Restaurant', 'Grocery shopping'],
            'Transport': ['Taxi', 'Bus fare', 'Fuel', 'Auto-rickshaw', 'Train ticket', 'Parking'],
            'Bills': ['Electricity bill', 'Water bill', 'Internet bill', 'Mobile recharge', 'Rent payment'],
            'Health': ['Doctor visit', 'Pharmacy', 'Medicine', 'Hospital', 'Dental care', 'Gym membership'],
            'Entertainment': ['Movie', 'Concert', 'Gaming', 'Sports event', 'Streaming subscription'],
            'Shopping': ['Clothes', 'Shoes', 'Books', 'Electronics', 'Home supplies', 'Personal care'],
            'Other': ['Misc expense', 'Gift', 'Charity', 'Subscription', 'Service'],
        }
        description = random.choice(descriptions[category])

        # Insert into database with parameterized query
        cursor.execute(
            'INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)',
            (user_id, amount, category, expense_date_str, description)
        )

        expenses.append({
            'id': cursor.lastrowid,
            'amount': amount,
            'category': category,
            'date': expense_date_str,
            'description': description
        })

    conn.commit()
    print(f"\n✓ Successfully inserted {count} expenses")

except Exception as e:
    conn.rollback()
    print(f"Error: Failed to insert expenses: {e}")
    conn.close()
    exit(1)

# Fetch inserted records for confirmation
cursor.execute(
    'SELECT id, amount, category, date, description FROM expenses WHERE user_id = ? ORDER BY date DESC LIMIT 5',
    (user_id,)
)
recent = cursor.fetchall()

# Calculate date range
dates = [exp['date'] for exp in expenses]
date_range = f"{min(dates)} to {max(dates)}"

print(f"Date range: {date_range}")
print(f"\nSample of {len(recent)} recent expenses:")
print("-" * 70)
print(f"{'Date':<12} {'Category':<15} {'Amount (₹)':<15} {'Description':<25}")
print("-" * 70)

for record in recent:
    print(f"{record['date']:<12} {record['category']:<15} {record['amount']:<15.2f} {record['description']:<25}")

print("-" * 70)

conn.close()

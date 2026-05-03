#!/usr/bin/env python3
import sys
import os
import random
from datetime import datetime
from werkzeug.security import generate_password_hash

# Add the project root to the path
sys.path.insert(0, os.path.dirname(__file__))

from database.db import get_db

# Indian names (first names and last names from different regions)
FIRST_NAMES = [
    'Rahul', 'Priya', 'Arjun', 'Anjali', 'Rohan', 'Neha', 'Vikram', 'Deepak',
    'Aisha', 'Karan', 'Pooja', 'Sanjay', 'Divya', 'Amit', 'Shruti', 'Nikhil',
    'Sneha', 'Akash', 'Meera', 'Varun', 'Isha', 'Ravi', 'Ananya', 'Aryan',
    'Ridhi', 'Manish', 'Kavya', 'Ashok', 'Ritika', 'Suresh'
]

LAST_NAMES = [
    'Sharma', 'Patel', 'Singh', 'Kumar', 'Verma', 'Gupta', 'Reddy', 'Nair',
    'Iyer', 'Desai', 'Joshi', 'Chopra', 'Bhat', 'Das', 'Rao', 'Malhotra',
    'Kapoor', 'Banerjee', 'Pandey', 'Mishra', 'Agarwal', 'Srivastava', 'Menon',
    'Saxena', 'Dutta', 'Roy', 'Bose', 'Chatterjee', 'Sinha', 'Trivedi'
]

def generate_user():
    """Generate a realistic Indian user."""
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    name = f"{first_name} {last_name}"

    # Generate email based on name with random suffix
    email_base = f"{first_name.lower()}.{last_name.lower()}"
    random_suffix = random.randint(10, 999)
    email = f"{email_base}{random_suffix}@gmail.com"

    password = "password123"
    password_hash = generate_password_hash(password)
    created_at = datetime.now().isoformat()

    return name, email, password_hash, created_at

def user_exists(conn, email):
    """Check if email already exists in database."""
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
    return cursor.fetchone() is not None

def seed_user():
    """Generate and insert a unique user into the database."""
    conn = get_db()
    cursor = conn.cursor()

    # Generate unique user
    max_attempts = 10
    for attempt in range(max_attempts):
        name, email, password_hash, created_at = generate_user()

        if not user_exists(conn, email):
            break
    else:
        print("ERROR: Could not generate unique email after 10 attempts")
        conn.close()
        return

    # Insert the user
    try:
        cursor.execute(
            'INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)',
            (name, email, password_hash, created_at)
        )
        conn.commit()
        user_id = cursor.lastrowid

        print(f"✓ User created successfully")
        print(f"  ID:    {user_id}")
        print(f"  Name:  {name}")
        print(f"  Email: {email}")

    except Exception as e:
        print(f"ERROR: Failed to insert user: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    seed_user()

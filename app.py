import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash,session
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
from database.db import init_db, seed_db, get_db,get_user_by_email

app = Flask(__name__)
app.secret_key = 'spendly-secret-key-change-in-production'

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("landing"))

    if request.method == "GET":
        return render_template("register.html")

    name     = request.form.get("name", "").strip()
    email    = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    confirm  = request.form.get("confirm_password", "")

    if not name:
        return render_template("register.html", error="Name is required.", name=name, email=email)
    if not email:
        return render_template("register.html", error="Email is required.", name=name, email=email)
    if len(password) < 6:
        return render_template("register.html", error="Password must be at least 6 characters.", name=name, email=email)
    if password != confirm:
        return render_template("register.html", error="Passwords do not match.", name=name, email=email)

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return render_template("register.html", error="Email already registered.", name=name, email=email)
    finally:
        conn.close()

    flash("Registration successful. Please log in.")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("landing"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = get_user_by_email(email)

        if user is None or not check_password_hash(user["password_hash"], password):
            return render_template("login.html", error="Invalid email or password")

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        return redirect(url_for("landing"))

    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = {
        "name": "Nitish Kumar",
        "email": "nitish@example.com",
        "initials": "NK",
        "member_since": "January 2026",
    }

    stats = {
        "total_spent": "₹18,240",
        "transactions": 34,
        "top_category": "Food",
    }

    transactions = [
        {"date": "20 May 2026", "description": "Dinner with friends",  "category": "Food",          "amount": "₹48.00"},
        {"date": "15 May 2026", "description": "Groceries",            "category": "Shopping",      "amount": "₹67.50"},
        {"date": "10 May 2026", "description": "Movie tickets",        "category": "Entertainment", "amount": "₹30.00"},
        {"date": "08 May 2026", "description": "Pharmacy",             "category": "Health",        "amount": "₹23.75"},
        {"date": "05 May 2026", "description": "Electricity bill",     "category": "Bills",         "amount": "₹85.00"},
    ]

    categories = [
        {"name": "Food",          "amount": "₹6,240", "percent": 34},
        {"name": "Bills",         "amount": "₹4,760", "percent": 26},
        {"name": "Shopping",      "amount": "₹3,680", "percent": 20},
        {"name": "Transport",     "amount": "₹2,250", "percent": 12},
        {"name": "Entertainment", "amount": "₹1,310", "percent": 8},
    ]

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)

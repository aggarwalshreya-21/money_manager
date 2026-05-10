import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash,session
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
from database.db import init_db, seed_db, get_db, get_user_by_email, get_user_by_id, get_user_expenses, get_category_stats

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
        return redirect(url_for("profile"))

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

    # Parse and validate date filter parameters
    start_date = request.args.get('start_date', '').strip() or None
    end_date = request.args.get('end_date', '').strip() or None

    def valid_date(s):
        try:
            datetime.strptime(s, '%Y-%m-%d')
            return True
        except ValueError:
            return False

    if start_date and not valid_date(start_date):
        start_date = None
    if end_date and not valid_date(end_date):
        end_date = None
    if start_date and end_date and end_date < start_date:
        start_date, end_date = end_date, start_date

    # --- SECTION A: user info & stats (Subagent 2) ---
    db_user = get_user_by_id(session["user_id"])
    initials = "".join(p[0].upper() for p in db_user["name"].split()[:2])
    member_since = datetime.strptime(db_user["created_at"][:10], "%Y-%m-%d").strftime("%B %Y")

    user = {
        "name": db_user["name"],
        "email": db_user["email"],
        "initials": initials,
        "member_since": member_since,
    }
    # --- END SECTION A ---

    # --- SECTION B: transaction history (Subagent 1) ---
    raw_expenses = get_user_expenses(session["user_id"], start_date, end_date)
    transactions = [
        {
            "date": datetime.strptime(row["date"], "%Y-%m-%d").strftime("%-d %B %Y"),
            "description": row["description"] or "",
            "category": row["category"],
            "amount": f"₹{row['amount']:.2f}",
        }
        for row in raw_expenses
    ]
    # --- END SECTION B ---

    # --- SECTION C: category breakdown (Subagent 3) ---
    categories = get_category_stats(session["user_id"], start_date, end_date)
    # --- END SECTION C ---

    # Recalculate stats from filtered expenses
    total_amount = sum(row["amount"] for row in raw_expenses) if raw_expenses else 0.0
    tx_count = len(raw_expenses)
    top_cat = "—"
    if raw_expenses:
        cat_totals = {}
        for row in raw_expenses:
            cat = row["category"]
            cat_totals[cat] = cat_totals.get(cat, 0) + row["amount"]
        top_cat = max(cat_totals, key=cat_totals.get)

    stats = {
        "total_spent": f"₹{total_amount:,.2f}",
        "transactions": tx_count,
        "top_category": top_cat,
    }

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        start_date=start_date or '',
        end_date=end_date or '',
        filter_active=bool(start_date or end_date),
    )


@app.route("/analytics")
def analytics():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template("analytics.html")


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

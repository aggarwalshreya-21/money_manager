# Spec: Backend Connection For Profile Page

## Overview
This feature replaces the hardcoded data in the `/profile` route with real database queries. The goal is to wire the profile page UI (built in Step 4) to the actual `users` and `expenses` tables, so each logged-in user sees their own data: their name, email, member-since date, total spending, transaction count, top category, transaction history, and category breakdown. This step validates the UI design and confirms the database schema supports the feature set.

## Depends on
- Step 1: Database setup (schema and seed data must exist)
- Step 2: Registration (user accounts must be creatable)
- Step 3: Login + Logout (session must be set; `/profile` must be protected)
- Step 4: Profile Page (UI must be designed and hardcoded)

## Routes
No new routes. The `/profile` route exists and will be modified to fetch real data.

## Database changes
No database changes. The existing `users` and `expenses` tables are sufficient.

## Templates
- **Modify:** `templates/profile.html` — no changes needed (data binding is already in place from Step 4)

## Files to change
- `app.py` — modify the `/profile` route to:
  - Fetch the logged-in user's record from the `users` table
  - Fetch all expenses for that user from the `expenses` table
  - Calculate total spent (sum of amounts)
  - Calculate transaction count (number of expenses)
  - Calculate top category (category with highest total amount)
  - Calculate per-category totals and percentages
  - Replace hardcoded context variables with real data from the database

- `database/db.py` — add helper functions:
  - `get_user_by_id(user_id)` — fetch user record by ID
  - `get_user_expenses(user_id)` — fetch all expenses for a user, ordered by date descending
  - `get_user_spending_stats(user_id)` — return dict with total_spent, transaction count, and category breakdown

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()` only
- Parameterised queries only — never string-format SQL
- Passwords hashed with werkzeug (no changes to auth in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Authentication guard: check `session.get("user_id")`; if absent, `redirect(url_for("login"))`
- Numeric calculations (totals, percentages) must be performed in Python, not in the template
- Format currency in Python before passing to template (use Indian Rupee ₹ format consistent with the design)
- Handle edge cases: user with no expenses should show 0.00 for total and empty category list
- Date formatting: convert ISO 8601 dates from database to display format in Python (e.g. "20 May 2026")

## Definition of done
- [ ] Visiting `/profile` without being logged in redirects to `/login`
- [ ] Visiting `/profile` while logged in returns HTTP 200
- [ ] The profile page displays the logged-in user's actual name from the database
- [ ] The profile page displays the logged-in user's actual email from the database
- [ ] The page displays the actual total spent (sum of user's expenses)
- [ ] The page displays the actual transaction count (number of user's expenses)
- [ ] The page displays the actual top category based on user's expenses
- [ ] The page displays the user's actual recent transactions from the database (ordered by date descending)
- [ ] The page displays actual category breakdown percentages based on user's expenses
- [ ] A user with no expenses sees "₹0.00" for total spent and an empty or "No categories" message
- [ ] Two different logged-in users see their own respective data (not shared/mixed)
- [ ] The database queries use parameterised statements only (no SQL injection vectors)
- [ ] All date/time data is formatted before rendering (ISO format from DB → display format in Python)

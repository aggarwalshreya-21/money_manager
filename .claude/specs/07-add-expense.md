# Spec: Add Expense

## Overview
This feature allows logged-in users to create new expense records via a form at `/expenses/add`. Users provide a date, amount, category, and optional description; the form validates input and saves the expense to the database, then redirects back to the profile page. This is the first feature that allows users to directly manipulate the `expenses` table and prepares the foundation for editing and deleting expenses in later steps.

## Depends on
- Step 1: Database setup (schema must exist)
- Step 2: Registration (user accounts must be creatable)
- Step 3: Login + Logout (session must be set; `/expenses/add` must be protected)
- Step 4: Profile Page (UI patterns and styling)
- Step 5: Backend Connection (database functions must be available)
- Step 6: Date Filter for Profile Page (profile page must be fully functional)

## Routes
- GET /expenses/add — show the expense creation form — logged-in only
- POST /expenses/add — handle expense creation, validate input, save to database, and redirect to profile — logged-in only

## Database changes
No new tables or columns. The existing `expenses` table is sufficient:
- `id` — auto-incrementing primary key
- `user_id` — foreign key to `users`
- `amount` — REAL (positive value)
- `category` — TEXT
- `date` — TEXT (YYYY-MM-DD format)
- `description` — TEXT (nullable)
- `created_at` — timestamp (auto-set)

## Templates
- **Create:** `templates/add-expense.html` — a form with:
  - Date input field (type="date", required, defaults to today)
  - Amount input field (type="number", required, step="0.01", min="0.01")
  - Category select dropdown (required) with predefined options:
    - Food
    - Transport
    - Bills
    - Health
    - Entertainment
    - Shopping
    - Other
  - Description textarea (optional, max 200 characters)
  - "Add Expense" submit button
  - "Cancel" link that returns to `/profile`
  - Form should show validation error messages inline if validation fails

## Files to change
- `app.py` — implement the `/expenses/add` route:
  - GET: check session; if not logged in, redirect to `/login`
  - GET: render `templates/add-expense.html` with empty form
  - POST: extract form fields (date, amount, category, description)
  - POST: validate all inputs:
    - date must be in YYYY-MM-DD format and not in the future
    - amount must be a positive number (> 0)
    - category must be one of the predefined categories
    - description is optional; trim whitespace
  - POST: if validation fails, re-render the form with the submitted values and error messages
  - POST: if validation succeeds, insert the expense into the database using parameterized queries
  - POST: redirect to `/profile` with a flash message (optional: "Expense added successfully")

- `database/db.py` — add a helper function:
  - `add_expense(user_id, amount, category, date, description=None)` — insert a new expense record and return the new expense ID (or nothing if silent insert is preferred)

## Files to create
- `templates/add-expense.html` — expense creation form

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()` only
- Parameterised queries only — never string-format SQL
- Passwords hashed with werkzeug (no changes to auth in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Authentication guard: check `session.get("user_id")`; if absent, `redirect(url_for("login"))`
- Date validation: use `datetime.strptime()` to validate YYYY-MM-DD format; reject dates in the future
- Amount validation: must be a decimal number > 0; use float parsing and catch ValueError
- Category validation: whitelist check against predefined categories only
- Form submission should be POST to prevent caching and CSRF concerns
- On validation error, re-render the form with previous user input (form sticky values) and error messages
- On success, redirect to `/profile` (can optionally use `flash()` to show a success message)
- The form should be user-friendly and match the design language of the rest of the app (use consistent styling with other forms like login/register)

## Definition of done
- [ ] Visiting `/expenses/add` without being logged in redirects to `/login`
- [ ] Visiting `/expenses/add` while logged in returns HTTP 200 and displays the expense form
- [ ] The form has input fields for date (type="date", defaults to today), amount, category (dropdown), and description (textarea)
- [ ] The date field defaults to today's date (YYYY-MM-DD format)
- [ ] The category dropdown lists all predefined categories (Food, Transport, Bills, Health, Entertainment, Shopping, Other)
- [ ] The description field is optional and shows placeholder text like "e.g., Lunch at cafe"
- [ ] Submitting the form with valid data creates a new expense in the database
- [ ] After successful submission, the user is redirected to `/profile`
- [ ] If the form is submitted with an empty date field, an error is shown: "Date is required"
- [ ] If the form is submitted with a future date, an error is shown: "Date cannot be in the future"
- [ ] If the form is submitted with an invalid date format, an error is shown: "Invalid date format"
- [ ] If the form is submitted with an empty or zero amount, an error is shown: "Amount must be greater than zero"
- [ ] If the form is submitted with a non-numeric amount, an error is shown: "Amount must be a valid number"
- [ ] If the form is submitted with an empty category, an error is shown: "Category is required"
- [ ] If a validation error occurs, the form is re-rendered with the previously entered values (sticky form)
- [ ] If a validation error occurs, the form displays error messages in a user-friendly format
- [ ] The new expense appears in the `/profile` page transaction history after creation
- [ ] The new expense is correctly attributed to the logged-in user (not shared with other users)
- [ ] The expense amount is stored correctly in the database (with decimal precision)
- [ ] The expense date is stored in ISO format (YYYY-MM-DD) in the database
- [ ] The database insert uses parameterised queries only (no SQL injection vectors)
- [ ] Multiple users can add expenses independently without seeing each other's data

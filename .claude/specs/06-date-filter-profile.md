# Spec: Date Filter for Profile Page

## Overview
This feature adds date-range filtering to the profile page, allowing users to view expenses and category statistics within a specific date window. Users can select a start and end date, and the page will dynamically update to show only transactions within that range. This feature validates that the profile page can handle dynamic filtering and prepares the foundation for more advanced filtering and searching in later steps.

## Depends on
- Step 1: Database setup (schema must exist)
- Step 2: Registration (user accounts must be creatable)
- Step 3: Login + Logout (session must be set; `/profile` must be protected)
- Step 4: Profile Page (UI must be designed and hardcoded)
- Step 5: Backend Connection (real database queries must be wired up)

## Routes
No new routes. The `/profile` route will be modified to accept optional `start_date` and `end_date` query parameters.
- GET /profile?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD — render profile page with filtered data — logged-in only

## Database changes
No database changes. The existing `users` and `expenses` tables are sufficient.

## Templates
- **Modify:** `templates/profile.html` — add a date filter form with:
  - Start date input field (type="date")
  - End date input field (type="date")
  - "Filter" button to apply the date range
  - Optional "Reset" or "Clear" button to remove the filter
  - Display the currently applied date range on the page (e.g., "Showing expenses from 1 May 2026 to 31 May 2026")

## Files to change
- `app.py` — modify the `/profile` route to:
  - Extract optional `start_date` and `end_date` query parameters from the request
  - Validate the date parameters (YYYY-MM-DD format; end_date must be >= start_date if both provided)
  - Pass the date parameters to the database query functions
  - Display the applied date range in the context passed to the template

- `database/db.py` — modify and add helper functions:
  - Modify `get_user_expenses(user_id, start_date=None, end_date=None)` — add optional date range filtering
  - Modify `get_category_stats(user_id, start_date=None, end_date=None)` — add optional date range filtering to category totals

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
- Date filter is optional; if not provided, show all expenses (same as Step 5 behavior)
- Date parameters must be validated in the route before passing to database functions
- If `start_date` is provided without `end_date`, use the current date as `end_date`
- If `end_date` is provided without `start_date`, use a sensible default (e.g., first day of the current month, or the earliest date with expenses)
- Category breakdown and stats (total spent, transaction count, top category) must be recalculated based on the filtered date range
- Date range display on the page must be user-friendly (e.g., "1 May 2026 to 31 May 2026")
- Form submission should be via GET request so the URL reflects the applied filter (users can bookmark/share filtered views)

## Definition of done
- [ ] Visiting `/profile` without being logged in redirects to `/login`
- [ ] Visiting `/profile` while logged in with no date parameters shows all expenses (same as Step 5)
- [ ] The date filter form is visible on the profile page with start and end date input fields
- [ ] Entering a date range and clicking "Filter" updates the page to show only expenses within that range
- [ ] The transaction history table is filtered to show only transactions within the selected date range
- [ ] The total spent stat is recalculated based on filtered transactions
- [ ] The transaction count stat is recalculated based on filtered transactions
- [ ] The top category is recalculated based on filtered transactions
- [ ] The category breakdown percentages are recalculated based on filtered transactions
- [ ] The page displays the currently applied date range (e.g., "Showing: 1 May 2026 — 31 May 2026")
- [ ] Clearing the date filter (or removing query parameters) shows all expenses again
- [ ] If a user selects a date range with no expenses, the page shows "No expenses found" instead of empty sections
- [ ] The database queries use parameterised statements only (date filtering must not allow SQL injection)
- [ ] Query parameters in the URL use the format `?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
- [ ] Two different logged-in users can filter their own data independently

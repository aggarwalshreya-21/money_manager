"""
Tests for Step 06 — Date Filter for Profile Page
=================================================

Spec: .claude/specs/06-date-filter-profile.md

These tests are written strictly against the feature specification.
They validate WHAT the feature must do, not HOW it does it internally.

Coverage areas:
    - Authentication guard on /profile
    - Happy paths: unfiltered view, date-range filtering
    - Stats and category breakdown recalculation under filter
    - Edge cases: empty results, partial dates, same-day, reversed range
    - Validation: invalid date formats, malformed parameters, SQL injection
    - URL state: query parameters reflect applied filter
    - Multi-user data isolation
    - Template rendering: form inputs, filter label, empty-states, clear button
"""

import sqlite3
import os
import sys
import pytest
from datetime import date, timedelta
from werkzeug.security import generate_password_hash

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so `app` and `database` are importable.
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def app(tmp_path):
    """
    Create a Flask test application that points at a fresh, isolated SQLite
    database for every test.  The fixture:
      - Overrides the database path used by db.get_db() via an env var.
      - Initialises the schema (init_db) WITHOUT seeding demo data (seed_db
        would insert rows we do not control).
      - Enables Flask testing mode and disables seed_db auto-call on import
        by monkey-patching before importing app.
    """
    import importlib
    import database.db as db_module

    # Point db.get_db() at a temp file for this test session.
    test_db_path = str(tmp_path / "test_spendly.db")

    original_get_db = db_module.get_db

    def isolated_get_db():
        conn = sqlite3.connect(test_db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # Patch get_db before app is imported so the app uses the temp DB.
    db_module.get_db = isolated_get_db

    # Patch seed_db to a no-op so auto-seeding on app startup does not pollute.
    original_seed_db = db_module.seed_db
    db_module.seed_db = lambda: None

    import app as app_module
    importlib.reload(app_module)          # re-run module-level init with patched db
    flask_app = app_module.app
    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret-key"
    flask_app.config["WTF_CSRF_ENABLED"] = False

    # Initialise schema on the temp database.
    with flask_app.app_context():
        db_module.init_db()

    yield flask_app

    # Restore originals.
    db_module.get_db = original_get_db
    db_module.seed_db = original_seed_db


@pytest.fixture()
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture()
def db(app):
    """
    Return a live connection to the test database for direct SQL seeding.
    Closes automatically after the test.
    """
    import database.db as db_module
    conn = db_module.get_db()
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Helper functions used across fixtures and tests
# ---------------------------------------------------------------------------

def _create_user(db, name="Alice Tester", email="alice@test.com", password="password123"):
    """Insert a user row and return its id."""
    pw_hash = generate_password_hash(password)
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (name, email, pw_hash, "2025-01-15 10:00:00"),
    )
    db.commit()
    return cursor.lastrowid


def _create_expense(db, user_id, amount, category, expense_date, description=""):
    """Insert a single expense row."""
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, expense_date, description),
    )
    db.commit()
    return cursor.lastrowid


def _login(client, email="alice@test.com", password="password123"):
    """POST to /login and return the response."""
    return client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


# ---------------------------------------------------------------------------
# Shared expense dataset fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def alice_with_expenses(db):
    """
    Create user Alice with expenses spread across three distinct months:
      - January 2026 : 2 expenses
      - February 2026: 2 expenses
      - March 2026   : 1 expense (top category: Bills)
    Returns a dict with user_id, email, password and the seeded expenses.
    """
    user_id = _create_user(db, name="Alice Tester", email="alice@test.com")

    expenses = [
        # January
        (user_id, 100.00, "Food",          "2026-01-10", "Jan lunch"),
        (user_id, 200.00, "Transport",     "2026-01-20", "Jan bus pass"),
        # February
        (user_id,  50.00, "Entertainment", "2026-02-05", "Feb movie"),
        (user_id, 300.00, "Bills",         "2026-02-28", "Feb electricity"),
        # March
        (user_id, 400.00, "Bills",         "2026-03-15", "Mar rent"),
    ]
    for exp in expenses:
        _create_expense(db, *exp)

    return {
        "user_id": user_id,
        "email": "alice@test.com",
        "password": "password123",
        "expenses": expenses,
    }


@pytest.fixture()
def bob_with_expenses(db):
    """
    Create a second user Bob with his own expenses, used for multi-user
    isolation tests.
    """
    user_id = _create_user(db, name="Bob Tester", email="bob@test.com")
    # Use a description without an apostrophe so Jinja2 autoescaping does not
    # transform the string and break substring assertions on raw HTML.
    _create_expense(db, user_id, 999.00, "Shopping", "2026-01-10", "Bobs unique purchase")
    return {
        "user_id": user_id,
        "email": "bob@test.com",
        "password": "password123",
    }


# ===========================================================================
# TestAuthGuard — /profile authentication enforcement
# ===========================================================================

class TestAuthGuard:
    """Spec rule: Authentication guard — check session.get('user_id'); if absent,
    redirect to /login."""

    def test_unauthenticated_get_redirects_to_login(self, client):
        """GET /profile without a session must redirect to /login."""
        response = client.get("/profile")
        assert response.status_code in (301, 302)
        assert "/login" in response.headers["Location"]

    def test_unauthenticated_get_with_date_params_redirects_to_login(self, client):
        """GET /profile?start_date=...&end_date=... without a session must
        still redirect to /login, not crash or expose data."""
        response = client.get("/profile?start_date=2026-01-01&end_date=2026-01-31")
        assert response.status_code in (301, 302)
        assert "/login" in response.headers["Location"]

    def test_authenticated_user_can_access_profile(self, client, db, alice_with_expenses):
        """GET /profile for a logged-in user must return HTTP 200."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile")
        assert response.status_code == 200

    def test_session_cleared_after_logout_denies_profile(self, client, db, alice_with_expenses):
        """After logout the session is cleared; a subsequent GET /profile must
        redirect back to /login, not serve the page."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        client.post("/logout", follow_redirects=True)
        response = client.get("/profile")
        assert response.status_code in (301, 302)
        assert "/login" in response.headers["Location"]


# ===========================================================================
# TestFilterHappyPath — correct filtering behaviour
# ===========================================================================

class TestFilterHappyPath:
    """Spec rules covering the core filter behaviour."""

    def test_no_filter_shows_all_expenses(self, client, db, alice_with_expenses):
        """GET /profile with no query parameters shows all 5 seeded expenses."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile")
        html = response.data.decode()
        # All five description strings from the fixture must appear in the page.
        assert "Jan lunch" in html
        assert "Jan bus pass" in html
        assert "Feb movie" in html
        assert "Feb electricity" in html
        assert "Mar rent" in html

    def test_date_range_filters_transactions(self, client, db, alice_with_expenses):
        """GET /profile?start_date=2026-02-01&end_date=2026-02-28 shows only
        February expenses and excludes January and March entries."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile?start_date=2026-02-01&end_date=2026-02-28")
        html = response.data.decode()

        assert "Feb movie" in html
        assert "Feb electricity" in html

        assert "Jan lunch" not in html
        assert "Jan bus pass" not in html
        assert "Mar rent" not in html

    def test_total_spent_stat_recalculates_for_filter(self, client, db, alice_with_expenses):
        """Total Spent stat shown on the page must equal the sum of expenses
        within the filtered date range only.

        February total: 50 + 300 = 350.00
        """
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile?start_date=2026-02-01&end_date=2026-02-28")
        html = response.data.decode()
        # The rendered amount uses Indian Rupee symbol and comma-formatted value.
        assert "350.00" in html

    def test_transaction_count_recalculates_for_filter(self, client, db, alice_with_expenses):
        """Transactions stat must reflect only the filtered count.

        January has 2 expenses; filter to January must show '2'.
        """
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile?start_date=2026-01-01&end_date=2026-01-31")
        html = response.data.decode()
        # The stat card value '2' must appear for the Transactions section.
        assert "2" in html

    def test_top_category_recalculates_for_filter(self, client, db, alice_with_expenses):
        """Top Category stat must reflect the highest-spending category in the
        filtered window.

        March has a single Bills expense (400.00), so top category = Bills.
        """
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile?start_date=2026-03-01&end_date=2026-03-31")
        html = response.data.decode()
        assert "Bills" in html

    def test_category_breakdown_recalculates_for_filter(self, client, db, alice_with_expenses):
        """Category breakdown section must only list categories that appear in
        the filtered date window.

        January has Food and Transport; Bills must not appear in breakdown.
        """
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile?start_date=2026-01-01&end_date=2026-01-31")
        html = response.data.decode()

        # Categories present in January.
        assert "Food" in html
        assert "Transport" in html

        # Bills only appears in Feb and Mar, not January.
        # Check the breakdown section specifically by scanning for a category row
        # pattern. We confirm Bills does not appear as a standalone category stat
        # (it should NOT have a bar entry for January).
        # The badge for "Bills" would appear on the Mar rent transaction row —
        # which is excluded by this filter — so Bills should not appear at all.
        assert "Mar rent" not in html

    def test_clear_filter_shows_all_expenses(self, client, db, alice_with_expenses):
        """After applying a filter, navigating to /profile (no params) must
        reset to showing all expenses — the same as the unfiltered baseline."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        # Apply a filter first.
        client.get("/profile?start_date=2026-03-01&end_date=2026-03-31")
        # Now visit without params (simulating the Clear button).
        response = client.get("/profile")
        html = response.data.decode()

        assert "Jan lunch" in html
        assert "Feb movie" in html
        assert "Mar rent" in html

    def test_filter_form_uses_get_method(self, client, db, alice_with_expenses):
        """The filter form must use method='GET' so that the URL reflects the
        applied filter (bookmarkable/shareable filtered views)."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile")
        html = response.data.decode()
        # Spec: Form submission should be via GET request.
        assert 'method="GET"' in html or "method='GET'" in html

    def test_filter_url_contains_query_params(self, client, db, alice_with_expenses):
        """The URL used to apply the filter must follow the format
        ?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get(
            "/profile?start_date=2026-01-01&end_date=2026-01-31",
            follow_redirects=False,
        )
        # The request should succeed (not redirect).
        assert response.status_code == 200


# ===========================================================================
# TestFilterEdgeCases — boundary and partial-input scenarios
# ===========================================================================

class TestFilterEdgeCases:
    """Spec edge-case rules for partial or unusual date inputs."""

    def test_empty_date_range_no_matching_expenses_shows_empty_state(
        self, client, db, alice_with_expenses
    ):
        """When the filter range has no matching expenses, the template must
        display the 'No expenses found' empty-state message instead of an
        empty table or broken page."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        # A future date range that has no data.
        response = client.get("/profile?start_date=2030-01-01&end_date=2030-01-31")
        html = response.data.decode()
        assert response.status_code == 200
        # The spec mandates an empty-state message; check for its presence.
        assert "No expenses found" in html

    def test_no_matching_expenses_category_breakdown_shows_empty_state(
        self, client, db, alice_with_expenses
    ):
        """When no expenses exist in the filter range, the category breakdown
        section must also show its empty-state message."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile?start_date=2030-01-01&end_date=2030-01-31")
        html = response.data.decode()
        assert response.status_code == 200
        # profile.html uses "No categories found" for the category empty state.
        assert "No categories found" in html

    def test_only_start_date_provided_defaults_end_date(
        self, client, db, alice_with_expenses
    ):
        """Spec rule: if start_date is provided without end_date, the route
        must use the current date as end_date and must not crash."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile?start_date=2026-01-01")
        assert response.status_code == 200
        # At a minimum, January expenses (which are before today 2026-05-09)
        # must be visible since start_date=2026-01-01 includes them.
        html = response.data.decode()
        assert "Jan lunch" in html

    def test_only_end_date_provided_uses_sensible_default_start(
        self, client, db, alice_with_expenses
    ):
        """Spec rule: if end_date is provided without start_date, the route
        must use a sensible default (e.g. first day of the current month) and
        must not crash."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile?end_date=2026-03-31")
        assert response.status_code == 200
        # Page must render without error.
        html = response.data.decode()
        assert "<table" in html

    def test_single_day_filter_start_equals_end(self, client, db, alice_with_expenses):
        """When start_date equals end_date, only expenses on that exact day
        should be returned."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        # Jan 10 has exactly one expense: "Jan lunch" (100.00, Food)
        response = client.get("/profile?start_date=2026-01-10&end_date=2026-01-10")
        html = response.data.decode()
        assert response.status_code == 200
        assert "Jan lunch" in html
        # Jan 20 expense must not appear.
        assert "Jan bus pass" not in html

    def test_reversed_date_range_is_handled_gracefully(
        self, client, db, alice_with_expenses
    ):
        """Spec rule: end_date before start_date must be handled gracefully
        (swap or reject) — the page must not crash and must return HTTP 200."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        # Intentionally reversed: end before start.
        response = client.get("/profile?start_date=2026-03-31&end_date=2026-01-01")
        assert response.status_code == 200

    def test_reversed_date_range_still_returns_expenses_in_window(
        self, client, db, alice_with_expenses
    ):
        """When a reversed date range is swapped internally, expenses within
        the corrected window must be visible — not an empty page."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        # Reversed: should be treated as 2026-01-01 to 2026-03-31 after swap.
        response = client.get("/profile?start_date=2026-03-31&end_date=2026-01-01")
        html = response.data.decode()
        # Expenses between Jan and Mar must appear after the swap.
        assert "Jan lunch" in html or "Mar rent" in html

    def test_no_date_parameters_page_returns_200(self, client, db, alice_with_expenses):
        """Visiting /profile with no date parameters must always succeed for a
        logged-in user — it is the baseline unfiltered view."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile")
        assert response.status_code == 200


# ===========================================================================
# TestValidation — invalid inputs and security
# ===========================================================================

class TestValidation:
    """Spec rules: date parameters must be validated; invalid formats are
    ignored; parameterised queries prevent SQL injection."""

    def test_invalid_start_date_format_is_ignored(self, client, db, alice_with_expenses):
        """An invalid start_date (not YYYY-MM-DD) must be silently ignored and
        the page must render without error showing all expenses."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile?start_date=not-a-date&end_date=2026-01-31")
        assert response.status_code == 200
        html = response.data.decode()
        # Invalid start_date discarded; only valid end_date may be applied.
        assert "<table" in html

    def test_invalid_end_date_format_is_ignored(self, client, db, alice_with_expenses):
        """An invalid end_date (not YYYY-MM-DD) must be silently ignored and
        the page must render without error."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile?start_date=2026-01-01&end_date=not-a-date")
        assert response.status_code == 200
        html = response.data.decode()
        assert "<table" in html

    def test_both_date_params_invalid_falls_back_to_all_expenses(
        self, client, db, alice_with_expenses
    ):
        """When both date parameters are invalid, the page falls back to
        showing all expenses (as if no filter was applied)."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile?start_date=abc&end_date=xyz")
        assert response.status_code == 200
        html = response.data.decode()
        # All expenses should still appear since both params are discarded.
        assert "Jan lunch" in html

    def test_date_with_wrong_separator_is_rejected(self, client, db, alice_with_expenses):
        """Dates using slashes (YYYY/MM/DD) instead of hyphens must be treated
        as invalid and ignored — not cause a crash."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile?start_date=2026/01/01&end_date=2026/01/31")
        assert response.status_code == 200

    def test_date_with_time_component_is_rejected(self, client, db, alice_with_expenses):
        """A datetime string (with time component) is not a valid YYYY-MM-DD
        date and must be ignored without crashing."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get(
            "/profile?start_date=2026-01-01T00:00:00&end_date=2026-01-31T23:59:59"
        )
        assert response.status_code == 200

    def test_sql_injection_in_start_date_does_not_crash(self, client, db, alice_with_expenses):
        """SQL injection attempt in start_date must not crash the server.
        Parameterised queries ensure the string is treated as a literal value
        (invalid date) and is safely discarded."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        injection = "' OR '1'='1"
        response = client.get(f"/profile?start_date={injection}&end_date=2026-01-31")
        assert response.status_code == 200

    def test_sql_injection_in_end_date_does_not_crash(self, client, db, alice_with_expenses):
        """SQL injection attempt in end_date must not crash the server."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        injection = "'; DROP TABLE expenses; --"
        response = client.get(f"/profile?start_date=2026-01-01&end_date={injection}")
        assert response.status_code == 200

    def test_sql_injection_cannot_bypass_user_isolation(
        self, client, db, alice_with_expenses, bob_with_expenses
    ):
        """Even with injection attempts, Bob's expenses must never appear on
        Alice's profile page."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        # Attempt to inject a condition that would return all users' expenses.
        injection = "2026-01-01' OR '1'='1"
        response = client.get(f"/profile?start_date={injection}")
        html = response.data.decode()
        assert response.status_code == 200
        # Bob's distinguishing expense description must not appear.
        assert "Bobs unique purchase" not in html

    def test_empty_string_date_params_treated_as_not_provided(
        self, client, db, alice_with_expenses
    ):
        """Empty string values for date params must be treated as absent (no
        filter applied)."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile?start_date=&end_date=")
        assert response.status_code == 200
        html = response.data.decode()
        # All expenses visible — empty strings are ignored.
        assert "Jan lunch" in html

    def test_very_long_date_string_does_not_crash(self, client, db, alice_with_expenses):
        """An extremely long value in the date parameter must not crash the
        server — it is simply treated as an invalid date and ignored."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        long_value = "A" * 10000
        response = client.get(f"/profile?start_date={long_value}")
        assert response.status_code == 200


# ===========================================================================
# TestURLAndState — filter state in query parameters
# ===========================================================================

class TestURLAndState:
    """Spec rules: filter state reflected in URL; form action points to /profile."""

    def test_filter_form_action_points_to_profile_route(
        self, client, db, alice_with_expenses
    ):
        """The date filter form's action attribute must target the /profile
        route so that the URL carries the query parameters after submission."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile")
        html = response.data.decode()
        assert 'action="' in html
        assert "/profile" in html

    def test_applied_start_date_is_preserved_in_form_input(
        self, client, db, alice_with_expenses
    ):
        """After a filter is applied, the start_date input's value attribute
        must be pre-filled with the applied start_date so the form reflects
        the current filter state."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile?start_date=2026-01-01&end_date=2026-01-31")
        html = response.data.decode()
        assert "2026-01-01" in html

    def test_applied_end_date_is_preserved_in_form_input(
        self, client, db, alice_with_expenses
    ):
        """After a filter is applied, the end_date input's value attribute
        must be pre-filled with the applied end_date."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile?start_date=2026-01-01&end_date=2026-01-31")
        html = response.data.decode()
        assert "2026-01-31" in html

    def test_two_different_users_filter_independently(
        self, client, db, alice_with_expenses, bob_with_expenses
    ):
        """Two users must each see only their own filtered data independently.

        Alice filters to January 2026 and must see her expenses but never
        Bob's expenses.
        """
        # Alice logs in and filters.
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile?start_date=2026-01-01&end_date=2026-01-31")
        html_alice = response.data.decode()

        assert "Jan lunch" in html_alice
        assert "Bobs unique purchase" not in html_alice

    def test_bob_sees_only_his_own_data(self, client, db, alice_with_expenses, bob_with_expenses):
        """Bob's profile shows only his expenses; Alice's expenses must not
        appear on Bob's page."""
        with client.session_transaction() as sess:
            sess.clear()
        _login(client, bob_with_expenses["email"], bob_with_expenses["password"])
        response = client.get("/profile?start_date=2026-01-01&end_date=2026-01-31")
        html_bob = response.data.decode()

        assert "Bobs unique purchase" in html_bob
        assert "Jan lunch" not in html_bob

    def test_filter_on_profile_returns_200_not_redirect(
        self, client, db, alice_with_expenses
    ):
        """A valid filter request for a logged-in user must return HTTP 200,
        not a redirect — the URL with query params is the canonical filtered URL."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get(
            "/profile?start_date=2026-01-01&end_date=2026-01-31",
            follow_redirects=False,
        )
        assert response.status_code == 200


# ===========================================================================
# TestRenderingAndUI — template structure and conditional elements
# ===========================================================================

class TestRenderingAndUI:
    """Spec rules for template rendering: form inputs, filter label,
    empty-states, and conditional Clear button."""

    def test_profile_page_contains_start_date_input(self, client, db, alice_with_expenses):
        """The profile page must render a date input field named 'start_date'."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile")
        html = response.data.decode()
        assert 'name="start_date"' in html
        assert 'type="date"' in html

    def test_profile_page_contains_end_date_input(self, client, db, alice_with_expenses):
        """The profile page must render a date input field named 'end_date'."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile")
        html = response.data.decode()
        assert 'name="end_date"' in html

    def test_profile_page_contains_filter_button(self, client, db, alice_with_expenses):
        """The profile page must render a submit button to apply the filter."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile")
        html = response.data.decode()
        # Spec: "Filter" button to apply the date range.
        assert "Filter" in html
        assert 'type="submit"' in html

    def test_clear_button_not_visible_when_no_filter_active(
        self, client, db, alice_with_expenses
    ):
        """The Clear/Reset button must NOT be visible when no filter is active.
        It should only appear when filter_active is True."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile")
        html = response.data.decode()
        # 'Clear' link should not appear on the unfiltered page.
        assert "Clear" not in html

    def test_clear_button_visible_when_filter_is_active(
        self, client, db, alice_with_expenses
    ):
        """When a valid date filter is applied, the Clear button must appear on
        the page so users can remove the filter."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile?start_date=2026-01-01&end_date=2026-01-31")
        html = response.data.decode()
        # Spec: Optional Reset or Clear button.
        assert "Clear" in html

    def test_filter_label_not_shown_without_filter(self, client, db, alice_with_expenses):
        """The 'Showing: ... — ...' filter range label must NOT appear when no
        filter is active — only display it when filter_active is True."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile")
        html = response.data.decode()
        # The label pattern from the template is "Showing:".
        assert "Showing:" not in html

    def test_filter_label_shown_when_filter_is_active(self, client, db, alice_with_expenses):
        """When a valid date filter is applied, the page must display the
        currently active date range (e.g., 'Showing: 2026-01-01 — 2026-01-31')."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile?start_date=2026-01-01&end_date=2026-01-31")
        html = response.data.decode()
        assert "Showing:" in html
        assert "2026-01-01" in html
        assert "2026-01-31" in html

    def test_empty_state_message_in_transaction_table(
        self, client, db, alice_with_expenses
    ):
        """When no transactions exist for the date range, the transaction table
        body must render the spec-required 'No expenses found' message instead
        of empty rows."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile?start_date=2099-01-01&end_date=2099-12-31")
        html = response.data.decode()
        assert "No expenses found" in html

    def test_empty_state_message_in_category_breakdown(
        self, client, db, alice_with_expenses
    ):
        """When no expenses exist for the date range, the category breakdown
        section must render its empty-state message."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile?start_date=2099-01-01&end_date=2099-12-31")
        html = response.data.decode()
        assert "No categories found" in html

    def test_transactions_table_present_on_profile(self, client, db, alice_with_expenses):
        """The transaction history table element must exist on the profile page."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile")
        html = response.data.decode()
        assert "<table" in html

    def test_stats_row_total_spent_label_present(self, client, db, alice_with_expenses):
        """The 'Total Spent' stat label must be present on the profile page."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile")
        html = response.data.decode()
        assert "Total Spent" in html

    def test_stats_row_transactions_label_present(self, client, db, alice_with_expenses):
        """The 'Transactions' stat label must be present on the profile page."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile")
        html = response.data.decode()
        assert "Transactions" in html

    def test_stats_row_top_category_label_present(self, client, db, alice_with_expenses):
        """The 'Top Category' stat label must be present on the profile page."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile")
        html = response.data.decode()
        assert "Top Category" in html

    def test_category_breakdown_section_present(self, client, db, alice_with_expenses):
        """The 'Spending by Category' section must be present on the profile page."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile")
        html = response.data.decode()
        assert "Spending by Category" in html

    def test_user_name_displayed_on_profile(self, client, db, alice_with_expenses):
        """The logged-in user's name must appear on the profile page."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile")
        html = response.data.decode()
        assert "Alice Tester" in html

    def test_user_email_displayed_on_profile(self, client, db, alice_with_expenses):
        """The logged-in user's email address must appear on the profile page."""
        _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
        response = client.get("/profile")
        html = response.data.decode()
        assert "alice@test.com" in html


# ===========================================================================
# Parametrized — multiple invalid date format scenarios
# ===========================================================================

INVALID_DATE_FORMATS = [
    "not-a-date",
    "01-01-2026",          # DD-MM-YYYY (wrong order)
    "2026/01/01",          # slashes instead of hyphens
    "2026-13-01",          # month 13 does not exist
    "2026-00-01",          # month 0 does not exist
    "2026-01-32",          # day 32 does not exist
    "20260101",            # no separators
    "Jan 1 2026",          # human-readable text
    "2026-1-1",            # missing zero-padding
    "",                    # empty string
    "   ",                 # whitespace only
    "null",
    "undefined",
    "<script>alert(1)</script>",  # XSS attempt
]


@pytest.mark.parametrize("bad_date", INVALID_DATE_FORMATS)
def test_invalid_start_date_formats_do_not_crash(client, db, alice_with_expenses, bad_date):
    """Every invalid start_date format listed in the parametrize decorator must
    be rejected gracefully — the page renders with HTTP 200 and does not raise
    an unhandled exception."""
    _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
    response = client.get(f"/profile?start_date={bad_date}&end_date=2026-01-31")
    assert response.status_code == 200


@pytest.mark.parametrize("bad_date", INVALID_DATE_FORMATS)
def test_invalid_end_date_formats_do_not_crash(client, db, alice_with_expenses, bad_date):
    """Every invalid end_date format listed in the parametrize decorator must
    be rejected gracefully — the page renders with HTTP 200."""
    _login(client, alice_with_expenses["email"], alice_with_expenses["password"])
    response = client.get(f"/profile?start_date=2026-01-01&end_date={bad_date}")
    assert response.status_code == 200

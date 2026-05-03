# Spec: Registration

## Overview

Implement user registration functionality that allows new users to create an account with their name, email, and password. This feature adds form validation, error handling, and securely persists user data to the database. Registration is the first step in the authentication flow and must be completed before users can access the expense tracker dashboard.

## Depends on

- Step 1: Database Setup — users table must exist with proper schema

## Routes

- `GET /register` — display registration form (already exists in app.py)
- `POST /register` — process registration form submission, validate input, create user account

## Database changes

No new database changes. Uses existing `users` table:
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `name` (TEXT NOT NULL)
- `email` (TEXT UNIQUE NOT NULL)
- `password_hash` (TEXT NOT NULL)
- `created_at` (TEXT DEFAULT CURRENT_TIMESTAMP)

## Templates

- **Modify:** `templates/register.html` — update form to support POST submission with proper error display

## Files to change

- `app.py` — implement `POST /register` handler with form processing and validation
- `templates/register.html` — add form fields, error messages, and submission support

## Files to create

None

## New dependencies

No new dependencies. Uses:
- `flask` (already installed)
- `werkzeug.security.generate_password_hash` (already installed)
- `database.db.get_db()` (already implemented)

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never use string formatting in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Form validation must occur server-side in Python, not just client-side HTML
- On successful registration, redirect user to login page with a success message (or to dashboard if auto-login)
- On validation error or duplicate email, re-render form with error messages
- Email must be unique (database constraint will enforce this, catch `sqlite3.IntegrityError`)
- Password must be at least 6 characters
- Name and email are required and non-empty

## Definition of done

- [ ] GET `/register` displays a form with fields: name, email, password, password confirmation
- [ ] POST `/register` accepts form data with proper validation
- [ ] Form validates: name non-empty, email is valid format, password ≥ 6 chars, passwords match
- [ ] Password is hashed using `generate_password_hash` before storage
- [ ] Duplicate email error is caught and displayed: "Email already registered"
- [ ] Other validation errors are displayed clearly (e.g., "Passwords do not match")
- [ ] On success, user is redirected to login page with message: "Registration successful. Please log in."
- [ ] Form errors persist form data (pre-fill name and email on re-render, never re-fill password)
- [ ] Page displays form with proper styling using CSS variables from `base.html`
- [ ] All SQL queries use parameterized syntax (?, ?)
- [ ] Registration form is responsive on mobile and desktop

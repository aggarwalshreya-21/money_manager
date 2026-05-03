# Spec: Login and Logout

## Overview
Implement user authentication with login and logout functionality. This step enables users to securely authenticate with their credentials and manage their session. Session data will be stored using Flask sessions (server-side). This is a critical feature that protects user data and enables the personalized dashboard experience in future steps.

## Depends on
- Step 1: Database Setup (users table must exist with password_hash column)

## Routes
- `POST /login` — Process login form submission, validate credentials, create session if valid. Access: public
- `POST /logout` — Clear session and redirect to landing page. Access: logged-in
- `GET /login` — Already exists, shows login form. Access: public

## Database changes
No new database changes. Uses existing `users` table with email and password_hash columns.

## Templates
- **Modify:** `login.html` — form already exists, may add error messages display
- **Modify:** `base.html` — update navbar to show logout link for logged-in users, hide login/register for logged-in users
- **Create:** `auth.html` (optional) — helper template for auth-related messages if needed

## Files to change
- `app.py` — implement POST handlers for `/login` and `/logout`, add session management
- `templates/base.html` — update navbar to conditionally show login/logout based on session
- `templates/login.html` — ensure form layout supports error messages

## Files to create
None

## New dependencies
No new dependencies. Flask session support is built-in.

## Rules for implementation
- No SQLAlchemy or ORMs — use parameterized queries only
- Passwords must be verified using `werkzeug.security.check_password_hash()`
- Use Flask sessions for session management with `flask.session`
- Session secret must be configured in Flask app
- All SQL queries must be parameterized (no string formatting)
- Error messages must be user-friendly (e.g., "Invalid email or password" not database-specific errors)
- Redirect after successful login to `/profile` (Step 4)
- Redirect after logout to `/` (landing page)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`

## Definition of done
- [ ] User can submit login form with email and password
- [ ] Valid credentials create a session and redirect to profile page
- [ ] Invalid credentials show error message "Invalid email or password"
- [ ] Navbar shows username and logout link for logged-in users
- [ ] Navbar shows "Sign in" and "Get started" for logged-out users
- [ ] Logout clears session and redirects to landing page
- [ ] Session persists across page navigation
- [ ] Password verification uses werkzeug.security.check_password_hash
- [ ] All SQL queries use parameterized syntax
- [ ] App starts without errors
- [ ] Demo user (demo@spendly.com / demo123) can log in successfully

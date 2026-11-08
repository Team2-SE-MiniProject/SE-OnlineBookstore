# Deviations from the SRS, SAD and Test Plan

**Project:** Online Bookstore (Team 2) · **Covers:** Sprint 1 and Sprint 2 · **Last updated:** 5 November 2026

This file lists where the implementation differs from the submitted SRS v1.0, SAD v1.0 and Test Plan v1.0, why, and what is planned. Requirement IDs (BOOK-F-…, BOOK-SR-…) come from those documents. 

## 1. Deviations

| # | Area (document reference) | Documented | Implemented | Reason / plan |
|---|---|---|---|---|
| D1 | Login method (SAD 3.4 and 4.3, BOOK-F-002) | JWT login at `POST /api/auth/login` with `{email, password}` | The storefront signs in with a session cookie through `POST /accounts/login/` (username and password, form post). The JWT endpoint `POST /api/auth/login` also exists (email or username) and returns `{status, token, role}`. Tokens are accepted by the cart, address and wishlist APIs. | Server-rendered pages work most simply with Django's session login. JWT is available for API clients. |
| D2 | Login error format (SAD 4.4) | Errors as `{code, message}` | `/accounts/login/` answers `{error}` (plus `locked_until` when locked). Every other API endpoint, including the JWT login, uses `{code, message}`. | The login view was written before the error standard. The pages read both formats. |
| D3 | Roles in the login response (SAD 4.3, BOOK-SR-004) | A role from RBAC | The `role` in the JWT login response is derived from the account: superuser is `admin`, a member of the `seller` group is `seller`, everyone else is `buyer`. | Kept simple. Permissions themselves are enforced by the RBAC code and the admin scoping. |
| D4 | TLS (BOOK-SR-001, SAD 3.9) | TLS 1.2+ for all connections | Django redirects HTTP to HTTPS and sets secure cookies and HSTS when `DEBUG` is off. Local development and the Docker demo run over plain HTTP. | The TLS protocol version is enforced by the web server or host in front of Django, so it belongs to deployment. |
| D5 | Database (SAD 3.6) | PostgreSQL | PostgreSQL is the default. It is used in CI and by `docker compose`. SQLite can be chosen locally with `DB_ENGINE=django.db.backends.sqlite3`. | Easier setup on student laptops. |
| D6 | Payment (BOOK-F-030 to 035, BOOK-SR-003, SAD Fig. 3) | Razorpay or Stripe, tokenised payment, order set to PAID | Razorpay Checkout opens from the checkout page. A verification endpoint and a webhook mark the order PAID. The project runs in Razorpay **test mode** only, so no real money moves. No card data touches our servers. | The webhook needs a public URL, which a laptop does not have, so locally the payment is confirmed by the browser's verification step. A live deployment would add live keys and the public webhook. |
| D7 | Catalog API (SAD 4.3) | `GET /api/books` with `q`, `genre`, `sort`, `page` | Path is `/api/books/` (trailing slash). Added `min_price` and `max_price`. The page size is fixed at 20. `sort` accepts `title`, `price_asc`, `price_desc`, `newest` and `rating` (average review rating, unrated books last). Search matches title, author, genre and ISBN, and every word must match. | Django URL convention, and the filters the SRS asks for (BOOK-F-011). |
| D8 | Email verification result (BOOK-F-001) | A confirmation for the user | Opening the emailed link shows a small JSON message (`Email verified. You can now log in.`) instead of a styled page. | Time. A confirmation page is a small later improvement. |
| D9 | Notifications (SRS 2.2, SAD 3.4) | Email and SMS | Both are sent in the background through Celery. Email covers registration and order confirmation. SMS covers order confirmation and goes to the phone number on the delivery address. By default both are printed in the worker log. Real email works through SMTP settings. A Twilio SMS backend exists but has not been tested against a live account. | Sending SMS in India needs DLT registration with the operators, which is beyond a student project. The backend is switchable through `SMS_BACKEND`. |
| D10 | Test tooling (Test Plan sections 5 and 6) | pytest, Selenium or Playwright, JMeter or Locust | Django's built-in test runner (`manage.py test`). The end-to-end test drives the real URLs with Django's test client, not a browser. The load test is a standard-library script (`tests/perf/load_test.py`). CI is GitHub Actions running flake8 (errors only) and the tests against PostgreSQL. Test names do not carry the TC-xxx IDs. | Faster, runs in CI and needs nothing extra installed. The RTM maps the TC IDs to the automated tests. |
| D11 | Seller and admin dashboards (SAD 3.3, BOOK-F-050 to 054) | Dashboards on Django Admin | Built on Django Admin at `/admin/`. A seller sees only their own books and the orders that contain them, can edit price and stock, and can mark orders shipped or delivered. An admin manages users (activate, deactivate, unlock), books, reviews, orders and read-only logs. Sales analytics exists only as a standalone prototype in `seller-analytics/`, not inside the application. | Django Admin follows the SAD and was the fastest correct route. Analytics inside the application is not done. |
| D12 | Fulfilment (BOOK-F-040 to 044) | Statuses placed, shipped, delivered, cancelled | Statuses are PENDING, PAID, SHIPPED, DELIVERED and CANCELLED, with rules for which move is allowed. Fulfilment is per order, so if an order has books from two sellers, whoever ships it ships the whole order. | Keeps the rules simple. Per-seller shipments are future work. |
| D13 | Reviews (BOOK-F-060 to 062) | Only verified buyers can review | The reviews API requires a login, but it does not check that the user bought the book. Moderation (hide and approve) works. | Not done in time. A check for a non-cancelled order containing the book is a small change. |

## 2. Additions not described in the documents

| # | Addition | Why |
|---|---|---|
| A1 | `isbn` field on `Book`. The sample books use real ISBNs. | The SRS requires search by ISBN, and the first model had no ISBN. |
| A2 | Address API (`/api/addresses/`) and an address form on the checkout page. | Checkout needs an `addressId`, and nothing could create one. |
| A3 | Storefront in Django templates and plain JavaScript: book list with search, filters, sort and pagination, book detail with reviews, login, register, cart, checkout with payment, and wishlist. | The SAD lists a Storefront Web UI, but the first backlog had no UI story. |
| A4 | `GET /api/auth/me` returns the current user and role. | A simple way to check a session or token. |
| A5 | `seed_books` loads 34 sample books with real ISBNs, prices and Open Library cover links. | Same test data for everyone and a realistic demo. |
| A6 | Docker setup (`Dockerfile`, `docker-compose.yml`) that starts the web app (gunicorn with WhiteNoise), the Celery worker, PostgreSQL and Redis with one command, plus `.env.example` and `docs/SETUP.md`. | Easy to run on any machine, and it documents the PostgreSQL requirement. |
| A7 | A console email backend that prints emails with unbroken links. | The standard one wraps long lines, which breaks the verification link when copied. |
| A8 | A `seller` field on `Book` and a `make_seller` command. | Sellers need to own books for the seller admin to work. |
| A9 | Catalog caching in Redis (cleared whenever a book or review changes), request monitoring and automated database backups. | Performance and operations stories (BOOK-NF-001 and BOOK-NF-002). |
| A10 | Order history, order confirmation and invoice, and return and refund requests as API endpoints. | BOOK-F-030 to 035 and 040 to 044. |

## 3. Implemented as documented (notes)

- **Passwords (BOOK-SR-002):** new passwords use bcrypt. The PBKDF2 hasher stays enabled so older accounts can still log in, and their hash is upgraded at their next login.
- **Account lockout (BOOK-F-003):** 5 failed attempts lock the account for 15 minutes, answer 423 and write an audit log entry. The session login and the JWT login share one implementation.
- **Error format (SAD 4.4):** a handler returns `{code, message}` for API errors, with a `details` field for validation errors.
- **Safe logging (SAD 4.4):** a log filter removes passwords, tokens, Bearer headers and card-like numbers from log output.
- **Admin action log (BOOK-SR-005):** changes made in the admin are recorded with time, user and action in a read-only "Admin action log", and security events in a read-only "Security event logs". Old audit records are cleaned up by a retention command.

## 4. Known issues

| # | Issue | Effect | Plan |
|---|---|---|---|
| K1 | Verification emails and SMS are sent by a background worker that needs Redis. | Without Redis and a running worker, registration still succeeds but nothing is sent, and the account stays inactive. | `docker compose up` starts both. `docs/SETUP.md` explains how to start them without Docker. |
| K2 | The tests, the catalog cache and request monitoring need Redis, and the tests need PostgreSQL (or the SQLite setting) available. | With Redis down, each request waits about 2 seconds for the monitoring write before carrying on, so a test run takes many minutes and fails. | Start the services first (`docker compose up -d db redis`). A short timeout for the monitoring write is planned. |
| K3 | Book covers load from Open Library by ISBN. | Covers need internet. A book with no cover shows a grey box. | None needed. |
| K4 | After a paid order, the cart is not emptied. | The same items stay in the cart. | Deactivate the cart when an order is paid. |

## 5. Not built, or carried over

- Order history and return requests have no storefront pages. They are available through the API.
- Sales analytics inside the application (only the prototype exists).
- Buttons to edit or delete your own review (the API supports both).
- Browser-based end-to-end tests (Playwright) and a production deployment.
- The 1,000-user load test (BOOK-NF-004). 200 users were tested.
- Real SMS delivery and a real uptime monitor.

## 6. Process notes

- Sprints are GitHub Milestones ("Sprint 1" and "Sprint 2"). Epics are parent issues, and stories are their sub-issues. Story points are a Project field. Practice issues from the first attempt were deleted, so the real issues start at #17.
- The first backlog had no UI story, so a "[UI] Storefront pages" issue was added during Sprint 1.
- The history of `main` was rewritten once during Sprint 1 to fix one team member's commit author email, so commit hashes changed. Pull requests and their numbers are unaffected.
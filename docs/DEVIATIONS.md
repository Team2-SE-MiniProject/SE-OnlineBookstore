# Deviations from the SRS, SAD and Test Plan

**Project:** Online Bookstore (Team 2) · **Covers:** Sprint 1 (19–23 Oct 2026) · **Last updated:** 24 Oct 2026

This file lists where the implementation differs from the submitted SRS v1.0, SAD v1.0 and Test Plan v1.0, why, and what is planned. Requirement IDs (BOOK-F-…, BOOK-SR-…) come from those documents.

## 1. Deviations

| # | Area (document reference) | Documented | Implemented | Reason / plan |
|---|---|---|---|---|
| D1 | Login method (SAD 3.4 and 4.3, BOOK-F-002) | JWT login at `POST /api/auth/login` with `{email, password}` | The storefront signs in with a session cookie through `POST /accounts/login/` (username and password, form post). The JWT endpoint `POST /api/auth/login` also exists (email or username) and returns `{status, token, role}`. Tokens are accepted by the cart and address APIs. The checkout endpoint still uses session login. | Server-rendered pages work most simply with Django's session login. JWT is available for API clients. |
| D2 | Login error format (SAD 4.4) | Errors as `{code, message}` | `/accounts/login/` answers `{error}` (plus `locked_until` when locked). Every other API endpoint, including the JWT login, uses `{code, message}`. | The login view was written before the error standard. The UI reads both formats. Planned: align it. |
| D3 | Roles (SAD 4.3, BOOK-SR-004) | Role from RBAC | The `role` in the JWT login response is derived: superuser is `admin`, a member of the `seller` group is `seller`, everyone else is `buyer`. | The RBAC story (#35) defines the real rules. |
| D4 | TLS (BOOK-SR-001, SAD 3.9) | TLS 1.2+ for all connections | Django redirects HTTP to HTTPS and sets secure cookies and HSTS when `DEBUG` is off. Local development runs over plain HTTP. | The TLS protocol version is enforced by the web server or host in front of Django, so it is part of deployment. |
| D5 | Database (SAD 3.6) | PostgreSQL | PostgreSQL is the default and is used in CI. SQLite can be chosen locally with `DB_ENGINE=django.db.backends.sqlite3`. | Easier setup on student laptops. |
| D6 | Payment (BOOK-F-030 to 035, BOOK-SR-003, SAD Fig. 3) | Razorpay or Stripe, tokenised payment, order set to PAID by webhook | Checkout creates a `PENDING` order and returns a placeholder `paymentUrl`. Stock is not reduced yet. The UI does not follow the placeholder link and shows a confirmation saying payment is pending. No card data is handled. | Gateway integration is the "Payment gateway integration" story in Sprint 2. |
| D7 | Catalog API (SAD 4.3) | `GET /api/books` with `q`, `genre`, `sort`, `page` | Path is `/api/books/` (trailing slash). Added `min_price` and `max_price`. The page size is fixed at 20. `sort` accepts `title`, `price_asc`, `price_desc`, `newest` and `rating` (average review rating, unrated books last). Search matches title, author, genre and ISBN, and every word must match. | Django URL convention, and the filters the SRS asks for (BOOK-F-011). |
| D8 | Email verification result (BOOK-F-001) | A confirmation for the user | Opening the emailed link shows a small JSON message (`Email verified. You can now log in.`) instead of a styled page. | Time. A confirmation page is a small later improvement. |
| D9 | Notifications (SRS 2.2, SAD 3.4) | Email and SMS | Email only (registration and order confirmation, sent through Celery). SMS is not implemented. | Out of Sprint 1 scope. |
| D10 | Test tooling (Test Plan sections 5 and 6) | pytest, Selenium or Playwright, JMeter or Locust | Django's built-in test runner (`manage.py test`). CI is GitHub Actions running flake8 (errors only) and the tests against PostgreSQL. End-to-end, load and security test tooling is planned for Sprint 2. Test names do not carry the TC-xxx IDs yet. | The RTM is updated in the "UAT, RTM update and Test Summary Report" story in Sprint 2. |
| D11 | Seller and admin dashboards (SAD 3.3, BOOK-F-050 to 054) | Dashboards on Django Admin | Not built yet. Django's built-in admin is available at `/admin/`. | Planned for Sprint 2. |

## 2. Additions not described in the documents

| # | Addition | Why |
|---|---|---|
| A1 | `isbn` field on `Book` (catalog migration 0002). | The SRS requires search by ISBN, and the first model had no ISBN. Sample ISBNs are made up. |
| A2 | Address API `GET` and `POST /api/addresses/`, plus an address form on the checkout page. | Checkout needs an `addressId` (BOOK-F-030 to 035), and nothing could create one. |
| A3 | Storefront UI in Django templates and plain JavaScript: book list with search, filters, sort and pagination, login, register, cart, checkout and order confirmation. | The SAD lists a Storefront Web UI, but the first backlog had no UI story. A "[UI] Storefront pages" issue was added during Sprint 1. Not built yet: wishlist page, book detail page, order history, seller and admin screens. |
| A4 | `GET /api/auth/me` returns the current user and role. | A simple way to check a session or token. |
| A5 | `seed_books` command loads 25 sample books with placeholder covers. | Gives everyone the same test data and makes the demo realistic. |

## 3. Implemented as documented (notes)

- **Passwords (BOOK-SR-002):** new passwords use bcrypt. The PBKDF2 hasher stays enabled so older accounts can still log in, and their hash is upgraded at their next successful login.
- **Account lockout (BOOK-F-003):** 5 failed attempts lock the account for 15 minutes, answer 423, and write an audit log entry. The session login and the JWT login share one implementation.
- **Error format (SAD 4.4):** a handler returns `{code, message}` for API errors. Validation errors add a `details` field. Unexpected server errors return a generic JSON 500 when `DEBUG` is off.
- **Safe logging (SAD 4.4):** a log filter removes passwords, tokens, Bearer headers and card-like numbers from log messages and tracebacks.

## 4. Known issues

| # | Issue | Effect | Plan |
|---|---|---|---|
| K1 | Verification emails are sent through Celery and Redis. Without Redis and a running worker, nothing is sent. | Registration still succeeds, but the account stays inactive. For the demo, the verification link was generated from the server instead. | Document the Redis and Celery start-up steps and fix delivery in Sprint 2. |
| K2 | Checkout does not empty the cart after an order is created. | The same items can be ordered again. | Deactivate the cart after order creation. |
| K3 | Sample book covers load from placehold.co. | Covers do not show offline. | None needed. |

## 5. Process notes

- Sprints are GitHub Milestones ("Sprint 1" and "Sprint 2"). Epics are parent issues, and stories are their sub-issues. Story points are a Project field. Practice issues from the first attempt were deleted, so the real issues start at #17.
- The history of `main` was rewritten once during Sprint 1 to fix one team member's commit author email, so commit hashes changed. Pull requests and their numbers are unaffected.
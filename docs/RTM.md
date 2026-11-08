# Requirements Traceability Matrix (RTM)

**Project:** Online Bookstore (Team 2) · **Updated:** 5 November 2026 · **Replaces:** the sample RTM in SRS section 8

This matrix connects every requirement in the SRS to the code that implements it, the test cases that check it and the current status. The automated tests are Django test modules. Run them all with `python manage.py test` (start `docker compose up -d db redis` first).

**Status legend (as in the SRS RTM):** **A** = requirement met and verified · **P** = partly met, see the comment · **N** = not met.

## Functional requirements

| Req ID | Requirement (short) | Implemented in | Test case | Automated tests | Status | Comments |
|---|---|---|---|---|---|---|
| BOOK-F-001 | Register with email verification | `accounts/registration.py`, storefront register page | TC-Auth-01 | `accounts.test_registration`, `bookstore.test_e2e` | A | The email is sent through Celery. See DEVIATIONS D8 and K1. |
| BOOK-F-002 | Authenticate with hashed password and JWT | `accounts/views.py` (session login), `accounts/token_views.py` (JWT login) | TC-Auth-02 | `accounts.test_token_auth`, `accounts.tests` | A | Session login for the pages, JWT for API clients. See D1. |
| BOOK-F-003 | Lock the account after 5 failed logins for 15 minutes | `accounts/views.py` (`authenticate_with_lockout`) | TC-Auth-03 | `accounts.tests` (lockout), `accounts.test_token_auth` | A | Both logins share one implementation. |
| BOOK-F-010 | Paginated catalog, 20 per page | `catalog` (`/api/books/`), storefront book list | TC-Cat-01 | `catalog.test_api`, `catalog.tests`, `catalog.test_detail`, `catalog.test_caching`, `catalog.test_cache_invalidation`, `storefront.tests` | A | Load test results are under BOOK-NF-001. |
| BOOK-F-011 | Search by title, author, ISBN or genre, with filter and sort | `catalog/views.py` | TC-Cat-02 | `catalog.test_search`, `bookstore.test_security` (fuzzing) | A | Sort by price, newest, title and rating. |
| BOOK-F-020 to 023 | Cart and wishlist, cart kept across sessions | `cart`, `wishlist`, storefront cart and wishlist pages | | `cart.test_cart`, `cart.tests`, `wishlist.tests`, `storefront.test_wishlist_page`, `bookstore.test_e2e` | A | |
| BOOK-F-030 to 035 | Checkout, coupons, payment, confirmation and invoice | `orders` (checkout, payment verification, webhook, confirmation, invoice), storefront checkout page | | `orders.tests`, `notifications.test_sms`, `bookstore.test_e2e` | A | Razorpay test mode (D6). The invoice is an API endpoint. |
| BOOK-F-040 to 044 | Order history, tracking, returns and refunds, fulfilment | `orders` (history, return and refund requests, `fulfilment.py`) | | `orders.tests`, `orders.test_fulfilment` | A | Fulfilment is per order (D12). History and returns are API only. |
| BOOK-F-050 to 054 | Seller and admin dashboards, analytics | Django Admin: `accounts/admin.py`, `catalog/admin.py`, `orders/admin.py`, `reviews/admin.py` | | `accounts.test_admin`, `catalog.test_seller_admin`, `reviews.test_admin`, `orders.test_fulfilment` | P | Sales analytics exists only as a prototype in `seller-analytics/` (D11). |
| BOOK-F-060 to 062 | Ratings, reviews and moderation | `reviews`, storefront book page | | `reviews.test_reviews`, `reviews.test_moderation`, `reviews.tests`, `storefront.test_book_detail` | P | Moderation works. The "verified buyers only" rule is not enforced (D13). |

## Non-functional requirements

| Req ID | Requirement (short) | Implemented in | Test case | Automated tests and evidence | Status | Comments |
|---|---|---|---|---|---|---|
| BOOK-NF-001 | Catalog and product pages in 2 s or less for 90% of requests | Redis caching, gunicorn, WhiteNoise | TC-Perf-01 | `tests/perf/load_test.py` (results in `tests/perf/results.md`), `catalog.test_caching` | A | 90th percentile 142 ms at 50 users and 1,636 ms at 200 users. |
| BOOK-NF-002 | 99.5% availability per month | `monitoring` app, automated database backups | Ops report | `monitoring.tests` | P | Availability can only be measured in production. |
| BOOK-NF-003 | PCI-DSS: no card data in plaintext on our servers | Razorpay handles card entry. No model has a card field. | TC-Sec-01 | `bookstore.test_security.DataProtectionTests` | A | A formal PCI-DSS audit applies only to a production deployment. |
| BOOK-NF-004 | At least 1,000 concurrent users | gunicorn (4 workers, 4 threads) | TC-Perf-02 | `tests/perf/load_test.py` | P | 200 users tested. 1,000 users cannot be shown on a laptop. |
| BOOK-NF-005 | WCAG 2.1 AA on browse, cart and checkout | Storefront templates and CSS | TC-UX-01 | `docs/accessibility/WCAG-2.1-AA-report.md`, UAT scenarios U-23 and U-24 | P | Becomes A when the manual keyboard and zoom checks in the UAT script are recorded as passed. |

## Security requirements

| Req ID | Requirement (short) | Implemented in | Test case | Automated tests | Status | Comments |
|---|---|---|---|---|---|---|
| BOOK-SR-001 | TLS 1.2+ for all connections | `bookstore/settings.py` (HTTPS redirect, secure cookies, HSTS when `DEBUG` is off) | TC-Sec-02 | `bookstore.test_security.AccessControlTests` (includes CSRF) | P | The TLS version is enforced by the web server or host. See D4. |
| BOOK-SR-002 | Salted bcrypt or argon2 password hashes | `PASSWORD_HASHERS` in settings | TC-Sec-03 | `accounts.test_token_auth.PasswordHashingTests`, `bookstore.test_security.DataProtectionTests` | A | |
| BOOK-SR-003 | Card data never stored | No card fields in any model | TC-Sec-04 | `bookstore.test_security.DataProtectionTests` | A | The test scans every model for card-related field names. |
| BOOK-SR-004 | Role-based access control | `accounts/permissions.py`, admin scoping | TC-Sec-05 | `accounts.test_rbac`, `accounts.test_rbac_endpoints`, `bookstore.test_security.AccessControlTests`, `catalog.test_seller_admin` | A | |
| BOOK-SR-005 | Admin actions logged with time, user and action, kept for 1 year | Django admin log, `AuditLog`, retention clean-up | TC-Sec-06 | `accounts.test_audit`, `accounts.test_admin` | A | |

## Summary

- **20 requirement groups:** 14 met (A), 6 partly met (P), 0 not met (N).
- Partly met: sales analytics inside the application (BOOK-F-050 to 054), the verified-buyer rule (BOOK-F-060 to 062), measured availability (BOOK-NF-002), 1,000 concurrent users (BOOK-NF-004), manual accessibility checks (BOOK-NF-005) and TLS version enforcement (BOOK-SR-001).
- Every requirement has at least one automated test or documented evidence.
- Test cases TC-Auth-01 to 03, TC-Cat-01 and 02, TC-Perf-01 and 02 and TC-Sec-01 to 06 are covered by the automated tests above. TC-UX-01 is covered by the accessibility report and the UAT script.
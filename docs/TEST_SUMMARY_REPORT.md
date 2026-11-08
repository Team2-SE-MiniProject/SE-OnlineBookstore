# Test Summary Report

**Project:** Online Bookstore (Team 2) · **Version:** 1.0 · **Date:** 5 November 2026 · **Prepared by:** Zia Kadijah (QA Lead)

**Related documents:** SRS v1.0, SAD v1.0, Test Plan v1.0, `docs/RTM.md`, `docs/UAT.md`, `docs/DEVIATIONS.md`, `tests/perf/results.md`.

## 1. Summary

The project has an automated suite of **228 tests** that runs on every pull request in GitHub Actions. All of them pass on `main`. On top of that there is an end-to-end journey test, a security suite that includes fuzzing, and a load test. Performance meets the 2-second target at 50 and 200 simultaneous users on the production-style setup (gunicorn). The manual user acceptance test is prepared in `docs/UAT.md` and is run and signed off by the Product Owner. Fourteen of the twenty requirement groups are fully met and six are partly met. They are listed in section 9.

## 2. Scope and approach

Tested as planned in the Test Plan: authentication, catalog and search, cart and wishlist, checkout and payment, order management, seller and admin management, and reviews. The payment gateway's internal processing and the Django admin framework itself are not tested, as the Test Plan states.

| Test level or type (Test Plan section 5) | What was done |
|---|---|
| Unit | Module-level Django tests in every app. |
| Integration | API and database tests in each app, checkout integration tests, and payment verification and webhook tests with the gateway calls mocked. |
| System | `bookstore.test_e2e`: register, verify, log in, search, cart, address, checkout, an admin ships the order, a review is written and then hidden. |
| Acceptance | `docs/UAT.md`, 26 scenarios, run by hand. |
| Functional and regression | The full suite runs on every pull request in CI. |
| Performance | `tests/perf/load_test.py` (section 5). |
| Security | `bookstore.test_security` (section 6). |
| Usability and accessibility | `docs/accessibility/WCAG-2.1-AA-report.md`, with a manual keyboard and zoom check in the UAT script. |

Deviations from the Test Plan: Django's built-in test runner replaced pytest, the end-to-end test drives the real URLs with Django's test client rather than a browser tool, and the load test is a standard-library script rather than JMeter or Locust (see `docs/DEVIATIONS.md`, D10).

## 3. Test environment

| Environment | Setup |
|---|---|
| Developer machines | Windows, Python 3.14, SQLite or PostgreSQL, Redis. Tests need Redis and the database running: `docker compose up -d db redis`. |
| CI (GitHub Actions) | Python 3.12, PostgreSQL, Redis, flake8 for serious lint errors, then `python manage.py test`. |
| Docker (`docker compose up`) | Python 3.12 image, PostgreSQL 16, Redis 7, Celery worker, gunicorn with 4 workers and 4 threads, static files served by WhiteNoise. Used for the load tests and the demo. |

## 4. Automated results

All 228 tests passed in the final run on `main`, and CI is green. The tests cover these areas:

| Area | Test modules |
|---|---|
| Accounts: login, registration, lockout, roles, audit log, admin | `accounts.*` |
| Project level: end-to-end journey, error format, log redaction, security | `bookstore.*` |
| Cart and wishlist | `cart.*`, `wishlist.*` |
| Catalog: list, search, caching, detail, seller admin | `catalog.*` |
| Monitoring | `monitoring.*` |
| Notifications: email, SMS, worker | `notifications.*` |
| Orders: checkout, payment, history, returns, fulfilment | `orders.*` |
| Reviews: API, moderation, admin | `reviews.*` |
| Storefront pages, book detail and wishlist pages, address API | `storefront.*` |

## 5. Performance results (BOOK-NF-001, BOOK-NF-004)

Method: `tests/perf/load_test.py` simulates users who keep opening the catalog, search, filtered and sorted lists, the home page, a book page and its reviews, against the Docker setup. The full tables are in `tests/perf/results.md`.

| Run | Users | Requests per second | Errors | 90th percentile | Target | Result |
|---|---|---|---|---|---|---|
| Development server (first run) | many | 12.9 | 0 | 16,299 ms | 2,000 ms | Fail |
| gunicorn and WhiteNoise | 1 | 7.1 | 0 | 54 ms | 2,000 ms | Pass |
| gunicorn and WhiteNoise | 50 | 259.6 | 0 | 142 ms | 2,000 ms | Pass |
| gunicorn and WhiteNoise | 200 | 235.6 | 0 | 1,636 ms | 2,000 ms | Pass |

The first run showed that Django's development server cannot handle concurrent load. Switching to gunicorn with several workers and threads, and serving static files with WhiteNoise, fixed it. The requirement of 1,000 concurrent users (BOOK-NF-004) was not demonstrated: a laptop running the whole stack cannot generate or serve that load, and at 200 users the 90th percentile is already close to the target.

## 6. Security test results (Test Plan section 5.1)

| Check | Result |
|---|---|
| Odd input (SQL fragments, script tags, very long text, unusual numbers, unicode) sent to the catalog filters, registration, login, address and review forms never causes a server error. | Pass, after one fix (defect 2). |
| Login with such input never lets anyone in. | Pass |
| Private pages and APIs (cart, addresses, checkout) require a login. | Pass |
| The admin needs staff access. Buyers and visitors are sent to the login page. | Pass |
| Users cannot see each other's carts, remove each other's cart items, or check out with another person's address. | Pass |
| A tampered JWT is rejected. | Pass |
| CSRF protection is enforced on login. | Pass |
| Passwords are stored as bcrypt hashes. | Pass |
| No model has a field for card data. | Pass |
| Book titles, authors and descriptions are HTML-escaped on the book page. | Pass |
| Seller admin: a seller sees and changes only their own books and orders, can ship but not cancel. | Pass |

Not tested: TLS versions (a deployment setting), and penetration testing with external tools.

## 7. Accessibility (BOOK-NF-005)

Static accessibility checks, a colour-contrast check and Lighthouse results are recorded in `docs/accessibility/WCAG-2.1-AA-report.md`. The pages have labelled form fields, a skip link, visible keyboard focus, and announcements for status messages. A manual keyboard and zoom check is part of the UAT script (U-25 and U-26).

## 8. Defects found and fixed

| # | Defect | Found by | Fix |
|---|---|---|---|
| 1 | The pull request failed in CI: PyJWT and bcrypt were missing from `requirements.txt`. | CI | Added both packages. |
| 2 | A very large `min_price` or `max_price` (for example `1e999`) crashed the catalog with a server error. | Fuzz tests | Prices above the stored maximum are answered with a normal 400 error. |
| 3 | The verification link in the emailed message was cut at a line break, so the link did not work when copied. | Manual testing | A console email backend that prints the message without wrapping. |
| 4 | The 90th percentile was about 16 seconds under load on the development server. | Load test | Run under gunicorn with WhiteNoise (section 5). |
| 5 | A test file broke the test run after a merge conflict (a syntax error). | CI | The file was repaired and the run passed again. |
| 6 | The payment verification and webhook routes were lost when the invoice branch was merged, so `main` was red with 6 failing payment tests. | CI and local runs | The two routes were restored. |
| 7 | Cached catalog and book pages could show old prices, stock and ratings after the data changed. Two tests failed locally. | Local test run | The cache is cleared whenever a book or review is saved or deleted, with new tests. |

All seven were fixed. No known defect is open. One limitation is recorded in `docs/DEVIATIONS.md` (K2): when Redis is down, each request waits about 2 seconds for the monitoring write, so test runs and pages are very slow until Redis is started.

## 9. Requirement coverage

`docs/RTM.md` links every requirement to its implementation and tests. **14 of 20** requirement groups are met and **6** are partly met, with none unmet.

Partly met: sales analytics inside the application (BOOK-F-050 to 054), the verified-buyer rule for reviews (BOOK-F-060 to 062), measured availability (BOOK-NF-002), 1,000 concurrent users (BOOK-NF-004), manual accessibility checks (BOOK-NF-005) and TLS version enforcement (BOOK-SR-001).

## 10. Exit criteria (Test Plan section 5)

| Criterion | Status |
|---|---|
| 100% of planned test cases executed | Met. The automated suite runs in full on every pull request, and the 26 UAT scenarios have been run. |
| 0 critical defects open | Met. No known defect is open. |
| All acceptance criteria satisfied | Mostly met. Fourteen requirement groups are fully met and six are partly met, as listed in section 9. |

## 11. Known limitations and work carried over

- Sales analytics exists as a prototype in `seller-analytics/`, not inside the application.
- The "verified buyers only" rule for reviews.
- Order history and return requests are API endpoints without storefront pages.
- End-to-end tests run without a real browser. A browser smoke test (Playwright) is a possible next step.
- A production deployment, a TLS certificate, real uptime monitoring and the 1,000-user load test.

## 12. Sign-off

| Role | Name | Signature / date |
|---|---|---|
| QA Lead | Zia Kadijah | |
| Dev Lead | | |
| Product Owner | Vidya Sri Ganesh | |
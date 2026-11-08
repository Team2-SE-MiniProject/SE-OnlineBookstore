# Online Bookstore

[![CI](https://github.com/Team2-SE-MiniProject/SE-OnlineBookstore/actions/workflows/ci.yml/badge.svg)](https://github.com/Team2-SE-MiniProject/SE-OnlineBookstore/actions/workflows/ci.yml)

A web bookstore built for the Software Engineering mini project (Team 2). Readers can browse, search, save and buy books. Sellers manage their own listings and orders. Admins oversee users, the catalog, orders and reviews.

## Team Members

- **Zia Kadijah** - [@zia0307](https://github.com/zia0307)
- **Nidhi Yedida** - [@nidhiyedida](https://github.com/nidhiyedida)
- **Vidya Sri Ganesh** - [@vidyasriganesh](https://github.com/vidyasriganesh)
- **Hithesh Nanjunda Swamy** - [@hithesh-n-03](https://github.com/hithesh-n-03)

## Features

- Register with email verification, log in (session for the pages, JWT for API clients), and account lockout after repeated failures
- Browse, search, filter and sort the catalog, with book pages showing ratings and reviews
- Cart, wishlist, delivery addresses, coupons, and checkout with Razorpay payment (test mode)
- Order history, order confirmation and invoice, and return and refund requests
- Seller and admin dashboards in Django Admin: sellers see only their own books and orders, and admins manage users, books, orders, reviews and logs
- Email and SMS notifications, printed in the worker log by default
- Accessible pages (WCAG 2.1 AA checks recorded in the accessibility report)

## Quick start

You need [Docker Desktop](https://www.docker.com/products/docker-desktop/) running.

```
docker compose up --build
```

Open <http://localhost:8000>. This starts the web app (gunicorn), the Celery worker, PostgreSQL and Redis, and loads 34 sample books. Create an admin login with `docker compose exec web python manage.py createsuperuser`.

The full guide, including running without Docker, email and SMS, Razorpay test keys and the load test, is in [docs/SETUP.md](./docs/SETUP.md).

## Running the tests

The tests need PostgreSQL and Redis to be running:

```
docker compose up -d db redis
python manage.py test
```

Load test (with the Docker stack running): `python tests/perf/load_test.py --users 50 --seconds 30`

## Built with

Python and Django, Django REST Framework, PostgreSQL, Redis and Celery, gunicorn and WhiteNoise, plain JavaScript and Django templates for the storefront, and Razorpay for payments.

## Project documents

- [Software Requirements Specification (SRS)](docs/2_SRS_MiniProject.pdf)
- [Software Architecture/Design Document (SAD)](docs/2_SAD_MiniProject.pdf)
- [Test Plan](docs/2_TestPlan_MiniProject.pdf)
- [Deviations from the documents](docs/DEVIATIONS.md)
- [Requirements traceability matrix (RTM)](docs/RTM.md)
- [User acceptance test (UAT) script](docs/UAT.md)
- [Test summary report](docs/TEST_SUMMARY_REPORT.md)
- [Accessibility report (WCAG 2.1 AA)](docs/accessibility/WCAG-2.1-AA-report.md)
- [Setup and run guide](docs/SETUP.md)

## Demo videos

- [Sprint 1 demo](docs/demos/sprint1_demo.mp4)
- [Sprint 2 demo](docs/demos/sprint2_demo.mp4)

## Status

Both sprints are complete and development is frozen for submission. What was not completed, and where the implementation differs from the submitted documents, is listed in [docs/DEVIATIONS.md](docs/DEVIATIONS.md).
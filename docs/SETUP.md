# Setup and run guide

How to run the Online Bookstore on your own machine. Pick **Option A (Docker)** for the least work, or **Option B (without Docker)** if you prefer to see each part.

## Option A: Docker (recommended)

You need [Docker Desktop](https://www.docker.com/products/docker-desktop/) running. Nothing else has to be installed: the project starts its own PostgreSQL, Redis, web server and Celery worker.

```
docker compose up --build
```

When the `web` service says it is running, open <http://localhost:8000>. The first start also creates the database tables and loads 25 sample books.

Useful commands (in a second terminal, from the project folder):

```
docker compose exec web python manage.py createsuperuser          # an account for /admin/ and for logging in
docker compose exec web python manage.py shell -c "from orders.models import Coupon; Coupon.objects.get_or_create(code='WELCOME10', defaults={'discount_percent': 10, 'is_active': True})"
docker compose exec web python manage.py test                     # run the test suite
docker compose logs -f worker                                     # emails and SMS appear here
docker compose down                                               # stop (add -v to also delete the database)
```

Stop any `runserver` you started outside Docker first, because both use port 8000.

## Option B: without Docker

You need Python 3.12 or newer.

```
python -m venv venv
venv\Scripts\activate            # Git Bash: source venv/Scripts/activate
pip install -r requirements.txt
copy .env.example .env           # Git Bash: cp .env.example .env
python manage.py migrate
python manage.py seed_books
python manage.py createsuperuser
python manage.py runserver
```

The `.env.example` file uses SQLite, so no database install is needed. Open <http://127.0.0.1:8000>.

### Using PostgreSQL instead of SQLite

PostgreSQL is the database named in the design document, and the CI pipeline uses it. Install PostgreSQL, create a database, then edit `.env`: delete the `DB_ENGINE` line and set `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` and `DB_PORT` (see the comments in `.env.example`). Run `python manage.py migrate` again. The Python driver is already in `requirements.txt`; the PostgreSQL server is a separate program.

### Sending emails and SMS (optional)

Registration emails and order confirmations are sent by a background worker, which needs Redis.

1. Start Redis. The easiest way is `docker run -d --name redis -p 6379:6379 redis:7`.
2. In another terminal with the virtual environment active, start the worker:
   - Windows: `celery -A bookstore worker -l info --pool=solo`
   - Mac or Linux: `celery -A bookstore worker -l info`
3. Register on `/register/` or place an order. The email (and the SMS, when the delivery address has a phone number) is printed in the **worker** terminal. Copy the verification link from there.

Without Redis, registration and checkout still work; the messages are just not sent.

To send **real emails**, set the `EMAIL_*` lines in `.env` (the Gmail example is in `.env.example`; Gmail needs an app password). SMS is printed to the worker log by default. A real provider can be switched on with `SMS_BACKEND` and the `TWILIO_*` settings, but sending SMS in India also needs DLT registration, so this has not been tested against a live account.

## Demo data

- `python manage.py seed_books` loads 25 sample books. It is safe to run again.
- Create a login with `createsuperuser`, or register on the site and use the verification link from the worker terminal.
- Create the `WELCOME10` coupon with the command shown in Option A (without `docker compose exec web`).

## Running the tests

```
python manage.py test
```

## Deployment plan (not deployed)

The project runs locally for the course demo. A production setup would use:

- **Web server:** gunicorn behind nginx, with TLS 1.2 or newer terminated at nginx (BOOK-SR-001).
- **Settings:** `DEBUG` off, `ALLOWED_HOSTS` set and a real `SECRET_KEY`, all from environment variables. `DEBUG` and `ALLOWED_HOSTS` are fixed in `settings.py` today and would be made configurable first.
- **Data:** managed PostgreSQL with automated backups, and Redis for Celery.
- **Workers:** the Celery worker as a separate service, with a real SMTP provider for email.
- **Static files:** `collectstatic`, served by nginx or a CDN.
- **Payments:** gateway keys (Razorpay or Stripe) from environment variables.
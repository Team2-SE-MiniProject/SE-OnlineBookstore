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

## Database Backups and Replication

### Automated PostgreSQL Backups

The Docker Compose setup includes a dedicated `backup` service.

- **Backup tool:** PostgreSQL `pg_dump`.
- **Format:** Custom compressed dump (`.dump`).
- **Frequency:** Every 24 hours.
- **Retention:** 7 days.
- **Storage:** Persistent Docker volume named `db_backups`.
- **Startup behaviour:** An initial backup is created when the backup service starts.

The backup interval and retention period can be configured using environment variables:

```bash
BACKUP_INTERVAL_SECONDS=86400
BACKUP_RETENTION_DAYS=7
```

Useful commands:

```bash
# Start the backup service
docker compose up -d backup

# View backup logs
docker compose logs backup

# List available backups
docker compose exec backup ls -lh /backups
```
### Restoring a Database Backup

1. Stop the application services before restoring:

```bash
docker compose stop web worker
```

2. List the available backups:

```bash
docker compose exec backup ls -lh /backups
```

3. Restore the selected backup:

```bash
docker compose exec backup pg_restore \
  -h db -U bookstore -d online_bookstore \
  --clean --if-exists --no-owner \
  /backups/online_bookstore_TIMESTAMP.dump
```

Replace `TIMESTAMP` with the actual backup filename.

**Warning:** The `--clean` option replaces existing database objects. Verify the backup before restoring.

4. Restart the application:

```bash
docker compose start web worker
```

### Standby PostgreSQL Database Replica

A production deployment can use PostgreSQL streaming replication to maintain a standby database.

**Architecture:**

- **Primary database:** Handles application reads and writes.
- **Standby database:** Receives and replays database changes from the primary.
- **Replication:** Uses PostgreSQL streaming replication to transfer database changes.
- **Failover:** If the primary becomes unavailable, the standby can be promoted to become the new primary.

**Configuration requirements:**

1. Configure the primary PostgreSQL server with:
   - `wal_level = replica`
   - `max_wal_senders` greater than zero.
   - A replication user with the `REPLICATION` privilege.
   - Appropriate replication access rules in `pg_hba.conf`.

2. Configure the standby server:
   - Initialize it using `pg_basebackup`.
   - Configure `primary_conninfo` to connect to the primary.
   - Create the `standby.signal` file to enable standby mode.

3. Monitor replication lag and standby availability.

4. Test failover and recovery procedures regularly.

**Current implementation status:** Automated database backups are configured in Docker Compose. A separate standby replica is documented as a production reliability design but is not deployed in the local development environment.

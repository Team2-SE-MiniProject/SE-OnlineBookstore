FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first so Docker can reuse this layer when only code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as a normal user instead of root.
RUN useradd --create-home app && chown -R app /app
USER app

EXPOSE 8000

# Development server. See "Deployment plan" in docs/SETUP.md for a production setup.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
# LinkPulse

A URL shortener built to demonstrate backend systems fundamentals, not just
CRUD: async event processing, rate limiting, and reliable webhook delivery.

## Why this exists

Most shortener projects stop at "generate a code, redirect." The interesting
engineering problems start after that: how do you log analytics without
slowing down the redirect? How do you protect the API from abuse? How do you
reliably notify a third party when their webhook endpoint is flaky?

## Architecture

```
Client → FastAPI ──┬──> PostgreSQL (users, urls, click_events, webhooks)
                    ├──> Redis (rate limiting + Celery broker/backend)
                    └──> Celery task queue
                              ├── record_click            (async click logging)
                              ├── dispatch_webhooks_for_click
                              └── deliver_webhook          (retries w/ backoff)
```

**Key design decision:** the redirect endpoint (`GET /{short_code}`) never
waits on a database write. It queues a Celery task and returns the 302
immediately — click logging, geo lookup, and webhook dispatch all happen
after the user is already on their way to the target URL.


## Running it

```bash
cp .env.example .env
docker compose up --build
```

This starts:
- `api` — FastAPI on `:8000`
- `worker` — Celery worker processing click/webhook tasks
- `db` — Postgres on `:5432`
- `redis` — Redis on `:6379`

API docs: `http://localhost:8000/docs`

## Example flow

```bash
# Register
curl -X POST localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "yourpassword"}'

# Shorten a URL (use the access_token from register/login)
curl -X POST localhost:8000/api/urls \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"target_url": "https://example.com/some/long/path"}'

# Visit the short link — this redirects immediately and queues click logging
curl -L localhost:8000/<short_code>
```

## Tests

```bash
pip install -r requirements.txt
pytest
```

Covers short-code generation (format, uniqueness under load) and the rate
limiter (allows under limit, blocks over limit, window expiry behavior).


  count and adding a read replica for analytics queries would be the next
  levers to pull.

## Stack

FastAPI · SQLAlchemy · PostgreSQL · Celery · Redis · Docker Compose · pytest

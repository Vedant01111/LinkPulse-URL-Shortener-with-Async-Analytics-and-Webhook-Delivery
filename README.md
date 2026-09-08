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

## Design decisions worth reading before an interview

- **Short codes**: generated with `secrets` (CSPRNG, not `random`), base62,
  7 chars by default (~3.5 trillion combinations). Collisions are handled
  optimistically — insert and retry on a DB unique-constraint conflict,
  rather than pre-checking existence, which avoids a race condition under
  concurrent requests.
- **Rate limiting**: Redis sorted-set sliding window, not a fixed-window
  counter. A fixed window lets a client burst up to 2x the limit across a
  window boundary; the sliding window tracks actual timestamps to avoid that.
- **Webhook retries**: exponential backoff (2s → 4s → 8s → 16s → 32s, capped,
  with jitter) via Celery's `autoretry_for`. Retrying a failing endpoint at a
  constant interval hammers a service that's already struggling — backoff
  gives it room to recover.
- **Denormalized click_count on URL**: kept in sync inside the same task that
  writes the ClickEvent row, so reads never need a `COUNT(*)` over
  potentially millions of click rows.

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

## What's intentionally left as a "next step"

- Alembic migrations (currently using `Base.metadata.create_all` for local
  dev simplicity — noted in `app/main.py`)
- Real geo-IP lookup in `click_tasks.py` (stubbed, structured so a real
  provider drops in without touching calling code)
- Analytics rollup endpoint (hourly/daily aggregation from `click_events`)
- Horizontal scaling notes: with click writes decoupled via Celery, the
  bottleneck under heavy load becomes worker throughput — scaling worker
  count and adding a read replica for analytics queries would be the next
  levers to pull.

## Stack

FastAPI · SQLAlchemy · PostgreSQL · Celery · Redis · Docker Compose · pytest

#!/bin/sh
# Runs the Celery worker as a background process, then starts uvicorn in the
# foreground. This exists ONLY for free-tier hosting platforms (like Render's
# free plan) that don't offer a separate free background-worker service type.
#
# Locally, via docker-compose, the API and worker run as two SEPARATE
# containers instead (see docker-compose.yml) — that's the architecturally
# correct setup and what you should describe as the "real" design. This
# script is a pragmatic, documented compromise for a $0 hosted demo.

set -e

echo "Starting Celery worker in background..."
celery -A app.tasks.celery_app worker --loglevel=info &

echo "Starting FastAPI (uvicorn) in foreground..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"

from fastapi import FastAPI

from app.core.database import Base, engine
from app.routers import auth, urls, webhooks

# NOTE: create_all is fine for local dev / demoing this project. For a real
# production setup you'd use Alembic migrations instead (there's a stub for
# this in alembic/ — see README) so schema changes are versioned.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="LinkPulse",
    description="URL shortener with async click analytics and webhook delivery",
    version="0.1.0",
)

@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(webhooks.router)
# urls.router is included LAST because it has a catch-all GET /{short_code}
# route for redirects. Starlette matches routes in registration order, so
# anything registered after this would be shadowed by that catch-all.
app.include_router(urls.router)

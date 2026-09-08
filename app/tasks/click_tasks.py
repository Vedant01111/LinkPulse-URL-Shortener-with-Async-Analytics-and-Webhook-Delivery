from app.core.database import SessionLocal
from app.models.url import URL, ClickEvent
from app.tasks.celery_app import celery_app


@celery_app.task(name="tasks.record_click")
def record_click(url_id: str, ip_address: str, user_agent: str, referrer: str):
    """
    Runs in a Celery worker, completely off the request path.

    This is the key design decision in the whole project: the redirect
    endpoint returns a 302 to the user in milliseconds, WITHOUT waiting for
    this DB write. Click logging, geo lookup, and the webhook trigger all
    happen here, after the user has already been redirected.
    """
    db = SessionLocal()
    try:
        click = ClickEvent(
            url_id=url_id,
            ip_address=ip_address,
            user_agent=user_agent,
            referrer=referrer,
            country=_lookup_country(ip_address),
        )
        db.add(click)

        # Denormalized counter kept in sync here so reads never need a COUNT(*)
        url = db.query(URL).filter(URL.id == url_id).first()
        if url:
            url.click_count = (url.click_count or 0) + 1

        db.commit()

        # Fire-and-forget: queue webhook delivery for this URL's owner, if any
        from app.tasks.webhook_tasks import dispatch_webhooks_for_click
        dispatch_webhooks_for_click.delay(url_id, str(click.id))

    finally:
        db.close()


def _lookup_country(ip_address: str) -> str | None:
    """
    Placeholder for a real geo-IP lookup (e.g. via a MaxMind GeoLite2 DB or
    an API like ipapi.co). Kept as a stub so the task structure is in place;
    swapping in a real lookup later doesn't touch any other code.
    """
    return None

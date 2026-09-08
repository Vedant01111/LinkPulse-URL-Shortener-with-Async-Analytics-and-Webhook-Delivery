import json
from datetime import datetime

import httpx

from app.core.database import SessionLocal
from app.models.url import URL, ClickEvent
from app.models.webhook import Webhook, WebhookDelivery
from app.tasks.celery_app import celery_app


@celery_app.task(name="tasks.dispatch_webhooks_for_click")
def dispatch_webhooks_for_click(url_id: str, click_id: str):
    """
    Finds the URL owner's active webhooks and queues one delivery task per
    webhook. Split out from click recording so a slow/broken webhook target
    can never delay click logging itself.
    """
    db = SessionLocal()
    try:
        url = db.query(URL).filter(URL.id == url_id).first()
        click = db.query(ClickEvent).filter(ClickEvent.id == click_id).first()
        if not url or not click:
            return

        webhooks = (
            db.query(Webhook)
            .filter(Webhook.owner_id == url.owner_id, Webhook.is_active.is_(True))
            .all()
        )

        payload = {
            "event": "url.clicked",
            "short_code": url.short_code,
            "target_url": url.target_url,
            "clicked_at": click.clicked_at.isoformat(),
            "country": click.country,
        }

        for webhook in webhooks:
            delivery = WebhookDelivery(
                webhook_id=webhook.id,
                payload=json.dumps(payload),
                status="pending",
            )
            db.add(delivery)
            db.commit()
            db.refresh(delivery)

            deliver_webhook.delay(str(delivery.id))
    finally:
        db.close()


@celery_app.task(
    name="tasks.deliver_webhook",
    bind=True,
    max_retries=5,
    # Exponential backoff: 2s, 4s, 8s, 16s, 32s between attempts.
    # This is the concrete trade-off to describe in an interview: retrying
    # too aggressively hammers a target that's already struggling, so the
    # delay grows with each failure instead of staying constant.
    autoretry_for=(httpx.RequestError, httpx.HTTPStatusError),
    retry_backoff=2,
    retry_backoff_max=60,
    retry_jitter=True,
)
def deliver_webhook(self, delivery_id: str):
    db = SessionLocal()
    try:
        delivery = db.query(WebhookDelivery).filter(WebhookDelivery.id == delivery_id).first()
        if not delivery:
            return

        webhook = db.query(Webhook).filter(Webhook.id == delivery.webhook_id).first()
        delivery.attempt_count += 1

        try:
            response = httpx.post(
                webhook.target_url,
                content=delivery.payload,
                headers={"Content-Type": "application/json"},
                timeout=5.0,
            )
            response.raise_for_status()

            delivery.status = "success"
            delivery.delivered_at = datetime.utcnow()
            db.commit()

        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            delivery.last_error = str(exc)
            if self.request.retries >= self.max_retries:
                delivery.status = "failed"
            db.commit()
            raise  # lets Celery's autoretry_for handle the backoff + re-raise

    finally:
        db.close()

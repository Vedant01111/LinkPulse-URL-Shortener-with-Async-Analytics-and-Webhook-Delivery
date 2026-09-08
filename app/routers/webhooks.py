from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.webhook import Webhook
from app.schemas import WebhookCreate, WebhookResponse

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("", response_model=WebhookResponse, status_code=201)
def register_webhook(
    payload: WebhookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    webhook = Webhook(owner_id=current_user.id, target_url=str(payload.target_url))
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return webhook


@router.get("", response_model=list[WebhookResponse])
def list_webhooks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Webhook).filter(Webhook.owner_id == current_user.id).all()


@router.delete("/{webhook_id}", status_code=204)
def delete_webhook(
    webhook_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(Webhook).filter(
        Webhook.id == webhook_id, Webhook.owner_id == current_user.id
    ).delete()
    db.commit()

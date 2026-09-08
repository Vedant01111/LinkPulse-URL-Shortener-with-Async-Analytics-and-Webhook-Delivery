from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import check_rate_limit
from app.core.security import get_current_user
from app.core.shortcode import generate_short_code
from app.models.url import URL
from app.models.user import User
from app.schemas import URLCreate, URLResponse
from app.tasks.click_tasks import record_click

router = APIRouter(tags=["urls"])

MAX_SHORTCODE_RETRIES = 5


@router.post("/api/urls", response_model=URLResponse, status_code=201)
def shorten_url(
    payload: URLCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_rate_limit(request, identifier=str(current_user.id))

    # Retry loop handles the rare case of a short-code collision: instead of
    # pre-checking existence (which is a race condition under concurrent
    # requests), we optimistically insert and let the DB's unique constraint
    # be the source of truth, retrying with a fresh code on conflict.
    for _ in range(MAX_SHORTCODE_RETRIES):
        code = generate_short_code()
        url = URL(short_code=code, target_url=str(payload.target_url), owner_id=current_user.id)
        db.add(url)
        try:
            db.commit()
            db.refresh(url)
            break
        except IntegrityError:
            db.rollback()
    else:
        raise HTTPException(status_code=500, detail="Could not generate a unique short code")

    return URLResponse(
        id=url.id,
        short_code=url.short_code,
        short_url=f"{settings.base_url}/{url.short_code}",
        target_url=url.target_url,
        click_count=url.click_count,
        created_at=url.created_at,
    )


@router.get("/{short_code}")
def redirect_to_target(short_code: str, request: Request, db: Session = Depends(get_db)):
    url = db.query(URL).filter(URL.short_code == short_code).first()
    if not url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    # Fire the click-logging task and return the redirect immediately —
    # we do NOT await or block on the task. This is the sub-50ms latency
    # claim: the response goes out before any DB write for the click happens.
    record_click.delay(
        str(url.id),
        request.client.host,
        request.headers.get("user-agent", ""),
        request.headers.get("referer", ""),
    )

    return RedirectResponse(url=url.target_url, status_code=302)


@router.get("/api/urls/mine", response_model=list[URLResponse])
def list_my_urls(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    urls = db.query(URL).filter(URL.owner_id == current_user.id).all()
    return [
        URLResponse(
            id=u.id,
            short_code=u.short_code,
            short_url=f"{settings.base_url}/{u.short_code}",
            target_url=u.target_url,
            click_count=u.click_count,
            created_at=u.created_at,
        )
        for u in urls
    ]

import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class URL(Base):
    __tablename__ = "urls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    short_code = Column(String(16), unique=True, nullable=False, index=True)
    target_url = Column(Text, nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    click_count = Column(Integer, default=0)  # denormalized counter for fast reads
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="urls")
    clicks = relationship("ClickEvent", back_populates="url", cascade="all, delete-orphan")


class ClickEvent(Base):
    """
    Written asynchronously by a Celery worker AFTER the redirect has already
    happened, so click logging never adds latency to the redirect response.
    """
    __tablename__ = "click_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url_id = Column(UUID(as_uuid=True), ForeignKey("urls.id"), nullable=False, index=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    referrer = Column(Text, nullable=True)
    country = Column(String, nullable=True)  # populated by geo lookup task
    clicked_at = Column(DateTime, default=datetime.utcnow, index=True)

    url = relationship("URL", back_populates="clicks")

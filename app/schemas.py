import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, HttpUrl


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class URLCreate(BaseModel):
    target_url: HttpUrl


class URLResponse(BaseModel):
    id: uuid.UUID
    short_code: str
    short_url: str
    target_url: str
    click_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class WebhookCreate(BaseModel):
    target_url: HttpUrl


class WebhookResponse(BaseModel):
    id: uuid.UUID
    target_url: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

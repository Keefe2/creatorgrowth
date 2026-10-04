"""Pydantic v2 request/response schemas. All input is validated here."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

Platform = Literal["facebook", "x", "youtube", "instagram"]
ALLOWED_PLATFORMS = {"facebook", "x", "youtube", "instagram"}


# ---------- Auth ----------
class RegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=200)


class UserOut(BaseModel):
    id: int
    email: str
    name: str

    model_config = {"from_attributes": True}


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Social accounts ----------
class SocialAccountIn(BaseModel):
    platform: Platform
    account_name: str = Field(min_length=1, max_length=255)
    access_token: str = Field(min_length=1, max_length=4096)


class SocialAccountOut(BaseModel):
    id: int
    platform: str
    account_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Content ----------
class ContentIn(BaseModel):
    title: str = Field(default="", max_length=255)
    body: str = Field(min_length=1, max_length=10000)
    platforms: list[Platform] = Field(min_length=1, max_length=4)

    @field_validator("platforms")
    @classmethod
    def _unique_platforms(cls, v: list[str]) -> list[str]:
        if len(set(v)) != len(v):
            raise ValueError("Duplicate platforms")
        return v


class ContentScheduleIn(ContentIn):
    scheduled_at: datetime


class ContentOut(BaseModel):
    id: int
    title: str
    body: str
    platforms: list[str]
    status: str
    scheduled_at: datetime | None
    published_at: datetime | None
    ai_generated: bool
    error: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AIGenerateIn(BaseModel):
    topic: str = Field(min_length=3, max_length=200)
    tone: Literal["bold", "playful", "professional", "viral"] = "viral"
    platform: Platform = "facebook"
    language: Literal["ur", "en"] = "ur"


class AIGenerateOut(BaseModel):
    title: str
    body: str
    hashtags: list[str]


# ---------- Comments ----------
class CommentIn(BaseModel):
    platform: Platform
    post_ref: str = Field(min_length=1, max_length=255)
    comment_text: str = Field(min_length=1, max_length=1000)


class CommentOut(BaseModel):
    id: int
    platform: str
    post_ref: str
    comment_text: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Analytics ----------
class AnalyticsIn(BaseModel):
    platform: Platform
    followers: int = Field(ge=0, le=10**12)
    impressions: int = Field(ge=0, le=10**15)
    engagement: int = Field(ge=0, le=10**15)


class AnalyticsOut(BaseModel):
    platform: str
    followers: int
    impressions: int
    engagement: int
    recorded_at: datetime

    model_config = {"from_attributes": True}


class DashboardOut(BaseModel):
    totals: dict[str, int]
    by_platform: list[AnalyticsOut]
    scheduled_count: int
    published_count: int

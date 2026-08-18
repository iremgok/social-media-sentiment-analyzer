from pydantic import BaseModel, Field
from typing import Optional


class ScrapeRequest(BaseModel):
    query: str = Field(..., min_length=2, example="PlayStation 5")
    limit: int = Field(default=20, ge=1, le=100)


class RawComment(BaseModel):
    id: str
    text: str
    platform: str
    created_utc: Optional[str] = None
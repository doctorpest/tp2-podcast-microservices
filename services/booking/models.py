from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
from typing import Optional

class Booking(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    studio_id: int
    start: datetime
    end: datetime
    status: str = "PENDING"
    code: Optional[str] = None
    quota_reservation_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProcessedMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    message_id: str = Field(index=True, unique=True)
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
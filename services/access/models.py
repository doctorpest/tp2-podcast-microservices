from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class AccessCode(SQLModel, table=True):
    booking_id: int = Field(primary_key=True)
    code: str
    valid_from: datetime
    valid_to: datetime
    status: str = "ACTIVE"  # ACTIVE|REVOKED|EXPIRED

    
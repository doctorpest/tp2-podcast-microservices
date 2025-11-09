from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class QuotaReservation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    week_start: datetime        # lundi 00:00 UTC de la semaine
    minutes_reserved: int       # cumul tenu
    status: str = "HELD"        # HELD|COMMITTED|RELEASED|DENIED
    booking_id: int             # pour tracer l’origine
from sqlmodel import Session, select
from models import Booking   # ← absolu

class BookingRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, b: Booking):
        self.session.add(b)
        self.session.commit()
        self.session.refresh(b)
        return b

    def get(self, booking_id: int):
        return self.session.exec(select(Booking).where(Booking.id == booking_id)).first()

    def update_status(self, booking_id: int, status: str):
        b = self.get(booking_id)
        if b:
            b.status = status
            self.session.commit()
            self.session.refresh(b)
        return b
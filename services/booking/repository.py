# ============================================================
# repository.py — Accès aux données Booking
# ------------------------------------------------------------
# Ce module implémente le design pattern "Repository" pour la
# table Booking. Il isole la logique d’accès et de manipulation
# des données de la couche API.
# ============================================================
from sqlmodel import Session, select
from models import Booking   


# BookingRepository
# Fournit des méthodes CRUD simplifiées sur la table Booking. Utilisé à la fois par les routes FastAPI et le consumer RabbitMQ.
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
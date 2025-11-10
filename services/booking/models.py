# ============================================================
# models.py — Modèles de données SQLModel (Booking Service)
# ------------------------------------------------------------
# Définit les structures de tables de la base PostgreSQL :
#   1️. Booking : représente une réservation
#   2️. ProcessedMessage : trace les messages RabbitMQ déjà traités
# ============================================================
from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
from typing import Optional


# ------------------------------------------------------------
# Booking
# ------------------------------------------------------------
# Représente une réservation de studio :
#  - Contient les métadonnées utilisateur / studio
#  - Gère le cycle de vie : PENDING → READY → IN_USE → FINISHED
#  - Peut être annulée (CANCELLED) en cas d’échec Access/Quota
#  - Stocke aussi le code d’accès et l’ID de réservation quota
# ------------------------------------------------------------
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
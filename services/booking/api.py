# ============================================================
# Booking API Router
# ------------------------------------------------------------
# Expose les endpoints REST pour créer/consulter une réservation
# et réaliser le check-in / check-out. Orchestration avec Access
# et Quota (HTTP) + publication d’événements (RabbitMQ).
# ============================================================

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, create_engine
from models import Booking                
from repository import BookingRepository   
from publisher import publish_event        
import os, httpx

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
LOCAL_TZ = ZoneInfo(os.getenv("LOCAL_TZ", "America/Toronto"))

# URLs de la DB et des services distants
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/booking")
ACCESS_URL = os.getenv("ACCESS_URL", "http://access:8001")
QUOTA_URL  = os.getenv("QUOTA_URL",  "http://quota:8002")

# Moteur SQLAlchemy/SQLModel + routeur FastAPI
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
router = APIRouter()
# Dépendance FastAPI : fournit une Session DB par requête, auto-close
def get_session():
    with Session(engine) as s:
        yield s

# ------------------------------------------------------------
# POST /v1/bookings — Créer une réservation
# ------------------------------------------------------------
# - Valide l’ordre temporel start/end
# - Persiste la réservation, puis publie l’événement BookingCreated
# ------------------------------------------------------------
@router.post("/v1/bookings", response_model=Booking, status_code=201)
def create_booking(b: Booking, s: Session = Depends(get_session)):
    # 1) start/end doivent être avant/après
    if b.start >= b.end:
        raise HTTPException(400, "start must be before end")

    # 2) si pas de tz, on suppose la timezone locale
    if b.start.tzinfo is None:
        b.start = b.start.replace(tzinfo=LOCAL_TZ)
    if b.end.tzinfo is None:
        b.end = b.end.replace(tzinfo=LOCAL_TZ)

    # 3) normaliser en UTC pour stocker/échanger
    b.start = b.start.astimezone(timezone.utc)
    b.end   = b.end.astimezone(timezone.utc)
    
    # 4) persistance + publication de l'événement
    repo = BookingRepository(s)
    created = repo.create(b)
    publish_event("BookingCreated", {
        "bookingId": created.id,
        "userId": created.user_id,
        "studioId": created.studio_id,
        "start": created.start.isoformat(),  # inclut le +00:00
        "end": created.end.isoformat()
    })
    return created


# On convertit un datetime stocké (UTC) en affichage local

def to_local(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(LOCAL_TZ).isoformat()

# ------------------------------------------------------------
# GET /v1/bookings/{booking_id} — Récupérer une réservation
# ------------------------------------------------------------
# Retourne l’objet Booking avec des dates en timezone locale
# ------------------------------------------------------------
@router.get("/v1/bookings/{booking_id}")
def get_booking(booking_id: int, s: Session = Depends(get_session)):
    repo = BookingRepository(s)
    b = repo.get(booking_id)
    if not b:
        raise HTTPException(404, "not found")
    # réponse “human-friendly” en local
    return {
        "id": b.id,
        "user_id": b.user_id,
        "studio_id": b.studio_id,
        "status": b.status,
        "code": b.code,
        "quota_reservation_id": b.quota_reservation_id,
        "start": to_local(b.start),
        "end": to_local(b.end),
        "created_at": to_local(b.created_at),
    }

# ------------------------------------------------------------
# POST /v1/bookings/{id}/checkin — Entrée avec code d’accès
# ------------------------------------------------------------
# - Accepte le paramètre `code` validé côté Access
# - Exige le statut actuel READY
# - Passe la réservation à IN_USE et publie BookingCheckedIn
# ------------------------------------------------------------

@router.post("/v1/bookings/{booking_id}/checkin")
def checkin(booking_id: int, code: str, s: Session = Depends(get_session)):
    repo = BookingRepository(s)
    b = repo.get(booking_id)
    if not b:
        raise HTTPException(404, "not found")
    if b.status != "READY":
        raise HTTPException(409, "not READY")
    # Validation synchrone auprès du service Access
    r = httpx.post(f"{ACCESS_URL}/v1/access/validate", params={"bookingId": b.id, "code": code}, timeout=5)
    ok = r.json().get("valid", False)
    if not ok:
        raise HTTPException(401, "invalid code")
     # Mise à jour + événement
    repo.update_status(b.id, "IN_USE")
    publish_event("BookingCheckedIn", {"bookingId": b.id})
    return {"status": "IN_USE"}

# ------------------------------------------------------------
# POST /v1/bookings/{id}/checkout — Sortie et commit de quota
# ------------------------------------------------------------
# - Exige le statut actuel IN_USE
# - Tente un commit côté Quota 
# - Passe la réservation à FINISHED + événement BookingCheckedOut
# ------------------------------------------------------------
@router.post("/v1/bookings/{booking_id}/checkout")
def checkout(booking_id: int, s: Session = Depends(get_session)):
    repo = BookingRepository(s)
    b = repo.get(booking_id)
    if not b:
        raise HTTPException(404, "not found")
    if b.status != "IN_USE":
        raise HTTPException(409, "not IN_USE")
    # Commit quota si on a un reservation_id 
    if b.quota_reservation_id:
        try:
            httpx.post(f"{QUOTA_URL}/v1/quotas/commit", params={"reservationId": int(b.quota_reservation_id)}, timeout=5)
        except Exception:
            pass
    repo.update_status(b.id, "FINISHED")
    publish_event("BookingCheckedOut", {"bookingId": b.id})
    return {"status": "FINISHED"}
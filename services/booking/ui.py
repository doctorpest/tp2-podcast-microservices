# ============================================================
# ui.py — Interface web (FastAPI + Jinja2)
# ------------------------------------------------------------
# Ce module fournit une interface utilisateur minimale
# pour visualiser, créer et màj les réservations.
#
# Il réutilise directement la logique métier du Booking Service :
#  - création de réservation (create_booking)
#  - check-in (vérification du code d’accès)
#  - check-out (libération du studio)
# ============================================================

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from models import Booking
from repository import BookingRepository
from api import engine, create_booking, checkin, checkout  # on réutilise la logique existante
from datetime import datetime

from datetime import timezone
from zoneinfo import ZoneInfo
import os


LOCAL_TZ = ZoneInfo(os.getenv("LOCAL_TZ", "America/Toronto"))

templates = Jinja2Templates(directory="templates")

def to_local(dt):
    if dt is None:
        return ""
    # si naïf, on suppose UTC (stockage)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # format lisible sans le suffixe ISO
    return dt.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")


# 👉 enregistre le filtre pour les templates
# templates.env.filters["to_local"] = to_local
router = APIRouter()
templates = Jinja2Templates(directory="templates")


# Gestion de la session SQLModel

def get_session():
    with Session(engine) as s:
        yield s

# Page principale de la UI
@router.get("/ui", response_class=HTMLResponse)
def ui_home(request: Request, s: Session = Depends(get_session)):
    # liste des 20 dernières réservations
    rows = s.exec(select(Booking).order_by(Booking.id.desc()).limit(20)).all()
    return templates.TemplateResponse("index.html", {"request": request, "rows": rows, "to_local": to_local})


# Création d’une réservation via le formulaire HTML
# On récupère les champs du formulaire, crée un Booking et renvoie le tableau mis à jour.
@router.post("/ui/create", response_class=HTMLResponse)
def ui_create(
    request: Request,
    user_id: int = Form(...),
    studio_id: int = Form(...),
    start: str = Form(...),
    end: str = Form(...),
    s: Session = Depends(get_session)
):
    b = Booking(
        user_id=int(user_id),
        studio_id=int(studio_id),
        start=datetime.fromisoformat(start),
        end=datetime.fromisoformat(end),
    )
    created = create_booking(b, s)  # réutilise l’API interne
    rows = s.exec(select(Booking).order_by(Booking.id.desc()).limit(20)).all()
    return templates.TemplateResponse("table.html", {"request": request, "rows": rows, "to_local": to_local})


# Check-in d’une réservation
# On vérifie le code d’accès auprès du service Access via API interne.
# Si le code est valide on met le statut à IN_USE.
@router.post("/ui/checkin/{booking_id}", response_class=HTMLResponse)
def ui_checkin(booking_id: int, code: str = Form(...), s: Session = Depends(get_session)):
    checkin(booking_id, code, s)
    rows = s.exec(select(Booking).order_by(Booking.id.desc()).limit(20)).all()
    return templates.TemplateResponse("table.html", {"request": None, "rows": rows, "to_local": to_local})

# Check-out d’une réservation
# On informe le service Quota pour finaliser la consommation, puis màj le statut à FINISHED.

@router.post("/ui/checkout/{booking_id}", response_class=HTMLResponse)
def ui_checkout(booking_id: int, s: Session = Depends(get_session)):
    checkout(booking_id, s)
    rows = s.exec(select(Booking).order_by(Booking.id.desc()).limit(20)).all()
    return templates.TemplateResponse("table.html", {"request": None, "rows": rows, "to_local": to_local})
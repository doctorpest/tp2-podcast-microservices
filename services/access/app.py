# ============================================================
#  Access Service
# ------------------------------------------------------------
# Ce microservice est responsable de la gestion et validation
# des codes d’accès générés pour chaque réservation (booking).
# Il expose une API REST simple et écoute aussi des événements
# RabbitMQ en arrière-plan via un consommateur (consumer.py).
# ============================================================

from fastapi import FastAPI
from sqlmodel import SQLModel, create_engine, Session, select
from models import AccessCode
from datetime import datetime
import os, threading
from consumer import start_consumer

# ------------------------------------------------------------
# Configuration de la base de données PostgreSQL
# ------------------------------------------------------------
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@access_db:5432/access")
engine = create_engine(DB_URL, pool_pre_ping=True)


app = FastAPI(title="Access Service")


# Cette fonction est exécutée automatiquement au lancement du
# service. Elle :
#  1. Crée les tables du modèle SQL si elles n’existent pas encore.
#  2. Lance un thread en arrière-plan pour écouter les messages
#     RabbitMQ (fonction `start_consumer` du module consumer.py).

@app.on_event("startup")
def startup():
    SQLModel.metadata.create_all(engine)
    threading.Thread(target=start_consumer, daemon=True).start()


#  Endpoint de validation d’un code d’accès
@app.post("/v1/access/validate")
def validate(bookingId: int, code: str):
    now = datetime.utcnow()
    with Session(engine) as s:
        # Recherche du code d’accès correspondant à la réservation
        ac = s.exec(select(AccessCode).where(AccessCode.booking_id == bookingId)).first()

        # Si aucun code trouvé ou code incorrect → invalide
        if not ac or ac.code != code:
            return {"valid": False}

        # Vérifie si la date actuelle est dans la période de validité
        if not (ac.valid_from <= now <= ac.valid_to):
            return {"valid": False}

        # Si toutes les conditions sont remplies → code valide
        return {"valid": True}
# ============================================================
# app.py — Point d’entrée du service Booking
# ------------------------------------------------------------
# Ce module initialise l’application FastAPI du service Booking :
#   - Crée les tables dans la base de données PostgreSQL
#   - Démarre un thread consommateur RabbitMQ (start_consumer)
#   - Monte les routes API principales et l’interface web (UI)
# ============================================================
from fastapi import FastAPI
from sqlmodel import SQLModel
from api import router, engine
import threading
from consumer import start_consumer

import models

app = FastAPI(title="Booking Service")

# Exécuté automatiquement par FastAPI au lancement du conteneur.
# 1️. Crée les tables SQL.
# 2️. Lance un thread secondaire pour écouter RabbitMQ sans bloquer l’API.

@app.on_event("startup")
def start():
    # crée les tables (Booking + ProcessedMessage)
    SQLModel.metadata.create_all(engine)
    # lance le worker dans un thread
    threading.Thread(target=start_consumer, daemon=True).start()


#  Inclusion du module d’interface utilisateur (UI)

from ui import router as ui_router
app.include_router(ui_router)


# Inclusion des routes principales REST (API Booking)

app.include_router(router)
# ============================================================
# models.py — Définition du modèle de données AccessCode
# ------------------------------------------------------------
# Ce module définit la structure de la table "access_code" dans
# la base de données PostgreSQL, à l’aide de SQLModel.
# Chaque instance représente un code d’accès unique associé à
# une réservation (booking).
# ============================================================

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime



class AccessCode(SQLModel, table=True):
    booking_id: int = Field(primary_key=True)  # Identifie la réservation
    code: str                                   # Code d’accès à 6 chiffres
    valid_from: datetime                        # Début de validité
    valid_to: datetime                          # Fin de validité
    status: str = "ACTIVE"                      # État du code : ACTIVE | REVOKED | EXPIRED
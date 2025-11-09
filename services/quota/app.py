from fastapi import FastAPI
from sqlmodel import SQLModel, create_engine, Session, select
from models import QuotaReservation
from consumer import start_consumer
import os, threading

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@quota_db:5432/quota")
engine = create_engine(DB_URL, pool_pre_ping=True)

app = FastAPI(title="Quota Service")

@app.on_event("startup")
def startup():
    SQLModel.metadata.create_all(engine)
    threading.Thread(target=start_consumer, daemon=True).start()

@app.post("/v1/quotas/commit")
def commit(reservationId: int):
    with Session(engine) as s:
        qr = s.exec(select(QuotaReservation).where(QuotaReservation.id==reservationId)).first()
        if not qr: return {"ok": False}
        qr.status = "COMMITTED"; s.commit()
        return {"ok": True}

@app.post("/v1/quotas/release")
def release(reservationId: int):
    with Session(engine) as s:
        qr = s.exec(select(QuotaReservation).where(QuotaReservation.id==reservationId)).first()
        if not qr: return {"ok": False}
        qr.status = "RELEASED"; s.commit()
        return {"ok": True}
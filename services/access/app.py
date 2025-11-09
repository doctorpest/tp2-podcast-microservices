from fastapi import FastAPI
from sqlmodel import SQLModel, create_engine, Session, select
from models import AccessCode
from datetime import datetime
import os, threading
from consumer import start_consumer

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@access_db:5432/access")
engine = create_engine(DB_URL, pool_pre_ping=True)

app = FastAPI(title="Access Service")

@app.on_event("startup")
def startup():
    SQLModel.metadata.create_all(engine)
    threading.Thread(target=start_consumer, daemon=True).start()

@app.post("/v1/access/validate")
def validate(bookingId: int, code: str):
    now = datetime.utcnow()
    with Session(engine) as s:
        ac = s.exec(select(AccessCode).where(AccessCode.booking_id==bookingId)).first()
        if not ac or ac.code != code:
            return {"valid": False}
        if not (ac.valid_from <= now <= ac.valid_to):
            return {"valid": False}
        return {"valid": True}
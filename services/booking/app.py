from fastapi import FastAPI
from sqlmodel import SQLModel
from api import router, engine
import threading
from consumer import start_consumer

import models

app = FastAPI(title="Booking Service")

@app.on_event("startup")
def start():
    # crée les tables (Booking + ProcessedMessage)
    SQLModel.metadata.create_all(engine)
    # lance le worker dans un thread
    threading.Thread(target=start_consumer, daemon=True).start()

from ui import router as ui_router
app.include_router(ui_router)

app.include_router(router)
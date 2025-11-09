from fastapi import FastAPI
import threading
from consumer import start_consumer

app = FastAPI(title="Notification Service")

@app.on_event("startup")
def startup():
    threading.Thread(target=start_consumer, daemon=True).start()

@app.get("/health")
def health():
    return {"ok": True}

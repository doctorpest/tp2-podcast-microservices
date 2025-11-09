import json, os, pika, time, sys
from sqlmodel import Session, create_engine, select
from models import Booking, ProcessedMessage
from repository import BookingRepository
from publisher import publish_event

RABBIT = os.getenv("RABBITMQ_HOST", "rabbitmq")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@booking_db:5432/booking")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

def already_processed(s: Session, mid: str) -> bool:
    return s.exec(select(ProcessedMessage).where(ProcessedMessage.message_id == mid)).first() is not None

def mark_processed(s: Session, mid: str):
    s.add(ProcessedMessage(message_id=mid))
    s.commit()

def on_message(ch, method, properties, body):
    try:
        msg = json.loads(body)
    except Exception as e:
        print(f"[consumer] bad payload: {e}", flush=True)
        return

    etype = msg.get("type")
    payload = msg.get("payload", {})
    message_id = msg.get("messageId") or f"{etype}:{payload.get('bookingId','?')}"
    print(f"[consumer] received {etype} mid={message_id} payload={payload}", flush=True)

    booking_id = payload.get("bookingId")
    if not booking_id:
        print("[consumer] skipping (no bookingId)", flush=True)
        return

    with Session(engine) as s:
        if already_processed(s, message_id):
            print("[consumer] already processed, skipping", flush=True)
            return

        repo = BookingRepository(s)
        b = repo.get(booking_id)
        if not b:
            print("[consumer] booking not found", flush=True)
            mark_processed(s, message_id)
            return

        if etype == "AccessCodeIssued":
            b.code = payload["code"]; s.commit(); s.refresh(b)
        elif etype == "QuotaReserved":
            b.quota_reservation_id = payload.get("reservationId", "ok"); s.commit(); s.refresh(b)
        elif etype in ("AccessIssueFailed", "QuotaDenied"):
            repo.update_status(booking_id, "CANCELLED")
            publish_event("BookingCancelled", {"bookingId": booking_id, "reason": etype})
            mark_processed(s, message_id)
            return

        if b.status == "PENDING" and b.code and b.quota_reservation_id:
            repo.update_status(booking_id, "READY")
            publish_event("BookingReady", {"bookingId": booking_id})

        mark_processed(s, message_id)

def start_consumer():
    # petit retry loop pour attendre RabbitMQ
    attempt = 0
    while True:
        try:
            print(f"[consumer] connecting to rabbitmq at {RABBIT}...", flush=True)
            conn = pika.BlockingConnection(pika.ConnectionParameters(host=RABBIT, heartbeat=60))
            ch = conn.channel()
            ch.exchange_declare(exchange="events", exchange_type="fanout", durable=True)
            q = ch.queue_declare(queue="", exclusive=True).method.queue
            ch.queue_bind(exchange="events", queue=q)
            print(f"[consumer] bound to exchange 'events' queue='{q}'. waiting for messages...", flush=True)
            ch.basic_consume(queue=q, on_message_callback=on_message, auto_ack=True)
            ch.start_consuming()
        except Exception as e:
            attempt += 1
            wait = min(5 * attempt, 30)
            print(f"[consumer] connection error: {e} — retrying in {wait}s", flush=True)
            time.sleep(wait)
import os, json, pika, time
from datetime import datetime, timedelta
from sqlmodel import SQLModel, create_engine, Session, select
from models import QuotaReservation

RABBIT = os.getenv("RABBITMQ_HOST", "rabbitmq")
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@quota_db:5432/quota")
MAX_MIN = int(os.getenv("QUOTA_MAX_MIN_PER_WEEK", "180"))  # 3h par défaut
engine = create_engine(DB_URL, pool_pre_ping=True)

def week_start(dt: datetime) -> datetime:
    # lundi 00:00 UTC
    monday = dt - timedelta(days=dt.weekday())
    return datetime(monday.year, monday.month, monday.day)

def publish(event_type: str, payload: dict):
    conn = pika.BlockingConnection(pika.ConnectionParameters(RABBIT, heartbeat=60))
    ch = conn.channel()
    ch.exchange_declare(exchange="events", exchange_type="fanout", durable=True)
    ch.basic_publish(exchange="events", routing_key="", body=json.dumps({"type": event_type, "payload": payload}))
    conn.close()

def on_message(ch, method, properties, body):
    try:
        msg = json.loads(body)
    except Exception:
        return
    if msg.get("type") != "BookingCreated":
        return

    p = msg["payload"]
    user_id = int(p["userId"])
    booking_id = int(p["bookingId"])
    start = datetime.fromisoformat(p["start"])
    end = datetime.fromisoformat(p["end"])
    duration_min = int((end - start).total_seconds() // 60)
    wk = week_start(start)

    with Session(engine) as s:
        # cumul des minutes HELD/COMMITTED sur cette semaine
        total = 0
        rows = s.exec(select(QuotaReservation).where(
            QuotaReservation.user_id == user_id,
            QuotaReservation.week_start == wk,
            QuotaReservation.status.in_(["HELD","COMMITTED"])
        )).all()
        for r in rows:
            total += r.minutes_reserved

        if total + duration_min > MAX_MIN:
            # deny
            qr = QuotaReservation(user_id=user_id, week_start=wk, minutes_reserved=0,
                                  status="DENIED", booking_id=booking_id)
            s.add(qr); s.commit()
            publish("QuotaDenied", {"bookingId": booking_id, "reason": "weekly-limit"})
        else:
            # hold
            qr = QuotaReservation(user_id=user_id, week_start=wk, minutes_reserved=duration_min,
                                  status="HELD", booking_id=booking_id)
            s.add(qr); s.commit()
            publish("QuotaReserved", {"bookingId": booking_id, "reservationId": str(qr.id)})

def start_consumer():
    SQLModel.metadata.create_all(engine)
    while True:
        try:
            print(f"[quota-consumer] connecting to rabbitmq {RABBIT}...", flush=True)
            conn = pika.BlockingConnection(pika.ConnectionParameters(RABBIT, heartbeat=60))
            ch = conn.channel()
            ch.exchange_declare(exchange="events", exchange_type="fanout", durable=True)
            q = ch.queue_declare(queue="", exclusive=True).method.queue
            ch.queue_bind(exchange="events", queue=q)
            print("[quota-consumer] bound to 'events'. waiting...", flush=True)
            ch.basic_consume(queue=q, on_message_callback=on_message, auto_ack=True)
            ch.start_consuming()
        except Exception as e:
            print(f"[quota-consumer] error: {e} — retrying in 5s", flush=True)
            time.sleep(5)
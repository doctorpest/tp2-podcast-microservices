import os, json, random, string, pika, time
from datetime import datetime, timedelta
from sqlmodel import SQLModel, create_engine, Session
from models import AccessCode

RABBIT = os.getenv("RABBITMQ_HOST", "rabbitmq")
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@access_db:5432/access")
engine = create_engine(DB_URL, pool_pre_ping=True)

def publish(event_type: str, payload: dict):
    conn = pika.BlockingConnection(pika.ConnectionParameters(RABBIT, heartbeat=60))
    ch = conn.channel()
    ch.exchange_declare(exchange="events", exchange_type="fanout", durable=True)
    ch.basic_publish(exchange="events", routing_key="", body=json.dumps({"type": event_type, "payload": payload}))
    conn.close()

def gen_code(n=6):  # 6 chiffres
    return "".join(random.choice(string.digits) for _ in range(n))

def on_message(ch, method, properties, body):
    try:
        msg = json.loads(body)
    except Exception:
        return
    if msg.get("type") != "BookingCreated":
        return

    p = msg["payload"]
    bid = int(p["bookingId"])
    start = datetime.fromisoformat(p["start"])
    end = datetime.fromisoformat(p["end"])

    # Simule 90% succès
    if random.random() < 0.9:
        code = gen_code()
        with Session(engine) as s:
            s.add(AccessCode(booking_id=bid, code=code, valid_from=start, valid_to=end))
            s.commit()
        publish("AccessCodeIssued", {"bookingId": bid, "code": code})
    else:
        publish("AccessIssueFailed", {"bookingId": bid, "reason": "hardware-unavailable"})

def start_consumer():
    # init tables
    SQLModel.metadata.create_all(engine)

    while True:
        try:
            print("[access-consumer] connecting to rabbitmq...", flush=True)
            conn = pika.BlockingConnection(pika.ConnectionParameters(RABBIT, heartbeat=60))
            ch = conn.channel()
            ch.exchange_declare(exchange="events", exchange_type="fanout", durable=True)
            q = ch.queue_declare(queue="", exclusive=True).method.queue
            ch.queue_bind(exchange="events", queue=q)
            print("[access-consumer] bound to 'events'. waiting messages...", flush=True)
            ch.basic_consume(queue=q, on_message_callback=on_message, auto_ack=True)
            ch.start_consuming()
        except Exception as e:
            print(f"[access-consumer] error: {e} — retrying...", flush=True)
            time.sleep(5)
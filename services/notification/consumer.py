import os, json, pika, time
RABBIT = os.getenv("RABBITMQ_HOST", "rabbitmq")

def on_message(ch, method, properties, body):
    try:
        msg = json.loads(body)
    except Exception:
        return
    t = msg.get("type")
    p = msg.get("payload", {})
    if t in ("BookingReady", "BookingCancelled", "BookingCheckedIn", "BookingCheckedOut"):
        print(f"[notification] {t} -> mock email: {p}", flush=True)

def start_consumer():
    while True:
        try:
            print("[notification] connecting to rabbitmq...", flush=True)
            conn = pika.BlockingConnection(pika.ConnectionParameters(RABBIT, heartbeat=60))
            ch = conn.channel()
            ch.exchange_declare(exchange="events", exchange_type="fanout", durable=True)
            q = ch.queue_declare(queue="", exclusive=True).method.queue
            ch.queue_bind(exchange="events", queue=q)
            print("[notification] bound to 'events'. waiting...", flush=True)
            ch.basic_consume(queue=q, on_message_callback=on_message, auto_ack=True)
            ch.start_consuming()
        except Exception as e:
            print(f"[notification] error: {e} — retry 5s", flush=True)
            time.sleep(5)

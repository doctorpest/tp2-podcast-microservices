import os, json, pika

RABBIT_HOST = os.getenv("RABBITMQ_HOST", "localhost")

def publish_event(event_type: str, payload: dict):
    conn = pika.BlockingConnection(pika.ConnectionParameters(host=RABBIT_HOST))
    ch = conn.channel()
    ch.exchange_declare(exchange="events", exchange_type="fanout", durable=True)
    message = {"type": event_type, "payload": payload}
    ch.basic_publish(exchange="events", routing_key="", body=json.dumps(message))
    print(f"[event] {event_type} {payload}")
    conn.close()
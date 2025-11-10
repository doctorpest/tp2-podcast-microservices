# ============================================================
# publisher.py — Émission d'événements RabbitMQ
# ------------------------------------------------------------
# Ce module gère la publication des événements inter-services.
# Chaque service (Booking, Access, Quota, Notification.) l’utilise pour
# informer les autres d’un changement d’état (BookingCreated,
# AccessCodeIssued, QuotaReserved, BookingReady)
# ============================================================
import os, json, pika

RABBIT_HOST = os.getenv("RABBITMQ_HOST", "localhost")

# Cette méthode publie un message sur l’échange "events" en mode fanout :
#
#   - event_type : nom de l’événement 
#   - payload    : contenu du message
#
# Tous les consommateurs liés à l’échange reçoivent le message.

def publish_event(event_type: str, payload: dict):
    # Ouvre une connexion vers RabbitMQ
    conn = pika.BlockingConnection(pika.ConnectionParameters(host=RABBIT_HOST))
    ch = conn.channel()
    # Déclare ou crée l’échange fanout s’il n’existe pas déjà
    # durable=True pour survivre aux redémarrages RabbitMQ
    ch.exchange_declare(exchange="events", exchange_type="fanout", durable=True)
    message = {"type": event_type, "payload": payload}
    # Publie le message JSON (broadcast via fanout)
    ch.basic_publish(exchange="events", routing_key="", body=json.dumps(message))
    print(f"[event] {event_type} {payload}")
    conn.close()
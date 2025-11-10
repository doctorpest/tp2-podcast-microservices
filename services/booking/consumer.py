# ============================================================
# Booking Service — RabbitMQ Consumer
# ------------------------------------------------------------
# Écoute les événements publiés sur l'échange "events".
# Màj les réservations en fonction des messages reçus :
#   - AccessCodeIssued permet d'enregistrer le code d’accès
#   - QuotaReserved permet d'enregistrer l’ID de réservation de quota
#   - AccessIssueFailed annule la réservation 
#   - QuotaDenied annule la réservation
# Quand code + quota sont présents et statut passe de PENDING à READY
# On publie alors l’événement "BookingReady".
# ============================================================

import json, os, pika, time, sys
from sqlmodel import Session, create_engine, select
from models import Booking, ProcessedMessage
from repository import BookingRepository
from publisher import publish_event

RABBIT = os.getenv("RABBITMQ_HOST", "rabbitmq")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@booking_db:5432/booking")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# ------------------------------------------------------------
# Ici on évite de traiter deux fois le même message
# ------------------------------------------------------------
# On garde en base (table ProcessedMessage) l’ID des messages
# déjà traités. Dans le cas où le broker redélivre un message ou si
# plusieurs consommateurs existent.
# ------------------------------------------------------------
def already_processed(s: Session, mid: str) -> bool:
    return s.exec(select(ProcessedMessage).where(ProcessedMessage.message_id == mid)).first() is not None

def mark_processed(s: Session, mid: str):
    s.add(ProcessedMessage(message_id=mid))
    s.commit()


# Callback exécuté à chaque message reçu depuis RabbitMQ

def on_message(ch, method, properties, body):
    try:
        msg = json.loads(body)
    except Exception as e:
        print(f"[consumer] bad payload: {e}", flush=True)
        return

    etype = msg.get("type")
    payload = msg.get("payload", {})

    # Génère un ID de message si un messageId est fourni on l’utilise
    # sinon on construit "Type:bookingId" 
    message_id = msg.get("messageId") or f"{etype}:{payload.get('bookingId','?')}"
    print(f"[consumer] received {etype} mid={message_id} payload={payload}", flush=True)

    booking_id = payload.get("bookingId")
    if not booking_id:
        print("[consumer] skipping (no bookingId)", flush=True)
        return

    with Session(engine) as s:
        # si déjà traité on ignore
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
            # On stocke le code d'accès sur la réservation
            b.code = payload["code"] 
            s.commit() 
            s.refresh(b)
        elif etype == "QuotaReserved":
            # On renseigne l'identifiant de réservation de quota
            b.quota_reservation_id = payload.get("reservationId", "ok"); s.commit(); s.refresh(b)
        elif etype in ("AccessIssueFailed", "QuotaDenied"):
            # Si un des services a échoué : on annule la réservation
            repo.update_status(booking_id, "CANCELLED")
            publish_event("BookingCancelled", {"bookingId": booking_id, "reason": etype})
            mark_processed(s, message_id)
            return
        
        # Si la réservation était en attente et que l'on a bien
        # reçu le code d’accès + la réservation de quota on passe à READY

        if b.status == "PENDING" and b.code and b.quota_reservation_id:
            repo.update_status(booking_id, "READY")
            publish_event("BookingReady", {"bookingId": booking_id})

        mark_processed(s, message_id)

#  Boucle de connexion + consommation RabbitMQ 

def start_consumer():
    # petit retry loop pour attendre RabbitMQ
    attempt = 0
    while True:
        try:
            print(f"[consumer] connecting to rabbitmq at {RABBIT}...", flush=True)
            conn = pika.BlockingConnection(pika.ConnectionParameters(host=RABBIT, heartbeat=60))
            ch = conn.channel()
            # Déclare l'échange 'events' de type fanout (broadcast)
            ch.exchange_declare(exchange="events", exchange_type="fanout", durable=True)
            # Déclare une queue anonyme, exclusive à ce consumer
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
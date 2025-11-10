# ============================================================
# Access Service - RabbitMQ Consumer
# ------------------------------------------------------------
# Ce module écoute les messages RabbitMQ, en particulier les
# événements "BookingCreated", pour générer un code d’accès
# unique et le stocker dans la base de données.
#
# Si l’opération réussit → publie un événement "AccessCodeIssued"
# Sinon → publie un événement "AccessIssueFailed"
# ============================================================

import os, json, random, string, pika, time
from datetime import datetime, timedelta
from sqlmodel import SQLModel, create_engine, Session
from models import AccessCode


# Configuration de RabbitMQ et de la base PostgreSQL

RABBIT = os.getenv("RABBITMQ_HOST", "rabbitmq")
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@access_db:5432/access")
engine = create_engine(DB_URL, pool_pre_ping=True)


# Cette fonction ouvre une connexion, déclare l’échange "events" puis publie un message contenant :
#   - type : le nom de l’événement
#   - payload : les données associées
# ------------------------------------------------------------
def publish(event_type: str, payload: dict):
    conn = pika.BlockingConnection(pika.ConnectionParameters(RABBIT, heartbeat=60))
    ch = conn.channel()
    ch.exchange_declare(exchange="events", exchange_type="fanout", durable=True)
    ch.basic_publish(exchange="events", routing_key="", body=json.dumps({"type": event_type, "payload": payload}))
    conn.close()


# Génération aléatoire d’un code à 6 chiffres
def gen_code(n=6):  
    return "".join(random.choice(string.digits) for _ in range(n))


# Cette fonction est appelée à chaque fois qu’un message arrive dans la file d’attente liée à l’échange "events"
# 1️. On parse le message JSON
# 2️. On vérifie que le type est "BookingCreated"
# 3️. Si oui, on crée un code d’accès associé à la réservation
# 4️. On simule une probabilité d’échec (10%)
# 5️. En cas de succès, on sauvegarde et publie "AccessCodeIssued"
# 6️. Sinon, on publie "AccessIssueFailed"

def on_message(ch, method, properties, body):
    try:
        msg = json.loads(body)
    except Exception:
        return    # ignore les messages mal formés
    # On ne traite que les événements BookingCreated
    if msg.get("type") != "BookingCreated":
        return
    
    # Extraction des données de la réservation
    p = msg["payload"]
    bid = int(p["bookingId"])
    start = datetime.fromisoformat(p["start"])
    end = datetime.fromisoformat(p["end"])

    # Simulation : 90 % de succès, 10 % d’échec aléatoire
    if random.random() < 0.9:
        code = gen_code()
        # Enregistrement du code d’accès dans la base
        with Session(engine) as s:
            s.add(AccessCode(booking_id=bid, code=code, valid_from=start, valid_to=end))
            s.commit()
            # Publication de l’événement "AccessCodeIssued"
        publish("AccessCodeIssued", {"bookingId": bid, "code": code})
    else:
        # Si échec → envoie un message d’erreur
        publish("AccessIssueFailed", {"bookingId": bid, "reason": "hardware-unavailable"})


# Cette fonction :
#  - crée les tables si nécessaire
#  - établit une connexion persistante à RabbitMQ
#  - s’abonne à l’échange "events" en mode fanout
#  - lance la boucle d’écoute infinie pour consommer les messages
# En cas d’erreur de connexion, elle attend 5 secondes avant
# de réessayer automatiquement.

def start_consumer():
    # S’assure que la base contient les tables nécessaires
    SQLModel.metadata.create_all(engine)

    while True:
        try:
            print("[access-consumer] connecting to rabbitmq...", flush=True)
            conn = pika.BlockingConnection(pika.ConnectionParameters(RABBIT, heartbeat=60))
            ch = conn.channel()
            # Déclaration de l’échange "events" (fanout = broadcast)
            ch.exchange_declare(exchange="events", exchange_type="fanout", durable=True)
            # Création d’une file temporaire et exclusive à ce service
            q = ch.queue_declare(queue="", exclusive=True).method.queue
            ch.queue_bind(exchange="events", queue=q)
            print("[access-consumer] bound to 'events'. waiting messages...", flush=True)
            # Abonnement à la file : appel de on_message() à chaque message reçu
            ch.basic_consume(queue=q, on_message_callback=on_message, auto_ack=True)
            ch.start_consuming() # Boucle infinie d’écoute
        except Exception as e:
            print(f"[access-consumer] error: {e} — retrying...", flush=True)
            time.sleep(5)
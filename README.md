# 🎧 TP2 — Microservices : Podcast Booking System

Ce projet illustre une architecture **microservices événementielle** construite autour d’un système de réservation de studio d’enregistrement de podcast.  
Chaque service est indépendant et communique via **RabbitMQ** à travers des **événements asynchrones**.

---

## 🧩 Architecture générale

### 🗺️ Diagramme global
![Architecture Diagram](A_flowchart_diagram_in_this_digital_vector_illustr.png)

### 🧠 Description des composants

| Service | Rôle |
|----------|------|
| **User API / UI** | Interface (via navigateur ou cURL) permettant de créer et gérer les réservations. |
| **Booking Service** | Service central qui orchestre la création, la validation et le suivi des réservations. |
| **Access Service** | Génère et valide les codes d’accès aux studios. |
| **Quota Service** | Réserve les créneaux horaires disponibles pour les studios. |
| **Notification Service** | Envoie les confirmations et notifications. |
| **RabbitMQ** | Message broker gérant les communications asynchrones entre microservices. |

---

## ⚙️ Technologies utilisées

- **Python 3.11**
- **FastAPI** (pour les APIs REST)
- **SQLModel / SQLite** (pour la persistance des données)
- **RabbitMQ** (communication interservices)
- **HTMX + Jinja2** (pour l’interface web)
- **Docker Compose** (orchestration des services)

---

## 🚀 Étape 1 : Cloner le projet

```bash
git clone https://github.com/<ton-user>/tp2-podcast-microservices.git
cd tp2-podcast-microservices

FROM python:3.11-slim

# 1) Déps système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2) Déps Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3) Code
COPY . .

EXPOSE 8000

# 4) Démarrage API
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
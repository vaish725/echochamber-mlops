FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ ./scripts/

ENV KAFKA_BOOTSTRAP_SERVERS=kafka:29092

CMD ["python", "scripts/producer.py"]

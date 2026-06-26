# EchoChamber MLOps

A real-time misinformation detection platform that ingests social media posts via Kafka, classifies them using an LLM (Anthropic Claude), and surfaces results to downstream consumers and dashboards. Deployed on Kubernetes with full MLOps practices.

## Architecture

```
[Data Producer]
     │  (synthetic social media posts)
     ▼
[Kafka: social-media-stream]
     │
     ▼
[LLM Detection Service]  ◄──── [MLflow Model Registry]
     │  (label + confidence + reasoning)
     ▼
[Kafka: detection-results]
     │
     ├──► [Storage Sink: PostgreSQL + S3/MinIO]
     └──► [Prometheus + Grafana]

[All services on Kubernetes · CI/CD via GitHub Actions]
```

## Components

| Folder | Description | Status |
|--------|-------------|--------|
| `kafka-ingestion/` | Kafka producer + consumer + docker-compose | ✅ Complete |
| `detection-service/` | FastAPI LLM classifier (Claude) | 🔲 Next |
| `storage-sink/` | PostgreSQL + S3/MinIO writer | 🔲 Planned |
| `mlflow/` | Experiment tracking + model registry | 🔲 Planned |
| `k8s/` | Kubernetes manifests | 🔲 Planned |
| `dashboards/` | Grafana dashboard JSON | 🔲 Planned |

## Quickstart — Kafka Ingestion

**Prerequisites:** Docker, Docker Compose, Python 3.10+

```bash
# 1. Start Kafka + Zookeeper
cd kafka-ingestion
docker compose up -d

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the producer (sends a post every 2 seconds)
python scripts/producer.py

# 4. In a separate terminal, run the consumer
python scripts/consumer.py
```

**Kafka listeners:**
- `localhost:9092` — host machine access (for running scripts locally)
- `kafka:29092` — inter-container access (for Docker services)

## Running Tests

```bash
# Start Kafka first (see above), then:
pip install pytest
pytest kafka-ingestion/tests/ -v
```

## Environment Variables

See `.env.example` for all required variables and their defaults.

## Project Status

See `prd.md` (gitignored) for the full Product Requirements Document and roadmap.

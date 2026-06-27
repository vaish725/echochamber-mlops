import pytest

from app.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        kafka_bootstrap_servers="localhost:9092",
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="echochamber",
        postgres_user="echochamber",
        postgres_password="changeme",
        s3_endpoint_url="http://localhost:9000",
        s3_bucket="echochamber-raw",
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin",
        parquet_flush_interval_seconds=30,
    )


RAW_POST = {
    "user_id": "11111111-1111-1111-1111-111111111111",
    "username": "alice",
    "post_text": "The earth is round.",
    "created_at": "2026-01-01T00:00:00+00:00",
    "location": "NYC, USA",
}

RAW_DETECTION = {
    "post_id": "11111111-1111-1111-1111-111111111111",
    "post_text": "The earth is round.",
    "label": "CREDIBLE",
    "confidence": 0.95,
    "reasoning": "Factual scientific claim.",
    "model_version": "claude-sonnet-4-6",
    "prompt_version": "v1",
    "detected_at": "2026-01-01T00:00:01+00:00",
}

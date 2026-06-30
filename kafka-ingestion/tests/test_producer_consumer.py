"""
Smoke test: verifies producer → Kafka → consumer roundtrip.
Requires a running Kafka broker at localhost:9092 (docker-compose up).
Run with: pytest kafka-ingestion/tests/ -v
"""
import json
import time
import uuid

import pytest
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable

BOOTSTRAP_SERVERS = ["localhost:9092"]
TOPIC = "smoke-test-" + uuid.uuid4().hex[:8]


@pytest.fixture(scope="module")
def producer():
    try:
        p = KafkaProducer(
            bootstrap_servers=BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
    except NoBrokersAvailable:
        pytest.skip("Kafka not reachable at localhost:9092 — start docker-compose first")
    yield p
    p.close()


@pytest.fixture(scope="module")
def consumer():
    try:
        c = KafkaConsumer(
            TOPIC,
            bootstrap_servers=BOOTSTRAP_SERVERS,
            auto_offset_reset="earliest",
            consumer_timeout_ms=10_000,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            group_id="smoke-test-group",
        )
    except NoBrokersAvailable:
        pytest.skip("Kafka not reachable at localhost:9092 — start docker-compose first")
    yield c
    c.close()


def test_producer_consumer_roundtrip(producer, consumer):
    payload = {
        "user_id": str(uuid.uuid4()),
        "username": "smoke_tester",
        "post_text": "This is a smoke test message.",
        "created_at": "2026-01-01T00:00:00Z",
        "location": "Test City, Test Country",
    }

    future = producer.send(TOPIC, payload)
    record_metadata = future.get(timeout=10)
    assert record_metadata.topic == TOPIC

    producer.flush()
    time.sleep(1)

    received = []
    for message in consumer:
        received.append(message.value)
        break

    assert len(received) == 1
    assert received[0]["user_id"] == payload["user_id"]
    assert received[0]["post_text"] == payload["post_text"]


def test_post_schema_fields(producer, consumer):
    """All required post fields must be present and non-empty."""
    required_fields = {"user_id", "username", "post_text", "created_at", "location"}
    payload = {
        "user_id": str(uuid.uuid4()),
        "username": "field_checker",
        "post_text": "Checking required fields.",
        "created_at": "2026-01-01T00:00:01Z",
        "location": "Field City, Check Country",
    }

    producer.send(TOPIC, payload).get(timeout=10)
    producer.flush()
    time.sleep(1)

    for message in consumer:
        assert required_fields.issubset(message.value.keys())
        for field in required_fields:
            assert message.value[field], f"Field '{field}' is empty"
        break

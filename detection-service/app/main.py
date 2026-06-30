import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastapi import FastAPI, Response
from prometheus_client import make_asgi_app

from app.config import get_settings
from app.consumer import KafkaDetectionConsumer
from app.detector import MisinformationDetector
from app.experiment_tracker import ExperimentTracker
from app.logging_config import configure_logging
from app.publisher import DetectionPublisher

logger = logging.getLogger(__name__)

_kafka_consumer: Optional[KafkaDetectionConsumer] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global _kafka_consumer
    configure_logging()
    settings = get_settings()
    detector = MisinformationDetector(settings)
    publisher = DetectionPublisher(settings)
    tracker = ExperimentTracker(settings)
    await publisher.start()
    _kafka_consumer = KafkaDetectionConsumer(settings, detector, publisher, tracker)
    await _kafka_consumer.start()
    logger.info("Detection service ready")
    try:
        yield
    finally:
        await _kafka_consumer.stop()
        await publisher.stop()
        logger.info("Detection service shut down")


app = FastAPI(title="EchoChamber Detection Service", version="1.0.0", lifespan=lifespan)

app.mount("/metrics", make_asgi_app())


@app.get("/health")
async def health() -> Response:
    """FR-2.3: 200 when Kafka consumer is running, 503 otherwise."""
    if _kafka_consumer is not None and _kafka_consumer.is_healthy:
        return Response(
            content='{"status":"ok"}',
            status_code=200,
            media_type="application/json",
        )
    return Response(
        content='{"status":"unavailable"}',
        status_code=503,
        media_type="application/json",
    )

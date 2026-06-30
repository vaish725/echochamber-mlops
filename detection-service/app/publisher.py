import json
import logging

from aiokafka import AIOKafkaProducer

from app.config import Settings
from app.schemas import Detection

logger = logging.getLogger(__name__)


class DetectionPublisher:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await self._producer.start()
        logger.info(
            "Detection publisher started",
            extra={"topic": self._settings.kafka_output_topic},
        )

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()

    async def publish(self, detection: Detection) -> None:
        assert self._producer is not None, "Publisher not started"
        await self._producer.send_and_wait(
            self._settings.kafka_output_topic,
            value=detection.model_dump(),
        )

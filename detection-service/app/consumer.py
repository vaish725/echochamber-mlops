import asyncio
import json
import logging
from typing import Optional

from aiokafka import AIOKafkaConsumer

from app.config import Settings
from app.detector import MisinformationDetector
from app.experiment_tracker import ExperimentTracker
from app.metrics import detections_by_label_total, errors_total, posts_processed_total
from app.publisher import DetectionPublisher
from app.schemas import Post

logger = logging.getLogger(__name__)

# Strong references to fire-and-forget tasks so GC doesn't collect them mid-flight
_background_tasks: set[asyncio.Task[None]] = set()


class KafkaDetectionConsumer:
    def __init__(
        self,
        settings: Settings,
        detector: MisinformationDetector,
        publisher: DetectionPublisher,
        tracker: ExperimentTracker,
    ) -> None:
        self._settings = settings
        self._detector = detector
        self._publisher = publisher
        self._tracker = tracker
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._loop_task: Optional[asyncio.Task[None]] = None

    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            self._settings.kafka_input_topic,
            bootstrap_servers=self._settings.kafka_bootstrap_servers,
            group_id=self._settings.kafka_consumer_group,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            value_deserializer=lambda b: json.loads(b.decode("utf-8")),
        )
        await self._consumer.start()
        self._loop_task = asyncio.create_task(self._consume_loop(), name="kafka-consume-loop")
        logger.info("Kafka consumer started", extra={"topic": self._settings.kafka_input_topic})

    async def stop(self) -> None:
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        if self._consumer:
            await self._consumer.stop()
        logger.info("Kafka consumer stopped")

    @property
    def is_healthy(self) -> bool:
        return self._loop_task is not None and not self._loop_task.done()

    async def _consume_loop(self) -> None:
        assert self._consumer is not None
        async for message in self._consumer:
            task = asyncio.create_task(
                self._handle_message(message.value),
                name=f"handle-offset-{message.offset}",
            )
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)

    async def _handle_message(self, raw: dict) -> None:  # type: ignore[type-arg]
        try:
            post = Post(**raw)
            detection = await self._detector.classify(post)
            await self._publisher.publish(detection)
            posts_processed_total.inc()
            detections_by_label_total.labels(label=detection.label.value).inc()
            self._tracker.record(detection)
            if self._tracker.should_flush():
                self._tracker.flush()
            logger.info(
                "Post classified",
                extra={
                    "post_id": detection.post_id,
                    "label": detection.label.value,
                    "confidence": detection.confidence,
                },
            )
        except Exception:
            errors_total.labels(error_type="processing_error").inc()
            logger.exception("Failed to process message", extra={"raw_preview": str(raw)[:200]})

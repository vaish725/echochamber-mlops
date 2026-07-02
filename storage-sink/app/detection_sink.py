import asyncio
import json
import logging
import uuid

from aiokafka import AIOKafkaConsumer
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.config import Settings
from app.logging_config import set_trace_id
from app.models import Detection, Post
from app.parquet_archiver import ParquetArchiver
from app.schemas import DetectionMessage

logger = logging.getLogger(__name__)

_MAX_RETRIES = 10
_RETRY_BASE_SECONDS = 2


class DetectionSink:
    def __init__(self, settings: Settings, engine: AsyncEngine, archiver: ParquetArchiver) -> None:
        self._settings = settings
        self._session_factory = async_sessionmaker(engine, expire_on_commit=False)
        self._archiver = archiver
        self._retry_queue: asyncio.Queue[tuple[dict, int]] = asyncio.Queue()  # type: ignore[type-arg]

    async def run(self) -> None:
        consumer = AIOKafkaConsumer(
            self._settings.kafka_detections_topic,
            bootstrap_servers=self._settings.kafka_bootstrap_servers,
            group_id=self._settings.kafka_detections_consumer_group,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            value_deserializer=lambda b: json.loads(b.decode("utf-8")),
        )
        await consumer.start()
        logger.info(
            "Detection sink consumer started",
            extra={"topic": self._settings.kafka_detections_topic},
        )
        retry_task = asyncio.create_task(self._drain_retry_queue(), name="detection-retry-drain")
        try:
            async for message in consumer:
                await self._handle(message.value, retry_count=0)
                await consumer.commit()
        finally:
            retry_task.cancel()
            await consumer.stop()

    async def _handle(self, raw: dict, retry_count: int) -> None:  # type: ignore[type-arg]
        try:
            msg = DetectionMessage(**raw)
            set_trace_id(str(msg.post_id))
            # Deterministic detection_id for idempotency (FR-3.6)
            detection_id = uuid.uuid5(
                uuid.NAMESPACE_OID,
                f"{msg.post_id}:{msg.detected_at.isoformat()}:{msg.model_version}",
            )

            async with self._session_factory() as session:
                # Check for FK dependency before inserting
                post = await session.get(Post, msg.post_id)
                if post is None:
                    if retry_count < _MAX_RETRIES:
                        wait = min(_RETRY_BASE_SECONDS ** retry_count, 30)
                        logger.warning(
                            "Post not yet in DB — queuing retry",
                            extra={
                                "post_id": str(msg.post_id),
                                "retry": retry_count,
                                "wait_s": wait,
                            },
                        )
                        await self._retry_queue.put((raw, retry_count + 1))
                    else:
                        logger.error(
                            "Dead-letter: post not found after max retries",
                            extra={"post_id": str(msg.post_id)},
                        )
                    return

                stmt = (
                    pg_insert(Detection)
                    .values(
                        detection_id=detection_id,
                        post_id=msg.post_id,
                        label=msg.label,
                        confidence=msg.confidence,
                        reasoning=msg.reasoning,
                        model_version=msg.model_version,
                        prompt_version=msg.prompt_version,
                        detected_at=msg.detected_at,
                    )
                    .on_conflict_do_nothing(index_elements=["detection_id"])
                )
                await session.execute(stmt)
                await session.commit()

            self._archiver.buffer(self._settings.kafka_detections_topic, raw)
            logger.info(
                "Detection stored",
                extra={
                    "detection_id": str(detection_id),
                    "post_id": str(msg.post_id),
                    "label": msg.label,
                },
            )
        except Exception:
            logger.exception("Failed to store detection", extra={"raw_preview": str(raw)[:200]})

    async def _drain_retry_queue(self) -> None:
        while True:
            raw, retry_count = await self._retry_queue.get()
            wait = min(_RETRY_BASE_SECONDS ** retry_count, 30)
            await asyncio.sleep(wait)
            await self._handle(raw, retry_count)

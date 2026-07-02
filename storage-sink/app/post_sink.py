import json
import logging

from aiokafka import AIOKafkaConsumer
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.config import Settings
from app.logging_config import set_trace_id
from app.models import Post
from app.parquet_archiver import ParquetArchiver
from app.schemas import PostMessage

logger = logging.getLogger(__name__)


class PostSink:
    def __init__(self, settings: Settings, engine: AsyncEngine, archiver: ParquetArchiver) -> None:
        self._settings = settings
        self._session_factory = async_sessionmaker(engine, expire_on_commit=False)
        self._archiver = archiver

    async def run(self) -> None:
        consumer = AIOKafkaConsumer(
            self._settings.kafka_posts_topic,
            bootstrap_servers=self._settings.kafka_bootstrap_servers,
            group_id=self._settings.kafka_posts_consumer_group,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            value_deserializer=lambda b: json.loads(b.decode("utf-8")),
        )
        await consumer.start()
        logger.info("Post sink consumer started", extra={"topic": self._settings.kafka_posts_topic})
        try:
            async for message in consumer:
                await self._handle(message.value)
                await consumer.commit()
        finally:
            await consumer.stop()

    async def _handle(self, raw: dict) -> None:  # type: ignore[type-arg]
        try:
            msg = PostMessage(**raw)
            set_trace_id(str(msg.user_id))
            async with self._session_factory() as session:
                stmt = (
                    pg_insert(Post)
                    .values(
                        post_id=msg.user_id,   # user_id is the unique post identifier
                        user_id=msg.user_id,
                        username=msg.username,
                        post_text=msg.post_text,
                        location=msg.location,
                        created_at=msg.created_at,
                    )
                    .on_conflict_do_nothing(index_elements=["post_id"])
                )
                await session.execute(stmt)
                await session.commit()
            self._archiver.buffer(self._settings.kafka_posts_topic, raw)
            logger.info("Post stored", extra={"post_id": str(msg.user_id)})
        except Exception:
            logger.exception("Failed to store post", extra={"raw_preview": str(raw)[:200]})

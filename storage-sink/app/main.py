import asyncio
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.detection_sink import DetectionSink
from app.logging_config import configure_logging
from app.parquet_archiver import ParquetArchiver
from app.post_sink import PostSink

logger = logging.getLogger(__name__)

_MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"


def run_migrations(database_url: str) -> None:
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", str(_MIGRATIONS_DIR))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_cfg, "head")
    logger.info("Alembic migrations applied")


async def main() -> None:
    configure_logging()
    settings = get_settings()

    logger.info("Running database migrations")
    # run_migrations (via alembic's env.py) calls asyncio.run() internally, which
    # can't nest inside this already-running loop — run it in a worker thread instead.
    await asyncio.to_thread(run_migrations, settings.database_url)

    engine = create_async_engine(settings.database_url, echo=False)
    archiver = ParquetArchiver(settings)
    post_sink = PostSink(settings, engine, archiver)
    detection_sink = DetectionSink(settings, engine, archiver)

    logger.info("Storage sink starting")
    async with asyncio.TaskGroup() as tg:
        tg.create_task(post_sink.run(), name="post-sink")
        tg.create_task(detection_sink.run(), name="detection-sink")
        tg.create_task(archiver.flush_loop(), name="parquet-flush")


if __name__ == "__main__":
    asyncio.run(main())

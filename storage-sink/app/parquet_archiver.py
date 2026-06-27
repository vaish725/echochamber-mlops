import asyncio
import io
import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import boto3
import pyarrow as pa
import pyarrow.parquet as pq

from app.config import Settings

logger = logging.getLogger(__name__)


class ParquetArchiver:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._buffers: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._s3 = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )

    def buffer(self, topic: str, record: dict[str, Any]) -> None:
        self._buffers[topic].append(record)

    async def flush_loop(self) -> None:
        while True:
            await asyncio.sleep(self._settings.parquet_flush_interval_seconds)
            await self.flush()

    async def flush(self) -> None:
        for topic in list(self._buffers.keys()):
            records = self._buffers.pop(topic, [])
            if records:
                await self._upload(topic, records)

    async def _upload(self, topic: str, records: list[dict[str, Any]]) -> None:
        now = datetime.now(timezone.utc)
        key = (
            f"topic={topic}/"
            f"date={now.strftime('%Y-%m-%d')}/"
            f"hour={now.strftime('%H')}/"
            f"{uuid.uuid4()}.parquet"
        )
        # Convert all values to strings for Parquet schema consistency
        safe = [{k: str(v) for k, v in r.items()} for r in records]
        table = pa.Table.from_pylist(safe)
        buf = io.BytesIO()
        pq.write_table(table, buf)
        try:
            await asyncio.to_thread(
                self._s3.put_object,
                Bucket=self._settings.s3_bucket,
                Key=key,
                Body=buf.getvalue(),
            )
            logger.info(
                "Parquet archived",
                extra={"topic": topic, "records": len(records), "key": key},
            )
        except Exception:
            logger.exception("S3 upload failed", extra={"topic": topic, "key": key})

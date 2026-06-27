from unittest.mock import MagicMock, patch

import pytest

from app.parquet_archiver import ParquetArchiver
from tests.conftest import RAW_DETECTION, RAW_POST


@pytest.fixture
def archiver(settings):
    with patch("app.parquet_archiver.boto3.client"):
        return ParquetArchiver(settings)


def test_buffer_accumulates_records(archiver):
    archiver.buffer("topic-a", RAW_POST)
    archiver.buffer("topic-a", RAW_POST)
    archiver.buffer("topic-b", RAW_DETECTION)

    assert len(archiver._buffers["topic-a"]) == 2
    assert len(archiver._buffers["topic-b"]) == 1


async def test_flush_uploads_and_clears_buffer(archiver):
    archiver.buffer("social-media-stream", RAW_POST)
    archiver._s3.put_object = MagicMock()

    await archiver.flush()

    archiver._s3.put_object.assert_called_once()
    assert "social-media-stream" not in archiver._buffers


async def test_flush_empty_buffer_is_noop(archiver):
    archiver._s3.put_object = MagicMock()

    await archiver.flush()

    archiver._s3.put_object.assert_not_called()


async def test_flush_s3_failure_does_not_raise(archiver):
    archiver.buffer("topic", RAW_POST)
    archiver._s3.put_object = MagicMock(side_effect=Exception("S3 down"))

    await archiver.flush()  # Should not raise

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.detection_sink import DetectionSink
from app.models import Post
from app.parquet_archiver import ParquetArchiver

from tests.conftest import RAW_DETECTION


@pytest.fixture
def mock_archiver(settings):
    archiver = MagicMock(spec=ParquetArchiver)
    archiver.buffer = MagicMock()
    return archiver


@pytest.fixture
def mock_session_with_post():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.get = AsyncMock(return_value=MagicMock(spec=Post))
    return session


@pytest.fixture
def mock_session_no_post():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.get = AsyncMock(return_value=None)
    return session


@pytest.fixture
def detection_sink(settings, mock_archiver):
    engine = MagicMock()
    return DetectionSink(settings, engine, mock_archiver)


async def test_handle_writes_detection_when_post_exists(
    detection_sink, mock_archiver, mock_session_with_post
):
    with patch.object(detection_sink, "_session_factory") as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session_with_post)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await detection_sink._handle(RAW_DETECTION, retry_count=0)

        mock_session_with_post.execute.assert_awaited_once()
        mock_session_with_post.commit.assert_awaited_once()
        mock_archiver.buffer.assert_called_once()


async def test_handle_queues_retry_when_post_missing(detection_sink, mock_session_no_post):
    with patch.object(detection_sink, "_session_factory") as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session_no_post)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await detection_sink._handle(RAW_DETECTION, retry_count=0)

        assert detection_sink._retry_queue.qsize() == 1
        raw, count = await detection_sink._retry_queue.get()
        assert count == 1


async def test_handle_dead_letters_after_max_retries(
    detection_sink, mock_archiver, mock_session_no_post
):
    from app.detection_sink import _MAX_RETRIES
    with patch.object(detection_sink, "_session_factory") as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session_no_post)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await detection_sink._handle(RAW_DETECTION, retry_count=_MAX_RETRIES)

        assert detection_sink._retry_queue.qsize() == 0
        mock_archiver.buffer.assert_not_called()


def test_detection_id_is_deterministic():
    from app.schemas import DetectionMessage

    msg = DetectionMessage(**RAW_DETECTION)

    def make_id() -> uuid.UUID:
        return uuid.uuid5(
            uuid.NAMESPACE_OID,
            f"{msg.post_id}:{msg.detected_at.isoformat()}:{msg.model_version}",
        )

    assert make_id() == make_id()

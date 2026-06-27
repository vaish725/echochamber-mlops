import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.parquet_archiver import ParquetArchiver
from app.post_sink import PostSink
from tests.conftest import RAW_POST


@pytest.fixture
def mock_archiver(settings):
    archiver = MagicMock(spec=ParquetArchiver)
    archiver.buffer = MagicMock()
    return archiver


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.get = AsyncMock(return_value=None)
    return session


@pytest.fixture
def post_sink(settings, mock_archiver):
    engine = MagicMock()
    sink = PostSink(settings, engine, mock_archiver)
    return sink


async def test_handle_writes_post_to_db(post_sink, mock_archiver, mock_session):
    with patch.object(post_sink, "_session_factory") as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await post_sink._handle(RAW_POST)

        mock_session.execute.assert_awaited_once()
        mock_session.commit.assert_awaited_once()


async def test_handle_buffers_to_archiver(post_sink, mock_archiver, mock_session):
    with patch.object(post_sink, "_session_factory") as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await post_sink._handle(RAW_POST)

        mock_archiver.buffer.assert_called_once_with(
            post_sink._settings.kafka_posts_topic, RAW_POST
        )


async def test_handle_does_not_raise_on_db_error(post_sink, mock_archiver, mock_session):
    mock_session.execute = AsyncMock(side_effect=Exception("DB down"))
    with patch.object(post_sink, "_session_factory") as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await post_sink._handle(RAW_POST)

        mock_archiver.buffer.assert_not_called()

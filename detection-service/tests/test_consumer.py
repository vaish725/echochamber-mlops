from unittest.mock import AsyncMock, MagicMock

import pytest
from app.consumer import KafkaDetectionConsumer
from app.schemas import MisinformationLabel


@pytest.fixture
def mock_detector(sample_detection):
    detector = MagicMock()
    detector.classify = AsyncMock(return_value=sample_detection)
    return detector


@pytest.fixture
def mock_publisher():
    publisher = MagicMock()
    publisher.publish = AsyncMock()
    return publisher


@pytest.fixture
def mock_tracker():
    tracker = MagicMock()
    tracker.should_flush.return_value = False
    return tracker


@pytest.fixture
def kafka_consumer(settings, mock_detector, mock_publisher, mock_tracker):
    return KafkaDetectionConsumer(settings, mock_detector, mock_publisher, mock_tracker)


async def test_handle_message_calls_detector_and_publishes(
    kafka_consumer, mock_detector, mock_publisher
):
    raw = {
        "user_id": "u1",
        "username": "alice",
        "post_text": "Vaccines cause autism",
        "created_at": "2026-01-01T00:00:00Z",
        "location": "NYC, USA",
    }
    await kafka_consumer._handle_message(raw)

    mock_detector.classify.assert_awaited_once()
    mock_publisher.publish.assert_awaited_once()
    published = mock_publisher.publish.call_args[0][0]
    assert published.label == MisinformationLabel.MISINFORMATION


async def test_handle_message_records_to_tracker(kafka_consumer, mock_tracker):
    raw = {
        "user_id": "u1",
        "username": "alice",
        "post_text": "Vaccines cause autism",
        "created_at": "2026-01-01T00:00:00Z",
        "location": "NYC, USA",
    }
    await kafka_consumer._handle_message(raw)

    mock_tracker.record.assert_called_once()
    mock_tracker.should_flush.assert_called_once()


async def test_handle_message_flushes_tracker_when_due(kafka_consumer, mock_tracker):
    mock_tracker.should_flush.return_value = True
    raw = {
        "user_id": "u1",
        "username": "alice",
        "post_text": "Vaccines cause autism",
        "created_at": "2026-01-01T00:00:00Z",
        "location": "NYC, USA",
    }
    await kafka_consumer._handle_message(raw)

    mock_tracker.flush.assert_called_once()


async def test_handle_message_does_not_raise_on_classifier_error(
    settings, mock_publisher, mock_tracker
):
    failing_detector = MagicMock()
    failing_detector.classify = AsyncMock(side_effect=Exception("LLM down"))
    consumer = KafkaDetectionConsumer(settings, failing_detector, mock_publisher, mock_tracker)

    # Should swallow the exception and not propagate
    await consumer._handle_message({
        "user_id": "u", "username": "u", "post_text": "test",
        "created_at": "2026-01-01T00:00:00Z", "location": "City, Country",
    })
    mock_publisher.publish.assert_not_awaited()


def test_is_healthy_false_before_start(kafka_consumer):
    assert not kafka_consumer.is_healthy


def test_is_healthy_false_when_task_done(kafka_consumer):
    done_task = MagicMock()
    done_task.done.return_value = True
    kafka_consumer._loop_task = done_task
    assert not kafka_consumer.is_healthy


def test_is_healthy_true_when_task_running(kafka_consumer):
    running_task = MagicMock()
    running_task.done.return_value = False
    kafka_consumer._loop_task = running_task
    assert kafka_consumer.is_healthy

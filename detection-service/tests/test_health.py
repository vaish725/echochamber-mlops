from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_health_ok_when_consumer_alive():
    mock_consumer = MagicMock()
    mock_consumer.is_healthy = True
    with patch("app.main._kafka_consumer", mock_consumer):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_health_503_when_consumer_crashed():
    mock_consumer = MagicMock()
    mock_consumer.is_healthy = False
    with patch("app.main._kafka_consumer", mock_consumer):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
    assert response.status_code == 503


async def test_health_503_when_no_consumer():
    with patch("app.main._kafka_consumer", None):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
    assert response.status_code == 503

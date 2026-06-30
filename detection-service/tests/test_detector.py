import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.detector import MisinformationDetector
from app.schemas import MisinformationLabel, Post


def _make_openai_response(
    label: str, confidence: float = 0.9, reasoning: str = "test"
) -> MagicMock:
    content = json.dumps({"label": label, "confidence": confidence, "reasoning": reasoning})
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    choice.finish_reason = "stop"
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.fixture
def detector(settings):
    with patch("app.detector.AsyncOpenAI"):
        return MisinformationDetector(settings)


async def test_classify_returns_detection(detector, settings):
    detector._client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response("CREDIBLE", confidence=0.88)
    )
    post = Post(
        user_id="u1",
        username="alice",
        post_text="The sky is blue.",
        created_at="2026-01-01T00:00:00Z",
        location="NYC, USA",
    )
    result = await detector.classify(post)

    assert result.post_id == "u1"
    assert result.post_text == "The sky is blue."
    assert result.label == MisinformationLabel.CREDIBLE
    assert result.confidence == 0.88
    assert result.model_version == settings.llm_model
    assert result.prompt_version == "v1"
    assert result.detected_at


async def test_classify_all_five_labels(detector):
    labels = ["MISINFORMATION", "LIKELY_MISINFORMATION", "UNCERTAIN", "LIKELY_CREDIBLE", "CREDIBLE"]
    for label_str in labels:
        detector._client.chat.completions.create = AsyncMock(
            return_value=_make_openai_response(label_str)
        )
        post = Post(
            user_id="u", username="u", post_text="test",
            created_at="2026-01-01T00:00:00Z", location="City, Country",
        )
        result = await detector.classify(post)
        assert result.label.value == label_str


async def test_classify_retries_three_times_then_raises(detector):
    from openai import APITimeoutError
    detector._client.chat.completions.create = AsyncMock(
        side_effect=APITimeoutError(request=MagicMock())
    )
    post = Post(
        user_id="u", username="u", post_text="test",
        created_at="2026-01-01T00:00:00Z", location="City, Country",
    )
    with pytest.raises(APITimeoutError):
        await detector.classify(post)

    assert detector._client.chat.completions.create.call_count == 3


async def test_classify_succeeds_on_second_attempt(detector):
    from openai import APITimeoutError
    ok_response = _make_openai_response("LIKELY_CREDIBLE", confidence=0.75)
    detector._client.chat.completions.create = AsyncMock(
        side_effect=[APITimeoutError(request=MagicMock()), ok_response]
    )
    post = Post(
        user_id="u", username="u", post_text="test",
        created_at="2026-01-01T00:00:00Z", location="City, Country",
    )
    result = await detector.classify(post)
    assert result.label == MisinformationLabel.LIKELY_CREDIBLE
    assert detector._client.chat.completions.create.call_count == 2


async def test_content_filter_returns_uncertain(detector):
    response = _make_openai_response("CREDIBLE")
    response.choices[0].finish_reason = "content_filter"
    detector._client.chat.completions.create = AsyncMock(return_value=response)
    post = Post(
        user_id="u", username="u", post_text="sensitive content",
        created_at="2026-01-01T00:00:00Z", location="City, Country",
    )
    result = await detector.classify(post)
    assert result.label == MisinformationLabel.UNCERTAIN
    assert result.confidence == 0.0

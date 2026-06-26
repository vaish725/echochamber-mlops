import pytest
from pydantic import ValidationError

from app.schemas import Detection, LLMClassification, MisinformationLabel, Post


def test_post_valid():
    post = Post(
        user_id="u1",
        username="alice",
        post_text="Hello world",
        created_at="2026-01-01T00:00:00Z",
        location="NYC, USA",
    )
    assert post.user_id == "u1"


def test_detection_valid(sample_detection):
    assert sample_detection.label == MisinformationLabel.MISINFORMATION
    assert 0.0 <= sample_detection.confidence <= 1.0


def test_detection_confidence_below_zero_rejected():
    with pytest.raises(ValidationError):
        Detection(
            post_id="p1",
            post_text="test",
            label=MisinformationLabel.CREDIBLE,
            confidence=-0.1,
            reasoning="test",
            model_version="v1",
            prompt_version="v1",
        )


def test_detection_confidence_above_one_rejected():
    with pytest.raises(ValidationError):
        Detection(
            post_id="p1",
            post_text="test",
            label=MisinformationLabel.CREDIBLE,
            confidence=1.1,
            reasoning="test",
            model_version="v1",
            prompt_version="v1",
        )


def test_detection_invalid_label_rejected():
    with pytest.raises(ValidationError):
        Detection(
            post_id="p1",
            post_text="test",
            label="TOTALLY_MADE_UP",  # type: ignore[arg-type]
            confidence=0.5,
            reasoning="test",
            model_version="v1",
            prompt_version="v1",
        )


def test_all_five_labels_valid():
    for label in MisinformationLabel:
        d = Detection(
            post_id="p1",
            post_text="test",
            label=label,
            confidence=0.5,
            reasoning="test",
            model_version="v1",
            prompt_version="v1",
        )
        assert d.label == label


def test_llm_classification_parses_valid_json():
    clf = LLMClassification(
        label=MisinformationLabel.UNCERTAIN,
        confidence=0.5,
        reasoning="Not enough context.",
    )
    assert clf.label == MisinformationLabel.UNCERTAIN


def test_detection_detected_at_auto_populated():
    d = Detection(
        post_id="p1",
        post_text="test",
        label=MisinformationLabel.CREDIBLE,
        confidence=0.8,
        reasoning="looks fine",
        model_version="v1",
        prompt_version="v1",
    )
    assert d.detected_at  # non-empty ISO string

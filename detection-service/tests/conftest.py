import pytest

from app.config import Settings
from app.schemas import Detection, MisinformationLabel


@pytest.fixture
def settings() -> Settings:
    return Settings(
        kafka_bootstrap_servers="localhost:9092",
        kafka_input_topic="test-input",
        kafka_output_topic="test-output",
        kafka_consumer_group="test-group",
        llm_provider="claude",
        llm_model="claude-sonnet-4-6",
        anthropic_api_key="test-key-not-real",
        prompt_version="v1",
    )


@pytest.fixture
def sample_detection() -> Detection:
    return Detection(
        post_id="post-123",
        post_text="Vaccines cause autism according to new study",
        label=MisinformationLabel.MISINFORMATION,
        confidence=0.92,
        reasoning="This claim is scientifically disproven by extensive peer-reviewed research.",
        model_version="claude-sonnet-4-6",
        prompt_version="v1",
    )

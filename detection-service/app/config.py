from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_input_topic: str = "social-media-stream"
    kafka_output_topic: str = "detection-results"
    kafka_consumer_group: str = "misinformation-detectors-group-1"

    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    openai_api_key: str = Field(..., description="OpenAI API key — required")

    prompt_version: str = "v1"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def get_settings() -> Settings:
    return Settings()

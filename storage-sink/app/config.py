from pydantic import Field, computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_posts_topic: str = "social-media-stream"
    kafka_detections_topic: str = "detection-results"
    kafka_posts_consumer_group: str = "storage-sink-posts-group"
    kafka_detections_consumer_group: str = "storage-sink-detections-group"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "echochamber"
    postgres_user: str = "echochamber"
    postgres_password: str = Field(..., description="PostgreSQL password — required")

    s3_endpoint_url: str = "http://localhost:9000"
    s3_bucket: str = "echochamber-raw"
    aws_access_key_id: str = "minioadmin"
    aws_secret_access_key: str = "minioadmin"

    parquet_flush_interval_seconds: int = 30

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # required fields come from env/.env

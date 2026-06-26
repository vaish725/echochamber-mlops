from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class MisinformationLabel(str, Enum):
    MISINFORMATION = "MISINFORMATION"
    LIKELY_MISINFORMATION = "LIKELY_MISINFORMATION"
    UNCERTAIN = "UNCERTAIN"
    LIKELY_CREDIBLE = "LIKELY_CREDIBLE"
    CREDIBLE = "CREDIBLE"


class Post(BaseModel):
    user_id: str
    username: str
    post_text: str
    created_at: str
    location: str


class Detection(BaseModel):
    post_id: str
    post_text: str
    label: MisinformationLabel
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    model_version: str
    prompt_version: str
    detected_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class LLMClassification(BaseModel):
    """Intermediate model for parsing raw LLM JSON output."""
    label: MisinformationLabel
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str

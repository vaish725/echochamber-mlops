import uuid
from datetime import datetime

from pydantic import BaseModel


class PostMessage(BaseModel):
    user_id: uuid.UUID
    username: str
    post_text: str
    created_at: datetime
    location: str


class DetectionMessage(BaseModel):
    post_id: uuid.UUID
    post_text: str  # echoed from input — not stored in detections table
    label: str
    confidence: float
    reasoning: str
    model_version: str
    prompt_version: str
    detected_at: datetime

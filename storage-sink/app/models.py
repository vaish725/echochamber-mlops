from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Post(Base):
    __tablename__ = "posts"

    post_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))
    post_text: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Detection(Base):
    __tablename__ = "detections"
    __table_args__ = (Index("ix_detections_post_id", "post_id"),)

    detection_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    post_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.post_id"), nullable=True
    )
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[Numeric] = mapped_column(Numeric(4, 3), nullable=False)
    reasoning: Mapped[str | None] = mapped_column(Text)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(String(100))
    detected_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)

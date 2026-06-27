"""Initial schema: posts and detections tables

Revision ID: 0001
Revises:
Create Date: 2026-06-27
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "posts",
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("post_text", sa.Text(), nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("post_id"),
    )

    op.create_table(
        "detections",
        sa.Column("detection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("label", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(100), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["posts.post_id"]),
        sa.PrimaryKeyConstraint("detection_id"),
    )
    op.create_index("ix_detections_post_id", "detections", ["post_id"])


def downgrade() -> None:
    op.drop_index("ix_detections_post_id", table_name="detections")
    op.drop_table("detections")
    op.drop_table("posts")

from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.privacy_models import Scoped
from app.db import Base


class EvaluationDataset(Scoped, Base):
    __tablename__ = "evaluation_datasets"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id"),
        UniqueConstraint("workspace_id", "study_id", "key", "version"),
        ForeignKeyConstraint(
            ["workspace_id", "study_id"], ["studies.workspace_id", "studies.id"], ondelete="CASCADE"
        ),
        CheckConstraint("version > 0"),
    )
    study_id: Mapped[UUID]
    key: Mapped[str] = mapped_column(String(80))
    version: Mapped[int]
    creator_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    rights: Mapped[dict] = mapped_column(JSONB)
    schema: Mapped[dict] = mapped_column(JSONB)


class EvaluationIdentity(Scoped, Base):
    __tablename__ = "evaluation_identities"
    __table_args__ = (
        UniqueConstraint("workspace_id", "digest"),
        UniqueConstraint("workspace_id", "id"),
        CheckConstraint("partition IN ('train','evaluation')"),
    )
    digest: Mapped[str] = mapped_column(String(64))
    partition: Mapped[str] = mapped_column(String(16))


class EvaluationItem(Scoped, Base):
    __tablename__ = "evaluation_items"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id"),
        UniqueConstraint("dataset_id", "key"),
        ForeignKeyConstraint(
            ["workspace_id", "dataset_id"],
            ["evaluation_datasets.workspace_id", "evaluation_datasets.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "identity_id"],
            ["evaluation_identities.workspace_id", "evaluation_identities.id"],
        ),
    )
    dataset_id: Mapped[UUID]
    identity_id: Mapped[UUID]
    key: Mapped[str] = mapped_column(String(80))
    source: Mapped[dict] = mapped_column(JSONB)


class EvaluationAssignment(Scoped, Base):
    __tablename__ = "evaluation_assignments"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id"),
        UniqueConstraint("item_id", "reviewer_id"),
        ForeignKeyConstraint(
            ["workspace_id", "item_id"],
            ["evaluation_items.workspace_id", "evaluation_items.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("kind IN ('independent','adjudication')"),
        Index(
            "uq_evaluation_adjudication",
            "item_id",
            unique=True,
            postgresql_where=text("kind='adjudication'"),
        ),
    )
    item_id: Mapped[UUID]
    reviewer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(20))
    candidate_order: Mapped[list] = mapped_column(JSONB)
    independence_checked: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))


class EvaluationOutcome(Scoped, Base):
    __tablename__ = "evaluation_outcomes"
    __table_args__ = (
        UniqueConstraint("assignment_id"),
        CheckConstraint(
            "body->>'provenance' = 'authenticated_human'", name="evaluation_human_outcome"
        ),
        ForeignKeyConstraint(
            ["workspace_id", "assignment_id"],
            ["evaluation_assignments.workspace_id", "evaluation_assignments.id"],
            ondelete="CASCADE",
        ),
    )
    assignment_id: Mapped[UUID]
    body: Mapped[dict] = mapped_column(JSONB)


class EvaluationExportReview(Scoped, Base):
    __tablename__ = "evaluation_export_reviews"
    __table_args__ = (
        UniqueConstraint("dataset_id"),
        ForeignKeyConstraint(
            ["workspace_id", "dataset_id"],
            ["evaluation_datasets.workspace_id", "evaluation_datasets.id"],
            ondelete="CASCADE",
        ),
    )
    dataset_id: Mapped[UUID]
    reviewer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[dict] = mapped_column(JSONB)
    snapshot_digest: Mapped[str] = mapped_column(String(64))


class EvaluationRawExposure(Scoped, Base):
    """Durable first disclosure, independent of revocable grants."""

    __tablename__ = "evaluation_raw_exposures"
    __table_args__ = (
        UniqueConstraint("dataset_id", "actor_id"),
        ForeignKeyConstraint(
            ["workspace_id", "dataset_id"],
            ["evaluation_datasets.workspace_id", "evaluation_datasets.id"],
            ondelete="CASCADE",
        ),
    )
    dataset_id: Mapped[UUID]
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))

from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.privacy_models import Scoped
from app.db import Base


class TemplateInstance(Scoped, Base):
    __tablename__ = "template_instances"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id"),
        UniqueConstraint("version_id"),
        ForeignKeyConstraint(
            ["workspace_id", "study_id"], ["studies.workspace_id", "studies.id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["workspace_id", "version_id"],
            ["study_versions.workspace_id", "study_versions.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "template_version > 0 AND recipe_hash ~ '^[0-9a-f]{64}$' AND configuration_hash ~ '^[0-9a-f]{64}$'"
        ),
        CheckConstraint(
            "jsonb_typeof(recipe_snapshot) = 'object' AND jsonb_typeof(inputs_snapshot) = 'object'"
        ),
    )
    study_id: Mapped[UUID]
    version_id: Mapped[UUID]
    template_key: Mapped[str] = mapped_column(String(64))
    template_version: Mapped[int]
    recipe_hash: Mapped[str] = mapped_column(String(64))
    configuration_hash: Mapped[str] = mapped_column(String(64))
    recipe_snapshot: Mapped[dict] = mapped_column(JSONB)
    inputs_snapshot: Mapped[dict] = mapped_column(JSONB)

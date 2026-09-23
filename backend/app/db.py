from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, String, create_engine, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.config import Settings

REVISION = "003_jobs"


class Base(DeclarativeBase):
    pass


class AppMetadata(Base):
    """P01 synthetic fixture marker only, not a research data model."""

    __tablename__ = "app_metadata"
    __table_args__ = (CheckConstraint("is_synthetic IS TRUE", name="ck_metadata_synthetic"),)
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Database:
    def __init__(self, settings: Settings):
        self.engine = create_engine(
            settings.database_url.get_secret_value(),
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=True,
            pool_timeout=2,
            connect_args={
                "connect_timeout": settings.db_connect_timeout,
                "options": "-c statement_timeout=2000",
            },
            hide_parameters=True,
        )
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    def check_ready(self) -> bool:
        try:
            with self.engine.connect() as conn:
                revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
                conn.execute(text("SELECT key FROM app_metadata LIMIT 1"))
                return revision == REVISION
        except Exception:
            return False

    def close(self) -> None:
        self.engine.dispose()

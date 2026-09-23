import os

from alembic import context
from sqlalchemy import create_engine, pool

from app.auth import models as auth_models  # noqa: F401
from app.common.idempotency import IdempotencyRecord  # noqa: F401
from app.db import Base
from app.jobs import models as jobs_models  # noqa: F401

target_metadata = Base.metadata
url = os.environ.get("MIGRATION_DATABASE_URL")
if not url or not url.startswith("postgresql+psycopg://"):
    raise RuntimeError("A valid MIGRATION_DATABASE_URL is required")

if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool, hide_parameters=True)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()

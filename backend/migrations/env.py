import os

from alembic import context
from sqlalchemy import create_engine, pool

from app.ai import models as ai_models  # noqa: F401
from app.analytics import models as analytics_models  # noqa: F401
from app.auth import models as auth_models  # noqa: F401
from app.billing import models as billing_models  # noqa: F401
from app.collaboration import models as collaboration_models  # noqa: F401
from app.collection import models as collection_models  # noqa: F401
from app.common import privacy_models
from app.common.idempotency import IdempotencyRecord  # noqa: F401
from app.db import Base
from app.evaluation import models as evaluation_models  # noqa: F401
from app.jobs import models as jobs_models  # noqa: F401
from app.longitudinal import models as longitudinal_models  # noqa: F401
from app.privacy_ops import account_models as account_models  # noqa: F401
from app.privacy_ops import lifecycle_models as lifecycle_models  # noqa: F401
from app.privacy_ops import models as privacy_ops_models  # noqa: F401
from app.recruiting import models as recruiting_models  # noqa: F401
from app.reviews import models as review_models  # noqa: F401
from app.studies import models as study_models
from app.templates import models as template_models  # noqa: F401

assert privacy_models.ConsentDocument.__table__ is not None
assert study_models.Study.__table__ is not None

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

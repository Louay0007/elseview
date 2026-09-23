from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert

from app.config import load_settings
from app.db import AppMetadata


def seed_demo(engine):
    statement = (
        insert(AppMetadata)
        .values(
            key="p01_demo",
            value={"languages": ["fr", "ar", "aeb"], "label": "Synthetic P01 fixture"},
            is_synthetic=True,
        )
        .on_conflict_do_nothing(index_elements=["key"])
    )
    with engine.begin() as connection:
        connection.execute(statement)


def main():
    settings = load_settings()
    if settings.app_env not in {"development", "test"}:
        raise RuntimeError("Synthetic seeding is restricted to development/test")
    engine = create_engine(settings.migration_database_url.get_secret_value(), hide_parameters=True)
    try:
        seed_demo(engine)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

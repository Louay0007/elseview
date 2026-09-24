from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool
from test_notification_delivery import dispatch, queued  # noqa: F401
from test_recruiting import recruitment  # noqa: F401

from app.collaboration.models import NotificationDelivery
from app.privacy_ops.restore import copy_files, export_tombstones, replay, restore_ready

pytestmark = pytest.mark.db


def test_restored_presend_notification_cannot_replay_postsnapshot_acceptance(queued, db_engine):  # noqa: F811
    app, did = queued[1], queued[10]
    source = db_engine.url
    assert source.database.endswith("_test")
    name = "notification_" + uuid4().hex + "_restore"
    target_url = source.set(database=name)
    source_files = app.state.settings.private_root.resolve()
    target_files = source_files.parent / ("notification_" + uuid4().hex + "_restore")
    copy_files(source_files, target_files)
    app.state.database.engine.dispose()
    db_engine.dispose()
    admin = create_engine(
        source, isolation_level="AUTOCOMMIT", poolclass=NullPool, hide_parameters=True
    )
    target = create_engine(target_url, poolclass=NullPool, hide_parameters=True)
    created = False
    try:
        with admin.connect() as conn:
            quote = conn.dialect.identifier_preparer.quote_identifier
            conn.exec_driver_sql(f"CREATE DATABASE {quote(name)} TEMPLATE {quote(source.database)}")
            created = True
        assert dispatch(queued)
        with app.state.database.sessions() as s:
            assert s.get(NotificationDelivery, did).state == "sent"
            path = source_files / "notification-manifest.json"
            key = b"synthetic-restore-key-at-least-32-bytes"
            digest = export_tombstones(s, path, key)
        assert not restore_ready(target, target_files)
        replay(
            source.render_as_string(hide_password=False),
            target_url.render_as_string(hide_password=False),
            source_files,
            target_files,
            path,
            key,
            digest,
        )
        assert restore_ready(target, target_files)
        with Session(target) as s:
            row = s.get(NotificationDelivery, did)
            assert (row.state, row.outcome) == ("uncertain", "restore_quarantine")
    finally:
        target.dispose()
        if created:
            with admin.connect() as conn:
                quote = conn.dialect.identifier_preparer.quote_identifier
                conn.exec_driver_sql(f"DROP DATABASE {quote(name)}")
        admin.dispose()


def test_notification_migration_round_trip(migration_engine):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect

    config = Config("alembic.ini")
    assert "notification_deliveries" in inspect(migration_engine).get_table_names()
    command.downgrade(config, "027_diary_recovery")
    assert "notification_deliveries" not in inspect(migration_engine).get_table_names()
    command.upgrade(config, "028_notification_delivery")
    inspector = inspect(migration_engine)
    assert "notification_deliveries" in inspector.get_table_names()
    assert (
        next(
            c
            for c in inspector.get_columns("notification_preferences")
            if c["name"] == "email_reminders"
        )["default"]
        == "false"
    )

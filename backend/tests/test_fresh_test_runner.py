from unittest.mock import MagicMock, Mock

import pytest
from alembic import command

from app.test_runner import prepare_database


@pytest.fixture
def isolated_migrations(monkeypatch):
    import sqlalchemy

    engine = MagicMock()
    inspector = Mock()
    for name in (
        "get_table_names",
        "get_view_names",
        "get_materialized_view_names",
        "get_enums",
        "get_sequence_names",
    ):
        getattr(inspector, name).return_value = []
    inspector.get_schema_names.return_value = ["public", "information_schema"]
    monkeypatch.setattr(sqlalchemy, "create_engine", Mock(return_value=engine))
    monkeypatch.setattr(sqlalchemy, "inspect", Mock(return_value=inspector))
    monkeypatch.setattr(command, "upgrade", Mock())
    monkeypatch.setattr(command, "downgrade", Mock())
    return engine, inspector


def test_fresh_migrates_without_any_downgrade(isolated_migrations):
    config = object()
    prepare_database(config, "synthetic-unused-url", "fresh")
    command.downgrade.assert_not_called()
    command.upgrade.assert_called_once_with(config, "head")
    isolated_migrations[0].dispose.assert_called_once()


@pytest.mark.parametrize(
    "object_kind",
    [
        "get_table_names",
        "get_view_names",
        "get_materialized_view_names",
        "get_enums",
        "get_sequence_names",
        "get_schema_names",
    ],
)
def test_fresh_refuses_existing_objects_without_modification(isolated_migrations, object_kind):
    getattr(isolated_migrations[1], object_kind).return_value = ["existing"]
    with pytest.raises(RuntimeError, match="empty database"):
        prepare_database(object(), "synthetic-unused-url", "fresh")
    command.downgrade.assert_not_called()
    command.upgrade.assert_not_called()
    isolated_migrations[0].dispose.assert_called_once()


def test_unknown_mode_never_runs_migrations(isolated_migrations):
    with pytest.raises(RuntimeError, match="Unknown"):
        prepare_database(object(), "synthetic-unused-url", "freh")
    command.downgrade.assert_not_called()
    command.upgrade.assert_not_called()


def test_existing_explicit_reset_mode_preserved(isolated_migrations):
    config = object()
    prepare_database(config, "synthetic-unused-url")
    command.downgrade.assert_called_once_with(config, "base")
    command.upgrade.assert_called_once_with(config, "head")

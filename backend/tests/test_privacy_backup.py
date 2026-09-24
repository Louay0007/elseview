"""Snapshot archives bind both database and files; no PostgreSQL binaries needed."""

import hashlib
import json

import pytest

from app.privacy_ops import backup


def test_snapshot_binds_private_bytes_and_refuses_tampering(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    (source / "assets").mkdir()
    (source / "assets" / "synthetic").write_bytes(b"private synthetic bytes")
    calls = []

    def dump(command, **kwargs):
        calls.append(command)
        kwargs["stdout"].write(b"synthetic PostgreSQL archive")

    monkeypatch.setattr(backup.subprocess, "run", dump)
    directory = tmp_path / "snapshot"
    digest = backup.snapshot("postgresql://user:secret@database/live", source, directory)
    metadata = (directory / "snapshot.json").read_bytes()
    assert hashlib.sha256(metadata).hexdigest() == digest
    assert json.loads(metadata)["files"] == {
        "assets/synthetic": hashlib.sha256(b"private synthetic bytes").hexdigest()
    }
    assert (directory / "database.dump").stat().st_mode & 0o777 == 0o600
    (directory / "files" / "assets" / "synthetic").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="content mismatch"):
        backup.restore_snapshot(
            "postgresql://user@database/live",
            "postgresql://user@database/test_restore",
            source,
            tmp_path / "files_restore",
            directory,
            digest,
        )
    assert len(calls) == 1  # Never reaches pg_restore or a DB connection.


def test_partial_snapshot_never_gets_valid_metadata(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()

    def failure(*args, **kwargs):
        raise OSError("synthetic secret must not escape")

    monkeypatch.setattr(backup.subprocess, "run", failure)
    directory = tmp_path / "snapshot"
    with pytest.raises(RuntimeError, match="partial directory is not restorable"):
        backup.snapshot("postgresql://user:secret@database/live", source, directory)
    assert not (directory / "snapshot.json").exists()

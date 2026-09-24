"""Offline physical snapshots with external PostgreSQL client tools.

Requires pg_dump/pg_restore on PATH (e.g. run inside postgres:16 container).
No compression archive is extracted by Python. Password travels only in child env.
Use operator-managed encrypted volumes: neither PostgreSQL dump nor HMAC encrypts.
"""

import hashlib
import json
import os
import subprocess
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.privacy_ops.restore import copy_files, verify_isolation


def _connection(url):
    parsed = make_url(url)
    env = os.environ.copy()
    env.update(
        PGHOST=parsed.host or "",
        PGPORT=str(parsed.port or 5432),
        PGUSER=parsed.username or "",
        PGPASSWORD=parsed.password or "",
        PGDATABASE=parsed.database or "",
    )
    return env


def _digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _inventory(root):
    root = Path(root)
    entries = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError("Snapshot contains unsupported file")
        if path.is_file():
            entries[str(path.relative_to(root))] = _digest(path)
    return entries


def snapshot(source_url, source_files, destination):
    dest = Path(destination)
    dest.mkdir(mode=0o700, parents=False, exist_ok=False)
    dump = dest / "database.dump"
    fd = os.open(dump, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            subprocess.run(
                ["pg_dump", "--format=custom", "--no-owner", "--no-acl"],
                env=_connection(source_url),
                stdout=stream,
                stderr=subprocess.DEVNULL,
                check=True,
            )
        copy_files(source_files, dest / "files")
        metadata_value = {
            "version": 2,
            "database_sha256": _digest(dump),
            "files": _inventory(dest / "files"),
        }
        payload = json.dumps(metadata_value, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(payload).hexdigest()
        metadata = dest / "snapshot.json"
        fd = os.open(metadata, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        return digest
    except Exception:
        # Keep partial evidence offline, never mark ready.
        raise RuntimeError("Snapshot failed; partial directory is not restorable") from None


def restore_snapshot(
    source_url, restore_url, source_files, restore_files, snapshot_directory, expected_digest
):
    target = verify_isolation(source_url, restore_url, source_files, restore_files)
    snapshot = Path(snapshot_directory)
    dump = snapshot / "database.dump"
    if any(p.is_symlink() for p in (snapshot, *snapshot.parents)) or dump.is_symlink():
        raise ValueError("Snapshot symlinks are forbidden")
    metadata = snapshot / "snapshot.json"
    if metadata.is_symlink() or _digest(metadata) != expected_digest:
        raise ValueError("Snapshot digest mismatch")
    manifest = json.loads(metadata.read_bytes())
    if (
        manifest.get("version") != 2
        or manifest.get("database_sha256") != _digest(dump)
        or manifest.get("files") != _inventory(snapshot / "files")
    ):
        raise ValueError("Snapshot content mismatch")
    if target.exists() and any(target.iterdir()):
        raise ValueError("Target files must be empty before physical restore")
    # A distinct name alone does not make an existing database disposable.
    engine = create_engine(restore_url, hide_parameters=True)
    try:
        with engine.connect() as connection:
            if connection.scalar(
                text(
                    "SELECT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema'))"
                )
            ):
                raise ValueError("Target database must be empty before physical restore")
    finally:
        engine.dispose()
    subprocess.run(
        [
            "pg_restore",
            "--exit-on-error",
            "--no-owner",
            "--no-acl",
            "--dbname",
            make_url(restore_url).database,
            str(dump),
        ],
        env=_connection(restore_url),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    copy_files(snapshot / "files", target)
    # NO readiness marker: caller MUST replay latest live tombstones next.

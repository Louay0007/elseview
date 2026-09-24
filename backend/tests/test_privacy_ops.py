"""Offline protocol and dependency validation; no production connection."""

import hashlib
import hmac
import json
from uuid import uuid4

import pytest

from app.privacy_ops.restore import copy_files, read_manifest, verify_isolation


def test_restore_requires_isolated_database_and_files(tmp_path):
    source = tmp_path / "live"
    source.mkdir()
    target = tmp_path / "files_restore"
    assert (
        verify_isolation("postgresql://x/live", "postgresql://x/live_restore", source, target)
        == target
    )
    for url, path in [
        ("postgresql://x/live", target),
        ("postgresql://x/other", target),
        ("postgresql://x/live_restore", source),
    ]:
        with pytest.raises(ValueError):
            verify_isolation("postgresql://x/live", url, source, path)
    link = tmp_path / "link_restore"
    link.symlink_to(source)
    with pytest.raises(ValueError):
        verify_isolation("postgresql://x/live", "postgresql://x/live_restore", source, link)


def test_manifest_requires_latest_signature_and_no_content(tmp_path):
    key = b"x" * 32
    manifest = {
        "version": 3,
        "holds": [],
        "contact_holds": [],
        "accounts": [],
        "events": [],
        "tombstones": [
            {
                "id": str(uuid4()),
                "workspace_id": str(uuid4()),
                "subject_id": str(uuid4()),
                "purpose": "erasure",
            }
        ],
    }
    data = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(data).hexdigest()
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "manifest": manifest,
                "digest": digest,
                "signature": hmac.new(key, data, hashlib.sha256).hexdigest(),
            }
        )
    )
    assert read_manifest(path, key, digest) == manifest
    with pytest.raises(ValueError):
        read_manifest(path, key, "0" * 64)
    with pytest.raises(ValueError):
        read_manifest(path, b"y" * 32, digest)


def test_copy_rejects_symlink(tmp_path):
    source = tmp_path / "snapshot"
    source.mkdir()
    (source / "escape").symlink_to("/etc/passwd")
    with pytest.raises(ValueError):
        copy_files(source, tmp_path / "files_restore")


def test_registry_dependency_failure_is_not_silenced(monkeypatch):
    from app.common import privacy

    calls = []
    monkeypatch.setattr(privacy, "_ERASURE_HANDLERS", {})
    privacy.register_handler("later", lambda *a: calls.append("later"), after=("first",))
    privacy.register_handler("first", lambda *a: calls.append("first"))

    class Session:
        def flush(self):
            pass

    privacy.run_erasure_handlers(Session(), uuid4(), uuid4())
    assert calls == ["first", "later"]
    privacy.register_handler("bad", lambda *a: None, after=("missing",))
    with pytest.raises(RuntimeError):
        privacy.run_erasure_handlers(Session(), uuid4(), uuid4())


def test_copy_never_replays_readiness_marker(tmp_path):
    source = tmp_path / "snapshot"
    source.mkdir()
    (source / ".privacy-ready").write_text("stale marker")
    (source / "asset").write_bytes(b"synthetic")
    target = tmp_path / "files_restore"
    copy_files(source, target)
    assert not (target / ".privacy-ready").exists()
    assert (target / "asset").read_bytes() == b"synthetic"


def test_registry_failure_preserves_retry_not_completed(monkeypatch):
    from app.common import privacy

    monkeypatch.setattr(privacy, "_ERASURE_HANDLERS", {})
    calls = []
    failed = [True]

    def invalidate(*args):
        calls.append("invalidate")
        if failed[0]:
            raise OSError("synthetic disposable-store failure")

    privacy.register_handler("cache_invalidation", invalidate)
    privacy.register_handler(
        "delete", lambda *args: calls.append("delete"), after=("cache_invalidation",)
    )

    class Session:
        def flush(self):
            pass

    with pytest.raises(OSError):
        privacy.run_erasure_handlers(Session(), uuid4(), uuid4())
    assert calls == ["invalidate"]
    failed[0] = False
    privacy.run_erasure_handlers(Session(), uuid4(), uuid4())
    assert calls == ["invalidate", "invalidate", "delete"]


def test_review_inputs_reject_unknown_coercions_and_naive_deadlines():
    from datetime import timedelta

    from pydantic import ValidationError

    from app.auth.security import utcnow
    from app.privacy_ops.router import HoldBody, PolicyBody, future

    body = {
        "subject_id": str(uuid4()),
        "reason": " reviewed ",
        "review_deadline": (utcnow() + timedelta(days=1)).isoformat(),
    }
    assert HoldBody(**body).reason == "reviewed"
    for change in (
        {"extra": "raw text"},
        {"reason": "  "},
        {"review_deadline": "2030-01-01T00:00:00"},
    ):
        with pytest.raises(ValidationError):
            HoldBody(**(body | change))
    policy = {k: v for k, v in body.items() if k != "subject_id"}
    policy.update(purpose="raw", days=1, version=1)
    for change in ({"days": True}, {"version": "1"}, {"purpose": "identity"}):
        with pytest.raises(ValidationError):
            PolicyBody(**(policy | change))
    from app.common.errors import DomainError

    with pytest.raises(DomainError):
        future(HoldBody(**(body | {"review_deadline": utcnow() - timedelta(days=1)})))


def test_latest_overdue_retention_does_not_fall_back():
    from datetime import timedelta
    from types import SimpleNamespace

    from app.auth.security import utcnow
    from app.privacy_ops.service import reviewed_cutoff

    class Session:
        def scalar(self, query):
            assert "review_deadline >" not in str(query)
            assert "version DESC" in str(query)
            return SimpleNamespace(days=1, review_deadline=utcnow() - timedelta(days=1))

    assert reviewed_cutoff(Session(), uuid4(), "raw") is None


def test_actual_registry_callbacks_resolve_and_dependencies_exist():
    from app.common import privacy

    assert set(privacy._ERASURE_HANDLERS) == {
        "linked_assets",
        "longitudinal",
        "collection_analytics_ai_reviews",
        "evaluation",
        "financial",
        "recruiting",
        "assets_consent",
        "studies_templates",
        "operational_collaboration",
    }
    for callback, dependencies in privacy._ERASURE_HANDLERS.values():
        assert callable(callback)
        assert set(dependencies) <= privacy._ERASURE_HANDLERS.keys()
        if callback.__closure__:
            from importlib import import_module

            cells = dict(
                zip(
                    callback.__code__.co_freevars,
                    [cell.cell_contents for cell in callback.__closure__],
                    strict=True,
                )
            )
            assert callable(getattr(import_module(cells["module"]), cells["function"]))


def test_aggregate_cache_has_no_production_consumers():
    """A fake registry cache callback is not proof of deleting hashed Redis keys."""
    import ast
    from pathlib import Path

    root = Path(__file__).parents[1] / "app"
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text())
        assert not any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"get_json", "set_json"}
            for node in ast.walk(tree)
        ), str(path)


def test_ai_invalidation_preserves_raw_under_any_workspace_hold(monkeypatch):
    from types import SimpleNamespace

    from app.ai.service import invalidate_subject
    from app.billing import service

    row = SimpleNamespace(
        id=uuid4(),
        state="approved",
        output={"private": "synthetic"},
        instruction="synthetic raw",
        coverage={"sources": ["synthetic"]},
    )
    monkeypatch.setattr(service, "release_ai_addon", lambda *args: None)

    class Session:
        hold = True
        deletes = 0

        def scalar(self, query):
            return uuid4() if self.hold else None

        def scalars(self, query):
            return [row]

        def execute(self, query):
            self.deletes += 1

    session = Session()
    invalidate_subject(session, uuid4(), uuid4())
    assert row.state == "invalidated"
    assert row.output == {"private": "synthetic"}
    assert row.instruction == "synthetic raw" and session.deletes == 0
    session.hold = False
    invalidate_subject(session, uuid4(), uuid4())
    assert row.output is None and row.instruction == "" and session.deletes == 1


def test_financial_minimization_preserves_held_beneficiary(monkeypatch):
    from datetime import timedelta
    from types import SimpleNamespace

    from app.auth.security import utcnow
    from app.common import privacy
    from app.privacy_ops import service
    from app.reviews.privacy import minimize_financial

    subject = uuid4()
    reward = SimpleNamespace(
        subject_id=subject, retention_policy_id=uuid4(), settled_at=utcnow() - timedelta(days=10)
    )
    monkeypatch.setattr(privacy, "lock_workspace", lambda *args: None)
    hold = [True]
    monkeypatch.setattr(service, "held", lambda *args: hold[0])

    class Session:
        def scalars(self, query):
            return [reward]

        def get(self, *args):
            return SimpleNamespace(settled_days=1)

        def flush(self):
            pass

    assert minimize_financial(Session(), uuid4()) == 0
    assert reward.subject_id == subject
    hold[0] = False
    assert minimize_financial(Session(), uuid4()) == 1
    assert reward.subject_id is None


def test_recording_withdrawal_blocks_links_preserves_held_transcript(monkeypatch):
    from types import SimpleNamespace

    from app.longitudinal.service import recording_revoke
    from app.privacy_ops import service

    row = SimpleNamespace(id=uuid4(), asset_id=uuid4(), revoked=False)
    asset = SimpleNamespace(id=row.asset_id, state="ready")
    link = SimpleNamespace(revoked_at=None)
    monkeypatch.setattr(service, "held", lambda *args: True)

    class Session:
        calls = 0

        def scalars(self, query):
            self.calls += 1
            return [row] if self.calls == 1 else [link]

        def get(self, *args):
            return asset

        def execute(self, query):
            pytest.fail("held transcript must not be deleted")

    recording_revoke(Session(), uuid4(), uuid4(), None)
    assert row.revoked and asset.state == "blocked" and link.revoked_at is not None

"""Global assessment retention/revocation must survive backup replay."""

from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from test_language_assessments_db import (
    API,
    ATTEMPTS,
    begin,
    decide,
    ok,
    publish,
    submit,
)
from test_language_assessments_db import (
    assessment as assessment,
)

from app.auth.security import utcnow
from app.recruiting import assessment_privacy, assessments
from app.recruiting.models import (
    LanguageAssessmentAttempt as Attempt,
)
from app.recruiting.models import (
    LanguageAssessmentConsent as Consent,
)
from app.recruiting.models import (
    LanguageAssessmentDecision as Decision,
)

pytestmark = pytest.mark.db


def test_retention_read_cutoff_and_idempotent_physical_purge(assessment):
    x = assessment
    attempt = ok(begin(x, publish(x)), 201)
    ok(submit(x, attempt))
    ok(decide(x, attempt))
    with x["app"].state.database.sessions.begin() as session:
        session.get(Attempt, UUID(attempt["id"])).retention_until = utcnow() - timedelta(seconds=1)
    detail = ok(x["client"].get(ATTEMPTS + f"/{attempt['id']}", headers=x["ph"]))
    assert not detail["evidence_available"]
    assert detail["responses"] is None and detail["decisions"][0]["rationale"] is None
    assert (
        x["client"].get(x["root"] + f"/attempts/{attempt['id']}", headers=x["rh"]).status_code
        == 409
    )
    route = x["root"] + "/retention-sweep?language=french"
    assert ok(x["client"].post(route, headers=x["rh"]))["purged"] >= 1
    assert ok(x["client"].post(route, headers=x["rh"]))["purged"] == 0
    with x["app"].state.database.sessions() as session:
        row = session.get(Attempt, UUID(attempt["id"]))
        assert row.responses_json is None and row.purged_at is not None
        assert row.submission_digest is None and row.appeal_digest is None
        decision = session.scalar(select(Decision).where(Decision.attempt_id == row.id))
        assert decision.rationale is None and decision.findings_json is None
        assert decision.request_digest == "0" * 64


def test_global_account_erasure_purges_attempt_and_reviewer_rationale(assessment):
    from app.privacy_ops.account import apply_account_restriction

    x = assessment
    attempt = ok(begin(x, publish(x, synthetic=False)), 201)
    ok(submit(x, attempt))
    ok(decide(x, attempt))
    with x["app"].state.database.sessions.begin() as session:
        apply_account_restriction(session, x["pid"])
        apply_account_restriction(session, x["pid"])
        row = session.get(Attempt, UUID(attempt["id"]))
        assert row.responses_json is None and row.state == "withdrawn"
        assert assessments.current_qualifications(session, UUID(x["profile"])) == []
        assert (
            session.scalar(select(Decision).where(Decision.attempt_id == row.id)).rationale is None
        )
    with x["app"].state.database.sessions.begin() as session:
        assessment_privacy.purge_account(session, x["rid"])
        assert (
            session.scalar(
                select(Decision).where(Decision.attempt_id == UUID(attempt["id"]))
            ).findings_json
            is None
        )


def test_workspace_erasure_does_not_purge_global_assessments(assessment):
    from app.recruiting.service import erase_subject

    x = assessment
    attempt = ok(begin(x, publish(x)), 201)
    ok(submit(x, attempt))
    with x["app"].state.database.sessions.begin() as session:
        erase_subject(session, x["wid"], x["pid"])
        row = session.get(Attempt, UUID(attempt["id"]))
        assert row.responses_json is not None and row.state == "submitted"


def test_restore_revocation_prevents_resurrection_without_workspace_scope(assessment):
    x = assessment
    attempt = ok(begin(x, publish(x, synthetic=False)), 201)
    ok(submit(x, attempt))
    ok(decide(x, attempt))
    rows = [{"profile_id": x["profile"], "grant_id": x["grant"]["id"]}]
    with x["app"].state.database.sessions.begin() as session:
        assert assessments.current_qualifications(session, UUID(x["profile"]))
        assessment_privacy.replay_revocations(session, rows)
        assessment_privacy.replay_revocations(session, rows)
        assert assessments.current_qualifications(session, UUID(x["profile"])) == []
        assert rows[0] in assessment_privacy.export_revocations(session)
        assert session.get(Attempt, UUID(attempt["id"])).state == "withdrawn"
        assert (
            len(
                list(
                    session.scalars(
                        select(Consent).where(Consent.grant_id == UUID(x["grant"]["id"]))
                    )
                )
            )
            == 1
        )
        with pytest.raises(ValueError, match="scope mismatch"):
            assessment_privacy.replay_revocations(
                session, [{"profile_id": str(uuid4()), "grant_id": x["grant"]["id"]}]
            )


@pytest.mark.parametrize(
    "rows",
    [
        None,
        {},
        [None],
        [{"profile_id": None, "grant_id": None}],
        [{"profile_id": "bad", "grant_id": "bad"}],
        [{"profile_id": str(uuid4()), "grant_id": str(uuid4()), "answers": "forbidden"}],
    ],
)
def test_revocation_schema_is_identifier_only_and_fail_closed(rows):
    with pytest.raises(ValueError):
        assessment_privacy.validate_revocations(rows)


def test_duplicate_revocations_rejected():
    row = {"profile_id": str(uuid4()), "grant_id": str(uuid4())}
    with pytest.raises(ValueError, match="Duplicate"):
        assessment_privacy.validate_revocations([row, row])


def test_signed_manifest_v4_contains_only_identifier_revocations(assessment, tmp_path):
    from app.privacy_ops.restore import export_tombstones, read_manifest

    x = assessment
    ok(
        x["client"].put(
            API + "/panel/language-assessment-consent",
            headers=x["ph"],
            json=dict(
                decision="withdrawn",
                grant_id=x["grant"]["id"],
                document_version="1",
                presented_digest=assessments.CONSENT_DIGEST,
                receipt_key="manifest-withdraw",
            ),
        )
    )
    with x["app"].state.database.sessions() as session:
        path = tmp_path / "assessment-manifest.json"
        digest = export_tombstones(session, path, b"synthetic-signing-key-32-bytes-long")
    manifest = read_manifest(path, b"synthetic-signing-key-32-bytes-long", digest)
    assert manifest["version"] == 4
    assert {"profile_id": x["profile"], "grant_id": x["grant"]["id"]} in manifest[
        "assessment_revocations"
    ]
    for row in manifest["assessment_revocations"]:
        assert set(row) == {"profile_id", "grant_id"}


def test_physical_snapshot_replay_revokes_grant_and_purges_expired_evidence(
    assessment, migrated_database, db_engine, tmp_path, tmp_path_factory
):
    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import NullPool

    from app.privacy_ops.restore import copy_files, export_tombstones, replay, restore_ready

    x = assessment
    attempt = ok(begin(x, publish(x, synthetic=False)), 201)
    ok(submit(x, attempt))
    ok(decide(x, attempt))
    with x["app"].state.database.sessions.begin() as session:
        session.get(Attempt, UUID(attempt["id"])).retention_until = utcnow() - timedelta(seconds=1)
        assert assessments.current_qualifications(session, UUID(x["profile"]))
    source = make_url(migrated_database)
    assert source.database.endswith("_test")
    name = "c03_" + uuid4().hex + "_restore"
    target_url = source.set(database=name)
    source_files = x["app"].state.settings.private_root.resolve()
    target_files = tmp_path_factory.mktemp("assessment-snapshot").resolve() / "files_restore"
    copy_files(source_files, target_files)
    x["app"].state.database.engine.dispose()
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
        with Session(target) as session:
            assert assessments.current_qualifications(session, UUID(x["profile"]))
            assert session.get(Attempt, UUID(attempt["id"])).responses_json is not None
        ok(
            x["client"].put(
                API + "/panel/language-assessment-consent",
                headers=x["ph"],
                json=dict(
                    decision="withdrawn",
                    grant_id=x["grant"]["id"],
                    document_version="1",
                    presented_digest=assessments.CONSENT_DIGEST,
                    receipt_key="post-snapshot-revoke",
                ),
            )
        )
        key = b"synthetic-assessment-restore-key-32"
        path = tmp_path / "current-revocations.json"
        with Session(db_engine) as session:
            digest = export_tombstones(session, path, key)
        assert not restore_ready(target, target_files)
        for _ in range(2):
            replay(source, target_url, source_files, target_files, path, key, digest)
            assert restore_ready(target, target_files)
            with Session(target) as session:
                assert assessments.current_qualifications(session, UUID(x["profile"])) == []
                row = session.get(Attempt, UUID(attempt["id"]))
                assert row.state == "withdrawn" and row.responses_json is None
                assert row.purged_at is not None and row.submission_digest is None
                decision = session.scalar(select(Decision).where(Decision.attempt_id == row.id))
                assert decision.rationale is None and decision.findings_json is None
    finally:
        target.dispose()
        if created:
            with admin.connect() as conn:
                quote = conn.dialect.identifier_preparer.quote_identifier
                conn.exec_driver_sql(f"DROP DATABASE {quote(name)}")
        admin.dispose()

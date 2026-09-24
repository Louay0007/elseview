"""Complete-series acceptance is a single obligation, regardless of review order."""

import secrets
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_reviews_db import collected, decisions  # noqa: F401
from test_reviews_db import reviewed as reviewed_fixture

from app.auth.security import utcnow
from app.collection import service as collection
from app.collection.models import CollectionSession
from app.collection.schemas import AnswerBody, SubmitBody
from app.longitudinal import service
from app.longitudinal.schemas import DiaryBody, DiaryStartBody
from app.reviews import service as reviews
from app.reviews.models import LedgerTransaction, RewardRecord

pytestmark = pytest.mark.db
reviewed = reviewed_fixture


def test_complete_series_out_of_order_human_reviews_earn_exactly_once(
    reviewed,
    db_engine,
    monkeypatch,
):
    wid, base_id, owner, reviewers, subject = reviewed
    now = utcnow()
    windows = []
    for day in range(2):
        start = (now + timedelta(days=day, minutes=-1)).replace(tzinfo=None)
        windows.append(
            {
                "opens": {"local": start},
                "due": {"local": start + timedelta(minutes=10)},
                "grace": {"local": start + timedelta(minutes=20)},
            }
        )
    with Session(db_engine) as session, session.begin():
        occurrences = service.create_diary(
            session, wid, owner, DiaryBody(base_session_id=base_id, timezone="UTC", windows=windows)
        )
    children = []
    for day, occurrence in enumerate(occurrences):
        clock = now + timedelta(days=day)
        monkeypatch.setattr(service, "utcnow", lambda clock=clock: clock)
        monkeypatch.setattr(collection, "utcnow", lambda clock=clock: clock)
        with Session(db_engine) as session, session.begin():
            result = service.start_diary(
                session,
                subject,
                occurrence["id"],
                DiaryStartBody(capability=secrets.token_urlsafe(32)),
            )
            row = session.get(CollectionSession, UUID(result["session_id"]))
            collection.save_answer(
                session,
                row,
                "single",
                AnswerBody(
                    schema_version=1,
                    expected_revision=0,
                    client_event_id=uuid4(),
                    status="responded",
                    value={"option_id": "no"},
                ),
            )
            collection.submit(
                session, row, SubmitBody(version_id=row.version_id, expected_revision=1)
            )
            children.append(row.id)
    # Last chronological occurrence accepted first, initial baseline next,
    # then earlier occurrence last: only this last human consensus can earn.
    for index, sid in enumerate([children[1], base_id, children[0]]):
        with Session(db_engine) as session, session.begin():
            decisions(session, wid, sid, owner, reviewers)
            assert session.scalar(
                select(func.count())
                .select_from(RewardRecord)
                .where(RewardRecord.workspace_id == wid)
            ) == (1 if index == 2 else 0)
    with Session(db_engine) as session, session.begin():
        rewards = [
            reviews.earn(session, session.get(CollectionSession, sid))
            for sid in [base_id, *children, base_id]
        ]
        assert len({r.id for r in rewards}) == 1
        assert rewards[0].source_key == "accepted_v1:" + str(base_id)
        assert rewards[0].amount_millimes == 1000
        assert (
            session.scalar(
                select(func.count())
                .select_from(LedgerTransaction)
                .where(LedgerTransaction.workspace_id == wid)
            )
            == 1
        )

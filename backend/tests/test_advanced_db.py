"""P11 real PostgreSQL/API contracts. Execute only in lead-authorized DB window."""

import copy
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from research_support import document, upload
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from study_fixtures import ready_study

from app.analytics.metrics import reduce_block
from app.auth.models import User
from app.auth.security import token_hash, utcnow
from app.collection.models import Answer, AnswerRevision, CollectionSession, ResponseEvent
from app.common.privacy_models import ConsentDocument
from app.recruiting.models import (
    Candidate,
    Invitation,
    PanelConsent,
    ParticipantProfile,
    RecruitmentConfig,
)
from app.studies import methods
from app.studies.models import Launch

pytestmark = pytest.mark.db


def definitions(image, source):
    def labels(s):
        return {"fr": s, "ar": "نص " + s}

    options = [dict(id=k, label=labels(k)) for k in ["a", "b", "c"]]

    def ref(x):
        return dict(asset_id=x, asset_version=1)

    configs = [
        ("rank", "survey.ranking", dict(options=options, rank_count=2)),
        ("sum", "survey.constant_sum", dict(options=options, total_points=100)),
        (
            "click",
            "first_click",
            dict(
                asset_ref=ref(image),
                asset_width=2,
                asset_height=2,
                coordinate_space="normalized_asset",
                input_modes=["pointer", "keyboard_cursor"],
            ),
        ),
        (
            "cards",
            "card_sort",
            dict(mode="hybrid", cards=options, categories=options[:1], allow_unplaced=True),
        ),
        (
            "tree",
            "tree_test",
            dict(
                root_id="a",
                nodes=[
                    dict(o, parent_id=None if o["id"] == "a" else "a", selectable=o["id"] != "a")
                    for o in options
                ],
            ),
        ),
        (
            "issue",
            "accessibility.issue",
            dict(task_block_id="click", capture_context=True, criterion_refs=["contrast"]),
        ),
        (
            "language",
            "language.review",
            dict(
                source_asset_ref=ref(source),
                source_text="Texte original",
                source_language="fr",
                target_language="ar",
                rubric_version="v1",
                dimensions=[dict(id="accuracy", min=1, max=5)],
            ),
        ),
    ]
    blocks = [
        dict(block_key=k, type=t, schema_version=1, required=True, prompt=labels(k), config=c)
        for k, t, c in configs
    ]
    blocks[2]["evaluation"] = {
        "aois": [
            dict(
                id="SECRET_AOI",
                polygon=[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
                success=True,
            )
        ]
    }
    blocks[4]["evaluation"] = {"target_paths": [["a", "b"]]}
    return blocks


def value(block):
    return {
        "rank": {"ordered_option_ids": ["b", "a"]},
        "sum": {
            "allocations": [
                {"option_id": k, "points": n} for k, n in [("a", 0), ("b", 40), ("c", 60)]
            ]
        },
        "click": dict(
            block["config"].get("asset_ref", {}),
            x=0.5,
            y=0.5,
            elapsed_ms=20,
            input_mode="keyboard_cursor",
        ),
        "cards": {
            "groups": [{"group_id": "a", "card_ids": ["a", "b"]}],
            "unplaced_card_ids": ["c"],
        },
        "tree": dict(
            visited_node_ids=["a", "c", "a", "b"],
            selected_node_id="b",
            outcome="selected",
            elapsed_ms=100,
        ),
        "issue": {"issues": []},
        "language": dict(
            ratings=[dict(dimension_id="accuracy", value=4)],
            issues=[dict(quote="original", explanation=dict(text="Remarque", language="fr"))],
            rewrite=dict(text="نص", language="ar"),
        ),
    }[block["block_key"]]


@pytest.fixture
def advanced_study(research_app):
    client, app, actor = research_app
    headers, _, workspace = actor()
    base = f"/api/v1/workspaces/{workspace}"
    image = upload(client, base, headers)["asset"]["id"]
    source = upload(
        client, base, headers, content=b"Texte original", media_type="text/plain", extension="txt"
    )["asset"]["id"]
    blocks = definitions(image, source)
    fixture = ready_study(client, base, headers, blocks)
    return dict(
        client=client,
        app=app,
        actor=actor,
        headers=headers,
        workspace=workspace,
        base=base,
        blocks=blocks,
        fixture=fixture,
        image=image,
        source=source,
    )


def publish(s):
    r = s["client"].post(
        s["fixture"]["endpoint"] + "/publish", headers=s["headers"], json={"expected_revision": 2}
    )
    assert r.status_code == 200, r.text


def start(s, engine):
    raw = secrets.token_urlsafe(32)
    with Session(engine) as db, db.begin():
        user = User(
            email=f"p11-{uuid4().hex}@example.test", password_hash="synthetic", verified_at=utcnow()
        )
        db.add(user)
        db.flush()
        auth = {
            "Authorization": "Bearer " + s["app"].state.auth._new_login(db, user)["access_token"]
        }
        profile = ParticipantProfile(user_id=user.id)
        db.add(profile)
        db.flush()
        db.add(
            PanelConsent(
                profile_id=profile.id,
                decision="granted",
                document_version="1",
                document_digest="a" * 64,
                request_digest="a" * 64,
                receipt_key=uuid4().hex,
            )
        )
        launch = db.scalar(
            select(Launch).where(Launch.version_id == UUID(s["fixture"]["version_id"]))
        )
        if not db.scalar(select(RecruitmentConfig).where(RecruitmentConfig.launch_id == launch.id)):
            db.add(
                RecruitmentConfig(
                    workspace_id=s["workspace"],
                    launch_id=launch.id,
                    capacity=10,
                    budget_millimes=0,
                    reward_millimes=0,
                )
            )
        candidate = Candidate(
            workspace_id=s["workspace"],
            launch_id=launch.id,
            subject_id=user.id,
            source_kind="public",
            source_id=profile.id,
            status="eligible",
            attributes_json={},
        )
        db.add(candidate)
        db.flush()
        db.add(
            Invitation(
                workspace_id=s["workspace"],
                candidate_id=candidate.id,
                token_hash=token_hash(raw),
                expires_at=utcnow() + timedelta(hours=1),
            )
        )
        doc = db.get(ConsentDocument, UUID(s["fixture"]["body"]["consent_documents"]["fr"]))
        body = dict(
            invitation_token=raw,
            capability=secrets.token_urlsafe(32),
            locale="fr",
            document_id=str(doc.id),
            presented_digest=doc.digest,
            consent="granted",
        )
    r = s["client"].post("/api/v1/collection/sessions", headers=auth, json=body)
    assert r.status_code == 201, r.text
    data = r.json()
    return dict(
        url="/api/v1/collection/sessions/" + data["session_id"],
        headers={"X-Session-Token": body["capability"]},
        auth=auth,
        data=data,
    )


def put(s, p, block, v=None, revision=0):
    return s["client"].put(
        p["url"] + "/answers/" + block["block_key"],
        headers=p["headers"],
        json=dict(
            version_id=p["data"]["version_id"],
            schema_version=1,
            expected_revision=revision,
            client_event_id=str(uuid4()),
            status="responded",
            value=value(block) if v is None else v,
        ),
    )


def click_event(s, p, v=None, event_id=None):
    block = s["blocks"][2]
    body = dict(
        version_id=p["data"]["version_id"],
        events=[
            dict(
                block_key="click",
                event=dict(
                    kind="first_click.recorded",
                    client_event_id=event_id or str(uuid4()),
                    sequence=0,
                    elapsed_ms=20,
                    metadata=value(block) if v is None else v,
                ),
            )
        ],
    )
    return body


def reach(s, p, key):
    for b in s["blocks"]:
        if b["block_key"] == key:
            return
        if b["block_key"] == "click":
            r = s["client"].post(p["url"] + "/events", headers=p["headers"], json=click_event(s, p))
            assert r.status_code == 200, r.text
        r = put(s, p, b)
        assert r.status_code == 200, r.text


def test_all_seven_publish_preview_collect_reduce(advanced_study, db_engine):
    s = advanced_study
    publish(s)
    client = s["client"]
    r = client.post(
        s["fixture"]["endpoint"] + "/preview", headers=s["headers"], json={"locale": "fr"}
    )
    assert r.status_code == 200, r.text
    h = {"X-Preview-Token": r.json()["preview_token"]}
    answers = {}
    for expected in s["blocks"]:
        r = client.post("/api/v1/study-preview", headers=h, json={"answers": answers})
        assert r.status_code == 200, r.text
        b = r.json()["block"]
        assert b["type"] == expected["type"]
        assert "evaluation" not in b and "SECRET_AOI" not in r.text and "target_paths" not in r.text
        answers[b["block_key"]] = dict(status="responded", value=value(b))
    assert client.post("/api/v1/study-preview", headers=h, json={"answers": answers}).json()[
        "complete"
    ]
    with Session(db_engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(AnswerRevision)
                .join(CollectionSession, CollectionSession.id == AnswerRevision.session_id)
                .where(CollectionSession.version_id == UUID(s["fixture"]["version_id"]))
            )
            == 0
        )
    p = start(s, db_engine)
    for b in s["blocks"]:
        r = client.get(p["url"], headers=p["headers"])
        assert r.status_code == 200
        assert r.json()["block"]["type"] == b["type"] and "evaluation" not in r.json()["block"]
        assert "SECRET_AOI" not in r.text and "target_paths" not in r.text
        if b["block_key"] == "click":
            asset = client.get(p["url"] + "/assets/" + s["image"], headers=p["headers"])
            assert asset.status_code == 200
            assert put(s, p, b).status_code == 422
            event = click_event(s, p)
            r = client.post(p["url"] + "/events", headers=p["headers"], json=event)
            assert r.status_code == 200, r.text
            assert (
                client.post(p["url"] + "/events", headers=p["headers"], json=event).status_code
                == 200
            )
            assert client.get(p["url"], headers=p["headers"]).json()["block"][
                "first_click"
            ] == value(b)
            changed = value(b) | {"x": 0.2}
            assert put(s, p, b, changed).status_code == 422
        if b["block_key"] == "language":
            asset = client.get(p["url"] + "/assets/" + s["source"], headers=p["headers"])
            assert asset.status_code == 200 and asset.content == b"Texte original"
        r = put(s, p, b)
        assert r.status_code == 200, r.text
    r = client.post(
        p["url"] + "/submit",
        headers=p["headers"],
        json=dict(version_id=p["data"]["version_id"], expected_revision=7),
    )
    assert r.status_code == 200, r.text
    with Session(db_engine) as db:
        rows = list(
            db.scalars(
                select(AnswerRevision).where(
                    AnswerRevision.session_id == UUID(p["data"]["session_id"])
                )
            )
        )
        assert len(rows) == 7
        by_key = {db.get(Answer, row.answer_id).block_key: row for row in rows}
        for b in s["blocks"]:
            metric = reduce_block(methods.parse_block(b), [by_key[b["block_key"]].payload])
            assert metric["response"]["numerator"] == 1
            assert "Remarque" not in str(metric)
        assert (
            db.scalar(
                select(func.count())
                .select_from(ResponseEvent)
                .where(
                    ResponseEvent.session_id == UUID(p["data"]["session_id"]),
                    ResponseEvent.kind == "first_click.recorded",
                )
            )
            == 1
        )


@pytest.mark.parametrize("mutation", ["dimensions", "source", "foreign_asset"])
def test_publication_pinned_assets(advanced_study, mutation):
    s = advanced_study
    body = copy.deepcopy(s["fixture"]["body"])
    if mutation == "dimensions":
        body["blocks_json"][2]["config"]["asset_width"] = 3
    elif mutation == "source":
        body["blocks_json"][6]["config"]["source_text"] = "Forged source"
    else:
        headers, _, workspace = s["actor"]()
        foreign = upload(s["client"], f"/api/v1/workspaces/{workspace}", headers)["asset"]["id"]
        body["blocks_json"][2]["config"]["asset_ref"]["asset_id"] = foreign
    r = s["client"].put(s["fixture"]["endpoint"], headers=s["headers"], json=body)
    assert r.status_code == 200, r.text
    r = s["client"].post(
        s["fixture"]["endpoint"] + "/publish", headers=s["headers"], json={"expected_revision": 3}
    )
    assert r.status_code in {404, 422}, r.text


def test_first_click_concurrent_latch_and_sql_immutable(advanced_study, db_engine):
    s = advanced_study
    publish(s)
    p = start(s, db_engine)
    reach(s, p, "click")
    events = [click_event(s, p, value(s["blocks"][2]) | {"x": x}) for x in [0.25, 0.75]]

    def post(body):
        return s["client"].post(p["url"] + "/events", headers=p["headers"], json=body)

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(post, events))
    assert sorted(r.status_code for r in responses) == [200, 409]
    winner = events[next(i for i, r in enumerate(responses) if r.status_code == 200)]
    assert post(winner).status_code == 200
    latched = s["client"].get(p["url"], headers=p["headers"]).json()["block"]["first_click"]
    assert latched == winner["events"][0]["event"]["metadata"]
    assert put(s, p, s["blocks"][2], latched).status_code == 200
    with Session(db_engine) as db:
        rows = list(
            db.scalars(
                select(ResponseEvent).where(
                    ResponseEvent.session_id == UUID(p["data"]["session_id"]),
                    ResponseEvent.kind == "first_click.recorded",
                )
            )
        )
        assert len(rows) == 1
        with pytest.raises(DBAPIError):
            db.execute(
                text("UPDATE response_events SET payload='{}' WHERE id=:id"), {"id": rows[0].id}
            )
        db.rollback()


def test_optional_context_consent_and_foreign_evidence(advanced_study, db_engine):
    s = advanced_study
    publish(s)
    p = start(s, db_engine)
    reach(s, p, "issue")
    client = s["client"]
    b = s["blocks"][5]
    v = {
        "issues": [
            dict(
                description=dict(text="Obstacle", language="fr"),
                impact="blocked",
                context=dict(input_method="keyboard", assistive_technology="screen reader"),
            )
        ]
    }
    assert put(s, p, b, v).status_code == 422
    assert (
        client.get(p["url"], headers=p["headers"]).json()["block"]["context_consent_granted"]
        is False
    )
    doc = document(client, s["base"], s["headers"], purpose="accessibility_context")
    r = client.get(p["url"] + "/optional-consent?purpose=accessibility_context", headers=p["auth"])
    assert r.status_code == 200, r.text
    r = client.post(
        p["url"] + "/optional-consent",
        headers=p["auth"],
        json=dict(
            purpose="accessibility_context",
            document_id=doc["id"],
            presented_digest=doc["digest"],
            decision="granted",
            receipt_key=uuid4().hex,
        ),
    )
    assert r.status_code == 200, r.text
    assert (
        client.get(p["url"], headers=p["headers"]).json()["block"]["context_consent_granted"]
        is True
    )
    other = start(s, db_engine)
    assert (
        client.get(
            p["url"] + "/optional-consent?purpose=accessibility_context", headers=other["auth"]
        ).status_code
        == 404
    )
    h, _, w = s["actor"]()
    foreign = upload(client, f"/api/v1/workspaces/{w}", h, purpose="attachment")["asset"]["id"]
    bad = copy.deepcopy(v)
    bad["issues"][0]["evidence_asset_ref"] = dict(asset_id=foreign, asset_version=1)
    assert put(s, p, b, bad).status_code == 422
    assert put(s, p, b, v).status_code == 200
    r = client.post(
        p["url"] + "/optional-consent",
        headers=p["auth"],
        json=dict(
            purpose="accessibility_context",
            document_id=doc["id"],
            presented_digest=doc["digest"],
            decision="withdrawn",
            receipt_key=uuid4().hex,
        ),
    )
    assert r.status_code == 200, r.text
    assert put(s, p, b, v, revision=1).status_code == 422


def test_each_method_rejects_invalid_api_answer(advanced_study, db_engine):
    s = advanced_study
    publish(s)
    p = start(s, db_engine)
    invalid = {
        "rank": {"ordered_option_ids": ["a", "a"]},
        "sum": {
            "allocations": [
                {"option_id": k, "points": n} for k, n in [("a", 0), ("b", 40), ("c", 59)]
            ]
        },
        "click": value(s["blocks"][2]) | {"x": 1.001},
        "cards": {
            "groups": [{"group_id": "a", "card_ids": ["a", "a", "b"]}],
            "unplaced_card_ids": ["c"],
        },
        "tree": {
            "visited_node_ids": ["a", "b", "c"],
            "selected_node_id": "c",
            "outcome": "selected",
            "elapsed_ms": 30,
        },
        "issue": {
            "issues": [
                {
                    "description": {"text": "barrier", "language": "fr"},
                    "impact": "blocked",
                    "criterion_ref": "unknown",
                }
            ]
        },
        "language": {
            "ratings": [{"dimension_id": "accuracy", "value": 4}],
            "issues": [{"quote": "fabricated", "explanation": {"text": "note", "language": "fr"}}],
        },
    }
    for b in s["blocks"]:
        r = put(s, p, b, invalid[b["block_key"]])
        assert r.status_code == 422, (b["type"], r.text)
        if b["block_key"] == "click":
            bad = click_event(s, p, invalid["click"])
            assert (
                s["client"].post(p["url"] + "/events", headers=p["headers"], json=bad).status_code
                == 422
            )
            assert (
                s["client"].get(p["url"], headers=p["headers"]).json()["block"]["first_click"]
                is None
            )
            r = s["client"].post(p["url"] + "/events", headers=p["headers"], json=click_event(s, p))
            assert r.status_code == 200, r.text
        r = put(s, p, b)
        assert r.status_code == 200, r.text


def test_first_click_partial_index_and_private_event_access(advanced_study, db_engine):
    s = advanced_study
    publish(s)
    p = start(s, db_engine)
    reach(s, p, "click")
    r = s["client"].post(p["url"] + "/events", headers=p["headers"], json=click_event(s, p))
    assert r.status_code == 200, r.text
    other = start(s, db_engine)
    assert s["client"].get(p["url"], headers=other["headers"]).status_code == 404
    with Session(db_engine) as db:
        original = db.scalar(
            select(ResponseEvent).where(
                ResponseEvent.session_id == UUID(p["data"]["session_id"]),
                ResponseEvent.kind == "first_click.recorded",
            )
        )
        with pytest.raises(DBAPIError):
            db.add(
                ResponseEvent(
                    session_id=original.session_id,
                    block_key="click",
                    client_event_id=uuid4(),
                    sequence=2,
                    kind=original.kind,
                    provenance=original.provenance,
                    payload=original.payload,
                )
            )
            db.flush()
        db.rollback()


@pytest.mark.parametrize(
    "mutation", ["polygon", "target", "cycle", "rank", "sum", "category", "rubric"]
)
def test_publication_advanced_semantic_guards(advanced_study, mutation):
    s = advanced_study
    body = copy.deepcopy(s["fixture"]["body"])
    blocks = body["blocks_json"]
    if mutation == "polygon":
        blocks[2]["evaluation"]["aois"][0]["polygon"] = [
            [0.0, 0.0],
            [1.0, 1.0],
            [0.0, 1.0],
            [1.0, 0.0],
        ]
    elif mutation == "target":
        blocks[4]["evaluation"]["target_paths"] = [["a", "b", "c"]]
    elif mutation == "cycle":
        blocks[4]["config"]["nodes"][1]["parent_id"] = "c"
        blocks[4]["config"]["nodes"][2]["parent_id"] = "b"
    elif mutation == "rank":
        blocks[0]["config"]["rank_count"] = 4
    elif mutation == "sum":
        blocks[1]["config"]["total_points"] = True
    elif mutation == "category":
        blocks[3]["config"]["mode"] = "open"
    else:
        blocks[6]["config"]["dimensions"][0]["min"] = 5
    r = s["client"].put(s["fixture"]["endpoint"], headers=s["headers"], json=body)
    # Strict configs cannot enter a draft, hence cannot be published.
    assert r.status_code == 422, r.text

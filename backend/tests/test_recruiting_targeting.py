"""Isolated targeting contracts; no database or network required."""

import json
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.auth.security import utcnow
from app.common.errors import DomainError
from app.recruiting import service
from app.recruiting.models import ParticipantProfile, PrivateContact, PrivateContactConsent
from app.recruiting.router import panel_document, router, targeting_vocabulary
from app.recruiting.schemas import Attributes, ConfigBody, Filters, ImportBody, PanelBody

EXPERIENCE = {"version": "1", "categories": {"software": "advanced", "research": "beginner"}}
TARGETING = {"country_id": "TN", "city_id": "geonames:2464470", "experience": EXPERIENCE}


@pytest.mark.parametrize("schema", [Attributes, Filters])
@pytest.mark.parametrize(
    "values",
    [
        {},
        {"country_id": None},
        {"country_id": "TN"},
        TARGETING,
        {"experience": {"version": "1", "categories": {"design": "intermediate"}}},
    ],
)
def test_targeting_schema_valid(schema, values):
    parsed = schema.model_validate(values).model_dump()
    assert all(parsed[key] == values.get(key) for key in service.TARGETING_FIELDS)


@pytest.mark.parametrize("schema", [Attributes, Filters])
@pytest.mark.parametrize(
    "values",
    [
        {"country_id": "tn"},
        {"country_id": "ZZ"},
        {"country_id": "Tunisia"},
        {"country_id": 12},
        {"city_id": "geonames:2464470"},
        {"country_id": "TN", "city_id": "Tunis"},
        {"country_id": "TN", "city_id": "geonames:0"},
        {"country_id": "TN", "city_id": "geonames:12345678901"},
        {"experience": {"version": "2", "categories": {"software": "advanced"}}},
        {"experience": {"categories": {"software": "advanced"}}},
        {"experience": {"version": "1", "categories": {}}},
        {"experience": {"version": "1", "categories": {"secret": "advanced"}}},
        {"experience": {"version": "1", "categories": {"software": "expert"}}},
        {"experience": {"version": "1", "categories": {"software": None}}},
        {"experience": {"version": "1", "categories": {"software": "advanced"}, "verified": True}},
        {"_targeting_provenance": {"source": "verified"}},
    ],
)
def test_targeting_schema_rejects_unbounded_or_forged_values(schema, values):
    with pytest.raises(ValidationError):
        schema.model_validate(values)


@pytest.mark.parametrize(
    "attrs,filters,expected",
    [
        ({}, {}, True),
        ({}, {"country_id": "TN"}, False),
        ({"country_id": None}, {"country_id": "TN"}, False),
        (TARGETING, {"country_id": "FR"}, False),
        (TARGETING, {"country_id": "TN"}, True),
        (TARGETING, {"country_id": "TN", "city_id": "geonames:2464470"}, True),
        (TARGETING, {"country_id": "TN", "city_id": "geonames:2988507"}, False),
        (TARGETING, {"experience": EXPERIENCE}, True),
        ({}, {"experience": EXPERIENCE}, False),
        ({"experience": None}, {"experience": EXPERIENCE}, False),
        (
            {"experience": {"version": "2", "categories": EXPERIENCE["categories"]}},
            {"experience": EXPERIENCE},
            False,
        ),
        (
            TARGETING,
            {"experience": {"version": "1", "categories": {"software": "beginner"}}},
            False,
        ),
        (TARGETING, {"experience": {"version": "1", "categories": {"software": "advanced"}}}, True),
        (
            TARGETING,
            {
                "experience": {
                    "version": "1",
                    "categories": {"software": "advanced", "design": "advanced"},
                }
            },
            False,
        ),
        (TARGETING, {"verified_language": "fr"}, False),
        (TARGETING | {"age": 30}, {"country_id": "TN", "min_age": 40}, False),
        ({"languages": ["ar"], "devices": ["mobile"]}, {"country_id": "TN"}, False),
        ({"experience": {"version": "future"}}, {}, True),
    ],
)
def test_targeting_match_is_exact_intersection_and_unknown_is_not_inferred(
    attrs, filters, expected
):
    assert service.matches(attrs, filters) is expected


def test_config_and_intersecting_quotas_share_versioned_filters():
    body = ConfigBody(
        capacity=10,
        budget_millimes=100,
        reward_millimes=0,
        filters=TARGETING,
        quotas=[
            {"capacity": 1, "filters": {"country_id": "TN"}},
            {"capacity": 1, "filters": {"experience": EXPERIENCE}},
        ],
    )
    assert service.matches(TARGETING, body.filters.model_dump())
    assert all(service.matches(TARGETING, quota.filters.model_dump()) for quota in body.quotas)


def test_import_mapping_normalizes_without_inference():
    parsed = service.parse_import_attributes(
        {
            "nation": " TN ",
            "city": " geonames:2464470 ",
            "work": json.dumps(EXPERIENCE),
            "age": "30",
            "devices": "mobile, desktop",
            "languages": "fr, ar",
        },
        {
            "country_id": "nation",
            "city_id": "city",
            "experience": "work",
            "age": "age",
            "devices": "devices",
            "languages": "languages",
        },
    )
    assert parsed == TARGETING | {
        "age": 30,
        "devices": ["mobile", "desktop"],
        "languages": ["fr", "ar"],
    }
    empty = service.parse_import_attributes(
        {"nation": "  "}, {"country_id": "nation", "experience": "work"}
    )
    assert all(empty[key] is None for key in service.TARGETING_FIELDS)


@pytest.mark.parametrize(
    "cell",
    [
        "not JSON",
        "[]",
        "{}",
        "[" * 3000,
        '"' + "a" * 2049 + '"',
        '{"version":"1","categories":{"software":"expert"}}',
    ],
    ids=["invalid-json", "array", "empty-object", "too-deep", "too-large", "invalid-level"],
)
def test_import_rejects_malformed_and_oversized_experience(cell):
    with pytest.raises(DomainError, match="INVALID_ATTRIBUTES") as error:
        service.parse_import_attributes({"work": cell}, {"experience": "work"})
    assert error.value.code == "INVALID_ATTRIBUTES"


def test_import_explicit_null_experience_is_unknown():
    assert (
        service.parse_import_attributes({"work": "null"}, {"experience": "work"})["experience"]
        is None
    )


def panel_body(version="2", attributes=None, **overrides):
    doc = panel_document(version)
    return PanelBody(
        **(
            {
                "attributes": TARGETING if attributes is None else attributes,
                "decision": "granted",
                "document_version": version,
                "presented_digest": doc["digest"],
                "receipt_key": "synthetic-receipt",
            }
            | overrides
        )
    )


def test_legacy_receipt_digest_is_unchanged():
    body = panel_body("1", {"age": 30})
    old_payload = body.model_dump()
    old_payload["attributes"] = {"age": 30, "devices": [], "languages": []}
    assert service.panel_request_digest(body) == service.digest(old_payload)


def test_legacy_consent_cannot_authorize_new_targeting():
    session = Mock()
    with pytest.raises(DomainError) as error:
        service.panel_update(session, uuid4(), panel_body("1"))
    assert error.value.code == "TARGETING_CONSENT_REQUIRED"
    session.scalar.assert_not_called()


def test_new_consent_cannot_reuse_legacy_digest():
    with pytest.raises(DomainError) as error:
        service.panel_update(Mock(), uuid4(), panel_body(presented_digest=service.PANEL_DIGEST))
    assert error.value.code == "CONSENT_DOCUMENT_MISMATCH"


def test_public_provenance_is_server_owned_and_profile_attributes_roundtrip():
    profile = ParticipantProfile(id=uuid4(), user_id=uuid4(), status="active", attributes_json={})
    session = Mock()
    session.scalar.side_effect = [object(), profile, None]
    body = panel_body()
    assert service.panel_update(session, profile.user_id, body) is profile
    output = service.profile_output(profile)
    assert (
        Attributes.model_validate(output["attributes"]).experience.categories
        == EXPERIENCE["categories"]
    )
    assert output["targeting_provenance"]["source"] == "self_reported"
    assert (
        output["targeting_provenance"]["consent"]["document_digest"]
        == service.PANEL_TARGETING_DIGEST
    )
    output["attributes"]["experience"]["categories"]["software"] = "beginner"
    assert profile.attributes_json["experience"]["categories"]["software"] == "advanced"
    receipt = session.add.call_args.args[0]
    assert receipt.document_version == "2"
    assert receipt.request_digest == service.panel_request_digest(body)


def test_legacy_consent_replay_does_not_mutate_profile():
    profile = ParticipantProfile(
        id=uuid4(), user_id=uuid4(), status="active", attributes_json={"age": 30}
    )
    body = panel_body("1", {"age": 30})
    session = Mock()
    session.scalar.side_effect = [
        object(),
        profile,
        SimpleNamespace(request_digest=service.panel_request_digest(body)),
    ]
    assert service.panel_update(session, profile.user_id, body) is profile
    assert profile.attributes_json == {"age": 30}
    session.add.assert_not_called()


def test_v2_withdrawal_clears_attributes_and_provenance():
    profile = ParticipantProfile(
        id=uuid4(), user_id=uuid4(), status="active", attributes_json=TARGETING.copy()
    )
    session = Mock()
    session.scalar.side_effect = [object(), profile, None]
    service.panel_update(session, profile.user_id, panel_body(decision="withdrawn"))
    assert profile.status == "withdrawn"
    assert profile.attributes_json == {}


def import_setup(monkeypatch, *, preview=True, **overrides):
    workspace, user, document = uuid4(), uuid4(), uuid4()
    doc = SimpleNamespace(id=document, purpose="private_panel", digest="a" * 64)
    monkeypatch.setattr(service, "lock_workspace", Mock())
    monkeypatch.setattr(service, "require_workspace", Mock())
    monkeypatch.setattr(service, "get_scoped", Mock(return_value=doc))
    consent = {
        "version": "1",
        "purpose": "private_panel_targeting",
        "confirmed": True,
        "presented_digest": service.PRIVATE_TARGETING_DIGEST,
        "document_digest": doc.digest,
    }
    body = ImportBody.model_validate(
        {
            "rows": [
                {"mail": "hello@example.test", "country": "TN", "work": json.dumps(EXPERIENCE)}
            ],
            "mapping": {"email": "mail", "country_id": "country", "experience": "work"},
            "source": "synthetic",
            "consent_confirmed": True,
            "document_id": document,
            "retention_until": utcnow() + timedelta(days=30),
            "preview": preview,
            "targeting_consent": consent,
        }
        | overrides
    )
    session = Mock()
    session.scalar.return_value = None
    settings = SimpleNamespace(secret_key=SimpleNamespace(get_secret_value=lambda: "synthetic-key"))
    return session, settings, workspace, user, body, doc


@pytest.mark.parametrize("preview", [True, False])
def test_private_targeting_consent_is_required_in_preview_and_import(monkeypatch, preview):
    session, settings, w, user, body, _ = import_setup(
        monkeypatch, preview=preview, targeting_consent=None
    )
    with pytest.raises(DomainError) as error:
        service.import_contacts(session, settings, w, user, body)
    assert error.value.code == "TARGETING_CONSENT_REQUIRED"
    session.add.assert_not_called()


@pytest.mark.parametrize("field", ["document_digest", "presented_digest"])
def test_private_targeting_consent_binds_both_documents(monkeypatch, field):
    session, settings, w, user, body, _ = import_setup(monkeypatch)
    setattr(body.targeting_consent, field, "0" * 64)
    with pytest.raises(DomainError) as error:
        service.import_contacts(session, settings, w, user, body)
    assert error.value.code == "CONSENT_DOCUMENT_MISMATCH"
    session.add.assert_not_called()


@pytest.mark.parametrize("preview", [True, False])
def test_private_preview_and_import_use_same_targeting_and_workspace_provenance(
    monkeypatch, preview
):
    session, settings, w, user, body, doc = import_setup(monkeypatch, preview=preview)
    result = service.import_contacts(session, settings, w, user, body)
    assert result["accepted"] == 1
    assert result["targeting_summary"] == {
        "country_id": {"known": 1, "unknown": 0},
        "city_id": {"known": 0, "unknown": 1},
        "experience": {"known": 1, "unknown": 0},
    }
    assert "hello@example.test" not in str(result)
    if preview:
        session.add.assert_not_called()
    else:
        contact, receipt = [call.args[0] for call in session.add.call_args_list]
        assert isinstance(contact, PrivateContact) and isinstance(receipt, PrivateContactConsent)
        assert contact.attributes_json["experience"] == EXPERIENCE
        provenance = contact.attributes_json["_targeting_provenance"]
        assert provenance["workspace_id"] == str(w)
        assert provenance["imported_by"] == str(user)
        assert provenance["consent"]["document_id"] == str(doc.id)
        assert provenance["source"] == "workspace_import"
        assert not hasattr(contact, "user_id")


def test_legacy_import_unknowns_do_not_need_targeting_consent(monkeypatch):
    session, settings, w, user, body, _ = import_setup(
        monkeypatch,
        targeting_consent=None,
        rows=[{"mail": "hello@example.test"}],
    )
    result = service.import_contacts(session, settings, w, user, body)
    assert all(
        counts == {"known": 0, "unknown": 1} for counts in result["targeting_summary"].values()
    )


def test_targeting_http_vocabulary_and_versioned_consent_contract():
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        assert client.get("/api/v1/panel/consent").json()["version"] == "1"
        assert (
            client.get("/api/v1/panel/consent?version=2").json()["digest"]
            == service.PANEL_TARGETING_DIGEST
        )
        assert client.get("/api/v1/panel/consent?version=3").status_code == 422
        assert (
            client.get("/api/v1/recruiting/targeting-vocabulary").json() == targeting_vocabulary()
        )
        schemas = client.get("/openapi.json").json()["components"]["schemas"]
        assert schemas["PanelBody"]["properties"]["document_version"]["enum"] == ["1", "2"]
        assert "targeting_consent" in schemas["ImportBody"]["properties"]
        assert "experience" in schemas["Filters"]["properties"]


def test_invitation_deep_copies_nested_source_snapshot(monkeypatch):
    from app.recruiting.schemas import InviteBody

    monkeypatch.setattr(service, "manage_launch", Mock())
    monkeypatch.setattr(
        service, "config_for", Mock(return_value=SimpleNamespace(filters_json={}, screener_json={}))
    )
    attrs = Attributes.model_validate(TARGETING).model_dump()
    attrs["_targeting_provenance"] = {"source": "workspace_import", "consent": {"version": "1"}}
    monkeypatch.setattr(service, "source_attributes", Mock(return_value=(attrs, None)))
    session = Mock()
    session.scalar.return_value = None
    _, candidate, _ = service.issue_invitation(
        session, uuid4(), uuid4(), uuid4(), InviteBody(source_kind="private", source_id=uuid4())
    )
    attrs["experience"]["categories"]["software"] = "beginner"
    attrs["_targeting_provenance"]["consent"]["version"] = "changed"
    assert candidate.attributes_json["experience"]["categories"]["software"] == "advanced"
    assert candidate.attributes_json["_targeting_provenance"]["consent"]["version"] == "1"


def test_vocabulary_explains_unknowns_exact_levels_and_consent():
    vocabulary = targeting_vocabulary()
    assert len(vocabulary["country_ids"]) == 249
    assert vocabulary["experience_scope"] == "self_reported_not_verified_credentials"
    assert vocabulary["private_targeting_consent"]["digest"] == service.PRIVATE_TARGETING_DIGEST
    assert panel_document()["digest"] == service.PANEL_DIGEST
    assert panel_document("2")["digest"] == service.PANEL_TARGETING_DIGEST

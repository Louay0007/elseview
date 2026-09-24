from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import TypeAdapter, ValidationError

from app.analytics.router import ReportIndexResponse
from app.collaboration.router import NotificationPreferenceResponse
from app.recruiting.schemas import InvitationDeliveryResponse, RecruitmentInvitationResponse

pytestmark = pytest.mark.unit


def test_report_index_projects_only_typed_metadata():
    report_id = uuid4()
    page = ReportIndexResponse.model_validate(
        {
            "items": [
                {
                    "id": str(report_id),
                    "revision": 2,
                    "state": "approved",
                    "raw_answers": ["must not leave this projection"],
                }
            ],
            "has_more": False,
            "source_ids": [str(uuid4())],
        }
    )
    assert page.model_dump(mode="json") == {
        "items": [{"id": str(report_id), "revision": 2, "state": "approved"}],
        "has_more": False,
    }
    with pytest.raises(ValidationError):
        ReportIndexResponse.model_validate(
            {
                "items": [{"id": str(report_id), "revision": 0, "state": "approved"}],
                "has_more": False,
            }
        )


def test_preferences_project_both_independent_choices():
    assert NotificationPreferenceResponse.model_validate(
        {"reminders": False, "email_reminders": True, "recipient_address": "hidden"}
    ).model_dump() == {"reminders": False, "email_reminders": True}
    assert InvitationDeliveryResponse(status="queued").model_dump() == {"status": "queued"}


@pytest.mark.parametrize("delivery,token", [("manual", "synthetic-capability"), ("queued", None)])
def test_invitation_union_preserves_wire_fields_and_timestamp(delivery, token):
    stamp = datetime(2026, 9, 24, 12, tzinfo=UTC)
    payload = {
        "invitation_id": str(uuid4()),
        "candidate_id": str(uuid4()),
        "invitation_token": token,
        "expires_at": stamp,
        "delivery": delivery,
    }
    adapter = TypeAdapter(RecruitmentInvitationResponse)
    projected = adapter.validate_python({**payload, "recipient_address": "hidden"})
    assert adapter.dump_python(projected, mode="json") == {
        **payload,
        "expires_at": stamp.isoformat(),
    }


@pytest.mark.parametrize("delivery,token", [("queued", "must-not-leak"), ("manual", None)])
def test_invitation_delivery_cannot_mislabel_capability_projection(delivery, token):
    with pytest.raises(ValidationError):
        TypeAdapter(RecruitmentInvitationResponse).validate_python(
            {
                "invitation_id": str(uuid4()),
                "candidate_id": str(uuid4()),
                "invitation_token": token,
                "expires_at": datetime.now(UTC),
                "delivery": delivery,
            }
        )

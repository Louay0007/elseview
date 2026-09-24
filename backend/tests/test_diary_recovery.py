import secrets

import pytest
from pydantic import ValidationError

from app.longitudinal.schemas import DiaryRecoverBody

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("revision", [-1, True, "0", 1.5, None])
def test_recovery_requires_observed_strict_nonnegative_revision(revision):
    with pytest.raises(ValidationError):
        DiaryRecoverBody(capability=secrets.token_urlsafe(32), expected_revision=revision)


@pytest.mark.parametrize("capability", ["short", "x" * 129, "x" * 42 + "+", "x" * 42 + " "])
def test_recovery_capability_is_bounded_base64url(capability):
    with pytest.raises(ValidationError):
        DiaryRecoverBody(capability=capability, expected_revision=0)


def test_recovery_rejects_client_owned_identity_and_locale():
    with pytest.raises(ValidationError):
        DiaryRecoverBody(capability=secrets.token_urlsafe(32), expected_revision=0, locale="ar")

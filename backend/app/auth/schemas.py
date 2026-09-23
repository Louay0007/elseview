import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


def normalize_email(value: str) -> str:
    value = value.strip().casefold()
    if len(value) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        raise ValueError("Invalid email")
    return value


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class EmailBody(StrictSchema):
    email: str = Field(max_length=254)
    _email = field_validator("email")(normalize_email)


class LoginBody(EmailBody):
    password: SecretStr = Field(min_length=1, max_length=256)


class RegisterBody(LoginBody):
    display_name: str = Field(default="", max_length=100)
    password: SecretStr = Field(min_length=12, max_length=256)


class TokenBody(StrictSchema):
    token: SecretStr = Field(min_length=20, max_length=256)


class ResetBody(TokenBody):
    password: SecretStr = Field(min_length=12, max_length=256)


class WorkspaceBody(StrictSchema):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Name cannot be blank")
        return value.strip()


class InviteBody(EmailBody):
    role: Literal["admin", "researcher", "reviewer", "viewer"]


class MemberBody(StrictSchema):
    role: Literal["owner", "admin", "researcher", "reviewer", "viewer"]

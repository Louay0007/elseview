from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


# Identifiers are not inferred from IP, language or an imported address. City/country
# association is supplied by the participant/importer, not geographically verified.
COUNTRY_IDS = frozenset(
    "AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO "
    "BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ "
    "DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP "
    "GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG "
    "KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML "
    "MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE "
    "PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL "
    "SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM "
    "US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW".split()
)
ExperienceCategory = Literal[
    "software",
    "design",
    "research",
    "business",
    "education",
    "healthcare",
    "finance",
    "manufacturing",
    "retail",
    "hospitality",
]
ExperienceLevel = Literal["beginner", "intermediate", "advanced"]


class Experience(Strict):
    """Self-reported familiarity, never a qualification or professional credential."""

    version: Literal["1"]
    categories: dict[ExperienceCategory, ExperienceLevel] = Field(min_length=1, max_length=10)


class Targeting(Strict):
    country_id: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    city_id: str | None = Field(default=None, pattern=r"^geonames:[1-9][0-9]{0,9}$")
    experience: Experience | None = None

    @model_validator(mode="after")
    def identifiers(self):
        if self.country_id is not None and self.country_id not in COUNTRY_IDS:
            raise ValueError("unknown country identifier")
        if self.city_id is not None and self.country_id is None:
            raise ValueError("city identifier requires country identifier")
        return self


class Attributes(Targeting):
    age: int | None = Field(default=None, ge=18, le=120)
    devices: list[Literal["mobile", "desktop", "tablet"]] = Field(
        default_factory=list, max_length=3
    )
    languages: list[str] = Field(default_factory=list, max_length=10)


class Filters(Targeting):
    min_age: int | None = Field(default=None, ge=18, le=120)
    max_age: int | None = Field(default=None, ge=18, le=120)
    device: Literal["mobile", "desktop", "tablet"] | None = None
    language: str | None = Field(default=None, max_length=35)
    verified_language: str | None = Field(default=None, max_length=35)

    @model_validator(mode="after")
    def compatible(self):
        if self.min_age is not None and self.max_age is not None and self.min_age > self.max_age:
            raise ValueError("incompatible age range")
        return self


class PanelBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    attributes: Attributes = Field(default_factory=Attributes)
    decision: Literal["granted", "withdrawn"]
    document_version: Literal["1", "2"]
    presented_digest: str = Field(min_length=64, max_length=64)
    receipt_key: str = Field(min_length=1, max_length=128)


class PrivateTargetingConsent(Strict):
    version: Literal["1"]
    purpose: Literal["private_panel_targeting"]
    confirmed: Literal[True]
    presented_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    document_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class ImportBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rows: list[dict[str, str]] = Field(min_length=1, max_length=500)
    mapping: dict[str, str]
    source: str = Field(min_length=1, max_length=200)
    consent_confirmed: Literal[True]
    document_id: UUID
    retention_until: datetime
    duplicate_policy: Literal["skip", "reject"] = "skip"
    preview: bool = True
    targeting_consent: PrivateTargetingConsent | None = None


class ScreenerQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(min_length=1, max_length=500)
    options: list[str] = Field(min_length=2, max_length=20)
    eligible_options: list[str] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def choices(self):
        if len(set(self.options)) != len(self.options) or not set(self.eligible_options) <= set(
            self.options
        ):
            raise ValueError("invalid screener choices")
        return self


class QuotaBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    capacity: int = Field(ge=1, le=100000)
    filters: Filters = Field(default_factory=Filters)


class ConfigBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    capacity: int = Field(ge=1, le=100000)
    budget_millimes: int = Field(ge=0, le=10**12)
    reward_millimes: int = Field(ge=0, le=10**9)
    hold_seconds: int = Field(default=1800, ge=60, le=86400)
    filters: Filters = Field(default_factory=Filters)
    screeners: dict[str, ScreenerQuestion] = Field(default_factory=dict, max_length=20)
    quotas: list[QuotaBody] = Field(default_factory=list, max_length=20)
    screening_policy: Literal["uncompensated_disclosed"] = "uncompensated_disclosed"


class InviteBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_kind: Literal["public", "private"]
    source_id: UUID
    expires_seconds: int = Field(default=86400, ge=60, le=604800)


class ScreenBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answers: dict[str, str] = Field(default_factory=dict, max_length=20)


class QualificationBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: Literal["fr", "en", "ar"]
    assessment_version: Literal["development-basic-v1"]
    answers: list[str] = Field(min_length=2, max_length=2)


class PublicRecruitBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    count: int = Field(ge=1, le=50)
    filters: Filters = Field(default_factory=Filters)
    expires_seconds: int = Field(default=86400, ge=60, le=604800)

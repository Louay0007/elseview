"""Recipe v1 is frozen configuration, not a separate response implementation."""

import copy
import hashlib

from app.common.cache import canonical_json
from app.common.errors import DomainError
from app.studies.methods import RENDERERS

LOCALES = ("aeb", "fr", "ar", "aeb-Latn")
# Locale names are explicit: aeb = Tunisian Arabic; aeb-Latn = Arabizi.
FAMILIES = {
    "product_discovery": ("concept", "pricing", "competitor", "feature_ranking"),
    "product_journey": ("onboarding", "checkout", "registration", "full_journey"),
    "marketing": ("ad_message", "landing_page", "video", "audience", "brand", "prelaunch_offer"),
    "business": ("forms", "policies", "support_scripts", "packages", "market_entry"),
    "localization": ("tunisian_arabic", "french", "formal_arabic", "arabizi"),
}
LANGUAGE = dict(zip(FAMILIES["localization"], LOCALES, strict=True))
COMPARE = {"pricing", "competitor", "ad_message", "brand", "prelaunch_offer", "packages"}
BASE_CAVEATS = [
    "Descriptive research only; no causal conversion or population-level claims.",
    "Task completion is self-reported, not instrumented production behavior.",
    "Visual methods require authorized PNG assets; language review requires pinned UTF-8 text. No external browsing or video playback.",
    "Caller must provide approved translations and qualified reviewers; approval references are attestations, not platform certification.",
]


def _recipe(key, family):
    kind = (
        "preference" if key in COMPARE else "survey.ranking" if key == "feature_ranking" else None
    )
    caveats = list(BASE_CAVEATS)
    if key == "pricing":
        caveats.append(
            "Stated willingness to pay is not a purchase commitment or validated demand."
        )
    if key == "video":
        caveats.append(
            "Storyboard/key-frame content evaluation proxy only: no video playback, timing, audio or watch-through measurement."
        )
    if family == "localization":
        caveats.append(
            "Original-language quotes require qualified human review; dialect quality is not automatically scored."
        )
    tasks = ["task_" + str(i) for i in range(1, 5)] if key == "full_journey" else ["task_1"]
    specs = [{"block_key": task, "type": "prototype.task"} for task in tasks]
    if family == "localization":
        specs = [{"block_key": "language", "type": "language.review"}]
    if family == "marketing":
        specs += [{"block_key": "recall", "type": "survey.text"}]
        caveats.append(
            "Recall is self-reported after asset review, not a timed five-second exposure metric."
        )
    objectives = {
        "concept": "concept_understanding",
        "pricing": "willingness_to_pay",
        "competitor": "competitive_difference",
        "feature_ranking": "priority_reason",
        "onboarding": "first_value_barrier",
        "checkout": "payment_trust",
        "registration": "registration_friction",
        "full_journey": "journey_breakpoint",
        "ad_message": "message_takeaway",
        "landing_page": "value_proposition",
        "video": "storyboard_comprehension",
        "audience": "audience_relevance",
        "brand": "brand_association",
        "prelaunch_offer": "offer_expectation",
        "forms": "field_comprehension",
        "policies": "policy_comprehension",
        "support_scripts": "resolution_comprehension",
        "packages": "package_tradeoff",
        "market_entry": "local_market_fit",
    }
    if key in objectives:
        specs.append({"block_key": objectives[key], "type": "survey.text"})
    if kind:
        specs.append({"block_key": "comparison", "type": kind})
    specs += [
        {"block_key": "clarity", "type": "survey.rating"},
        {"block_key": "explanation", "type": "survey.text"},
    ]
    return {
        "key": key,
        "version": 1,
        "family": family,
        "locales": [LANGUAGE[key]] if key in LANGUAGE else list(LOCALES),
        "blocks": specs,
        "methods": sorted({s["type"] for s in specs}),
        "caveats": caveats,
        "required_inputs": {
            "language_review": "For localization only: pinned text/plain source asset and exact source_text, source/target locale, rubric_version and dimension IDs/ranges. Other recipes must omit.",
            "context": "Nonblank study-specific objective and audience; author-only.",
            "translation_approval_ref": "Operator approval reference covering all supplied localized labels.",
            "prompts": "Each stable block_key mapped to exact approved text for every selected locale.",
            "task_assets": "Each task key mapped to 1–100 authorized, complete, pinned PNG asset references.",
            "options": "2–10 stable IDs and approved localized labels; comparison variants require distinct PNG assets."
            if kind
            else "Must be empty.",
            "endpoint_labels": "low/high approved localized rating labels.",
            "reviewer_qualifications": "Required locale-specific reviewer qualifications for localization recipes; author-only.",
        },
        "report": "Shared analytics: task self-report, clarity distribution, original explanations, comparison frequencies/ranks when present. Standard suppression and redaction apply.",
    }


_RECIPES = {key: _recipe(key, family) for family, keys in FAMILIES.items() for key in keys}


def get_recipe(key, version=1):
    if key not in _RECIPES or version != 1:
        raise DomainError("TEMPLATE_NOT_FOUND", "Template version not found.", 404)
    recipe = copy.deepcopy(_RECIPES[key])
    recipe["recipe_hash"] = hashlib.sha256(canonical_json(recipe)).hexdigest()
    recipe["enabled"] = all(kind in RENDERERS for kind in recipe["methods"])
    recipe["renderers"] = {kind: kind in RENDERERS for kind in recipe["methods"]}
    return recipe


def catalogue():
    return [get_recipe(key) for key in sorted(_RECIPES)]

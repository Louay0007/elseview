import hashlib

from app.common.cache import canonical_json
from app.common.errors import DomainError
from app.studies import methods
from app.studies import service as studies
from app.studies.schemas import StudyBody, VersionBody

from .catalogue import get_recipe
from .models import TemplateInstance


def compile_recipe(recipe, body):
    inputs = body.inputs
    locales = set(body.locales)
    specs = recipe["blocks"]
    tasks = {s["block_key"] for s in specs if s["type"] == "prototype.task"}

    def invalid():
        raise DomainError(
            "TEMPLATE_INPUTS",
            "Exact localized prompts, approved labels, assets and recipe inputs are required.",
            422,
        )

    if (
        not recipe["enabled"]
        or len(locales) != len(body.locales)
        or not locales <= set(recipe["locales"])
        or set(inputs.prompts) != {s["block_key"] for s in specs}
        or set(inputs.task_assets) != tasks
        or set(inputs.endpoint_labels) != {"low", "high"}
    ):
        invalid()
    labels = (
        list(inputs.prompts.values())
        + list(inputs.endpoint_labels.values())
        + [o.label for o in inputs.options]
    )
    if any(set(label) != locales or any(not v.strip() for v in label.values()) for label in labels):
        invalid()
    if recipe["family"] == "localization" and (
        set(inputs.reviewer_qualifications) != locales
        or any(not q.strip() for q in inputs.reviewer_qualifications.values())
    ):
        invalid()
    language = inputs.language_review
    if recipe["family"] == "localization":
        if (
            language is None
            or language.source_language not in locales
            or language.target_language not in locales
        ):
            invalid()
    elif language is not None:
        invalid()
    comparison = next((s["type"] for s in specs if s["block_key"] == "comparison"), None)
    if comparison:
        if len(inputs.options) < 2 or len({o.id for o in inputs.options}) != len(inputs.options):
            invalid()
        if comparison == "preference" and (
            any(o.asset_ref is None for o in inputs.options)
            or len({o.asset_ref.asset_id for o in inputs.options}) != len(inputs.options)
        ):
            invalid()
        if comparison == "survey.ranking" and any(o.asset_ref for o in inputs.options):
            invalid()
    elif inputs.options:
        invalid()
    result = []
    for spec in specs:
        key, kind = spec["block_key"], spec["type"]
        if kind == "language.review":
            config = language.model_dump(mode="json")
        elif kind == "prototype.task":
            config = {
                "target": {
                    "mode": "asset_flow",
                    "asset_refs": [a.model_dump(mode="json") for a in inputs.task_assets[key]],
                },
                "success_mode": "self_report",
                "time_limit_ms": 600000,
            }
        elif kind == "preference":
            config = {
                "variants": [o.model_dump(mode="json") for o in inputs.options],
                "randomization": "uniform_permutation",
                "allow_tie": True,
                "allow_none": True,
            }
        elif kind == "survey.ranking":
            config = {
                "options": [
                    o.model_dump(mode="json", exclude={"asset_ref"}) for o in inputs.options
                ],
                "rank_count": len(inputs.options),
            }
        elif kind == "survey.rating":
            config = {"min": 1, "max": 5, "step": 1, "endpoint_labels": inputs.endpoint_labels}
        else:
            config = {"min_length": 1, "max_length": 4000}
        result.append(
            dict(spec, schema_version=1, required=True, prompt=inputs.prompts[key], config=config)
        )
    try:
        methods.validate_structure(result, body.locales, {})
    except (ValueError, TypeError):
        invalid()
    return result


def instantiate(session, workspace_id, actor_id, key, body):
    recipe = get_recipe(key, body.template_version)
    blocks = compile_recipe(recipe, body)
    study, version = studies.create_study(
        session,
        workspace_id,
        actor_id,
        StudyBody(
            title=body.title, retention_policy_id=body.retention_policy_id, ai_policy="human_only"
        ),
    )
    studies.edit_version(
        session,
        workspace_id,
        actor_id,
        study.id,
        version.id,
        VersionBody(
            expected_revision=1,
            blocks_json=blocks,
            rules_json={},
            locales=body.locales,
            consent_documents=body.consent_documents,
        ),
    )
    studies.validate_version(session, workspace_id, actor_id, version)
    snapshot = body.model_dump(mode="json")
    provenance = TemplateInstance(
        workspace_id=workspace_id,
        study_id=study.id,
        version_id=version.id,
        template_key=key,
        template_version=body.template_version,
        recipe_hash=recipe["recipe_hash"],
        recipe_snapshot=recipe,
        inputs_snapshot=snapshot,
        configuration_hash=hashlib.sha256(
            canonical_json({"blocks": blocks, "inputs": snapshot})
        ).hexdigest(),
    )
    session.add(provenance)
    session.flush()
    return {
        "study_id": str(study.id),
        "version_id": str(version.id),
        "revision": version.revision,
        "template_instance_id": str(provenance.id),
        "template_key": key,
        "template_version": body.template_version,
        "recipe_hash": provenance.recipe_hash,
        "configuration_hash": provenance.configuration_hash,
        "caveats": recipe["caveats"],
        "state": "draft",
    }

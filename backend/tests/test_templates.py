import copy
from uuid import uuid4

import pytest

from app.common.errors import DomainError
from app.templates.catalogue import catalogue, get_recipe
from app.templates.schemas import InstantiateBody
from app.templates.service import compile_recipe


def body_for(recipe, assets=None, consent=None, retention=None):
    locales = recipe["locales"]
    assets = assets or [str(uuid4()), str(uuid4())]

    def labels(text):
        return {locale: text for locale in locales}

    return {
        "template_version": recipe["version"],
        "title": "Synthetic " + recipe["key"],
        "retention_policy_id": retention or str(uuid4()),
        "locales": locales,
        "consent_documents": consent or {loc: str(uuid4()) for loc in locales},
        "inputs": {
            "language_review": {
                "source_asset_ref": {"asset_id": assets[0], "asset_version": 1},
                "source_text": "Synthetic original",
                "source_language": locales[0],
                "target_language": locales[0],
                "rubric_version": "synthetic_v1",
                "dimensions": [{"id": "clarity", "min": 1, "max": 5}],
            }
            if recipe["family"] == "localization"
            else None,
            "context": "Synthetic audience and objective; not customer evidence.",
            "translation_approval_ref": "synthetic-review-v1",
            "prompts": {
                s["block_key"]: labels("Synthetic " + recipe["key"] + " " + s["block_key"])
                for s in recipe["blocks"]
            },
            "task_assets": {
                s["block_key"]: [{"asset_id": assets[0], "asset_version": 1}]
                for s in recipe["blocks"]
                if s["type"] == "prototype.task"
            },
            "endpoint_labels": {"low": labels("Low"), "high": labels("High")},
            "options": [
                dict(
                    id="option_" + str(i),
                    label=labels("Synthetic option " + str(i)),
                    **(
                        {"asset_ref": {"asset_id": asset, "asset_version": 1}}
                        if "preference" in recipe["methods"]
                        else {}
                    ),
                )
                for i, asset in enumerate(assets)
            ]
            if "comparison" in {s["block_key"] for s in recipe["blocks"]}
            else [],
            "reviewer_qualifications": labels("Synthetic qualified reviewer"),
        },
    }


@pytest.mark.parametrize("recipe", catalogue(), ids=lambda r: r["key"])
def test_every_recipe_compiles_stable_localized_shared_methods(recipe):
    assert recipe["enabled"] and all(recipe["renderers"].values())
    body = body_for(recipe)
    blocks = compile_recipe(recipe, InstantiateBody(**body))
    changed = copy.deepcopy(body)
    for labels in changed["inputs"]["prompts"].values():
        for locale in labels:
            labels[locale] += " translation edit"
    translated = compile_recipe(recipe, InstantiateBody(**changed))
    assert [b["block_key"] for b in blocks] == [b["block_key"] for b in translated]
    assert [b["config"] for b in blocks] == [b["config"] for b in translated]
    body["inputs"]["prompts"].pop(next(iter(body["inputs"]["prompts"])))
    with pytest.raises(DomainError):
        compile_recipe(recipe, InstantiateBody(**body))


def test_catalogue_snapshot_copy_version_and_proxy():
    assert len(catalogue()) == 23
    first = get_recipe("video")
    first["blocks"].clear()
    assert get_recipe("video")["blocks"]
    assert any("proxy" in c for c in first["caveats"])
    assert "video" not in first["methods"]
    with pytest.raises(DomainError):
        get_recipe("video", 2)


def test_v1_recipe_hashes_are_pinned():
    import json
    from pathlib import Path

    import app.templates.catalogue as module

    pinned = json.loads(Path(module.__file__).with_name("v1_hashes.json").read_text())
    assert {r["key"]: r["recipe_hash"] for r in catalogue()} == pinned

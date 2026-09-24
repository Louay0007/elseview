from uuid import uuid4

from research_support import document, policy, upload


def blocks(asset_id):
    reference = {"asset_id": asset_id, "asset_version": 1}

    def labels(text):
        return {"fr": text, "ar": "نص " + text}

    configs = [
        (
            "survey.single",
            {
                "options": [
                    {"id": "yes", "label": labels("Oui")},
                    {"id": "no", "label": labels("Non")},
                ],
                "randomize_options": True,
            },
        ),
        (
            "survey.multi",
            {
                "options": [
                    {"id": "yes", "label": labels("Oui")},
                    {"id": "no", "label": labels("Non")},
                ],
                "min_selected": 1,
                "max_selected": 2,
            },
        ),
        (
            "survey.rating",
            {
                "min": 1,
                "max": 5,
                "step": 1,
                "endpoint_labels": {"low": labels("Difficile"), "high": labels("Facile")},
            },
        ),
        ("survey.text", {"min_length": 1, "max_length": 200}),
        (
            "preference",
            {
                "variants": [
                    {"id": "one", "label": labels("A"), "asset_ref": reference},
                    {"id": "two", "label": labels("B"), "asset_ref": reference},
                ],
                "randomization": "uniform_permutation",
                "allow_tie": True,
                "allow_none": True,
            },
        ),
        (
            "five_second",
            {
                "asset_ref": reference,
                "exposure_ms": 5000,
                "interruption_policy": "invalidate",
                "recall_block_ids": ["recall"],
            },
        ),
        ("survey.text", {"min_length": 1, "max_length": 200}),
        (
            "prototype.task",
            {
                "target": {"mode": "asset_flow", "asset_refs": [reference]},
                "success_mode": "self_report",
                "time_limit_ms": 60000,
            },
        ),
    ]
    keys = ["single", "multi", "rating", "text", "preference", "exposure", "recall", "prototype"]
    return [
        {
            "block_key": key,
            "schema_version": 1,
            "type": kind,
            "required": True,
            "prompt": labels(key),
            "config": config,
        }
        for key, (kind, config) in zip(keys, configs, strict=True)
    ]


def ready_study(client, base, headers, selected_blocks=None):
    asset = upload(client, base, headers)["asset"]["id"]
    retention = policy(client, base, headers)
    study_body = {"title": "Étude تجريبية", "retention_policy_id": retention}
    create = client.post(
        base + "/studies", headers=headers | {"Idempotency-Key": uuid4().hex}, json=study_body
    )
    assert create.status_code == 201, create.text
    result = create.json()
    endpoint = base + f"/studies/{result['study_id']}/versions/{result['version_id']}"
    key = uuid4().hex
    documents = {
        locale: document(client, base, headers, locale=locale, key=key)["id"]
        for locale in ("fr", "ar")
    }
    body = {
        "expected_revision": 1,
        "blocks_json": selected_blocks or blocks(asset),
        "rules_json": {"single": {"expected_option": "yes"}} if selected_blocks is None else {},
        "locales": ["fr", "ar"],
        "consent_documents": documents,
    }
    changed = client.put(endpoint, headers=headers, json=body)
    assert changed.status_code == 200, changed.text
    return result | {
        "endpoint": endpoint,
        "asset_id": asset,
        "body": body | {"expected_revision": 2},
        "study_body": study_body,
    }


def answer(block, locale="fr"):
    value = {
        "survey.single": {"option_id": "yes"},
        "survey.multi": {"option_ids": ["yes", "no"]},
        "survey.rating": {"value": 4},
        "survey.text": {"text": "Clair وواضح", "language": locale},
        "preference": {
            "assignment_id": block.get("assignment_id", "assignment"),
            "decision": "tie",
            "selected_variant_id": None,
            "reason": {"text": "Même préférence", "language": locale},
        },
        "five_second": {
            "attempt_id": block.get("attempt_id", "attempt"),
            "visible_ms": 5000,
            "interrupted": False,
        },
        "prototype.task": {"outcome": "completed", "elapsed_ms": 9000},
    }[block["type"]]
    return {"status": "responded", "value": value}

import json
from pathlib import Path

from app.contracts import ErrorEnvelope
from app.main import create_app


def test_generated_openapi_matches_reviewed_artifact(settings):
    app = create_app(settings)
    try:
        schema = app.openapi()
        artifact = Path(__file__).parents[1] / "contracts" / "openapi.json"
        assert json.loads(artifact.read_text()) == schema
        ids = []
        for path in schema["paths"].values():
            for operation in path.values():
                ids.append(operation["operationId"])
                assert "security" in operation
                for code in ("401", "403", "409", "413", "422", "429", "500", "503"):
                    assert operation["responses"][code]["content"]["application/json"][
                        "schema"
                    ] == {"$ref": "#/components/schemas/ErrorEnvelope"}
        assert len(ids) == len(set(ids))
        assert schema["paths"]["/api/v1/me"]["get"]["security"] == [{"BearerAuth": []}]
        answer = schema["paths"]["/api/v1/collection/sessions/{session_id}/answers/{block_key}"][
            "put"
        ]
        assert answer["security"] == [{"SessionCapability": []}]
        assert answer["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith(
            "/AnswerBody"
        )
        assert schema["paths"]["/api/v1/auth/register"]["post"]["security"] == []
    finally:
        app.state.database.close()
        app.state.cache.close()
        app.state.rate_limiter.close()


def test_actual_errors_follow_documented_envelope(client):
    cases = [
        client.get("/api/v1/me"),
        client.get("/api/v1/nonexistent"),
        client.post("/api/v1/auth/login", json={}),
        client.post("/api/v1/auth/login", content=b"x" * (1024 * 1024)),
    ]
    for response in cases:
        assert response.status_code >= 400
        envelope = ErrorEnvelope.model_validate(response.json())
        assert envelope.request_id == response.headers["x-request-id"]
        assert response.headers["cache-control"] == "no-store"


def test_request_contracts_have_exact_canonical_answer_shape():
    from uuid import uuid4

    from app.collection.schemas import AnswerBody

    body = AnswerBody(
        schema_version=1,
        expected_revision=0,
        client_event_id=uuid4(),
        status="responded",
        value={"text": "جواب / réponse"},
    )
    assert body.answer == {
        "status": "responded",
        "value": {"text": "جواب / réponse"},
        "reason_code": None,
    }
    assert body.model_json_schema()["additionalProperties"] is False

"""Deterministic API contract export; no database connection or public docs endpoint."""

import argparse
import json
from pathlib import Path

from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute, iter_route_contexts
from pydantic import BaseModel, ConfigDict


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    message: str


class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    error: ErrorDetail
    request_id: str


def dependency_calls(dependant):
    yield dependant.call
    for child in dependant.dependencies:
        yield from dependency_calls(child)


def build_contract(app):
    from app.auth.dependencies import current_user

    schema = get_openapi(
        title=app.title, version=app.version, description=app.description, routes=app.routes
    )
    components = schema.setdefault("components", {})
    models = components.setdefault("schemas", {})
    error = ErrorEnvelope.model_json_schema(ref_template="#/components/schemas/{model}")
    models.update(error.pop("$defs", {}))
    models["ErrorEnvelope"] = error
    models.pop("HTTPValidationError", None)
    models.pop("ValidationError", None)
    components["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
        "SessionCapability": {"type": "apiKey", "in": "header", "name": "X-Session-Token"},
        "ScopedAPIKey": {"type": "apiKey", "in": "header", "name": "X-API-Key"},
        "RefreshCookie": {"type": "apiKey", "in": "cookie", "name": "elseview_refresh"},
    }
    for context in iter_route_contexts(app.routes):
        route = context.route
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods:
            operation = schema["paths"][route.path_format][method.lower()]
            security = {}
            if current_user in set(dependency_calls(route.dependant)):
                security["BearerAuth"] = []
            headers = {
                p.get("name", "").lower()
                for p in operation.get("parameters", [])
                if p["in"] == "header"
            }
            if "x-session-token" in headers:
                security["SessionCapability"] = []
            if "x-api-key" in headers:
                security["ScopedAPIKey"] = []
            if route.path.endswith("/auth/refresh"):
                security["RefreshCookie"] = []
                operation["description"] = (
                    "Requires the HttpOnly refresh cookie, matching X-CSRF-Token and an exact approved Origin."
                )
            if route.path.endswith("/auth/logout"):
                operation["description"] = (
                    "Requires bearer authentication and exact Origin. If a refresh cookie is present, its matching X-CSRF-Token is also required."
                )
            operation["security"] = [security] if security else []
            for status in ("400", "401", "403", "404", "409", "413", "422", "429", "500", "503"):
                operation["responses"][status] = {
                    "description": "Safe error envelope; no internal exception or request data.",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ErrorEnvelope"}
                        }
                    },
                }
    schema["info"]["x-contract-review"] = (
        "Development contract: request and error schemas validated; untyped success projections are explicitly retained as unconstrained, not invented."
    )
    return schema


def install(app):
    def openapi():
        if app.openapi_schema is None:
            app.openapi_schema = build_contract(app)
        return app.openapi_schema

    app.openapi = openapi


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    from app.main import create_app

    app = create_app()
    try:
        payload = json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        if args.check:
            if not args.output.is_file() or args.output.read_text() != payload:
                raise SystemExit("OpenAPI artifact differs from application contract")
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload)
    finally:
        app.state.database.close()
        app.state.cache.close()
        app.state.rate_limiter.close()


if __name__ == "__main__":
    main()

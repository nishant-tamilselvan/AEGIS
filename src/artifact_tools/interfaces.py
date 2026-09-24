"""Scaffold and manage the decentralized interfaces contract store.

The single-file ``interface-specifications.md`` is a *routing index*; the real
contracts live as native schema files (OpenAPI/AsyncAPI ``.yaml``/``.json``,
``.graphql``, ``.proto``) under ``<artifact-dir>/interfaces/`` so tools and LLMs can
parse them directly instead of unwrapping them from Markdown code blocks.
"""

from __future__ import annotations

from pathlib import Path

INTERFACES_DIR = "interfaces"
_SUBDIRS = ("synchronous", "asynchronous", "graphql")

_README = """# Interfaces — Contract Store

Actual API, event and schema contracts for this project, in native formats so tools
and LLMs can parse them directly. The routing index lives one level up in
[`../interface-specifications.md`](../interface-specifications.md).

- `synchronous/` — OpenAPI/Swagger (`.yaml`) and gRPC (`.proto`) request/response contracts.
- `asynchronous/` — AsyncAPI (`.yaml` / `.json`) event/topic schemas.
- `graphql/` — GraphQL schema (`.graphql`) files.

Each row of the routing index links to exactly one file here. Keep one contract per
file to avoid merge conflicts and keep diffs reviewable.
"""

_OPENAPI_STUB = """openapi: 3.1.0
info:
  title: Identity & Auth API
  version: "1.0.0"
  description: Example synchronous REST contract. Replace with the real spec.
servers:
  - url: /api/v1/auth
paths:
  /token:
    post:
      summary: Issue an access token
      responses:
        "200":
          description: Token issued
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/TokenResponse"
components:
  schemas:
    TokenResponse:
      type: object
      properties:
        access_token: { type: string }
        expires_in: { type: integer }
"""

_ASYNCAPI_STUB = """asyncapi: 3.0.0
info:
  title: Order Events
  version: "1.0.0"
  description: Example asynchronous event contract. Replace with the real spec.
servers:
  kafka:
    host: broker:9092
    protocol: kafka
channels:
  enterprise.orders.v1:
    address: enterprise.orders.v1
    messages:
      OrderCreated:
        payload:
          type: object
          properties:
            order_id: { type: string, format: uuid }
            correlation_id: { type: string, format: uuid }
            occurred_at: { type: string, format: date-time }
operations:
  publishOrderCreated:
    action: send
    channel:
      $ref: "#/channels/enterprise.orders.v1"
"""

_GRAPHQL_STUB = """# Example GraphQL gateway schema. Replace with the real schema.
type Query {
  health: String!
}
"""

_PROTO_STUB = """syntax = "proto3";

// Example gRPC contract. Replace with the real service definition.
package catalog.v2;

service ProductCatalog {
  rpc GetProduct(GetProductRequest) returns (Product);
}

message GetProductRequest {
  string id = 1;
}

message Product {
  string id = 1;
  string name = 2;
}
"""

_JSON_EVENT_STUB = """{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "EmailNotificationRequested",
  "description": "Example asynchronous JSON event schema. Replace with the real schema.",
  "type": "object",
  "required": ["correlation_id", "to", "template"],
  "properties": {
    "correlation_id": { "type": "string", "format": "uuid" },
    "occurred_at": { "type": "string", "format": "date-time" },
    "to": { "type": "string", "format": "email" },
    "template": { "type": "string" },
    "data": { "type": "object" }
  }
}
"""

_STUBS = {
    "synchronous/identity-auth-v1.yaml": _OPENAPI_STUB,
    "synchronous/product-catalog-v2.proto": _PROTO_STUB,
    "asynchronous/order-events-kafka.yaml": _ASYNCAPI_STUB,
    "asynchronous/email-notifications.json": _JSON_EVENT_STUB,
    "graphql/gateway-schema.graphql": _GRAPHQL_STUB,
}


def init_interfaces_dir(base_dir: str | Path, *, with_stubs: bool = True) -> Path:
    """Create the ``interfaces/`` contract store next to the routing index.

    Idempotent: existing files are never overwritten. Returns the interfaces path.
    """
    interfaces = Path(base_dir) / INTERFACES_DIR
    for sub in _SUBDIRS:
        (interfaces / sub).mkdir(parents=True, exist_ok=True)

    readme = interfaces / "README.md"
    if not readme.exists():
        readme.write_text(_README, encoding="utf-8")

    if with_stubs:
        for rel, content in _STUBS.items():
            target = interfaces / rel
            if not target.exists():
                target.write_text(content, encoding="utf-8")

    return interfaces

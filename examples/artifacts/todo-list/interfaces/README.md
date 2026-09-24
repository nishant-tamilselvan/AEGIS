# Interfaces — Contract Store

Actual API, event and schema contracts for this project, in native formats so tools
and LLMs can parse them directly. The routing index lives one level up in
[`../interface-specifications.md`](../interface-specifications.md).

- `synchronous/` — OpenAPI/Swagger (`.yaml`) and gRPC (`.proto`) request/response contracts.
- `asynchronous/` — AsyncAPI (`.yaml` / `.json`) event/topic schemas.
- `graphql/` — GraphQL schema (`.graphql`) files.

Each row of the routing index links to exactly one file here. Keep one contract per
file to avoid merge conflicts and keep diffs reviewable.

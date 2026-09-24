# CLI reference

The `artifact_tools` package scaffolds, validates and maintains AEGIS artifacts. Agents
call it for you, and you can run it yourself:

```bash
python -m artifact_tools <command> --help
```

After `pip install -e .`, the same commands are also available as `artifact-tools`.

## Install on its own

The CLI is also published on PyPI as **`aegis-sdlc`**, for use outside an AEGIS clone,
for example in CI:

```bash
pip install aegis-sdlc
artifact-tools validate docs/artifacts/my-app --strict
```

The package bundles the artifact and implementation templates. When a repository has its
own `aegis/skills/.../templates` folders, those are used instead.

In the examples, `<app>` is an application folder such as `docs/artifacts/customer-portal`.

## Artifacts

### `scaffold`

Create an artifact from its template.

```bash
python -m artifact_tools scaffold <type> docs/artifacts/<app> --project "<Name>" [--title "<Title>"] [--force]
```

`<type>` is one of `product-requirements`, `functional-requirements`,
`non-functional-requirements`, `user-journey-map`, `system-blueprint`,
`executive-briefing`, `interface-specifications`, `data-architecture`,
`security-architecture`, `deployment-topology` or `observability-strategy`.

### `validate`

Validate one application, or every application under a parent folder.

```bash
python -m artifact_tools validate docs/artifacts/<app> [--strict]
python -m artifact_tools validate docs/artifacts [--strict]
```

`--strict` treats warnings as failures.

### `changelog`

Append a changelog entry to an artifact and bump its version.

```bash
python -m artifact_tools changelog docs/artifacts/<app>/<file>.md "<summary>" [--bump minor|major] [--phase <n>]
```

### `interfaces init`

Create the `interfaces/` contract store (`synchronous/`, `asynchronous/`, `graphql/`).

```bash
python -m artifact_tools interfaces init docs/artifacts/<app> [--no-stubs]
```

### `diagrams`

Render the Mermaid diagrams embedded in an application's Markdown files to images.

```bash
python -m artifact_tools diagrams docs/artifacts/<app> [--format png|svg] [--engine mmdc|mermaidx] [--theme default|neutral|dark|forest]
```

The `mmdc` engine needs the Mermaid CLI (Node.js). The `mermaidx` engine is pure Python:
`pip install -e ".[diagrams]"`.

## Architecture decisions

```bash
python -m artifact_tools adr init docs/artifacts/<app>/architecture-decisions
python -m artifact_tools adr new "<title>" docs/artifacts/<app>/architecture-decisions \
  [--status proposed|accepted|rejected|deprecated|superseded] \
  [--component <tag>] [--supersedes ADR-000X] [--deciders "<names>"]
```

## Implementation (phase 3)

### Readiness and setup

```bash
# Read-only gate. Run it before planning or writing code.
python -m artifact_tools implementation readiness docs/artifacts/<app> <target-workspace> \
  [--standards-review verified|manual-review-required]

# Create the implementation pointer and ledgers.
python -m artifact_tools implementation init docs/artifacts/<app> <target-workspace> \
  --target-baseline <commit> [--target-branch <branch>] [--project "<Name>"] \
  [--standards-review verified|manual-review-required]
```

Pass `--standards-review verified` only after the current Enterprise Standards were
checked, by the agents through the MCP server or by a person.

### Work packages

```bash
python -m artifact_tools implementation work-package new docs/artifacts/<app> "<title>" \
  --scope "<scope>" --source-ids "FR-001,ADR-0002" --target-paths "apps/example/src" \
  [--dependencies WP-0001] [--owner <name>] [--parallel-group <group>]

python -m artifact_tools implementation work-package transition docs/artifacts/<app> WP-0001 <status> \
  --actor <name> [--approved-by <name>] [--review-status pending|pass|needs-changes] [--note "<note>"]

python -m artifact_tools implementation work-package record-evidence docs/artifacts/<app> WP-0001 "<command>" pass|fail \
  [--details "<output summary>"]
```

Allowed status transitions:

| From | To |
| --- | --- |
| `planned` | `approved`, `deferred`, `cancelled` |
| `approved` | `in-progress`, `blocked`, `deferred`, `cancelled` |
| `in-progress` | `review`, `blocked` |
| `blocked` | `approved`, `in-progress`, `deferred`, `cancelled` |
| `review` | `in-progress`, `complete`, `blocked` |
| `deferred` | `planned` |
| `complete`, `cancelled` | none (final) |

A package reaches `complete` only with a reviewer PASS and at least one recorded piece of
evidence.

### Decisions

```bash
python -m artifact_tools implementation decision docs/artifacts/<app> "<question>" "<decision>" "<rationale>" \
  [--type tactical|material] [--status pending|accepted|rejected|superseded] \
  [--work-package WP-0001] [--sources "FR-001"] [--affected-paths "apps/example"] \
  [--approver <name>] [--adr ADR-0004] [--supersedes IDEC-0002]
```

A material decision needs an approver and an ADR.

### Status, validation and release

```bash
python -m artifact_tools implementation status docs/artifacts/<app>             # JSON
python -m artifact_tools implementation validate docs/artifacts/<app> [--strict]
python -m artifact_tools implementation release-approve docs/artifacts/<app> --approver <name> [--note "<note>"]
```

## Repository checks

These are for contributors, not for artifact work:

```bash
python scripts/ci/repo_checks.py all
python examples/enterprise-standards-server/library.py --check <knowledge-base>
```

See [CONTRIBUTING.md](../CONTRIBUTING.md#checks).

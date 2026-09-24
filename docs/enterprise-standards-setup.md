# Enterprise Standards Setup

AEGIS agents check your organization's standards before they propose requirements,
architecture or code. They read those standards from an **Enterprise Standards library**,
a read-only [MCP](https://modelcontextprotocol.io) server named
`enterprise-standards-server`.

AEGIS does not ship your standards. You connect your own library. This guide explains how.

## Contents

- [What the library does for AEGIS](#what-the-library-does-for-aegis)
- [Choose a setup option](#choose-a-setup-option)
- [Quick start with the reference server](#quick-start-with-the-reference-server)
- [Step 1: Write your standards](#step-1-write-your-standards)
- [Step 2: Validate the knowledge base](#step-2-validate-the-knowledge-base)
- [Step 3: Run the server](#step-3-run-the-server)
- [Step 4: Connect your agent host](#step-4-connect-your-agent-host)
- [Step 5: Check that the agents can see it](#step-5-check-that-the-agents-can-see-it)
- [Connect an existing standards system](#connect-an-existing-standards-system)
- [Tool contract reference](#tool-contract-reference)
- [Running without a library](#running-without-a-library)
- [Security](#security)
- [Troubleshooting](#troubleshooting)

## What the library does for AEGIS

Without a library, agents ask you questions your organization may already have answered,
such as "which API error format do we use?" or "how must confidential data be stored?".
With a library connected, every phase follows the same routine:

1. The agent searches the library for the Approved standards that apply to the work.
2. It checks that each standard is current: not superseded and not overdue for review.
3. It uses those standards in its proposal and cites their ids in the artifacts.
4. It asks you only about what the standards leave open.

The [`enterprise-standards` skill](../aegis/skills/enterprise-standards/SKILL.md) holds the
exact queries each agent runs. All agents reach the library through the tool reference
`enterprise-standards-server/*` in their frontmatter.

## Choose a setup option

| Option | Choose it when | Effort |
| --- | --- | --- |
| **A. Reference server** | Your standards are, or can be, Markdown files. | Low. Write the files and run the included server. |
| **B. Your own server** | Your standards live in another system, such as a wiki, a document store or a database. | Medium. Implement the [tool contract](#tool-contract-reference) in front of that system. |
| **C. No library** | You are trying AEGIS out, or you have no written standards yet. | None. See [Running without a library](#running-without-a-library). |

Most teams start with option A. The reference server is small enough to read in one
sitting, so it also serves as a working specification for option B.

## Quick start with the reference server

This runs the server with the sample standards, so you can see AEGIS use them before you
write your own.

```bash
# 1. Install the server's dependencies (Python 3.10+).
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # macOS / Linux
pip install -r examples/enterprise-standards-server/requirements.txt

# 2. Check the sample knowledge base.
python examples/enterprise-standards-server/library.py --check examples/enterprise-standards-server/knowledge-base

# 3. Create your local MCP configuration (both files are gitignored).
cp .vscode/mcp.example.json .vscode/mcp.json   # GitHub Copilot in VS Code
cp .mcp.example.json .mcp.json                 # Claude Code
```

Then start the server and ask for the domains:

| GitHub Copilot | Claude Code |
| --- | --- |
| Open `.vscode/mcp.json` in VS Code and select **Start** above the server entry. In Copilot Chat (Agent mode), ask *"Use enterprise-standards-server to list the domains."* | Start `claude` in the repository root and approve the `enterprise-standards-server` project server. Ask *"Use enterprise-standards-server to list the domains."* |

You should see the four sample domains.

To switch to your own standards, point `--knowledge-base` at your folder (see
[Step 4](#step-4-connect-your-agent-host)) and restart the server.

## Step 1: Write your standards

A knowledge base is a folder of Markdown files. Each file is one document with YAML
frontmatter. Subfolders are optional and only for your convenience. Files named
`README.md` are ignored.

```text
standards/
├── security/
│   └── ENT-STD-SEC-001-security-baseline.md
├── data/
│   └── ENT-STD-DAT-001-data-classification.md
└── architecture-decisions/
    └── ENT-DEC-0001-managed-postgresql.md
```

### Document format

```markdown
---
id: ENT-STD-SEC-001
title: Security Baseline
type: Standard
status: Approved
domain: Security
classification: internal
tags: [hardening, secrets, logging, encryption]
version: "2"
part_of_family: Security Baseline
owner: Security Architecture
summary: Minimum security controls every application must meet before production.
effective_date: 2026-02-01
last_reviewed: 2026-02-01
review_cycle_months: 12
relationships:
  supersedes: [ENT-STD-SEC-000]
  depends_on: [ENT-STD-DAT-001]
---

# Security Baseline

1. All traffic uses TLS 1.2 or later.
2. ...
```

The body is ordinary Markdown. Write it for people. Agents read it through `get_document`.

### Frontmatter fields

| Field | Required | Values | Purpose |
| --- | --- | --- | --- |
| `id` | Yes | Unique string. See [ID convention](#id-convention). | The id agents cite in artifacts. |
| `title` | Yes | Text | Display name. |
| `type` | Yes | `Standard`, `Policy`, `Guideline`, `Pattern`, `Architecture Decision Record (ADR)` | Agents filter by type. For example, the implementation phase looks for `Pattern`. |
| `status` | Yes | `Approved`, `Draft`, `Under Review`, `Deprecated`, `Superseded` | Agents base proposals only on `Approved` documents. |
| `domain` | Yes | Text. See [reference taxonomy](#reference-taxonomy). | The main filter each specialist agent uses. |
| `classification` | No | `public`, `internal`, `confidential` | Sensitivity of the document itself. |
| `tags` | No | List of strings | Finer filtering, such as `observability` or `ci-cd`. |
| `version` | No | String, for example `"2"` | Lets agents pick the version a project uses. Quote it so YAML keeps it as text. |
| `part_of_family` | No | Text | Groups related standards, such as `API Standards`. |
| `owner` | No | Text | The team accountable for the document. |
| `summary` | No | One sentence | Returned in search results and matched by `query`. |
| `effective_date` | No | `YYYY-MM-DD` | When the document took effect. |
| `last_reviewed` | No | `YYYY-MM-DD` | Drives review health. Without it the status is `Unknown`. |
| `review_cycle_months` | No | Integer, default `12` | How often the document must be reviewed. |
| `relationships` | No | Mapping of edge to list of ids | Links between documents. See below. |

### Relationships

Record each link once, on the document that makes the claim. The server adds the reverse
link automatically.

| You write | On document | Server adds on the target |
| --- | --- | --- |
| `supersedes: [OLD-ID]` | The new document | `superseded_by` |
| `depends_on: [OTHER-ID]` | The dependent document | `required_by` |
| `related_to: [OTHER-ID]` | Either document | `related_to` (both directions) |

When a document replaces another, set the old one's `status` to `Superseded` and add
`supersedes` to the new one. Agents follow `superseded_by` to make sure they never cite a
replaced standard.

### Review health

The server works out each document's review status from `last_reviewed` and
`review_cycle_months`:

| Status | Meaning |
| --- | --- |
| `Current` | Next review is more than 60 days away. |
| `Due Soon` | Next review is within 60 days. |
| `Overdue` | Next review passed up to 180 days ago. |
| `Severely Overdue` | Next review passed more than 180 days ago. |
| `Unknown` | No `last_reviewed` date. |

Agents still use an overdue standard, but they record the reliance on stale guidance as
a risk in the artifact. They do not treat the standard as silently current.

### ID convention

AEGIS artifacts use their own ids: `PR-`, `FR-`, `NFR-`, `UJ-`, `BP-`, `RISK-`, `IF-`,
`DM-`, `SEC-`, `DEP-`, `OBS-` and `ADR-` followed by three or more digits. The artifact
validator treats any such token in an artifact as an internal reference. It reports an
error if nothing defines that reference.

So a library id must never contain one of those prefixes followed by digits, unless
`STD-` comes directly before it. The validator skips anything after `STD-`.

| Library id | Safe? | Why |
| --- | --- | --- |
| `ENT-STD-SEC-001` | Yes | `SEC-001` follows `STD-`, so it is skipped. |
| `ENT-STD-API-001` | Yes | `API` is not an AEGIS prefix. |
| `ENT-PAT-001`, `ENT-POL-003`, `ENT-DEC-0001` | Yes | `PAT`, `POL` and `DEC` are not AEGIS prefixes. |
| `ENT-SEC-001` | No | `SEC-001` would be read as an internal security control. |
| `ADR-045` or `ACME-ADR-045` | No | `ADR-045` would be read as one of the application's own ADRs. |

Recommended patterns:

- Standards: `<ORG>-STD-<DOMAIN>-NNN`, for example `ENT-STD-SEC-001`.
- Other types: `<ORG>-<TYPE>-NNN` with a type code that is not an AEGIS prefix, for example
  `PAT` (pattern), `POL` (policy), `GDL` (guideline) or `DEC` (enterprise decision).

`library.py --check` flags any id that breaks this rule. Replace `ENT` with a short code
for your organization.

### Reference taxonomy

The skill's queries use the domain and family names below. You do not have to use them.
Agents call `list_domains` and `list_families` first and match your names. Staying close
to these names makes matches more reliable.

| Used by | Domains | Families |
| --- | --- | --- |
| `data-architect` | `Data`, `Data & Security`, `Records Management` | `Records Management` |
| `interface-integration-architect` | `Integration`, `Software Delivery` (tag `observability`) | `API Standards` |
| `security-architect` | `Security`, `Identity & Access` | `Security Baseline` |
| `platform-architect` | `Cloud`, `Software Delivery` (tags `ci-cd`, `container`) | `Cloud & Infrastructure` |
| Implementation agents | `Software Delivery` plus the package's own domain | Any |

The documents that give agents the most value to start with are:

1. A **data classification** standard. It drives data model, encryption and retention decisions.
2. A **security baseline**. It drives security controls.
3. An **API standard**. It drives interface contracts.
4. A **logging and observability** pattern. It drives the observability strategy.
5. Your existing **enterprise architecture decisions**, such as approved databases or cloud platforms.

## Step 2: Validate the knowledge base

```bash
python examples/enterprise-standards-server/library.py --check path/to/standards
```

The check reports:

- files without frontmatter;
- missing required fields;
- duplicate ids;
- unknown `type`, `status`, `classification` or relationship names;
- relationship targets that do not exist;
- `Superseded` documents that nothing supersedes;
- ids that AEGIS would misread (see [ID convention](#id-convention)).

It exits with status 1 when it finds problems, so you can run it in CI on the repository
that holds your standards.

## Step 3: Run the server

The server loads the knowledge base once at startup. Restart it after you change the
documents.

**Local (stdio).** Your agent host (VS Code or Claude Code) starts the server itself and
talks to it over stdin/stdout.
This is the simplest option for one person. It needs Python and the dependencies on each
developer's machine.

```bash
python examples/enterprise-standards-server/server.py --knowledge-base path/to/standards
```

**Shared (HTTP).** Run one server for the whole team, usually as a container or an
internal service:

```bash
python examples/enterprise-standards-server/server.py \
  --knowledge-base /srv/standards \
  --transport streamable-http --host 127.0.0.1 --port 8000
```

The MCP endpoint is `http://<host>:<port>/mcp`. You can also set the knowledge-base path
with the `ENTERPRISE_STANDARDS_KB` environment variable.

The reference server has no authentication of its own. Before you expose it beyond
`localhost`, read [Security](#security).

## Step 4: Connect your agent host

Each agent host reads its own MCP configuration file. Both files are gitignored because
they often hold URLs and credentials, and each has a committed template:

| Agent host | Config file | Template | Secrets |
| --- | --- | --- | --- |
| GitHub Copilot in VS Code | `.vscode/mcp.json` | `.vscode/mcp.example.json` | VS Code `inputs` (prompted, stored securely) |
| Claude Code | `.mcp.json` | `.mcp.example.json` | `${ENV_VAR}` expansion |
| Claude Code plugin | `.mcp.json` in **your own** repository | Copy the Claude Code section below | `${ENV_VAR}` expansion |

Plugin users have no AEGIS clone to run the reference server from. Use your organization's
shared server over HTTP, or clone AEGIS once and point `command` and `args` at its
`examples/enterprise-standards-server/server.py` with absolute paths.

In both, keep the server name exactly `enterprise-standards-server`. The agents refer to
it by that name: `enterprise-standards-server/*` in Copilot and
`mcp__enterprise-standards-server` in Claude Code.

### GitHub Copilot (VS Code)

Start from the template:

```bash
cp .vscode/mcp.example.json .vscode/mcp.json
```

**Local server (stdio)** — the template's default:

```json
{
  "servers": {
    "enterprise-standards-server": {
      "type": "stdio",
      "command": "python",
      "args": [
        "${workspaceFolder}/examples/enterprise-standards-server/server.py",
        "--knowledge-base",
        "${workspaceFolder}/examples/enterprise-standards-server/knowledge-base"
      ]
    }
  }
}
```

Change the `--knowledge-base` value to your own folder. If you installed the dependencies
in a virtual environment, set `command` to that environment's Python, for example
`${workspaceFolder}/.venv/Scripts/python.exe` on Windows or
`${workspaceFolder}/.venv/bin/python` on macOS and Linux.

**Shared server (HTTP) with a token.** Use an input so VS Code prompts for the secret and
stores it securely. The secret never appears in the file:

```json
{
  "inputs": [
    {
      "type": "promptString",
      "id": "enterprise-standards-token",
      "description": "Enterprise Standards access token",
      "password": true
    }
  ],
  "servers": {
    "enterprise-standards-server": {
      "type": "http",
      "url": "https://standards.example.com/mcp",
      "headers": {
        "Authorization": "Bearer ${input:enterprise-standards-token}"
      }
    }
  }
}
```

Do not paste tokens or Basic-auth strings straight into `mcp.json`. Base64 is an
encoding, not encryption.

### Claude Code

Start from the template:

```bash
cp .mcp.example.json .mcp.json
```

**Local server (stdio)** — the template's default. Claude Code starts MCP servers from the
repository root, so the paths are relative:

```json
{
  "mcpServers": {
    "enterprise-standards-server": {
      "command": "python",
      "args": [
        "examples/enterprise-standards-server/server.py",
        "--knowledge-base",
        "examples/enterprise-standards-server/knowledge-base"
      ]
    }
  }
}
```

Change the `--knowledge-base` value to your own folder. If you installed the dependencies
in a virtual environment, set `command` to that environment's Python, for example
`.venv/Scripts/python.exe` on Windows or `.venv/bin/python` on macOS and Linux.

**Shared server (HTTP) with a token.** Keep the token in an environment variable. Claude
Code expands `${VAR}` (and `${VAR:-default}`) in `.mcp.json`, so the secret never appears
in the file:

```json
{
  "mcpServers": {
    "enterprise-standards-server": {
      "type": "http",
      "url": "https://standards.example.com/mcp",
      "headers": {
        "Authorization": "Bearer ${ENTERPRISE_STANDARDS_TOKEN}"
      }
    }
  }
}
```

Set the variable before you start Claude Code, for example
`$env:ENTERPRISE_STANDARDS_TOKEN = "..."` in PowerShell or
`export ENTERPRISE_STANDARDS_TOKEN=...` in bash.

Claude Code asks you to approve project MCP servers from `.mcp.json` the first time.
Restart it after you change the file.

## Step 5: Check that the agents can see it

**GitHub Copilot:**

1. In VS Code, open `.vscode/mcp.json` and start the server. The status above the entry
   should show it running with 7 tools.
2. In Copilot Chat, switch to Agent mode and open the tools picker. Confirm the
   `enterprise-standards-server` tools are enabled.

**Claude Code:**

1. Start `claude` in the repository root and approve `enterprise-standards-server` when
   asked.
2. Run `/mcp`. The server should be listed as connected, with 7 tools.

**Both:**

1. Ask: *"Use enterprise-standards-server to search for Approved standards in the Security domain."*
2. Start a real session with `/start-ideation my-app <idea>`. Early in the session, the
   orchestrator should report which standards it found before it asks you questions.

If the agent says *"Enterprise Standards MCP unavailable"*, see
[Troubleshooting](#troubleshooting).

## Connect an existing standards system

If your standards already live in a wiki, a document store or a database, you do not have
to copy them into Markdown. Build a small MCP server in front of that system instead. The
server must:

1. be named `enterprise-standards-server` in `.vscode/mcp.json` and `.mcp.json`;
2. expose the seven tools in the [tool contract](#tool-contract-reference) with the same
   names and parameters;
3. return documents with the [frontmatter fields](#frontmatter-fields) as keys;
4. use the same `status`, `type`, edge and review-status values;
5. follow the [ID convention](#id-convention), or map your ids to it.

The simplest path is to reuse the reference server. Replace `KnowledgeBase._load` in
`examples/enterprise-standards-server/library.py` with code that reads your system and
builds the same `Document` objects. Search, relationships and review health then work
unchanged.

## Tool contract reference

All tools are read-only. `search_documents`, `list_families` (with a family) and the
listings return metadata only. Only `get_document` returns the body.

### `list_domains()`

Returns one entry per domain: `{domain, document_count, approved_count}`.

### `list_tags()`

Returns one entry per tag: `{tag, count}`.

### `list_families(family?)`

- Without `family`: returns one entry per family, `{family, document_count}`.
- With `family`: returns `{family, documents: [metadata...]}`.

### `search_documents(status?, type?, domain?, classification?, tags?, version?, part_of_family?, query?, limit?)`

| Parameter | Default | Behavior |
| --- | --- | --- |
| `status` | `"Approved"` | Exact match, case-insensitive. `"Any"` disables the filter. |
| `type`, `domain`, `classification`, `part_of_family` | none | Exact match, case-insensitive. |
| `tags` | none | The document must carry every listed tag. |
| `version` | none | Exact string match. |
| `query` | none | Case-insensitive substring match on `title` and `summary`. |
| `limit` | `50` | Maximum number of results. |

Returns a list of metadata objects, sorted by id. Each holds the frontmatter fields,
`relationships` (including derived edges) and `path`.

### `get_document(id)`

Returns the metadata plus `body` (the Markdown text) and `review`
(`{last_reviewed, next_review, review_status, days_overdue}`). An unknown id returns a
tool error that names the id.

### `get_related(id, edge_type?, depth?)`

Walks the relationship graph breadth-first from `id`.

- `edge_type` is one of `supersedes`, `superseded_by`, `depends_on`, `required_by` or
  `related_to`. When omitted, the tool follows all of them.
- `depth` ranges from 1 to 3 and defaults to 1.

Returns `{id, related: [{from, edge, to, title, status, depth}]}`. The walk visits each
document at most once.

### `review_health(domain?, review_status?)`

Returns one entry per document:
`{id, title, domain, status, last_reviewed, next_review, review_status, days_overdue}`.
`review_status` filters on one exact value, so `Overdue` does not include
`Severely Overdue`.

## Running without a library

AEGIS works without a library. Every agent that cannot reach `enterprise-standards-server`
says so, continues with best-effort proposals, and records that manual review is
required.

One gate needs a person to act. Implementation readiness checks whether current standards
were verified. Without a library, a person must review the approved artifacts against
your organization's standards by hand. After that review, pass the result explicitly:

```bash
python -m artifact_tools implementation readiness docs/artifacts/<app> <target-workspace> --standards-review verified
```

Until then, readiness reports the `standards-review` finding and blocks code generation.
This stops unreviewed designs reaching code by accident.

If you do not use a library at all, you can also remove `standards` from the `tools:`
lists in `aegis/agents/*.md` and run `python scripts/sync_platforms.py`. Agents on both
platforms then stop trying to call it.

## Security

- **Keep it read-only.** AEGIS only reads from the library. Do not add tools that modify
  documents.
- **Authenticate shared servers.** The reference server has no authentication. For a
  shared deployment, put it behind your organization's API gateway or a reverse proxy that
  enforces TLS and authentication, and keep the server bound to `127.0.0.1` or a private
  network.
- **Mind what you publish.** Agents copy standard ids and short extracts into artifacts,
  and artifacts may be committed to repositories. Leave out anything that must not appear
  there, or mark it `classification: confidential` and exclude it from the server.
- **Keep credentials out of git.** `.vscode/mcp.json` and `.mcp.json` are gitignored. Use
  VS Code `inputs` or Claude Code `${ENV_VAR}` expansion for secrets, as shown in
  [Step 4](#step-4-connect-your-agent-host).

## Troubleshooting

| Symptom | Likely cause and fix |
| --- | --- |
| Agent says *"Enterprise Standards MCP unavailable"* | The server is not running or not enabled. **Copilot:** start it from `.vscode/mcp.json` and check the tools picker in Copilot Chat. **Claude Code:** check that `.mcp.json` exists, restart Claude Code, approve the server and run `/mcp`. |
| Claude Code never offers to approve the server | `.mcp.json` is missing or not in the repository root, or the server was rejected earlier. Reset project MCP approvals with `claude mcp reset-project-choices`, then restart. |
| The token is not sent (Claude Code) | The environment variable was not set in the shell that started `claude`. Set it, then restart Claude Code. |
| Server fails to start with `ModuleNotFoundError: mcp` | `command` points at a Python without the dependencies. Install `requirements.txt` into it, or point `command` at your virtual environment. |
| Server starts but tools do not appear in agents | The server key is not exactly `enterprise-standards-server`. |
| Search returns nothing | Search defaults to `status: "Approved"`. Check the status values, or search with `status: "Any"` to confirm the documents loaded. |
| Edits to standards do not show up | The server loads documents at startup. Restart it. |
| Validation reports `references unknown id SEC-001` after citing a standard | The library id breaks the [ID convention](#id-convention). Rename it, for example to `ENT-STD-SEC-001`. |
| Server log shows `problem:` lines | Run `library.py --check` on the folder and fix the reported files. Documents with missing fields or duplicate ids are skipped; other problems are reported but the document still loads. |

# Reference Enterprise Standards server

A small, read-only MCP server that serves a folder of Markdown standards to the AEGIS
agents. Use it as is with your own documents, or as a working example when you build a
server in front of another system.

The full setup guide, including the document format, the ID convention and the
configuration for GitHub Copilot (`.vscode/mcp.json`) and Claude Code (`.mcp.json`), is in [`docs/enterprise-standards-setup.md`](../../docs/enterprise-standards-setup.md).

## Files

| File | Purpose |
| --- | --- |
| `library.py` | Loads and queries the knowledge base. Needs only PyYAML. Also validates a knowledge base with `--check`. |
| `server.py` | Exposes the library through the seven MCP tools the agents call. |
| `knowledge-base/` | Six sample documents. Replace them with your own. |
| `requirements.txt` | `mcp` (2.x) and `PyYAML`. |

## Run

```bash
pip install -r requirements.txt
python library.py --check knowledge-base          # validate
python server.py                                  # stdio, sample knowledge base
python server.py --knowledge-base /path/to/yours  # stdio, your standards
python server.py --transport streamable-http --port 8000   # shared, http://127.0.0.1:8000/mcp
```

The server has no authentication. Put it behind a gateway that enforces TLS and
authentication before you share it beyond `localhost`.

## Sample documents

| Id | Type | Status | Shows |
| --- | --- | --- | --- |
| `ENT-STD-SEC-000` | Standard | Superseded | A replaced standard, reached through `superseded_by`. |
| `ENT-STD-SEC-001` | Standard | Approved | `supersedes` and `depends_on` links. |
| `ENT-STD-DAT-001` | Standard | Approved | A review that is `Due Soon`. |
| `ENT-STD-API-001` | Standard | Approved | A family (`API Standards`) and a `related_to` link. |
| `ENT-PAT-001` | Pattern | Approved | A non-standard id that follows the ID convention. |
| `ENT-DEC-0001` | ADR | Approved | An enterprise decision whose review is `Overdue`. |

Review statuses depend on today's date, so they change over time.

"""Reference Enterprise Standards MCP server for AEGIS.

Serves a folder of Markdown standards (see ``knowledge-base/``) through the seven
read-only tools the AEGIS agents call. Run it over stdio for a single developer, or over
streamable HTTP to share one library across a team::

    python server.py                                   # stdio, ./knowledge-base
    python server.py --knowledge-base /srv/standards   # stdio, your own library
    python server.py --transport streamable-http --port 8000

The knowledge base is loaded once at startup; restart the server after editing it.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from library import KnowledgeBase

DEFAULT_KB = Path(__file__).resolve().parent / "knowledge-base"
READ_ONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)


def _checked(call, *args):
    """Report bad ids and arguments to the agent instead of as a server crash."""
    try:
        return call(*args)
    except KeyError as exc:
        raise ToolError(exc.args[0]) from exc
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


def build_server(kb: KnowledgeBase) -> MCPServer:
    server = MCPServer(
        name="enterprise-standards-server",
        instructions=(
            "Read-only Enterprise Standards library. Start with search_documents (metadata "
            "only, Approved by default), then get_document for the ids you need. Check "
            "supersession with get_related and freshness with review_health before relying "
            "on a document, and cite document ids exactly as returned."
        ),
    )

    @server.tool(annotations=READ_ONLY)
    def list_domains() -> list[dict[str, Any]]:
        """List the library's domains with total and Approved document counts."""
        return kb.list_domains()

    @server.tool(annotations=READ_ONLY)
    def list_tags() -> list[dict[str, Any]]:
        """List the controlled-vocabulary tags and how many documents use each."""
        return kb.list_tags()

    @server.tool(annotations=READ_ONLY)
    def list_families(family: str | None = None) -> list[dict[str, Any]] | dict[str, Any]:
        """List standard families, or the member documents of one family when `family` is given."""
        return kb.list_families(family)

    @server.tool(annotations=READ_ONLY)
    def search_documents(
        status: str | None = "Approved",
        type: str | None = None,
        domain: str | None = None,
        classification: str | None = None,
        tags: list[str] | None = None,
        version: str | None = None,
        part_of_family: str | None = None,
        query: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Find documents by metadata. Returns metadata only (no body).

        `status` defaults to "Approved"; pass "Any" to include every status. `tags` must all
        match. `query` is a case-insensitive substring match on title and summary.
        """
        return kb.search_documents(status, type, domain, classification, tags, version, part_of_family, query, limit)

    @server.tool(annotations=READ_ONLY)
    def get_document(id: str) -> dict[str, Any]:
        """Return one document's full body, metadata, relationships and review state."""
        return _checked(kb.get_document, id)

    @server.tool(annotations=READ_ONLY)
    def get_related(id: str, edge_type: str | None = None, depth: int = 1) -> dict[str, Any]:
        """Traverse the relationship graph from `id`.

        `edge_type` is one of supersedes, superseded_by, depends_on, required_by, related_to
        (all when omitted). `depth` is 1-3.
        """
        return _checked(kb.get_related, id, edge_type, depth)

    @server.tool(annotations=READ_ONLY)
    def review_health(domain: str | None = None, review_status: str | None = None) -> list[dict[str, Any]]:
        """Report review freshness: Current, Due Soon, Overdue, Severely Overdue or Unknown."""
        return kb.review_health(domain, review_status)

    return server


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--knowledge-base",
        type=Path,
        default=Path(os.environ.get("ENTERPRISE_STANDARDS_KB", DEFAULT_KB)),
        help="Folder of Markdown standards (default: $ENTERPRISE_STANDARDS_KB or ./knowledge-base).",
    )
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind address (streamable-http only).")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port (streamable-http only).")
    args = parser.parse_args()

    kb = KnowledgeBase(args.knowledge_base)
    # stdout carries the MCP protocol on stdio, so diagnostics go to stderr.
    for problem in kb.problems:
        print(f"[enterprise-standards] problem: {problem}", file=sys.stderr)
    print(f"[enterprise-standards] loaded {len(kb.documents)} document(s) from {args.knowledge_base}", file=sys.stderr)

    server = build_server(kb)
    if args.transport == "stdio":
        server.run("stdio")
    else:
        server.run("streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()

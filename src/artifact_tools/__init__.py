"""Deterministic tooling for all three AEGIS SDLC phases.

Public commands:
    scaffold    Create an artifact document from its template.
    validate    Check artifacts for schema, id, and cross-reference consistency.
    changelog   Append a changelog entry and bump the document version.
    adr         Create and index Architecture Decision Records.
    interfaces  Scaffold the native-format interface contract store.
    implementation  Manage readiness, work packages, decisions, evidence, and release.
"""

from artifact_tools.constants import ARTIFACT_TYPES, resolve_type

__all__ = ["ARTIFACT_TYPES", "resolve_type"]

"""Shared constants and small helpers for the artifact tooling."""

from __future__ import annotations

# Canonical artifact type -> metadata.
# `prefix` is the id prefix a document of this type is allowed to *define*.
ARTIFACT_TYPES: dict[str, dict[str, str]] = {
    "product-requirements": {
        "filename": "product-requirements.md",
        "prefix": "PR",
        "title": "Product Requirements",
    },
    "functional-requirements": {
        "filename": "functional-requirements.md",
        "prefix": "FR",
        "title": "Functional Requirements",
    },
    "non-functional-requirements": {
        "filename": "non-functional-requirements.md",
        "prefix": "NFR",
        "title": "Non-Functional Requirements",
    },
    "user-journey-map": {
        "filename": "user-journey-map.md",
        "prefix": "UJ",
        "title": "User Journey Map",
    },
    "system-blueprint": {
        "filename": "system-blueprint.md",
        "prefix": "BP",
        "title": "System Blueprint",
    },
    "executive-briefing": {
        "filename": "executive-briefing.md",
        "prefix": "RISK",
        "title": "Executive Briefing",
    },
    "interface-specifications": {
        "filename": "interface-specifications.md",
        "prefix": "IF",
        "title": "Interface Specifications",
    },
    "data-architecture": {
        "filename": "data-architecture.md",
        "prefix": "DM",
        "title": "Data Architecture",
    },
    "security-architecture": {
        "filename": "security-architecture.md",
        "prefix": "SEC",
        "title": "Security Architecture",
    },
    "deployment-topology": {
        "filename": "deployment-topology.md",
        "prefix": "DEP",
        "title": "Deployment Topology",
    },
    "observability-strategy": {
        "filename": "observability-strategy.md",
        "prefix": "OBS",
        "title": "Observability Strategy",
    },
}

# Convenience aliases accepted on the command line.
TYPE_ALIASES: dict[str, str] = {
    "prd": "product-requirements",
    "pr": "product-requirements",
    "product": "product-requirements",
    "fr": "functional-requirements",
    "functional": "functional-requirements",
    "nfr": "non-functional-requirements",
    "non-functional": "non-functional-requirements",
    "journey": "user-journey-map",
    "uj": "user-journey-map",
    "blueprint": "system-blueprint",
    "bp": "system-blueprint",
    "architecture": "system-blueprint",
    "briefing": "executive-briefing",
    "exec": "executive-briefing",
    "interfaces": "interface-specifications",
    "interface": "interface-specifications",
    "if": "interface-specifications",
    "api": "interface-specifications",
    "data": "data-architecture",
    "dm": "data-architecture",
    "data-model": "data-architecture",
    "security": "security-architecture",
    "sec": "security-architecture",
    "threat-model": "security-architecture",
    "deployment": "deployment-topology",
    "dep": "deployment-topology",
    "topology": "deployment-topology",
    "observability": "observability-strategy",
    "obs": "observability-strategy",
    "telemetry": "observability-strategy",
}

# All recognised id prefixes across the artifact set.
ALL_PREFIXES: tuple[str, ...] = (
    "PR",
    "FR",
    "NFR",
    "UJ",
    "BP",
    "RISK",
    "IF",
    "DM",
    "SEC",
    "DEP",
    "OBS",
    "ADR",
    "WP",
    "IDEC",
)

# Architecture Decision Records live in a folder of many files under the artifact
# directory, indexed by a README table. They are not single-file artifacts.
ADR_DIR: str = "architecture-decisions"
ADR_INDEX_FILENAME: str = "README.md"
ADR_TEMPLATE_FILENAME: str = "0001-adr-template.md"

VALID_ADR_STATUS: frozenset[str] = frozenset(
    {"proposed", "accepted", "rejected", "deprecated", "superseded"}
)

REQUIRED_FRONTMATTER: tuple[str, ...] = (
    "artifact",
    "title",
    "version",
    "status",
    "last_updated",
    "phase",
    "owner",
)

VALID_STATUS: frozenset[str] = frozenset(
    {"draft", "in-review", "approved", "superseded"}
)


def resolve_type(name: str) -> str:
    """Resolve a canonical type or alias to its canonical artifact type key."""
    key = name.strip().lower()
    if key in ARTIFACT_TYPES:
        return key
    if key in TYPE_ALIASES:
        return TYPE_ALIASES[key]
    raise KeyError(
        f"Unknown artifact type '{name}'. "
        f"Valid types: {', '.join(ARTIFACT_TYPES)}."
    )

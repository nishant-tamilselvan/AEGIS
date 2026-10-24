"""Optional ``aegis.config.yaml``: the extension points an organization edition uses.

Every key is optional, and a missing file means the defaults below, so the public
edition needs no config at all. The file can set:

==================  =========================================================
Key                 Effect
==================  =========================================================
``plugin``          Plugin name, description, author and repository URL used by
                    ``scripts/sync_platforms.py`` for the Claude Code plugin.
``overlay``         A folder of extra or replacement agents, prompts and skills
                    that ``sync_platforms.py`` merges on top of ``aegis/``.
``standards``       The MCP server name the agents call for Enterprise Standards.
``artifact_types``  Extra artifact types the CLI scaffolds, validates and gates.
==================  =========================================================

See ``docs/customizing.md`` for the full reference.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from artifact_tools import constants

CONFIG_FILENAME = "aegis.config.yaml"
# Points the CLI at a config file when it runs outside the repository that holds it.
CONFIG_ENV = "AEGIS_CONFIG"

DEFAULT_PLUGIN_NAME = "aegis"
DEFAULT_PLUGIN_DESCRIPTION = (
    "Agents that turn an idea into approved requirements, an implementable architecture and "
    "reviewed code, grounded in your enterprise standards."
)
DEFAULT_PLUGIN_AUTHOR = "Nishant Tamilselvan"
DEFAULT_REPO_URL = "https://github.com/nishant-tamilselvan/AEGIS"
DEFAULT_STANDARDS_SERVER = "enterprise-standards-server"

_SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
_SERVER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
_PREFIX_RE = re.compile(r"[A-Z][A-Z0-9]*")
# Source paths an overlay may replace: agents/<name>.md, prompts/<name>.md, skills/<name>/...
_OVERRIDE_RE = re.compile(r"(?:agents|prompts)/[^/]+\.md|skills/[^/]+/.+")

_TOP_LEVEL_KEYS = {"plugin", "overlay", "standards", "artifact_types"}
_PLUGIN_KEYS = {"name", "description", "author", "repo_url"}
_OVERLAY_KEYS = {"path", "overrides"}
_STANDARDS_KEYS = {"server"}
_TYPE_KEYS = {"prefix", "title", "template", "filename", "aliases", "required"}


class ConfigError(ValueError):
    """Raised when ``aegis.config.yaml`` is invalid."""


@dataclass(frozen=True)
class PluginIdentity:
    name: str = DEFAULT_PLUGIN_NAME
    description: str = DEFAULT_PLUGIN_DESCRIPTION
    author: str = DEFAULT_PLUGIN_AUTHOR
    repo_url: str = DEFAULT_REPO_URL


@dataclass(frozen=True)
class Overlay:
    path: Path
    overrides: tuple[str, ...] = ()


@dataclass(frozen=True)
class ArtifactType:
    key: str
    filename: str
    prefix: str
    title: str
    template: Path
    aliases: tuple[str, ...] = ()
    required: bool = True


@dataclass(frozen=True)
class AegisConfig:
    path: Path | None = None
    plugin: PluginIdentity = field(default_factory=PluginIdentity)
    overlay: Overlay | None = None
    standards_server: str = DEFAULT_STANDARDS_SERVER
    artifact_types: tuple[ArtifactType, ...] = ()


DEFAULT_CONFIG = AegisConfig()


# --------------------------------------------------------------------------- loading


def find_config(start: str | Path | None = None) -> Path | None:
    """The config file to use: ``$AEGIS_CONFIG``, else the nearest ``aegis.config.yaml``.

    The search walks up from `start` (default: the current directory). Returns None when
    there is no config, which means the defaults.
    """
    explicit = os.environ.get(CONFIG_ENV)
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_file():
            raise ConfigError(f"{CONFIG_ENV} points at {path}, which does not exist")
        return path.resolve()
    current = Path(start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        path = candidate / CONFIG_FILENAME
        if path.is_file():
            return path
    return None


def load_config(path: str | Path | None, *, root: str | Path | None = None) -> AegisConfig:
    """Parse and validate a config file. ``None`` returns the defaults.

    Relative paths in the file resolve against the file's own folder. The overlay folder
    must sit inside `root` (default: that same folder).
    """
    if path is None:
        return DEFAULT_CONFIG
    path = Path(path).resolve()
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path.name}: not valid YAML: {exc}") from exc
    if data is None:
        data = {}
    base = path.parent
    where = path.name
    _mapping(data, where, _TOP_LEVEL_KEYS)
    return AegisConfig(
        path=path,
        plugin=_plugin(data.get("plugin"), f"{where}: plugin"),
        overlay=_overlay(data.get("overlay"), f"{where}: overlay", base, Path(root).resolve() if root else base),
        standards_server=_standards(data.get("standards"), f"{where}: standards"),
        artifact_types=_artifact_types(data.get("artifact_types"), f"{where}: artifact_types", base),
    )


def _mapping(value: object, where: str, allowed: set[str]) -> dict:
    if not isinstance(value, dict):
        raise ConfigError(f"{where} must be a mapping")
    unknown = sorted(str(key) for key in set(value) - allowed)
    if unknown:
        raise ConfigError(f"{where}: unknown key(s) {', '.join(unknown)}; allowed: {', '.join(sorted(allowed))}")
    return value


def _text(value: object, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{where} must be a non-empty string")
    return value.strip()


def _plugin(value: object, where: str) -> PluginIdentity:
    if value is None:
        return PluginIdentity()
    data = _mapping(value, where, _PLUGIN_KEYS)
    values = {key: _text(data[key], f"{where}.{key}") for key in data}
    if "name" in values and not _SLUG_RE.fullmatch(values["name"]):
        raise ConfigError(f"{where}.name must be lower-case letters, digits and hyphens")
    if "repo_url" in values:
        if not values["repo_url"].startswith("https://"):
            raise ConfigError(f"{where}.repo_url must be an https:// URL")
        values["repo_url"] = values["repo_url"].rstrip("/")
    return PluginIdentity(**values)


def _overlay(value: object, where: str, base: Path, root: Path) -> Overlay | None:
    if value is None:
        return None
    data = _mapping(value, where, _OVERLAY_KEYS)
    if "path" not in data:
        raise ConfigError(f"{where}.path is required")
    path = (base / _text(data["path"], f"{where}.path")).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ConfigError(f"{where}.path must be inside {root}") from exc
    if path == root or path == (root / "aegis").resolve():
        raise ConfigError(f"{where}.path must be its own folder, not the repository root or aegis/")
    if not path.is_dir():
        raise ConfigError(f"{where}.path {path} is not a folder")
    overrides = data.get("overrides") or []
    if not isinstance(overrides, list):
        raise ConfigError(f"{where}.overrides must be a list of source paths")
    cleaned = []
    for item in overrides:
        rel = _text(item, f"{where}.overrides").replace("\\", "/")
        if not _OVERRIDE_RE.fullmatch(rel) or ".." in rel.split("/"):
            raise ConfigError(
                f"{where}.overrides entry {rel!r} must look like agents/<name>.md, "
                "prompts/<name>.md or skills/<name>/<file>"
            )
        cleaned.append(rel)
    return Overlay(path=path, overrides=tuple(cleaned))


def _standards(value: object, where: str) -> str:
    if value is None:
        return DEFAULT_STANDARDS_SERVER
    data = _mapping(value, where, _STANDARDS_KEYS)
    if "server" not in data:
        return DEFAULT_STANDARDS_SERVER
    server = _text(data["server"], f"{where}.server")
    if not _SERVER_RE.fullmatch(server):
        raise ConfigError(f"{where}.server must be letters, digits, '-' and '_'")
    return server


def _artifact_types(value: object, where: str, base: Path) -> tuple[ArtifactType, ...]:
    if value is None:
        return ()
    if not isinstance(value, dict):
        raise ConfigError(f"{where} must be a mapping of type name to settings")
    types = []
    for key, settings in value.items():
        here = f"{where}.{key}"
        if not isinstance(key, str) or not _SLUG_RE.fullmatch(key):
            raise ConfigError(f"{here}: type names are lower-case letters, digits and hyphens")
        data = _mapping(settings, here, _TYPE_KEYS)
        for required in ("prefix", "title", "template"):
            if required not in data:
                raise ConfigError(f"{here}.{required} is required")
        prefix = _text(data["prefix"], f"{here}.prefix")
        if not _PREFIX_RE.fullmatch(prefix):
            raise ConfigError(f"{here}.prefix must be upper-case letters and digits, such as PIA")
        template = (base / _text(data["template"], f"{here}.template")).resolve()
        if not template.is_file():
            raise ConfigError(f"{here}.template {template} does not exist")
        filename = _text(data.get("filename", f"{key}.md"), f"{here}.filename")
        if "/" in filename or "\\" in filename or not filename.endswith(".md"):
            raise ConfigError(f"{here}.filename must be a plain file name ending in .md")
        aliases = data.get("aliases") or []
        if not isinstance(aliases, list):
            raise ConfigError(f"{here}.aliases must be a list")
        required_flag = data.get("required", True)
        if not isinstance(required_flag, bool):
            raise ConfigError(f"{here}.required must be true or false")
        types.append(ArtifactType(
            key=key,
            filename=filename,
            prefix=prefix,
            title=_text(data["title"], f"{here}.title"),
            template=template,
            aliases=tuple(_text(alias, f"{here}.aliases").lower() for alias in aliases),
            required=required_flag,
        ))
    return tuple(types)


# --------------------------------------------------------------------------- applying


def register_artifact_types(types: tuple[ArtifactType, ...]) -> None:
    """Add configured artifact types to the CLI's registry in ``constants``.

    Registering the same type twice is a no-op, so repeated CLI runs in one process are
    safe. A type that clashes with an existing name, file, id prefix or alias is an error.
    """
    for item in types:
        meta = {"filename": item.filename, "prefix": item.prefix, "title": item.title}
        if constants.ARTIFACT_TYPES.get(item.key) == meta and constants.ARTIFACT_TEMPLATES.get(item.key) == item.template:
            continue
        where = f"artifact_types.{item.key}"
        if item.key in constants.ARTIFACT_TYPES or item.key in constants.TYPE_ALIASES:
            raise ConfigError(f"{where}: the type name is already used")
        if item.prefix in constants.ALL_PREFIXES:
            raise ConfigError(f"{where}: id prefix {item.prefix} is already used")
        if any(existing["filename"] == item.filename for existing in constants.ARTIFACT_TYPES.values()):
            raise ConfigError(f"{where}: file name {item.filename} is already used")
        for alias in item.aliases:
            if alias in constants.TYPE_ALIASES or alias in constants.ARTIFACT_TYPES:
                raise ConfigError(f"{where}: alias {alias!r} is already used")
        constants.ARTIFACT_TYPES[item.key] = meta
        constants.ARTIFACT_TEMPLATES[item.key] = item.template
        constants.TYPE_ALIASES.update({alias: item.key for alias in item.aliases})
        constants.ALL_PREFIXES = (*constants.ALL_PREFIXES, item.prefix)
        if not item.required:
            constants.OPTIONAL_ARTIFACT_TYPES.add(item.key)


def apply_workspace_config(start: str | Path | None = None) -> AegisConfig:
    """Find, load and apply the config that governs `start` (default: the current folder)."""
    config = load_config(find_config(start))
    register_artifact_types(config.artifact_types)
    return config

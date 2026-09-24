<!-- Generated from scripts/sync_platforms.py by scripts/sync_platforms.py. Edit the source, not this file. -->

# AEGIS plugin for Claude Code (v0.1.1)

Agents that turn an idea into approved requirements, an implementable architecture and reviewed code, grounded in your enterprise standards.

## Install

```text
/plugin marketplace add nishant-tamilselvan/AEGIS
/plugin install aegis@aegis
```

The agents call the AEGIS CLI, so install it for the Python on your PATH:

```bash
pip install aegis-sdlc
```

## Use

Run `/aegis:start-ideation <app-name> <idea>` in your repository. Artifacts are written to
`docs/artifacts/<app-name>/` in that repository. See the
[Claude Code plugin guide](https://github.com/nishant-tamilselvan/AEGIS/blob/main/docs/claude-code-plugin.md).

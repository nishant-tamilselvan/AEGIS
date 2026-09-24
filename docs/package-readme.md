# aegis-sdlc

The command-line tool behind [AEGIS](https://github.com/nishant-tamilselvan/AEGIS), a set
of agents for GitHub Copilot and Claude Code that turn an idea into approved
requirements, an implementable architecture and reviewed code.

The agents call this CLI to keep their documents consistent. You can also use it on its
own, for example in CI, to scaffold and validate AEGIS artifacts.

## Install

```bash
pip install aegis-sdlc
```

This installs the `artifact-tools` command. Python 3.10 or later is required.

## Use

```bash
artifact-tools scaffold product-requirements docs/artifacts/my-app --project "My App"
artifact-tools validate docs/artifacts/my-app --strict
artifact-tools adr new "Use PostgreSQL" docs/artifacts/my-app/architecture-decisions --status accepted
artifact-tools implementation readiness docs/artifacts/my-app /path/to/target-repo
```

The artifact and implementation templates are bundled with the package. Inside a
repository that has its own `aegis/skills/.../templates` folders, those are used instead,
so customized templates keep working.

## Claude Code plugin

To install the AEGIS agents themselves into your repository, add the plugin in Claude
Code, then install this package for the CLI:

```text
/plugin marketplace add nishant-tamilselvan/AEGIS
/plugin install aegis@aegis
```

See the [plugin guide](https://github.com/nishant-tamilselvan/AEGIS/blob/main/docs/claude-code-plugin.md).

## Learn more

- [AEGIS on GitHub](https://github.com/nishant-tamilselvan/AEGIS): the agents, prompts
  and skills for GitHub Copilot and Claude Code. If AEGIS is useful to you, a ⭐ on
  GitHub helps other teams find it.
- [CLI reference](https://github.com/nishant-tamilselvan/AEGIS/blob/main/docs/cli-reference.md)
- [A complete example](https://github.com/nishant-tamilselvan/AEGIS/tree/main/examples/artifacts)
- [Changelog](https://github.com/nishant-tamilselvan/AEGIS/blob/main/CHANGELOG.md)

MIT licensed.

# paseo-auto-zh

**[简体中文](README.md) · [English](README.en.md)**

[![License: MIT](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

A Chinese-language Agent Skill for [Paseo](https://paseo.sh) that runs the full
dispatch loop: dispatch a worker into an isolated workspace, supervise it, gate the
result, and merge two-way-door PRs.

## Install

```bash
npx skills add whutlichao/paseo-auto-zh --skill paseo-auto-zh
```

Or copy `skills/paseo-auto-zh/` to `~/.agents/skills/paseo-auto-zh/`.

## What it covers

- Dispatching one or more tickets into supervised workers with a five-part spec and an
  absolute pre-skill path.
- Handing a complete ticket map to a single long-horizon `implement-spec` worker.
- Gate acceptance per ticket type (docs / spec / tickets / implementation / merge),
  with rejection when evidence is missing.
- Auto-merging two-way-door PRs after the gates pass; one-way doors and unclear cases
  go to the human.
- Failure handling: daemon down, MCP errors, lost notifications, crashed agents —
  gather evidence and report precisely instead of re-dispatching blindly.

The skill body and its trigger conditions live in `skills/paseo-auto-zh/SKILL.md`
(written in Simplified Chinese, matching the upstream `orchestra-auto-zh` discipline).

## Development

```bash
python3 -m unittest discover -s tests -v
```

## Note

Paseo is a third-party product. This repository is not an official Paseo repository
and is not endorsed by it. It ships only this skill's text and evals.

## License

MIT

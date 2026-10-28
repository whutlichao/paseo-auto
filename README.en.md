# paseo-auto

**[简体中文](README.md) · [English](README.en.md)**

[![License: MIT](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

An Agent Skill for [Paseo](https://paseo.sh) that runs the full dispatch loop: dispatch a worker into
an isolated workspace, supervise it, gate the result, and merge two-way-door PRs. The repository ships
two content-equivalent variants: `paseo-auto-zh` (Simplified Chinese) and `paseo-auto` (English); their
flow, gates, reference file names and eval scenarios match one to one.

Dispatching is easy; the last 20% is the hard part. This skill covers that 20%: which workspace a
worker lands in, when a merge happens, when a human must be asked, and how to recover from a lost
notification or a crashed agent.

## Install

```bash
# Simplified Chinese
npx skills add whutlichao/paseo-auto --skill paseo-auto-zh

# English
npx skills add whutlichao/paseo-auto --skill paseo-auto
```

Or copy `skills/paseo-auto-zh/` or `skills/paseo-auto/` to `~/.agents/skills/<same name>/`.

## What it covers

| Case | Behaviour |
| --- | --- |
| One or more tickets to implement | Builds a supervised worker in an isolated worktree, with the five-element spec plus the pre-skill's absolute path |
| A complete ticket map to implement long-horizon | Dispatches exactly one `implement-spec` worker and closes on the integration PR |
| Gate acceptance and send-back | Runs G-docs / G-spec / G-tickets / G-impl / G-merge per ticket type; sends work back when evidence is missing |
| Two-way-door PRs | Auto-merges and syncs the main branch after the gates pass; one-way doors and unclear cases go to the human |
| Blocked execution | Daemon down, MCP errors, lost notifications, crashed agents: gather evidence and report precisely instead of re-dispatching blindly |
| Process errors | Retro per the retro reference: fix the process instead of retrying harder |

The trigger and exclusion conditions live in both `SKILL.md` frontmatters: use the skill when the user
mentions Paseo orchestration, worker dispatch, workspace/worktree isolation, acceptance gates, PR
auto-merge, or dispatch troubleshooting; plain question answering, read-only review, and Orca-side
orchestration do not start it.

## Layout

```text
skills/
├── paseo-auto-zh/                # Simplified Chinese variant
│   ├── SKILL.md                  # routing and core constraints (references are read on demand)
│   ├── references/               # 11 reference files, read on demand
│   └── evals/evals.json          # behavioural eval scenarios
└── paseo-auto/                   # English variant, section-for-section equivalent
    ├── SKILL.md
    ├── references/               # exactly the same file names as the Chinese variant
    └── evals/evals.json
```

Both variants' `references/` directories are identical in name and shape:

```text
references/
├── dispatch-preflight.md      # pre-dispatch tick sheet / teardown checks
├── dispatch-loop.md           # workspace / agent parameters, profile materialization, turn confirmation
├── spec-contract.md           # the template and criteria for a worker's spec
├── reply-protocol.md          # question classification: decisions to the human, details answered for them
├── gate-acceptance.md         # gates and merge execution
├── notifications-and-waiting.md
├── agent-recovery.md
├── long-horizon-tickets.md
├── gates-docs-planning.md
├── reformat-noise-recovery.md
└── failure-and-reporting.md
```

It shares its lineage with [`orchestra-auto`](https://github.com/whutlichao/orchestra-auto) on the Orca
side: the same supervision, isolation, gate and merge discipline, with Paseo's MCP / CLI as the control
plane.

## Development

```bash
python3 -m unittest discover -s tests -v
```

The tests need no network, credentials or particular machine: they walk every `skills/*/SKILL.md`,
check frontmatter, reference reachability, eval parseability and the absence of absolute home paths,
and verify that both skill variants ship the same reference file names and eval scenario ids, with no
CJK characters in the English variant.

## Note

Paseo is a third-party product. This repository is not an official Paseo repository and is not endorsed
by it. It ships only this skill's Chinese and English text and evals, not Paseo itself or any other
paseo-* skill.

## License

MIT

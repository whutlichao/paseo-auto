# Long-horizon ticket maps: implement-spec, one integration PR, door-aware merging

**When to read this**: G-tickets has accepted a complete ticket map and this round implements it; you
are about to dispatch or accept a long-horizon worker; you must judge whether an integration PR may
auto-merge; or a process error calls for a retro.

## Contents

- [1. Entry conditions: a complete ticket map](#1-entry-conditions-a-complete-ticket-map)
- [2. Dispatch exactly one long-horizon worker](#2-dispatch-exactly-one-long-horizon-worker)
- [3. Nested topology and Paseo's isolation capability](#3-nested-topology-and-paseos-isolation-capability)
- [4. Coordinator acceptance](#4-coordinator-acceptance)
- [5. Door-aware merging](#5-door-aware-merging)
- [6. Retro after a process error](#6-retro-after-a-process-error)
- [7. Fallbacks and stop conditions](#7-fallbacks-and-stop-conditions)

## 1. Entry conditions: a complete ticket map

`implement-spec` needs one spec plus one task map. Before dispatching, all of the following must hold:

- A spec pointer exists (a spec file or a parent issue). If this round only produced tickets, synthesize
  the pointer from the parent issue or the design document; with neither a spec nor a parent issue, go
  back to `to-spec` — do not invent one.
- Every ticket has a title, **what to build**, acceptance criteria, and a state the tracker can close.
  A local file tracker uses `.scratch/<feature>/issues/<NN>-<slug>.md`; a real tracker with native
  blocking edges should use those native edges.
- Every blocker points at a ticket that really exists. The graph is acyclic and the frontier has at
  least one ticket to pick up. A dependency pointing at a nonexistent or abandoned-closed ticket is a
  broken graph, not a frontier.
- The tracker is reachable: `docs/agents/issue-tracker.md` exists and the worker can use its command
  surface (`gh` / `glab` logged in, or local ticket files visible from the worktree). A gitignored
  `.scratch` does not appear in a fresh worktree, so expose it to the worker through an absolute path
  on a shared filesystem, or commit the ticket files into the repository; otherwise the tickets cannot
  be read.
- Every ticket fits in a fresh context; pre-refactor and expand–contract tickets come first. If a
  ticket is too big, go back to `to-tickets`; do not let `implement-spec` discover it halfway through.

A settled single ticket still goes down channel B. This path is for a ticket map, not a wrapper around
one ticket.

## 2. Dispatch exactly one long-horizon worker

Start one supervised worker for the whole map, not one per ticket:

```text
create_workspace({
  isolation: "worktree", mode: "branch-off", path: <repo>,
  branchName: "<feature>-integration", baseBranch: "<this round's default base, usually origin/main>",
  worktreeSlug: "<feature>-integration", title: "<feature> integration"
})
create_agent({
  title: "<feature> integration", provider: <profile>, workspaceId: <ws>,
  notifyOnFinish: true, initialPrompt: <long-horizon spec>
})
```

The spec is a set of pointers, not a copy of the tickets. It must contain (full template in
[spec contract](spec-contract.md) §4.4.4):

```text
Pre-skill: <absolute path>/implement-spec/SKILL.md — read it in full before starting.
Skill resolution: use the Skill tool for `tdd` / `code-review` when available; otherwise read
<absolute path>/tdd/SKILL.md and <absolute path>/code-review/SKILL.md directly — do not paraphrase.
PR skill: <absolute path>/pr/SKILL.md — use it to write the single integration PR body.
Tracker: <docs/agents/issue-tracker.md or the absolute path of the local ticket directory>.
Spec: <absolute path or issue URL>.
Tickets: <tracker query / local directory; state the frontier and the blocking edges>.
Integration branch: <name>; base: <this round's default base, usually origin/main>.
Concurrency: at most <N> implementers; default 3 unless the user or the repository says otherwise.
```

This worker is an **orchestrator** and must not implement tickets itself. It maintains the map and the
frontier, starts a fresh implementer for each ready ticket, merges their branches through a merger
step, runs the final review and opens the PR. Context pointers to the spec, tickets, notes and commits
are the communication channel; do not restate the whole map in every prompt.

Each implementer reports its own workspace, branch, commit, tests, and what it merged from the
integration branch. All decision-class questions — scope, user-observable behaviour, approach forks or
the escalation five — go up through the top-level worker to the coordinator. A worker must not answer
for the human.

## 3. Nested topology and Paseo's isolation capability

`implement-spec` assumes every implementer has its own worktree. In Paseo the top-level worker achieves
that by calling `create_workspace` + `create_agent` itself. That assumption must be proven before the
map is spent. The worker's first report must state:

1. it can create a worktree workspace whose branch is cut from the integration branch;
2. it can create a separate agent per ticket (`workspaceId` pointing at that workspace,
   `notifyOnFinish: true`), or run implementers in parallel in the background, or explicitly switch to
   serial;
3. it can merge branches without editing the main working copy.

When isolation holds, run implementers in parallel along the frontier, up to the concurrency limit.
Each implementer confirms its workspace is based on the integration branch, invokes `tdd`, merges the
integration tip into its own branch before reporting completion, and keeps the branch clean. A merger
subagent — or the worker itself when the harness has no subagents — merges finished branches into the
integration branch in DAG order, re-running the affected tests after each merge.

When isolation cannot be proven, **never let two implementers share one worktree**. Switch to serial
work, one ticket at a time, inside the worker's own workspace, and record the degradation. When the
worker cannot create subagents at all, fall back to the per-ticket worker model in §7 and state the
reason in the report.

The top-level worker is still accountable for the nested agents' workspaces, branches and output; the
coordinator never enters a nested workspace.

## 4. Coordinator acceptance

The coordinator accepts the **integration PR**, not each nested branch. Check:

- The whole map produced one PR (or a recorded fallback); the head matches the final accepted SHA;
  before it is marked ready, the integration branch has been rebased onto the current default base.
- Every ticket's branch is merged; no ticket exists only inside a workspace. Each ticket is closed the
  way the tracker closes them, and the PR body carries `Closes` links for the spec and the tickets.
- The final tree passes the applicable full gates. Spot check at least two tickets' evidence — their
  tests and acceptance criteria — instead of trusting the summary. Per-ticket TDD is the implementer's
  contract; one two-axis `code-review` on the integration branch is this path's review gate. Record
  that choice in the report.
- The worker cleaned up the nested workspaces; the main working copy is untouched; there are no
  unexplained uncommitted changes.

On a missing branch, a red test, an unclosed ticket or a stale head, send the findings back to the
top-level worker. The coordinator does not enter a nested workspace and does not complete a ticket
itself.

## 5. Door-aware merging

The worker writes the PR body with the `pr` skill, including `Door`, `Blast Radius` and the evidence.
The coordinator then checks the door claim against the real diff. The worker's label is input, not
proof.

**The one-way trigger list is the single list in [gate-acceptance](gate-acceptance.md) G-merge item
0**; this file keeps no copy, so two paths cannot reach different conclusions about the same PR. When
unsure, treat it as one-way. A two-way door is necessary, not sufficient: G-merge still applies and
repository rules still win.

When a trigger appears in the diff, treat the PR as one-way even if the body says two-way. Send it back
to the worker to fix the body, then treat it as one-way.

- **Two-way door + G-merge all green + the repository allows it** → auto-merge, sync main, close the
  tickets.
- **One-way door, uncertain, a red gate, or a rule that blocks it** → stop at the open PR. Report the
  door, the evidence, the blast radius and the exact action for the human to merge manually. Do not
  merge, do not sync main, do not ask once more for auto-approval. The human merges manually; the open
  PR is this round's endpoint.

## 6. Retro after a process error

Product bugs go through send-back. A **process error** is a harness defect that can recur: a worker
crossing the role boundary, a gate accepting a red result, two consecutive dispatch failures for the
same cause, notifications stalling, a misjudged ticket type, scope drift, a misjudged merge door, or
the same gate sent back repeatedly.

When one appears, preserve the evidence first and, when safe, continue the round. At a safe point, run
`retro` read-only: read its skill file, then the primary sources — the session, the worker transcript
(`paseo logs` / `get_agent_activity`), `git`/PR evidence, the ledger and the gate results. `retro` is
normally user-triggered, so treat this round's request for it as authorization for a read-only analysis
and **not** as authorization to land changes. Without the Skill tool, read the `writing-for-agents`
skill file directly. Save `retro-candidates.md` **outside the target repository**, ordered by severity.
For each candidate write the category (navigation, automated checks, coding standards, AGENTS.md, tool
economy, ineffective instructions, information acquisition), the evidence, the exact file or check to
change, how to verify it, and the risk.

Hand the candidates to the human. Do not land them automatically. Once the human selects candidates,
dispatch a worker to land them through the normal gates: for this skill's repository that means two
language variants, matching evals, tests and READMEs; for a target repository it means following that
repository's conventions. Write the PR with the `pr` skill and add one eval per accepted candidate so
the defect cannot regress silently. While this round is still running, landing improvements waits for
the round's endpoint; a retro never modifies the skill mid-run.

## 7. Fallbacks and stop conditions

| Condition | Action |
| --- | --- |
| The map is incomplete (cycles, missing blockers, no acceptance, unreachable tracker) | Send it back to G-tickets / `to-tickets`; do not dispatch. |
| Only one settled single ticket | Channel B; one worker, one workspace. |
| The worker cannot prove isolated workspaces/agents | Run implementers serially inside its own workspace; record the degradation. |
| The worker cannot run subagents | Per-ticket Paseo workers, default concurrency 3; record the fallback. |
| The integration PR is a one-way door | Keep it open; the human merges manually. |
| Nested workspaces left behind, or main was modified | Preserve the scene, send it back, do not accept. |
| The worker stalls or is unreachable | Handle it per [agent recovery](agent-recovery.md); do not dispatch a second editor. |

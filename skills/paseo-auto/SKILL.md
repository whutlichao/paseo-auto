---
name: paseo-auto
description: >-
  Use to dispatch work in Paseo, supervise tasks, or drive authorized development or planning work to
  acceptance and auto-merge. Covers: supervised workers in isolated worktrees; a complete map handed to
  `implement-spec`; Merge Danger deciding auto-merge vs human merge; gate acceptance, send-back, PR
  merge, main-branch sync; process-error retro. Also covers blocked execution (daemon down,
  `paseo status` timeouts, MCP `create_agent` / `send_agent_prompt` errors or permission denied, lost
  notifications, crashes, breakers): "how can we keep going", "should we report", "don't just
  re-dispatch" — gather evidence, report precisely, never re-dispatch. Triggers: Paseo orchestration,
  worker dispatch, worktree isolation, gates, PR auto-merge, dispatch troubleshooting. Exclusions: Orca
  workers use `orchestra-auto`; message/DAG coordination uses `orchestration`; single-agent queries,
  second opinions, handoffs use `paseo` / `paseo-advisor` / `paseo-handoff`. Plain Q&A and reading or
  reviewing this skill start no run.
---

# Paseo Auto — the fully automatic dispatch loop

You are the coordinator. Start by pinning down the scope the user asked for. Any change that lands
in a project repository this round is by default committed by a worker, pushed on a branch, and
opened as a PR; once the gates pass, the coordinator merges it automatically and syncs the main
branch. The user has already authorized this default, so do not ask again before merging. "Open a PR
when you're done" and "give me a PR" describe how the work lands, not where the round stops; the only
open-PR exception is an explicit request to **keep the PR unmerged and look at it yourself**. If the
user asks for that exception, if repository rules block the merge, or if a gate has not passed, keep
the PR and report the real state. Pure Q&A and reports that write no repository files create no PR.

A human appears at three moments: they said one sentence when the task started; a worker asks a
decision-class question and the human is invited to settle it (§5); or something genuinely requires
a human (credentials / third party / approval / permissions). **What auto automates is the process
(dispatch / gates / send-back), not the decisions** — a worker's recommended answer is reference
input only. For anything §5 classifies as decision-class, attach your own leaning, ask the human to
settle it, and only then reply to the worker.

This skill supplies the orchestration procedure; the user's request, the repository's conventions and
Paseo's current tool contract decide this round's scope and execution. Channel selection is §1, role
boundaries §2, and dispatch parameters §4. It does not depend on the target repo's `AGENTS.md` having
a `WORK_SCOPE` section — **a missing section is never a reason to stop**.

```text
user input → §1 pin the delivery endpoint and channel → §2 hard-rule self-check → §4 create a workspace + agent when edits are needed
              → §5 answer when a completion or question notification arrives (decisions go to the human) → §6 gate acceptance
              → send back or advance → after a two-way-door PR passes G-merge, §6.5 auto-merge
              → archive the agent / workspace → §7 closing report; stop at the agreed delivery endpoint
```

Files under `references/` are read conditionally; SKILL.md keeps the routing and the core
constraints:

| File | When to read it |
| --- | --- |
| `references/dispatch-preflight.md` | Before every dispatch (tick every line), and at teardown after a worker reports completion but before you claim a gate passed |
| `references/dispatch-loop.md` | Every B/C dispatch (full workspace/agent parameters, profile materialization, turn confirmation, CLI fallback) |
| `references/spec-contract.md` | When writing a worker's spec, on any channel and for any ticket type |
| `references/reply-protocol.md` | When classifying or answering a worker question, or deciding whether to escalate to the human or answer for them |
| `references/gate-acceptance.md` | When a ticket closes and you pick a gate; when merging a project PR or archiving an agent / workspace |
| `references/notifications-and-waiting.md` | Before each Run's first dispatch, after every notification, and when a notification never arrives or a worker looks unreachable |
| `references/agent-recovery.md` | `create_agent` fails, a turn never starts, a permission request arrives, or an agent crashes or is closed |
| `references/long-horizon-tickets.md` | G-tickets accepted a complete ticket map and this round implements it; or a process error calls for a retro |
| `references/gates-docs-planning.md` | This ticket is a design / spec / ticket-splitting ticket heading for G-docs / G-wayfinder / G-spec / G-tickets |
| `references/reformat-noise-recovery.md` | §4.0.1 finds tens of thousands of lines of uncommitted change (formatter reflow noise) |
| `references/failure-and-reporting.md` | The Paseo daemon is unavailable, an MCP tool is missing, a breaker trips, or a report is due |

## 0. Initialize only when executing orchestration; editing this skill does not start a run

Enter the flow below only when the current task actually asks for Paseo orchestration. When the user
asks to modify or review this skill, it is material to be edited: create no workspace, dispatch no
agent, and do not switch roles just because you read the body text. Use §1 to decide whether this
round really needs a worker.

Right before dispatching, confirm the Paseo control plane is available: prefer the in-session Paseo
MCP tools (`create_workspace`, `create_agent`, `send_agent_prompt`, `get_agent_status`); when MCP is
absent, fall back to the CLI, which requires `paseo status --json` to report a healthy daemon —
otherwise stop and report. **Always prefer MCP for dispatch**: only MCP `create_agent` /
`send_agent_prompt` arm the completion notification; CLI dispatch does not (see
[notifications and waiting](references/notifications-and-waiting.md)).

Read `list_profiles` once right before dispatching, and record the profiles available this round plus
their `notes`; a profile the user named wins, otherwise pick the one whose notes best fit this
ticket. When no profile fits, use `list_providers` / `inspect_provider` to discover capabilities, and
tell the user explicitly that this is a fallback path. A profile is startup configuration only — do
not remember it across Runs or infer drift. Pure channel-A answers do not look up profiles.

```text
mode paseo-auto | channel <A|B|C> | intent <task type> | pre-skill <actual path / none> | worker <profile → provider/model / none> | delivery endpoint <answer / report / merged project change / other endpoint the user named>
```

All six columns need **concrete values**; "TBD" is not allowed. When not dispatching, write "none"
for worker. When dispatching, the pre-skill column must be the **actual absolute path** in the form
`<skill root>/<name>/SKILL.md`, chosen by request type from §1: single-ticket implementation =
`implement`, bug fix = `diagnosing-bugs`, research / design / spec / ticket splitting = `research` /
`grill-with-docs` / `to-spec` / `to-tickets`, complete ticket map = `implement-spec`. A bare skill
name does not count; what spec-contract requires is exactly that absolute path. Take the worktree
name as a slug at dispatch time.

Before this round's first dispatch, resolve the **round default base** once:
`git symbolic-ref --short refs/remotes/origin/HEAD`, falling back to
`gh repo view --json defaultBranchRef --jq .defaultBranchRef.name`; write the result into the mode
declaration and the ledger, and use it for every `baseBranch` below. Hard-coding `origin/main` in a
repository whose default branch is `master` / `develop`, or whose remote is not called `origin`,
either fails worktree creation outright or branches off the wrong baseline.

## 1. Channel and delivery endpoint

Record what the user asked for and where it stops. Project changes get a PR created and merged
automatically by default; a one-way Merge Danger door is the exception and keeps an open PR for a
human to merge manually. Exploration may change the implementation path; it may not widen the work.

| Request | Channel | Handling |
| --- | --- | --- |
| Explanation, status, discussion, or a verbal research conclusion | A | Answer directly; no worker, no repository writes |
| A clearly bounded small change, a bug fix, an existing spec or ticket | B | Read-only exploration, then dispatch an implementation worker; for a bug fix use `diagnosing-bugs` first |
| Research, design, spec or ticket splitting that must land on disk | B/C | The matching `research` / `grill-with-docs` / `to-spec` / `to-tickets`; stop at the agreed artifact |
| A multi-ticket or not-yet-converged full implementation request | C | Converge on requirements and dependencies first; once G-tickets accepts a complete ticket map, dispatch **one** long-horizon `implement-spec` worker |
| External issues/PRs, conflicts, or terminology governance | B/C | The repository's triage, conflict-handling or domain-modeling flow |

When the fog is heavy enough that no stable requirement can be formed, `wayfinder` can produce a map
and decision tickets; read the target repository's wayfinding conventions first and do not invent
labels. If the change would overturn an existing ADR or planned decision, settle that decision first.
A full implementation request normally runs
`grill-with-docs → to-spec → to-tickets → implement-spec`; with a valid spec or ticket, enter at the
matching stage. A settled single ticket still goes down channel B; only a complete ticket map uses
`implement-spec`. If only design was asked for, close once that design artifact's PR is merged; the
open-PR exception needs an explicit request to keep the PR unmerged (criterion in §0) — asking for a
PR is not that exception.

If §4.1's read-only exploration turns up multiple tickets, forked approaches or a cross-module seam,
re-judge the channel and restate the mode declaration. If the scope itself is unclear, ask the human
to settle it per §5; never convert a discussion request into implementation authorization.

## 2. Role boundary: the coordinator plans and accepts, workers edit and commit

- The coordinator does read-only exploration, task splitting, dispatch, message handling, answering,
  acceptance, and executing authorized PR merges.
- With a long-horizon ticket map, nested implementers are the top-level worker's subagents. The
  coordinator talks only to the top-level worker, never enters a nested workspace, and treats the
  top-level worker as accountable for nested branches, merges and cleanup.
- Every addition, deletion, edit, format, restore, conflict resolution, stage, commit, push and PR
  body for a project file is done by a worker inside that ticket's workspace (including governance
  documents, ticket status and Answer text, and one-line fixes). **The coordinator must never edit or
  commit inside a worker's workspace, and must never bypass this with a script or another agent.**
- The coordinator may write task specs, communication ledgers, evidence and reports outside the
  repository; `/tmp` holds process artifacts and `~/.paseo-auto/` holds the persistent audit. Landing
  files inside the project is the worker's job.
- Check who is writing and where before every write. If project files / the index / branch content
  would change ⇒ dispatch a worker. Acceptance caches and artifacts go in a temporary acceptance
  directory and never update the user's main working copy.
- **Paseo places an agent in the caller's workspace by default**; this skill overrides that default:
  an implementation ticket must create an isolated worktree workspace first and the agent second
  (§4.3). The coordinator never opens a worker inside its own workspace.
- The coordinator may create an isolated acceptance workspace, fetch, run checks and merge PRs; after
  each merge **pull the merged main branch** per §6.5.1 — that is syncing accepted work, not
  implementing. Only a clean main working copy may run `git pull --ff-only`; do not reset, do not
  auto-stash, and do not switch the user's current branch.
- On a missed change, formatter noise, a missing commit/PR, or a merge conflict: list the evidence and
  send it back to the worker. When a worker is unreachable, confirm its state per
  [recovery](references/agent-recovery.md) and resume or replace it; the coordinator does not take
  over the implementation.
- `detach` (turning a subagent into an independent top-level agent) is the user's manual action in
  subagents; the coordinator does not call it.

## 3. Lightweight implementation

A single ticket whose approach is settled and whose blast radius can be bounded goes down channel B:
one isolated worktree, a short spec, and verification proportionate to the risk. A bug fix needs
regression evidence that reproduces on the old code and passes on the new. Pure copy, style or
configuration changes are accepted with the applicable check and an observable result; do not
manufacture red-green tests for them. Project file changes are committed to a PR and auto-merged by
default.

A two-axis review may be omitted for a small bounded change (record the reason in the spec and the
Answer); a cross-ticket change, a shared interface or an unclear blast radius gets wider G-impl
verification. Documentation / planning tickets run their own gates. Small size never changes the role
boundary: authorized implementation still edits inside an isolated worktree, by a worker.

## 4. Dispatch (channels B / C)

### 4.0 Pre-dispatch preflight

Tick every line of [dispatch preflight](references/dispatch-preflight.md); do not dispatch until all
are green. The three mechanical criteria are the `Test tier:` line in an implementation ticket's
spec, the literal `code-review`, and a base-commit check for every baseline number. After a worker
reports completion and before you claim a gate passed, run that file's teardown / formatter-noise
checks.

### 4.1 Read-only exploration

First, on main, gather the facts needed to write the spec (at most three parallel reads).
**Exploration's endpoint is the spec, not the edit** — "I could just change this line myself" is the
signal to dispatch, not a licence to skip it.

### 4.2 Choose the worker configuration

Before dispatching, read the profile materialization section of
[dispatch loop](references/dispatch-loop.md): materialize the chosen profile's `provider`, `model`,
`modeId`, `thinkingOptionId` and `featureValues` into `create_agent`'s `provider` and `settings`;
omit what is missing, and do not fill gaps from memory. With no profile, run `inspect_provider` first
and set only the feature IDs it returned. When the provider cannot be determined, stop and report; do
not guess a model name.

### 4.3 ★ Hard override: one task, one isolated worktree workspace

Paseo's agent-scoped `create_agent` lands in **your current workspace** by default; dispatching an
implementation ticket that way puts the worker in main. **paseo-auto overrides that default: every
task creates a worktree workspace first, then an agent inside it.**

```text
create_workspace({
  isolation: "worktree",
  mode: "branch-off",
  path: <absolute path to the target repo>,
  branchName: <ticket slug>,
  baseBranch: "<this round's default base, usually origin/main>",
  worktreeSlug: <ticket slug>,
  title: <ticket title>
})
create_agent({
  title: <ticket title>,
  provider: <profile → provider/model>,
  workspaceId: <workspaceId from the step above>,
  initialPrompt: <the §4.4 spec>,
  notifyOnFinish: true,
  labels: { "ticket": <ticket slug>, "run": <run id> },
  settings: { modeId, thinkingOptionId, features }
})
```

- **Never omit `workspaceId`**; never reuse the coordinator's own workspace or another ticket's
  workspace.
- `branchName` and `worktreeSlug` use the same ticket slug; `baseBranch` explicitly carries the
  round default base resolved in §0 (usually `origin/main`). Do not write a bare `main` — a bare name
  prefers the local main, which may not be the baseline you want.
- `notifyOnFinish: true` must be written explicitly. Although the agent-scoped default is true,
  writing it makes the receipt's `guidance` checkable and avoids a silent break if the default
  changes later.
- When the session cwd is not the target repo, `create_workspace.path` takes an absolute path. Paseo
  resolves it on the machine running the daemon.
- A long-horizon worker uses the same parameters with `branchName` set to `<feature>-integration`; it
  creates nested workspaces for implementers itself and degrades to serial work when isolation
  cannot be proven — see [long-horizon tickets](references/long-horizon-tickets.md).
- Dispatch through the CLI only as a fallback when MCP is unavailable; the CLI does not arm
  completion notifications, so run the bounded mode from
  [notifications and waiting](references/notifications-and-waiting.md).

### 4.3.1 Confirming the turn started after dispatch

`create_agent` returns `status` and `guidance`. When `guidance` says
"You will get notified when the created agent finishes…", the notification is armed; when it falls
back to "Observe completion using get_agent_status…", the notification is **not** armed — use the
bounded mode from the notifications reference.

`status: running` means the turn was accepted, but whether the first tool call actually executed
needs one more `get_agent_status` check; if it is immediately `idle` with no assistant output, read
`get_agent_activity` to tell "just created, not started yet" from "failed at the start" — do not wait
blindly. The exact criteria are in [agent recovery](references/agent-recovery.md).

### 4.4 The spec contract

Write the spec from the [spec contract](references/spec-contract.md) template; every element is
required, including the behaviour rules, the pre-skill's absolute path, the ticket-type and gate
line, an implementation ticket's `Test tier:` line (narrow/wide; a narrow tier states why the blast
radius is bounded), and the `Not run this ticket:` line. A worker sees only the spec, so anything
left out is not done.

### 4.5 A completion notification is the communication loop

Paseo's supervised worker sends "finished / errored / needs permission / was closed" back to the
coordinator through `notifyOnFinish`. A **terminal notification** (finished / errored / was closed /
was canceled) fires once; a **permission notification is not terminal** — `respond_to_permission`
does not change the armed state, so the terminal notification for that turn still arrives after you
answer, and you must not send a message just to "re-arm". **`send_agent_prompt` re-arms by default**,
so answering a worker's question once is the same as installing the next wait. Read
[notifications and waiting](references/notifications-and-waiting.md) before dispatching and keep this
discipline:

- Do not poll `list_agents` / `get_agent_status` before a notification arrives; do other authorized
  work instead.
- On arrival, read `<agent-response>` in full (use `get_agent_activity` when truncated) and handle it
  per §5's classification.
- If no notification arrives but the agent is already idle, read `get_agent_activity` and the
  workspace state and continue acceptance; do not idle-wait for a lost notification.
- With no MCP notification capability, keep each turn bounded (≤60 seconds per wait) and record
  explicitly which entry points cannot be woken automatically.

## 5. Reply protocol: decisions go to the human, details are answered for them

For every question from a worker (grill / wayfinder / prototype and so on), classify it first, then
decide who answers — the flow must not stall on a question, but "never ask the human" is not the
default. A worker asks by ending its turn: the last message starts with `[[PASEO-ASK]]` and ends with
`[[/PASEO-ASK]]` (see [spec contract](references/spec-contract.md)).

- **Decision-class** (deliverable shape / user-observable behaviour, approach forks, scope
  boundaries, or the escalation five: credentials, third-party accounts, payment, manual approval,
  irreversible live-data operations): attach your own leaning and ask the human to settle it. A
  worker's `recommended:` is reference only — no question may go from recommendation straight to
  answer without classification.
- **Detail-class** (naming, directory placement, implementation technique, test style, in-library API
  usage): the coordinator answers, grounded in project context / ADR / spec / the user's own words.
- Merging an already-authorized project change is an execution step of §6, not a product decision
  that needs re-approval.

Classification criteria, how to ask the human, and record-keeping details are in
[reply protocol](references/reply-protocol.md). Reply to a worker with `send_agent_prompt`; the
answer itself re-arms the completion notification.

## 6. Gate acceptance

Verify observable results and evidence yourself, and on failure list what is missing and send it
back. Choose the gate by ticket type; details are in
[gate acceptance](references/gate-acceptance.md). That file also covers G-impl item by item, the
G-merge composition rules, §6.5 merge execution and §6.5.1 local main-branch sync, plus the agent /
workspace lifecycle and the send-back protocol. For a long-horizon integration PR, also check the
Merge Danger door against the real diff: a one-way door never auto-merges, and an uncertain case is
treated as one-way.

## 7. Landing work, implementation, and closing

Each round is bounded by the scope declared in §0. A full implementation request with unclear
requirements runs `grill-with-docs → to-spec → to-tickets → implement-spec` in order; with a clear
spec or existing tickets, enter at the matching stage. A design-only, spec-only or tickets-only
request closes once that stage's artifact PR is merged, and you do not drift into implementation on
your own. When the user explicitly asked to keep the PR unmerged, close at that exception (criterion
in §0).

- Design tickets are accepted under G-docs or G-wayfinder. If this round also includes to-spec /
  to-tickets, keep landing and reconcile the tracker; otherwise the report records the follow-up
  entry point and does not mark the unauthorized stages as defects.
- A complete ticket map runs through exactly one long-horizon worker; it owns the frontier and its
  concurrency. The per-ticket fallback (one worker per ticket, default 3) is for a degraded run and is
  recorded in the ledger. Accept the integration PR once, not per ticket.
- Per-ticket TDD and evidence are the worker's contract; the final integration PR is the
  coordinator's gate. When the same field or interface changes across call sites, the Answer
  enumerates every location and its disposition.
- Terminology and ticket wording follow the repository's existing conventions first.

The closing report goes in a persistent directory outside the repository and must be readable on its
own. Record: this round's request and delivery endpoint; the artifacts with their commit/PR/merge
state; key acceptance results and evidence locations; the decisions the human made and the ones
answered for them; unfinished items; and the worker lifecycle count. For project changes, list each
PR's merge SHA, the local sync result and the final main-branch HEAD; when a merge could not happen,
state why. A suggested layout is `~/.paseo-auto/runs/<run-id>/ledger.md` with `report.md` beside it.

## 8. Planning dependency initialization (on demand)

Only when this round actually uses `grill-with-docs`, `to-spec`, `to-tickets` or `triage` and their
required repository configuration is missing, check that repository's planning setup. Reuse the
repository's existing issue tracker and domain docs configuration first. If initialization would add
governance files, labels or PRs, confirm they belong to the user's requested planning scope. When it
is genuinely needed, a worker lands it in an isolated worktree and the coordinator accepts it.

## 9. Failure and reporting discipline

When the Paseo daemon is unavailable, MCP dispatch fails, a `create_agent` receipt looks wrong, a
permission request arrives, a notification is lost, or a breaker trips, follow
[failure and reporting](references/failure-and-reporting.md) instead of improvising. Every rule there
has the same shape: gather evidence before deciding, report the exact error, and never re-dispatch
unconditionally. A process error (not a product bug) also triggers a read-only retro; its candidates
need human selection before a worker lands them — see
[long-horizon tickets](references/long-horizon-tickets.md) §6.

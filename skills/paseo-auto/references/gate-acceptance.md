# Gate acceptance, merge execution and agent lifecycle

**When to read this**: when a ticket closes and you must pick a gate by ticket type and run
acceptance; and when merging a project PR or archiving an agent / workspace.

## 6. Gate acceptance

The coordinator verifies observable results and evidence itself, and on failure lists what is missing
and sends it back. A UI / runtime change must be exercised for real in an isolated environment with
isolated data, following the repository's browser discipline — not accepted on a test's claim alone.
The conclusions and key numbers go into the persistent §7 report; process logs may live in a temporary
evidence directory, but the report must not depend on a temporary directory surviving.

### Choosing a gate by ticket type

| Ticket type | Gate | Acceptance focus |
| --- | --- | --- |
| Design / wayfinder | G-docs / G-wayfinder | Decisions, terminology, frontier and document structure |
| Research | Source and conclusion verification | Traceable sources, evidence-backed conclusions, explicit limits and delivery endpoint |
| Spec | G-spec | User stories, seams, scope and tracker state |
| Ticket splitting | G-tickets | Vertical slices, dependencies, per-ticket acceptance |
| Implementation | G-impl | Changed behaviour, tests, quality, deliverables |
| Auto-merge of a project change | G-merge | PR, CI, combined result and merge safety |

Documentation / planning tickets run only the applicable gates; with no source behaviour change, do
not force source tests or a two-axis source review. The full documentation gates are in
[planning gates](gates-docs-planning.md); read only the subsection for the ticket at hand. Decide the
ticket type before dispatch from the expected Target / Change and re-check it against the real diff
afterwards; handle a boundary crossing per §5.

### Where to take evidence

The worker's workspace `cwd` comes from the `create_workspace` return value and is already in the
ledger. The coordinator can accept read-only with `git -C <cwd> status|diff|log`, `gh pr view` and CI
results. When checks must run locally, prefer **another acceptance workspace** (created with the
`checkout-pr` mode from the PR head) or CI; do not write acceptance caches into the worker's
workspace, and do not edit there.

### G-impl — implementation tickets

0. **The scene**: read `git -C <cwd> status --porcelain`, the changed-file list and
   `git diff --numstat`. Uncommitted content must be explained; for an abnormally large diff, protect
   the real work first, then investigate per [formatter recovery](reformat-noise-recovery.md) — never
   restore directly.
1. **Behaviour and tests**: run the repository's existing tests according to the blast radius. A
   single ticket with a bounded blast radius runs the affected tests; a shared interface, build
   configuration, types or an unclear blast radius runs the full suite. Do not re-run the full suite
   locally on the same code; the final head is judged by CI or one local full run. A fix's test must
   fail before the fix and pass after it; new behaviour leaves observable red-green evidence. Pure
   copy, style or configuration changes prove the result with real rendering, a check, or applicable
   tests. A UI ticket's evidence must land on the text, elements, accessible names or real browser
   behaviour the product renders. Check the spec's `Test tier:` line against what actually ran: a
   narrow tier's selector, results and cited reason must line up; running narrower than declared
   (picking a single test) or running the full suite every round (slow, unexplained) is sent back, and
   the coordinator rewrites that line when the tier changes. A narrow tier governs the iteration
   phase's verification scope; it does not waive the previous rule that the final head is judged by CI
   or one local full run.
2. **Quality**: run the static checks, lint and format gates the project actually has, per the
   repository's real configuration — TS typecheck, Python mypy/ruff, Go `go vet`, Rust clippy/fmt are
   per-language examples, not a mandatory checklist. When the repository has no gate of some kind, do
   not invent one; write "this project has no such gate" in the report, and do not report a false red
   because a tool is missing. If the repository has pre-existing problems, take a comparable baseline
   at this ticket's base commit and report the number of new problems; a log from another branch is
   not this ticket's baseline.
3. **Review and coverage**: `[[PASEO-DONE]]` / the Answer must show actual execution evidence for the
   pre-skill. When a two-axis code-review is needed, give the Standards and Spec conclusions, their
   findings and how each was handled separately; the small implementation tickets defined in §3 may
   omit it with the reason already recorded in the spec. When a field, prop or parameter changes
   source, enumerate every related call site and state, one by one, whether it changed or why it did
   not. Keep similar operations inside one ticket consistent; any difference needs a checkable reason.
4. **Task state**: the task state and the Answer match the real degree of completion;
   `[[PASEO-DONE]]` proves only that the turn ended and never substitutes for accepting the artifacts.
   When a notification is lost, check the agent activity, the workspace and the artifacts; do not
   dispatch a second editor.
5. **Deliverables**: when project files changed, check that the workspace is clean, the commit exists
   and the branch is pushed; check that the OPEN PR's head matches this ticket's final commit and that
   the body accurately states Summary, Evidence, Merge Danger and `Closes`; the worker uses the `pr`
   skill or the repository template and creates or updates the PR with `--body-file`. A long-horizon
   ticket map's deliverable is one integration PR: check that every ticket's branch is merged and spot
   check the evidence of at least two tickets; per-ticket TDD plus one `code-review` on the final
   integration branch replaces per-ticket two-axis review, and that choice goes into the report. If no
   PR can be found or the body lacks evidence, send it back to the worker to complete; the coordinator
   does not write it for them.

### G-merge — the door-aware merge gate for project PRs

0. **Door check**: read `Door` and `Blast Radius` from the PR body, then check the claim against the
   real diff. One-way triggers: schema/data migration, backfill or deletion; a breaking public
   API/CLI/SDK change (removal, rename, or a change to an existing signature/semantics/default) or a
   persisted-format change — purely additive, backward-compatible additions are not one-way by
   themselves; authentication/permission/secret or trust-boundary changes; billing/pricing or
   entitlement changes; deployment/infrastructure or runtime-configuration changes; irreversible
   external side effects; feature removal; major-version dependency upgrades; a very wide blast radius
   with no simple rollback. If any one holds, the whole PR is one-way; when unsure, treat it as
   one-way. **This list is the only authority in this skill**; other paths such as long-horizon ticket
   maps reference it directly and keep no copy of their own. When the body says two-way but the diff
   contains a trigger, send it back to the worker to fix the body, then treat it as one-way. A one-way
   door stops here: keep the PR open and report the exact action for the human to merge manually.
   Never auto-merge a one-way door.

Read the repository's CI and merge conventions first. Separate a known baseline failure from a real
failure this ticket introduced. For multiple PRs, the integration worker composes the final head in an
isolated workspace in the intended merge order and DAG order, recording the base, each head SHA and
each step's tree SHA; the coordinator checks the composition and runs the applicable full gates on the
final tree — CI by default, and only when the repository has no usable CI, one equivalent local full
gate as a substitute. A single PR gets the same verification on its final head. On a composition
conflict or a genuine red, fix the PR first; after any head or target base changes, re-judge whether
the original evidence still covers what will be merged. A two-way door with all gates green enters
§6.5 auto-merge with no separate user confirmation; when the user explicitly asked to keep the PR
open, stop here.

### §6.5 Merge execution and closing

1. In DAG or stacked-PR order, check the current head against the accepted SHA; merge one at a time
   with a method the repository allows. Merge conflicts go back to that ticket's worker to resolve in
   its workspace, then re-run the affected gates and G-merge.
2. After each merge run §6.5.1, and check that the main-branch tree SHA matches the corresponding
   verified prefix. Pause and update the integration evidence only when an unplanned main-branch
   commit appears, the merge result differs, or a pending head changes.
3. After all merges, check that the final main branch contains the expected commits, do a quick
   check, and record the SHA. On an anomaly, preserve the scene and dispatch a fix ticket; never write
   a merged state up as accepted.
4. Close at the stage this round's scope reaches; merging a design PR does not by itself authorize
   creating implementation tickets. A one-way door never enters this merge loop: a human merges it
   manually, and a later turn records the merge SHA and syncs main.

#### §6.5.1 Syncing the local main branch after each PR merge

Record the PR's MERGED state, its base and its merge SHA. Run `git pull --ff-only` only after
confirming the main working copy is on the target main branch, the working tree and index are clean,
and the remote and upstream are unambiguous. Then check with
`git merge-base --is-ancestor <merge_sha> HEAD` and record the local HEAD. When the conditions do not
hold, preserve the scene and report "the remote is merged, the local sync is blocked", and pause
further merges; do not auto-stash, reset, check out, or create a local merge commit. A network error
may be retried once after it is diagnosed.

### Agent lifecycle and send-back

- When the worker has finished, acceptance passed, the PR is merged and synced:
  `archive_agent({ agentId })`. `archive_agent` interrupts a running agent and removes it from the
  active list; make sure the work is persisted before calling it.
- When the ticket no longer needs follow-up, call `archive_workspace({ workspaceId })`. It archives
  the agents and terminals and removes the Paseo-owned worktree once the last active reference is
  archived. **Only after the branch is pushed and the PR is merged**; under the open-PR exception keep
  the workspace until the human is done, unless the user explicitly asks for cleanup.
- Long-horizon ticket maps: the top-level worker cleans up the nested workspaces it created; the
  coordinator archives only the top-level worker's workspace, and confirms during acceptance that no
  nested workspace is left behind.
- A send-back states which gate, what evidence is missing, and exactly what to add. For a worker that
  has already ended, send a follow-up with `send_agent_prompt` (same agent, same workspace, reusing
  the original branch); the notification re-arms automatically, and the new turn goes through §4.3.1
  again. When the same gate fails twice in a row, pause that ticket and give the user a differential
  analysis to decide. When send-backs across tickets reach 5, or there is no substantive progress for
  a long time, stop dispatching new work and report the current state; wind down the remaining
  in-flight work safely on the available evidence.
- **Do not** create a second agent editing the same ticket for a send-back; that produces two branches
  unaware of each other. Only when an agent is `closed` / unrecoverable do you create a replacement in
  the same workspace, keeping the original branch and commits.

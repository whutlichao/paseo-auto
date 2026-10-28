# Dispatch loop: profile materialization, workspace/agent parameters, turn confirmation

**When to read this**: on every B/C dispatch, for the full `create_workspace` / `create_agent`
parameters, the profile materialization detail, how to confirm the turn, and the CLI fallback when
MCP is unavailable.

## 4.2 Profile materialization

Run `list_profiles` once before dispatching and read each profile's `notes`:

1. The user named a profile → select it by name.
2. Otherwise pick the notes that best fit this ticket's work (design / review / research /
   implementation are matched separately).
3. When several fit, prefer a provider family different from the coordinator's, to reduce
   same-source blind spots.
4. No suitable profile → discover with `list_providers` / `inspect_provider` / `list_models`, and
   write the "fallback path" into this round's report.

Materialize the profile into `create_agent`:

```text
provider  = "<profile.provider>/<profile.model>"
settings  = {
  modeId:          <profile.modeId>,
  thinkingOptionId:<profile.thinkingOptionId>,
  features:        <profile.featureValues>
}
```

Omit what is missing; do not keep a `profile` field (`create_agent` has no such parameter) and do not
reuse remembered values across Runs. Set only feature IDs that `inspect_provider` returned.

## 4.3 Two-step dispatch

### Step one: create the worktree workspace

```text
create_workspace({
  isolation: "worktree",
  mode: "branch-off",
  path: "<absolute path to the target repo>",
  branchName: "<ticket slug>",
  baseBranch: "<this round's default base, usually origin/main>",
  worktreeSlug: "<ticket slug>",
  title: "<ticket title>"
})
```

It returns `{ workspaceId, projectId, cwd, isolation, kind, title, background }`. Write `workspaceId`
and `cwd` into the ledger; `cwd` is the working directory for later read-only evidence and
acceptance.

Constraints:

- `path` must be the absolute path of the source checkout; the daemon resolves it on its own machine.
  This is especially non-optional when the session cwd differs from the target repo.
- `baseBranch` explicitly carries the round default base resolved in §0 (usually `origin/main`). A
  bare `main` prefers the local main, which may not be the baseline you want; hard-coding
  `origin/main` fails outright in a repository whose default branch is not main.
- One ticket, one workspace. Do not reuse another ticket's workspace, and do not use
  `isolation: "local"` to put a worker into an existing directory.
- Omit `background`. Pass `true` only when the user explicitly asks for a hidden agent.

### Step two: create the agent

```text
create_agent({
  title: "<ticket title>",
  provider: "<profile.provider>/<profile.model>",
  workspaceId: "<workspaceId from step one>",
  initialPrompt: "<the complete §4.4 spec>",
  notifyOnFinish: true,
  labels: { "ticket": "<ticket slug>", "run": "<run id>" },
  settings: { ... }
})
```

Take at least `agentId`, `status`, `workspaceId` and `guidance` from the receipt. Only when `guidance`
contains "You will get notified…" is the completion notification armed; otherwise run the bounded
mode from the notifications reference.

**Never** omit `workspaceId` on `create_agent`: that lands in the coordinator's own workspace
(agent-scoped) or creates a new local workspace on a top-level call — neither is a permitted
implementation location for this skill.

## 4.3.1 Confirming the turn started

1. Receipt `status: running`: the turn was accepted by the provider.
2. `get_agent_status({agentId})`: still `running`, or a tool call / assistant output already exists ⇒
   it has started.
3. Receipt `status: idle` and `get_agent_activity` shows no `turn_started` / tool call / assistant
   output:
   - no `error` ⇒ the initial turn never started; send one explicit resume instruction per
     [agent recovery](agent-recovery.md) §2 (that send re-arms the notification);
   - `error` / immediate `closed` ⇒ gather evidence per agent-recovery;
   - still no events ⇒ treat it as a failure and gather evidence; do not wait blindly — a turn that
     never started produces no terminal notification.
4. The returned `guidance` says "Observe completion…" ⇒ the notification is not armed. Do not pretend
   you can continue automatically; switch to bounded waiting, or move to a caller that has MCP.

## 4.3.2 Long-horizon dispatch (one worker per ticket map)

Once G-tickets accepts a complete ticket map, start **one** worker for the whole map:

```text
create_workspace({ isolation: "worktree", mode: "branch-off",
  path: <repo>, branchName: "<feature>-integration",
  baseBranch: "<this round's default base, usually origin/main>",
  worktreeSlug: "<feature>-integration", title: "<feature> integration" })
create_agent({ title: "<feature> integration", provider: <profile>, workspaceId: <ws>,
  notifyOnFinish: true, initialPrompt: <long-horizon spec> })
```

The spec uses `implement-spec` as the pre-skill and carries `Tracker:` / `Spec:` / `Tickets:` /
`Integration branch:` pointers (see [long-horizon tickets](long-horizon-tickets.md)). It must first
prove it can create isolated workspaces and agents for implementers, and only then spend the whole
map; if it cannot prove that, run implementers serially, or have the coordinator fall back to
per-ticket workers (default concurrency 3). The coordinator accepts the single integration PR only.

## 4.5 The communication loop

- Do not poll after dispatch; completion / questions / permissions all come back as notifications.
- On every notification: read it in full → update the ledger → classify → handle. Answer questions
  with `send_agent_prompt` (default `steer`, which also re-arms the notification).
- A single worker run commonly takes 10–30 minutes. Do other tickets or other authorized work until
  the notification arrives.
- Notification lost but the agent is already idle: read the activity and workspace evidence and
  continue; handle it per [notifications and waiting](notifications-and-waiting.md) §5.

## 4.6 CLI fallback without MCP

Use only when the MCP tools are unavailable. The CLI does **not** send completion notifications to
the parent agent, so the bounded mode is mandatory.

```bash
# create the workspace
paseo workspace create --isolation worktree --mode branch-off \
  --path "<repo>" --new-branch "<slug>" --base "<this round's default base, usually origin/main>" \
  --worktree-slug "<slug>" --title "<ticket title>" --json
# dispatch the agent (--no-wait returns the agentId immediately)
paseo run --provider "<provider/model>" --mode "<modeId>" \
  --thinking "<thinkingOptionId>" --workspace "<workspaceId>" \
  --title "<ticket title>" --label "ticket=<slug>" --label "run=<run-id>" \
  --no-wait "<spec>"
# follow-up
paseo wait <agentId> --timeout 60
paseo inspect <agentId> --json
paseo logs <agentId> --tail 40 --json
paseo send <agentId> --behavior steer --no-wait "<answer>"   # without --no-wait it blocks up to 600 seconds
```

Without `--no-wait`, `paseo run` blocks in the foreground until the agent finishes; when the Bash
tool's timeout matches the application's, prefer `--no-wait` plus a bounded `paseo wait` so one long
task cannot drag the call down with it.

## 4.7 Archiving

- After merging and syncing the main branch: `archive_agent({agentId})`, then
  `archive_workspace({workspaceId})` if needed.
- `archive_workspace` archives its agents and terminals and removes the Paseo-owned worktree once the
  last active reference is archived. **Use it only after the branch is pushed and the PR is merged**;
  with an open PR, keep the workspace until the human is done, unless the user explicitly asks for
  cleanup.
- When a one-way door keeps an open PR: keep the agent until the ticket is definitely no longer
  followed up (the PR is merged or a human takes over), then archive it; keep the workspace until the
  human is done, unless the user explicitly asks for cleanup. Confirm the remote branch was pushed
  first.
- The authoritative criterion for archiving timing is "agent lifecycle and send-back" in
  [gate-acceptance](gate-acceptance.md); where this section conflicts with it, that file wins.

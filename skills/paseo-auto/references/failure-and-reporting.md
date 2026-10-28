# Failure and reporting discipline

**When to read this**: the Paseo daemon is unavailable, an MCP tool is missing, a `create_agent` receipt
looks wrong, a permission request cannot be handled automatically, notifications stall, a breaker trips,
or a report to the user is due.

## 9. Failure and reporting discipline

- **The control plane is unavailable**: when the MCP tools are absent and `paseo status --json` reports a
  daemon fault, report the exact error (command, exit code, error text) and stop. Do not guess commands,
  do not swap executables, and do not restart the daemon unconditionally. When local evidence is needed,
  read the latest entries in `~/.paseo/daemon.log`; restart only when the user asks or when it is clearly
  a local daemon operation, and re-check agent state after a restart before continuing.
- **MCP dispatch fails**: gather evidence per [agent recovery](agent-recovery.md), then decide whether to
  retry or report. **Do not** fall back to asynchronous CLI dispatch just to route around the failure —
  the CLI does not arm completion notifications, so the wake is silently lost. When the CLI is genuinely
  the only option, switch to the bounded waiting mode and tell the user explicitly.
- **Notifications stall**: when the agent is idle but no notification arrived, read `get_agent_status` /
  `get_agent_activity` and the workspace evidence first; if the work is done, continue acceptance and do
  not ask for a resend. If the agent is still running, do not disturb it.
- **A permission request cannot be handled automatically**: when it involves credentials, a third-party
  account, payment, manual approval or an irreversible live-data operation, stop immediately and ask the
  human, stating the requested operation, its target and the risk. Do not auto-approve and do not switch
  to bypass mode.
- **Any breaker trips** (ticket-level: two consecutive failures of the same gate; run-level: the
  cumulative send-back threshold) → stop immediately and ask the human, stating which stage is stuck,
  the evidence already in hand, and what the human must decide.
- **An agent is closed / canceled / errored**: handle it per [agent recovery](agent-recovery.md); first
  confirm whether committed work is persisted, then decide between a replacement and a send-back.
  Without evidence, deleting a workspace or force-pushing is never authorized.
- **A process error** (a harness defect that can recur): at a safe point run a read-only retro, hand the
  candidates to the human, and land only what they select — see
  [long-horizon tickets](long-horizon-tickets.md) §6. A retro never modifies the skill mid-run.
- Authorized implementation work is not skipped because the task is small or the repo lacks
  `WORK_SCOPE`; pure Q&A, reports, and later stages beyond this round's delivery endpoint are not
  dispatched. When the scope is unclear, explore read-only first and re-check per §1.
- When a later stage is already inside this round's scope, advance into it directly; when it is not, the
  report states the current state and the next entry point.
- Design terminology follows the repository's language; when architectural analysis is needed, use
  codebase-design vocabulary to express it.

## Report format

A report must be understandable on its own and contain at least:

```text
this round's request and delivery endpoint
which step is stuck (channel / dispatch / acceptance / merge)
the exact error and where the evidence is (command, exit code, log, agentId, workspaceId, PR)
the recovery actions already tried and their results
agents still running / items still pending
what the human must decide (if anything)
```

Never write "no notification arrived" as "the worker failed", and never write "the PR is open" as "the
work is complete".

# Dispatch failures, permissions and lost-contact recovery

**When to read this**: `create_agent` fails, a turn never starts, a permission request arrives, an
agent errors / is closed / is canceled, or a worker shows no progress for a long time. Do not read it
on the normal path.

## 1. `create_agent` fails

Read the error first, then decide; do not retry unconditionally, and do not try another provider on a
hunch.

| Error / symptom | Evidence | Action |
| --- | --- | --- |
| provider/model not recognized | `inspect_provider({provider})`; `list_models` | Recreate with a model the response says is valid; if it still fails, report a provider configuration problem |
| workspace missing / no access | `list_workspaces`; check the workspaceId in the ledger | Use the correct workspaceId; if the workspace is gone, recreate one on the same branch (`checkout-branch`) |
| worktree creation failed (branch exists, base resolution failed) | Read the `create_workspace` error; `git -C <repo> branch --list <slug>` | When the branch already exists, switch to `mode: "checkout-branch", branch: <slug>`; write the round default base resolved in §0 as the base |
| The first prompt is rejected / immediate idle | `get_agent_status`; `get_agent_activity` | Check whether the spec is empty, over-long, or carries an attachment the provider rejects; fix and recreate |

Before retrying, confirm the cause is gone. Consecutive failures for the same cause go through the §6
breaker; do not retry forever. **Never** put the worker into the main workspace just to route around a
failure.

## 2. The turn never started

`create_agent` returning `status: running` only says the provider accepted the turn; whether it really
started is judged with `get_agent_status` and `get_agent_activity`:

- `turn_started` / a tool call / assistant output ⇒ it started; wait for the notification.
- Still `running` with no events, and just created ⇒ it may still be initializing; give it one
  notification-sized window.
- `idle` with no assistant output ⇒ it failed to start. Read the error in the activity; if needed send
  one `send_agent_prompt`: "start from the spec's first item; end the turn with `[[PASEO-ASK]]` on any
  decision-class question". That send re-arms the notification.
- `error` / `closed` ⇒ handle it per §5.

Do not send "continue" repeatedly; if there are still no events after one resume, treat it as a
failure and preserve the scene.

## 3. Permission requests

The notification carries a `<permission-request>` JSON (`agentId`, `requestId`, `request`).

1. Read the concrete operation, target path, command and risk in `request`.
2. Handle only operations already authorized this round. Reading and writing inside the project,
   running tests, committing and pushing are usually inside the implementation authorization;
   credentials, third-party accounts, payment, manual approval and irreversible live-data operations
   must be escalated to the human per §5.
3. Approve:
   - MCP: `respond_to_permission({ agentId, requestId, response })`, where `response` takes the shape
     the provider requires (the request in the notification gives the acceptable values);
   - CLI: `paseo permit allow <agentId> <requestId>`, or `--all` to approve every pending request for
     that agent.
4. Deny: `paseo permit deny <agentId> <requestId>`, plus a `send_agent_prompt` explaining why so the
   worker can take an authorized path instead.
5. Afterwards re-check with `list_pending_permissions` to confirm nothing is left.

Never treat "allow" as the default, and never switch to bypass / full-access mode just to avoid the
prompt.

## 4. Lost notifications

First take the three evidence points from [notifications and waiting](notifications-and-waiting.md)
§5 (status / activity / workspace), then decide. The common conclusions:

- The agent is idle and its artifacts are complete ⇒ the notification was lost, the work was not;
  accept directly.
- The agent is idle but stopped mid-way ⇒ one resume instruction.
- The agent is `running` ⇒ wait for the notification, do not disturb it.

## 5. An agent errors, is closed, or is canceled

1. Read the last error and the last assistant message from `get_agent_activity`.
2. Read the workspace: `git status`, `git log --oneline -5`, `git branch --show-current`.
   **First confirm whether the committed work is persisted**; handle uncommitted changes with the
   protection steps in [formatter recovery](reformat-noise-recovery.md), never a direct reset.
3. Committed but not pushed: have the replacement worker push first, then continue.
4. Recoverable (same workspace, same branch): create a replacement agent in the original workspace and
   write in its spec "commits `<sha>` already exist; continue from the current branch; do not redo the
   finished part".
5. Unrecoverable: keep the artifacts and evidence and report the blockage; do not open a blank
   worktree and redo the whole ticket.

A ticket always has exactly one active editor. Once the replacement agent exists, archive the old one
so two branches never run in parallel.

## 6. Stop conditions

- Two consecutive dispatch failures for the same cause ⇒ stop and ask the human, with the exact error
  and what has been ruled out.
- Two consecutive failures of the same gate on the same ticket ⇒ trip the ticket breaker, pause that
  ticket and ask the human to decide.
- run-level send-backs reaching 5, or no substantive progress for a long time ⇒ stop dispatching new
  work, wind down the in-flight work safely and report.
- A permission request covering the escalation five ⇒ escalate immediately, do not auto-approve.

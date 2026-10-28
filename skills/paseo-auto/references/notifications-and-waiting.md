# Notifications, waiting, and lost-contact recovery

**When to read this**: before each Run's first dispatch; after every notification; when a
notification is slow to arrive or a worker looks unreachable.

## Contents

- [1. The only wake mechanism](#1-the-only-wake-mechanism)
- [2. What a notification looks like](#2-what-a-notification-looks-like)
- [3. One-shot and re-arming](#3-one-shot-and-re-arming)
- [4. Waiting discipline](#4-waiting-discipline)
- [5. When no notification arrives](#5-when-no-notification-arrives)
- [6. The bounded mode without MCP](#6-the-bounded-mode-without-mcp)
- [7. The ledger](#7-the-ledger)

---

## 1. The only wake mechanism

Paseo does not provide Orca-style inbox polling. A supervised worker wakes the coordinator through a
**finish notification**:

- an agent-scoped `create_agent` with `notifyOnFinish: true` registers a completion observer;
- when the worker finishes, errors, requests permission, or is closed, Paseo delivers a notification
  message into the coordinator's session;
- the notification is delivered as a `steer`, so it is appended even while the coordinator is in
  another turn.

That notification is the wake. **Do not** poll `list_agents`, `get_agent_status` or
`get_agent_activity` "to see progress"; that burns calls while the worker is working normally, and it
also makes you misread "still running" as "no activity".

## 2. What a notification looks like

Finished / errored / closed:

```text
Agent <childAgentId> (<title>) finished.

<agent-response>
…the worker's last assistant message (possibly truncated to 4000 characters)…
</agent-response>
```

Permission request:

```text
Agent <childAgentId> (<title>) needs permission.

Respond with `respond_to_permission` using the `agentId` and `requestId` below.

<permission-request>
{"agentId": "...", "requestId": "...", "request": { ... }}
</permission-request>
```

A canceled message shows up as an `errored` event; a closed one as `closed`. None of the three may
be treated as "completed normally".

An `<agent-response>` longer than 4000 characters carries
`[truncated …; use get_agent_activity for the full response]`. When truncated, read the whole thing
with `get_agent_activity` first, then classify.

## 3. One-shot and re-arming

A **terminal notification** (finished / errored / was closed / was canceled) is one-shot: once it
fires the observer stops and it will not fire again for the same agent's next idle period. A
**permission notification (needs permission) is not terminal**: it does not release the observer, it
deduplicates by `requestId` and fires once per distinct requestId; `respond_to_permission` does not
change the armed state, so after the permission is resolved you still get one terminal notification
when that turn ends — therefore do not send a message "to re-arm" after answering a permission, and do
not fall back to polling.

In an agent-scoped call `send_agent_prompt` defaults to `notifyOnFinish: true`, which registers an
observer for the new turn. So the normal loop is:

```text
create_agent (arm) → worker asks/finishes → notification arrives
  → read the response → classify → send_agent_prompt (re-arm) → the next notification
```

Rules:

- Always answer a worker's question with `send_agent_prompt`, not another channel; it also does the
  re-arming.
- **Do not** set `notifyOnFinish` to `false` unless this worker is genuinely fire-and-forget.
- The receipt's `guidance` is the on-the-spot evidence of whether the notification is armed:
  - "You will get notified when the prompted agent finishes…" ⇒ armed;
  - "Observe completion using get_agent_status…" ⇒ not armed; use the bounded mode in §6.

## 4. Waiting discipline

- After dispatch, write agentId / workspaceId / ticket slug / last notification time into the ledger,
  then **go do something else**.
- With several tickets in flight, one worker per ticket; handle whichever notifies first. Do not
  idle-wait on one "to keep the order".
- A worker run commonly takes 10–30 minutes; do not check status every two minutes.
- When a notification arrives, do three things in one step: read it in full → update the ledger →
  classify and handle (question / completion / permission / failure).

## 5. When no notification arrives

A notification can be lost because the agent never started, the observer was replaced, the session
restarted mid-flight, or the worker crashed outright. Gather evidence in order; do not re-dispatch
immediately:

1. `get_agent_status({agentId})`: look at `status` and `pendingPermissions`.
2. `get_agent_activity({agentId})`: read the latest events and the last assistant message.
3. The workspace's actual state: `git -C <workspace.cwd> status --porcelain`,
   `git log --oneline -5`, `git branch --show-current`. Read-only, no modifications.
4. If it looks like a permission request, cross-check with `list_pending_permissions`.

| Observation | Action |
| --- | --- |
| `idle` with a complete completion message | The notification was lost but the work is done; treat it as complete, continue acceptance, do not ask for a resend |
| `idle` and the last message is `[[PASEO-ASK]]` | Treat it as a question; answer with `send_agent_prompt` and re-arm |
| `idle` and the last message stops mid-way or follows a tool call with no conclusion | Send one explicit resume instruction (read the spec's remaining items, continue implementing, close per the spec); send it once |
| `running` | It is already working; send nothing, wait for the notification |
| `error` / `closed` / `canceled` | Read the error and the workspace evidence, and handle it per [agent recovery](agent-recovery.md) |
| The agent does not exist | The ledger disagrees with reality; check the agentId, do not guess from the title |

At most one resume or closing instruction. If there is still no progress after that, keep the
artifacts and report the blockage; do not loop on "continue", and do not open another worker editing
the same ticket.

## 6. The bounded mode without MCP

If the current session has no Paseo MCP tools (for example running Claude Code / Codex directly in a
terminal), only the CLI is available:

- `paseo run <prompt>` **blocks in the foreground until the agent finishes by default**; the process
  returning is one wake. Limit a single wait with `--wait-timeout`. It gets you the final result but
  **does not** send a completion notification to the parent agent.
- `paseo run --no-wait` returns only the agentId; afterwards block with
  `paseo wait <agentId> --timeout <seconds>`.
- `paseo send <agentId> --behavior steer --no-wait "<answer>"` sends the answer; a CLI send likewise
  does not arm a notification. **`--no-wait` is mandatory**: without it send blocks in the foreground
  until that turn ends, with a hard ceiling of 600 seconds and no option to shorten the wait, which
  conflicts with this mode's "≤60 seconds per foreground wait". When you need the result, run
  `paseo wait <agentId> --timeout 60` separately.
- Judge state with `paseo inspect <agentId> --json` and `paseo logs <agentId> --tail 40 --json`.

Bounded-mode discipline:

- No single foreground wait longer than 60 seconds; after a timeout read `inspect` / `logs` /
  workspace evidence and then decide the next step.
- Only after three consecutive rounds with no progress do you handle it per
  [agent recovery](agent-recovery.md).
- When the environment must take control back, report explicitly: the agentId still running, the last
  progress, the ledger path, and the limitation that it cannot be woken automatically. Never claim it
  "will continue on its own".

## 7. The ledger

One per Run, kept outside the repository (default `~/.paseo-auto/runs/<run-id>/ledger.md`). Record at
least:

```text
Run / coordinator agentId
per ticket: workspaceId / workspace.cwd / agentId / branch / last notification time / state / PR
per question: question id / classification (decision/detail) / who answered / the answer / the basis
per completion: notification time / conclusion / acceptance result
```

After context compaction or a restart, read the ledger and the real state from `get_agent_status`
first; do not guess agentIds or progress from the old conversation.

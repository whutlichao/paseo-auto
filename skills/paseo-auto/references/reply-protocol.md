# Reply protocol: decisions go to the human, details are answered for them

**When to read this**: when a worker notification arrives and you must decide whether it is asking a
question or reporting completion; or when deciding whether to escalate to the human or answer
yourself.

For every question from a worker (grill / wayfinder / prototype and so on), classify it first, then
decide who answers. The core of this skill is that the flow must not stall on a question — but
"never ask the human" is not the default. Merging an already-authorized project change is an
execution step of §6, not a product decision that needs re-approval; escalate per this section only
when a merge would change the user's stated scope or needs extra external authorization. A worker's
`recommended:` is reference information only: **no question may go from recommendation straight to
answer without classification.**

## 5.1 Recognizing a question

Inside the notification's `<agent-response>`:

- starts with `[[PASEO-ASK]]` and ends with `[[/PASEO-ASK]]` ⇒ a question;
- ends with `[[PASEO-DONE]]` ⇒ a completion report, handled by §6 acceptance;
- neither, but the agent is idle ⇒ "the turn ended without the contract's closing block"; read the
  activity and the workspace and send one closing instruction per
  [notifications and waiting](notifications-and-waiting.md) §5; do not accept directly.

For a truncated response, read the whole thing with `get_agent_activity({agentId})` before
classifying. One notification may contain both implementation progress and a question; the last
contract block wins.

## 5.2 Classification criteria (check each; any one hit makes it decision-class)

1. **It affects the deliverable's shape or user-observable behaviour**: product direction,
   requirement tradeoffs, visible UI / copy / interaction tradeoffs.
2. **An approach fork**: several viable implementation paths where the choice affects architecture,
   dependencies, seams or how later tickets are split.
3. **A scope boundary**: whether a feature is in or out, what goes into Out of Scope, how strict the
   acceptance criteria are.
4. **The escalation five**: credentials, third-party accounts, payment, manual approval, irreversible
   live-data operations — these skip the other criteria, stop immediately, forward the question
   verbatim to the human, and continue only after a human answer. Better to stop too often than to
   answer for them. **What stops is this worker, not the whole run**: with several tickets in flight,
   an escalation freezes the ticket that raised it and the others keep moving through their gates — a
   credential problem on one ticket should not freeze the pipeline. A global freeze happens only when
   the run-level breaker in §6's send-back protocol trips.

Only when none of the four applies — naming, directory placement, implementation technique, test
style, in-library API usage and the like — is it **detail-class**, answered by you (§5.4). Self-check:
if you cannot write down "why it misses all four", treat it as decision-class — if the reason cannot
be written, the classification does not hold.

**Contradictory premise**: if the question exposes a premise that contradicts repository facts,
`CONTEXT.md`, an ADR or this ticket's spec (for example "this repo has no login" while someone is
editing the login page), do not answer it as a detail and do not just keep implementing; escalate per
criterion 3 (scope boundary) with the read-only evidence, and ask the human to confirm whether "the
ticket is on the wrong repo / out of bounds" or "the premise has changed".

Mind the direction: an older version listed "requirements unclear / unsure which option the user
wants" as never-ask-the-human, decide-yourself cases; **those are exactly the decision-class cases
criteria 1 and 2 now cover, and they must go to the human.**

## 5.3 Decision-class: attach your leaning and ask the human

Pause before replying to the worker, and put three things in front of the human:

- the worker's original question (including the recommendation and reasoning it gave, if any);
- your leaning and one sentence of reasoning (grounded in project context / ADR / spec / the user's
  own words);
- one sentence of cost per remaining option.

Only after the human confirms or picks differently do you reply to the worker with
`send_agent_prompt`. When the human's choice differs from yours, theirs wins — do not lobby twice; if
you have a strong technical reason you may state it once, and if they do not change their mind, follow
theirs. Say everything in one pass to reduce round trips.

## 5.4 Detail-class: the coordinator answers

Ground the answer in project context, an ADR, the spec and the user's own words, and pick the option
closest to the user's expressed intent and the existing architecture. When the worker's recommendation
does not conflict with its reasoning, answer with the recommendation; when it conflicts, explain in
the reply why the recommendation was dropped. Write the reasoning into the reply.

Reply template:

```text
[[PASEO-ANSWER]]
decision: <conclusion>
basis: <grounds: spec / ADR / the user's words / repository convention>
next: <what the worker should continue doing; do not restate the whole spec>
[[/PASEO-ANSWER]]
```

`send_agent_prompt` defaults to `steer`; the worker is idle at this moment and starts a new turn
immediately. Do not send an extra empty message "to re-arm the notification" — this answer already
re-arms it.

## 5.5 Recording

Append `Q → A (human-decided / answered-for-them) → one sentence of reasoning` to the ledger (or the
Answer's Decisions section); for human decisions also record the key points of the options they
chose. The §7 report summarizes this audit list, and the human can overturn any answered-for-them
decision afterwards.

## 5.6 A permission request is not a question

When the notification body contains `<permission-request>`, handle it per the permission section of
[agent recovery](agent-recovery.md): approve only operations already authorized this round; anything
involving credentials, a third party, payment, approval or an irreversible operation escalates per
§5.3. Never treat "allow" as the default, and never switch to bypass mode just to clear the prompt.

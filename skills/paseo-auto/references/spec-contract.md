# The spec contract

**When to read this**: when you are about to write a worker's spec, on any channel and for any
ticket type.

A worker sees only the spec in `create_agent.initialPrompt`, never this skill. The spec must be
self-contained and must carry the applicable behaviour rules and the actual delivery endpoint.

## 4.4.1 The five elements and the fixed first line

The guide's five-element task-spec contract must be complete: **Target / Change / Constraints /
Ownership / Observable acceptance**. Plus a fixed first item:

```text
Pre-skill: <absolute path> — read it in full before starting, follow its procedure, do not skip.
```

**This line is the only entry point to the other skills.** Without it the worker never reads
grill-with-docs / tdd / diagnosing-bugs / code-review, and the "we didn't use the other skills"
failure reproduces itself. Put the path in the spec and let the worker read the whole file; do not
paraphrase it for them.

**What the Answer is**: the ticket's closing record. On a remote tracker (such as a GitHub issue) the
Answer is a comment on that issue or the PR description, and **the canonical text lives in the
issue**; on a local ticket the Answer is the `## Answer` section of that ticket's file, and the
canonical text lives at a path the worker can see. When writing the spec, pick one according to the
tracker type; do not assume "the canonical text lives inside the worktree". When this round has no
ticket, omit Status / Answer and put the evidence into the PR description and the §7 report.

## 4.4.2 Implementation ticket template

```text
[BEHAVIOR RULE (obey verbatim; do not paraphrase or trim)]
1. Questions: do not use AskUserQuestion and do not wait for messages. Finish everything you can
   do, then end the turn with a last message containing only:
   [[PASEO-ASK]]
   question: <the concrete question a human must settle>
   recommended: <your recommendation and one sentence of reasoning>
   options: <one sentence of cost per remaining option>
   [[/PASEO-ASK]]
   The coordinator answers through send_agent_prompt, and then you continue the same ticket.
2. Completion: whether or not project files changed, end the turn with a last message containing
   only:
   [[PASEO-DONE]]
   status: succeeded | failed
   summary: <three sentences: what changed, what you found, what is left>
   pr: <PR URL or none>
   evidence: <test/check commands and results, one per line>
   files: <list of changed files>
   [[/PASEO-DONE]]
   When project files changed, commit, push and create or update the PR first, and put the URL in
   `pr:`. Record the PR number and the CI reading once, in a single backfill commit after the PR
   exists (never one commit per reading; documentation-only commits are not CI-chased — the final
   CI is the coordinator's to accept). When no project files changed, write `pr: none` and say "no
   project file changes" in the summary. Failure must be reported too; a plain summary is not a
   substitute.
3. Needing a human / credentials / a third-party account / a paid service / manual approval /
   irreversible live-data operations → raise it verbatim through [[PASEO-ASK]]; do not act on the
   human's behalf.
4. Use codebase-design vocabulary when describing design; follow the repository's language for
   existing terms in source, tests and reports.
5. Going beyond this spec's authorization → raise it through [[PASEO-ASK]]; do not widen scope on
   your own.
6. Take red evidence on an isolated copy or a baseline worktree; back up and reconcile all
   uncommitted work before any restore or automatic formatting. Check `git status` and the diff
   before delivering; on an abnormally large diff, preserve evidence first and handle it file by
   file per the recovery reference. Configure a locally ignored formatter override before starting
   only when automatic reflow has been confirmed as a real risk in this repository.
7. You work only inside your own workspace; do not switch to or write into the coordinator's main
   working copy, and do not detach yourself or create a new top-level agent (long-horizon workers
   excepted, see their spec).

Pre-skill: <absolute path> — read it in full before starting, follow its procedure, do not skip.
Target: <files/modules>
Change: <the concrete result to produce>
Constraints: <boundaries not to cross; use codebase-design vocabulary for terms>
Ownership: <what this ticket may edit; the canonical ticket location follows the tracker type (a
  remote issue lives in the issue, a local ticket at a path the worker can see); when there is a
  ticket you own its Status transitions and append the Answer at the location above; when this round
  has no ticket, omit Status/Answer and put the evidence into the PR description and the report>
Observable acceptance: <the applicable test commands and observable results; red→green evidence for
  fixes; the two-axis code-review when needed.
  When project files changed: parse and use the local pr skill to write the PR body, push the branch,
  create or update the PR with --body-file, and write the PR number and body path to the location
  above (in the same push as the code, never an extra commit for a backfill);
  whether or not project files changed, always finish by emitting [[PASEO-DONE]]>
```

## 4.4.3 The ticket-type line

**Write the ticket type, the gates and the test tier immediately after the pre-skill line**:

```text
Type: research ticket | design ticket | spec ticket | ticket splitting | implementation ticket
Gates: <research = source and conclusion verification / design = G-docs / spec = G-spec / splitting = G-tickets / implementation = G-impl>
Test tier: narrow (affected tests + selector) | wide (full suite)   ← required for implementation; narrow must state why the blast radius is bounded
Not run this ticket: <list the inapplicable source gates>          ← required for research/design/spec/splitting; fill in truthfully for implementation
```

**Why this line is a hard requirement**: a worker treats exactly what the spec says as its
deliverable surface. With no ticket type in the spec it can only guess; the only general clue it
holds about "gates" is the repository `CONTRIBUTING.md`'s `Keep it green`, so a design ticket with
zero source changes goes off and runs the full suite. The cost of the missing line is concrete: one
long wait + one full run far beyond any useful timeout + one false red from a binary it does not
have.

Likewise, with no "not run" line, "two-axis review" becomes a requirement for every ticket, and it
reviews the diff — a design ticket's diff is documentation, so the Standards axis can only pick at
the evidence directory.

**The test-tier line is the same kind of thing**: narrow-vs-wide is a judgement the coordinator
should have finished before dispatch, but the worker cannot see that judgement. With no test tier it
falls back to "the full suite is safest" or picks a few tests itself; with a narrow tier but no
reason, it cannot tell whether a given test counts as "affected". A narrow tier must carry one
sentence on **why the blast radius is bounded**, plus a selector the worker can run as written
(`node glob` is only an example; Python writes `python3 -m unittest tests.test_x` — do not leave the
worker to assemble the command). If the test tier is wrong, the coordinator re-decides on send-back;
the worker does not change the criterion on the spot.

## 4.4.4 Additional items for a long-horizon ticket map

`Pre-skill` is the absolute path to `implement-spec`. Add:

```text
Skill resolution: use `tdd` / `code-review` through the Skill tool when it exists; otherwise read
  their absolute paths directly — do not paraphrase.
PR skill: <absolute path>/pr/SKILL.md — use it to write the single integration PR body.
Tracker: <docs/agents/issue-tracker.md or the absolute path of the local ticket directory>.
Spec: <absolute path or issue URL>.
Tickets: <tracker query / local directory; state the frontier and the blocking edges>.
Integration branch: <name>; base: <this round's default base, usually origin/main>.
Concurrency: at most <N> implementers; default 3 unless the user or the repository says otherwise.
Paseo dispatch: each implementer gets its own workspace via create_workspace (isolation worktree,
  base = the integration branch), then create_agent pointing at that workspaceId with
  notifyOnFinish: true.
  The first report must prove you can do this; if you cannot prove it, run implementers serially and
  record the degradation.
```

A long-horizon worker is an **orchestrator** and must not implement tickets itself. It maintains the
map and the frontier, starts a fresh implementer for each ready ticket, merges their branches through
a merger step, runs the final review and opens the PR. Nested decision-class questions are raised
through the top-level worker; a worker must not answer for the human. Per-ticket TDD plus one
`code-review` on the integration branch is this path's review model; do not schedule a per-ticket
two-axis review.

## 4.4.5 Criterion

Decide the ticket type before dispatch from Target / Change and the expected files, and re-check it
against the real diff once the worker finishes. If the real change crosses the ticket-type boundary,
escalate the scope question per §5; do not silently reclassify with a path regex.

# Dispatch preflight: tick sheet and teardown checks

**When to read this**: before every dispatch (tick every line), and in the teardown stage after a
worker reports `[[PASEO-DONE]]` but before you claim a gate passed.

## Live worker configuration lookup

Query only when the Run is about to dispatch, and only through Paseo's own tool surface:

```text
MCP: list_profiles → read notes → select → materialize provider/model/mode/thinking/features
CLI: paseo provider ls --json; paseo provider models <provider> --json
```

Do not infer providers and models from old sessions, this skill's text, eval fixtures or stale logs.
A profile the user named wins over your own match; when no profile fits, take the `inspect_provider`
fallback and say so in the report.

## 4.0 Pre-dispatch tick sheet (tick every line; do not dispatch until all are green)

Its only job is to turn "did I miss a rule" into one pass of checkboxes instead of memory — by the
back half of a long spec, the constraints you already confirmed are the ones most likely to drop out
quietly. The parenthesized reference is the section that owns the rule.

- [ ] **The Paseo control plane is alive**: MCP `create_workspace` / `create_agent` are available, or
      `paseo status --json` reports a healthy daemon. If it will not start → report the exact error
      per §9 and stop; do not swap executables and do not guess commands.
- [ ] **The worker configuration is materialized** (§4.2): the profile's
      provider/model/mode/thinking/features are converted into `create_agent` parameters; when no
      profile fits, the fallback and its reason are recorded.
- [ ] **The channel is decided, and re-checked if you explored** (§1, "re-judge after exploration").
- [ ] **The ticket type is decided and the spec carries the ticket-type line** (§4.4): research,
      design, spec, ticket splitting or implementation. Decide it from Target, Change and the
      expected files before dispatch; the workspace does not exist yet, so do not run `git diff`
      against it. A documentation ticket writes only the applicable documentation gates and does not
      list source tests or a two-axis source review as acceptance items. Re-check the type against
      the real diff afterwards.
- [ ] **All five spec elements are present**: Target / Change / Constraints / Ownership / Observable
      acceptance, opening with BEHAVIOR RULE and the pre-skill's absolute path (§4.4).
- [ ] **The workspace/agent parameters are right** (§4.3): `create_workspace` uses
      `isolation: "worktree"`, `mode: "branch-off"`, an explicit `path`,
      `branchName` = `worktreeSlug` = the ticket slug, and `baseBranch` equal to this round's
      resolved default base (§0, usually `origin/main`); `create_agent` **explicitly carries
      `workspaceId`** and `notifyOnFinish: true`. A long-horizon map uses `<feature>-integration` and
      dispatches exactly one worker.
- [ ] **A long-horizon map really is ready**: one integration PR, `implement-spec` as the pre-skill, a
      complete ticket map, a reachable tracker; the worker's first report proves it can create nested
      workspaces/agents, or the serial degradation is recorded (see the long-horizon reference).
- [ ] **The main hard rule was really walked through** (§2): this round will not modify project files
      or create commits in the main working copy; only the fast-forward sync of already-merged work
      in §6.5.1 may update the main branch.
- [ ] **The ticket location is pinned by tracker type** (§4.4): for a remote tracker the canonical
      text lives in the issue (the Answer is an issue comment or the PR description); for a local
      ticket the canonical text lives at a path the worker can see; when this round has no ticket,
      "no ticket" is recorded explicitly and the evidence goes into the PR description and the §7
      report. The coordinator only reads and accepts on main.
- [ ] **The gates are named and decidable**: which ones this stage must pass (G-docs / G-spec /
      G-tickets / G-impl / G-merge), with each one's evidence form mechanically judgeable per §6.
      For an implementation ticket tick two more items:
      ① the test tier (narrow/wide) is chosen per §6 G-impl rule 1 and **written into the spec's
      `Test tier:` line**; if "narrow" is chosen, the same line states why the blast radius is
      bounded and gives a selector that can be run as written;
      ② if this ticket skips the two-axis review, §3's countable criteria are confirmed and the reason
      is written down.
      **Mechanical criterion (test tier)**: `grep -c 'Test tier:' <spec>` returning 0 means do not
      dispatch (implementation ticket).
      **Mechanical check (review)**: the implementation ticket's `Observable acceptance` must contain
      the literal `code-review` (together with "two-axis / Standards + Spec"), unless §3 omitted it.
      A long-horizon map writes "one two-axis code-review on the integration branch" plus per-ticket
      TDD, and must not also require a per-ticket two-axis review. Run `grep -c 'code-review' <spec>`;
      0 means it is not written and you must not dispatch.
- [ ] **Every baseline number in the spec was checked against the base commit**: any measured figure
      such as "baseline before the change: Test Files X / Tests Y" must be confirmed to come from a
      log taken at **the same base commit as this ticket's workspace**. If not, **do not use** that
      number, or write explicitly "baseline from `<commit>`, N commits away from this ticket's base,
      order-of-magnitude reference only".
- [ ] **If this repository really has automatic formatting risk, targeted prevention and safe
      recovery requirements are written into the spec** (§4.4).
- [ ] **After dispatch, the turn really started** (§4.3.1), and the receipt's `guidance` proves the
      notification is armed. When it is not armed, the bounded mode is in use and recorded in the
      ledger.

Send-backs and breakers are not in this table — follow §6's send-back protocol (with a concrete list
of what is missing; two consecutive failures of the same gate on the same ticket stop the ticket and
ask the human).

## 4.0.1 Always check at teardown: formatter noise

After a worker reports `[[PASEO-DONE]]` and before you claim a gate passed, **run these three lines
first** (§6 G-impl step 0). Run them read-only in the `cwd` returned by `create_workspace`; do not
start editing:

```bash
cd <task workspace cwd>
git status --porcelain
git diff --numstat | awk '{a+=$1; d+=$2} END {print "worktree uncommitted:", a, "added", d, "deleted"}'
```

- No uncommitted changes → clean, continue acceptance.
- Uncommitted changes totalling **tens of thousands of lines** → whole-file reflow noise; read
  `references/reformat-noise-recovery.md` and recover.
- Uncommitted changes in a normal amount → ask the worker why they are uncommitted; do not accept them
  by default.

**One-sentence criterion**: when `git diff --numstat` shows four digits or more, check whether line
width was squeezed toward 80 — editor plugins and repository formatters reflow **the whole file** to
their own default width when they write it, that action is unconstrained when the repository has no
formatter configuration, and much repository source is written in a wide-line style.

**Recovery is the worker's job; the coordinator only preserves evidence and sends it back.** Back up
the full diff, the untracked files and the index first, then confirm file by file which content is
real work. A non-empty `git diff --cached` does not prove the rest of the working tree is noise; do
not check out anything before that confirmation and backup. The full recovery order is in the
reference file.

**Root fix**: only when you have confirmed the current worker really loaded a reflowing plugin and the
repository carries automatic-reflow risk, configure the locally ignored override per the
[recovery reference](reformat-noise-recovery.md); other environments do not introduce that
configuration.

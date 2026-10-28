# G-docs / G-wayfinder / G-spec / G-tickets — gates for documentation and planning tickets

**When to read this file**: the ticket in hand is a design, spec or ticket-splitting ticket and you are
heading into closing acceptance.
**Read only the section you need**, do not read it end to end — the four gates' criteria are not
interchangeable (G-docs and G-wayfinder in particular produce completely different artifacts, and
their criteria must not be borrowed from each other).

**An implementation ticket goes through none of these four gates**; it goes through G-impl (see
SKILL.md §6).

---

## Contents

- [G-docs — requirement alignment (the grill-with-docs path: document structure completeness)](#g-docs--requirement-alignment-the-grill-with-docs-path-document-structure-completeness)
- [G-wayfinder — the wayfinder path (map and decision tickets)](#g-wayfinder--the-wayfinder-path-map-and-decision-tickets)
- [G-spec — after to-spec lands](#g-spec--after-to-spec-lands)
- [G-tickets — after to-tickets lands](#g-tickets--after-to-tickets-lands)

---

## G-docs — requirement alignment (the grill-with-docs path: document structure completeness)

**Covers only the design document grill produces.** The wayfinder path goes through G-wayfinder.

- The spec/document file exists, its sections exactly equal the repo effort template's sections, with
  no improvised sections and no leftover draft code blocks.
- Terminology decisions are landed inline in `CONTEXT.md` (not as "TBD" placeholders).
- An ADR exists only when all three conditions hold; when they do not, no ADR exists (**less is a
  pass**).
- The design tree's frontier is empty: no unresolved questions, no "open decision" placeholders.
- The worker's completion report shows the grill round records and where each round's answers went.

### After G-docs there is still work

A full implementation request normally runs
`grill-with-docs → to-spec → to-tickets → implement-spec`. G-docs accepts only the design stage; once
the design file's PR passes G-merge and is auto-merged, if this round asked only for design, record
the follow-up entry point in the report and stop; if this round includes implementation, continue
with to-spec and to-tickets. See SKILL.md §7.

---

## G-wayfinder — the wayfinder path (map and decision tickets)

**Applicability**: §1 judged the input as "too large for one session, heavy fog (several undecided
directions)" and this round uses `wayfinder`. Check first whether the target repository already has
Wayfinding conventions; when it does not, do not assume labels and mappings on your own.

**Read the repository's own Wayfinding operating section first**, then run this section's criteria:
the map and its child tickets, native blocking, the frontier query, claiming and resolving all live
there. **This section only covers what to accept.**

- **The map exists and is a single issue**, carrying the map label, with four sections in its body:
  destination / notes / decisions so far / not yet specified (+ out of scope, optional).
- **Every child ticket is a decision ticket, not an implementation slice**: its body answers only "what
  must be decided", and it carries a type label (`research` / `prototype` / `grilling` / `task`).
  **Criterion**: the ticket's output is **one decision**, not a piece of deliverable; if it is "do a
  thing" (write code, change configuration), it is an implementation ticket from SKILL.md §7 and does
  not belong on this map.
- **Blocking uses the tracker's native dependency relation**, not a hand-written line in the body — only
  a native relation draws the frontier **visibly** in the tracker UI, and that UI is exactly where a
  human judges "which one is next". Bot wiring takes the database id, not the issue number (commands
  are in the repository's Wayfinding operating section).
- **An empty frontier is this stage's endpoint**: among the map's open child tickets, remove those with
  an open blocker and those with an assignee; what remains should be empty. And **nothing in not yet
  specified can still become a ticket** (the fog has cleared). **Verify the two conditions
  separately**: an empty frontier ≠ cleared fog (the former only means nothing is pickable right now;
  the latter requires every question that can take shape to have taken shape).
- **Each entry in decisions so far points at its ticket**, without restating the decision — the map is
  an **index**, not a store; a decision lives in exactly one place (its ticket).
- **The closing signal is not "are we done" but "is the road clear"**: wayfinder produces decisions by
  default (plan, don't do); if the effort carries it all the way to execution, either the effort
  explicitly overrode that in its notes, or the fog has cleared and it is time to hand off to §7 for
  implementation tickets. **State in the report which of the two it is.**

---

## G-spec — after to-spec lands

- The spec has landed at this round's delivery endpoint; when a tracker publication is needed, labels
  and states follow the target repository's conventions. If the repository distinguishes a spec anchor
  from implementation tickets, do not mix the two. When the upstream skill conflicts with the
  repository's conventions, check the user's goal first, then land per this repository's rules.
- Seams are declared and as few as possible (ideally one), and as high as possible; use
  codebase-design vocabulary.
- User stories cover enough length; Out of Scope is non-empty.

**Seam placement is reply-protocol.md §5.2 criterion 2 (approach fork)**: attach your leaning and ask
the human per SKILL.md §5, and record the answer in the audit list.

---

## G-tickets — after to-tickets lands

- Every ticket is a vertical tracer bullet (cuts through all layers, independently verifiable, fits in
  one context), blocking edges are declared; a wide refactor uses expand–contract instead of a hard
  cut.
- Tickets are published to the configured tracker first (a remote issue or a committed local file). On
  the long-horizon path the worker cuts the integration branch from the default base and each
  implementer cuts its own branch from the integration branch; a downstream ticket only waits for its
  blocker to merge into the integration branch, not for the whole map to merge.
- **Long-horizon entry check**: a spec pointer exists; every ticket has a title, what to build,
  acceptance criteria and a state; every blocker points at a ticket that really exists; the graph is
  acyclic; the frontier has at least one ticket; the tracker is reachable and local ticket files are
  visible from the worktree; every ticket fits in a fresh context. If any fails, go back to
  `to-tickets` and do not dispatch `implement-spec`.
- On a per-ticket fallback, downstream tickets wait for the upstream PR to merge before cutting their
  base; stacked PRs remain an explicit exception (time pressure plus a short dependency chain) — when
  used, write the stack order on the tickets, §6.5 merges in stack order, and a rebase of any one
  rebases the whole stack.

**Splitting granularity is reply-protocol.md §5.2 criterion 3 (scope boundary)**, and likewise goes to
the human. When writing splitting options, describe **the number of tickets and what each delivers** in
to-tickets' own language; do not invent colloquialisms (SKILL.md §7 has the ban and the replacement
table).

---

## Related

- SKILL.md §6 — the master table routing gates by ticket type (read it first to confirm which gate
  applies)
- SKILL.md §7 — advancing by delivery endpoint, splitting language, and closing reconciliation for
  design tickets
- SKILL.md §5 — decisions to the human, details answered for them (seam placement and splitting
  granularity both go through it)

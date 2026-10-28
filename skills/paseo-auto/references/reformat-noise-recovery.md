# Formatter reflow noise: evidence and recovery

**When to read this**: after a worker finishes you find an abnormally large uncommitted diff, and a
file-by-file check shows large areas of pure formatting change. An abnormal line count is only an
investigation signal; it never justifies discarding content.

## Protect the real work first

The worker performs the recovery inside the workspace it owns; the coordinator preserves evidence,
accepts the result and gives the concrete send-back items. Before any restore or stash, save the
following evidence outside the repository in a directory with controlled permissions, and confirm the
files are readable:

```bash
git status --porcelain=v1 -uall
git diff --binary > <evidence dir>/worktree.patch
git diff --cached --binary > <evidence dir>/index.patch
git ls-files --others --exclude-standard > <evidence dir>/untracked.txt
```

Untracked files must be copied or archived one by one; the patch does not contain them. If a patch may
contain credentials, restrict access and never paste it into a message. Compare `HEAD`, the index, the
working tree and the worker's edit record file by file, and mark real changes versus formatting noise.
A non-empty `git diff --cached` only says the index has content; it **does not prove** the rest of the
working tree can be discarded.

## Recovery

Prefer rebuilding the real change from the worker's edit history or a committed version. Use
`git restore` / `git checkout` on a file only after confirming and backing up all of its real changes
file by file; after recovery, check the diff and the test results. When mixed hunks cannot be split
reliably, keep the evidence and have the worker redo the work on a clean copy instead of guessing
semantic equivalence through whitespace-insensitive comparison. If two rounds still do not converge the
diff to the expected scope, stop auto-repairing and report to the coordinator.

## Prevention conditions

Only when the current worker really loaded a reflowing formatter and its auto-formatting conflicts with
the repository style, write a local formatter override at the root of **that workspace**:

```json
{"format":{"enabled":false}}
```

Add that file to that workspace's local ignore (not a tracked ignore file) and do not commit it. Other
workers, and repositories that already have a formatting standard, follow their existing tool
configuration. This setting is a local fix for a confirmed failure, not a fixed pre-step for every
ticket.

## Paseo-specific notes

- Take evidence with `git -C <workspace.cwd>`; do not enter the worker's workspace and modify it just to
  look at the diff.
- If a clean copy must be rebuilt, have the worker do it inside its own workspace; the coordinator does
  not do it for them.
- `archive_workspace` removes the Paseo-owned worktree; do not archive before evidence collection and
  recovery are finished.

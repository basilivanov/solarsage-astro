# R14 Phase C1A-R7G — final test tail only

## Scope freeze

Read review 126. Do not change production transaction behavior unless a new
test proves an actual bug. Change only the two C1A harnesses. No production
state, C1B/C2, commit or push.

## Signal harness

Move markers exactly:

- SIG02: within the transaction profile-write loop, after the first
  `os.fsync(fd)` and `os.close(fd)`; guard with `len(created_files) == 1` so it
  pauses only once.
- SIG05: after `ngfd` opens and immediately before the first post-switch
  `vfd = os.open(...)`/read.

After `wait` and before cleanup, for every signal row assert:

```text
exact rc;
old current exact;
child no longer exists;
no .current-* / .rb-* / .rollback-* / .staging-*;
every gen-* has mode 750 and exact seven 0640 regular nlink=1 files;
canonical check-installed succeeds;
canonical retry succeeds and its new current also checks successfully.
```

If marker polling expires, send KILL, wait/reap, print/preserve sandbox path and
fail. Never leave `/tmp/sig.*`.

## Mutation harness

Run the canonical transaction harness once before the mutation matrix and
require rc 0. For each mutation, inspect the diff and require exactly one
removed source line and one added source line; adjust sed address ranges so only
the intended production occurrence changes. Keep sandbox cwd and repo-lock
snapshot. Any undetected or multi-edit mutation fails the suite.

## Acceptance

Run transaction twice directly, mutation once directly, then loader 75/B6
111/offsite/fingerprint/diff. Handoff includes SIG02/SIG05 postcondition lines
and mutation exact-one proof. Stop; no commit/push.

# R14 Phase C1A-R7E — fix env fd and prove exact retry semantics

## Scope

Read review 122. Only C1A tool and transaction/mutation tests. No production,
C1B/C2, consumers, commit or push.

## 1. Fix production recovery

- Replace the undefined `env_fd` argument in `cmd_install_set` with the owned
  `env_dir_fd`.
- Initialize `symlink_target = None` before the transaction; remove the
  `try/except NameError: pass` and pass the explicit state value.
- After strict temp unlink, strict staging/generation removal and fsync, prove
  `.current-*`, staging and new generation absence before rethrowing the
  original replace `OSError` as rc13.
- Remove broad/pass cleanup that can hide a programming error. A `NameError` or
  other unexpected recovery exception must never be mistaken for successful
  cleanup.

## 2. Make FI08/08B assertions exact

FI08 must assert:

```text
rc=13
old pointer unchanged
no .current-* / staging / new generation
stderr has ordinary safe I/O diagnostic
canonical check succeeds
canonical retry succeeds
```

FI08B must inject an explicit `OSError` in strict temp unlink (not replace code
with `pass`) and assert:

```text
rc=16
old pointer unchanged
.current-* retained and its basename appears in stderr
new diagnostic generation retained as specified
canonical retry fails closed on that artifact
```

## 3. Enforce FI12/FI13, not comments

`inject_fi_dual` must accept expected rc and pointer mode and fail unless they
match. It must assert `.rb-*` existence/target/stderr for FI12, and the defined
post-replace verification state for FI13. Remove `rm -rf ... || true`; cleanup
failure is a harness failure after evidence is captured.

## 4. Signal and mutation minimum

Before deleting each signal sandbox, assert no transaction artifacts and run
canonical check/retry. Move SIG02/SIG05 to their exact boundaries. Mutation
runner must verify exact replacement count and a green baseline per case.

## 5. Acceptance

Run the complete commands directly. Independently run the exact FI08
reproduction from review 122 and include its rc/artifact/retry output. Stop only
after all are green; no timeout/filter final evidence, commit or push.

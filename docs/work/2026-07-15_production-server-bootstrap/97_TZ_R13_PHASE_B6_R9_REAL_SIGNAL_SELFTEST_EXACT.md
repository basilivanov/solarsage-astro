# R13 Phase B6 R9 — exact implementation for real signal cleanup self-test

## Scope

Change only `scripts/tests/test-prod-deploy-source-loader.sh`. Do not invent a
second inline cleanup implementation. The self-test must execute the exact same
functions used by normal harness startup.

## 1. Canonical functions

Keep one implementation only:

```bash
lock_cleanup() {
  local td="${TEST_DIR:-}"
  local pid="${LOCK_PID:-}"
  if [ -n "$pid" ]; then
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
    LOCK_PID=""
  fi
  if [ -n "$td" ]; then
    rm -rf -- "$td"
  fi
}

on_hup()  { lock_cleanup; exit 129; }
on_int()  { lock_cleanup; exit 130; }
on_term() { lock_cleanup; exit 143; }

install_harness_traps() {
  trap on_hup HUP
  trap on_int INT
  trap on_term TERM
  trap lock_cleanup EXIT
}
```

Normal harness startup calls `install_harness_traps` after creating its own
`TEST_DIR`.

Do not define another `lock_cleanup` inside a heredoc. The child wrapper must be
generated from `declare -f lock_cleanup on_hup on_int on_term
install_harness_traps`.

## 2. Parent-owned paths

For each signal, create:

- `child_td` under `/tmp/sigclean.<signal>.XXXXXX` — owned by child cleanup;
- `wrapper` under the main harness `TEST_DIR` — parent-owned;
- `report_f` under the main harness `TEST_DIR` — parent-owned.

The report file **must not** live inside `child_td`, because successful cleanup
removes that directory before the parent verifies the holder PID.

## 3. Child wrapper content

Generate a wrapper containing:

1. shebang and `set -uo pipefail`;
2. exact function bodies emitted by `declare -f`;
3. assignment `TEST_DIR=<exact safely quoted child_td>`;
4. assignment `LOCK_PID=""`;
5. `install_harness_traps`;
6. `sleep 30 & LOCK_PID=$!`;
7. write `$LOCK_PID` to the parent-owned `report_f`;
8. `wait "$LOCK_PID"`.

Use safe shell quoting (`printf '%q'`) when embedding paths.

Do not start a second `tail -f`/read-loop process. The tracked sleep holder is
the process the child waits for and the real cleanup must kill/wait it.

## 4. Real signal execution

Run the wrapper as the foreground command of GNU timeout so SIGINT is not
silently ignored as an asynchronous shell job:

```bash
set +e
/usr/bin/timeout \
  --foreground \
  --preserve-status \
  --signal="$signame" \
  --kill-after=2s \
  1s \
  bash "$wrapper"
rc=$?
set -e
```

This is a real HUP/INT/TERM delivered to the child Bash. `--kill-after` only
bounds a broken handler; a correct handler exits before it is needed.

## 5. Assertions after timeout returns

For each signal:

1. report file exists and contains a numeric PID;
2. exact rc equals 129/130/143;
3. `kill -0 "$holder"` fails;
4. `child_td` does not exist;
5. no `sigclean.<signal>.*` artifact for that invocation remains;
6. remove only parent-owned wrapper/report files after assertions.

On assertion failure, print only symbolic signal/case reason. Then perform
best-effort cleanup of the exact child/holder/wrapper/report before returning
non-zero. Never delete or scan other concurrent harness directories.

## 6. Mutation audit assertions

Finish the already-started stage assertions using actual `%q` audit bytes:

- MUT17: `fingerprint`, exact `load-env .env.staging
  astro.vasiliy-ivanov.ru`, no controlled-stop;
- MUT18: `fingerprint`, exact `load-env .env.production wrong.com`, no
  controlled-stop;
- MUT19: `fingerprint`, exact three-argument load-env record, no
  controlled-stop;
- MUT20: exact `git rev-parse origin/bad`, no checkout/fingerprint/loader;
- MUT21: exact wrong checkout record, no fingerprint/loader;
- MUT22: exact checkout of `OLD_HEAD`, no fingerprint/loader.

Before each MUT17–22 run assert no `untracked.*`; after each run assert none.

## 7. Completion

Only after the source contains no duplicate inline cleanup implementation:

```bash
bash -n scripts/prod-deploy.sh scripts/tests/test-prod-deploy-source-loader.sh
timeout 300 bash scripts/tests/test-prod-deploy-source-loader.sh
timeout 300 bash scripts/tests/test-prod-deploy-source-loader.sh
git diff --check
```

Then rerun adversarial mode660, OLD_SHA checkout and removed-temp-cleanup copies.
No production, commit or push.

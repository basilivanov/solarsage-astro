# R14 Phase C1A-R6 review — rejected: transaction still leaves unsafe state

## Verdict

R6 is **rejected**. The reported green suites do not prove the required
transaction contract. The production implementation still contains the old
best-effort cleanup and an inner recovery `except`, and independent fault
injection leaves stale pointers/directories that block the next install.

No C1B/C2 work, production mutation, commit or push is authorized.

## Independent baseline

The following commands were run directly from the repository root (without a
`grep`/`tail` success pipeline):

```text
bash -n ...                                      OK
python3.12 -I -S ...compile(...)                  OK
test-prod-env-loader.sh                           SUCCESS
test-prod-env-profiles.sh                         75/75
test-prod-deploy-source-loader.sh                 111/111
test-prod-host-offsite-routing.sh                 SUCCESS
test-prod-env-install-transaction.sh              36/36
git diff --check                                  OK
```

The baseline being green does not waive the failures below; each failure is
observable on a fresh temporary environment and is outside the current
harness's oracle.

## P0 blockers

### 1. Current-replace failure leaves a stale `.current-*` and blocks recovery

I copied the tool, replaced the production `os.replace(current_tmp, "current",
...)` call with an explicit `OSError`, and ran `install-set` on a valid
previous generation.

Observed:

```text
fault rc=13
current before == current after
leftover: .current-<id> (symlink)
next canonical install: rc=14
Error: stale temp symlink .current-<id>
```

The recovery branch only cleans `sfd`/staging and a renamed generation. It
never removes `current_tmp` when the atomic replace itself fails. This is a
real operational deadlock: a transient replace error makes the next approved
retry fail closed until a human removes the artifact.

Required invariant: every pre-switch failure, including failure at the replace
call itself, removes the exact temporary symlink and proves no canonical
pointer changed.

### 2. Pre-directory signal leaves `.staging-*`

I paused the copied tool immediately after `os.mkdir(staging_name, ...)`, sent
`SIGHUP` directly to the child, and waited for the exact signal status.

Observed:

```text
rc=129; current unchanged
leftover: generations/.staging-<id>
```

At this boundary `sfd` is still `None`, so the current recovery code skips all
staging cleanup. The R6 signal suite pauses later (after `sfd` is open) and
therefore cannot detect this case.

Required invariant: the transaction records the staging name immediately after
mkdir and removes/validates it for a signal or exception at every pre-rename
point.

### 3. `check-installed` accepts invalid physical state

On a freshly installed temporary environment I independently ran
`check-installed` after each mutation:

```text
add generations/<current>/extra                 -> rc=0, check: OK
chmod 777 generations/<current>                 -> rc=0, check: OK
add env/.current-<id> stale symlink              -> rc=0, check: OK
```

`cmd_check_installed` calls `_validate_current_link` and then checks only the
expected profile files. It does not call the physical generation/inventory and
housekeeping validators, does not validate generation owner/mode, and does not
reject stale temp/direct legacy/non-canonical entries. This violates the
explicit C1A check contract and makes readiness checks false-green.

Required invariant: check is read-only but fail-closed for the same exact
physical state that install requires: current owner/type/target, generation
owner/mode/exact seven-file inventory, profile metadata, lock metadata and
housekeeping.

### 4. Recovery failure leaves the new pointer and has no distinct result

I injected two explicit failures into a copied tool: a post-switch failure and
the rollback `os.replace` failure. Observed:

```text
rc=13
diagnostic: Error: recovery failed, manual recovery needed
current after = new generation (not previous)
leftover: .rb-<id> -> previous generation
new generation retained
```

The required contract is a distinct recovery error with preserved/reportable
artifact paths and no claim of successful rollback. `EXIT_IO=13` is also used
for ordinary transaction I/O, and the diagnostic does not identify the
preserved artifacts. More importantly, the inline recovery currently catches
and swallows cleanup failures (`except OSError: pass`) before the outer
`except Exception`, so it is not a strict state machine.

## False-green test findings

### FI12/FI13 are not an independent oracle

The FI harness mutates the same environment sequentially. FI08 leaves
`.current-*`; subsequent runs fail at housekeeping before reaching their named
fault boundary, yet the harness counts a non-zero status plus unchanged
`current` as detection. A direct fresh FI13 copy succeeds and changes
`current`, proving the named mutation is not detected by that oracle.

The FI harness also does not assert exactly one replacement, does not run a
green canonical oracle immediately before each mutation, and does not assert
artifact state. Several `sed` expressions replace more than one occurrence.

### Signal matrix does not cover the specified boundaries

- SIG-PRE-DIR is not tested; the first pause is after `sfd` setup.
- SIG-POST-VERIFY pauses after `os.close(ngfd)`, not before content
  verification.
- `sleep 0.5` is a race, not a deterministic pause marker.
- The suite asserts only `current`; it removes the temporary environment before
  checking staging/current-temp/rollback artifacts and live generation
  integrity.
- `kill ... || true` hides failed delivery; no marker proves the child reached
  the intended boundary.

### Source still contradicts the R6 scope

The transaction body still contains:

```text
old _rollback_current/_cleanup_staging/_remove_generation helpers with
best-effort `except OSError: pass`;
inline nested `try`/`except OSError: pass` cleanup;
outer recovery `except Exception`;
sys.exit() inside cmd_install_set rather than translation in main();
no finally that restores handlers/unlocks/closes every fd.
```

This is not the required one `try/except BaseException/finally` state machine.

## Required next step

Implement `113_TZ_R14_PHASE_C1A_R7_STRICT_RECOVERY_AND_READONLY_CHECK.md`.
Do not change consumers, systemd, Docker, deploy sequence, or production paths.

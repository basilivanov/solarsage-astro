# Stage 1.W4 — architect errata: next-env mtime is not a launcher contract

Дата: 2026-07-13
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted base: `7d37acbaa31118a8545987a39a5fabe18fbb6e32`
Amends only:

- `117_STAGE_1_W4_STRICT_REAL_PREVIEW_EXECUTION_TZ.md` config snapshot equality;
- untracked allowlist/count;
- success/blocked callback config wording.

Статус: **AUTHORIZED NARROW CORRECTION — REPEAT W4 FROM FULL PREFLIGHT**

## 1. Observed fail-closed run

Первый W4 execution прошёл все preflight gates и успешно поднял managed real
preview:

```text
launcher unit: 31 passed
typecheck: PASS
prod guard: PASS
strict interception patterns: zero
astro:v2-preview.0: created
three exact launcher labels: present
root/day/API rewrite through 3003: 200
managed launcher -> Next process tree: present
3003 listener: exactly one
8001/18092: absent
```

До E2E coder остановился из-за section 7:

```text
next-env.d.ts SHA: unchanged
next-env.d.ts size: unchanged
next-env.d.ts mode/owner: unchanged
next-env.d.ts mtime: advanced
git tracked/index: clean/empty
```

Coder выполнил scoped cleanup:

```text
one C-c: sent
launcher awaited shutdown: completed
dead tmux window: removed
3003 listener/descendants: absent
services PID/start: unchanged
repository edits: zero
strict E2E: not started
```

## 2. Architect diagnosis

The W4 ТЗ incorrectly promoted `next-env.d.ts` mtime to an invariant.

Accepted launcher contract in source is explicit:

```text
readFileSnapshot -> bytes, text, permission mode
restoreGeneratedNextEnv -> exact snapshot bytes and original permission mode
```

Implementation intentionally uses:

```js
writeFileSync(filePath, snapshot.bytes)
chmodSync(filePath, snapshot.mode)
```

Next.js generates its declaration during startup. The launcher restores exact
tracked bytes and mode after readiness/shutdown. A normal write necessarily
updates mtime. The accepted source, module contract and 31 behavioral tests do
not promise historical mtime restoration.

Independent architect proof after cleanup:

```text
current next-env SHA:
7b550dda9686c16f36a17bf9051d5dbf31e98555b30d114ac49fc49a1e712651

HEAD next-env SHA:
7b550dda9686c16f36a17bf9051d5dbf31e98555b30d114ac49fc49a1e712651

size = 247
mode = 664
owner = astro:astro
git tracked tree = clean
```

Therefore there is no launcher/product defect. Do not edit launcher or tests and
do not try to restore an old mtime with `touch`, `utimes`, checkout or file
rewrite.

## 3. Unchanged prohibitions

All non-config parts of 117 remain literal:

- no repository edits by coder;
- no git add/commit/push;
- no services/env/unit/nginx changes;
- no fixtures/interception/mock/18092/8001;
- no second API/manual uvicorn;
- strict chromium + mobile E2E unchanged;
- failure cleanup scoped to managed preview;
- success leaves `astro:v2-preview.0` and review URL running.

## 4. Corrected config contract

### 4.1 next-env.d.ts

Before, during and after launcher, record:

```text
SHA-256
byte size
permission mode
owner/group
mtime for observation only
```

Acceptance requires:

```text
SHA-256 == HEAD/current preflight tracked bytes
byte size == preflight
mode == preflight
owner/group == preflight
git diff for next-env.d.ts == empty
```

mtime is explicitly non-contractual. It may remain equal or advance after Next
generates and launcher restores the declaration. It must not be manually
modified or restored.

### 4.2 tsconfig.json

`tsconfig.json` remains verify-only during successful startup.

Require exact preflight equality for:

```text
SHA-256
byte size
mode
owner/group
mtime
git diff
```

Any tsconfig write/drift is still failure.

### 4.3 package.json and pnpm-lock.yaml

Require exact preflight equality for SHA, size, mode, owner/group, mtime and git
diff.

### 4.4 Git authority

`git diff --quiet` and `git diff --cached --quiet` remain the ultimate tracked
content/index gates. They must stay clean while preview is running and after
tests.

## 5. Corrected untracked allowlist

Repeat full preflight from section 5 of 117. Exact seven untracked paths:

```text
?? .grace/
?? artifacts/design/
?? docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
?? docs/work/2026-07-11_today-v2-real-horizons-main-deploy/117_STAGE_1_W4_STRICT_REAL_PREVIEW_EXECUTION_TZ.md
?? docs/work/2026-07-11_today-v2-real-horizons-main-deploy/118_STAGE_1_W4_ARCH_ERRATA_NEXT_ENV_MTIME_NON_CONTRACT_TZ.md
?? grace.db
?? skills/
```

Any other tracked/untracked/index path blocks execution.

## 6. Repeat W4 from full preflight

Do not resume at E2E directly.

Repeat:

1. git/local/remote identity;
2. exact seven untracked paths;
3. service PID/start/listeners/health;
4. absence of preview window/process/3003 listener;
5. corrected config snapshots;
6. launcher unit 31, typecheck, prod guard, static strictness;
7. one new managed `astro:v2-preview` window;
8. exact readiness labels and three HTTP 200;
9. managed process ownership;
10. corrected config/git clean proof;
11. strict chromium + mobile E2E;
12. artifact/journal/final running proof.

Do not create a second window while one exists. Only one successful managed
preview may remain.

## 7. Corrected callback fragments

On success replace:

```text
config_snapshots: EXACT_UNCHANGED
untracked_scope: EXACT_6_ALLOWED
```

with:

```text
next_env_bytes_size_mode_owner: EXACT_HEAD_AND_PREFLIGHT
next_env_mtime: OBSERVED_NON_CONTRACT
tsconfig_package_lock_snapshots: EXACT_UNCHANGED
tracked_config_diff: ZERO
untracked_scope: EXACT_7_ALLOWED
```

All other success fields in 117 remain required.

On failure cleanup, `config_restored: PASS` means:

```text
next-env exact HEAD bytes/size/mode/owner and zero git diff;
tsconfig/package/lock exact snapshots including mtime;
```

Do not classify next-env mtime advancement alone as failure.

После callback остановиться. On full success leave preview running; no evidence
doc or commit/push until architect review.

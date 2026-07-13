# Stage 2.W3C — sidecar changed-path static proof

Дата: `2026-07-13`

Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`0717bdd4123cee145a30d2c6120f22d155522246`

Parent master:
`127_STAGE_2_CORRECTIVE_RELEASE_MAIN_DEPLOY_WAVE_MASTER.md`.

Accepted predecessor:
`167_STAGE_2_W3B3_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md`.

Статус: **W3C AUTHORIZED — READ-ONLY PROOF WAVE, NO CODE EDITS, NO COMMIT/PUSH**

Исполнитель работает лично. Запрещены subagents, delegation, `delegate_*`,
background coding/review agents и использование их результатов as evidence.

## 1. Goal

Prove the release requirement for feature-changed sidecar paths without
mixing unrelated legacy static debt into the V2 release:

1. inventory the exact sidecar diff against `origin/main`;
2. run Ruff 0.15.14 from the API venv against all changed Python paths;
3. prove every remaining Ruff diagnostic is pre-existing in main and lies on
   an unchanged line;
4. prove the feature introduced zero new Ruff diagnostic signatures and zero
   diagnostics on added/replaced lines;
5. run the complete sidecar test suite and sidecar-venv `pip check`;
6. preserve source, venvs, runtime services and ports byte-for-byte.

This is a proof-only wave. No source correction is currently authorized.

## 2. Entry gate

Require before any command:

```text
HEAD = upstream feature = remote feature
  0717bdd4123cee145a30d2c6120f22d155522246

main = origin/main = remote main
  c9bc36bd9a947566eddb1ffcf5617967c7412676

tracked worktree                 clean
index                            empty
```

Allowed untracked state:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/168_STAGE_2_W3C_SIDECAR_CHANGED_PATH_STATIC_PROOF_TZ.md
```

Stop on mismatch. Do not reset, restore, checkout, stash, amend or rebase.

## 3. Exact sidecar inventory

The branch changes exactly 18 sidecar paths against main:

```text
apps/solarsage/Dockerfile
apps/solarsage/pyproject.toml
apps/solarsage/solarsage/api/activation_layer.py
apps/solarsage/solarsage/core/versions.py
apps/solarsage/solarsage/schemas/activation.py
apps/solarsage/solarsage/services/activation_builder.py
apps/solarsage/solarsage/services/firdar.py
apps/solarsage/solarsage/services/returns.py
apps/solarsage/solarsage/services/transit_timing.py
apps/solarsage/solarsage/utils/ephemeris.py
apps/solarsage/tests/test_activation_layer_endpoint.py
apps/solarsage/tests/test_activation_schema.py
apps/solarsage/tests/test_activation_transits.py
apps/solarsage/tests/test_firdar.py
apps/solarsage/tests/test_lunar_return.py
apps/solarsage/tests/test_profections.py
apps/solarsage/tests/test_solar_return.py
apps/solarsage/tests/test_transit_timing.py
```

Exactly 16 of them are Python files; `Dockerfile` and `pyproject.toml` are not
Ruff inputs.

Require exact inventory equality before continuing.

## 4. Absolute no-edit constraints

Do not edit any tracked file, including sidecar source/tests, pyproject,
Dockerfile, lock/config/generated files or this architect-owned document.

Do not:

- run Ruff `--fix` or formatter;
- install Ruff or any package into `apps/solarsage/venv`;
- change sidecar venv metadata;
- add noqa/ignore/per-file-ignore/exclude rules;
- change test expectations;
- stage, commit or push;
- start/restart/reload services or containers.

Use only:

```text
Ruff executable:    apps/api/.venv/bin/python -m ruff
Sidecar tests/pip:  apps/solarsage/venv/bin/python
```

## 5. Confirmed baseline classification

Architect inventory established:

```text
Ruff version                                  0.15.14
origin/main diagnostics on 14 existing paths 18
feature diagnostics on 16 current paths       8
removed baseline diagnostics                 10
new normalized signatures                     0
diagnostics on feature-added/replaced lines    0
```

The eight current diagnostics are legacy expressions already present in
`origin/main`:

```text
activation_builder.py
  F841 planet_names
  F841 target_type_prefix
  E741 list-comprehension variable l
  F841 source_display
  F401 progressed_sun_transitions import

test_activation_layer_endpoint.py
  F401 pytest import
  F541 SUPPORTED_ORDER message
  F541 ALL_TECHNIQUES message
```

None of these lines was added or replaced by the feature diff. Do not clean
them in W3C. The master permits documented legacy debt and forbids unrelated
cleanup; the owned release invariant is zero new feature diagnostics.

## 6. Required Ruff evidence

### 6.1 Current changed paths

From repo root:

```bash
mapfile -t paths < <(
  git diff --name-only origin/main...HEAD -- apps/solarsage |
  rg '^apps/solarsage/.*\.py$'
)

test "${#paths[@]}" -eq 16

set +e
apps/api/.venv/bin/python -m ruff check \
  --output-format json "${paths[@]}" \
  > /tmp/stage2-w3c-current-ruff.json
rc=$?
set -e
test "$rc" -eq 1
```

Require exact 8 diagnostics.

### 6.2 Diff-line ownership proof

Parse each diagnostic row against the new-side hunk ranges from:

```bash
git diff --unified=0 origin/main...HEAD -- <diagnostic path>
```

For every `@@ -old +new,count @@`, treat only the `new ... new+count-1`
range as feature-added/replaced. Require:

```text
feature_added_line_diagnostics = 0
```

The proof parser must use diagnostic JSON and hunk headers, not manual visual
claims or current blame alone.

### 6.3 Main comparison

Of the 16 current Python paths, first use `git cat-file -e origin/main:<path>`
to select the exact 14 paths that exist in `origin/main`. The two added clean
files `solarsage/services/transit_timing.py` and
`tests/test_transit_timing.py` must not be passed to Ruff as nonexistent main
paths, because Ruff would report synthetic `E902` missing-file diagnostics.

Export the 14 existing `origin/main` paths into a temporary directory outside
the repository, run the same API-venv Ruff JSON command, and compare normalized
`(code, message)` multisets.

Require:

```text
main existing paths            14
main diagnostics               18
current diagnostics             8
current minus main signatures   0
main minus current diagnostics 10
```

Delete the temporary directory after the proof. Do not create a git worktree,
branch, stash or tracked artifact.

## 7. Required runtime-independent sidecar gates

Run from repo root:

```bash
PYTHONPATH=apps/solarsage \
  apps/solarsage/venv/bin/python -m pytest apps/solarsage/tests/ -q

apps/solarsage/venv/bin/python -m pip check
```

Require:

```text
sidecar tests   201 passed
skipped         0
failed/errors   0
warnings        exact known Starlette deprecation only
pip check       No broken requirements found
```

Do not run or start the sidecar server. No port is required for these tests.

## 8. Worktree/runtime proof

After all commands require:

- `git status --short` has no tracked change;
- index empty;
- only the allowed untracked state from section 2 remains;
- `git diff --check` passes;
- local/tracking/remote refs unchanged;
- main refs unchanged;
- no listener on `3003`, `8001`, `18092`;
- no systemd/Docker/runtime mutation.

No evidence JSON or logs may be added to the repository. `/tmp` evidence is
ephemeral and must contain no secret/profile/auth data.

## 9. Required callback and stop

```text
READY_STAGE_2_W3C_SIDECAR_STATIC_PROOF_REVIEW
base_head: 0717bdd4123cee145a30d2c6120f22d155522246
sidecar_changed_paths: EXACT_18
sidecar_changed_python_paths: EXACT_16
ruff_binary: API_VENV_0.15.14
sidecar_venv_tool_install: NOT_PERFORMED
ruff_main_diagnostics: 18
ruff_current_diagnostics: 8
ruff_removed_baseline: 10
ruff_new_normalized_signatures: ZERO
ruff_feature_added_line_diagnostics: ZERO
sidecar_tests: 201_PASS
sidecar_test_warning: KNOWN_STARLETTE_DEPRECATION_ONLY
sidecar_pip_check: PASS
tracked_worktree: CLEAN
index: EMPTY
frozen_untracked: PRESERVED
runtime_services: UNCHANGED
ports: 3003/8001/18092_ABSENT
commit_push: NOT_PERFORMED
final_rc: NOT_STARTED
main_deploy: NOT_STARTED
```

Then stop for architect review.

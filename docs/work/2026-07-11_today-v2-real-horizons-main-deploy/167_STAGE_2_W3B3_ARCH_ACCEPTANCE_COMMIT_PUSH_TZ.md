# Stage 2.W3B3 — architect acceptance, commit and push

Дата: `2026-07-13`

Branch: `preview/solarsage-v2-human-first-navigator-ux`

Accepted parent / current HEAD:
`a0646a0b2d02f3a40c209a45286cb60d0d846a91`

Implementation chain:

- `160_STAGE_2_W3B3_SEMANTIC_TODAY_INTEGRATION_MYPY_TZ.md`;
- `163_STAGE_2_W3B3_AUTHORIZATION_BASE_AND_GATE_AMENDMENT_TZ.md`;
- `164_STAGE_2_W3B3_R1_PREFETCH_AND_BOUNDARY_CORRECTION_TZ.md`;
- `165_STAGE_2_W3B3_R1A_EXACT_STALE_MOCK_AND_GATE_AMENDMENT_TZ.md`;
- `166_STAGE_2_W3B3_R2_EXACT_PREFETCH_CALL_ASSERTIONS_TZ.md`.

Статус: **ARCHITECT ACCEPTED — AUTHORIZE EXACT COMMIT AND PUSH ONLY**

No subagents, delegation or background coding/review agents.

## 1. Accepted architecture

Architect review accepts the final result:

- one canonical `ContentAccessState` Python class and unchanged JSON wire;
- no runtime `__doc__` mutation;
- strict `SemanticLayer.model_dump()` boundary;
- exact W3B3 MyPy correction with no feature diagnostics;
- validated birth-identity narrowing without fake fallback;
- typed horizon audit union;
- canonical `SessionLocal` for background prefetch;
- seven independent per-day sessions under one concurrent gather;
- per-day failure boundary includes session acquisition and payload build;
- strong asyncio task ownership until completion;
- no request DB reuse and no preview selection-context propagation;
- exact regression proof for child user/date/access/kwargs and DB identities;
- generated contracts unchanged by this wave.

## 2. Independently confirmed gates

```text
Ruff changed paths                         PASS 7
GRACE self-tests                           13 PASS
GRACE changed paths                        PASS 7
cold MyPy                                  80 diagnostics / 11 paths
MyPy feature production paths              0 errors
focused R1A tests                          68 PASS
W3B3 targeted suite                        226 PASS
full API                                   1406 PASS / 4 SKIP
full API lifecycle errors/warnings          0
known Starlette deprecation warning         1 accepted
contracts focused generation tests         110 PASS
contracts generated drift                   0
contracts compatibility                    16 additive / 0 breaking
fixture normalization                      PASS
Python contract package                    44 PASS
frontend guard                             PASS
content access identity/source guards      PASS
git diff --check                           PASS
today_service.py lines                     998
test_today_preview_transport.py lines      1000
index                                      empty
feature local/tracking/remote               a0646a0... equal
main/origin-main                            c9bc36b... unchanged
ports 3003/8001/18092                       absent
```

## 3. Accepted hashes before commit

Require these exact hashes before staging:

```text
9ea5bab15dca91b35ae2876489550d5d2126c213e351e4f1aa3fedc2e7ddcc76  apps/api/app/schemas/access.py
3e026b959d0eb6f851342120e2fec6ccb833fb32b5de5d277b5da9ec4399375d  apps/api/app/schemas/today.py
532a173c6646ad4cee49a173c81bf7b43fbbe91008d3b9b831a94577d9b70c6c  apps/api/app/services/semantic_v2_service.py
874f236f0a8b38015d3da6e2c04a820b4e30c683954bdf3aac3b8bc7936cf388  apps/api/app/services/today_service.py
af07ba25208f5d06cabed561431518a4635af32ec51ce9d756333eebc20f0042  apps/api/tests/test_day_no_birthday_fallback.py
7186f7249b5d35de1ddd2f4dfe41706243b1e7735a3d6e6aee67e5d87c7b4800  apps/api/tests/test_today_preview_transport.py
e162cd9d50ac5d8ce6de6e9717cb74340a617d3d08a0b7f850bf54b7dd48eb3b  apps/api/tests/test_wave3_day_pipeline_reuse.py
f29742d0d7eeb6527ccdcc34e7ec65fae2aa537774aabdbde7320fe7e5014a7f  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/163_STAGE_2_W3B3_AUTHORIZATION_BASE_AND_GATE_AMENDMENT_TZ.md
9125fa8747c925d9c65d47228b6d220abb224456fc9d785fc32475dc8245b244  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/164_STAGE_2_W3B3_R1_PREFETCH_AND_BOUNDARY_CORRECTION_TZ.md
a0d8b8fe29114a93c1472e9d6bb685fb1262b919dbdcdcb6386dd594ad92a116  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/165_STAGE_2_W3B3_R1A_EXACT_STALE_MOCK_AND_GATE_AMENDMENT_TZ.md
58df0339c844c05b29a12b6734571d7e90a2a9b1b4657b8c19a5b8436880109b  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/166_STAGE_2_W3B3_R2_EXACT_PREFETCH_CALL_ASSERTIONS_TZ.md
```

Doc 167 is newly architect-created and is not included in the pre-existing
hash list.

Stop on any mismatch. Do not repair, reset, restore, checkout, amend or rebase.

## 4. Exact staging allowlist

Stage exactly these 12 paths:

```text
apps/api/app/schemas/access.py
apps/api/app/schemas/today.py
apps/api/app/services/semantic_v2_service.py
apps/api/app/services/today_service.py
apps/api/tests/test_day_no_birthday_fallback.py
apps/api/tests/test_today_preview_transport.py
apps/api/tests/test_wave3_day_pipeline_reuse.py
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/163_STAGE_2_W3B3_AUTHORIZATION_BASE_AND_GATE_AMENDMENT_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/164_STAGE_2_W3B3_R1_PREFETCH_AND_BOUNDARY_CORRECTION_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/165_STAGE_2_W3B3_R1A_EXACT_STALE_MOCK_AND_GATE_AMENDMENT_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/166_STAGE_2_W3B3_R2_EXACT_PREFETCH_CALL_ASSERTIONS_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/167_STAGE_2_W3B3_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md
```

Use explicit `git add -- <12 paths>`. Never use `git add .`, `git add -A`, a
directory add or wildcard.

Frozen unrelated untracked paths must remain untracked and unstaged:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

After staging require:

- `git diff --cached --name-only` equals the exact 12-path set;
- unstaged tracked diff is empty;
- frozen groups remain absent from the index;
- `git diff --cached --check` passes.

## 5. Exact commit

Create one normal commit with exact subject:

```text
refactor(api): harden today semantic pipeline
```

No amend, fixup, squash, rebase, merge commit, signing workaround or hook
bypass.

After commit require:

- parent exactly `a0646a0b2d02f3a40c209a45286cb60d0d846a91`;
- commit contains exact 12 paths;
- worktree has no tracked modifications;
- index empty;
- only frozen unrelated untracked groups remain.

## 6. Exact push

Push only the current feature branch:

```bash
git push origin HEAD:preview/solarsage-v2-human-first-navigator-ux
```

No force, no tags, no main push.

After push independently prove:

```text
local HEAD = upstream feature = remote feature
main = origin/main = remote main = c9bc36bd9a947566eddb1ffcf5617967c7412676
```

Do not start W3C, final RC, main merge or deploy.

## 7. Runtime prohibition

Do not start/restart/reload/stop any systemd, Docker, frontend, API or sidecar
service. Do not bind ports `3003`, `8001`, `18092`. Canonical services and
ports remain untouched.

## 8. Required callback and stop

```text
PUSHED_STAGE_2_W3B3_ACCEPTED
parent: a0646a0b2d02f3a40c209a45286cb60d0d846a91
commit: <40-char SHA>
subject: refactor(api): harden today semantic pipeline
commit_paths: EXACT_12
local_tracking_remote_feature: EQUAL
main_origin_remote_main: c9bc36bd9a947566eddb1ffcf5617967c7412676_UNCHANGED
tracked_worktree: CLEAN
index: EMPTY
frozen_untracked: PRESERVED
runtime_services: UNCHANGED
ports: 3003/8001/18092_ABSENT
w3c: NOT_STARTED
main_deploy: NOT_STARTED
```

Then stop.

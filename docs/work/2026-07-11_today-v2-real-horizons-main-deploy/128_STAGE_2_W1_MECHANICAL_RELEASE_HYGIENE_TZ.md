# Stage 2.W1 — mechanical release hygiene

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`7179818b6504be725afa48b513bc1f0a7852e387`
Parents: `126_STAGE_2_W0_RELEASE_CANDIDATE_GATE_INVENTORY_TZ.md`,
`127_STAGE_2_CORRECTIVE_RELEASE_MAIN_DEPLOY_WAVE_MASTER.md`

Статус: **AUTHORIZED MECHANICAL CORRECTION — NO MAIN, DEPLOY OR SERVICE CHANGE**

## 1. Scope and outcome

This wave fixes only three proven release-hygiene groups:

1. `git diff --check origin/main...feature` — 71 trailing-whitespace issues
   and one extra EOF blank line in 18 historical architect documents;
2. two false secret examples in tracked baseline docs/script;
3. one exact empty ignored `packages/py-contracts/solarsage_contracts.egg-info/`
   directory that masks installed distribution metadata during tests.

No application behavior, contract schema, frontend, API or sidecar source may
change.

Expected exit:

```text
feature diff check = PASS
guardrails:secrets = PASS
py-contracts = 44 PASS
tracked task diff = exact 20 existing paths + docs 126–128
```

## 2. Preflight

Require:

```text
branch/head/tracking/remote = preview/... / 7179818...
main/origin-main = c9bc36b...
origin/main direct ancestor; feature-only 44; main-only 0
tracked tree/index clean
untracked = five frozen paths + architect docs 126–128
3003/8001/18092 absent
API/sidecar/frontend/nginx active and PID/start unchanged from W0
```

Run and preserve `/tmp/stage2-w0-*` logs read-only until callback.

## 3. Exact markdown hygiene allowlist

Edit only these 18 existing documents for whitespace:

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/67_STAGE_B2B1_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/68_STAGE_B2B2_DETERMINISTIC_GUIDANCE_CLAIMS_COVERAGE_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/69_STAGE_B2B2_ARCH_REVIEW_CORRECTIONS_R1_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/70_STAGE_B2B2_ARCH_REVIEW_CORRECTIONS_R2_NEW_CODER_HANDOFF_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/71_STAGE_B2B2_ARCH_REVIEW_CORRECTIONS_R3_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/72_STAGE_B2B2_ARCH_REVIEW_CORRECTIONS_R4_SANITIZATION_FINAL_PROOF_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/73_STAGE_B2B2_R5_NEW_CODER_CONTINUATION_FINAL_SANITIZATION_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/74_STAGE_B2B2_ACCEPTANCE_COMMIT_PUSH_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/86_STAGE_B4_W1_GENERATED_WIRE_STEADY_STATE_CONSUMER_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/87_STAGE_B4_W1_ARCH_REVIEW_R1_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/88_STAGE_B4_W1_ARCH_REVIEW_R2_FINAL_CLEANUP_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/89_STAGE_B4_W1_ACCEPTANCE_COMMIT_PUSH_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/91_STAGE_B4_W2_FINAL_HUMAN_FIRST_UX_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/92_STAGE_B4_W2_ARCH_REVIEW_R1_COMPLETENESS_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/93_STAGE_B4_W2_ARCH_REVIEW_R2_PROOF_TRUTH_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/94_STAGE_B4_W2_ARCH_REVIEW_R3_FINAL_CONTRACT_CLEANUP_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/95_STAGE_B4_W2_ARCH_REVIEW_R4_CARD_COPY_ORDER_INVARIANT_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/96_STAGE_B4_W2_ACCEPTANCE_BUILD_CLEANUP_COMMIT_PUSH_TZ.md
```

Allowed transformations only:

- remove spaces/tabs at line ends;
- in document 74, remove the single extra blank line at EOF;
- preserve all visible text, headings, punctuation, code-fence contents and
  final one-newline convention.

A bounded mechanical whitespace formatter over the exact allowlist is allowed.
Do not run a general Markdown formatter.

## 4. Exact secret-example corrections

### 4.1 `DEPLOYMENT_GUIDE.md`

At the migration example, remove the literal credential-bearing assignment:

```text
DATABASE_URL=postgresql+asyncpg://astro:astro_dev_password@localhost:5433/astro
```

Replace it with truthful prose saying `DATABASE_URL` must already be supplied
through the protected environment, followed by the command without an inline
assignment:

```bash
cd apps/api
../../venv/bin/alembic upgrade head
```

Do not invent a new credential placeholder containing `KEY=value`.

### 4.2 `scripts/alert.sh`

Replace only the usage line that prints:

```text
export TELEGRAM_BOT_TOKEN=your_token
```

with a safe instruction that both environment variables must be set, without
any token-like `KEY=value` literal. Script behavior and exit codes remain
unchanged.

No secret-scanner rule or allowlist edit.

## 5. Exact ignored artifact cleanup

Before removal prove:

```text
packages/py-contracts/solarsage_contracts.egg-info/
is git-ignored
contains zero filesystem entries
```

Remove it only with `rmdir`. If non-empty, stop and report; do not `rm -rf`.

After removal prove installed API distribution metadata remains:

```text
name = solarsage-contracts
version = 0.1.0
```

Do not install/reinstall packages in this wave.

## 6. Gates

Run:

```bash
git diff --check
git diff --check origin/main...HEAD
pnpm guardrails:secrets

PYTHONPATH=packages/py-contracts \
  apps/api/.venv/bin/python -m pytest packages/py-contracts/tests/ -q

pnpm contracts:check
```

Because the whitespace fixes are uncommitted, also construct the prospective
tree check without committing. At minimum verify:

- `git diff --check` current working diff = zero;
- every path/line previously listed in `/tmp/stage2-w0-feature-diff-check.log`
  no longer has trailing spaces in the worktree;
- document 74 ends with exactly one newline and no blank line;
- after the later commit, `git diff --check origin/main...HEAD` is expected zero.

Exact expected:

```text
secrets guard PASS
py-contracts 44 passed
contracts check 110 passed
```

No need to rerun full frontend/API/sidecar suites for this mechanical wave.

## 7. Scope proof and callback

Tracked diff must be exactly:

```text
18 markdown hygiene paths
DEPLOYMENT_GUIDE.md
scripts/alert.sh
```

Architect docs 126–128 are untracked and byte-identical. Index empty. No
commit/push until architect review.

Runtime final:

```text
3003/8001/18092 absent
canonical service PID/start unchanged
no env/systemd/build/runtime mutation
```

Callback:

```text
READY_STAGE_2_W1_HYGIENE_REVIEW
tracked_scope: EXACT_20
markdown_whitespace: 71_TRAILING_PLUS_1_EOF_FIXED
secret_examples: EXACT_2_SAFE
ignored_egg_info: EMPTY_REMOVED
distribution_metadata: SOLARSAGE_CONTRACTS_0_1_0
working_diff_check: PASS
prospective_feature_diff_check: PASS
secrets_guard: PASS
py_contracts: 44 PASS
contracts_check: 110 PASS
index: EMPTY
commit_push: NOT_PERFORMED
runtime_services: UNCHANGED
ports: 3003/8001/18092 ABSENT
architect_docs: UNCHANGED_126_TO_128
```

Then stop for architect review.

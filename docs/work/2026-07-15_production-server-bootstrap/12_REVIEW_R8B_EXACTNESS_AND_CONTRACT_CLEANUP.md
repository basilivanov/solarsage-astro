# Review R8B — exactness and contract cleanup

Дата: 2026-07-15

R8 architecture is accepted. Fix only the exactness/contract issues below; preserve R3–R8A changes.

## Allowed files

```text
scripts/prod-deploy.sh
infra/production/solarsage-github-deploy
.github/workflows/deploy-production.yml
docs/PRODUCTION_RUNBOOK.md
```

No other runtime file changes. No restore/reset/checkout/clean, commit, push, server access or deploy.

## 1. Wrapper must use one literal space

Current regex uses `[[:space:]]+`, which accepts tabs/multiple spaces/newline-like whitespace while the contract says exact `deploy <sha>`.

Accept only:

```text
deploy<one ASCII space><40 lowercase hex>
```

Use a Bash regex equivalent to:

```bash
^deploy\ ([0-9a-f]{40})$
```

Prove that one literal space passes in inert harness and tab, two spaces, leading/trailing whitespace all fail 126.

Update wrapper contract:

- `emitted_logs` must mention safe stderr validation errors;
- inputs/output/invariants must reflect exact pinned command;
- rejected command value must never be printed.

## 2. NUL-safe non-ignored untracked detection

`untracked=$(git ls-files ...)` loses trailing newlines and cannot safely represent arbitrary Git paths.

Keep the required command but use NUL records:

```bash
git ls-files --others --exclude-standard -z
```

Preferred Bash implementation: `mapfile -d '' -t` into a local array, then test array length. Print each path safely with Bash `printf '%q'` or an equally safe path-only representation. Do not print contents and do not mutate files.

Regression must include a non-ignored untracked filename containing a newline and prove gate fails/preserves it; after matching ignore rule, gate passes.

## 3. Parser/module contract accuracy

In the deploy script module contract inputs, document both:

```text
--current
--expected-sha <40 lowercase hex>
```

`check_clean_source` contract may say it exits on failure, but wording must match its real safe path logging.

## 4. Provider validation

Normalize provider with `strip().lower()` and require the selected key to be non-empty after `.strip()`.

Do not print key value. Unsupported provider remains failure.

## 5. Runbook env placement and wording

Under `Required Environment Variables`, add:

- `OPENROUTER_API_KEY`: required when `LLM_PROVIDER=openrouter`;
- `ANTHROPIC_API_KEY`: required when `LLM_PROVIDER=anthropic`.

Do not claim both values must be mutually exclusive or that the inactive key must be absent. State that only the active provider key is required/validated. Remove or correct the contradictory sentence in deployment transport section.

## 6. Workflow contract comments

No runtime workflow behavior change. Update only contract/invariants if needed to document:

- main ref + exact `GITHUB_SHA` guard;
- empty permissions;
- 45-minute job bound;
- exact pinned remote command.

## Checks

```bash
bash -n scripts/prod-deploy.sh
bash -n infra/production/solarsage-github-deploy
git diff --check
python3 - <<'PY'
from pathlib import Path
import yaml
yaml.safe_load(Path('.github/workflows/deploy-production.yml').read_text())
PY
```

Wrapper inert harness scenarios:

1. exact one-space command -> exact expected argv;
2. empty -> 126;
3. tab -> 126;
4. two spaces -> 126;
5. leading space -> 126;
6. trailing space -> 126;
7. uppercase/short/extra token -> 126.

Clean gate scenarios from R8 plus newline-containing filename. Repeat R7 byte-exact scenarios, guardrails, systemd verify and visudo.

Return exact diff scope and results. Stop after handoff.

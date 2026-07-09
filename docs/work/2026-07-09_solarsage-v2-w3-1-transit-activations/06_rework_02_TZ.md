# Rework 02 TZ: Finish W3.1 Test Contract and Traceability

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: main
Push/deploy: do not push/deploy before architect review

## Goal

Close the remaining W3.1 Rework 01 gaps from `05_rework_01_review.md`.

This is a narrow test/report rework. Do not change scoring v2. Do not wire TodayService to sidecar activation layer. Do not push or deploy.

## Required Fixes

### 1. Strengthen Basil lot regression test

In `apps/solarsage/tests/test_activation_transits.py`, replace the weak assertion:

```python
common = lot_keys & expected_lots
assert len(common) >= 1
```

with a real all-seven assertion:

```python
missing = expected_lots - lot_keys
assert not missing, f"Missing expected Basil audit lots: {sorted(missing)}"
```

Keep the assertion that all `by_lot` refs point to valid activation ids.

Expected lot keys:

```text
FORTUNE
SPIRIT
EROS
MARRIAGE
NECESSITY
VICTORY
NEMESIS
```

### 2. Remove no-op uppercase evidence test block

In `apps/solarsage/tests/test_activation_transits.py`, remove or replace the block that does:

```python
if word not in ("ASC", "MC", "DSC", "IC"):
    pass
```

If you keep a generic uppercase evidence test, make it a real assertion. It must fail when a transit-to-natal planet evidence string contains uppercase planet display text such as `natal PLUTO`.

Keep the exact Basil regression:

```python
assert "Transit Moon opposition natal Pluto" in act.get("evidence", "")
```

### 3. Write Rework 02 report with actual commit SHA

Write:

```text
docs/work/2026-07-09_solarsage-v2-w3-1-transit-activations/07_rework_02_report.md
```

Include:

- changed files;
- exact lot test strengthening;
- no-op test block removal/replacement;
- exact verification results;
- actual Rework 02 commit SHA after commit;
- push status `NOT_ATTEMPTED`.

Do not edit `04_rework_01_report.md` just to rewrite history. The new report is the traceable correction.

## Required Verification

Run and report exact results:

```bash
cd apps/solarsage && venv/bin/python -m pytest tests/test_activation_transits.py tests/test_activation_layer_endpoint.py tests/test_activation_schema.py -q
```

```bash
python3 scripts/audit_sidecar_activation.py --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 --date 2026-07-08 --out artifacts/audit/2026-07-08/17_sidecar_activation_layer.json
git diff --exit-code -- artifacts/audit/2026-07-08/17_sidecar_activation_layer.json
```

```bash
for i in 1 2 3; do
  PYTHONHASHSEED=random python3 scripts/audit_sidecar_activation.py --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 --date 2026-07-08 --out /tmp/sidecar_activation_$i.json
  sha256sum /tmp/sidecar_activation_$i.json
done
cmp -s /tmp/sidecar_activation_1.json /tmp/sidecar_activation_2.json
cmp -s /tmp/sidecar_activation_1.json /tmp/sidecar_activation_3.json
```

```bash
rg -n 'Transit Moon opposition natal Pluto|\"phase\": \"separating\"|\"applying\": false' artifacts/audit/2026-07-08/17_sidecar_activation_layer.json
rg -n 'natal PLUTO|annual_profection|firdar_major|solar_return|secondary_progression|eclipse_window' artifacts/audit/2026-07-08/17_sidecar_activation_layer.json || true
rg -n 'sidecar_activation_layer=None' apps/api/app/services/today_service.py
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
git status --short --branch
```

## Callback

After committing and writing the report, call:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W3.1 Rework 02 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w3-1-transit-activations/07_rework_02_report.md. Review: docs/work/2026-07-09_solarsage-v2-w3-1-transit-activations/05_rework_01_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w3-1-transit-activations/06_rework_02_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```

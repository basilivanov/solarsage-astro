# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_DEPLOY_WORKFLOW_CONTRACTS — deploy workflow wiring.
# ROLE: Static contract proofs for .github/workflows/deploy-production.yml:
#       the artifact-acceptance migration step must run from apps/api (where
#       alembic.ini lives), never from the repo root; the ephemeris extraction
#       step must stream the read-only baked bundle via tar (never `docker cp`)
#       while keeping the manifest/health identity checks and the image-side
#       immutability invariant intact.
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-DEPLOY-WORKFLOW-CONTRACTS
# purpose: Fail closed if the artifact-acceptance migration command loses
#   its apps/api working directory (repo-root alembic exits 255 with a
#   missing script_location), or if the ephemeris bundle extraction regresses
#   to `docker cp` (client-side extraction applies the deliberately read-only
#   0555 dir modes eagerly and fails with EACCES — run 29943208636), or if the
#   manifest/health identity checks or the image-side read-only bake are
#   weakened to "fix" that failure.
# owns:
#   - apps/api/tests/test_deploy_workflow_contracts.py
# inputs: the workflow YAML and the sidecar Dockerfile (read-only).
# outputs: assertions on the migration step wiring, the ephemeris extraction
#   transport, and the bundle immutability invariant.
# dependencies: yaml, pathlib.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - The acceptance migration step declares working-directory: apps/api.
#   - Its run command invokes the venv alembic (no repo-root invocation).
#   - The ephemeris extraction step streams `tar` from the container, never
#     `docker cp`, and keeps AUDIT_EPHEMERIS_PATH=/tmp/audit-ephe/ephe plus the
#     manifest artifact_id/sha256-vs-health assertions.
#   - The sidecar Dockerfile keeps the bundle root-owned 0555/0444.
#   - Pre-convergence acceptance steps (audit-day-freeze, V2 API/UI proofs)
#     stay retired with an explicit TODO(convergence-acceptance) marker until
#     the convergence acceptance realignment package lands.
# failure_policy: assertion failure.
# END_MODULE_CONTRACT: M-TESTS-DEPLOY-WORKFLOW-CONTRACTS

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy-production.yml"


def _acceptance_migration_step() -> dict:
    jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
    steps = jobs["artifact-acceptance"]["steps"]
    for step in steps:
        if isinstance(step, dict) and step.get("name") == "Run migrations on the ephemeral acceptance DB":
            return step
    raise AssertionError("acceptance migration step not found in deploy-production.yml")


def test_acceptance_migration_runs_from_apps_api() -> None:
    step = _acceptance_migration_step()
    # The command must run from the app root where alembic.ini lives —
    # a repo-root invocation can never find the configuration.
    assert step.get("working-directory") == "apps/api"
    run = step["run"]
    assert "alembic upgrade head" in run
    assert "apps/api/.venv/bin/alembic" not in run  # no repo-root relative invocation
    assert ".venv/bin/alembic" in run


# START_BLOCK: EPHEMERIS_EXTRACTION_CONTRACT
def _ephemeris_extraction_step() -> dict:
    jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
    steps = jobs["artifact-acceptance"]["steps"]
    for step in steps:
        if isinstance(step, dict) and step.get("name") == (
            "Extract the baked ephemeris bundle for the astronomy oracle"
        ):
            return step
    raise AssertionError("ephemeris extraction step not found in deploy-production.yml")


def test_ephemeris_extraction_uses_tar_stream_not_docker_cp() -> None:
    # START_FUNCTION_CONTRACT: F-M-TESTS-DEPLOY-WORKFLOW-CONTRACTS.test_ephemeris_extraction_uses_tar_stream_not_docker_cp
    # purpose: Prove the extraction step cannot regress to the `docker cp`
    #   transport that failed closed in run 29943208636 (client-side
    #   extraction applies the baked 0555 dir modes eagerly -> EACCES), and
    #   that the manifest/health identity checks are unchanged.
    # inputs: .github/workflows/deploy-production.yml (read-only).
    # returns: None; raises AssertionError on any violation.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure on docker cp usage, missing tar pipe,
    #   changed AUDIT_EPHEMERIS_PATH, or weakened identity checks.
    # END_FUNCTION_CONTRACT: F-M-TESTS-DEPLOY-WORKFLOW-CONTRACTS.test_ephemeris_extraction_uses_tar_stream_not_docker_cp
    run = _ephemeris_extraction_step()["run"]
    # Forbidden transport: docker cp extracts client-side as the unprivileged
    # runner user and cannot create files inside the fresh read-only dirs.
    # Check executable lines only — the run block documents the incident in
    # comments, which legitimately mention the failed command.
    commands = "\n".join(
        ln for ln in run.splitlines() if not ln.lstrip().startswith("#")
    )
    assert "docker cp" not in commands
    # Required transport: tar streamed out of the container; GNU tar defers
    # directory-mode application until extraction ends.
    assert "docker exec acceptance-sidecar tar -C /opt/solarsage-ephemeris/bundle -cf -" in run
    assert "tar -C /tmp/audit-ephe -xf -" in run
    # Unchanged downstream contract: env path + identity checks vs health.
    assert "AUDIT_EPHEMERIS_PATH=/tmp/audit-ephe/ephe" in run
    assert "/tmp/audit-ephe/manifest.json" in run
    assert 'manifest["artifact_id"] == health["ephemeris_artifact_id"]' in run
    assert "digest == health[\"ephemeris_manifest_sha256\"]" in run


def test_sidecar_image_keeps_readonly_ephemeris_bake() -> None:
    # START_FUNCTION_CONTRACT: F-M-TESTS-DEPLOY-WORKFLOW-CONTRACTS.test_sidecar_image_keeps_readonly_ephemeris_bake
    # purpose: Prove the image-side immutability invariant that motivates the
    #   tar-stream transport is never weakened as a "fix" for the extraction
    #   failure: bundle stays root-owned with dirs 0555 and files 0444.
    # inputs: apps/solarsage/Dockerfile (read-only).
    # returns: None; raises AssertionError on any violation.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure if the read-only bake is removed.
    # END_FUNCTION_CONTRACT: F-M-TESTS-DEPLOY-WORKFLOW-CONTRACTS.test_sidecar_image_keeps_readonly_ephemeris_bake
    dockerfile = (REPO_ROOT / "apps" / "solarsage" / "Dockerfile").read_text(encoding="utf-8")
    assert "chown -R root:root /opt/solarsage-ephemeris/bundle" in dockerfile
    assert "find /opt/solarsage-ephemeris/bundle -type d -exec chmod 0555" in dockerfile
    assert "find /opt/solarsage-ephemeris/bundle -type f -exec chmod 0444" in dockerfile
# END_BLOCK: EPHEMERIS_EXTRACTION_CONTRACT


# START_BLOCK: RETIRED_ACCEPTANCE_STEPS
def test_pre_convergence_acceptance_steps_retired() -> None:
    # START_FUNCTION_CONTRACT: F-M-TESTS-DEPLOY-WORKFLOW-CONTRACTS.test_pre_convergence_acceptance_steps_retired
    # purpose: Fail closed against silently reintroducing the retired
    #   pre-convergence acceptance steps (audit-day-freeze runs, real V2 API
    #   proof, same-payload V2 UI proof) without the convergence realignment
    #   package. They validated the today.v2.2 payload retired by the
    #   spheres/facets rework and could not run green (no live API in the job).
    #   Retirement marker: TODO(convergence-acceptance) in the workflow.
    # inputs: .github/workflows/deploy-production.yml (read-only).
    # returns: None; raises AssertionError on any violation.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure on retired step names or missing marker.
    # END_FUNCTION_CONTRACT: F-M-TESTS-DEPLOY-WORKFLOW-CONTRACTS.test_pre_convergence_acceptance_steps_retired
    text = WORKFLOW.read_text(encoding="utf-8")
    jobs = yaml.safe_load(text)["jobs"]
    steps = jobs["artifact-acceptance"]["steps"]
    names = [str(s.get("name", "")) for s in steps if isinstance(s, dict)]
    retired = ("Audit day freeze", "Real V2 API proof", "Same-payload V2 UI proof")
    for name in names:
        assert not name.startswith(retired), name
    assert "TODO(convergence-acceptance)" in text
    assert any(name == "Golden snapshots gate" for name in names), names
# END_BLOCK: RETIRED_ACCEPTANCE_STEPS

# ############################################################################
# AI_HEADER: TEST_EPHEMERIS_RUNTIME — pinned artifact + engine flag proof.
# ROLE: Proves manifest/hash verification, fail-closed production behavior,
#       SWIEPH-vs-Moshier classification, and health v2 identity fields.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-EPHEMERIS-RUNTIME
# purpose: Verify the ephemeris runtime: valid staged artifact + SWIEPH flags
#   passes with exact identity; missing/tampered artifact fails; MOSEPH
#   returned flags are fatal in production; explicit moshier mode works only
#   outside production; health exposes the v2 identity fields.
# owns:
#   - apps/solarsage/tests/test_ephemeris_runtime.py
# inputs: staged tmp artifact trees; monkeypatched swe.calc_ut.
# outputs: pytest assertions.
# dependencies: solarsage.core.ephemeris_runtime.
# side_effects: tmp filesystem fixtures only.
# emitted_logs: none.
# invariants:
#   - no real ephemeris files are used; engine flags are always mocked.
# failure_policy: assertion failure on contract violation.
# END_MODULE_CONTRACT: M-TEST-EPHEMERIS-RUNTIME

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from solarsage.core import ephemeris_runtime as rt


@pytest.fixture(autouse=True)
def _reset_identity():
    rt._reset_identity_for_tests()
    yield
    rt._reset_identity_for_tests()


def _stage_artifact(root: Path, artifact_id: str = "se-test-2026a") -> Path:
    ephe = root / "ephe"
    ephe.mkdir(parents=True)
    data = b"fake-ephemeris-bytes-for-tests"
    (ephe / "sepl_18.se1").write_bytes(data)
    (ephe / "semo_18.se1").write_bytes(data)
    files = []
    for name in ("sepl_18.se1", "semo_18.se1"):
        files.append({
            "path": f"ephe/{name}",
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    manifest = {
        "schema_version": "solarsage-ephemeris/v1",
        "artifact_id": artifact_id,
        "created_at_utc": "2026-07-19T00:00:00Z",
        "supported_date_range": "1800-2399",
        "swiss_data_version": "2.10.03",
        "files": files,
    }
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode()
    (root / "manifest.json").write_bytes(manifest_bytes)
    (root / "manifest.sha256").write_text(hashlib.sha256(manifest_bytes).hexdigest())
    return root


def _mock_swe(monkeypatch, retflag: int):
    monkeypatch.setattr(rt.swe, "calc_ut", lambda jd, body, flags: ((1.0, 0.5, 0.0, 0.1, 0.1, 0.1), retflag))
    monkeypatch.setattr(rt.swe, "set_ephe_path", lambda path: None)


def _set_env(monkeypatch, root: Path, app_env: str = "production", allow_moshier: bool = False):
    monkeypatch.setattr(rt.settings, "ephemeris_root", str(root))
    monkeypatch.setattr(rt.settings, "app_env", app_env)
    monkeypatch.setattr(rt.settings, "ephemeris_allow_moshier", allow_moshier)


def test_valid_artifact_swieph_identity(tmp_path, monkeypatch):
    root = _stage_artifact(tmp_path / "artifact")
    _set_env(monkeypatch, root)
    _mock_swe(monkeypatch, rt.swe.FLG_SWIEPH | rt.swe.FLG_SPEED)

    identity = rt.verify_and_configure()
    assert identity.engine == "swieph"
    assert identity.fallback is False
    assert identity.artifact_id == "se-test-2026a"
    assert len(identity.manifest_sha256) == 64
    assert identity.swiss_data_version == "2.10.03"
    assert identity.ephemeris_path.endswith("ephe")


def test_missing_root_fails_closed(tmp_path, monkeypatch):
    _set_env(monkeypatch, tmp_path / "does-not-exist")
    _mock_swe(monkeypatch, rt.swe.FLG_SWIEPH | rt.swe.FLG_SPEED)
    with pytest.raises(rt.EphemerisError, match="not a directory|missing"):
        rt.verify_and_configure()


def test_tampered_inventory_file_fails(tmp_path, monkeypatch):
    root = _stage_artifact(tmp_path / "artifact")
    (root / "ephe" / "sepl_18.se1").write_bytes(b"tampered")
    _set_env(monkeypatch, root)
    _mock_swe(monkeypatch, rt.swe.FLG_SWIEPH | rt.swe.FLG_SPEED)
    with pytest.raises(rt.EphemerisError, match="size mismatch|sha256 mismatch"):
        rt.verify_and_configure()


def test_missing_manifest_hash_fails(tmp_path, monkeypatch):
    root = _stage_artifact(tmp_path / "artifact")
    (root / "manifest.sha256").unlink()
    _set_env(monkeypatch, root)
    _mock_swe(monkeypatch, rt.swe.FLG_SWIEPH | rt.swe.FLG_SPEED)
    with pytest.raises(rt.EphemerisError, match="not a regular file|missing"):
        rt.verify_and_configure()


def test_moseph_flag_fatal_in_production(tmp_path, monkeypatch):
    root = _stage_artifact(tmp_path / "artifact")
    _set_env(monkeypatch, root, app_env="production", allow_moshier=False)
    _mock_swe(monkeypatch, rt.swe.FLG_MOSEPH | rt.swe.FLG_SPEED)
    with pytest.raises(rt.EphemerisError, match="FLG_SWIEPH"):
        rt.verify_and_configure()


def test_moshier_allowed_only_outside_production(tmp_path, monkeypatch):
    _set_env(monkeypatch, tmp_path / "missing", app_env="development", allow_moshier=True)
    monkeypatch.setattr(rt.swe, "set_ephe_path", lambda path: None)
    identity = rt.verify_and_configure()
    assert identity.engine == "moshier"
    assert identity.fallback is True
    assert identity.artifact_id == "moshier-only"


def test_moshier_allow_flag_ignored_in_production(tmp_path, monkeypatch):
    _set_env(monkeypatch, tmp_path / "missing", app_env="production", allow_moshier=True)
    with pytest.raises(rt.EphemerisError):
        rt.verify_and_configure()


def test_symlink_inventory_file_fails(tmp_path, monkeypatch):
    root = _stage_artifact(tmp_path / "artifact")
    target = root / "ephe" / "sepl_18.se1"
    link = root / "ephe" / "semo_18.se1"
    link.unlink()
    link.symlink_to(target)
    _set_env(monkeypatch, root)
    _mock_swe(monkeypatch, rt.swe.FLG_SWIEPH | rt.swe.FLG_SPEED)
    with pytest.raises(rt.EphemerisError, match="must not be a symlink"):
        rt.verify_and_configure()


def test_check_health_v2(tmp_path, monkeypatch):
    from solarsage.core.health import check_health

    root = _stage_artifact(tmp_path / "artifact")
    _set_env(monkeypatch, root)
    _mock_swe(monkeypatch, rt.swe.FLG_SWIEPH | rt.swe.FLG_SPEED)
    ok, error, identity = check_health()
    assert ok and error == "" and identity is not None and identity.engine == "swieph"

    rt._reset_identity_for_tests()
    _set_env(monkeypatch, tmp_path / "missing")
    ok, error, identity = check_health()
    assert not ok and error and identity is None


def test_extra_unlisted_file_fails(tmp_path, monkeypatch):
    root = _stage_artifact(tmp_path / "artifact")
    (root / "ephe" / "extra.se1").write_bytes(b"extra")
    _set_env(monkeypatch, root)
    _mock_swe(monkeypatch, rt.swe.FLG_SWIEPH | rt.swe.FLG_SPEED)
    with pytest.raises(rt.EphemerisError, match="extra unlisted file"):
        rt.verify_and_configure()


def test_entry_missing_sha256_fails(tmp_path, monkeypatch):
    root = _stage_artifact(tmp_path / "artifact")
    manifest = json.loads((root / "manifest.json").read_text())
    manifest["files"][0] = {"path": "ephe/sepl_18.se1", "size": len(b"fake-ephemeris-bytes-for-tests")}
    mb = json.dumps(manifest, sort_keys=True).encode()
    (root / "manifest.json").write_bytes(mb)
    (root / "manifest.sha256").write_text(hashlib.sha256(mb).hexdigest())
    _set_env(monkeypatch, root)
    _mock_swe(monkeypatch, rt.swe.FLG_SWIEPH | rt.swe.FLG_SPEED)
    with pytest.raises(rt.EphemerisError, match="64 lowercase hex"):
        rt.verify_and_configure()


def test_entry_missing_size_fails(tmp_path, monkeypatch):
    root = _stage_artifact(tmp_path / "artifact")
    manifest = json.loads((root / "manifest.json").read_text())
    manifest["files"][0].pop("size")
    mb = json.dumps(manifest, sort_keys=True).encode()
    (root / "manifest.json").write_bytes(mb)
    (root / "manifest.sha256").write_text(hashlib.sha256(mb).hexdigest())
    _set_env(monkeypatch, root)
    _mock_swe(monkeypatch, rt.swe.FLG_SWIEPH | rt.swe.FLG_SPEED)
    with pytest.raises(rt.EphemerisError, match="non-negative int"):
        rt.verify_and_configure()


def test_empty_manifest_hash_file_fails(tmp_path, monkeypatch):
    root = _stage_artifact(tmp_path / "artifact")
    (root / "manifest.sha256").write_text("")
    _set_env(monkeypatch, root)
    _mock_swe(monkeypatch, rt.swe.FLG_SWIEPH | rt.swe.FLG_SPEED)
    with pytest.raises(rt.EphemerisError, match="empty"):
        rt.verify_and_configure()


def test_ephe_dir_symlink_fails(tmp_path, monkeypatch):
    root = _stage_artifact(tmp_path / "artifact")
    real = tmp_path / "elsewhere"
    real.mkdir()
    (root / "ephe").rename(real / "ephe")
    (root / "ephe").symlink_to(real / "ephe")
    _set_env(monkeypatch, root)
    _mock_swe(monkeypatch, rt.swe.FLG_SWIEPH | rt.swe.FLG_SPEED)
    with pytest.raises(rt.EphemerisError, match="ephe/"):
        rt.verify_and_configure()


def test_boundary_probes_cover_declared_range(tmp_path, monkeypatch):
    root = _stage_artifact(tmp_path / "artifact")
    _set_env(monkeypatch, root)
    calls = []
    monkeypatch.setattr(rt.swe, "set_ephe_path", lambda path: None)
    monkeypatch.setattr(rt.swe, "calc_ut", lambda jd, body, flags: (calls.append((jd, body)) or ((1.0,) * 6, rt.swe.FLG_SWIEPH | rt.swe.FLG_SPEED)))
    rt.verify_and_configure()
    jds = [jd for jd, _ in calls]
    assert rt.swe.julday(1800, 1, 1, 12.0) in jds
    assert rt.swe.julday(2399, 12, 31, 12.0) in jds
    assert len(calls) == 4  # Sun, Moon, range-start, range-end


def test_calc_ut_checked_requires_swieph_in_production(tmp_path, monkeypatch):
    root = _stage_artifact(tmp_path / "artifact")
    _set_env(monkeypatch, root)
    _mock_swe(monkeypatch, rt.swe.FLG_SWIEPH | rt.swe.FLG_SPEED)
    rt.verify_and_configure()
    # Degrade the engine AFTER verification: fallback must be caught per call.
    monkeypatch.setattr(rt.swe, "calc_ut", lambda jd, body, flags: ((1.0,) * 6, rt.swe.FLG_MOSEPH))
    with pytest.raises(rt.EphemerisError, match="fallback during calculation"):
        rt.calc_ut_checked(1.0, rt.swe.SUN, rt.swe.FLG_SWIEPH)


def test_calc_ut_checked_passes_swieph(tmp_path, monkeypatch):
    root = _stage_artifact(tmp_path / "artifact")
    _set_env(monkeypatch, root)
    _mock_swe(monkeypatch, rt.swe.FLG_SWIEPH | rt.swe.FLG_SPEED)
    result = rt.calc_ut_checked(1.0, rt.swe.MOON, rt.swe.FLG_SWIEPH | rt.swe.FLG_SPEED)
    assert result[1] & rt.swe.FLG_SWIEPH


def test_calc_ut_checked_moshier_mode_marked(tmp_path, monkeypatch):
    _set_env(monkeypatch, tmp_path / "missing", app_env="development", allow_moshier=True)
    monkeypatch.setattr(rt.swe, "set_ephe_path", lambda path: None)
    monkeypatch.setattr(rt.swe, "calc_ut", lambda jd, body, flags: ((1.0,) * 6, rt.swe.FLG_MOSEPH))
    result = rt.calc_ut_checked(1.0, rt.swe.SUN, rt.swe.FLG_SWIEPH)
    assert rt.get_identity().engine == "moshier"
    assert rt.get_identity().fallback is True
    assert result[1] & rt.swe.FLG_SWIEPH == 0  # passes through, marked


def test_cross_ut_checked_requires_verified_configuration(tmp_path, monkeypatch):
    _set_env(monkeypatch, tmp_path / "missing", app_env="production")
    with pytest.raises(rt.EphemerisError):
        rt.cross_ut_checked(lambda *a: 2461244.0, 120.0, 1.0, 2)
    root = _stage_artifact(tmp_path / "artifact")
    _set_env(monkeypatch, root)
    _mock_swe(monkeypatch, rt.swe.FLG_SWIEPH | rt.swe.FLG_SPEED)
    assert rt.cross_ut_checked(lambda *a: 2461244.0, 120.0, 1.0, 2) == 2461244.0

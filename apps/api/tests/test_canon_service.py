"""Tests for canon service: loading, validation, versioning."""

import pytest
from pathlib import Path

from app.services.canon_service import (
    validate_canon_bundle,
    load_canon_bundle,
    get_canon_versions,
    CanonValidationError,
    CANON_DIR,
)


VALID_HORIZON_CANON = (CANON_DIR / "horizon_selection.v1.yml").read_text(encoding="utf-8")


def test_validate_canon_bundle_success():
    """All five canon files load and validate successfully."""
    bundle = validate_canon_bundle()
    assert "spheres.v1.yml" in bundle
    assert "dignities.v1.yml" in bundle
    assert "aspect_rules.v1.yml" in bundle
    assert "activation_rules.v1.yml" in bundle
    assert "scoring_v2.v1.yml" in bundle
    assert bundle["spheres.v1.yml"]["schema_version"] == "spheres.v1"
    assert bundle["scoring_v2.v1.yml"]["schema_version"] == "scoring_v2.v1"


def test_get_canon_versions():
    """Canon versions dict has expected keys."""
    versions = get_canon_versions()
    assert "spheres" in versions
    assert "aspect_rules" in versions
    assert "activation_rules" in versions
    assert "scoring_v2" in versions


def test_load_canon_bundle_from_repo():
    """load_canon_bundle works with the real repo canon dir."""
    bundle = load_canon_bundle()
    assert "spheres.v1.yml" in bundle
    assert "aspect_rules.v1.yml" in bundle


def test_missing_canon_file_raises(tmp_path: Path):
    """validate_canon_bundle raises on missing file."""
    with pytest.raises(CanonValidationError, match="Missing canon file"):
        validate_canon_bundle(tmp_path)


def test_invalid_canon_data_raises(tmp_path: Path):
    """validate_canon_bundle raises on invalid YAML."""
    d = tmp_path / "missing_schema"
    d.mkdir()
    (d / "spheres.v1.yml").write_text('schema_version: spheres.v1\nspheres: {}\n', encoding="utf-8")
    (d / "dignities.v1.yml").write_text('schema_version: dignities.v1\n', encoding="utf-8")
    (d / "aspect_rules.v1.yml").write_text('schema_version: aspect_rules.v1\naspect_weights: {}\naspect_threshold: {}\n', encoding="utf-8")
    (d / "activation_rules.v1.yml").write_text('schema_version: activation_rules.v1\ntechnique_families: {}\n', encoding="utf-8")
    (d / "scoring_v2.v1.yml").write_text('schema_version: scoring_v2.v1\n', encoding="utf-8")
    (d / "horizon_selection.v1.yml").write_text(VALID_HORIZON_CANON, encoding="utf-8")
    with pytest.raises(CanonValidationError, match="is empty"):
        validate_canon_bundle(d)


def test_missing_required_key_raises(tmp_path: Path):
    """Missing required key in canon file raises."""
    d = tmp_path / "missing_key"
    d.mkdir()
    (d / "spheres.v1.yml").write_text('schema_version: spheres.v1\nspheres: {}\n', encoding="utf-8")
    (d / "dignities.v1.yml").write_text('schema_version: dignities.v1\n', encoding="utf-8")
    # aspect_rules missing required 'aspect_weights'
    (d / "aspect_rules.v1.yml").write_text('schema_version: aspect_rules.v1\nsome_other_key: true\n', encoding="utf-8")
    (d / "activation_rules.v1.yml").write_text('schema_version: activation_rules.v1\ntechnique_families:\n  transit:\n    members: [transit_to_natal]\n    independence_weight: 1.0\n', encoding="utf-8")
    (d / "scoring_v2.v1.yml").write_text('schema_version: scoring_v2.v1\n', encoding="utf-8")
    (d / "horizon_selection.v1.yml").write_text(VALID_HORIZON_CANON, encoding="utf-8")
    with pytest.raises(CanonValidationError, match="missing required key"):
        validate_canon_bundle(d)

# ############################################################################
# AI_HEADER: TEST_TODAY-CONVERGENCE-TITLES — deterministic drilldown title coverage.
# ROLE: Verifies localization, prefix stripping, and honest null behavior for
#       snapshot factor-unit titles.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-TITLES
# purpose: Exercise the public title projection used by Today drilldown events.
# owns:
#   - apps/api/tests/test_today_convergence_titles.py
# inputs: normalized and raw-prefixed factor-unit mappings.
# outputs: localized title or null assertions.
# dependencies: app.services.today_convergence_titles.
# side_effects: none.
# emitted_logs: none.
# invariants: no technical prefixes or generic placeholders reach the title.
# failure_policy: pytest failure on leaked or fabricated driver labels.
# END_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-TITLES

from __future__ import annotations

from app.services.today_convergence_titles import build_today_convergence_event_title


def test_aspect_title_localizes_and_strips_raw_prefixes() -> None:
    title = build_today_convergence_event_title(
        {
            "source_key": "Transit_MARS",
            "target_key": "Natal_NEPTUNE",
            "target_type": "natal_planet",
            "aspect_type": "opposition",
        }
    )

    assert title == "Марс напротив твоего Нептуна"
    assert "Transit_" not in title
    assert "Natal_" not in title


def test_generic_activation_has_no_fabricated_title() -> None:
    assert build_today_convergence_event_title(
        {
            "source_key": "activation-evt-v1",
            "target_key": "",
            "target_type": "",
            "aspect_type": None,
        }
    ) is None

# ############################################################################
# AI_HEADER: TEST_NARRATIVE_SANITIZER — machine-token leak guard coverage.
# ROLE: Verifies that public narrative text fails closed on known provider
#       signal-name artifacts.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-NARRATIVE-SANITIZER
# purpose: Exercise the deterministic narrative sanitizer independently from
#   either provider orchestration path.
# owns:
#   - apps/api/tests/test_narrative_sanitizer.py
# inputs: safe and provider-leaked text samples.
# outputs: sanitizer boolean and safe-text assertions.
# dependencies: app.services.narrative_sanitizer, pytest.
# side_effects: none.
# emitted_logs: none.
# invariants: forbidden text is never returned as publishable text.
# failure_policy: pytest failure on an accepted machine token.
# END_MODULE_CONTRACT: M-TEST-NARRATIVE-SANITIZER

from __future__ import annotations

import pytest

from app.services.narrative_sanitizer import (
    has_forbidden_narrative_tokens,
    sanitize_narrative_text,
)


@pytest.mark.parametrize(
    "text",
    [
        "Transit_Mars создаёт напряжение.",
        "Transit_ нельзя показывать.",
        "Natal_Moon поддерживает привычный ритм.",
        "Сигнал Planet нельзя показывать пользователю.",
        "Связка M, Mars не является человеческим описанием.",
        "Natal, Planet, Moon — служебный список.",
    ],
)
def test_machine_driver_artifacts_are_rejected(text: str) -> None:
    assert has_forbidden_narrative_tokens(text) is True
    assert sanitize_narrative_text(text) is None


def test_safe_russian_text_is_trimmed_and_kept() -> None:
    assert sanitize_narrative_text("  Выбери один понятный шаг.  ") == "Выбери один понятный шаг."

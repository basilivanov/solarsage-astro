import pytest
from app.schemas.today import ConcreteAdviceEvidence, ConcreteAdviceRow
from app.services.today_interpretation_service import validate_row_text

def test_concrete_advice_consistency_avoid():
    row = ConcreteAdviceRow(
        key="relationships",
        label="Отношения",
        icon_name="sparkle",
        rank=4,
        verdict="avoid",
        confidence="high",
        text="",
        evidence=[
            ConcreteAdviceEvidence(
                kind="aspect",
                title="Transit Moon opposition natal Pluto",
                planet="Transit_Moon",
                target_planet="Pluto",
                aspect_type="opposition",
            )
        ],
    )

    # 1. Active advice under avoid should fail
    assert validate_row_text(row, "Общайся с близкими для улучшения отношений") is False
    assert validate_row_text(row, "Начни новые переговоры сегодня") is False

    # 2. Negative/cautionary advice under avoid should pass
    assert validate_row_text(row, "Избегай активного общения сегодня") is True
    assert validate_row_text(row, "Не начинай новых разговоров") is True

    # 3. Spec allowed mitigation example must pass
    spec_example = "Если нужно общаться с близкими — выбирай короткий, спокойный формат и не разбирай острые темы."
    assert validate_row_text(row, spec_example) is True

import pytest
from app.services.llm_claim_validator import LLMClaimValidator

def test_llm_claim_validator_relationships_avoid():
    validator = LLMClaimValidator()
    # Safe text
    text = "Проведи время наедине с собой, отдохни."
    assert validator.validate_concrete_advice_text(
        row_key="relationships", verdict="avoid", text=text, evidence=[]
    ) == text

    # Unsafe text (relationship improvement / conflict-opening advice)
    unsafe_text = "Сегодня отличный день, чтобы выяснять отношения с партнером и поговорить по душам."
    res = validator.validate_concrete_advice_text(
        row_key="relationships", verdict="avoid", text=unsafe_text, evidence=[]
    )
    assert "Если контакт неизбежен" in res

def test_llm_claim_validator_money_avoid():
    validator = LLMClaimValidator()
    text = "Сегодня не стоит тратить деньги на мелочи."
    res = validator.validate_concrete_advice_text(
        row_key="money", verdict="avoid", text=text, evidence=[]
    )
    assert "Для финансовых решений день не подходит" in res

def test_llm_claim_validator_sport_avoid():
    validator = LLMClaimValidator()
    text = "Отличный день для интенсивного спорта и нагрузок."
    res = validator.validate_concrete_advice_text(
        row_key="sport", verdict="avoid", text=text, evidence=[]
    )
    assert "Избегай чрезмерных нагрузок" in res

def test_llm_claim_validator_communication_avoid():
    validator = LLMClaimValidator()
    text = "Проведи важные переговоры и договаривайся с коллегами."
    res = validator.validate_concrete_advice_text(
        row_key="communication", verdict="avoid", text=text, evidence=[]
    )
    assert "Отложи важные переговоры" in res

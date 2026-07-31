# 08_TZ: Синастрия — Tests

## 1. Packet title
Синастрия / Совместимость — Tests (срез 8 из N)

## 2. Phase / Wave
W-SYNASTRY-MVP, slice 8: Tests

## 3. Modules
- apps/api/tests/test_synastry_*.py
- __tests__/synastry/*.test.tsx

## 4. Goal
Дописать тесты: unit (pytest), API security, PostgreSQL integration, billing, unit (vitest), mock e2e.

## 5. Exact write scope
- `apps/api/tests/test_synastry_scoring.py` — расширить
- `apps/api/tests/test_synastry_llm.py` — расширить
- `apps/api/tests/test_synastry_api.py` — расширить
- `apps/api/tests/test_synastry_service.py` — расширить
- `apps/api/tests/test_synastry_integration.py` — новый
- `__tests__/synastry/synastry-screen.test.tsx` — новый
- `__tests__/synastry/synastry-add-sheet.test.tsx` — новый
- `__tests__/synastry/synastry-detail-screen.test.tsx` — новый
- `e2e/mock-visual/synastry.spec.ts` — новый

## 6. Frozen / Out of scope
- Не трогать production code
- Не трогать existing tests

## 7. Must-preserve invariants
- Unit tests: all pure fixtures/boundaries from 03_SCORING_AND_TONE_CONTRACT.md
- API security: чужой partner_id → 404 на всех endpoints
- Integration: concurrent PartnerCreate, spend/refund, process death
- Billing: purchase/start, attribution, refund
- Frontend: list/detail/status states, CityPicker, unknown-time restore, drilldown, paywall, delete confirmation
- Mock e2e: structural contract on stable payload

## 8. Verification commands
```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_synastry_*.py -q
npx vitest run __tests__/synastry
```

## 9. Expected evidence
- `git diff --name-only` — test files
- `pytest tests/test_synastry_*.py -q` — успешно
- `vitest run __tests__/synastry` — успешно

## 10. Escalation rule
Нужен production code change → стоп, доложить, новый packet.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.

# 09_TZ: Синастрия — Sidecar endpoint

## 1. Packet title
Синастрия / Совместимость — Sidecar endpoint (срез 9 из N)

## 2. Phase / Wave
W-SYNASTRY-MVP, slice 9: Sidecar endpoint

## 3. Modules
- M-SIDECAR-API-SYNASTRY (apps/solarsage/solarsage/api/synastry.py)
- M-SIDECAR-SERVICE-SYNASTRY (apps/solarsage/solarsage/services/synastry.py)
- M-SIDECAR-SCHEMAS-SYNASTRY (apps/solarsage/solarsage/schemas/synastry.py)

## 4. Goal
Создать sidecar endpoint `/v1/synastry` для расчёта партнёрской карты и межкарточных аспектов. По образцу natal.py.

## 5. Exact write scope
- `apps/solarsage/solarsage/api/synastry.py` — POST /v1/synastry endpoint
- `apps/solarsage/solarsage/services/synastry.py` — SynastryService
- `apps/solarsage/solarsage/schemas/synastry.py` — SynastryRequest, SynastryResponse

## 6. Frozen / Out of scope
- Не трогать existing sidecar endpoints
- Не трогать API backend (уже готов)
- Не трогать frontend (уже готов)

## 7. Must-preserve invariants
- Additive only: natal/transits schemas и endpoints не трогаются
- Input: owner chart (already calculated) + partner birth data
- Output: partner planets, available partner houses/ASC, cross aspects, precision flags
- Unknown time → partner houses/ASC unavailable, Moon approximate
- Sidecar не вычисляет tone, score, narrative

## 8. Verification commands
```bash
cd apps/solarsage && source .venv/bin/activate 2>/dev/null || true
python -c "from solarsage.api.synastry import router; print('sidecar synastry OK')"
python -m pytest tests/test_synastry.py -q 2>/dev/null || echo "tests not yet written"
```

## 9. Expected evidence
- `git diff --name-only` — только sidecar files
- Импорт router — успешно

## 10. Escalation rule
Нужен API backend change → стоп, доложить, новый packet.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.

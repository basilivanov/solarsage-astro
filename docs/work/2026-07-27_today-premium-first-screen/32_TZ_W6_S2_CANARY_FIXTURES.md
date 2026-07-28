# 32 TZ W6-S2 — Sanitized Canary Fixtures (W4-CANARY) — test/tooling slice

1. **Packet title**: W6-S2-CANARY-SANITIZED-FIXTURES
2. **Phase / Wave**: W6-FOCUS-HARDENING, срез S2 (backend/test tooling).
   Normative source: `30_TZ_W4_CANARY_SANITIZED_FIXTURES.md` (далее «doc 30») —
   обязателен целиком. Зависит от W6-S1 (selector в main): oracle cases A/B
   проходят против реализованного §3 канона.
3. **Modules**: M-DAY-SERVICE.audit (scripts/audit_day_contract.py),
   M-CONTRACTS.tooling (scripts/contracts), test fixtures layer.
4. **Goal**: reusable sanitized canary слой (factor fixtures A–J + public
   fixtures + loader/oracle/permutation/privacy tests) и безопасный
   `--freeze-focus` exporter. Ни один fixture не содержит персональных данных.

## 5. Exact write scope

- `apps/api/tests/fixtures/today_focus/README.md` — НОВЫЙ: schema, privacy
  allowlist, regeneration policy (doc 30 §8).
- `apps/api/tests/fixtures/today_focus/factors/*.json` — НОВЫЕ cases A–J
  (top-level allowlist doc 30 §3.1).
- `apps/api/tests/fixtures/today_focus/public/*.json` — НОВЫЕ public focus
  fixtures (ready synthetic copy + failure states, doc 30 §3.2).
- `apps/api/tests/test_today_focus_fixture_canaries.py` — НОВЫЙ: loader,
  schema/allowlist/denylist validation, builder oracle, permutation,
  null-time, contentState, privacy scan, max-size guard (doc 30 §9).
- `scripts/audit_day_contract.py` — добавить `--freeze-focus PATH` (doc 30 §7)
  и честно переименовать в help существующий `--freeze` как full-payload
  regression (не sanitized).
- `scripts/contracts/normalize_today_focus_fixture.py` — НОВЫЙ deterministic
  formatter/`--check` для fixtures (doc 30 §8).
- `Makefile` — `audit-focus-live`/`audit-focus-freeze` с явными обязательными
  TG_ID/DATE, без default реального пользователя; существующий
  `audit-day-freeze` help-пометка «full payload, не для W4 canary».

## 6. Frozen / Out of scope

- НЕ менять selector/builder/title builder/today_service/frontend (doc 30 §8:
  «fixture выявляет расхождение, но не чинит production code»).
- НЕ копировать существующие full-day fixtures (`day_valence/frozen-*.json`)
  как основу.
- НЕ использовать live `--freeze` output как fixture; НЕ коммитить полный
  payload.
- Live LLM/network/Telegram/DB/sidecar в unit/CI — запрещены (doc 30 §9.10).
- Case J: `decisionRequired=true`, winner НЕ утверждается (blocked до решения
  владельца) — это diagnostic gate, не ranking change.

## 7. Must-preserve invariants

- Существующие тесты зелёные; `python3 scripts/grace_lint.py app` → PASS.
- Oracle cases A (28.07) и B (29.07) — expected events по doc 30 §4/§5
  (case A: 13:31 Moon-Pluto conv anchor, 18:19 Moon-Uranus, 19:52 Mars-Neptune;
  case B: вечерние 19:24 Moon-Sun / 19:40 Moon-Moon, firdar НЕ event).
- Privacy denylist (doc 30 §9.2) проверяется тестом рекурсивно на всех
  fixtures: tg/telegram/username/userId/UUID/birthday/coordinates/initData/
  cookie/token/profile/prompt/response.
- Каждый `expected.events[].sourceActivationIds` существует в input factors.

## Дизайн-заметки

- Cases A/B пишутся руками из нормативных таблиц doc 30 §4/§5 + W6-S1 inline
  canary data (уже в test_today_focus_builder.py) — переиспользовать как
  fixture JSON вместо inline (W6-S1 тесты могут ссылаться на fixture loader;
  допустимо оставить и inline, дублирование не критично, но предпочтителен
  один источник — ревьюер примет любой вариант с обоснованием).
- Exporter `--freeze-focus`: только allowlisted normalized factors + expected
  focus; нейтральный caseId; рекурсивное удаление user/profile/auth/provider
  полей; sorted keys; schema validation; refuse на неизвестном key; atomic
  write; non-zero при privacy failure. Auth — live preflight только, никогда не
  сохраняется (doc 30 §7).
- Max fixture size guard: предложить 64 KB на factor-case — полный payload
  туда физически не влезает.

## 8. Verification

```bash
cd apps/api && source .venv/bin/activate && \
python -m pytest tests/test_today_focus_fixture_canaries.py -q && \
python -m pytest tests/test_today_focus_builder.py tests/test_today_focus_contract.py -q && \
cd ../.. && python3 scripts/contracts/normalize_today_focus_fixture.py apps/api/tests/fixtures/today_focus --check
```

## 9. Expected evidence

Список case IDs (A–J), privacy scanner output (0 hits), oracle diff (пустой),
вывод verification, пример `--freeze-focus` на synthetic/test profile (не
реальный пользователь), git diff --stat.

## 10. Escalation

Нельзя построить кейс без нового sidecar поля/wire change/raw profile/ручного
угадывания IDs — стоп (doc 30 §11).

## 11. No-commit

Ничего не коммитить и не пушить — коммит делает ревьюер.

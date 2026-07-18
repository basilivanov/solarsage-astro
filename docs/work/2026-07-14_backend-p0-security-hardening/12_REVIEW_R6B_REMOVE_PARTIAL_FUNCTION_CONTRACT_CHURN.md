# Review R6B — убрать частичный function-contract churn и продолжить

Дата: 2026-07-14

Это последнее уточнение к R6/R6A; при конфликте этот файл имеет приоритет.

## 1. Текущее фактическое состояние

До полного interrupt кодер успел применить в `apps/api/tests/test_auth_endpoints.py`:

- нужные R6 imports/helper/regression tests;
- правдивый обновлённый module header/contract/map;
- пять ненужных `START_FUNCTION_CONTRACT` блоков в старых Telegram auth tests.

Следующий большой patch для остальных тестов был прерван и не применился.

## 2. Что оставить

Оставить без изменений:

- весь R6 executable test code;
- `_trusted_loopback_dev_auth_request()`;
- staging deny endpoint test;
- parametrized env tests;
- новые imports;
- уже применённый module header/contract/map в начале файла: он теперь правдиво описывает существенно изменённый test-модуль и сам по себе не создаёт опасного churn.

## 3. Что удалить

Удалить ровно пять comment-only блоков от `START_FUNCTION_CONTRACT` до соответствующего `END_FUNCTION_CONTRACT` внутри функций:

```text
test_login_happy_path
test_login_secure_flag_when_enabled
test_login_idempotent_user_upsert
test_login_400_on_invalid_hmac_no_db_write
test_login_401_on_expired_initdata
```

Не менять ни одной исполняемой строки этих тестов.

Не добавлять function contracts в какие-либо другие test functions.

Удалить блоки через точный `apply_patch`, а не глобальный regex, formatter или восстановление файла из HEAD.

После удаления проверить:

```bash
rg -n 'START_FUNCTION_CONTRACT|END_FUNCTION_CONTRACT' apps/api/tests/test_auth_endpoints.py
```

Ожидается пустой output. Наличие module contract/map допустимо и ожидаемо.

## 4. Gates

Продолжить R6 gates, но GRACE запускать только:

```bash
python3 scripts/grace_lint.py apps/api/app/api/auth.py
```

Test-файл проверять через Ruff, pytest и `git diff --check`, как сказано в R6A.

## 5. Stage scope

В R6 commit включить ровно:

```text
apps/api/app/api/auth.py
apps/api/tests/test_auth_endpoints.py
docs/work/2026-07-14_backend-p0-security-hardening/10_REVIEW_R6_STAGING_DEV_AUTH_LOCAL_BYPASS.md
docs/work/2026-07-14_backend-p0-security-hardening/11_REVIEW_R6A_NO_LEGACY_GRACE_RETROFIT.md
docs/work/2026-07-14_backend-p0-security-hardening/12_REVIEW_R6B_REMOVE_PARTIAL_FUNCTION_CONTRACT_CHURN.md
```

Далее выполнить отдельный commit, preflight, restart только API и live acceptance из R6. Push запрещён. После handoff остановиться.

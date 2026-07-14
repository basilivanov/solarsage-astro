# Review R6A — не ретрофитить legacy test-файл ради GRACE gate

Дата: 2026-07-14

Это обязательное уточнение к `10_REVIEW_R6_STAGING_DEV_AUTH_LOCAL_BYPASS.md`.

## 1. Причина остановки

Команда из R6:

```bash
python3 scripts/grace_lint.py \
  apps/api/app/api/auth.py \
  apps/api/tests/test_auth_endpoints.py
```

потребовала бы добавить module contract/map и function contracts ко всем старым тестам в `test_auth_endpoints.py`. Это было бы отдельным массовым metadata-ретрофитом legacy-файла и противоречило бы правилу репозитория:

```text
Старые файлы не переписывать ради GRACE-формата отдельно от задачи.
```

Архитектор остановил кодера до применения такого patch. На момент остановки в test-файле есть только нужные R6 imports/helper/regression tests — 76 добавленных строк, без массовой GRACE-разметки. Их сохранить.

## 2. Исправленная GRACE-проверка

В рамках R6 запускать strict GRACE lint только на существенно изменённом production-файле:

```bash
python3 scripts/grace_lint.py apps/api/app/api/auth.py
```

Для `apps/api/tests/test_auth_endpoints.py` обязательны:

```bash
apps/api/.venv/bin/python -m ruff check apps/api/tests/test_auth_endpoints.py
apps/api/.venv/bin/python -m pytest apps/api/tests/test_auth_endpoints.py -q
git diff --check
```

Не добавлять в legacy test-файл:

- `START_MODULE_CONTRACT`/`START_MODULE_MAP` только ради прохождения linter;
- function contracts ко всем существующим тестам;
- массовые comment-only изменения;
- реорганизацию старых тестов.

Новый private helper `_trusted_loopback_dev_auth_request()` и новые regression tests допустимы без полного ретрофита файла.

## 3. Scope после уточнения

Code/test scope остаётся ровно:

```text
apps/api/app/api/auth.py
apps/api/tests/test_auth_endpoints.py
```

В commit также включить оба R6 docs:

```text
docs/work/2026-07-14_backend-p0-security-hardening/10_REVIEW_R6_STAGING_DEV_AUTH_LOCAL_BYPASS.md
docs/work/2026-07-14_backend-p0-security-hardening/11_REVIEW_R6A_NO_LEGACY_GRACE_RETROFIT.md
```

Исправленный explicit stage:

```bash
git add -- \
  apps/api/app/api/auth.py \
  apps/api/tests/test_auth_endpoints.py \
  docs/work/2026-07-14_backend-p0-security-hardening/10_REVIEW_R6_STAGING_DEV_AUTH_LOCAL_BYPASS.md \
  docs/work/2026-07-14_backend-p0-security-hardening/11_REVIEW_R6A_NO_LEGACY_GRACE_RETROFIT.md
```

Все остальные tests, full suite, commit message, preflight, restart и live acceptance из R6 выполнять без изменений.

## 4. Продолжение

Продолжить с локальных gates раздела 6 R6, заменив только GRACE-команду согласно разделу 2 этого файла. После зелёных gates — отдельный commit, staging preflight, restart только API и live probes.

Push запрещён. После handoff остановиться.

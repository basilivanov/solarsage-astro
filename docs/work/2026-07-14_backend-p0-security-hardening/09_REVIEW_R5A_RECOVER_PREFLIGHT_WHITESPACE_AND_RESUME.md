# Review R5A — восстановить preflight после whitespace gate и продолжить rollout

Дата: 2026-07-14

Исполнитель: новый интерактивный кодер в `tmux astro:0.0`

Основное ТЗ после corrective-фазы: `08_RUNTIME_STAGING_ROLLOUT_TZ.md`.

## 1. Почему выполнение было остановлено

На фазе `git diff --cached --check` обнаружился технический пробел предыдущей приёмки: новые P0-файлы были untracked, поэтому обычный `git diff --check` их не видел. После explicit `git add` staged check корректно нашёл trailing whitespace.

Предыдущий кодер снял весь index и начал вручную удалять пробелы. Большинство сделанных изменений — безопасная whitespace-only нормализация, однако одна ручная замена потеряла перевод строки в `runtime_security.py` и превратила две строки в одну:

```python
for orig in raw_origins.split(","):        orig = orig.strip()
```

Архитектор остановил процесс до commit, env change и restart.

Фактическое безопасное состояние на момент этого ТЗ:

- branch остаётся `fix/backend-p0-security-hardening`;
- index пуст;
- commit не создан;
- push не выполнен;
- `.env` mtime не менялся, mode пока 664;
- `.env.production` не менялся, mode пока 664;
- `solarsage-api.service` всё ещё старый процесс PID `203504`, active/running, `NRestarts=0`;
- никакой live service не перезапускался.

## 2. Точная история уже сделанных R5-изменений

По журналу tool calls после начала R5 менялись только четыре исходных/test файла:

1. `apps/api/app/core/log_identity.py`
   - удалены только пробелы на пустых строках;
   - functional content не менялся;
   - оставляем текущее состояние.

2. `apps/api/app/core/runtime_security.py`
   - удалены пробелы на пустых строках;
   - одна строка цикла случайно склеена с телом;
   - требуется ровно одно функционально нейтральное восстановление newline, описанное ниже.

3. `apps/api/tests/test_cors_security.py`
   - удалены только пробелы на одной пустой строке;
   - оставляем текущее состояние.

4. `apps/api/tests/test_logging_privacy.py`
   - удалены только пробелы на нескольких пустых строках;
   - оставляем текущее состояние;
   - в файле остались другие trailing-space строки, их убрать механически, а не ручными многострочными Edit.

Никакие эти whitespace cleanup не откатывать.

## 3. Corrective scope — сначала ровно одна строка

В `apps/api/app/core/runtime_security.py` заменить текущую склеенную строку:

```python
        for orig in raw_origins.split(","):        orig = orig.strip()
```

на ровно две строки с правильным отступом:

```python
        for orig in raw_origins.split(","):
            orig = orig.strip()
```

Не менять рядом имена, условия, комментарии, типы, error codes или CORS-логику.

Сразу после этой одной правки выполнить:

```bash
cd /opt/solarsage-astro
apps/api/.venv/bin/python -m py_compile apps/api/app/core/runtime_security.py
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_runtime_security_policy.py \
  apps/api/tests/test_cors_security.py \
  -q
apps/api/.venv/bin/python -m ruff check \
  apps/api/app/core/runtime_security.py \
  apps/api/tests/test_runtime_security_policy.py \
  apps/api/tests/test_cors_security.py
```

Если здесь что-то падает, не stage и не чинить иное — остановиться с отчётом.

## 4. Whitespace cleanup — только механически и только exact files

Первый staged check до остановки перечислил whitespace defects только в этих файлах:

```text
apps/api/app/core/runtime_security.py
apps/api/tests/test_cors_security.py
apps/api/tests/test_logging_privacy.py
apps/api/tests/test_public_surface_security.py
apps/api/tests/test_runtime_security_policy.py
docs/work/2026-07-14_backend-p0-security-hardening/08_RUNTIME_STAGING_ROLLOUT_TZ.md
```

Использовать одну механическую whitespace-команду, которая:

- убирает только spaces/tabs непосредственно перед newline;
- нормализует EOF до ровно одного `\n`;
- не соединяет строки;
- не форматирует Python и не перестраивает imports.

Разрешённый вариант:

```bash
cd /opt/solarsage-astro
perl -0pi -e 's/[ \t]+(?=\n)//g; s/\n+\z/\n/' \
  apps/api/app/core/runtime_security.py \
  apps/api/tests/test_cors_security.py \
  apps/api/tests/test_logging_privacy.py \
  apps/api/tests/test_public_surface_security.py \
  apps/api/tests/test_runtime_security_policy.py \
  docs/work/2026-07-14_backend-p0-security-hardening/08_RUNTIME_STAGING_ROLLOUT_TZ.md
```

Не применять эту команду ко всему repo и не добавлять другие пути.

После неё проверить синтаксис всех затронутых Python-файлов:

```bash
apps/api/.venv/bin/python -m py_compile \
  apps/api/app/core/log_identity.py \
  apps/api/app/core/runtime_security.py \
  apps/api/tests/test_cors_security.py \
  apps/api/tests/test_logging_privacy.py \
  apps/api/tests/test_public_surface_security.py \
  apps/api/tests/test_runtime_security_policy.py
```

Затем выполнить принятый security gate:

```bash
cd /opt/solarsage-astro/apps/api
source .venv/bin/activate
python -m pytest \
  tests/test_runtime_security_policy.py \
  tests/test_public_surface_security.py \
  tests/test_cors_security.py \
  tests/test_logging.py \
  tests/test_logging_privacy.py \
  tests/test_log_envelope_shape.py \
  tests/test_log_intake.py \
  tests/test_redactor_canaries.py \
  tests/test_microcopy_misses.py \
  -q
python -m ruff check \
  app/core/log_identity.py \
  app/core/runtime_security.py \
  tests/test_cors_security.py \
  tests/test_logging_privacy.py \
  tests/test_public_surface_security.py \
  tests/test_runtime_security_policy.py
deactivate
cd /opt/solarsage-astro
python3 scripts/check_logging_guardrails.py
```

Важно: не запускать `ruff --fix`, `ruff format`, Black или общий formatter.

## 5. Повторный explicit stage

После зелёных checks повторить exact `git add -- ...` из раздела 5.1 основного `08_RUNTIME_STAGING_ROLLOUT_TZ.md`.

Затем обязательно:

```bash
git diff --cached --check
git diff --cached --name-status
git status --short
```

Ожидается:

- `git diff --cached --check` exit 0 и пустой stdout;
- frozen paths не staged;
- `.env`/`.env.production` не staged;
- staged набор соответствует whitelist.

Если staged check покажет новый whitespace defect:

1. снять весь exact whitelist через explicit `git restore --staged -- <те же paths>`;
2. не делать ручных многострочных замен;
3. если defect относится к одному из шести exact files раздела 4 — повторить механическую cleanup-команду только для него;
4. если defect относится к любому другому файлу — остановиться и передать архитектору path/line, не исправлять самостоятельно.

## 6. После зелёного staged check

Вернуться к `08_RUNTIME_STAGING_ROLLOUT_TZ.md` и продолжить с раздела 5.2:

1. локальный commit;
2. secure env backup;
3. exact staging env whitelist;
4. import/policy preflight;
5. snapshot соседних PID;
6. restart только `solarsage-api.service`;
7. health/public surface/OpenAPI/CORS/log privacy live-probes;
8. финальный handoff;
9. остановиться без push.

Все запреты, rollback и критерии из R5 остаются в силе.

## 7. Непереговорные ловушки

- Не интерпретировать whitespace gate как разрешение рефакторить код.
- Не переписывать новый файл целиком.
- Не восстанавливать untracked P0-файлы через git: в HEAD их нет.
- Не использовать `git clean`, reset или checkout.
- Не менять env до локального commit и зелёного startup preflight.
- Не restart при любой красной проверке.
- Не печатать secrets.
- Не push.

## 8. Corrective checkpoint перед commit

Перед `git commit` в handoff/рабочем выводе должно быть явно:

```text
R5A_RECOVERY_CHECKPOINT
runtime_security_newline: restored
whitespace_cleanup_scope: exact_6_files
py_compile: pass
security_targeted_tests: pass
ruff_exact_files: pass
logging_guardrails: pass
cached_diff_check: pass
index_scope: exact_whitelist
env_changed: no
service_restarted: no
```

После этого без паузы продолжить основной R5. Финальный ответ — только формат раздела 15 файла `08_RUNTIME_STAGING_ROLLOUT_TZ.md`.

# Stage 1.W3 — architect errata: legacy-unversioned stale API preflight

Дата: 2026-07-13
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted W2 SHA: `55d98917842bd94700030356da7fa1fc50abe86e`
Amends only:

- `113_STAGE_1_W3_CONTROLLED_CANONICAL_API_CONVERGENCE_TZ.md`, section 6.7;
- section 6.1 untracked allowlist/count;
- section 12 success callback label for the pre-restart control.

Статус: **AUTHORIZED NARROW PREFLIGHT CORRECTION — RESUME W3 FROM FULL PREFLIGHT**

## 1. Причина errata

Первый W3 запуск корректно остановился до restart:

```text
BLOCKED_STAGE_1_W3_PREFLIGHT
failed_gate: 6.7 Pre-restart real HTTP control must still be V1
auth_status: 200
control_status: 200
meta.payloadVersion: absent
meta.frontendPayloadVersion: absent
v2_present: false
api_restart_performed: NO
```

Архитектор независимо подтвердил после callback:

```text
API MainPID: 355509 unchanged
API start: Wed 2026-07-08 21:05:20 MSK unchanged
sidecar/frontend/nginx PID/start: unchanged
listeners 3003/8001/18092: absent
HEAD/local/origin: 55d98917842bd94700030356da7fa1fc50abe86e
tracked worktree/index: clean/empty
```

Это не W2 defect и не неожиданно включённый V2. Старый API process загружен до
появления явных public fields `payloadVersion` и `frontendPayloadVersion`.
Поэтому его V1 response может быть **legacy-unversioned**: `v2` отсутствует,
schema остаётся `today/v1`, но новые discriminator fields ещё не сериализуются.

Требовать от stale pre-restart process новые explicit fields было
архитектурно неверно. После restart новый process обязан выполнять строгий
explicit contract; это требование не ослабляется.

## 2. Неизменные запреты

Все разделы 3–5 и запреты 113 остаются в силе буквально:

- no repository edits by coder;
- no git add/commit/push;
- no env/unit/nginx edits;
- no daemon-reload;
- no manual uvicorn/second API/8001;
- no 3003/18092/W4;
- no restart sidecar/frontend/nginx;
- exactly one manual API restart only after full preflight;
- no secrets, session token, full payload or personal data in output;
- no second restart after any post-restart failure.

Coder не редактирует `113` или `114`; оба файла созданы архитектором.

## 3. Full preflight must be repeated

Начать заново с раздела 6.1 документа 113, а не продолжать сразу с restart.

Повторить:

1. branch/HEAD/local/tracking/remote;
2. tracked clean/index empty;
3. canonical unit identity;
4. exact old API PID/start;
5. env values and before hashes/metadata;
6. all four service PID/start witnesses;
7. listeners and health;
8. adversarial host-chain deny;
9. `59 passed` W2 module;
10. corrected pre-restart HTTP classification from section 5 below.

Если API PID/start уже отличается от accepted old baseline, restart запрещён.

## 4. Corrected untracked allowlist

Раздел 6.1 документа 113 теперь допускает exact seven untracked entries:

```text
?? .grace/
?? artifacts/design/
?? docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
?? docs/work/2026-07-11_today-v2-real-horizons-main-deploy/113_STAGE_1_W3_CONTROLLED_CANONICAL_API_CONVERGENCE_TZ.md
?? docs/work/2026-07-11_today-v2-real-horizons-main-deploy/114_STAGE_1_W3_ARCH_ERRATA_LEGACY_UNVERSIONED_PREFLIGHT_TZ.md
?? grace.db
?? skills/
```

Все остальные tracked/untracked/index изменения блокируют restart.

Final state в разделе 11 и callback в разделе 12 также должны использовать:

```text
untracked_scope: EXACT_7_ALLOWED
```

## 5. Replacement for section 6.7

Полностью заменить только acceptance logic раздела 6.7 документа 113 следующей
closed classification.

### 5.1 Transport remains identical

Real HTTP auth и control request остаются теми же:

```text
POST http://127.0.0.1:8000/api/auth/dev
GET  http://127.0.0.1:8000/api/day/2026-07-08
```

Day headers:

```text
Host: 127.0.0.1:8000
Origin: http://127.0.0.1:3003
X-Forwarded-For: 127.0.0.1
X-Real-IP: 127.0.0.1
X-Forwarded-Host: 127.0.0.1:3003
X-Forwarded-Port: 3003
Cookie: held only in process memory
X-SolarSage-Preview-Mode: ABSENT
```

### 5.2 Exact accepted pre-restart families

Общие обязательные условия:

```text
auth HTTP = 200
control HTTP = 200
meta is an object
meta.schemaVersion = today/v1
v2 is null/absent
```

После этого разрешены ровно две mutually exclusive V1 формы.

Form A — explicit V1:

```text
meta.payloadVersion = today.v1
meta.frontendPayloadVersion = 1
```

Form B — legacy-unversioned V1:

```text
meta.payloadVersion is absent/null
meta.frontendPayloadVersion is absent/null
```

Для Form B оба discriminator fields обязаны отсутствовать вместе. Нельзя
принимать partial form, например absent payload + frontend 1.

### 5.3 Absolute pre-restart denies

Restart запрещён, если найдено хоть одно:

```text
payloadVersion in {today.v2, today.v2.1}
frontendPayloadVersion in {2, 3}
v2 body present
v2.horizons present
only one discriminator absent
schemaVersion != today/v1
auth/control HTTP != 200
```

Отсутствие discriminator fields не означает автоматический pass. Оно допустимо
только вместе с exact `schemaVersion=today/v1` и отсутствующим V2 body.

### 5.4 Safe output

Для observed Form B вывести:

```text
PRE_RESTART_CONTROL: PASS_LEGACY_UNVERSIONED_V1
auth_status: 200
control_status: 200
schemaVersion: today/v1
payloadVersion: ABSENT
frontendPayloadVersion: ABSENT
v2_present: false
```

Для Form A:

```text
PRE_RESTART_CONTROL: PASS_EXPLICIT_V1
auth_status: 200
control_status: 200
schemaVersion: today/v1
payloadVersion: today.v1
frontendPayloadVersion: 1
v2_present: false
```

Human text/full body/session token не печатать.

## 6. Post-restart contract is not relaxed

Разделы 8–11 документа 113 остаются строгими.

После authorized restart legacy-unversioned response является failure.

Post-restart control обязателен exact:

```text
meta.schemaVersion = today/v1
meta.payloadVersion = today.v1
meta.frontendPayloadVersion = 1
v2 null/absent
```

Post-restart preview обязателен exact:

```text
meta.schemaVersion = today/v1
meta.payloadVersion = today.v2.1
meta.frontendPayloadVersion = 3
meta.contentVersion = 10
v2 body present
horizon pipeline = built / selected / 3
horizons = long, medium, fast
```

Control after preview обязан снова быть explicit `today.v1 / 1`; это доказывает
request scope и отсутствие global mutation.

Cache, provenance, timing, actions, journal privacy, PID/listener and env/unit
immutability gates не меняются.

## 7. Corrected success callback fragment

В success callback документа 113 заменить только:

```text
pre_restart_control: PASS_TODAY_V1_FRONTEND_1
untracked_scope: EXACT_6_ALLOWED
```

на:

```text
pre_restart_control: PASS_LEGACY_UNVERSIONED_V1
untracked_scope: EXACT_7_ALLOWED
```

Если фактически наблюдалась Form A, использовать:

```text
pre_restart_control: PASS_EXPLICIT_V1
```

Остальной callback из 113 — буквально без ослаблений.

После callback остановиться. Не запускать W4/3003, не создавать evidence doc,
не выполнять commit/push.

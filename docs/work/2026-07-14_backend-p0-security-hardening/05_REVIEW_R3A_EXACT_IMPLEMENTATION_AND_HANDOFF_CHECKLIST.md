# R3A — точная реализация для слабой coding-модели и checklist перед сдачей

Этот документ дополняет `04_REVIEW_R3_PROVEN_BYPASSES_AND_CORS_SIMPLIFICATION.md`.

Цель: не оставлять модели архитектурных решений и не допускать «зелёный test при неверном коде».

## 1. Немедленная поправка AST guardrail

Текущий checker ошибочно сравнивает base `credit` с forbidden key `credit_id`, поэтому `credit.id` не ловится. Кроме того, production checker и self-test содержат две расходящиеся реализации.

### 1.1. Не чинить текущую копию ещё одной копией

Вынести общие module-level constants/helpers и использовать их и в real scan, и в self-tests:

```python
FORBIDDEN_RAW_NAMES = {
    "user_id", "tg_user_id", "telegram_id", "session_id", "token",
    "question_id", "credit_id", "thread_id", "message_id", "report_id",
    "natal_context_id", "profile_id",
}

FORBIDDEN_ID_BASES = {
    "user", "session", "question", "credit", "thread", "message",
    "report", "profile", "natal_context",
}

APPROVED_HASH_HELPERS = {"hash_log_identifier", "hash_user_id"}
INPUT_BEARING_ATTRS = {"text", "content", "question"}
```

Не пытаться получить `credit` из `credit_id` через текущее equality-сравнение — это и есть причина падения.

### 1.2. Точный helper dotted path

```python
def _dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None
```

Примеры:

```text
credit.id              -> credit.id
question.id            -> question.id
obj.report.id           -> obj.report.id
context.natal_context.id -> context.natal_context.id
```

### 1.3. Один recursive expression analyzer

Сделать module-level private helper с GRACE contract, например:

```python
def _collect_log_expr_violations(node: ast.AST) -> list[str]:
    violations: list[str] = []

    def visit(current: ast.AST) -> None:
        if (
            isinstance(current, ast.Call)
            and isinstance(current.func, ast.Name)
            and current.func.id in APPROVED_HASH_HELPERS
        ):
            return  # raw argument разрешён только внутри approved hash helper

        if isinstance(current, ast.Name):
            if current.id.lower() in FORBIDDEN_RAW_NAMES:
                violations.append(f"raw identifier: {current.id}")

        elif isinstance(current, ast.Attribute):
            dotted = _dotted_name(current)
            parts = dotted.lower().split(".") if dotted else []

            if (
                len(parts) >= 2
                and parts[-1] == "id"
                and parts[-2] in FORBIDDEN_ID_BASES
            ):
                violations.append(f"raw attribute chain: {dotted}")

            if current.attr.lower() in FORBIDDEN_RAW_NAMES:
                violations.append(f"raw attribute: .{current.attr}")

            if current.attr.lower() in INPUT_BEARING_ATTRS:
                violations.append(f"forbidden input attribute: .{current.attr}")

        for child in ast.iter_child_nodes(current):
            visit(child)

    visit(node)
    return violations
```

Важные детали, которые модель обычно упускает:

- approved hash call нужно вернуть **до** обхода children, иначе `credit.id` внутри `hash_log_identifier("credit", credit.id)` будет ошибочно запрещён;
- использовать `parts[-2]`, а не сравнивать `credit` с `credit_id`;
- `ast.unparse()` можно использовать только для текста violation, не для логики;
- helper анализирует только expression, переданный из конкретного `log_event`, а не весь файл;
- `Name("id")` сам по себе не запрещать;
- arbitrary `model.id` не запрещать, если base не входит в `FORBIDDEN_ID_BASES`.

### 1.4. Один analyzer log_event call

Вынести module-level helper, например:

```python
def _collect_log_event_violations(call: ast.Call, file_info: str) -> list[str]:
    ...
```

Он должен:

1. Проверить literal dict keys через существующий `_check_dict_for_forbidden_keys`.
2. Для каждого `payload`, `error`, `http` вызвать `_collect_log_expr_violations(kw.value)`.
3. Найти `msg` и в positional, и в keyword форме.
4. Для `msg` вызвать тот же `_collect_log_expr_violations`.
5. Проверить `*_id_hash` value:
   - допустим `Name` с suffix `_hash`;
   - допустим direct approved hash helper call;
   - literal/raw/другой call запрещён.

Real repo scan и snippet self-tests должны вызывать **один и тот же** `_collect_log_event_violations`. Удалить локальные `check_dict_values_recursively`, `check_expr_for_forbidden_vars` и их копии из `run_self_tests`.

### 1.5. Self-test helper

```python
def _violations_for_snippet(code: str) -> list[str]:
    tree = ast.parse(code)
    result: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "log_event"
        ):
            result.extend(_collect_log_event_violations(node, "<self-test>"))
    return result
```

Assertions:

```text
safe prepared hash                         -> []
safe direct hash_log_identifier(credit.id) -> []
payload actor=user_id                     -> violation
payload actor=credit.id                   -> violation containing credit.id
msg question.id                           -> violation containing question.id
nested error report.id                    -> violation containing report.id
literal raw user_id_hash                  -> violation
```

Self-test не должен иметь отдельную реализацию detection logic.

## 2. Correlation: точная форма, без двусмысленности

Перед сдачей проверить буквально:

```python
SAFE = re.compile(r"^h1_[0-9a-f]{24}$")
```

- применять `fullmatch`, не `match`;
- `new_correlation_id()` всегда возвращает SAFE;
- `normalize_correlation_id(None/""/whitespace)` всегда возвращает SAFE;
- safe input сохраняется exactly;
- raw UUID/email/arbitrary bounded string хешируется и возвращает SAFE;
- >100/control/non-printable заменяется новым SAFE, raw value не хешируется/не логируется;
- middleware, `bind_log_context`, intake используют один helper;
- `build_envelope` fallback использует `new_correlation_id()`;
- `redact_dict({"correlation_id": raw})` не сохраняет raw;
- `redact_dict({"correlation_id": safe})` сохраняет safe.

Запрещённая ошибка: сделать middleware safe, но оставить direct binder/intake/redactor bypass.

## 3. Intake: точный порядок

Внутри loop:

```python
normalized = dict(envelope)
normalized["correlation_id"] = normalize_correlation_id(
    normalized.get("correlation_id")
)
redacted = redact_dict(normalized)
self._emit_line(redacted)
accepted += 1
```

Проверить:

- присваивание реально есть;
- redactor идёт после normalize;
- `_emit_line` получает `redacted`, не исходный `envelope`;
- исходный dict можно не мутировать;
- нет временных комментариев «wait/let's check/why failed/print exception»;
- нет runtime test-env monkeypatch/bypass;
- individual invalid envelope увеличивает `rejected`, но safe/deployed config error не маскируется под accepted.

## 4. Logger: точный exception boundary

```text
event registry validation  -> до try, programmer error может raise
build/redact/emit           -> внутри try, никогда не выходит наружу
fallback emit               -> nested try, его ошибка swallowing
```

Не использовать `except Exception as e` с повторным `raise` по классу `ValueError/RuntimeError/AssertionError`.

## 5. Runtime errors

Пройти `rg 'raise ValueError' apps/api/app/core/runtime_security.py` и проверить каждую строку:

- ни одна строка не форматирует raw settings value;
- запрещены `{orig}`, `{domain}`, `{hostname}`, `{settings.app_env}`, DSN/token/salt;
- допустимы только key, index, reason.

Тест обязан вставлять canary и утверждать `canary not in str(exc)`.

## 6. CORS

Перед сдачей `main.py` не содержит:

```text
class SafeCORSMiddleware
_send_wrapper
access-control-allow-origin в ручном ASGI коде
```

Должен использоваться только штатный `CORSMiddleware` с exact policy origins. Evil origin acceptance проверяется по отсутствию matching ACAO, а не по одному ACAC header.

## 7. Tests: не проверять helper вместо реального пути

Обязательные captures:

- middleware request -> response header + emitted `system.request`;
- direct `bind_log_context(raw)` -> `build_envelope` + `log_event`;
- HTTP `/api/_log` -> monkeypatched `_emit`;
- redactor/emit synthetic failure -> business call не бросает;
- runtime invalid canary -> exception не содержит canary.

Запрещённая подмена: вызвать только `hash_log_identifier(raw)` и объявить весь route/service защищённым.

## 8. Финальный handoff checklist

Перед словами «готово» модель сама отвечает `yes/no` по каждому пункту:

```text
[ ] Нет temporary reasoning/debug comments в production diff.
[ ] Нет duplicated AST analyzer между real scan и self-test.
[ ] Correlation output всегда fullmatch h1_[0-9a-f]{24}.
[ ] Intake присваивает normalized correlation до redaction.
[ ] Direct bind не выпускает raw correlation.
[ ] Logger не бросает internal redactor/emit errors.
[ ] Startup errors не содержат config canary.
[ ] Используется штатный CORSMiddleware.
[ ] Guardrail ловит credit.id/question.id/report.id.
[ ] Guardrail разрешает credit.id внутри approved hash helper.
[ ] Targeted tests зелёные.
[ ] Full API tests зелёные.
[ ] Ruff зелёный по всем changed/new Python.
[ ] GRACE lint зелёный по changed/new Python.
[ ] Logging guardrail зелёный.
[ ] compileall зелёный.
[ ] git diff --check пуст.
[ ] No live config/restart/commit/push.
```

Если любой пункт `no`, работа не завершена.

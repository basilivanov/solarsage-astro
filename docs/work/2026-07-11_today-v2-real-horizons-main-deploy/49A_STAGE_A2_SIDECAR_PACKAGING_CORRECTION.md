# Stage A2 Packaging Correction — fix the project backend, remove Docker hack

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Parent implementation TZ: `49_STAGE_A2_CONTRACT_AUTOMATION_IMPLEMENTATION_TZ.md`
Статус: **BLOCKING ARCHITECT CORRECTION**.

## 1. Найденная причина

Clean sidecar install/build падает:

```text
BackendUnavailable: Cannot import 'setuptools.build_backend'
```

Причина находится в настоящем project metadata:

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_backend"
```

`setuptools.build_backend` не является корректным PEP 517 backend. Канонический
backend для этого setuptools project:

```toml
build-backend = "setuptools.build_meta"
```

## 2. Запрещённый workaround

Нельзя создавать внутри image искусственный файл:

```text
site-packages/setuptools/build_backend.py
```

или переписывать installed setuptools. Такой workaround:

- скрывает дефект project metadata;
- делает local/CI/Docker installation разными;
- зависит от внутреннего layout third-party package;
- нарушает требование «один и тот же package install path».

Полностью удалить добавленный Python block из `apps/solarsage/Dockerfile`.

## 3. Разрешённое расширение allowlist

К A2 allowlist добавляется ровно один product metadata path:

```text
apps/solarsage/pyproject.toml
```

В нём изменить только:

```diff
-build-backend = "setuptools.build_backend"
+build-backend = "setuptools.build_meta"
```

Не менять dependencies, project version, requires-python или dev extras.

## 4. Required proof

После correction:

```bash
apps/solarsage/venv/bin/python -m pip install -e './apps/solarsage[dev]'
apps/solarsage/venv/bin/python -m pip check

docker build -f apps/solarsage/Dockerfile \
  -t solarsage-sidecar-contract-proof:a2 .

docker run --rm --entrypoint python \
  solarsage-sidecar-contract-proof:a2 -c \
  'from importlib.metadata import version; import solarsage.app, solarsage_contracts; assert version("solarsage-contracts") == "0.1.0"; print("sidecar-import-ok")'
```

Проверить, что Dockerfile больше не содержит:

```text
build_backend.py
Path(setuptools.__file__)
import setuptools
```

CI sidecar install должен использовать обычный `pip install -e
'./apps/solarsage[dev]'` и не иметь workaround.

## 5. Остальные границы

- Все остальные требования `49_STAGE_A2...` сохраняются.
- Commit/push по-прежнему запрещены.
- Stage B/A3/baseline fixes не начинать.
- После исправления продолжить A2 gates и вернуть исходный exact callback.

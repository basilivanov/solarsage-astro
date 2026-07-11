# S1.W3 Guidance — API test import bootstrap

Дата: 2026-07-11

Статус: точечная подсказка для продолжения текущей S1.W3, не отдельная волна.
Commit/push запрещены.

## Причина

При запуске из `apps/api`:

```text
.venv/bin/python -m pytest tests/test_today_fixture_contract.py
```

`sys.path` содержит API root, но не repository root. Поэтому import
`scripts.contracts.normalize_today_fixture` не находится.

## Решение

В `apps/api/tests/test_today_fixture_contract.py` до import из `scripts`:

```py
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.contracts.normalize_today_fixture import normalize_file
```

`FIXTURE_PATH` строить от того же `REPO_ROOT`.

Import `normalize_file` держать module-level после bootstrap, не импортировать
внутри test function.

Также в этом файле:

- удалить unused `os`;
- убрать trailing whitespace;
- сохранить import ordering;
- не менять application package path;
- не делать relative copy/import normalizer;
- после исправления сразу повторить два targeted API tests и продолжить весь
  S1.W3 по `27_S1_W3_IMPLEMENTATION_TZ.md`.

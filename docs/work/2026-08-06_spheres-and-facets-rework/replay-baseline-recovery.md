# Baseline replay recovery notes (2026-08-07)

## Инцидент 1: OOM-kill

09:46 MSK — OOM killer убил main-процесс baseline replay (pid 1421717) на 98/120
карт (7 ГБ хост, 8 воркеров + параллельная нагрузка). Чекпоинты 0–97 целы.

## Инцидент 2: абсолютный путь к canon в ablation_harness.py

`analysis/ablation_harness.py` читал canon YAML по абсолютному пути
`/opt/solarsage-astro/grace/canon/...` — т.е. из MAIN checkout, а не из
worktree. Оригинальный прогон (старт ~00:57, до коммита S2 в 01:24) держал в
памяти воркеров СТАРЫЙ canon — карты 0–97 валидны. Возобновлённый прогон
(11:02) поднял воркеров с НОВЫМ canon (12 новых ключей) при старом коде —
`project_group_spheres` падал с `ValueError: tuple.index(x)` на группах с
голосами за старые ключи (money/decisions/shopping). Ошибочно помечены error:
syn-098..syn-105 (8 карт).

## Восстановление

1. `ablation_harness.py` в обоих worktree пропатчен: пути canon через
   `Path(__file__).resolve().parents[4]` (как уже делал convergence_canon.py).
   Тот же фикс закоммичен в main (`fe4f758d`).
2. `factor_dump.json` (gitignored вход, 7.5 МБ) скопирован из main checkout в
   оба worktree — тот же файл, что использовал оригинальный прогон.
3. Новый source fingerprint baseline: `d0b032ca…` (изменился только
   ablation_harness.py; его поведение на картах 0–97 не менялось — прочитанное
   содержимое canon до S2 идентично worktree-копии, проверено: V2 keys старые).
4. 98 валидных чекпоинтов переподписаны новым fingerprint (метаданные, данные
   не тронуты); 8 corrupted error-чекпоинтов удалены.
5. Baseline перезапущен с `--resume` (pid 2009234): `120 charts, 22 pending`.
6. Candidate worktree: патч путей + манифест обновлён до вычисленного
   fingerprint `84694feb…` (= main после fe4f758d, проверено совпадение).
7. Chainer pid 2010019: candidate стартует автоматически после baseline,
   4 воркера + лимиты BLAS-потоков (OMP/OPENBLAS/MKL=1).

## Уроки

- Replay из worktree обязан читать ВСЕ входы из worktree; абсолютные пути в
  analysis-скриптах — скрытая зависимость от main checkout.
- `--workers 8` на 7 ГБ хосте — OOM; дальше только 4 + thread limits.

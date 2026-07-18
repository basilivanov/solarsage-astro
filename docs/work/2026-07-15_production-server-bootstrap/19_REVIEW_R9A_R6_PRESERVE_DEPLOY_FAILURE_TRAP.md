# Review R9A-R6 — preserve deploy failure trap

Дата: 2026-07-15

Исполнитель: кодер в `tmux astro:0.0`, модель `cliproxy/gemini-3-flash-agent`.

Статус: одна финальная блокирующая коррекция; commit/push/live apply запрещены.

## Проблема

`scripts/prod-deploy.sh` устанавливает глобальный `trap failure_handler EXIT`. Новая реализация `check_clean_source()` затем делает:

```bash
trap 'rm -f "$tmp_untracked"' EXIT INT TERM
...
trap - EXIT INT TERM
```

Это перезаписывает, а затем окончательно удаляет глобальный deploy failure trap. После первой clean-source проверки последующие ошибки теряют stage/old SHA/target SHA diagnostic contract.

## Исправление

Изолируй временный cleanup так, чтобы `failure_handler` не изменялся ни при success, ни при failure, ни при INT/TERM. Предпочтительный простой вариант: выполнить тело `check_clean_source` в функции-subshell (`check_clean_source() ( ... )`) и держать temp cleanup trap только внутри этого subshell. Внешний `EXIT` trap должен остаться byte-for-byte/semantically тем же и сработать после non-zero функции.

Альтернатива допустима только если старые traps EXIT/INT/TERM сохраняются и восстанавливаются точно, без `eval` пользовательских данных.

Nested `runuser ... bash -c` gate в `prod-host-prepare.sh` живёт в отдельном shell и глобальный deploy trap не затрагивает — не переделывай его без необходимости.

## Проверки

1. `bash -n` всех четырёх shell-файлов.
2. Локальный безопасный harness: установить test EXIT trap, вызвать успешный `check_clean_source`, затем вызвать контролируемый `false`; доказать, что исходный EXIT trap всё ещё сработал. Не запускать реальный deploy.
3. Проверить cleanup temp-файла на error path.
4. `git diff --check`, systemd verify, visudo, compose config.
5. Не читать/копировать/печатать настоящий `.env.production`; использовать только synthetic redacted fixtures.

Не commit/push/live apply/deploy/services. Дай короткий точный handoff и остановись.

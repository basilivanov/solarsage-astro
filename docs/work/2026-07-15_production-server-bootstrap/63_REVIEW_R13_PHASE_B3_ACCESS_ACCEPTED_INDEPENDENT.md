# R13 Phase B3 — access contract matrix ACCEPTED independently

## Решение

Узкий access-only проход принят после R3. `56_HANDOFF_R13_PHASE_B3_ACCESS_ONLY.md`
теперь соответствует фактическому коду и независимым прогонам.

## Независимая проверка архитектора

Выполнено:

```bash
bash -n scripts/prod-github-access.sh scripts/tests/test-prod-github-access.sh
timeout 300 bash scripts/tests/test-prod-github-access.sh
git diff --check -- scripts/prod-github-access.sh scripts/tests/test-prod-github-access.sh
```

Затем `timeout 300 bash scripts/tests/test-prod-github-access.sh` запущен второй
раз.

Результат обоих запусков:

- `rc 0`;
- финальная строка `All 162 test-prod-github-access matrix cases passed!`;
- выполнен последний `FAIL09_REC`;
- exact expected ID manifest совпал с actual manifest;
- syntax и diff check — `rc 0`.

## Что проверено инспекцией

- setup cases не входят в product `CASE_COUNT`;
- 162 ID заданы независимым expected manifest и сравниваются exact после sort;
- installed symlink/mode/owner cases разделены;
- mocks ограничены exact argv/path/type/category contracts и имеют negative
  self-checks;
- NET cases проверяют exact curl/get-url/timeout/ls-remote counts;
- API body, malformed remote и env sentinels реально проходят через потенциально
  опасные каналы и не появляются в output;
- FAIL01–09 не печатают success, не оставляют temp, сохраняют complete old-or-new
  destination state;
- каждый `_REC` восстанавливает exact canonical files/modes/origin;
- raw case/preparation output не печатается в diagnostics;
- `/tmp/solarsage-r13-access-test.*` после успешных прогонов отсутствует.

## Safety

- Production apply/deploy, real network/SSH/GitHub API не выполнялись.
- Commit и push не выполнялись.
- Другие R13 harness/phases в этом acceptance не запускались и не изменялись.
- На этом подзадача остановлена.

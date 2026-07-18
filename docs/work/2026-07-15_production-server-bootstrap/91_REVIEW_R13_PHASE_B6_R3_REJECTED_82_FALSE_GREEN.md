# R13 Phase B6 R3 — rejected: 82/82 is still false-green

## Verdict

Текущие `82/82` **не приняты**. Это второй преждевременный переход к final runs при открытых todo. Требования `90_REVIEW...` не заменяются ростом счётчика.

Ниже delta по фактическому состоянию harness после `82/82`. Закрыть каждый пункт до следующего handoff.

## Фактически не исправленный foundation

- Harness trap всё ещё `trap 'rm -rf "$TEST_DIR"' EXIT INT TERM HUP`: нет signal exit codes, idempotent cleanup и cleanup background lock-holder.
- Controlled stop всё ещё вставляется простым `sed ... exit 0`: нет exact pre/post anchor count, audit marker `controlled-stop` и proof достижения конкретной точки.
- Git/access/loader audit всё ещё записывается через `echo "$*"`, а не однозначные safe records.
- Access mock принимает любой lowercase SHA длины 40, но не проверяет, что это **тот же exact expected SHA** scenario.
- Loader mock игнорирует exact domain, не имеет configurable failure/no-export/wrong-export modes.
- `run_case` не проверяет temp leftovers после каждого case.
- Canary scan не проверяет audit; `FP_CANARY` и `ENV_SECRET_CANARY` не являются реальными значениями scenario, поэтому raw fingerprint/env leakage всё ещё может пройти.
- Invalid CLI cases не доказывают пустой audit до rc 2.

## Structural loader boundary всё ещё false-green

Текущий grep:

```bash
grep -nE '^\s*(source|\.|eval|set -a|set \+a).*\.env\.production'
```

не ловит variable-indirect source, например assignment пути на одной строке и `source "$ENV_PATH"` на другой. Он также печатает matching source line в stdout, что запрещено safe diagnostics contract.

Общий structural validator всё ещё не запускается на mutation copies. Независимая direct/indirect source mutation должна делать полный harness non-zero по symbolic reason без печати строки source.

## Env/loader matrix всё ещё неполна

Добавлены env directory/FIFO и несколько owner/mode cases, но отсутствуют:

- loader directory;
- loader FIFO;
- loader unreadable regular file;
- loader returns non-zero;
- loader returns zero without ephemeris export;
- loader exports nonexistent/wrong path как отдельный loader contract case;
- loader wrong env argument rejection;
- loader wrong domain rejection;
- valid loader exact argv + exact export audit assertion.

Без этого `ENV01..ENV16` не доказывают loader contract.

## Fingerprint matrix всё ещё неполна

Добавлены directory, several modes, owner/group и FIFO. Отсутствуют минимум:

- host unreadable;
- host mode 660;
- mocked leading-zero mode response;
- host exact-length nonhex;
- host spaces;
- host long record;
- repository empty output;
- repository long single line;
- repository command failure after partial output;
- две реальные valid 64-hex canary values и обязательный no-leak scan stdout/stderr/audit;
- per-failure proof, что loader/controlled-stop не достигнуты и fingerprint temp удалён.

## Transport/mode contract всё ещё неполон

Hostile empty/credential/multiline origins добавлены, но для них нет exact assertions `no access`, `no fetch`, `no checkout`, `no fingerprint`, `no loader`, `no set-url`.

Нет byte-exact audit manifests для:

- current mode с доказанным отсутствием всех transport calls;
- no-arg mode с fetch/checkout, но без access proof;
- pinned mode с marker `controlled-stop` и полным exact order.

Нет executable wrong-ref и wrong-checkout argv cases.

## Mutation engine фактически остался старым

После `82/82` в файле всё ещё присутствуют все rejected patterns:

- md5 вместо `cmp`;
- regex pre-count без exact post-count;
- MUT03 создаёт бессмысленный `get-url remote set-url`, а не реальный set-url regression;
- MUT06 удаляет весь fingerprint section вместо конкретного record-gate bypass;
- MUT07 не доказывает exact reached stage;
- MUT08 запускается с valid ephemeris и потому остаётся tautological;
- MUT09 сам объявляет PASS по наличию canonical lock path вместо запуска общего validator;
- `MUT10_RC` не asserted, controlled-stop не доказан;
- `MUT11_RC` не asserted, common runner/scanner не отвергает mutation;
- duplicate `leftovers=` и duplicate comments сохранены.

Это P0: не запускать final pair и не писать handoff, пока mutation section не переписан по разделу 6 файла `90_REVIEW...`.

## Следующее действие кодера

1. Остановить текущую финализацию после диагностического прогона.
2. Закрыть foundation и loader runtime matrix.
3. Закрыть fingerprint/transport exact assertions.
4. Полностью переделать mutation engine.
5. Только затем выполнить два **необрезанных** прогона, сохранить exact rc/stdout/stderr отдельно и написать handoff.

Production/network/DB/SSH/systemd/deploy/commit/push по-прежнему запрещены.

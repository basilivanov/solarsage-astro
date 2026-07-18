# R13 Phase B3A — убрать test-only comparators из production access

## Блокирующая корректировка

Текущие изменения в `scripts/prod-github-access.sh` неприемлемы:

1. Wrapper validation сначала сравнивает с `$REPO_DIR/...`, затем делает fallback на абсолютный `/opt/solarsage-astro/...`.
2. Known-hosts validation создаёт `real_template`, который в production совпадает с `TEMPLATE_KNOWN_HOSTS`, то есть `cmp` сравнивает файл с самим собой.
3. Harness затем добавляет специальные `sed` для этих fallback paths. Это тестирует тестовую ветку, а не production semantics.

## Требуемая production логика

### Wrapper

Вернуть единственную проверку:

```bash
cmp -s "$FORCED_WRAPPER" "$REPO_DIR/infra/production/solarsage-github-deploy"
```

Без fallback absolute path и без test-only branches. Path substitution `REPO_DIR` в copied harness уже достаточна.

### Known-hosts template

Нужен независимый production trust invariant, а не self-comparison.

- Добавить audited constant approved SHA-256 canonical template:
  `b6f76c2776447c3c23678e7ba4d2474836282c7bfa4ccc294b120ce68cd5261e`.
- После file type/owner/mode validation вычислить `sha256sum "$TEMPLATE_KNOWN_HOSTS"` и сравнить exact lowercase 64-hex с constant.
- Не выводить contents/keys.
- Добавить `sha256sum` в declared dependencies/required-command inventory, если его там ещё нет.
- При будущей ротации GitHub host keys оператор сознательно обновляет и template, и audited constant в одном review.

Harness мутирует copied template; production copy обязана упасть по hash mismatch без любых дополнительных absolute-path substitutions.

### SSH Host alias outside managed block

Текущий `grep -iq "Host[[:space:]]\+github.com-solarsage-prod"` не ловит alias вторым/третьим pattern (`Host other github.com-solarsage-prod`).

Разобрать строки outside block так:

- игнорировать blank/full-comment lines;
- keyword `Host` сравнивать case-insensitive;
- проверить каждый positive pattern field после keyword case-insensitive на exact `github.com-solarsage-prod`;
- alias первым или среди нескольких patterns должен fail;
- обычный comment с alias не должен fail.

Можно использовать bounded Python 3.12 helper/awk; raw config не переписывать.

## Harness cleanup

- Удалить все `sed` substitutions для `real_template` и absolute fallback comparator.
- Оставить только canonical constant/path substitutions из `55_TZ`.
- Сначала показать red `PATH35` на modified template и red `CFG10/CFG11`, затем production fix, затем green.

Продолжить только access pass. Остальные файлы и `51` не трогать. Production/real network/commit/push запрещены.

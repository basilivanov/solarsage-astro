# Canonical production database identity contract

## Dependency

Выполнять после/вместе с profile boundary из `70_TZ_ENV_PROFILES_AND_SECRET_BOUNDARY.md`. Эта задача закрывает P0 из `69_AUDIT...`: backup, Alembic и API не должны иметь возможность работать с разными БД.

Production/DB/network не запускать. Все tests используют только synthetic credentials и mocks. Реальные URL/password/user/database не читать и не выводить.

## Exact accepted identity

Принимается только одна canonical URL form:

```text
postgresql+asyncpg://<pct-user>:<pct-password>@127.0.0.1:5433/<database>
```

Правила:

- driver exact lowercase `postgresql+asyncpg`;
- host exact text `127.0.0.1`;
- port explicit decimal `5433`;
- query и fragment отсутствуют;
- path содержит ровно один non-empty database segment;
- `POSTGRES_USER` и `POSTGRES_DB` exact conservative ASCII identifiers: `^[a-z_][a-z0-9_]{0,62}$`;
- URL-decoded username/database byte-exact равны `POSTGRES_USER`/`POSTGRES_DB`;
- `POSTGRES_PASSWORD` non-empty, без NUL/control; reserved и Unicode разрешены только через canonical UTF-8 percent encoding;
- каждый `%` принадлежит `%[0-9A-F]{2}`; lowercase hex, double encoding и unnecessary encoding unreserved chars запрещены;
- leading/trailing whitespace, CR/LF/tab/NUL запрещены.

Fail closed reject:

- `postgresql://`, `postgres://`, psycopg/другой/mixed-case driver;
- `localhost`, IPv6, `0.0.0.0`, alternate textual/integer/octal/hex IPv4, DNS, Unix socket;
- missing/default/alternate port;
- empty/multiple path segments;
- any query (`ssl`, `sslmode`, `host`, `port`, `options`, multi-host и т.п.);
- user/database/password cross-field mismatch;
- case-only identity mismatch.

TLS/PG policy задаётся trusted command/systemd profile (`PGSSLMODE=disable` для loopback), а не URL query.

## Layer A — stdlib validation before any build/DB action

Разместить pure validation в non-executing env parser либо отдельном reusable testable module. Запускать через canonical `/usr/bin/python3.12 -I -S` там, где это отдельный process.

Algorithm over already parsed in-memory values:

1. Проверить четыре required keys и identifier/password contracts.
2. Проверить controls и percent escapes.
3. Построить canonical URL in memory через `urllib.parse.quote(..., safe='')`, fixed host/port и validated plain DB.
4. Сравнить supplied/canonical ASCII bytes через `hmac.compare_digest`.
5. Defense-in-depth `urlsplit`: exact scheme/netloc/path, empty query/fragment; strict UTF-8 decode user/password и byte-exact compare.
6. Любая ошибка возвращает только stable code `DB_IDENTITY_INVALID`/specific symbolic subcode.

Запрещено выводить URL, canonical reconstruction, username, database, password, их lengths, parsed object/repr, exception text или argv. Python memory нельзя обещать криптографически очистить; гарантируется отсутствие file/argv/log/output leakage.

Layer A выполняется:

- до profile generation/export;
- до `pnpm`/pip/build;
- до Docker DB initialization/config;
- до backup/restore/migration/restart.

Failure означает zero exports, zero partial profile replacements и zero external DB/build calls.

## Layer B — SQLAlchemy interpretation parity

После создания API venv, но до первого backup/migration/restart, запустить isolated child с DB-only profile:

- `sqlalchemy.engine.make_url`;
- проверить driver/host/port/database/empty query;
- `URL.translate_connect_args()` содержит exact host/database/username/password/port;
- password сравнивается через UTF-8 `hmac.compare_digest`;
- `ArgumentError`/exception text не выводится;
- не использовать `repr(url)`, `render_as_string` или kwargs logs.

Layer B доказывает, что SQLAlchemy/asyncpg интерпретирует строку как ту же identity, которую принял stdlib validator.

## PG environment boundary

Source env отвергает любые names matching case-insensitive `^PG`, включая `PGHOST`, `PGPORT`, `PGUSER`, `PGDATABASE`, `PGPASSWORD`, `PGPASSFILE`, `PGSERVICE*`, `PGOPTIONS`, `PGSSL*`, `PGTARGETSESSIONATTRS`.

Для pg tools использовать `env -i`/profile child:

- trusted HOME/PATH/locale;
- exact flags `-h 127.0.0.1 -p 5433 -U ... -d ...`;
- derived `PGPASSWORD` только в child scope;
- command-owned `PGSSLMODE=disable`;
- `psql -X --no-password` где применимо.

`pg_isready` — только endpoint readiness, не authentication/identity proof.

## Integration points

### `scripts/lib/prod-env-loader.sh`

Заменить current empty/non-SQLite substring check на Layer A до записи assignments/profiles. Сделать validation reusable по profile contract.

### `scripts/prod-deploy.sh`

- source/origin/SHA/fingerprint gates остаются env-free;
- Layer A до install/build;
- Layer B после venv build и до backup/migration;
- DB/API preflight в isolated profile, без глобального secret export;
- no DB action after any identity mismatch.

### Backup/restore

`prod-backup.sh`/`prod-db-restore.sh` используют DB-only profile и Layer A. Identity failure означает no pg_dump/temp dump/service mutation/safety backup/psql/pg_restore.

### Alembic

Убрать fragile textual `.replace('+asyncpg', ...)`. Использовать:

```python
async_url = make_url(DATABASE_URL)
sync_url = async_url.set(drivername="postgresql+psycopg")
```

Передавать SQLAlchemy `URL` object напрямую где возможно. Если ConfigParser требует string, escape `%` корректно и никогда не логировать. Migration child получает минимальный DB profile.

### DB systemd/bootstrap

Layer A обязателен до первого `docker compose up`, иначе container может быть initialized по `POSTGRES_*`, а API указывать на другой target. После startup добавить authenticated boolean smoke query без вывода identity/password.

## Synthetic test matrix

### Valid

- simple identifiers/password;
- password with `@ : / ? # [ ] % + space`, canonical percent encoding;
- UTF-8 password encoded canonical bytes;
- literal `%` as `%25`;
- boundary identifier/password lengths;
- SQLAlchemy parity exact five connect args;
- no secret canary in stdout/stderr/audit/temp.

### Invalid URL/driver/encoding

- wrong/mixed driver;
- missing user/password/db/colon;
- whitespace/control/NUL;
- malformed/lowercase percent hex, double/unnecessary encoding;
- raw reserved password characters;
- query/fragment/extra path.

### Invalid host/port

- localhost/IPv6/0.0.0.0/trailing-dot/alternate IPv4/DNS/socket/encoded host;
- missing/5432/zero/out-of-range/nonnumeric/query override.

### Cross-field mismatch

- username/database/password mismatch;
- case-only mismatch;
- invalid identifier characters/Unicode;
- missing each required key;
- Unicode normalization forms compare byte-exact (никакой implicit normalization).

### PG injection and ordering

- representative source/inherited `PG*` rejected/stripped;
- child audit contains only exact allowed env names;
- loader mismatch → no assignments;
- deploy mismatch → no install/build/backup/Alembic/restart;
- backup mismatch → no pg_dump/temp;
- restore mismatch → no service mutation/backup/restore;
- no temp file and no secret via argv.

### Mutation proof

Удалить/ослабить по одному assertion driver/host/port/query/user/db/password/PG strip. Тот же test suite обязан стать non-zero. Green “Postgres-like URL” check не принимается.

## Acceptance

Coder выполняет только isolated tests. Architect проверяет code path и два независимых прогона. Production DB connectivity будет отдельным explicit launch rehearsal после команды пользователя.

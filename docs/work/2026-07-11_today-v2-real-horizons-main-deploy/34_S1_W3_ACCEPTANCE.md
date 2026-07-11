# S1.W3 Architect Acceptance — one-source fixture and contract workflow

Дата: 2026-07-11
Вердикт: `ACCEPTED_S1_W3`
База: `5ffeebac283f3a95a11f122c7b0ef35923cefecf`

## Принятая архитектура

```text
Pydantic API wire schema
  -> deterministic OpenAPI
  -> generated TypeScript
  -> generated runtime Zod
  -> one runtime validation at fetchDay
  -> typed adapter without reparse

canonical Today JSON fixture
  -> strict extra-forbid Pydantic validation
  -> deterministic alias dump
  -> generated Zod validation
  -> thin TypeScript wrapper
```

`activeFrom`, `exactAt`, `activeUntil` добавлены consumer-first как optional
wire fields в API и sidecar schemas. Calculation/producer population и version
bump в S1.W3 отсутствуют.

## Developer workflow после S1.W3

Изменение API contract:

```bash
# 1. изменить Pydantic schema
pnpm contracts:generate
# 2. исправить типизированных consumers
pnpm contracts:check
```

Изменение canonical visual payload:

```bash
# 1. изменить единственный JSON
pnpm contracts:fixture:normalize
pnpm contracts:check
```

`contracts:check` сам выполняет generate → fixture read-only check → generated
diff. CI запускает этот же gate отдельным job.

## Независимые проверки архитектора

```text
YAML parse: PASS
contracts:check: PASS
API contract tests: 12 passed
sidecar schema tests: 6 passed
focused contract/guard Vitest: 3 files / 18 passed
full Vitest: 95 files / 980 passed
TypeScript: PASS
mobile visual E2E with --update-snapshots=none: 2 passed
production proof build from implementation gate: PASS
git diff HEAD --check: PASS
git diff --cached --check: PASS
forbidden type/suppression scan: 0
staged S1.W3 paths: 30
staged binary paths: 0
```

Дополнительно доказано:

- exact guarded dev-route import — ровно один;
- нулевой/второй/не-awaited import не проходит guard;
- normalizer `--check` не пишет файл и не создаёт parent directory;
- invalid payload error не выводит sentinel/raw JSON;
- wrapper принимает только no args или exact `--check`;
- один payload source для `day-v2-2026-07-08`;
- adapter сохраняет identity `payload.v2`;
- generated Zod отвергает неверный timing type;
- version constants не менялись.

## Commit sequencing

Сначала выполнить отдельный accepted visual baseline repair из:

```text
docs/work/2026-07-11_preview-visible-sphere-status-labels/02_VISUAL_BASELINE_REPAIR_ACCEPTANCE.md
```

После его commit/push собрать только S1.W3 allowlist, включая этот acceptance,
но без baseline PNG и без unrelated untracked paths.

S1.W3 commit subject:

```text
test(contracts): prove today v2 fixture round trip
```

Push только:

```text
origin/preview/solarsage-v2-human-first-navigator-ux
```

После push подтвердить, что origin SHA равен local HEAD, а worktree содержит
только заранее существовавшие unrelated untracked paths.

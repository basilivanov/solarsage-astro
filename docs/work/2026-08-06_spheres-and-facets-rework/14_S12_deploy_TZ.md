# S12 TZ — deploy to dev

## packet title
S12-deploy-dev

## Phase / Wave
W-SPHERES-FACETS-REWORK

## Выполняет ревьюер (не кодер), после зелёных replay gates (S11).

## Чеклист
1. Replay gates (мастер-ТЗ §10.5): full candidate replay errors=0,
   unmapped/group-without-sphere=0, old keys=0, invalid facet=0;
   physical signatures baseline vs candidate совпадают (event IDs, group IDs,
   hero, evidence, polarity, dayTone, state); разрешённый delta только
   sphere/facet/selected/labels. Сравнение: свести
   `/var/tmp/spheres-baseline/physical_signatures.jsonl` и
   `/var/tmp/spheres-candidate/physical_signatures.jsonl` по
   (chart_id, birth_mode, target_date).
2. `git push origin main`.
3. `NODE_ENV=production npm run build` (собирает в `.next-prod`).
4. `cd apps/api && .venv/bin/alembic upgrade head` (0031 check-in data-migration;
   на dev БД ожидаемый no-op — 2 строки NULL, подтверждено preflight).
5. `systemctl restart solarsage-api solarsage-frontend solarsage-sidecar`.
6. Post-deploy smoke:
   - `curl https://dev.astro.vasiliy-ivanov.ru/api/health` — git_sha == HEAD;
   - Telegram-auth e2e smoke: день открывается, 12 тайлов новых ключей,
     drilldown работает, `/day/spheres/<key>` → 404;
   - `GET /api/spheres/finance` → 200 с periodSynthesis/note;
   - `GET /api/spheres/money` → 4xx (старый ключ);
   - check-in создаётся с новыми ключами.
7. Обновить AGENTS.md, если поменялось поведение портов/юнитов (не ожидается).
8. Отчёт владельцу: SHA, результаты smoke, ссылка на dev.

## Rollback
`git revert` пакета + rebuild + restart; миграция 0031 data-only, downgrade —
no-op by design (старое поведение ключей не восстанавливается на уровне данных,
но кодовый revert не ломает новые значения: старый код не читает finance —
поэтому rollback только после решения владельца о данных).

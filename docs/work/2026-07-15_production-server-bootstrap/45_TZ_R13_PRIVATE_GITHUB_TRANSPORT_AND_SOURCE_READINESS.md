# R13 — private GitHub transport и source-readiness без deploy

## Роль и границы

Ты кодер `cliproxy/gemini-3-flash-agent` в tmux `astro:0.0`. Реализуй только этот infra slice.

Запрещено: менять visibility GitHub repository; удалять deploy keys; читать/выводить/коммитить private keys, tokens, `.env.production` или API keys; SSH в production; реальный deploy/fetch/push/systemd app restart; commit/push. Не трогать `.grace/`, `artifacts/design/`, `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`, `grace.db`, `skills/`.

Все тесты — только temporary HOME/repository и mock ssh/git/curl. Никакой внешней мутации.

## Известные facts

- repository: `basilivanov/solarsage-astro`, branch `main`;
- production SSH alias должен быть отдельным: `github.com-solarsage-prod`;
- repository сейчас PUBLIC: final source-readiness обязан fail-closed до ручного перевода в private;
- GitHub production environment уже использует secret names `PROD_HOST`, `PROD_USER`, `PROD_SSH_PRIVATE_KEY`, `PROD_KNOWN_HOSTS`; values не читать;
- существует production read-only deploy key и отдельный legacy write key. Не удалять их автоматически; write key — внешний operator review.

## 1. GitHub host-key template

Добавить `infra/ssh/github.com.known_hosts` с тремя canonical public host keys GitHub (`ssh-ed25519`, `ecdsa-sha2-nistp256`, `ssh-rsa`) и комментариями с SHA256 fingerprints. Источник — официальный GitHub Meta API/официальная документация. Не использовать слепой `ssh-keyscan` как trust root.

- только `github.com`, без wildcard/hashed aliases;
- при host install: `astro:astro 0600`;
- добавить в infra fingerprint и host-prepare inventory;
- tests должны обнаруживать changed/unknown key.

## 2. `scripts/prod-github-access.sh`

Новый GRACE-marked script. Exact CLI:

```text
scripts/prod-github-access.sh --apply
scripts/prod-github-access.sh --preflight
scripts/prod-github-access.sh --check
scripts/prod-github-access.sh --check --expected-sha <40 lowercase hex>
```

Другие args → rc 2 до privilege checks.

### Canonical paths

- checkout private key: `/home/astro/.ssh/solarsage_prod_server_ed25519`;
- derived public key: `/home/astro/.ssh/solarsage_prod_server_ed25519.pub`;
- GitHub known hosts: `/home/astro/.ssh/known_hosts.github`;
- SSH config: `/home/astro/.ssh/config`;
- operator-supplied Actions public key: `/etc/solarsage/keys/github-actions-deploy.pub`;
- authorized keys: `/home/astro/.ssh/authorized_keys`;
- forced wrapper: `/usr/local/sbin/solarsage-github-deploy`;
- repo: `/opt/solarsage-astro`.

Не генерировать и не overwrite checkout private key. Missing/invalid → safe error with path, never key material.

### Common validation

1. Require real regular non-symlink objects and exact ownership/modes:
   - `.ssh`: `astro:astro 0700`;
   - private checkout key: `astro:astro 0600`;
   - public key: `astro:astro 0644`;
   - known_hosts/config/authorized_keys: `astro:astro 0600`;
   - Actions public key: preferably `root:root 0644`.
2. `ssh-keygen -y -P ''` derives checkout public key; compare normalized type+base64 with `.pub`, suppress content. Require noninteractive/no-passphrase key.
3. Print only SHA256 fingerprint, never public/private key text.
4. Actions key must be one exact `ssh-ed25519` line, no options/extra lines/private material.
5. Reject symlinks/FIFO/directories/duplicates and unsafe modes.

### `--apply` (root-only)

Idempotent and atomic:

1. Verify inputs and forced wrapper `root:root 0755`.
2. Install repo known_hosts template atomically to canonical user path.
3. Preserve unrelated SSH config and manage one exact block:

```sshconfig
# BEGIN SOLARSAGE-PROD-GITHUB
Host github.com-solarsage-prod
  HostName github.com
  User git
  IdentityFile ~/.ssh/solarsage_prod_server_ed25519
  IdentitiesOnly yes
  UserKnownHostsFile ~/.ssh/known_hosts.github
  StrictHostKeyChecking yes
  PasswordAuthentication no
  KbdInteractiveAuthentication no
  BatchMode yes
# END SOLARSAGE-PROD-GITHUB
```

Reject duplicate/conflicting managed block. Use same-directory 0600 temp + atomic rename; no `sed -i`.

4. Normalize origin only if it already points to the expected owner/repo; otherwise fail unchanged:

```text
git@github.com-solarsage-prod:basilivanov/solarsage-astro.git
```

5. Manage exact Actions forced-command line:

```text
restrict,command="/usr/local/sbin/solarsage-github-deploy" ssh-ed25519 <operator-public-key> solarsage-github-actions-prod
```

- preserve unrelated authorized_keys lines byte-exact;
- replace only exact managed comment;
- same key elsewhere without exact forced command → fail closed;
- duplicate managed lines → fail;
- same-directory 0600 temp + atomic rename;
- never remove operator/root access keys.

6. Do not reload/restart sshd. After apply run only local/read-only preflight; public repository may warn but not claim production-ready.

### `--preflight`

Read-only and allowed as `astro`:

- structural file/config/remote validation;
- bounded `git -C /opt/solarsage-astro ls-remote --exit-code origin refs/heads/main` through pinned alias/key;
- optional expected SHA exact comparison;
- GitHub HTTPS reachability;
- PUBLIC repository is an explicit warning, not green production readiness.

### `--check`

Read-only final source readiness:

1. Query anonymous `https://api.github.com/repos/basilivanov/solarsage-astro`, capture only HTTP status/body suppressed:
   - 200 → fail `repository is public`;
   - 404 + successful SSH `ls-remote` → private proof;
   - 403/5xx/timeout/other → fail.
2. `--expected-sha` compares exactly to remote `refs/heads/main`.
3. No fetch/checkout/push/mutation.

Safe output: statuses, SHA, paths, fingerprints. Never key contents, token, credential URL or API response body.

## 3. Forced-command wrapper

Update `infra/production/solarsage-github-deploy`:

- zero positional args;
- exact commands only:
  - `deploy <40 hex>` → current deploy script;
  - `source-check <40 hex>` → `prod-github-access.sh --check --expected-sha <sha>`;
- empty/other/injection/extra whitespace/newline → rc 126;
- direct `exec`, no `eval` or shell reconstruction.

Add isolated wrapper harness; valid dispatches use mocks and never real deploy.

## 4. Manual source-readiness workflow

Add `.github/workflows/source-readiness.yml`:

- `workflow_dispatch` only;
- concurrency `production-source-readiness`, `cancel-in-progress: false`;
- `environment: production`, `permissions: {}`, timeout <=10m;
- require main ref, lowercase 40-char SHA, `github.event.repository.private == true` before SSH config;
- only existing PROD_* environment secrets;
- ephemeral key + strict known_hosts;
- exact remote `source-check $GITHUB_SHA`;
- always cleanup key/known_hosts;
- no checkout/build/deploy/restart.

Add a private-repository gate to existing `deploy-production.yml` before any production connection.

Static workflow test must prove manual-only, private gate, permissions {}, exact command, timeout, cleanup and no secret logging.

## 5. `scripts/prod-deploy.sh` hardening

Do not deploy; change code path only:

1. Remove `source .env.production`/`set -a` execution and old self-check. Use existing non-executing `scripts/lib/prod-env-loader.sh` + `prod_env_load .env.production astro.vasiliy-ivanov.ru` after owner/mode checks.
2. Require loader regular/non-symlink; exported variables must remain available to later preflight/migrations.
3. Before fetch in expected-SHA mode call `prod-github-access.sh --check --expected-sha "$EXPECTED_SHA"` (or exact shared read-only function). No fetch/checkout before transport validation.
4. Git must use pinned `github.com-solarsage-prod` alias; reject credential URL/unknown repo.
5. Add isolated harness for env-loader/Git routing; no real fetch/build/restart.

## 6. Inventory and runbook

Add new script/template/workflow/tests to host inventory, `bash -n` and infra fingerprint. Do not silently install Actions key from an unrelated transaction. Canonical operator sequence:

```bash
sudo /opt/solarsage-astro/scripts/prod-github-access.sh --apply
sudo -u astro -- /opt/solarsage-astro/scripts/prod-github-access.sh --preflight
```

Update `docs/PRODUCTION_RUNBOOK.md`:

1. register checkout public key as GitHub **read-only** deploy key;
2. Actions private key lives only in GitHub environment, its public key is placed on host;
3. run apply/preflight;
4. owner manually changes repository visibility to private;
5. source-readiness workflow must be green before deploy workflow;
6. legacy write deploy key is reviewed/revoked manually when no longer needed; task never revokes it;
7. no key contents or secret values in docs/logs.

After implementation write `46_REVIEW_R13_OPERATOR_INPUTS.md` listing required external inputs without values.

## 7. Required isolated tests

Add GRACE-marked:

```text
scripts/tests/test-prod-github-access.sh
scripts/tests/test-prod-github-wrapper.sh
scripts/tests/test-prod-source-readiness-workflow.sh
scripts/tests/test-prod-deploy-source-loader.sh
```

Coverage:

- key/config/known_hosts owner/mode/symlink/type rejection;
- authorized_keys unrelated-line preservation, idempotence, duplicate/unrestricted-key failure, atomic write failure;
- exact alias/remote;
- mocked ls-remote success/SHA mismatch/nonzero/timeout;
- mocked GitHub API 200/404/403/5xx/timeout;
- wrapper exact dispatch and rc126 invalid commands;
- workflow contract;
- deploy uses env loader, no direct `.env` source/eval;
- zero real SSH/network/visibility/key/repo mutations.

Acceptance:

```bash
bash -n scripts/prod-github-access.sh scripts/tests/test-prod-github-access.sh scripts/tests/test-prod-github-wrapper.sh scripts/tests/test-prod-source-readiness-workflow.sh scripts/tests/test-prod-deploy-source-loader.sh
scripts/tests/test-prod-github-access.sh
scripts/tests/test-prod-github-wrapper.sh
scripts/tests/test-prod-source-readiness-workflow.sh
scripts/tests/test-prod-deploy-source-loader.sh
scripts/prod-infra-fingerprint.sh
git diff --check
```

No commit/push. Stop with exact handoff, operator inputs and remaining blockers.

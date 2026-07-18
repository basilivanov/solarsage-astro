# Non-cyclic fresh-host GitHub transport and lockout-safe SSH hardening

## Problem

Current runbook orders `prod-github-access.sh --apply` before `prod-host-prepare.sh --apply`, but access apply already requires the forced wrapper installed by host-prepare. It also calls checkout key “server-generated” without a canonical generation command. Fresh-host flow is therefore cyclic and incomplete.

Production apply/SSH/network is forbidden while implementing this task. Tests use sandbox paths/mocks only. GitHub registration and final sshd lockout changes remain explicit operator gates.

## Canonical order

```text
trusted offline clean checkout at known SHA
  → OS bootstrap
  → production env profiles / DNS / certificate inputs
  → host-prepare (installs wrapper + sudoers; no application deploy)
  → GitHub key bootstrap phase
  → checkout public key registered read-only in GitHub
  → Actions public key installed on server; private key only in GitHub Environment
  → prod-github-access --apply
  → --preflight while repository may still be public
  → operator changes repository to private
  → local --check --expected-sha
  → manual Source Readiness workflow for same SHA
  → pinned first deploy for same SHA
  → final lockout-safe sshd hardening
```

Runbook must state actor (`root`, `astro`, workstation/GitHub owner), expected rc/evidence and stop points.

## 1. Trusted bootstrap source

Fresh host receives a trusted clean checkout including `.git` at an operator-pinned SHA. A source archive without `.git` is insufficient for current access/deploy contracts.

Required state before transport setup:

```text
/opt/solarsage-astro        astro:astro 0750
checkout and .git           astro:astro
worktree/index              clean
origin                      canonical credential-free HTTPS or approved SSH
HEAD                        exact operator-provided lowercase 40-hex
```

Add a read-only bootstrap-source verifier that accepts expected SHA and proves owner/mode, `.git`, clean worktree, exact HEAD and credential-free origin. It must not fetch or rewrite origin.

## 2. Wrapper ownership remains host-prepare

`prod-host-prepare.sh --apply` is the canonical owner of:

```text
/usr/local/sbin/solarsage-github-deploy   root:root 0755
/etc/sudoers.d/90-solarsage-deploy       root:root 0440, visudo-valid
```

Host-prepare must complete before GitHub access apply, while still not deploying application code. Do not duplicate manual wrapper installation in the normal flow.

## 3. New root-only key bootstrap script

Create a check/apply script dedicated to filesystem/key preparation; it must not call GitHub/network and must never print private key material.

Suggested CLI:

```text
prod-github-key-bootstrap.sh --check --actions-public-key <path>
prod-github-key-bootstrap.sh --apply --actions-public-key <path>
```

Responsibilities:

1. Require root for apply; check can be read-only root.
2. Verify user/group `astro` and installed forced wrapper.
3. Create/verify:

```text
/home/astro/.ssh                                      astro:astro 0700
/etc/solarsage                                       root:root 0755
/etc/solarsage/keys                                  root:root 0755
```

4. Checkout keypair:

```text
/home/astro/.ssh/solarsage_prod_server_ed25519       astro:astro 0600
/home/astro/.ssh/solarsage_prod_server_ed25519.pub   astro:astro 0644
```

- generate ed25519 as user `astro`, no passphrase, canonical comment;
- generate into private temp directory and atomically install;
- if neither exists, generate once;
- if one half exists, pair mismatches, key has passphrase, wrong type/owner/mode, fail without overwrite;
- never regenerate/rotate automatically;
- public file exact one LF-terminated line;
- diagnostics may print only SHA256 fingerprint, never key text/base64/private path contents.

5. Actions public key:

```text
/etc/solarsage/keys/github-actions-deploy.pub         root:root 0644
```

- private Actions key is created on trusted operator workstation, never on production server;
- input path must be regular non-symlink, exact one LF line, valid `ssh-ed25519`, expected canonical comment;
- atomic install; idempotent byte-exact second apply;
- different existing key requires explicit separate rotation workflow, not silent replacement.

6. Script does not edit `authorized_keys`, SSH config, known_hosts or Git origin; those remain `prod-github-access.sh --apply` responsibilities after operator registration.

Add isolated owner/mode/type/partial-pair/idempotence/failure-injection harness. No real home/etc paths in tests.

## 4. Four independent identities

Never reuse one key:

- operator login key: workstation/security key → `/home/ops/.ssh/authorized_keys`;
- server checkout key: private only on server → GitHub read-only deploy key;
- Actions inbound key: private only GitHub Environment → forced line for `astro`;
- SSH host identity: server host private key → public line in `PROD_KNOWN_HOSTS`.

GitHub Actions environment secrets stay exactly:

```text
PROD_HOST PROD_USER PROD_SSH_PRIVATE_KEY PROD_KNOWN_HOSTS
```

Host known_hosts value comes from trusted provider console/root observation of the host ed25519 public key, not blind unauthenticated `ssh-keyscan`.

## 5. Access and private-transition gates

After operator registers checkout public key read-only and supplies Actions public key:

1. root `prod-github-access.sh --apply`;
2. `astro` `--preflight` (can warn public, not final gate);
3. operator switches repository to private;
4. `astro --check --expected-sha <SHA>`;
5. GitHub Source Readiness workflow exact same SHA;
6. pinned deploy exact same SHA.

Record only rc/fingerprints/SHA, never keys or secret values. Existing unrelated unrestricted key in `astro/authorized_keys` is a launch blocker: script currently preserves unrelated lines, so operator review/removal must be explicit and tested.

## 6. Separate operator account

Create `ops`, not administrator access through `astro`:

```text
/home/ops                         ops:ops 0750
/home/ops/.ssh                    ops:ops 0700
/home/ops/.ssh/authorized_keys    ops:ops 0600
/etc/sudoers.d/90-ops-admin       root:root 0440, visudo-valid
```

Operator public key is an explicit input. Do not generate/reuse Actions or checkout key. Sudo policy is explicit; if `NOPASSWD: ALL` is chosen, record it as operator-only risk/decision.

## 7. Lockout-safe sshd hardening

Implement managed drop-in + check/apply phases with rollback copy, but final transition requires operator confirmation after fresh-session proof.

Safe sequence:

1. Keep current root/provider-console access open.
2. Install and prove `ops` key in a second session; prove `sudo` and reconnect.
3. Verify UFW port 22 and Fail2ban state.
4. Write staged drop-in, run `/usr/sbin/sshd -t` and inspect effective `/usr/sbin/sshd -T` plus `-C user=...` cases.
5. Staged policy:

```text
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitEmptyPasswords no
AuthenticationMethods publickey
PermitRootLogin prohibit-password
AllowUsers root ops astro
MaxAuthTries 3
```

6. `systemctl reload ssh`, never restart.
7. Prove new `ops`, temporary root pubkey, and forced Actions/source-readiness connections.
8. Only after explicit operator confirmation generate final policy:

```text
PermitRootLogin no
AllowUsers ops astro
```

9. Repeat syntax/effective checks, reload and fresh ops+sudo login.
10. Close old root session only after proof.

Effective `sshd -T` values are authoritative because provider configs may precede the managed drop-in. SSH host keys are never regenerated during hardening or `PROD_KNOWN_HOSTS` breaks.

Tests must mock `sshd/systemctl`, prove invalid config causes no reload, exact rollback bytes, staged/final distinction and no mutation before operator-finalize token/input. No live SSH in implementation tests.

## 8. Runbook acceptance

Replace the old cyclic/duplicate GitHub sections with one numbered checklist. Every step specifies:

- actor;
- exact command;
- expected rc/safe output;
- evidence location;
- rollback/retry;
- whether it is automated or operator-owned.

Coder must not claim live SSH proof. Architect accepts code/tests; live fresh-host rehearsal remains a separate explicit user command.

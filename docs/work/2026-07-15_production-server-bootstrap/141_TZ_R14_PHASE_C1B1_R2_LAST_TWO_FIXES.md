# R14 Phase C1B1-R2 — last two fixes only

Read `140_REVIEW_R14_PHASE_C1B1_R1_REJECTED_LAST_CONTROL_RANGE.md` completely.

## Boundaries

- Work directly, no subagents/Task/explorer/delegation.
- No production, network, SSH, systemd, Docker, database, commit or push.
- Do not start C1B2/C2.
- Change only:
  - `scripts/lib/prod-env-tool.py`;
  - `scripts/tests/test-prod-env-runtime.sh`;
  - `scripts/tests/test-prod-env-runtime-mutations.sh` only for duplicate
    contract removal if needed.

## Fix A — exact control predicate

In `deserialize_envfile()` reject exactly:

```text
all code points 0x00..0x1F except LF 0x0A, plus DEL 0x7F
```

Use a simple explicit expression such as:

```python
if (code < 32 and code != 10) or code == 127:
```

The existing specialized safe diagnostics for CR/NUL may remain before it, but
the generic condition must still cover TAB, VT, FF and all other controls.
Change the comment to “except record LF”. Do not alter printable Unicode,
canonical escaping or source values.

Add exact ordinary-harness cases for:

- TAB `0x09`;
- vertical tab `0x0B`;
- form feed `0x0C`.

Each mutates only a non-exact optional/value field inside a canonical generated
profile, returns `14`, does not execute the child and does not leak bytes/value.
Keep existing U+0001/DEL/CR/NUL/invalid-UTF8 cases.

## Fix B — one GRACE contract

Remove the older duplicated module-contract block at the top of
`test-prod-env-runtime-mutations.sh`. Retain exactly:

- one AI header;
- one `START_MODULE_CONTRACT`/`END_MODULE_CONTRACT` pair;
- one `START_MODULE_MAP`/`END_MODULE_MAP` pair.

The retained contract must list the real `sudo` and `strace` test dependencies.
Do not change mutation code or output for this cleanup.

## Required commands

```bash
bash -n scripts/tests/test-prod-env-runtime.sh \
  scripts/tests/test-prod-env-runtime-mutations.sh
python3.12 -I -S -c \
  'compile(open("scripts/lib/prod-env-tool.py", "rb").read(), "scripts/lib/prod-env-tool.py", "exec")'
bash scripts/tests/test-prod-env-runtime.sh
bash scripts/tests/test-prod-env-runtime.sh
bash scripts/tests/test-prod-env-runtime-mutations.sh
sudo -n bash scripts/tests/test-prod-env-runtime-root.sh
bash scripts/tests/test-prod-env-profiles.sh
bash scripts/tests/test-prod-env-install-transaction.sh
bash scripts/tests/test-prod-env-profiles-mutations.sh
sudo -n env TOOL_OVERRIDE=/opt/solarsage-astro/scripts/lib/prod-env-tool.py \
  bash scripts/tests/test-prod-env-root-identity.sh
bash scripts/prod-infra-fingerprint.sh
git diff --check
```

Handoff must state the exact VT/FF/TAB rc, contract/map marker counts and true
test rc. Stop afterward; no C1B2/C2/commit/push.

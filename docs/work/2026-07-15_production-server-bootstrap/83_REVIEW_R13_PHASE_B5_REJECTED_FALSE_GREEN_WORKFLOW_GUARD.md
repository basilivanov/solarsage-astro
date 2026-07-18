# R13 Phase B5 — REJECT: workflow guard remains false-green

## Verdict

`scripts/tests/test-prod-source-readiness-workflow.sh` is **not accepted**.

The bundled harness passes twice with `41/41`, both canonical workflows return `rc=0`, temporary directories are removed, and `git diff --check` is clean. Those green results do not prove the deploy transport contract: independent sandbox mutations of temporary workflow copies exposed multiple release-blocking `rc=0` false-greens.

The canonical content of `.github/workflows/source-readiness.yml` and `.github/workflows/deploy-production.yml` currently contains the intended four steps, exact secret references, pinned SSH options, quoted forced command, and cleanup. The rejection is about the validator/harness proof, not a request to redesign the canonical workflow.

No network, SSH, GitHub Actions, production service, commit, or push was used during independent review.

## P0 false-greens proven with `rc=0`

### 1. Step mappings are not closed

The parser represents a step as `sequence_item`, but duplicate detection is applied only to `mapping` parents. The semantic validator also does not enforce an exact allowed field set per step.

Accepted unsafe mutations include:

- `continue-on-error: true` on the gate or SSH step;
- `shell: python` on Configure SSH;
- a second `run: |` key containing an unsafe command;
- duplicate `if`, `name`, or other step-level keys.

This can make a failed gate/deploy non-fatal or hide a malicious last-wins YAML key behind the safe first key inspected by `find_child`.

### 2. Gate validation is substring-based

The validator does not parse the three guard blocks. It only searches the raw literal body for expected fragments and any later `exit 1`.

Accepted unsafe mutations include:

- `if false && [ "$IS_PRIVATE" != "true" ]; then`;
- `exit 0` before the guard blocks;
- branch/SHA/private guard text moved into comments;
- arbitrary executable `id`/`uname` commands;
- `continue-on-error: true` on the step.

The bundled `MUT08` and `MUT10` are also not valid semantic proofs: they leave a dangling `fi`, and the extracted shell body fails `bash -n` with `rc=2`.

### 3. Configure SSH is presence-based, not an allowlist

The validator checks that several substrings exist and rejects only a small blacklist.

Accepted unsafe mutations include:

- unredirected `printf`/`echo` of `$PROD_SSH_PRIVATE_KEY` or `$PROD_KNOWN_HOSTS`;
- `> key > /dev/stderr`, which leaves the key file empty and exposes the value;
- `2> key`, `>> key`, a second destination, or a later unsafe mode override;
- arbitrary executable `id`;
- direct `${{ secrets.EXTRA_SECRET }}` inside a `run` body.

Current `MUT18_SECRET_LEAK` does not test unredirected secret output. It only duplicates an env reference in another step.

### 4. Secret identity and location are not actually parsed

The validator treats the env key as the secret name and only checks that the value starts with `${{ secrets.`. It does not parse the exact expression and does not scan executable `run` nodes.

Accepted unsafe mutations include:

- `PROD_USER` mapped to `secrets.PROD_HOST` and vice versa;
- private-key and known-hosts expressions swapped;
- an expected env key mapped to `secrets.EXTRA_SECRET`;
- a duplicate secret reference in an earlier step that is overwritten in the collector;
- a secret expression embedded directly in executable shell.

### 5. SSH argv is not exact

Options are accumulated in a dict, so duplicates disappear. Unknown short flags are explicitly skipped by the unknown-option check. Positional arguments and remote command are inferred with overwriting variables and raw substring checks.

Accepted unsafe mutations include:

- extra `-v` or `-F /dev/null`;
- unsafe-first duplicate `StrictHostKeyChecking=no` followed by the canonical value;
- unsafe-first duplicate `UserKnownHostsFile=/dev/null` followed by the canonical value;
- missing raw double quotes around `$PROD_USER@$PROD_HOST`;
- an extra positional argument before destination;
- a wrong real forced command while the expected string exists only in a comment;
- an altered remote argument with extra text;
- missing or replaced `GITHUB_SHA` in the SSH step env.

Local `ssh -G` confirmed that OpenSSH can use the unsafe first duplicate value while the validator retains the safe last value.

### 6. Cleanup is not exact

Cleanup is validated by substring counts plus a short operator blacklist.

Accepted unsafe mutations include:

- `echo rm -f ...`, which deletes nothing;
- deleting an additional path such as `~/.ssh/config`;
- command substitution such as `"$(id)"`;
- redirect/background variants;
- an extra step field such as `continue-on-error`.

## P1 parser and harness failures

- Mixed `space + TAB` structural indentation is accepted.
- YAML anchor, tag, and flow value can be placed in an unchecked scalar and accepted.
- Duplicate keys under step sequence items are not rejected.
- A blank/comment line inside an active backslash continuation is modeled differently from Bash.
- `E_FILE_READ_ERROR`, `E_PARSE_ERROR`, and `E_SUCCESS` are referenced but undefined on exceptional paths.
- Non-numeric SSH option values can cause a traceback and generic `rc=1` instead of a stable symbolic code.
- Diagnostics can include arbitrary rejected scalar/token content; only symbolic code and safe field labels are permitted.
- `MUT29`/`MUT30` inject words into an existing literal body; they do not create the required extra inline/multiline YAML `run` nodes.
- Comment-decoy coverage tests only `permissions`, not gate and SSH options.
- There is no separate known-hosts mode mutation.
- Generic mutation helpers do not prove pre-anchor count exactly one, changed bytes, restricted-subset parse validity, and shell syntax validity.
- `scripts/tests/lib/swap_workflow_steps.py` does not require unique exact step anchors or byte-exact block preservation.
- `scripts/tests/lib/__pycache__/` was left in the repository worktree.

## Required disposition

Do not patch individual false-green examples with more substring blacklists. Replace the implementation with the bounded exact validator described in `84_TZ_R13_PHASE_B5_R1_EXACT_WORKFLOW_DEPLOY_GUARD.md`.

Phase B6 (`prod-deploy.sh` source loader and fingerprint) starts only after this guard is independently accepted. Production launch remains forbidden until the user gives a separate explicit command.

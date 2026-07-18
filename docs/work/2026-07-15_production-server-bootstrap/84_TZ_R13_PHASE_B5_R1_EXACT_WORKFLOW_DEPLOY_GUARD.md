# R13 Phase B5 R1 — exact workflow guard for the production deploy script

## Objective

Replace the current false-green workflow validator/harness with a small fail-closed validator for the **exact restricted subset used by the two production workflows**.

This is the security guard in front of the deployment script. It must prove that GitHub Actions can only invoke the pinned forced command over pinned SSH transport, cannot leak the ephemeral key, cannot continue after a failed gate/SSH call, and always removes both temporary SSH files.

After this task, stop for architect review. Do not start Phase B6 yourself.

## Hard prohibitions

- Do not launch production or any service.
- Do not run real Actions, SSH, GitHub API, network calls, deploy, systemctl, Docker, database commands, or remote commands.
- Do not read or print real secret values.
- Do not commit or push.
- Do not touch frozen/unrelated paths: `.grace/`, `artifacts/design/`, `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`, `grace.db`, `skills/`.
- Do not add PyYAML, yq, actionlint, or any dependency.
- Do not grow a generic YAML/shell parser. Support only the canonical subset needed by these two files and fail closed on everything else.
- Do not fix a false-green by adding another substring blacklist.

## Allowed scope

Only these paths may change:

- `scripts/tests/lib/prod_workflow_validator.py`;
- `scripts/tests/test-prod-source-readiness-workflow.sh`;
- `scripts/tests/lib/swap_workflow_steps.py` — rewrite to the exact byte-slice contract below, or remove it and replace its use with an equally strict test-only helper;
- `.github/workflows/deploy-production.yml` — retain the already-added exact `UserKnownHostsFile=~/.ssh/known_hosts`; no other canonical change unless the new exact validator proves a concrete deviation;
- `.github/workflows/source-readiness.yml` — only for a concrete canonical deviation proven by the validator;
- removal of generated `scripts/tests/lib/__pycache__/` and `*.pyc` artifacts.

Do not edit the review/TZ documents.

## Implementation strategy

Prefer replacing the 900-line implementation with a smaller deterministic model. The validator should have three explicit stages:

1. raw/restricted-YAML validation;
2. exact structural extraction to a minimal AST;
3. exact per-workflow semantic validation.

Every mapping, including every step sequence item, must use the same duplicate-key detection. A step is a mapping, not a special container exempt from duplicate checks.

### CLI modes

Provide stable CLI modes so the harness can distinguish parser proof from semantic proof:

```text
prod_workflow_validator.py FILE readiness
prod_workflow_validator.py FILE deploy
prod_workflow_validator.py FILE parse-only
```

- `parse-only` returns `0` only when the file is valid in the restricted subset and has no duplicate/unsupported construct; it does not require canonical semantics.
- semantic modes return one stable numeric code mapped to one symbolic constant.
- no traceback is allowed for malformed input.
- stderr contains only `SYMBOLIC_CODE: safe structural label`; never echo a body, scalar value, argv token, destination, expression, or secret-like content.

## 1. Raw and restricted-YAML rules

Before semantic parsing:

- decode strict UTF-8;
- require final LF;
- reject NUL and CR anywhere;
- reject a TAB in any structural leading whitespace, including `spaces + TAB`;
- reject YAML anchors, aliases, tags, merge keys, folded blocks, inline comments, block chomping modifiers, and flow collections; exact scalar `{}` is the only allowed flow-like token and only for `permissions: {}`;
- comments and blank lines may be skipped structurally, but comments inside a `run: |` remain literal body text and must never satisfy executable contracts;
- reject unknown indentation transitions and children beneath scalar/empty-map nodes;
- capture `run: |` until the first nonblank physical line with indentation less than or equal to the key indentation;
- strip only the exact common content indentation and preserve physical line boundaries;
- detect duplicate keys at every mapping level: root, trigger, concurrency, jobs, job, step, and env;
- reject any unsupported sequence form. The only sequence is `steps`, and every item begins with exact six-space `      - name: ...` and is parsed as a mapping.

Do not rely on unchecked top-level values to hide unsupported syntax. Raw forbidden-construct scanning applies to all structural lines, including `name`.

## 2. Exact workflow schema

For both workflows:

- top-level keys exactly, in canonical order: `name`, `on`, `concurrency`, `jobs`;
- `on` has exactly one empty child `workflow_dispatch` and no inputs/other event;
- `concurrency` keys exactly `group`, `cancel-in-progress`;
- group exact by type; cancel exact scalar `false`;
- `jobs` has exactly one exact job ID;
- job keys exactly `runs-on`, `timeout-minutes`, `permissions`, `environment`, `steps`;
- `runs-on: ubuntu-latest`;
- `permissions` is the executable empty map `{}`;
- `environment: production`;
- readiness timeout is positive and `<=10` with canonical value `10`; deploy timeout exact `45`;
- exactly four ordered step mappings and exact names from the original TZ.

Reject all extra fields such as `if` on the wrong step, `continue-on-error`, `shell`, `uses`, `working-directory`, `with`, or a second `run/env/name`.

Exact allowed step key sets:

```text
gate:      name, env, run
configure: name, env, run
trigger:   name, env, run
cleanup:   name, if, run
```

## 3. Exact env and secret-reference contract

Parse env mappings as exact key/value pairs, not prefix matches.

Gate env must equal:

```text
GITHUB_REF = ${{ github.ref }}
GITHUB_SHA = ${{ github.sha }}
IS_PRIVATE = ${{ github.event.repository.private }}
```

Configure env must equal:

```text
PROD_SSH_PRIVATE_KEY = ${{ secrets.PROD_SSH_PRIVATE_KEY }}
PROD_KNOWN_HOSTS     = ${{ secrets.PROD_KNOWN_HOSTS }}
```

Trigger env must equal:

```text
PROD_USER  = ${{ secrets.PROD_USER }}
PROD_HOST  = ${{ secrets.PROD_HOST }}
GITHUB_SHA = ${{ github.sha }}
```

Cleanup has no env.

Scan every executable scalar and literal body for `${{ secrets.`. The global exact multiset is four references, each exactly once, and each reference is allowed only as the exact value of its exact env key above. A secret expression in `run`, name, condition, comments, or another env key is rejected.

## 4. Gate body: three real shell guards and nothing else

Parse nonblank physical lines; comment lines are permitted only as inert comments and are excluded before contract matching. They cannot provide required text.

Require exactly three ordered `if ...; then` blocks:

1. exact branch condition: `[ "$GITHUB_REF" != "refs/heads/main" ]`;
2. exact SHA condition: `[[ ! "$GITHUB_SHA" =~ ^[0-9a-f]{40}$ ]]`;
3. exact private condition: `[ "$IS_PRIVATE" != "true" ]`.

Each block must contain:

- at most one generic diagnostic `echo ... >&2` line;
- exact `exit 1`;
- exact closing `fi`.

There are no executable lines before, between, or after those blocks. Reject prefixes such as `false &&`, `true ||`, negation changes, `exit 0`, `:`, command substitution, backticks, `eval`, source/dot commands, subshells, an extra redirect, and any extra command. Echo content is not a guard and must not be used to satisfy a condition.

For any mutation intended to preserve shell syntax, the harness must independently extract the body and prove `bash -n` returns `0` before expecting a semantic code.

## 5. Configure SSH body: exact six-command allowlist

After excluding blank/comment-only lines, require exactly these six commands in this order:

```text
mkdir -p ~/.ssh
chmod 700 ~/.ssh
install -m 600 /dev/null ~/.ssh/solarsage_prod_deploy
printf '%s\n' "$PROD_SSH_PRIVATE_KEY" | tr -d '\r' > ~/.ssh/solarsage_prod_deploy
printf '%s\n' "$PROD_KNOWN_HOSTS" | tr -d '\r' > ~/.ssh/known_hosts
chmod 644 ~/.ssh/known_hosts
```

Use anchored full-line matching for the two deliberately allowed pipelines. Require exact single `>` redirect and exact destination. Reject `>>`, `2>`, multiple redirects, suffix/prefix commands, a second destination, mode override, unredirected output, `tee`, `cat`, `echo`, `env`, `printenv`, `set -x`, `id`, or any seventh command.

Do not execute these lines in the harness with real values. All mutation proof uses syntax/structure and synthetic canaries only.

## 6. Trigger SSH body: exact ordered argv

Build logical lines only from immediate physical backslash continuations. If a blank/comment line occurs while a continuation buffer is active, reject it; Bash does not treat that as a transparent continuation.

Require exactly one logical command. Parse with:

```python
lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>")
lexer.whitespace_split = True
lexer.commenters = ""
```

Require the exact ordered argv, with no dict overwrite and no optional/unknown token:

```text
ssh
-T
-i
~/.ssh/solarsage_prod_deploy
-o
IdentitiesOnly=yes
-o
BatchMode=yes
-o
StrictHostKeyChecking=yes
-o
ConnectTimeout=15
-o
ServerAliveInterval=30
-o
ServerAliveCountMax=3
-o
UserKnownHostsFile=~/.ssh/known_hosts
$PROD_USER@$PROD_HOST
TYPE_SPECIFIC_REMOTE_COMMAND
```

`TYPE_SPECIFIC_REMOTE_COMMAND` means exactly `source-check $GITHUB_SHA` for readiness and exactly `deploy $GITHUB_SHA` for deploy; the vertical bar is not part of either command. Exact ordered argv automatically rejects duplicates, unsafe-first values, `-v`, `-F`, extra positionals, and extra remote argv.

Separately match the reconstructed raw logical command with an anchored pattern proving exact double quotes around both `"$PROD_USER@$PROD_HOST"` and the type-specific remote command. No expected command string in a comment may satisfy this check.

Reject every shell punctuation token, command substitution, backticks, prefix/suffix, second logical line, and dangling continuation. Catch all shlex/value errors and map them to a stable symbolic code without including the rejected token.

## 7. Cleanup body: exact argv

Require exact `if: always()` and no other step field.

After excluding blank/comment-only lines, require one logical line. Reject shell punctuation, redirection, backgrounding, substitution, backticks, globbing, or extra path. `shlex` argv must equal exactly:

```text
["rm", "-f", "~/.ssh/solarsage_prod_deploy", "~/.ssh/known_hosts"]
```

`echo rm ...`, an additional destination, or an output redirect must fail.

## 8. Swap helper exactness

If `swap_workflow_steps.py` remains:

- read/write bytes and require final LF;
- find exact byte starts `b"      - name: Verify branch and SHA\n"` and `b"      - name: Configure SSH\n"`;
- each anchor occurs exactly once;
- determine each block end at the next exact six-space step anchor or end of steps block;
- require nonempty, ordered, non-overlapping slices;
- swap byte slices without changing bytes inside either block;
- prove output differs from input;
- prove both original blocks are present byte-exactly exactly once after swap;
- prove each exact step anchor occurs exactly once;
- reject duplicates and literal-body decoys.

Otherwise remove the helper and implement the same byte assertions in a test-only mutation helper.

## 9. Mandatory mutation matrix

Keep stable case IDs and an exact manifest of tuples:

```text
case_id | workflow_type | expected_symbolic_code | expected_numeric_code
```

For every semantic mutation:

1. prove the source anchor count is exactly one;
2. apply the mutation in `$TEST_DIR` only;
3. prove bytes changed;
4. prove the intended postcondition exactly;
5. run `parse-only` and require `rc=0`;
6. when it is a shell-semantic case, require extracted body `bash -n rc=0`;
7. run semantic validation and require the exact symbolic/numeric code.

Parser-error cases deliberately skip semantic parse validity and require their exact parser code.

At minimum cover the original matrix from `65_TZ...` plus these previously false-green cases:

- `continue-on-error` on gate and SSH step;
- extra/duplicate step key: second `run`, duplicate `if`, and `shell` override;
- valid `false &&` private-gate bypass;
- all real gate blocks removed with complete shell-valid block removal plus comment decoys;
- extra generic gate command that is not on a word blacklist;
- exact env value swap and missing SSH-step `GITHUB_SHA`;
- direct secret expression in `run`;
- actual unredirected output for private key and known_hosts;
- unsafe redirect variants and extra Configure SSH command;
- key mode override and known_hosts mode override as separate cases;
- extra `-v`, extra `-F`, duplicate `-T`, unsafe-first duplicate strict-host-key and known-hosts options;
- unquoted destination, extra positional argv, wrong remote command with expected comment decoy;
- comment/blank inside backslash continuation;
- cleanup `echo`-only, extra path, substitution, redirect/background, and extra step field;
- mixed `space + TAB`, anchor, alias, tag, flow collection, folded block;
- duplicate top-level key and duplicate step-level key;
- separate comment decoys for permission, gate, and SSH option;
- real extra fifth inline `run` step, real extra fifth multiline `run: |` step, and real extra `uses` step, not merely forbidden words inserted into an existing body;
- deploy-specific missing `UserKnownHostsFile`, wrong forced command, and SSH `continue-on-error`.

Do not optimize for a particular case count. Optimize for exact contract proof and a readable manifest.

## 10. GRACE and generated artifacts

- Add complete `AI_HEADER`, `START_MODULE_CONTRACT`, and `START_MODULE_MAP` to both Python helper files.
- Add `START_FUNCTION_CONTRACT` for nontrivial public/internal parser and validator functions.
- Contract `emitted_logs` is `none`; these tools must not log workflow bodies or secrets.
- Remove `scripts/tests/lib/__pycache__/` and all repo-local `*.pyc`.
- Compile with `PYTHONPYCACHEPREFIX` pointing to `/tmp` so the artifact does not return.

## 11. Required coder verification

Run exactly from `/opt/solarsage-astro`:

```bash
bash -n scripts/tests/test-prod-source-readiness-workflow.sh
PYTHONPYCACHEPREFIX=/tmp/solarsage-r13-pycache python3.12 -m py_compile \
  scripts/tests/lib/prod_workflow_validator.py \
  scripts/tests/lib/swap_workflow_steps.py
timeout 180 bash scripts/tests/test-prod-source-readiness-workflow.sh
timeout 180 bash scripts/tests/test-prod-source-readiness-workflow.sh
find /tmp -maxdepth 1 -type d -name 'solarsage-r13-workflow-test.*' -print
find scripts/tests/lib -type d -name '__pycache__' -o -type f -name '*.pyc'
git diff --check
```

If the swap helper is removed, omit it from `py_compile` and prove the file is no longer referenced.

Expected:

- every command returns `rc=0` except that both `find` commands print nothing;
- both harness runs report the identical exact manifest/count;
- no traceback;
- no secret/body/token value in diagnostics;
- no network, Actions, SSH, production, commit, or push.

## Handoff

Report:

- exact files changed/removed;
- validator line count and why its scope is bounded;
- exact canonical count plus mutation count;
- exact manifest equality result;
- both run results and rc;
- proof repo-local pycache is absent;
- confirmation that production/network/SSH/GitHub/commit/push were not used.

Then stop and wait for independent architect review.

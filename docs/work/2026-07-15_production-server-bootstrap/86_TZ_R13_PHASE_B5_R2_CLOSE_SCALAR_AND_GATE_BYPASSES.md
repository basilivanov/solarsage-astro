# R13 Phase B5 R2 — close scalar-node, gate, parser, and mutation-proof gaps

## Objective

Make the existing bounded workflow validator fail closed for every security-critical node type and close the concrete `rc=0` bypasses documented in `85_REVIEW...`.

This is a targeted correction, not another generic parser rewrite. Preserve the exact ordered Configure SSH, SSH argv, and cleanup models that already work. After verification, stop for architect review.

## Prohibitions and scope

All prohibitions from `84_TZ...` remain active: no production, service launch, network, SSH, Actions, GitHub API, Docker, database, secret reads, commit, or push.

Allowed changes only:

- `scripts/tests/lib/prod_workflow_validator.py`;
- `scripts/tests/lib/swap_workflow_steps.py` only if an acceptance case proves a helper defect;
- `scripts/tests/test-prod-source-readiness-workflow.sh`;
- removal of generated `scripts/tests/lib/__pycache__/`/`*.pyc`.

Do not change either canonical workflow in this R2 task. Do not touch frozen/unrelated paths or review/TZ documents.

## 1. Required node-type assertions

Never use `if node and isinstance(node.val, list): validate...` without an `else` failure.

Before reading children, assert exact node type:

```text
root                         mapping
name                         scalar
on                           mapping
on.workflow_dispatch         mapping with zero executable children
concurrency                  mapping
jobs                         mapping
single job                   mapping
job.permissions              empty_map
job.steps                    mapping/container holding the supported sequence
each step                    sequence_item mapping
each env                     mapping
gate.run                     literal
configure.run                literal
trigger.run                  literal
cleanup.if                   scalar
cleanup.run                  literal
```

Wrong type gets a dedicated stable semantic code or the closest existing structural code. It must never fall through.

Required independent behavior:

- `on: workflow_dispatch` — nonzero;
- `workflow_dispatch: true` — nonzero;
- `workflow_dispatch` with `inputs` child — nonzero;
- `concurrency: ignored` — nonzero;
- scalar `run` on each of the four steps — nonzero;
- scalar `run` containing `${{ secrets.* }}` — nonzero before any possible execution.

Add an exact helper such as `_require_type(node, expected_type, code, safe_label)` to avoid repeating fall-through bugs.

## 2. Positive timeout

Readiness timeout must be an ASCII decimal integer satisfying:

```text
1 <= timeout <= 10
```

Deploy remains exact `45`. `0`, signs, spaces, floats, booleans, and non-digits fail with stable `E_TIMEOUT` and no rejected value in stderr.

## 3. Gate lines must match fully, not by substring

After comment/blank removal, require these exact full condition lines in exact order:

```bash
if [ "$GITHUB_REF" != "refs/heads/main" ]; then
if [[ ! "$GITHUB_SHA" =~ ^[0-9a-f]{40}$ ]]; then
if [ "$IS_PRIVATE" != "true" ]; then
```

Compare the whole line with equality. Reject every prefix/suffix, including:

- `false && ...`;
- `... && false`;
- `... || true`;
- a second condition;
- extra redirect/operator;
- text after `then`;
- comments appended to the condition.

Each block remains exact ordered `if`, optional diagnostic, `exit 1`, `fi`.

### Diagnostic line contract

If a diagnostic exists, it must satisfy all of these:

- exact shape `echo "..." >&2`;
- no `$(`, backtick, `${{`, semicolon, pipe, `<`, newline escape, `eval`, `source`, or dot-command;
- no `&&`, `||`, standalone `&`, or additional redirect;
- the only permitted output redirect is the final exact `>&2`;
- it cannot satisfy any guard requirement.

The canonical `$GITHUB_REF` text inside its branch diagnostic remains allowed as ordinary double-quoted variable expansion. Do not allow command substitution.

## 4. Secret scan covers the complete executable AST

Perform a recursive scan over every parsed scalar and literal node, with known structural location.

Rules:

- every occurrence matching `${{ secrets.` must parse as the exact whole expression `${{ secrets.NAME }}`;
- the exact total occurrence count is four;
- exact `(location, env key, secret name)` tuples are the four canonical env values;
- no occurrence in top-level name, step name, `if`, scalar/literal `run`, comments inside a literal, concurrency, or another scalar;
- no duplicate expected reference at another location;
- no dynamic/indexed/malformed expression.

Run this scan immediately after structural parsing/type validation and before body-specific validation so a direct secret in any `run` returns stable `E_SECRET_REF`.

## 5. Restricted parser corrections

- Reject YAML tag indicators in structural values: `!foo`, `!!str`, `!<...>`, and any other unquoted tag spelling.
- Reject aliases, anchors, merge keys, folded blocks, flow collections, and inline comments on structural lines.
- Inline comment detection must understand the narrow canonical quoted scalars and reject a real unquoted ` #`; do not reject `#` inside a quoted scalar.
- Preserve blank physical lines in a literal block. A blank line does not end the block; stop only at the next **nonblank** line with indent less than or equal to the literal key.
- Reject a TAB in any structural leading whitespace, including spaces followed by TAB.
- Reject children below scalar/empty-map nodes and unknown indentation transitions.
- Catch file open/read errors and return a stable symbolic file code without traceback.

Do not accept a construct merely because its scalar is currently semantically ignored.

## 6. Stable safe diagnostics

Create a fixed mapping from numeric code to symbolic name. `_fail` prints exactly once:

```text
E_SYMBOLIC_CODE: safe_label
```

Requirements:

- no workflow body, rejected scalar, argv list/token, destination, expression, path argument supplied by the file, or secret-like canary;
- `safe_label` comes from a fixed allowlist such as `gate.condition.private`, `ssh.argv`, `cleanup.argv`, not from parsed content;
- no traceback for any malformed input;
- first failure wins and only one line is emitted.

Remove all dynamic f-string diagnostics that include `tm`, actual step name, key sets, argv, trigger list, job ID, operator, or rejected text.

The harness must capture stderr and assert both exact numeric rc and exact symbolic prefix for every case. Do not discard stderr.

## 7. Mandatory R2 mutation additions

Keep all currently passing cases and add the following exact cases. Every semantic fixture must pass `parse-only`; parser-error fixtures require their exact parser code.

### Node types and timeout

- scalar `on`;
- scalar `workflow_dispatch`;
- nonempty `workflow_dispatch` child;
- scalar `concurrency`;
- timeout `0`;
- scalar gate `run`;
- scalar Configure SSH `run`;
- scalar trigger `run`;
- scalar cleanup `run`;
- scalar `run` containing a secret expression.

### Gate

- private condition suffix `&& false`;
- branch condition suffix `&& false`;
- diagnostic `echo "$(id)" >&2`;
- diagnostic with backticks;
- guard text only in a comment while the full block is removed;
- extra generic executable command.

All shell-semantic gate fixtures must be `bash -n rc=0` before semantic validation.

### Secret/configure boundary

- missing trigger `GITHUB_SHA`;
- env key mapped to the wrong exact secret;
- direct secret in scalar and literal run;
- unredirected private key and known_hosts separately;
- `>>`, `2>`, and second-destination redirect representative cases;
- extra Configure SSH command `id`;
- key mode override and known-hosts mode override as separate cases.

### SSH argv and step fields

- `continue-on-error: true` on SSH step for readiness and deploy;
- duplicate cleanup `if` parser case;
- extra `-F /dev/null`;
- duplicate `-T`;
- unsafe-first duplicate `StrictHostKeyChecking=no`;
- unsafe-first duplicate `UserKnownHostsFile=/dev/null`;
- extra positional argv before destination;
- wrong real remote command with expected command only in a comment;
- blank line and comment line inside an active continuation as separate cases.

### Cleanup

- `echo rm -f ...`;
- extra path;
- command substitution;
- output redirect;
- background `&`;
- `continue-on-error: true` on cleanup step.

### Restricted YAML and decoys

- alias;
- tag `!foo`;
- tag `!!str`;
- folded block;
- structural inline comment;
- gate comment decoy;
- SSH option comment decoy.

### Deploy-specific

- wrong deploy forced command;
- expected deploy command only in a comment;
- deploy SSH `continue-on-error`.

## 8. Mutation proof and manifest

No `true`, `:` or other unconditional postcondition is permitted.

Every mutation must prove:

1. exact source anchor count `1`;
2. exact mutation application count `1`;
3. changed bytes;
4. exact postcondition count/value;
5. `parse-only rc=0` for semantic cases;
6. `bash -n rc=0` for shell-semantic gate cases;
7. exact numeric rc;
8. exact symbolic stderr prefix and one-line diagnostic.

The manifest must contain and compare sorted exact tuples:

```text
case_id|workflow_type|symbolic_code|numeric_code
```

Duplicate/missing/extra tuples fail the harness.

## 9. GRACE

Add complete `START_MODULE_CONTRACT` and `START_MODULE_MAP` blocks to both Python helpers. Add `START_FUNCTION_CONTRACT` to nontrivial parser/validator/helper functions. `emitted_logs: none`; these test tools emit only sanitized validation diagnostics.

Do not rewrite unrelated old files merely for GRACE.

## 10. Required verification

From `/opt/solarsage-astro`:

```bash
bash -n scripts/tests/test-prod-source-readiness-workflow.sh
PYTHONPYCACHEPREFIX=/tmp/solarsage-r13-r2-pycache python3.12 -m py_compile \
  scripts/tests/lib/prod_workflow_validator.py \
  scripts/tests/lib/swap_workflow_steps.py
python3.12 scripts/tests/lib/prod_workflow_validator.py .github/workflows/source-readiness.yml readiness
python3.12 scripts/tests/lib/prod_workflow_validator.py .github/workflows/deploy-production.yml deploy
timeout 240 bash scripts/tests/test-prod-source-readiness-workflow.sh
timeout 240 bash scripts/tests/test-prod-source-readiness-workflow.sh
find /tmp -maxdepth 1 -type d -name 'solarsage-r13-workflow-test.*' -print
find scripts/tests/lib -type d -name '__pycache__' -o -type f -name '*.pyc'
git diff --check
```

Both harness runs must have identical counts/manifest and `rc=0`; both `find` commands print nothing. No traceback, secret-like diagnostic, network, SSH, Actions, production, commit, or push.

## Handoff

Report exact files, validator/harness line counts, canonical count, semantic mutation count, parser mutation count, exact manifest equality, both run results, diagnostic self-test result, clean temp/pycache proof, and forbidden-action confirmation. Then stop.

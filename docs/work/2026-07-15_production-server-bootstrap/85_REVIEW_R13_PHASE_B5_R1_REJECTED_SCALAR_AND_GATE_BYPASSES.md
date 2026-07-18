# R13 Phase B5 R1 — REJECT: scalar-run and gate bypasses remain

## Verdict

The R1 workflow guard is **not accepted**.

Independent baseline:

- `bash -n` — `rc=0`;
- Python compile through `/tmp` — `rc=0`;
- canonical source-readiness — `rc=0`;
- canonical deploy — `rc=0`;
- bundled harness run 1 — `52/52`, `rc=0`;
- bundled harness run 2 — `52/52`, `rc=0`;
- harness stderr — empty;
- no leftover workflow temp directories or repo-local pycache;
- `git diff --check` — clean.

Despite that baseline, independent temporary mutations expose release-blocking `rc=0` false-greens. No repository mutation, network, SSH, GitHub Actions, production action, commit, or push was used by the review.

## P0 false-greens independently reproduced

All cases below returned validator `rc=0`.

### Structural nodes are only checked when they happen to be mappings

- `on: workflow_dispatch` as a scalar;
- `workflow_dispatch: true` instead of an empty mapping;
- `concurrency: ignored` as a scalar.

The validator conditionally validates these blocks only when `node.val` is a list. Wrong node types fall through without an error.

### Every security-critical `run` can be changed to a scalar and skipped

The step key set still contains `run`, but semantic body validation executes only when `run.type == "literal"`. A scalar silently bypasses the body contract.

Accepted `rc=0` mutations:

- gate body replaced by `run: echo bypass`;
- gate body replaced by `run: echo ${{ secrets.PROD_SSH_PRIVATE_KEY }}`;
- Configure SSH replaced by `run: echo not-configuring-ssh`;
- forced-command SSH trigger replaced by `run: echo not-calling-forced-command`;
- cleanup replaced by `run: echo not-cleaning`.

This simultaneously bypasses gate, secret-in-run scan, exact Configure SSH allowlist, exact SSH argv, forced command, and cleanup.

### Gate condition is still substring-based

The private guard changed to:

```bash
if [ "$IS_PRIVATE" != "true" ] && false; then
```

returned `rc=0`. The expected condition is present as a substring and the line starts with `if [`, but the real guard can never enter its failure branch.

### Gate diagnostic permits command execution

Replacing a diagnostic with:

```bash
echo "$(id)" >&2
```

returned `rc=0`. The optional diagnostic rule checks only `startswith("echo")` and presence of `>&2`; command substitution, backticks, operators, and extra execution are not rejected.

### Positive timeout is not enforced

`timeout-minutes: 0` returned `rc=0`; the readiness check rejects only values greater than ten.

## P1 parser and diagnostics gaps

- `name: !foo Source Readiness Check` returned `rc=0`; tag detection only looks for selected `!` spellings.
- An inline structural comment on top-level `name` returned `rc=0`, although inline comments are outside the restricted subset.
- `_fail()` records a numeric code but prints nothing. Independent failure output therefore cannot contain the required stable symbolic code and safe structural label.
- Several `_fail` call sites build messages from rejected values/argv. If printing is restored naively, diagnostics can leak synthetic canaries or secret-like rejected tokens.
- Read errors are not caught around `open(...).read()`.
- Literal capture stops on an unindented blank line instead of preserving blank physical lines until the next nonblank dedent.
- Module/function GRACE contracts required by `AGENTS.md` are incomplete or absent in the new Python files.

## Harness does not implement the mandatory R1 matrix

The current 52 cases omit multiple explicit requirements from `84_TZ...`, including representative cases for:

- scalar wrong types for `on`, `workflow_dispatch`, `concurrency`, and all four `run` nodes;
- positive timeout zero;
- guard suffix bypass and diagnostic command substitution;
- SSH-step `continue-on-error`, duplicate `if`, and missing trigger `GITHUB_SHA`;
- unsafe redirect variants, extra Configure SSH command, and separate known-hosts mode override;
- `-F`, duplicate `-T`, unsafe-first duplicate SSH options, extra positional argv, wrong real remote command with comment decoy;
- blank/comment inside continuation;
- cleanup echo-only, extra path, substitution, redirect/background, and extra step field;
- YAML alias, tag, folded block, and inline comment;
- separate comment decoys for gate and SSH option;
- deploy wrong forced command and deploy SSH `continue-on-error`.

The manifest records only IDs, not the required tuple `(case_id, workflow_type, symbolic_code, numeric_code)`.

## Required disposition

Apply the bounded R2 corrections in `86_TZ_R13_PHASE_B5_R2_CLOSE_SCALAR_AND_GATE_BYPASSES.md`. Do not proceed to Phase B6 until independent acceptance.

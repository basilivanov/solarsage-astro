# TZ R14 Phase C2 — promotion/rollback authority integration and safe GC

## Read first

Read completely before editing:

- repository `AGENTS.md`;
- `146_TZ_R14_PHASE_C2_IMMUTABLE_PROMOTION_AND_FULL_PROD_READINESS_HANDOFF.md`;
- `151_REVIEW_R14_PHASE_C2_POINTER_CANONICALIZATION_ACCEPTED_INDEPENDENT.md`;
- `152_ARCH_R14_PHASE_C2_PRIVILEGED_RELEASE_AUTHORITY.md`;
- `159_ARCH_R14_PHASE_C2_STICKY_RELEASE_STAGING_AND_FINALIZATION.md`;
- `163_REVIEW_R14_PHASE_C2_FINALIZE_ACCEPTED_INDEPENDENT.md`;
- `169_REVIEW_R14_DEPLOY_NAMESPACE_REFACTOR_ACCEPTED_INDEPENDENT.md`;
- `170_ARCH_R14_PHASE_C2_PROMOTION_AUTHORITY_AND_GC.md`.

Use only canonical paths under `scripts/deploy/`. Historical documents contain pre-refactor `scripts/...` paths; do not recreate them.

## Scope

Implement only promotion/rollback/GC integration with the accepted privileged authority and add `gc-remove`. Do not start backup/restore, async deploy control plane, host installation, Nginx maintenance routing or production rollout in this slice.

Primary allowed files:

- `scripts/deploy/lib/prod-release-promotion.sh`;
- `scripts/deploy/prod-release-authority.py`;
- `scripts/deploy/tests/test-prod-release-promotion.sh`;
- `scripts/deploy/tests/test-prod-release-pointer-contract.sh` only for necessary exact-count/substitution updates;
- `scripts/deploy/tests/test-prod-release-authority.sh` only for the now-implemented argv contract and shared fixture adjustments;
- new focused `scripts/deploy/tests/test-prod-release-promotion-authority.sh`;
- new focused `scripts/deploy/tests/test-prod-release-gc-authority.sh`;
- `scripts/deploy/prod-release-promote.sh` only if the library contract strictly requires it;
- `scripts/deploy/tests/run-deploy-matrix.sh`, `scripts/deploy/README.md` and namespace test expectations only as mechanically required for the two new suites;
- one implementation report in this work directory.

Do not modify accepted env/profile, source, builder, manifest, finalize, maintenance foundation or unrelated product files unless a concrete compile/test blocker proves a narrow compatibility edit necessary. Stop and report before widening scope.

## Required production changes

### 1. One authority bridge

Replace all direct privileged filesystem/Git operations in the promotion library with one internal GRACE-contracted bridge whose production command is exactly:

```bash
/usr/bin/sudo -n -- /usr/local/libexec/solarsage/release-authority "$@"
```

Required operations: `switch-pointer`, `remove-pointer`, `maintenance-on`, `maintenance-off`, `gc-remove`.

Remove `_prod_prm_python_switch`, `_prod_prm_create_flag`, `_prod_prm_delete_flag`, direct pointer `rm`, direct `git`, `rev-parse`, and direct worktree removal. `/usr/bin/systemctl` restart and `/usr/bin/curl` health remain the coordinator's existing enumerated capabilities.

### 2. Exact transaction snapshot and reconciliation

Implement small internal helpers, not duplicated branches, for:

- reading an optional canonical pointer while distinguishing absent from malformed;
- proving both pointers equal an expected snapshot;
- switching/removing one pointer through authority and post-verifying it;
- restoring the exact pre-operation pair with every return checked;
- validating the authority-owned maintenance flag state;
- marking `recovery_class=recovery_required` without swallowing a write failure.

Treat non-zero authority rc as outcome unknown. Re-read state even after failure. No branch may assume a failed helper did not mutate.

Promotion and explicit rollback must satisfy ARCH 170 ordering and symmetry. On safe restoration after an operation failure, persist the safe terminal phase, prove maintenance-off and return the operation's non-zero rc. On any uncertain restoration, keep/prove maintenance mode, persist recovery required and return non-zero.

Persist `services_switching` before pointer mutation and `health_verified` before opening traffic. Do not claim success until `completed` is durable and maintenance-off is proven.

### 3. First-install activation failure

Add a named case where first installation reaches service restart/health and fails. It must return non-zero, never report successful rollback, retain a valid maintenance flag and persist `recovery_required`, even if pointer removal succeeds. Assert exact pointer state and service-call order.

### 4. Maintenance flag cutover

Use only `/run/solarsage/maintenance`, root:root `0644`, through authority. Durable `active.json` remains under `/var/lib/solarsage/maintenance`.

Cover at least:

- maintenance-on failure before and after mock mutation;
- maintenance-off failure before and after mock mutation;
- malformed flag metadata/type;
- flag retained for recovery-required paths;
- flag absent only on proven success or proven safe restore.

### 5. Implement `gc-remove <sha>` in authority

Follow ARCH 170 exactly. Reuse the accepted isolated subprocess/error boundary and complete finalized-release proof. Add small reusable pointer/registry parsing helpers rather than copying finalize parsing.

The authority must independently protect current, previous, running request and the deterministic two newest finalized releases. It must bind to the fixed source repo, require exact registered path/HEAD/detached status, invoke only exact `git worktree remove --force`, prove filesystem and registry absence, and fsync. No raw recursive deletion.

Preserve `finalize-release`, pointer and flag behavior. Update module contracts/maps to remove the obsolete statement that GC is unimplemented.

### 6. Coordinator GC

Make running-request validation fail closed with canonical `astro:astro 0700` directory and `astro:astro 0600` regular files containing one exact SHA. Missing/invalid/unreadable entries make GC non-zero before deletion.

Select only complete finalized releases, protect current/previous/requested SHAs, retain the deterministic two newest, and invoke authority for each older eligible SHA. Stop on the first authority failure. Increment/report deletion count only after rc `0` and local absence proof.

No caller-cwd Git discovery or direct Git command may remain in the promotion library.

## Focused harness requirements

### `test-prod-release-promotion-authority.sh`

Use a sandbox authority mock with an exact argv ledger and controllable failure points before and after mutation. Required named cases include:

- normal promotion exact authority order and no direct mutator;
- previous switch failure before mutation with exact safe snapshot restore;
- current switch failure after mutation with exact pair restore;
- restore operation failure -> recovery required + flag retained;
- health failure restores old pair, restarts old exact SHA and safely removes flag;
- first-install health failure is recovery required;
- maintenance-on/off uncertain outcomes;
- explicit rollback has the same restoration guarantees;
- GC calls only `gc-remove <sha>`, stops on failure and never false-increments count.

Add external mutation self-proofs for at least the exact-pair reconciliation guard, first-install recovery-required rule and GC deleted-count/post-absence guard. Each mutation uses exact 1→0 anchor proof, `bash -n`, green baseline oracle and non-zero mutant oracle.

### `test-prod-release-gc-authority.sh`

Exercise the actual substituted Python helper with mock Git and no real paths. Required named cases include:

- exact argv/format rejection;
- eligible old finalized worktree success with exact list/remove/list argv and absence proofs;
- current, previous and running-request target rejection;
- target among deterministic newest two rejection, including equal-mtime SHA tie ordering;
- malformed/missing request registry, wrong owner/mode/type/content, symlink entry;
- malformed pointer, invalid/unfinalized target, unknown releases entry;
- missing/duplicate/unregistered registry block, HEAD mismatch, non-detached block;
- list/remove/post-list failure and filesystem-residue failure;
- fsync/error boundary fixed rc `78`, one safe line, no traceback/path leakage;
- mutation self-proofs for protected pointer, running request, newest-two and post-removal registry/absence guards.

Do not append these blocks to the 1400-line authority harness. Keep each new focused suite deterministic with an execution ledger.

## Regression and static gates

- Exact-count substitutions must cover the installed helper, `/run` flag, runtime roots, request registry, sudo, Git, curl and systemctl; post-counts for real production anchors are zero in executable sandbox copies.
- No test invokes real sudo/Git/systemctl/curl or changes real `/opt`, `/run`, `/var/lib`.
- No unchecked `|| true`, ignored authority rc or direct pointer/flag delete on recovery paths.
- No reasoning/debug residue (`Wait`, `Let's`, `Ah`, `we can`, `we should`) in changed production/tests.
- New files have complete GRACE headers/contracts/maps and are included in README canonical inventory/compatibility map plus the deployment matrix.
- Preserve the dirty worktree; no reset/restore/checkout, commit or push.

Run changed focused suites twice and prove byte-identical output:

```bash
bash -n \
  scripts/deploy/lib/prod-release-promotion.sh \
  scripts/deploy/prod-release-promote.sh \
  scripts/deploy/tests/test-prod-release-promotion.sh \
  scripts/deploy/tests/test-prod-release-pointer-contract.sh \
  scripts/deploy/tests/test-prod-release-authority.sh \
  scripts/deploy/tests/test-prod-release-promotion-authority.sh \
  scripts/deploy/tests/test-prod-release-gc-authority.sh

python3.12 -I -S -m py_compile scripts/deploy/prod-release-authority.py

timeout 240 bash scripts/deploy/tests/test-prod-release-authority.sh
timeout 240 bash scripts/deploy/tests/test-prod-release-promotion.sh
timeout 240 bash scripts/deploy/tests/test-prod-release-pointer-contract.sh
timeout 240 bash scripts/deploy/tests/test-prod-release-promotion-authority.sh
timeout 240 bash scripts/deploy/tests/test-prod-release-gc-authority.sh
timeout 240 bash scripts/deploy/tests/test-prod-release-build.sh
timeout 240 bash scripts/deploy/tests/test-prod-release-pinning.sh
bash scripts/deploy/tests/test-prod-namespace-layout.sh
bash scripts/deploy/tests/test-prod-legacy-root-discovery.sh
bash scripts/deploy/tests/run-deploy-matrix.sh
```

The matrix runner already executes its suite inventory twice and compares canonical transcripts; one successful invocation is required after the focused deterministic runs.

## Stop condition

Write an implementation report with exact changed files, case ledgers, raw exit codes, deterministic-output evidence, mutation results and explicit non-actions. Then stop for independent review.

No real helper invocation/install, pointer/flag/worktree mutation, sudoers apply, systemd/nginx/database operation, deploy, commit or push.

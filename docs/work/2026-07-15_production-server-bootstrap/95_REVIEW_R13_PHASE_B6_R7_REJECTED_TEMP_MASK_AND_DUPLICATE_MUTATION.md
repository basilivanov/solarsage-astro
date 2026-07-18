# R13 Phase B6 R7 — rejected: mutation temp leak is masked

## Verdict

The `111/111` handoff is not accepted. Static review found a deliberate
false-green cleanup in the common mutation runner, a duplicate checkout
mutation, and a signal self-test that still does not exercise the real traps.

## 1. Mutation runner masks temp leaks

`check_loader_mutation` currently says that wrapper temp leftovers are not a
test failure and deletes them with `find ... -exec rm` before returning PASS.
This violates the per-case fail-closed contract.

The observed leftover is caused by `MUT10`: the mutated wrapper runs two clean
source checks and leaves multiple `untracked.*` files. Cleanup uses:

```bash
rm -f "$LEFTOVERS"
```

where `LEFTOVERS` is a newline-separated list. Quoting the whole list creates
one nonexistent pathname, so the files survive into later mutation cases. The
generic mutation runner then silently removes them.

Required fix:

- `MUT10` must clean its intentional leftovers with safe iteration or
  `find ... -exec rm -f -- {} +` after proving their exact presence;
- every subsequent common runner must assert zero pre-existing leftovers before
  starting and zero new leftovers after finishing;
- never convert a temp leak into PASS by deleting it inside the assertion;
- fingerprint temp and clean-source temp leaks remain test failures.

## 2. MUT20 and MUT21 are duplicates

Both currently replace:

```bash
git rev-parse origin/main
```

with `origin/bad`. One is labelled wrong ref and the other wrong target SHA, but
they execute the same mutation.

Required distinct proofs:

- wrong ref: `rev-parse origin/bad`, mock rejects exact ref;
- wrong checkout argv/target: keep valid `origin/main` resolution, then invoke
  checkout with an independently wrong 40-hex value or wrong argv shape;
- OLD_SHA semantic mutation remains separate;
- each mutation must assert the exact attempted audit record and the expected
  stop stage, not only rc 1.

## 3. Signal proof remains tautological

`SIGCLEAN` starts a child, manually kills its holder and manually removes its
directory. It does not send HUP/INT/TERM to the actual harness signal handlers
and does not assert exit codes 129/130/143.

Implement an isolated test-only harness mode or equivalent that runs the real
`lock_cleanup` plus installed traps. Parent must send each signal and assert:

- exact exit code;
- holder process no longer alive;
- that invocation's exact private directory removed;
- no raw/global cleanup of another concurrent harness directory.

The current global `ls /tmp/solarsage-deploy-source-loader-test.*` inside
`lock_cleanup` is concurrency-unsafe and only prints FAIL without changing rc.
Remove it; verify the exact invocation directory from the parent proof instead.

## 4. Contract drift

Header/module/section comments still say 16 mutations while the manifest has
MUT01 through MUT22. Update all contract counts and descriptions.

## Completion

After these changes, run two full unfiltered harness executions, confirm no
stale directories, and rerun the two independent adversarial mutations from
`94_REVIEW...` plus a mutation that removes temp cleanup.

No production deploy, commit or push.

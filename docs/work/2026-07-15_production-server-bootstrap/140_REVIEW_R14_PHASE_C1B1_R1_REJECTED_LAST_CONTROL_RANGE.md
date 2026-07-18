# R14 Phase C1B1-R1 — independent review rejected on last two gaps

## Verdict

The first corrective pass fixed the important lock hang, invalid UTF-8 path,
hostile wrapper PATH and real root mutation execution. C1B1 is still **not yet
accepted** because one control-byte range remains wrong and the new mutation
harness has a duplicated GRACE contract block.

No C1B2/C2, production action, commit or push occurred.

## Independently confirmed fixes

```text
FIFO .profile.lock probe                         rc=14 (previously timeout 124)
mutation harness invoked as astro               rc=0
MUT12 output                                     real sudo root oracle marker present
hostile PATH wrapper oracle                      PASS
invalid UTF-8/U+0001/DEL/CR/NUL harness rows     PASS
```

## Remaining blocker 1 — VT and FF are still accepted

The new predicate in `deserialize_envfile()` is:

```python
if (code < 10 or code > 13) and code < 32 or code == 127:
```

It unintentionally permits ASCII vertical tab `0x0B` and form feed `0x0C`.
Independent synthetic probes placed each byte only inside the otherwise valid
`CORS_ALLOWED_ORIGINS` value:

```text
VT 0x0B → run-installed rc=0, child executed
FF 0x0C → run-installed rc=0, child executed
```

C1B1 requires every ASCII control except record LF to be rejected before child
exec. Replace the range expression with an unambiguous exact predicate and add
VT/FF regression rows. Update the stale “except LF/TAB” comment to the actual
contract.

## Remaining blocker 2 — duplicate module contract

`scripts/tests/test-prod-env-runtime-mutations.sh` contains two consecutive
`START_MODULE_CONTRACT`/`END_MODULE_CONTRACT` blocks with the same ID. Keep one
complete contract (including `sudo`/`strace` dependencies) and one module map.
This is a structural GRACE cleanup only; do not change mutation semantics.

## Next action

Perform only `141_TZ_R14_PHASE_C1B1_R2_LAST_TWO_FIXES.md`, run the bounded
regression set, hand off and stop. Do not start C1B2/C2 or commit/push.

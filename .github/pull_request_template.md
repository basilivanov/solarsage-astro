<!--
Grace wave-gate PR template.
Every box below MUST be checked before merge. CI enforces them mechanically;
this template makes the contract visible to humans during review.
-->

## Wave / Packet

- Wave: <!-- e.g. W-1.1 -->
- Packet: `grace/packets/W-1.1.md`
- Modules touched: <!-- e.g. M-API-BOOT, M-DB-SESSION, M-CONFIG -->

## Summary

<!-- 2–4 sentences: what changed and why. -->

## Allowed Write Scope compliance

- [ ] All modified files are listed in the packet's **Allowed Write Scope**.
- [ ] No file in **Frozen / Out Of Scope** was modified.
- [ ] `git diff --name-only origin/main...` matches the packet scope (paste below).

```
<!-- paste output of: git diff --name-only origin/main... | sort -->
```

## Verification gates (must all be PASS)

- [ ] `python scripts/grace_lint.py apps/api/app` — **grace_lint PASS**
- [ ] `cd apps/api && ruff check .` — **ruff PASS**
- [ ] `cd apps/api && mypy app` — **mypy PASS**
- [ ] `cd apps/api && alembic upgrade head` (fresh sqlite) — **migrations PASS**
- [ ] `cd apps/api && pytest -q` — **pytest PASS**
- [ ] Packet `Verification` section steps all executed and pasted under **Evidence**.

## Evidence

<!--
Paste the raw output of every verification step here.
Reviewer (per Canon §10.5) MUST re-run them locally before approving.
-->

## Escalations

- [ ] No packet **Escalation triggers** were hit (or, if they were, an issue
      was opened and linked here BEFORE the change was made).

---

> Reviewer checklist (Canon §10.5): do not approve unless **every** box above
> is checked AND the CI job `grace-gate / contracts-and-tests` is green.

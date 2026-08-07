# S11 candidate replay smoke

Candidate smoke was run with the packet command after regenerating the replay
manifest. The full 120-chart / 730-day replay is intentionally left for the
reviewer.

```text
apps/api/.venv/bin/python docs/work/2026-07-29_today-convergence-rewrite/analysis/corpus_replay.py --output-dir /var/tmp/spheres-smoke --residues 0,1,2,3,4 --limit-charts 5 --from-date 2026-07-01 --to-date 2026-07-30 --workers 4
```

Candidate fingerprint: `c86c4f8b54b1f8803f31f094c20f53ee17f2a9817e3dc7e4126c4638877ec83c`

## Gate result

| gate | result |
|---|---:|
| charts | 5/5 ok |
| chart errors | 0 |
| physical signatures | 900 |
| group without sphere | 0 in every mode |
| unmapped | day 48; evening 48; exact 2180; morning 47; night 48; unknown 47 |
| old keys (`decisions`/`shopping`) | 0 |
| invalid facet | 0 |
| nullable facet | observed; no invalid values |
| repeated-sphere days | observed in every mode (97–106) |

Aggregate and JSONL artifacts are in `/var/tmp/spheres-smoke/`:
`aggregate.json`, `report.md`, and `physical_signatures.jsonl`.

## Signature example

```jsonl
{"schema_version":"today-convergence-physical-signature.v1","chart_id":"syn-000-moscow","birth_mode":"exact","target_date":"2026-07-01","canonical_event_ids":["...MARS__SQUARE__URANUS","...URANUS__SQUARE__URANUS"],"audit_only_event_ids":["act:annual_profection__HOUSE__11","act:lunar_return__ANGLE_MC__NATAL_HOUSE_11"],"unmapped_event_ids":["act:t2n__URANUS__SQUARE__URANUS"],"group_ids":["group:6f7538341e727bc20a2fe5cc6c7f7d857ba068db416e6d5cc784bbda30407941"],"groups":[{"group_id":"group:6f7538341e727bc20a2fe5cc6c7f7d857ba068db416e6d5cc784bbda30407941","member_event_ids":["act:t2n__MARS__SQUARE__URANUS","act:t2n__URANUS__SQUARE__URANUS"],"polarity":"tense","spheres":["work"]}],"selected_group_ids":["group:6f7538341e727bc20a2fe5cc6c7f7d857ba068db416e6d5cc784bbda30407941"],"state":"quiet_day","dayTone":"mixed"}
```

The example is a compact excerpt of the actual JSONL row. The unresolved
URANUS unit remains a physical group member and is counted by `unmapped`; the
group is resolver-backed (`work`), so `group_without_sphere` stays zero here.

Parity replay against `/var/tmp/s1-verify` (same 2 charts × 5 days × 6 modes):
`days compared: 60`, `physical mismatches: 0`, `PASS: physical parity baseline==candidate`.

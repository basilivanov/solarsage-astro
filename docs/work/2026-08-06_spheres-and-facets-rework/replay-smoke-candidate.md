# S11 candidate replay smoke

Candidate smoke was run with the packet command after regenerating the replay
manifest. The full 120-chart / 730-day replay is intentionally left for the
reviewer.

```text
apps/api/.venv/bin/python docs/work/2026-07-29_today-convergence-rewrite/analysis/corpus_replay.py --output-dir /var/tmp/spheres-smoke --residues 0,1,2,3,4 --limit-charts 5 --from-date 2026-07-01 --to-date 2026-07-30 --workers 4
```

Candidate fingerprint: `269d52b75f8de92ce5063531c31d807d55545738cf7d8ee2476a611f9ddfe308`

## Gate result

| gate | result |
|---|---:|
| charts | 5/5 ok |
| chart errors | 0 |
| physical signatures | 900 |
| group without sphere | 0 in every mode |
| unmapped | 0 in every mode |
| old keys (`decisions`/`shopping`) | 0 |
| invalid facet | 0 |
| nullable facet | observed; no invalid values |
| repeated-sphere days | observed in every mode (97–106) |

Aggregate and JSONL artifacts are in `/var/tmp/spheres-smoke/`:
`aggregate.json`, `report.md`, and `physical_signatures.jsonl`.

## Signature example

```jsonl
{"birth_mode":"day","canonical_event_ids":["act:firdar_major__PERIOD_LORD__MERCURY","act:firdar_minor__SUBPERIOD_LORD__SATURN","act:t2n__JUPITER__CONJUNCTION__SUN","act:t2n__MARS__SQUARE__URANUS","act:t2n__MERCURY__CONJUNCTION__SUN","act:t2n__MOON__OPPOSITION__SUN","act:t2n__NEPTUNE__SQUARE__SATURN","act:t2n__SATURN__SEXTILE__NEPTUNE","act:t2n__SATURN__TRINE__MERCURY","act:t2n__SATURN__TRINE__PLUTO","act:t2n__SUN__CONJUNCTION__SATURN","act:t2n__SUN__TRINE__MARS","act:t2n__VENUS__CONJUNCTION__JUPITER","act:t2n__VENUS__TRINE__PLUTO"],"chart_id":"syn-000-moscow","date":"2026-07-01","dayTone":"mixed","driver_keys":["fam:firdar","src:JUPITER","src:MARS","src:MERCURY","src:MOON","src:NEPTUNE","src:SATURN","src:SUN","src:VENUS"],"group_ids":["group:241abd7a32afc1193f11b00a01d50342da344b5cced9a36f782bd70e0ef1c9d1"],"group_polarity":{"group:241abd7a32afc1193f11b00a01d50342da344b5cced9a36f782bd70e0ef1c9d1":"tense"},"groups":[{"driver_keys":["src:JUPITER","src:MERCURY","src:MOON"],"group_id":"group:241abd7a32afc1193f11b00a01d50342da344b5cced9a36f782bd70e0ef1c9d1","hero":false,"hero_anchor_id":null,"hero_confirmation_id":null,"hero_evidence_level":null,"independence_keys":["src:JUPITER","src:MERCURY","src:MOON"],"member_event_ids":["act:t2n__JUPITER__CONJUNCTION__SUN","act:t2n__MERCURY__CONJUNCTION__SUN","act:t2n__MOON__OPPOSITION__SUN"],"n_independent":3,"polarity":"tense","spheres":["work"]}],"hero_anchor_ids":[],"hero_confirmation_ids":[],"hero_evidence_level":null,"independence_keys":["src:JUPITER","src:MERCURY","src:MOON"],"mode":"day","repeated_sphere_selected_count":3,"repeated_spheres":["creativity"],"schema_version":"today-convergence-physical-signature.v1","selected_event_ids":["act:t2n__JUPITER__CONJUNCTION__SUN","act:t2n__MERCURY__CONJUNCTION__SUN","act:t2n__MOON__OPPOSITION__SUN"],"selected_group_ids":["group:241abd7a32afc1193f11b00a01d50342da344b5cced9a36f782bd70e0ef1c9d1"],"selected_sphere_counts":{"creativity":3},"state":"quiet_day","target_date":"2026-07-01"}
```

The baseline replay was still running when this candidate smoke completed; no
baseline output was modified or awaited.

# W0 Audit Summary: Basil, 2026-07-08

## Executive summary
Production `TodayPayload` for Basil on 2026-07-08 has `day_status=supportive`, UI summary "Поддерживающий день" and status line "День возможностей". This is confirmed by the independent scoring oracle: production and oracle matched on `day_status`, all `sphere_scores`, and `top_signals` with `0.00` tolerance.

Why the day became supportive: the sum of positive aspects passing threshold is 7.35; the sum of tense aspects is 4.93; ratio is 1.4917 which is greater than the production threshold 1.3. Top positive factors: `Transit_Pluto trine Saturn`, `Transit_Sun trine Mercury`. Top tense factors: `Transit_Neptune opposition Saturn`, `Transit_Moon opposition Pluto`.

The astronomical oracle confirmed transit longitudes and houses. Discovered/fixed: raw retrograde flags are correct (Mercury, Neptune, Pluto are retrograde); Moon phase matches Swiss formula (43.792%); Moon-Pluto aspect is Transit Moon opposite natal Pluto.

## Trace map: production TodayPayload path
See `trace_map.json` for details.

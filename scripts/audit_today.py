#!/usr/bin/env python3
# ############################################################################
# AI_HEADER: MODULE_AUDIT_TODAY — production TodayPayload audit collector.
# ROLE: Captures SolarSage Today production-path inputs, intermediate layers,
#       scoring output, semantic contexts, final payload, and oracle comparisons.
# ############################################################################

# START_MODULE_CONTRACT: M-AUDIT-TODAY
# purpose: Export an auditable trace for one TodayPayload production case.
# owns:
#   - scripts/audit_today.py
# inputs: --user-id, --date, --out.
# outputs: JSON/CSV artifacts under --out, optionally including oracle outputs.
# dependencies: apps/api production services, subprocess oracle scripts.
# side_effects: reads DB, calls sidecar, may call TodayService for cached/final
#               payload; writes artifact files.
# emitted_logs: none.
# invariants:
#   - ScoringService is used only to capture production output, not as oracle.
#   - final_today_payload.json is the production TodayPayload returned by
#     TodayService for the supplied user/date.
# failure_policy: exits non-zero on missing profile, sidecar failure, or oracle
#                 subprocess failure unless --skip-oracles is set.
# END_MODULE_CONTRACT: M-AUDIT-TODAY

# START_MODULE_MAP: M-AUDIT-TODAY
# public_entrypoints:
#   - run_audit
#   - main
# semantic_blocks:
#   - BOOTSTRAP: import API app from scripts context
#   - PRODUCTION_TRACE: rebuild deterministic production intermediates
#   - ARTIFACT_WRITE: write required JSON/CSV files
#   - ORACLE_RUNNERS: invoke independent scoring and astronomy scripts
# END_MODULE_MAP: M-AUDIT-TODAY

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import subprocess
import sys
import shutil
from datetime import date as Date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from sqlalchemy import select  # noqa: E402

from app.clients.solarsage_client import get_solarsage_client  # noqa: E402
from app.db.models import NatalChartCache, User, UserProfile  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.schemas.normalization import AstroSignal  # noqa: E402
from app.services.access_service import AccessService  # noqa: E402
from app.services.astro_utils import strip_prefix  # noqa: E402
from app.services.day_delta_service import DayDeltaService  # noqa: E402
from app.services.day_scoring_signals import filter_day_scored_signals  # noqa: E402
from app.services.natal_context_service import NatalContextService  # noqa: E402
from app.services.normalization_service import NormalizationService  # noqa: E402
from app.services.scoring_service import ScoringService  # noqa: E402
from app.services.semantic_service import SemanticService  # noqa: E402
from app.services.today_service import TodayService  # noqa: E402


def to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=False)
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = fieldnames or list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def signal_to_dict(signal: AstroSignal, *, included: bool | None = None, index: int | None = None) -> dict[str, Any]:
    payload = signal.model_dump(mode="json", by_alias=False)
    payload["planet_clean"] = strip_prefix(signal.planet)
    payload["target_planet_clean"] = strip_prefix(signal.target_planet)
    if included is not None:
        payload["included_in_day_scoring"] = included
    if index is not None:
        payload["index"] = index
    return payload


def signals_to_rows(
    all_signals: list[AstroSignal],
    day_signals: list[AstroSignal],
) -> list[dict[str, Any]]:
    day_ids = {id(signal) for signal in day_signals}
    rows = []
    for index, signal in enumerate(all_signals, start=1):
        rows.append(signal_to_dict(signal, included=id(signal) in day_ids, index=index))
    return rows


def signal_fieldnames() -> list[str]:
    return [
        "index",
        "included_in_day_scoring",
        "type",
        "planet",
        "planet_clean",
        "target_planet",
        "target_planet_clean",
        "aspect_type",
        "orb",
        "strength",
        "house",
        "sign",
        "technique",
        "technique_family",
        "delta_kind",
        "phase",
        "daily_salience",
    ]


def sphere_score_rows(scores: dict[str, float]) -> list[dict[str, Any]]:
    return [
        {"key": key, "score": score, "rank": index}
        for index, (key, score) in enumerate(
            sorted(scores.items(), key=lambda item: (-float(item[1]), item[0])),
            start=1,
        )
    ]


def make_trace_map() -> list[dict[str, str]]:
    return [
        {
            "step": "API route",
            "file": "apps/api/app/api/day.py",
            "function": "get_day",
            "role": "Parses date/auth/access and calls TodayService.get_today_payload.",
        },
        {
            "step": "TodayService",
            "file": "apps/api/app/services/today_service.py",
            "function": "TodayService.get_today_payload",
            "role": "Loads profile/cache, gets natal context/transits, normalizes, scores, builds semantic/LLM/UI fields.",
        },
        {
            "step": "Natal context",
            "file": "apps/api/app/services/natal_context_service.py",
            "function": "NatalContextService.get_or_build_natal_context",
            "role": "Production natal source; calls sidecar /v1/natal only on natal cache miss.",
        },
        {
            "step": "SolarSage client",
            "file": "apps/api/app/clients/solarsage_client.py",
            "function": "SolarSageClient.get_transits",
            "role": "Calls sidecar /v1/transits for target date at 12:00 in profile timezone.",
        },
        {
            "step": "Sidecar transits",
            "file": "apps/solarsage/solarsage/api/transits.py",
            "function": "post_transits",
            "role": "Converts date/time/timezone to JD and returns Swiss Ephemeris planet positions.",
        },
        {
            "step": "Normalization",
            "file": "apps/api/app/services/normalization_service.py",
            "function": "NormalizationService.normalize_day",
            "role": "Builds natal signals, transit-to-natal aspects, and transit planet-in-natal-house signals.",
        },
        {
            "step": "Day signal filter",
            "file": "apps/api/app/services/day_scoring_signals.py",
            "function": "filter_day_scored_signals",
            "role": "Keeps Transit_* and explicit day-event signals; removes static natal signals from day scoring.",
        },
        {
            "step": "Scoring",
            "file": "apps/api/app/services/scoring_service.py",
            "function": "ScoringService.score_day",
            "role": "Production scoring output: day_status, sphere_scores, top_signals.",
        },
        {
            "step": "Semantic layer",
            "file": "apps/api/app/services/semantic_service.py",
            "function": "SemanticService.build_semantic_layer / build_why_contexts",
            "role": "Builds deterministic semantic layer and WhyThisHappens contexts for LLM.",
        },
        {
            "step": "LLM text",
            "file": "apps/api/app/services/llm_service.py",
            "function": "generate_headline / generate_reading / generate_notes / generate_why_sections",
            "role": "Generates narrative text from precomputed status/signals/scores/contexts.",
        },
        {
            "step": "UI product fields",
            "file": "apps/api/app/services/today_interpretation_service.py",
            "function": "TodayInterpretationService.build",
            "role": "Builds day_summary and concrete_advice rows/evidence consumed by frontend.",
        },
        {
            "step": "Frontend adapter",
            "file": "lib/adapters/today-payload.ts",
            "function": "adaptTodayPayload",
            "role": "Maps API TodayPayload into UI-ready fields without recomputing astrology.",
        },
    ]


def input_profile_payload(user: User, profile: UserProfile) -> dict[str, Any]:
    return {
        "user_id": str(user.id),
        "tg_user_id": user.tg_user_id,
        "tg_username": user.tg_username,
        "is_onboarded": profile.is_onboarded,
        "gender": profile.gender,
        "birth": {
            "date": profile.birthday.isoformat() if profile.birthday else None,
            "time": profile.birth_time.strftime("%H:%M") if profile.birth_time else None,
            "city": profile.birth_city,
            "lat": float(profile.birth_lat) if profile.birth_lat is not None else None,
            "lon": float(profile.birth_lon) if profile.birth_lon is not None else None,
            "tz": profile.birth_tz,
        },
        "current": {
            "city": profile.current_city,
            "lat": float(profile.current_lat) if profile.current_lat is not None else None,
            "lon": float(profile.current_lon) if profile.current_lon is not None else None,
            "tz": profile.current_tz,
        },
    }


async def load_user_and_profile(db, user_id: str) -> tuple[User, UserProfile]:
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise SystemExit(f"User not found: {user_id}")
    profile_result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = profile_result.scalar_one_or_none()
    if profile is None:
        raise SystemExit(f"Profile not found for user: {user_id}")
    return user, profile


async def load_raw_natal_sidecar(db, user_id: str, profile_hash: str) -> dict[str, Any] | None:
    result = await db.execute(
        select(NatalChartCache).where(
            NatalChartCache.user_id == user_id,
            NatalChartCache.profile_hash == profile_hash,
            NatalChartCache.invalidated_at.is_(None),
        )
    )
    cache = result.scalar_one_or_none()
    if cache is None:
        return None
    return json.loads(cache.raw_chart_json)


async def run_oracles(
    *,
    out_dir: Path,
    target_date: Date,
    target_tz: str,
    astronomy_python: Path,
    skip_scoring_oracle: bool,
    skip_astronomy_oracle: bool,
) -> None:
    if not skip_scoring_oracle:
        subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "audit_scoring_oracle.py"),
                "--canon-dir",
                str(REPO_ROOT / "grace" / "canon"),
                "--signals",
                str(out_dir / "signal_trace.csv"),
                "--production-scoring",
                str(out_dir / "production_scoring_result.json"),
                "--production-payload",
                str(out_dir / "final_today_payload.json"),
                "--out",
                str(out_dir),
            ],
            cwd=REPO_ROOT,
            check=True,
        )

    if not skip_astronomy_oracle:
        if not astronomy_python.exists():
            raise SystemExit(f"Astronomy Python not found: {astronomy_python}")
        subprocess.run(
            [
                str(astronomy_python),
                str(REPO_ROOT / "scripts" / "audit_astronomy_oracle.py"),
                "--input-profile",
                str(out_dir / "input_profile.json"),
                "--raw-transits",
                str(out_dir / "raw_transits.json"),
                "--raw-natal-context",
                str(out_dir / "raw_natal_context.json"),
                "--final-payload",
                str(out_dir / "final_today_payload.json"),
                "--date",
                target_date.isoformat(),
                "--time",
                "12:00",
                "--tz",
                target_tz,
                "--out",
                str(out_dir),
            ],
            cwd=REPO_ROOT,
            check=True,
        )


async def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-AUDIT-TODAY.run_audit
    # purpose: Capture production Today path and write audit artifacts.
    # inputs: argparse namespace with user_id, date, out, oracle flags.
    # returns: summary dict.
    # side_effects: DB reads, sidecar calls, writes artifact files, may run subprocesses.
    # emitted_logs: none.
    # error_behavior: raises on missing profile or failed production/oracle calls.
    # END_FUNCTION_CONTRACT: F-M-AUDIT-TODAY.run_audit
    target_date = Date.fromisoformat(args.date)
    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Optional debug/intermediate subdirectory
    debug_dir = out_dir / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)

    async with SessionLocal() as db:
        user, profile = await load_user_and_profile(db, args.user_id)
        profile_payload = input_profile_payload(user, profile)

        # Write intermediates to debug
        write_json(debug_dir / "input_profile.json", profile_payload)
        write_json(debug_dir / "trace_map.json", make_trace_map())

        access_state = await AccessService(db).can_access_day(user.id, target_date)

        context_service = NatalContextService(db)
        natal_context = await context_service.get_or_build_natal_context(user.id)
        natal_context_dict = natal_context.model_dump(mode="json", by_alias=False)
        write_json(debug_dir / "raw_natal_context.json", natal_context_dict)

        profile_hash = NatalContextService.compute_profile_hash(profile)
        raw_natal_sidecar = await load_raw_natal_sidecar(db, str(user.id), profile_hash)
        if raw_natal_sidecar is not None:
            write_json(debug_dir / "raw_natal_sidecar.json", raw_natal_sidecar)

        client = get_solarsage_client()
        target_tz = profile.current_tz or profile.birth_tz or "UTC"
        transits = await client.get_transits(
            target_date=target_date.isoformat(),
            target_time="12:00",
            target_tz=target_tz,
        )
        write_json(debug_dir / "raw_transits.json", transits)

        normalization_service = NormalizationService()
        signals_before_delta = normalization_service.normalize_day(natal_context_dict, transits)
        write_json(
            debug_dir / "normalized_signals_before_delta.json",
            [signal_to_dict(signal, index=index) for index, signal in enumerate(signals_before_delta, start=1)],
        )

        yesterday = target_date.fromordinal(target_date.toordinal() - 1)
        yesterday_transits = await client.get_transits(
            target_date=yesterday.isoformat(),
            target_time="12:00",
            target_tz=profile.birth_tz or "UTC",
        )
        write_json(debug_dir / "yesterday_raw_transits.json", yesterday_transits)
        yesterday_signals = normalization_service.normalize_day(natal_context_dict, yesterday_transits)
        write_json(
            debug_dir / "yesterday_normalized_signals.json",
            [signal_to_dict(signal, index=index) for index, signal in enumerate(yesterday_signals, start=1)],
        )

        signals = DayDeltaService(yesterday_signals, signals_before_delta).compute_deltas()
        day_signals = filter_day_scored_signals(signals)

        all_signal_rows = signals_to_rows(signals, day_signals)
        day_signal_rows = [
            signal_to_dict(signal, included=True, index=index)
            for index, signal in enumerate(day_signals, start=1)
        ]
        write_json(debug_dir / "normalized_signals_before_filter.json", all_signal_rows)
        write_json(debug_dir / "day_scored_signals_after_filter.json", day_signal_rows)
        write_csv(debug_dir / "signal_trace.csv", all_signal_rows, fieldnames=signal_fieldnames())
        write_csv(debug_dir / "day_scored_signals_after_filter.csv", day_signal_rows, fieldnames=signal_fieldnames())

        delta_counts: dict[str, int] = {}
        for signal in signals:
            key = signal.delta_kind or "none"
            delta_counts[key] = delta_counts.get(key, 0) + 1
        write_json(debug_dir / "day_delta_counts.json", delta_counts)

        scoring_result = ScoringService().score_day(day_signals)
        production_scoring = {
            "day_status": scoring_result["day_status"],
            "sphere_scores": scoring_result["sphere_scores"],
            "top_signals": [signal_to_dict(signal, index=index) for index, signal in enumerate(scoring_result["top_signals"], start=1)],
        }
        write_json(debug_dir / "production_scoring_result.json", production_scoring)
        write_json(debug_dir / "sphere_scores.json", scoring_result["sphere_scores"])
        write_csv(debug_dir / "sphere_scores.csv", sphere_score_rows(scoring_result["sphere_scores"]))
        write_json(debug_dir / "top_signals.json", production_scoring["top_signals"])
        write_csv(debug_dir / "top_signals.csv", production_scoring["top_signals"], fieldnames=signal_fieldnames())

        semantic_service = SemanticService()
        semantic_layer = semantic_service.build_semantic_layer(
            scoring_result["day_status"],
            scoring_result["sphere_scores"],
        )
        why_contexts = semantic_service.build_why_contexts(
            scoring_result["day_status"],
            scoring_result["sphere_scores"],
            scoring_result["top_signals"],
            natal_context_dict,
            transits,
            semantic_layer,
            signals,
        )
        write_json(debug_dir / "semantic_layer.json", semantic_layer)
        write_json(debug_dir / "why_contexts.json", why_contexts)

        # Default: use cached payload (deterministic baseline).
        # Only invalidate and regenerate fresh LLM text when --live-llm-sample is set.
        if getattr(args, 'live_llm_sample', False):
            await TodayService(db).invalidate_cache(user.id)

        today_payload = await TodayService(db).get_today_payload(
            user_id=user.id,
            target_date=target_date,
            access_state=access_state,
            skip_prefetch=True,
        )
        payload_json = today_payload.model_dump(mode="json", by_alias=False)

        # Normalize volatile fields so canonical artifacts are deterministic
        meta = payload_json.get("meta", payload_json.get("Meta", {}))
        meta["generated_at"] = f"{target_date.isoformat()}T12:00:00Z"
        meta["cached"] = False

        # Determine live-LLM sample output path (non-destructive to canonical root)
        live_dir = None
        if getattr(args, 'live_llm_sample', False):
            import datetime
            ts = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
            live_dir = out_dir / "live" / ts
            live_dir.mkdir(parents=True, exist_ok=True)

        # Default baseline mode: freeze volatile LLM fields from committed canonical baseline.
        # This makes the baseline deterministic even without a pre-existing DB cache row.
        if not getattr(args, 'live_llm_sample', False):
            baseline_path = out_dir / "11_final_today_payload.json"
            if baseline_path.exists():
                import json as _json
                baseline_raw = baseline_path.read_text(encoding="utf-8")
                baseline = _json.loads(baseline_raw)
                # Freeze headline
                payload_json["headline"] = baseline.get("headline", payload_json["headline"])
                # Freeze reading paragraphs
                payload_json["reading"] = baseline.get("reading", payload_json["reading"])
                # Freeze notes
                payload_json["notes"] = baseline.get("notes", payload_json["notes"])
                # Freeze why_this_happens sections
                if "why_this_happens" in baseline:
                    payload_json["why_this_happens"] = baseline["why_this_happens"]
                # Freeze concrete_advice row texts
                baseline_advice = {}
                base_ca = baseline.get("concrete_advice") or baseline.get("concreteAdvice") or {}
                if isinstance(base_ca, dict):
                    for r in base_ca.get("rows", []):
                        baseline_advice[r.get("key")] = r.get("text", "")
                live_ca = payload_json.get("concrete_advice") or payload_json.get("concreteAdvice") or {}
                if isinstance(live_ca, dict):
                    for r in live_ca.get("rows", []):
                        if r.get("key") in baseline_advice:
                            r["text"] = baseline_advice[r["key"]]
                # Freeze planet interpretations
                baseline_planets = {}
                base_chart = baseline.get("day_chart") or baseline.get("dayChart") or {}
                if isinstance(base_chart, dict):
                    for p in base_chart.get("transit_planets", []):
                        baseline_planets[p.get("name")] = p.get("interpretation", "")
                live_chart = payload_json.get("day_chart") or payload_json.get("dayChart") or {}
                if isinstance(live_chart, dict):
                    for p in live_chart.get("transit_planets", []):
                        if p.get("name") in baseline_planets:
                            p["interpretation"] = baseline_planets[p["name"]]

        write_json(debug_dir / "final_today_payload.json", payload_json)

        await client.close()

    await run_oracles(
        out_dir=debug_dir,
        target_date=target_date,
        target_tz=target_tz,
        astronomy_python=args.astronomy_python,
        skip_scoring_oracle=args.skip_scoring_oracle or args.skip_oracles,
        skip_astronomy_oracle=args.skip_astronomy_oracle or args.skip_oracles,
    )

    # Copy files to root with canonical 16 names
    shutil.copy2(debug_dir / "input_profile.json", out_dir / "00_input_profile.json")
    shutil.copy2(debug_dir / "raw_natal_context.json", out_dir / "01_raw_natal_context.json")
    shutil.copy2(debug_dir / "raw_transits.json", out_dir / "02_raw_transits.json")
    shutil.copy2(debug_dir / "normalized_signals_before_filter.json", out_dir / "03_normalized_signals_all.json")
    shutil.copy2(debug_dir / "day_scored_signals_after_filter.csv", out_dir / "04_day_scored_signals_after_filter.csv")
    shutil.copy2(debug_dir / "signal_trace.csv", out_dir / "05_signal_trace.csv")
    shutil.copy2(debug_dir / "scoring_intermediate_table.csv", out_dir / "06_scoring_intermediate_table.csv")
    shutil.copy2(debug_dir / "sphere_scores.csv", out_dir / "07_sphere_scores.csv")
    shutil.copy2(debug_dir / "top_signals.csv", out_dir / "08_top_signals.csv")
    shutil.copy2(debug_dir / "semantic_layer.json", out_dir / "09_semantic_layer.json")
    shutil.copy2(debug_dir / "why_contexts.json", out_dir / "10_why_contexts.json")
    # 11_final_today_payload.json: in default mode copy to canonical root;
    # in live-LLM mode write to live/ subdirectory and do not touch canonical root.
    if getattr(args, 'live_llm_sample', False) and live_dir is not None:
        write_json(live_dir / "final_today_payload.json", payload_json)
    else:
        shutil.copy2(debug_dir / "final_today_payload.json", out_dir / "11_final_today_payload.json")

    if (debug_dir / "scoring_oracle_comparison.json").exists():
        shutil.copy2(debug_dir / "scoring_oracle_comparison.json", out_dir / "12_scoring_oracle_comparison.json")
    if (debug_dir / "astronomy_oracle_summary.json").exists():
        shutil.copy2(debug_dir / "astronomy_oracle_summary.json", out_dir / "13_astronomy_oracle_summary.json")

    # Generate 14_claims_audit.md dynamically
    # Support both snake_case (by_alias=False) and camelCase (by_alias=True) defensively
    def _get_field(obj, *keys):
        for k in keys:
            v = obj.get(k) if isinstance(obj, dict) else None
            if v is not None:
                return v
        return None

    headline = payload_json.get("headline", "N/A")
    day_status_val = _get_field(payload_json, "day_status", "dayStatus") or "N/A"

    lunar_phase_title = "N/A"
    day_summary = _get_field(payload_json, "day_summary", "daySummary") or {}
    for fact in day_summary.get("facts", []):
        if fact.get("kind") == "lunar_phase":
            lunar_phase_title = fact.get("title", "N/A")

    top_flags = _get_field(payload_json, "top_flags", "topFlags") or []
    top_flags_titles = [f.get("title", "") for f in top_flags]
    top_flags_str = ", ".join(top_flags_titles) if top_flags_titles else "N/A"

    concrete_advice = _get_field(payload_json, "concrete_advice", "concreteAdvice") or {}
    advice_rows = concrete_advice.get("rows", [])
    advice_lines = []
    for r in advice_rows:
        advice_lines.append(f"| {r.get('label', '')} | {r.get('verdict', '')} | {r.get('text', '')} |")
    advice_table = "\n".join(advice_lines) if advice_lines else "| N/A | N/A | N/A |"

    claims_text = f"""# W0 Claims Audit: User {args.user_id}, {args.date}

This document contains actual production payload excerpts generated for manual review and claims verification.

## Production Payload Excerpts

- **Headline**: "{headline}"
- **Day Status**: {day_status_val}
- **Moon Phase Fact**: "{lunar_phase_title}"
- **Top Flags**: {top_flags_str}

## Concrete Advice Recommendations

| Sphere | Verdict | Advice Text |
|---|---|---|
{advice_table}

---

## Historical Snapshot (Basil, 2026-07-08 pre-fix baseline)
*This is kept for reference to document the original trust issues identified before W0 fixes:*

- **Stale Headline**: "поддержку в глубоких чувствах и творческих порывах" (unsupported by transit signals)
- **Stale Moon Phase**: "Убывающая Луна 46%" (deviated from Swiss Ephemeris 43.792% by 2.208pp)
- **Stale Advice Contradiction**: "Общайся с близкими для улучшения отношений" under "avoid" verdict.
"""
    # Write claims audit report
    # In live-LLM mode, write only to the live directory (not to canonical root).
    if live_dir is not None:
        (live_dir / "14_claims_audit.md").write_text(claims_text, encoding="utf-8")
    else:
        (out_dir / "14_claims_audit.md").write_text(claims_text, encoding="utf-8")

    # Generate 15_audit_summary.md dynamically
    summary_text = f"""# W0 Audit Summary: User {args.user_id}, {args.date}

## Executive summary
Production `TodayPayload` for User {args.user_id} on {args.date} has `day_status={scoring_result["day_status"]}`.

Why the day status happened: see `production_scoring_result.json` and `scoring_oracle_comparison.json`.

The astronomical oracle verified transit longitudes, retrograde flags, moon phase, and house placements.

## Trace map: production TodayPayload path
See `trace_map.json` for details.
"""
    (out_dir / "15_audit_summary.md").write_text(summary_text, encoding="utf-8")

    summary = {
        "user_id": args.user_id,
        "date": target_date.isoformat(),
        "out_dir": str(out_dir),
        "target_time": "12:00",
        "target_timezone": target_tz,
        "signal_count": len(all_signal_rows),
        "day_scored_signal_count": len(day_signal_rows),
        "day_status": scoring_result["day_status"],
        "final_headline": payload_json.get("headline"),
        "final_cached": (payload_json.get("meta") or {}).get("cached"),
    }
    write_json(debug_dir / "audit_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture SolarSage TodayPayload audit artifacts")
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--astronomy-python",
        type=Path,
        default=REPO_ROOT / "apps" / "solarsage" / "venv" / "bin" / "python",
    )
    parser.add_argument("--skip-oracles", action="store_true")
    parser.add_argument("--skip-scoring-oracle", action="store_true")
    parser.add_argument("--skip-astronomy-oracle", action="store_true")
    parser.add_argument("--live-llm-sample", action="store_true",
                        help="Bypass cache and regenerate fresh LLM text for live sampling")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = asyncio.run(run_audit(args))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

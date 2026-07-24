# ############################################################################
# AI_HEADER: MODULE_SERVICES_ELECTION_ENGINE
# ROLE: Computational scoring engine for elective astrology date selection (v2)
# DEPENDENCIES: pyyaml, path/to/canon
# GRACE_ANCHORS: [ELECTION_ENGINE]
# ############################################################################

# START_MODULE_CONTRACT: M-ELECTION-ENGINE
# purpose: Score candidate days for specific elective events based on lunar facts and canon rules.
# owns:
#   - apps/api/app/services/election_engine.py
# inputs: event_type (str), from_date (date), to_date (date), lunar_days (list[dict]), natal_moon_sign (str | None)
# outputs: dict with event, best_days, avoid_days, days, facts
# dependencies: grace/canon/election_rules.v1.yml
# side_effects: reads canon file from disk
# emitted_logs: none
# failure_policy: raises ValueError for unknown event_type
# END_MODULE_CONTRACT: M-ELECTION-ENGINE

# START_MODULE_MAP: M-ELECTION-ENGINE
# public_entrypoints:
#   - scan
#   - resolve_event
# semantic_blocks:
#   - ELECTION_ENGINE: Rule evaluation and scoring logic
# END_MODULE_MAP: M-ELECTION-ENGINE

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml

# Root of solarsage-astro repo: apps/api/app/services/election_engine.py -> parents[4]
REPO_ROOT = Path(__file__).resolve().parents[4]
CANON_PATH = REPO_ROOT / "grace" / "canon" / "election_rules.v1.yml"


def _load_canon() -> dict[str, Any]:
    if not CANON_PATH.exists():
        raise FileNotFoundError(f"Canon file not found: {CANON_PATH}")
    with CANON_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get_label(score: int) -> str:
    if score >= 75:
        return "great"
    if score >= 55:
        return "good"
    if score >= 35:
        return "ok"
    return "avoid"


def resolve_event(event_type: str, canon: dict[str, Any] | None = None) -> tuple[str, str, dict[str, Any]]:
    if canon is None:
        canon = _load_canon()

    categories = canon.get("categories", {})

    # 1. Format "category:sub"
    if ":" in event_type:
        cat_key, sub_key = event_type.split(":", 1)
        if cat_key in categories and sub_key in categories[cat_key].get("subs", {}):
            return cat_key, sub_key, categories[cat_key]["subs"][sub_key]
        raise ValueError(f"Unknown event type format: {event_type}")

    # 2. Plain sub key (search globally)
    for cat_key, cat_val in categories.items():
        subs = cat_val.get("subs", {})
        if event_type in subs:
            return cat_key, event_type, subs[event_type]

    # 3. Fallback for legacy events block if any
    legacy_events = canon.get("events", {})
    if event_type in legacy_events:
        return "general", event_type, legacy_events[event_type]

    raise ValueError(f"Unknown event type: {event_type}")


async def scan(
    event_type: str,
    from_date: date,
    to_date: date,
    lunar_days: list[dict[str, Any]],
    natal_moon_sign: str | None = None,
) -> dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-ELECTION-ENGINE.scan
    # purpose: Score lunar_days for event_type between from_date and to_date.
    # inputs: event_type, from_date, to_date, lunar_days, natal_moon_sign
    # returns: dict containing event, best_days, avoid_days, days, facts
    # side_effects: reads canon YAML file
    # error_behavior: raises ValueError on unknown event_type
    # END_FUNCTION_CONTRACT: F-M-ELECTION-ENGINE.scan
    canon = _load_canon()
    cat_key, sub_key, sub_rule = resolve_event(event_type, canon)

    scoring_cfg = canon.get("scoring", {})
    base_score = scoring_cfg.get("base", 50)
    pref_bonus = scoring_cfg.get("preferred_sign", 25)
    dis_penalty = scoring_cfg.get("disfavored_sign", -15)
    wax_bonus = scoring_cfg.get("waxing", 10)
    voc_over_cfg = scoring_cfg.get("voc_fraction_over", {"threshold": 0.25, "penalty": -40})
    merc_penalty = scoring_cfg.get("mercury_retro_penalty", -20)
    clamp_min, clamp_max = scoring_cfg.get("clamp", [0, 100])

    preferred_signs = set(sub_rule.get("preferred", []))
    disfavored_signs = set(sub_rule.get("disfavored", []))
    mercury_sensitive = sub_rule.get("mercury_sensitive", False)
    moon_signs_ru = canon.get("moon_signs_ru", {})

    evaluated_days: list[dict[str, Any]] = []

    for day in lunar_days:
        day_date_str = day["date"]
        d_obj = date.fromisoformat(day_date_str)
        if not (from_date <= d_obj <= to_date):
            continue

        score = base_score
        reasons: list[str] = []

        moon_sign = day.get("moon_sign", "")
        moon_sign_ru = moon_signs_ru.get(moon_sign, day.get("moon_sign_ru", moon_sign))

        if moon_sign in preferred_signs:
            score += pref_bonus
            reasons.append(f"Луна в {moon_sign_ru} — благоприятный знак для события")
        elif moon_sign in disfavored_signs:
            score += dis_penalty
            reasons.append(f"Луна в {moon_sign_ru} — нежелательный знак для события")
        else:
            reasons.append(f"Луна в {moon_sign_ru} — нейтральный фон")

        waxing = bool(day.get("waxing"))
        if waxing:
            score += wax_bonus
            reasons.append("Луна растущая — способствует развитию и росту")

        voc_frac = day.get("voc_fraction", 0.0)
        voc_threshold = voc_over_cfg.get("threshold", 0.25)
        if voc_frac > voc_threshold:
            score += voc_over_cfg.get("penalty", -40)
            pct = int(round(voc_frac * 100))
            reasons.append(f"Луна без курса ~{pct}% дня — риск задержек и холостых усилий")

        merc_retro = bool(day.get("mercury_retro"))
        if mercury_sensitive and merc_retro:
            score += merc_penalty
            reasons.append("Меркурий ретроградный — риск ошибок в коммуникации и документах")

        final_score = max(clamp_min, min(clamp_max, score))
        label = _get_label(final_score)

        # Format voc_intervals to up to 2 "HH:MM-HH:MM" UTC strings
        voc_intervals_raw = day.get("voc_intervals", [])
        formatted_voc: list[str] = []
        for interval in voc_intervals_raw[:2]:
            if isinstance(interval, dict):
                st = interval.get("start", "")
                en = interval.get("end", "")
                st_time = st.split("T")[1][:5] if "T" in st else ""
                en_time = en.split("T")[1][:5] if "T" in en else ""
                if st_time and en_time:
                    formatted_voc.append(f"{st_time}-{en_time}")
            elif hasattr(interval, "start") and hasattr(interval, "end"):
                st_time = interval.start.split("T")[1][:5] if "T" in interval.start else ""
                en_time = interval.end.split("T")[1][:5] if "T" in interval.end else ""
                if st_time and en_time:
                    formatted_voc.append(f"{st_time}-{en_time}")

        phase_angle = day.get("phase_angle", 0.0)
        phase_pct = int(round((phase_angle / 360.0) * 100))

        evaluated_days.append({
            "date": day_date_str,
            "score": final_score,
            "label": label,
            "reasons": reasons,
            "moon_sign": moon_sign,
            "moon_sign_ru": moon_sign_ru,
            "waxing": waxing,
            "phase_pct": phase_pct,
            "voc_fraction": voc_frac,
            "voc_intervals": formatted_voc,
            "mercury_retro": merc_retro,
        })

    sorted_days = sorted(evaluated_days, key=lambda x: x["score"], reverse=True)
    best_days = [d for d in sorted_days if d["label"] != "avoid"][:3]
    avoid_days = [d for d in sorted_days if d["label"] == "avoid"][:3]

    hero_day = best_days[0] if best_days else None
    natal_moon_ru = moon_signs_ru.get(natal_moon_sign, "") if natal_moon_sign else None
    resonates = (hero_day["moon_sign"] == natal_moon_sign) if (hero_day and natal_moon_sign) else False

    facts = {
        "event": {
            "category": cat_key,
            "sub": sub_key,
            "label": sub_rule.get("label", sub_key),
        },
        "personal": {
            "natal_moon_sign": natal_moon_sign,
            "natal_moon_sign_ru": natal_moon_ru,
            "resonates": resonates,
        },
    }

    return {
        "event": event_type,
        "best_days": best_days,
        "avoid_days": avoid_days,
        "days": evaluated_days,
        "facts": facts,
    }

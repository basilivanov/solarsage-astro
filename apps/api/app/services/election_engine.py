# ############################################################################
# AI_HEADER: MODULE_SERVICES_ELECTION_ENGINE
# ROLE: Computational scoring engine for elective astrology date selection
# DEPENDENCIES: pyyaml, path/to/canon
# GRACE_ANCHORS: [ELECTION_ENGINE]
# ############################################################################

# START_MODULE_CONTRACT: M-ELECTION-ENGINE
# purpose: Score candidate days for specific elective events based on lunar facts and canon rules.
# owns:
#   - apps/api/app/services/election_engine.py
# inputs: event_type (str), from_date (date), to_date (date), lunar_days (list[dict])
# outputs: dict with best_days, avoid_days, event
# dependencies: grace/canon/election_rules.v1.yml
# side_effects: reads canon file from disk
# emitted_logs: none
# failure_policy: raises ValueError for unknown event_type
# END_MODULE_CONTRACT: M-ELECTION-ENGINE

# START_MODULE_MAP: M-ELECTION-ENGINE
# public_entrypoints:
#   - scan
# semantic_blocks:
#   - ELECTION_ENGINE: Rule evaluation and scoring logic
# END_MODULE_MAP: M-ELECTION-ENGINE

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml

# Root of solarsage-astro repo from apps/api/app/services/election_engine.py
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


async def scan(
    event_type: str,
    from_date: date,
    to_date: date,
    lunar_days: list[dict[str, Any]],
) -> dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-ELECTION-ENGINE.scan
    # purpose: Score lunar_days for event_type between from_date and to_date.
    # inputs: event_type, from_date, to_date, lunar_days
    # returns: dict containing event, best_days, avoid_days
    # side_effects: reads canon YAML file
    # error_behavior: raises ValueError on unknown event_type
    # END_FUNCTION_CONTRACT: F-M-ELECTION-ENGINE.scan
    canon = _load_canon()
    events_cfg = canon.get("events", {})

    if event_type not in events_cfg:
        raise ValueError(f"Unknown event type: {event_type}. Valid types: {list(events_cfg.keys())}")

    event_rule = events_cfg[event_type]
    scoring_cfg = canon.get("scoring", {})
    base_score = scoring_cfg.get("base", 50)
    pref_bonus = scoring_cfg.get("preferred_sign", 25)
    dis_penalty = scoring_cfg.get("disfavored_sign", -15)
    wax_bonus = scoring_cfg.get("waxing", 10)
    voc_over_cfg = scoring_cfg.get("voc_fraction_over", {"threshold": 0.25, "penalty": -40})
    merc_penalty = scoring_cfg.get("mercury_retro_penalty", -20)
    clamp_min, clamp_max = scoring_cfg.get("clamp", [0, 100])

    preferred_signs = set(event_rule.get("preferred", []))
    disfavored_signs = set(event_rule.get("disfavored", []))
    mercury_sensitive = event_rule.get("mercury_sensitive", False)
    moon_signs_ru = canon.get("moon_signs_ru", {})

    evaluated_days: list[dict[str, Any]] = []

    for day in lunar_days:
        day_date_str = day["date"]
        # Check range
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

        if day.get("waxing"):
            score += wax_bonus
            reasons.append("Луна растущая — способствует развитию и росту")

        voc_frac = day.get("voc_fraction", 0.0)
        voc_threshold = voc_over_cfg.get("threshold", 0.25)
        if voc_frac > voc_threshold:
            score += voc_over_cfg.get("penalty", -40)
            pct = int(round(voc_frac * 100))
            reasons.append(f"Луна без курса ~{pct}% дня — риск задержек и холостых усилий")

        if mercury_sensitive and day.get("mercury_retro"):
            score += merc_penalty
            reasons.append("Меркурий ретроградный — риск ошибок в коммуникации и документах")

        # Clamp
        final_score = max(clamp_min, min(clamp_max, score))
        label = _get_label(final_score)

        evaluated_days.append({
            "date": day_date_str,
            "score": final_score,
            "label": label,
            "reasons": reasons,
        })

    # Sort days by score descending
    sorted_days = sorted(evaluated_days, key=lambda x: x["score"], reverse=True)

    best_days = [d for d in sorted_days if d["label"] != "avoid"][:3]
    avoid_days = [d for d in sorted_days if d["label"] == "avoid"][:3]

    return {
        "event": event_type,
        "best_days": best_days,
        "avoid_days": avoid_days,
    }

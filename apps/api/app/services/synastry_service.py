# ############################################################################
# AI_HEADER: MODULE_SERVICES_SYNASTRY_SERVICE
# ROLE: Orchestration service for synastry calculations, state machine, LLM pipeline, credit spending, and persistence.
# DEPENDENCIES: sqlalchemy, httpx, app.db.models, app.services.synastry_scoring, app.services.synastry_llm, app.services.llm.client
# GRACE_ANCHORS: [SYNASTRY_SERVICE]
# ############################################################################

# START_MODULE_CONTRACT: M-SYNASTRY-SERVICE
# purpose: Orchestrate synastry partner creation, credit consumption, state machine, scoring, LLM generation, and retrieval.
# owns:
#   - apps/api/app/services/synastry_service.py
# inputs: AsyncSession
# outputs: SynastryPartner, SynastryReport, SynastryAspectDetail, SynastryFeedback
# dependencies:
#   - M-DB-MODELS
#   - M-SYNASTRY-SCORING
#   - M-LLM-SYNASTRY
#   - M-LLM-CLIENT
# side_effects:
#   - creates DB records, spends/refunds credits, executes state machine, calls sidecar & LLM
# emitted_logs: sidecar.called, scoring.computed, llm.requested, llm.response_validated, llm.response_rejected, system.error
# failure_policy:
#   - raises HTTPException(404) for unowned partner/report
#   - raises HTTPException(409) for duplicate partner or incomplete profile
#   - sets state=FAILED on sidecar failure or repeated LLM validation failure, and refunds credit
# END_MODULE_CONTRACT: M-SYNASTRY-SERVICE

# START_MODULE_MAP: M-SYNASTRY-SERVICE
# public_entrypoints:
#   - SynastryService.create_partner_and_report
#   - SynastryService.run_report_pipeline
#   - SynastryService.get_aspect_drilldown
#   - SynastryService.submit_feedback
#   - SynastryService.delete_partner
# semantic_blocks:
#   - SYNASTRY_SERVICE: High-level orchestration for synastry feature
# owned_tests:
#   - apps/api/tests/test_synastry_service.py
# END_MODULE_MAP: M-SYNASTRY-SERVICE

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any
import uuid

from fastapi import HTTPException, status
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.log_identity import hash_log_identifier
from app.core.logging import bind_log_context, log_event
from app.db.models import (
    HoraryCredit,
    SynastryAspectDetail,
    SynastryCreditSpend,
    SynastryFeedback,
    SynastryPartner,
    SynastryReport,
    UserProfile,
)
from app.schemas.synastry import (
    AspectDrilldown,
    AspectDrilldownScene,
    PartnerCreate,
    PlanetInfo,
    SynastryFeedbackRead,
)
from app.services.llm.client import LLMClient
from app.services.synastry_llm import (
    ASPECT_MEANINGS,
    PLANET_MEANINGS,
    build_drilldown_prompt,
    build_report_prompt,
    validate_drilldown_output,
    validate_llm_output,
)
from app.services.synastry_scoring import (
    RawAspectInput,
    SynastryScoringEngine,
)


def _compute_partner_hash(
    owner_id: uuid.UUID,
    name: str,
    birth_date_str: str,
    birth_time_str: str | None,
    city: str | None,
) -> str:
    raw = f"{owner_id}:{name.strip().lower()}:{birth_date_str}:{birth_time_str or ''}:{city or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _format_orb_label(orb: float | None) -> str | None:
    if orb is None:
        return None
    deg = int(orb)
    mins = int(round((orb - deg) * 60))
    if mins == 60:
        deg += 1
        mins = 0
    return f"{deg}°{mins:02d}′"


_RU_TO_EN_ASTRO = {
    "солнце": "sun",
    "луна": "moon",
    "меркурий": "mercury",
    "венера": "venus",
    "марс": "mars",
    "юпитер": "jupiter",
    "сатурн": "saturn",
    "уран": "uranus",
    "нептун": "neptune",
    "плутон": "pluto",
    "асцендент": "ascendant",
    "соединение": "conjunction",
    "трин": "trine",
    "секстиль": "sextile",
    "квадрат": "square",
    "оппозиция": "opposition",
    "квиконс": "quincunx",
}


def _normalize_tech_str(s: str) -> str:
    low = s.lower()
    for ru, en in _RU_TO_EN_ASTRO.items():
        low = low.replace(ru, en)
    return re.sub(r"[^\w]", "", low)


def _match_translation_aspect_id(tech: str | None, aspects: list[dict[str, Any]]) -> str | None:
    if not tech:
        return None

    # Handle combined tech e.g. "Марс ☍ Марс + Меркурий □ Меркурий" by checking each part
    parts = [p.strip() for p in re.split(r"[+\/,]", tech) if p.strip()]
    if not parts:
        parts = [tech]

    for part in parts:
        norm_part = _normalize_tech_str(part)
        if not norm_part:
            continue
        for a in aspects:
            aid = a.get("id", "")
            base_aid = re.sub(r"_\d+$", "", aid)
            norm_aid = _normalize_tech_str(base_aid)
            tsig = a.get("tech_signature", "")
            norm_tsig = _normalize_tech_str(tsig)

            if norm_aid and (norm_aid in norm_part or norm_part in norm_aid):
                return aid
            if norm_tsig and (norm_tsig in norm_part or norm_part in norm_tsig):
                return aid

            # Match planet names and aspect type
            op = a.get("owner_planet", "").lower()
            pp = a.get("partner_planet", "").lower()
            if op and pp and _normalize_tech_str(op) in norm_part and _normalize_tech_str(pp) in norm_part:
                return aid

    return None


def _parse_llm_json(raw_text: str) -> Any:
    """Parse LLM JSON output, tolerating markdown fences and surrounding prose."""
    text = raw_text.strip()
    if text.startswith("```"):
        # Strip ```json ... ``` fences
        text = text.split("```", 2)[1] if text.count("```") >= 2 else text
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip().rstrip("`").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Last resort: extract the outermost {...} block (prose around JSON)
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _find_house(planet_lon: float, houses: list[dict[str, Any]]) -> int:
    if not houses:
        return 1
    sorted_houses = sorted(houses, key=lambda h: int(h.get("number", 0)))
    for i in range(len(sorted_houses)):
        curr_h = sorted_houses[i]
        next_h = sorted_houses[(i + 1) % len(sorted_houses)]
        c_cusp = float(curr_h["cusp"])
        n_cusp = float(next_h["cusp"])
        if c_cusp <= n_cusp:
            if c_cusp <= planet_lon < n_cusp:
                return int(curr_h["number"])
        else:
            if planet_lon >= c_cusp or planet_lon < n_cusp:
                return int(curr_h["number"])
    return 1


# START_BLOCK: SYNASTRY_SERVICE
class SynastryService:
    """High-level orchestration service for synastry features."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_partner_and_report(
        self,
        user_id: uuid.UUID,
        body: PartnerCreate,
    ) -> tuple[SynastryPartner, SynastryReport]:
        """Validate profile, deduplicate, consume 1 credit in one DB transaction, and create records."""
        # 1. Profile completeness check
        p_stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        p_res = await self.db.execute(p_stmt)
        user_profile = p_res.scalar_one_or_none()

        if not user_profile or not user_profile.birthday or not user_profile.birth_lat:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User birth profile must be complete to calculate synastry.",
            )

        b_time_str = body.birth_time.isoformat() if body.birth_time else None
        partner_hash = _compute_partner_hash(
            owner_id=user_id,
            name=body.name,
            birth_date_str=body.birth_date.isoformat(),
            birth_time_str=b_time_str,
            city=body.birth_city,
        )

        # 2. Deduplication check
        dup_stmt = select(SynastryPartner).where(
            SynastryPartner.owner_id == user_id,
            SynastryPartner.partner_input_hash == partner_hash,
            SynastryPartner.invalidated_at.is_(None),
        )
        dup_res = await self.db.execute(dup_stmt)
        if dup_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Partner '{body.name}' already exists.",
            )

        # 3. Credit spend in ONE DB transaction
        credit_stmt = (
            select(HoraryCredit)
            .where(
                HoraryCredit.user_id == user_id,
                HoraryCredit.amount > HoraryCredit.used_amount,
            )
            .order_by(HoraryCredit.created_at.asc())
            .limit(1)
        )
        credit_res = await self.db.execute(credit_stmt)
        credit = credit_res.scalar_one_or_none()

        if not credit:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Insufficient credits for synastry report.",
            )

        credit.used_amount += 1

        partner = SynastryPartner(
            id=uuid.uuid4(),
            owner_id=user_id,
            name=body.name.strip(),
            relation_type=body.relation,
            birth_date=body.birth_date,
            birth_time=body.birth_time,
            birth_city=body.birth_city,
            birth_lat=body.birth_lat,
            birth_lon=body.birth_lon,
            birth_tz=body.birth_tz,
            precision=body.birth_time_precision,
            partner_input_hash=partner_hash,
        )
        self.db.add(partner)

        report = SynastryReport(
            id=uuid.uuid4(),
            owner_id=user_id,
            partner_id=partner.id,
            owner_profile_hash=f"{user_profile.birthday.isoformat()}_{user_profile.birth_lat}",
            state="pending",
            stage="init",
            attempt_count=0,
        )
        self.db.add(report)

        spend = SynastryCreditSpend(
            id=uuid.uuid4(),
            user_id=user_id,
            credit_id=credit.id,
            report_id=report.id,
            amount=1,
            idempotency_key=body.idempotency_key or str(uuid.uuid4()),
        )
        self.db.add(spend)

        # Commit DB transaction BEFORE external calls
        await self.db.commit()
        await self.db.refresh(partner)
        await self.db.refresh(report)

        return partner, report

    async def _fail_and_refund(
        self,
        report: SynastryReport,
        error_code: str,
        error_message: str,
    ) -> SynastryReport:
        report.state = "failed"
        report.error_code = error_code
        report.error_message = error_message
        log_event(
            "system.error",
            level="error",
            msg=f"synastry report failed: {error_code}",
            payload={"report_id_hash": hash_log_identifier("report", report.id), "error_code": error_code},
        )

        # Refund credit spend if not already refunded
        spend_stmt = select(SynastryCreditSpend).where(
            SynastryCreditSpend.report_id == report.id,
            SynastryCreditSpend.refunded_at.is_(None),
        )
        spend_res = await self.db.execute(spend_stmt)
        spend = spend_res.scalar_one_or_none()

        if spend:
            now = datetime.now(timezone.utc)
            spend.refunded_at = now
            credit_stmt = select(HoraryCredit).where(HoraryCredit.id == spend.credit_id)
            credit_res = await self.db.execute(credit_stmt)
            credit = credit_res.scalar_one_or_none()
            if credit and credit.used_amount > 0:
                credit.used_amount -= 1

        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def _fetch_sidecar_synastry(
        self,
        user_profile: UserProfile,
        partner: SynastryPartner,
    ) -> dict[str, Any]:
        owner_time = user_profile.birth_time.isoformat()[:5] if user_profile.birth_time else "12:00"
        partner_time = partner.birth_time.isoformat()[:5] if partner.birth_time else None

        owner_lat = float(user_profile.birth_lat) if user_profile.birth_lat is not None else 0.0
        owner_hs = "WHOLE_SIGN" if abs(owner_lat) >= 60 else "PLACIDUS"

        req_payload = {
            "owner_birth_date": user_profile.birthday.isoformat() if user_profile.birthday else "1990-01-01",
            "owner_birth_time": owner_time,
            "owner_birth_lat": owner_lat,
            "owner_birth_lon": float(user_profile.birth_lon) if user_profile.birth_lon is not None else 0.0,
            "owner_birth_tz": user_profile.birth_tz or "UTC",
            "partner_birth_date": partner.birth_date.isoformat(),
            "partner_birth_time": partner_time,
            "partner_birth_lat": float(partner.birth_lat) if partner.birth_lat is not None else None,
            "partner_birth_lon": float(partner.birth_lon) if partner.birth_lon is not None else None,
            "partner_birth_tz": partner.birth_tz,
            "partner_birth_time_precision": partner.precision,
            "house_system": owner_hs,
        }

        url = f"{settings.solarsage_url}/v1/synastry"
        log_event("sidecar.called", msg="POST /v1/synastry")
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, json=req_payload)
            resp.raise_for_status()
            return resp.json()

    async def _generate_llm_narrative(
        self,
        scoring_res: Any,
        det_payload: dict[str, Any],
        precision_mode: str,
    ) -> dict[str, Any] | None:
        prompt_dict = build_report_prompt(
            score=scoring_res.score,
            status=scoring_res.status,
            counters=scoring_res.counters,
            aspects=det_payload["aspects"],
            partner_precision=precision_mode,
            house_overlays=det_payload.get("house_overlays", []),
        )

        try:
            llm_client = LLMClient()
            log_event("llm.requested", msg="synastry narrative requested")
            raw_text = await llm_client._generate_text(
                prompt=f"{prompt_dict['system']}\n\n{prompt_dict['user']}",
                max_tokens=2000,
            )

            if not raw_text:
                log_event("llm.response_rejected", level="warning", msg="synastry narrative: empty response")
                return None

            parsed = _parse_llm_json(raw_text)
            if isinstance(parsed, dict):
                valid, _ = validate_llm_output(parsed, report_precision=precision_mode)
                if valid:
                    log_event("llm.response_validated", msg="synastry narrative validated")
                    return parsed
            log_event("llm.response_rejected", level="warning", msg="synastry narrative: validation failed")
        except Exception as exc:
            log_event(
                "llm.response_rejected",
                level="warning",
                msg=f"synastry narrative: generation error: {type(exc).__name__}",
            )

        return None

    async def run_report_pipeline(self, report_id: uuid.UUID) -> SynastryReport:
        """State machine pipeline: PENDING -> CALCULATING -> NARRATIVE_GENERATING -> READY."""
        stmt = select(SynastryReport).where(
            SynastryReport.id == report_id,
            SynastryReport.invalidated_at.is_(None),
        )
        res = await self.db.execute(stmt)
        report = res.scalar_one_or_none()

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        bind_log_context(slice="W-SYNASTRY-MVP", module="M-SYNASTRY-SERVICE", block="SYNASTRY_SERVICE")

        # Read partner & owner profile
        p_stmt = select(SynastryPartner).where(SynastryPartner.id == report.partner_id)
        p_res = await self.db.execute(p_stmt)
        partner = p_res.scalar_one_or_none()

        profile_stmt = select(UserProfile).where(UserProfile.user_id == report.owner_id)
        profile_res = await self.db.execute(profile_stmt)
        user_profile = profile_res.scalar_one_or_none()

        if not partner or not user_profile or not user_profile.birthday:
            return await self._fail_and_refund(
                report, "PROFILE_OR_PARTNER_MISSING", "User profile or partner birth data is missing"
            )

        precision_mode = partner.precision or "exact"

        # Step 1: CALCULATING (Sidecar + Scoring engine)
        report.state = "calculating"
        report.stage = "scoring"
        await self.db.commit()

        # Call sidecar
        try:
            sidecar_data = await self._fetch_sidecar_synastry(user_profile, partner)
        except Exception as exc:
            return await self._fail_and_refund(
                report, "SIDECAR_FAILED", f"Sidecar calculation failed: {exc}"
            )

        # Map sidecar cross_aspects to RawAspectInput
        raw_aspects = [
            RawAspectInput(
                owner_planet=ca.get("owner_planet", ""),
                partner_planet=ca.get("partner_planet", ""),
                aspect_type=ca.get("aspect_type", ""),
                orb_degrees=float(ca.get("orb_degrees", 0.0)),
                applying=ca.get("applying"),
            )
            for ca in sidecar_data.get("cross_aspects", [])
        ]

        scoring_res = SynastryScoringEngine.calculate_score(
            aspects=raw_aspects,
            partner_time_precision=precision_mode,
        )
        log_event(
            "scoring.computed",
            msg="synastry scoring computed",
            payload={"score": scoring_res.score, "status": scoring_res.status, "aspects_count": len(raw_aspects)},
        )

        # Format owner and partner planet points for wheel geometry
        formatted_owner_planets = [
            {
                "id": f"owner_{p.get('name', '').lower()}",
                "owner": "user",
                "planet": p.get("name", ""),
                "longitude": float(p.get("longitude", 0.0)),
                "sign": p.get("sign"),
                "retrograde": bool(p.get("retrograde", False)),
                "house": None,
                "house_reliable": False,
            }
            for p in sidecar_data.get("owner_planets", [])
        ]

        partner_houses = sidecar_data.get("partner_houses")
        houses_avail = (
            bool(sidecar_data.get("precision_flags", {}).get("houses_available", False))
            and bool(partner_houses)
        )

        formatted_partner_planets = []
        for p in sidecar_data.get("partner_planets", []):
            p_lon = float(p.get("longitude", 0.0))
            h_num = _find_house(p_lon, partner_houses or []) if houses_avail else None
            formatted_partner_planets.append({
                "id": f"partner_{p.get('name', '').lower()}",
                "owner": "partner",
                "planet": p.get("name", ""),
                "longitude": p_lon,
                "sign": p.get("sign"),
                "retrograde": bool(p.get("retrograde", False)),
                "house": h_num,
                "house_reliable": houses_avail,
            })

        owner_houses = sidecar_data.get("owner_houses") or []
        owner_hs = sidecar_data.get("house_system") or sidecar_data.get("owner_house_system") or "PLACIDUS"
        partner_hs = sidecar_data.get("partner_house_system") or owner_hs

        from app.services.astro_utils import find_house
        PLANET_RU_NAME = {
            "Sun": "Солнце", "Moon": "Луна", "Mercury": "Меркурий", "Venus": "Венера",
            "Mars": "Марс", "Jupiter": "Юпитер", "Saturn": "Сатурн", "Uranus": "Уран",
            "Neptune": "Нептун", "Pluto": "Плутон", "Ascendant": "ASC", "ASC": "ASC",
        }

        house_overlays = []
        # 1. Partner planets into Owner's houses
        for pp in sidecar_data.get("partner_planets", []):
            p_lon = float(pp.get("longitude", 0.0))
            p_name = pp.get("name", "")
            if p_name in ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"):
                h_num = find_house(p_lon, owner_houses)
                if h_num:
                    p_ru = PLANET_RU_NAME.get(p_name, p_name)
                    tech = f"Его {p_ru} → твой {h_num} дом"
                    house_overlays.append({
                        "tech": tech,
                        "planet": p_name,
                        "planet_owner": "partner",
                        "house": h_num,
                        "house_system": owner_hs,
                    })

        # 2. Owner planets into Partner's houses (if partner houses available and exact)
        if houses_avail and partner_houses:
            for op in sidecar_data.get("owner_planets", []):
                p_lon = float(op.get("longitude", 0.0))
                p_name = op.get("name", "")
                if p_name in ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"):
                    h_num = find_house(p_lon, partner_houses)
                    if h_num:
                        p_ru = PLANET_RU_NAME.get(p_name, p_name)
                        tech = f"Твоя {p_ru} → его {h_num} дом"
                        house_overlays.append({
                            "tech": tech,
                            "planet": p_name,
                            "planet_owner": "owner",
                            "house": h_num,
                            "house_system": partner_hs,
                        })

        det_payload = {
            "score": scoring_res.score,
            "status": scoring_res.status,
            "counters": scoring_res.counters,
            "precision_flags": scoring_res.precision_flags,
            "owner_planets": formatted_owner_planets,
            "partner_planets": formatted_partner_planets,
            "house_overlays": house_overlays,
            "house_system": owner_hs,
            "aspects": [
                {
                    "id": a.id,
                    "owner_planet": a.owner_planet,
                    "partner_planet": a.partner_planet,
                    "aspect": a.aspect,
                    "orb_degrees": a.orb_degrees,
                    "tone": a.tone,
                    "confidence": a.confidence,
                    "weight": a.weight,
                    "tech_signature": a.tech_signature,
                }
                for a in scoring_res.aspects
            ],
            "spheres": [
                {
                    "id": s.id,
                    "title": s.title,
                    "score": s.score,
                    "tone": s.tone,
                }
                for s in scoring_res.spheres
            ],
        }

        report.deterministic_payload_json = json.dumps(det_payload, ensure_ascii=False)

        # Step 2: NARRATIVE_GENERATING
        report.state = "narrative_generating"
        report.stage = "llm_narrative"

        if report.attempt_count >= 2:
            return await self._fail_and_refund(
                report, "MAX_ATTEMPTS_EXCEEDED", "LLM generation reached max attempts limit"
            )

        report.attempt_count += 1
        await self.db.commit()

        # LLM Generation loop (max 2 attempts across pipeline runs)
        narrative_data = await self._generate_llm_narrative(scoring_res, det_payload, precision_mode)

        if not narrative_data and report.attempt_count < 2:
            report.attempt_count += 1
            await self.db.commit()
            narrative_data = await self._generate_llm_narrative(scoring_res, det_payload, precision_mode)

        if not narrative_data:
            return await self._fail_and_refund(
                report, "LLM_VALIDATION_FAILED", "LLM narrative generation or validation failed"
            )

        raw_translations = narrative_data.get("translations", [])
        det_aspects = det_payload.get("aspects", [])
        matched_translations = []
        for t in raw_translations:
            if isinstance(t, dict):
                aspects_list = det_aspects if isinstance(det_aspects, list) else []
                t_aspect_id = t.get("aspect_id") or t.get("aspectId") or _match_translation_aspect_id(t.get("tech"), aspects_list)
                matched_translations.append({
                    "tone": t.get("tone"),
                    "title": t.get("title", ""),
                    "aspect_id": t_aspect_id,
                    "tech": t.get("tech"),
                    "text": t.get("text"),
                    "scene": t.get("scene"),
                })

        narrative_payload = {
            "verdict": narrative_data.get("verdict") or f"Совместимость пары ({scoring_res.score}/100)",
            "summary": narrative_data.get("summary", "Анализ взаимодействия завершён."),
            "hero_title": narrative_data.get("hero_title"),
            "hero_description": narrative_data.get("hero_description"),
            "translations": matched_translations,
            "house_overlays": narrative_data.get("house_overlays", []),
            "sphere_texts": narrative_data.get("spheres") if isinstance(narrative_data.get("spheres"), dict) else {},
        }

        report.narrative_payload_json = json.dumps(narrative_payload, ensure_ascii=False)
        report.state = "ready"
        report.stage = "done"
        report.error_code = None
        report.error_message = None

        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def get_aspect_drilldown(
        self,
        user_id: uuid.UUID,
        partner_id: uuid.UUID,
        aspect_id: str,
    ) -> AspectDrilldown:
        """Get or generate aspect drilldown interpretation. Owner-scoped (404 if unowned)."""
        p_stmt = select(SynastryPartner).where(
            SynastryPartner.id == partner_id,
            SynastryPartner.owner_id == user_id,
            SynastryPartner.invalidated_at.is_(None),
        )
        p_res = await self.db.execute(p_stmt)
        partner = p_res.scalar_one_or_none()

        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")

        r_stmt = select(SynastryReport).where(
            SynastryReport.owner_id == user_id,
            SynastryReport.partner_id == partner.id,
            SynastryReport.invalidated_at.is_(None),
        ).order_by(SynastryReport.created_at.desc()).limit(1)
        r_res = await self.db.execute(r_stmt)
        report = r_res.scalar_one_or_none()

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        # 1. Locate aspect in report's deterministic_payload_json
        target_aspect = None
        if report.deterministic_payload_json:
            try:
                det = json.loads(report.deterministic_payload_json)
                for a in det.get("aspects", []):
                    if a.get("id") == aspect_id:
                        target_aspect = a
                        break
            except Exception:
                pass

        if not target_aspect:
            raise HTTPException(status_code=404, detail="Aspect not found in report")

        # Map planet metadata & aspect fields
        op_key = target_aspect.get("owner_planet", "Sun")
        pp_key = target_aspect.get("partner_planet", "Moon")
        asp_type = target_aspect.get("aspect", "").lower()
        orb_val = target_aspect.get("orb_degrees")

        ASPECT_SYMBOLS = {"conjunction": "☌", "conjunct": "☌", "trine": "△", "sextile": "⚹", "square": "□", "opposition": "☍", "quincunx": "⚹"}
        ASPECT_KIND_LABELS = {"conjunction": "Соединение", "conjunct": "Соединение", "trine": "Тригон", "sextile": "Секстиль", "square": "Квадрат", "opposition": "Оппозиция", "quincunx": "Квиконс"}
        PLANET_SYMBOLS = {"Sun": "☉", "Moon": "☽", "Mercury": "☿", "Venus": "♀", "Mars": "♂", "Jupiter": "♃", "Saturn": "♄", "Uranus": "♅", "Neptune": "♆", "Pluto": "♇", "Ascendant": "ASC", "ASC": "ASC", "Midheaven": "MC", "MC": "MC"}
        PLANET_RU_NAMES = {"Sun": "Солнце", "Moon": "Луна", "Mercury": "Меркурий", "Venus": "Венера", "Mars": "Марс", "Jupiter": "Юпитер", "Saturn": "Сатурн", "Uranus": "Уран", "Neptune": "Нептун", "Pluto": "Плутон", "Ascendant": "Асцендент", "ASC": "Асцендент", "Midheaven": "MC", "MC": "MC"}

        asp_symbol = ASPECT_SYMBOLS.get(asp_type, "△")
        asp_kind_label = ASPECT_KIND_LABELS.get(asp_type, asp_type.capitalize())
        orb_txt = f"орб {_format_orb_label(orb_val)}" if orb_val is not None else None

        op_info = {
            "key": op_key,
            "label": PLANET_RU_NAMES.get(op_key, op_key),
            "glyph": PLANET_SYMBOLS.get(op_key, op_key[:2]),
            "meaning": PLANET_MEANINGS.get(op_key, "Функция планеты в натальной карте."),
        }
        pp_info = {
            "key": pp_key,
            "label": PLANET_RU_NAMES.get(pp_key, pp_key),
            "glyph": PLANET_SYMBOLS.get(pp_key, pp_key[:2]),
            "meaning": PLANET_MEANINGS.get(pp_key, "Функция планеты в натальной карте."),
        }
        asp_mechanics = ASPECT_MEANINGS.get(asp_type, {}).get("explanation", "")

        # 2. Check existing SynastryAspectDetail
        ad_stmt = select(SynastryAspectDetail).where(
            SynastryAspectDetail.report_id == report.id,
            SynastryAspectDetail.aspect_id == aspect_id,
        )
        ad_res = await self.db.execute(ad_stmt)
        detail = ad_res.scalar_one_or_none()

        if detail and detail.state == "ready" and detail.payload_json:
            data = json.loads(detail.payload_json)
            scenes_data = data.get("scenes", [])
            parsed_scenes = [
                AspectDrilldownScene(title=s.get("title", ""), text=s.get("text", ""))
                for s in scenes_data if isinstance(s, dict)
            ]
            owner_p = PlanetInfo(**data["owner_planet"]) if isinstance(data.get("owner_planet"), dict) else PlanetInfo(**op_info)
            partner_p = PlanetInfo(**data["partner_planet"]) if isinstance(data.get("partner_planet"), dict) else PlanetInfo(**pp_info)

            return AspectDrilldown(
                aspect_id=aspect_id,
                title=data.get("title", target_aspect.get("tech_signature") or aspect_id),
                tone=data.get("tone", target_aspect.get("tone", "good")),
                tech_signature=data.get("tech_signature", target_aspect.get("tech_signature")),
                aspect_symbol=data.get("aspect_symbol", asp_symbol),
                aspect_kind_label=data.get("aspect_kind_label", asp_kind_label),
                orb_text=data.get("orb_text", orb_txt),
                headline=data.get("headline") or data.get("title"),
                owner_planet=owner_p,
                partner_planet=partner_p,
                aspect_mechanics=data.get("aspect_mechanics", asp_mechanics),
                explanation=data.get("explanation") or data.get("intro") or "",
                scenes=parsed_scenes,
                repairs=data.get("repairs", []),
                not_means=data.get("not_means", []),
                scenario=data.get("scenario"),
                advice=data.get("advice"),
            )

        # 3. Generate aspect drilldown via LLM (one retry on invalid output)
        prompt_dict = build_drilldown_prompt(target_aspect)
        attempt_count = (detail.attempt_count if detail else 0) + 1

        llm_data = None
        err_msg = None

        for attempt in range(2):
            try:
                llm_client = LLMClient()
                log_event("llm.requested", msg="synastry drilldown requested", payload={"aspect_id": aspect_id, "attempt": attempt + 1})
                raw_text = await llm_client._generate_text(
                    prompt=f"{prompt_dict['system']}\n\n{prompt_dict['user']}",
                    max_tokens=2000,
                )
                if raw_text:
                    parsed = _parse_llm_json(raw_text)
                    if isinstance(parsed, dict):
                        valid, err_reason = validate_drilldown_output(parsed)
                        if valid:
                            llm_data = parsed
                            log_event("llm.response_validated", msg="synastry drilldown validated", payload={"aspect_id": aspect_id})
                            break
                        else:
                            err_msg = err_reason
                            log_event("llm.response_rejected", level="warning", msg="synastry drilldown: validation failed", payload={"aspect_id": aspect_id})
                else:
                    log_event("llm.response_rejected", level="warning", msg="synastry drilldown: empty response", payload={"aspect_id": aspect_id})
            except Exception as exc:
                err_msg = str(exc)
                log_event("llm.response_rejected", level="warning", msg="synastry drilldown: generation error", payload={"aspect_id": aspect_id})

        if not llm_data:
            # LLM failure: record failed detail, keep base report READY, no refund
            if not detail:
                detail = SynastryAspectDetail(
                    id=uuid.uuid4(),
                    report_id=report.id,
                    aspect_id=aspect_id,
                    prompt_version="1",
                    state="failed",
                    attempt_count=attempt_count,
                    error_code="LLM_VALIDATION_FAILED",
                    error_message=err_msg or "Aspect drilldown LLM generation failed",
                )
                self.db.add(detail)
            else:
                detail.state = "failed"
                detail.attempt_count = attempt_count
                detail.error_code = "LLM_VALIDATION_FAILED"
                detail.error_message = err_msg or "Aspect drilldown LLM generation failed"

            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate aspect drilldown",
            )

        # Map LLM JSON output to AspectDrilldown format
        scenes_list = llm_data.get("scenes", [])
        repairs_list = llm_data.get("repairs", [])
        not_means_list = llm_data.get("not_means", [])

        scenario_text = "\n".join(
            f"• {s.get('title', '')}: {s.get('text', '')}" if isinstance(s, dict) else str(s)
            for s in scenes_list
        ) if isinstance(scenes_list, list) else str(scenes_list)

        advice_text = "\n".join(str(r) for r in repairs_list) if isinstance(repairs_list, list) else str(repairs_list)

        # Strip leading enumeration the LLM may add ("1. ", "2) ") — the UI renders its own numbered badges
        repairs_clean = (
            [re.sub(r"^\s*\d+[\.\)]\s*", "", str(r)) for r in repairs_list]
            if isinstance(repairs_list, list)
            else repairs_list
        )

        drilldown_payload = {
            "aspect_id": aspect_id,
            "title": target_aspect.get("tech_signature") or f"{op_info['label']} {asp_kind_label.lower()} {pp_info['label']}",
            "tone": target_aspect.get("tone", "good"),
            "tech_signature": target_aspect.get("tech_signature") or aspect_id,
            "aspect_symbol": asp_symbol,
            "aspect_kind_label": asp_kind_label,
            "orb_text": orb_txt,
            "headline": llm_data.get("headline") or llm_data.get("title") or f"{op_info['label']} {asp_kind_label.lower()} {pp_info['label']}",
            "owner_planet": op_info,
            "partner_planet": pp_info,
            "aspect_mechanics": asp_mechanics,
            "explanation": llm_data.get("intro") or llm_data.get("explanation", ""),
            "scenes": scenes_list if isinstance(scenes_list, list) else [],
            "repairs": repairs_clean,
            "not_means": not_means_list if isinstance(not_means_list, list) else [],
            "scenario": scenario_text,
            "advice": advice_text,
        }

        if not detail:
            detail = SynastryAspectDetail(
                id=uuid.uuid4(),
                report_id=report.id,
                aspect_id=aspect_id,
                prompt_version="1",
                state="ready",
                attempt_count=attempt_count,
                payload_json=json.dumps(drilldown_payload, ensure_ascii=False),
            )
            self.db.add(detail)
        else:
            detail.state = "ready"
            detail.attempt_count = attempt_count
            detail.payload_json = json.dumps(drilldown_payload, ensure_ascii=False)
            detail.error_code = None
            detail.error_message = None

        await self.db.commit()

        parsed_scenes_obj = [
            AspectDrilldownScene(title=s.get("title", ""), text=s.get("text", ""))
            for s in drilldown_payload["scenes"] if isinstance(s, dict)
        ]

        return AspectDrilldown(
            aspect_id=aspect_id,
            title=drilldown_payload["title"],
            tone=drilldown_payload["tone"],
            tech_signature=drilldown_payload["tech_signature"],
            aspect_symbol=drilldown_payload["aspect_symbol"],
            aspect_kind_label=drilldown_payload["aspect_kind_label"],
            orb_text=drilldown_payload["orb_text"],
            headline=drilldown_payload["headline"],
            owner_planet=PlanetInfo(**drilldown_payload["owner_planet"]),
            partner_planet=PlanetInfo(**drilldown_payload["partner_planet"]),
            aspect_mechanics=drilldown_payload["aspect_mechanics"],
            explanation=drilldown_payload["explanation"],
            scenes=parsed_scenes_obj,
            repairs=drilldown_payload["repairs"],
            not_means=drilldown_payload["not_means"],
            scenario=drilldown_payload["scenario"],
            advice=drilldown_payload["advice"],
        )

    async def submit_feedback(
        self,
        user_id: uuid.UUID,
        partner_id: uuid.UUID,
        value: str,
    ) -> SynastryFeedbackRead:
        """Submit reality check feedback. Owner-scoped (404 if unowned)."""
        p_stmt = select(SynastryPartner).where(
            SynastryPartner.id == partner_id,
            SynastryPartner.owner_id == user_id,
            SynastryPartner.invalidated_at.is_(None),
        )
        p_res = await self.db.execute(p_stmt)
        partner = p_res.scalar_one_or_none()

        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")

        r_stmt = select(SynastryReport).where(
            SynastryReport.owner_id == user_id,
            SynastryReport.partner_id == partner.id,
            SynastryReport.invalidated_at.is_(None),
        ).order_by(SynastryReport.created_at.desc()).limit(1)
        r_res = await self.db.execute(r_stmt)
        report = r_res.scalar_one_or_none()

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        fb_stmt = select(SynastryFeedback).where(
            SynastryFeedback.user_id == user_id,
            SynastryFeedback.report_id == report.id,
        )
        fb_res = await self.db.execute(fb_stmt)
        fb = fb_res.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if fb:
            fb.value = value
            fb.updated_at = now
        else:
            fb = SynastryFeedback(
                id=uuid.uuid4(),
                user_id=user_id,
                report_id=report.id,
                value=value,
                created_at=now,
                updated_at=now,
            )
            self.db.add(fb)

        await self.db.commit()
        await self.db.refresh(fb)

        return SynastryFeedbackRead(
            report_id=report.id,
            value=fb.value,
            updated_at=fb.updated_at,
        )

    async def delete_partner(
        self,
        user_id: uuid.UUID,
        partner_id: uuid.UUID,
    ) -> None:
        """Soft delete partner and partner's reports. Owner-scoped (404 if unowned)."""
        p_stmt = select(SynastryPartner).where(
            SynastryPartner.id == partner_id,
            SynastryPartner.owner_id == user_id,
            SynastryPartner.invalidated_at.is_(None),
        )
        p_res = await self.db.execute(p_stmt)
        partner = p_res.scalar_one_or_none()

        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")

        now = datetime.now(timezone.utc)
        partner.invalidated_at = now

        r_stmt = select(SynastryReport).where(
            SynastryReport.owner_id == user_id,
            SynastryReport.partner_id == partner.id,
            SynastryReport.invalidated_at.is_(None),
        )
        r_res = await self.db.execute(r_stmt)
        reports = list(r_res.scalars().all())

        for rep in reports:
            rep.invalidated_at = now

        await self.db.commit()
# END_BLOCK: SYNASTRY_SERVICE

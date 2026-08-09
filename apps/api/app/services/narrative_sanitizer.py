# ############################################################################
# AI_HEADER: MODULE_NARRATIVE_SANITIZER — fail-closed guard for public narrative text.
# ROLE: Rejects provider text that exposes machine signal identifiers or
#       enumeration artifacts before it can enter a public API response.
# ############################################################################

# START_MODULE_CONTRACT: M-NARRATIVE-SANITIZER
# purpose: Validate public narrative text against known machine-token leaks and
#   deterministic sphere/facet/polarity grounding rules.
# owns:
#   - apps/api/app/services/narrative_sanitizer.py
# inputs: provider-generated narrative text and, for grounding, its selected
#   product sphere/facets plus polarity.
# outputs: stripped safe text or None when the text must not be published;
#   grounding violations are reported as booleans or safe rule metadata without
#   exposing raw text.
# dependencies: Python standard library only.
# side_effects: none; pure validation.
# emitted_logs: none (the narrative service owns claim-null instrumentation).
# invariants: rejected text is never returned as a sanitized value; an unknown
#   sphere, facet, or polarity fails closed; hard cross-sphere/domain language
#   and forbidden tokens remain fail-closed; soft connective words do not
#   authorize a foreign hard facet.
# failure_policy: fail closed with None for blank or forbidden text.
# END_MODULE_CONTRACT: M-NARRATIVE-SANITIZER

# START_MODULE_MAP: M-NARRATIVE-SANITIZER
# public_entrypoints:
#   - has_forbidden_narrative_tokens
#   - sanitize_narrative_text
#   - has_narrative_grounding_violation
#   - explain_narrative_grounding_violation
# semantic_blocks:
#   - FORBIDDEN_TOKENS: machine prefixes, generic Planet labels, and list artifacts.
#   - GROUNDING: hard/soft sphere/facet vocabulary, scope checks, health safety,
#     lot-name masking, polarity-antonym checks, and negation windows.
#   - SANITIZE: deterministic trim-and-reject boundary.
# owned_tests:
#   - apps/api/tests/test_narrative_sanitizer.py
# END_MODULE_MAP: M-NARRATIVE-SANITIZER

from __future__ import annotations

import re
from collections.abc import Collection, Mapping


_FORBIDDEN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?<![A-Za-zА-Яа-я0-9_])(?:Transit_|Natal_)[A-Za-z0-9_]*", re.IGNORECASE),
    re.compile(r"\bPlanet\b", re.IGNORECASE),
    re.compile(r"(?<![A-Za-zА-Яа-я0-9_])M\s*,\s*[A-Za-zА-Яа-я][A-Za-zА-Яа-я0-9_-]*", re.IGNORECASE),
)


# These stems are deliberately conservative: they cover the twelve public
# labels and their obvious Russian forms without turning ordinary action copy
# ("шаг", "фокус", "результат") into a sphere claim. The keys are the only
# product-sphere vocabulary accepted by the convergence narrative boundary.
_SPHERE_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "work": (re.compile(r"(?<!\w)(?:работ\w*|статус\w*)", re.IGNORECASE),),
    "finance": (re.compile(r"(?<!\w)(?:финанс\w*|деньг\w*|ресурс\w*)", re.IGNORECASE),),
    "documents": (
        re.compile(r"(?<!\w)(?:документ\w*|формальност\w*|бумаг\w*|договор\w*)", re.IGNORECASE),
    ),
    "relationships": (
        re.compile(r"(?<!\w)(?:отношени\w*|близост\w*|партн[её]р\w*)", re.IGNORECASE),
    ),
    "sport": (
        re.compile(r"(?<!\w)(?:движен\w*|трениров\w*|спорт\w*)", re.IGNORECASE),
    ),
    "communication": (
        re.compile(r"(?<!\w)(?:общен\w*|разговор\w*|переписк\w*|контакт\w*)", re.IGNORECASE),
    ),
    "health": (
        re.compile(r"(?<!\w)(?:самочув\w*|здоров\w*|режим\w*|восстанов\w*|тонус\w*)", re.IGNORECASE),
    ),
    "home_family": (
        re.compile(r"(?<!\w)(?:дом\w*|семь\w*|жиль\w*|семейн\w*)", re.IGNORECASE),
    ),
    "travel": (
        re.compile(r"(?<!\w)(?:поезд\w*|маршрут\w*|дорог\w*)", re.IGNORECASE),
    ),
    "creativity": (re.compile(r"(?<!\w)(?:творч\w*|креатив\w*)", re.IGNORECASE),),
    "study": (
        re.compile(r"(?<!\w)(?:обуч\w*|уч[её]б\w*|образован\w*)", re.IGNORECASE),
    ),
    "friends_goals": (
        re.compile(r"(?<!\w)(?:друз\w*|сообществ\w*|план\w*|цел(?:ь|и|ями|ям|ей|ях)\w*)", re.IGNORECASE),
    ),
}

# A sphere word can be ordinary connective language («семья», «общение»,
# «ресурс») rather than a hard cross-sphere claim. Keep the complete table
# above for deterministic detection/audit, but only these high-signal terms
# reject a foreign sphere. Explicit «сфера отношений» remains hard.
_HARD_SPHERE_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "work": (
        re.compile(r"(?<!\w)(?:карьер\w*|статус\w*|начальник\w*|профессиональн\w*)", re.IGNORECASE),
    ),
    "finance": (
        re.compile(r"(?<!\w)(?:финанс\w*|деньг\w*|кредит\w*|налог\w*)", re.IGNORECASE),
    ),
    "documents": (
        re.compile(r"(?<!\w)(?:документ\w*|формальност\w*|бумаг\w*|договор\w*)", re.IGNORECASE),
    ),
    "relationships": (
        re.compile(
            r"(?<!\w)(?:брак\w*|супруг\w*|партн[её]р\w*|сфер\w*\s+отношени\w*)",
            re.IGNORECASE,
        ),
    ),
    "sport": (
        re.compile(r"(?<!\w)(?:движен\w*|трениров\w*|спорт\w*)", re.IGNORECASE),
    ),
    "communication": (
        re.compile(r"(?<!\w)(?:коммуникац\w*|переговор\w*|аудитор\w*|публичн\w* выступ\w*)", re.IGNORECASE),
    ),
    "health": (
        re.compile(r"(?<!\w)(?:здоров\w*|болезн\w*|симптом\w*|лечен\w*)", re.IGNORECASE),
    ),
    "home_family": (
        re.compile(r"(?<!\w)(?:жиль\w*|недвижим\w*|семейн\w* корн\w*|домашн\w* баз\w*)", re.IGNORECASE),
    ),
    "travel": (
        re.compile(r"(?<!\w)(?:поезд\w*|маршрут\w*|дорог\w*)", re.IGNORECASE),
    ),
    "creativity": (re.compile(r"(?<!\w)(?:творч\w*|креатив\w*)", re.IGNORECASE),),
    "study": (
        re.compile(r"(?<!\w)(?:обуч\w*|уч[её]б\w*|образован\w*)", re.IGNORECASE),
    ),
    "friends_goals": (
        re.compile(r"(?<!\w)(?:друз\w*|сообществ\w*)", re.IGNORECASE),
    ),
}

_RELATED_SPHERES: dict[str, frozenset[str]] = {
    # The resolver assigns one sphere to one physical signal. Narrative text
    # therefore cannot borrow a neighbouring sphere as an implicit allowance.
    sphere: frozenset() for sphere in _SPHERE_PATTERNS
}


# A1 audit showed that one undifferentiated facet table treated ordinary
# connective language as a hard domain leak. Hard patterns remain fail-closed:
# credit/tax/debt, purchase/price, career/status, documents, marriage, and the
# S17 phrase «романтических разговорах». The exact false-positive examples
# were `ценности` matching `цен*`, `долгий` matching `долг*`, and everyday
# `тонус`/`разговоры` in otherwise valid sport/relationship claims.
_HARD_FACET_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "daily_work": (re.compile(r"(?:служебн\w*|рабоч\w* нагруз\w*|рабоч\w* задач\w*)", re.IGNORECASE),),
    "career_status": (re.compile(r"(?:карьер\w*|продвижен\w*|публичн\w* роль\w*)", re.IGNORECASE),),
    "personal_money": (re.compile(r"(?:доход\w*|расход\w*|накоплен\w*|личн\w* (?:средств\w*|имуще\w*))", re.IGNORECASE),),
    "shared_money": (re.compile(r"(?:общ\w* бюджет\w*|партнёрск\w* средств\w*|страхов\w*|наслед\w*)", re.IGNORECASE),),
    "purchases_transactions": (
        re.compile(
            r"(?:покуп\w*|продаж\w*|(?<![а-яёА-ЯЁ])цен(?:а|у|ы|е|ой|ою|ами|ам|ах|ник\w*)\b|сделк\w*|транзакц\w*|магазин\w*)",
            re.IGNORECASE,
        ),
    ),
    "financial_obligations": (
        re.compile(r"(?:кредит\w*|долг(?:а|и|ов|у|ом|ами|ам|ах)?\b|налог\w*|рассроч\w*|возврат\w*)", re.IGNORECASE),
    ),
    "admin_documents": (re.compile(r"(?:заявлен\w*|справк\w*|оформлен\w*|переписк\w*)", re.IGNORECASE),),
    "legal_foreign_education_documents": (re.compile(r"(?:юридическ\w*|иностран\w* документ\w*|виз\w*|образовательн\w* документ\w*)", re.IGNORECASE),),
    "contracts": (re.compile(r"(?:контракт\w*|договор\w* между|договорн\w* отношен\w*)", re.IGNORECASE),),
    "financial_documents": (re.compile(r"(?:сч[её]т\w*|кредитн\w* документ\w*|налогов\w* документ\w*|страхов\w* документ\w*)", re.IGNORECASE),),
    "property_documents": (re.compile(r"(?:жиль\w* документ\w*|недвижим\w*|имущественн\w* документ\w*)", re.IGNORECASE),),
    "romance": (re.compile(r"(?:симпат\w*|свидан\w*|романтик\w*|романтическ\w*)", re.IGNORECASE),),
    "partnership": (re.compile(r"(?:партнёр\w*|партнер\w*|брак\w*|супруг\w*)", re.IGNORECASE),),
    "physical_energy": (re.compile(r"(?:телесн\w* энерг\w*|готовност\w* действ\w*)", re.IGNORECASE),),
    "training_routine": (re.compile(r"(?:трениров\w*|режим активност\w*)", re.IGNORECASE),),
    "competition_performance": (re.compile(r"(?:соревн\w*|спортивн\w* выступ\w*|результат\w* выступ\w*)", re.IGNORECASE),),
    "everyday_contacts": (re.compile(r"романтическ\w*\s+(?:разговор\w*|переписк\w*)", re.IGNORECASE),),
    "negotiations": (re.compile(r"(?:переговор\w*|договорённост\w*|договоренност\w*)", re.IGNORECASE),),
    "groups_audience": (re.compile(r"(?:групп\w*|аудитор\w*|сообществ\w*)", re.IGNORECASE),),
    "public_speech_teaching": (re.compile(r"(?:публичн\w* выступ\w*|преподав\w*|лекц\w*)", re.IGNORECASE),),
    "symptoms_routine_treatment": (re.compile(r"(?:симптом\w*|лечен\w*|восстановительн\w* режим\w*)", re.IGNORECASE),),
    "recovery_isolation": (re.compile(r"(?:изоляц\w*|стационар\w*)", re.IGNORECASE),),
    "family_roots": (re.compile(r"(?:родител\w*|семейн\w* корн\w*|домашн\w* баз\w*)", re.IGNORECASE),),
    "housing_property": (re.compile(r"(?:жиль\w*|недвижим\w*|бытов\w* пространств\w*)", re.IGNORECASE),),
    "relocation": (re.compile(r"(?:переезд\w*|перемещен\w* дом\w*)", re.IGNORECASE),),
    "local_travel": (re.compile(r"(?:коротк\w* поезд\w*|местн\w* поезд\w*|локальн\w* маршрут\w*)", re.IGNORECASE),),
    "long_distance_foreign_travel": (re.compile(r"(?:дальн\w* поезд\w*|заграниц\w*|международн\w*)", re.IGNORECASE),),
    "self_expression": (re.compile(r"(?:самовыраж\w*|авторск\w* проявлен\w*)", re.IGNORECASE),),
    "creative_work": (re.compile(r"(?:творческ\w* проект\w*|творческ\w* работ\w*)", re.IGNORECASE),),
    "private_inner_creativity": (re.compile(r"(?:уединённ\w* творчеств\w*|уединенн\w* творчеств\w*|личн\w* творческ\w*)", re.IGNORECASE),),
    "skills_courses": (re.compile(r"(?:навык\w*|курс\w*|базов\w* обуч\w*)", re.IGNORECASE),),
    "higher_education_worldview": (re.compile(r"(?:высш\w* образован\w*|философ\w*|мировоззрен\w*)", re.IGNORECASE),),
    "friends_community": (re.compile(r"(?:друз\w*|сообществ\w* единомышлен\w*|единомышлен\w*)", re.IGNORECASE),),
    "collective_projects": (re.compile(r"(?:совместн\w* проект\w*|коллективн\w* проект\w*)", re.IGNORECASE),),
    "long_term_goals": (re.compile(r"(?:долгосрочн\w* (?:план\w*|направлен\w*|цел\w*)|направлен\w* развит\w*)", re.IGNORECASE),),
}

_SOFT_FACET_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "daily_work": (re.compile(r"рутин\w*", re.IGNORECASE),),
    "purchases_transactions": (re.compile(r"заказ\w*", re.IGNORECASE),),
    "everyday_contacts": (
        re.compile(r"(?:разговор\w*|переписк\w*|повседневн\w* контакт\w*)", re.IGNORECASE),
    ),
    "romance": (re.compile(r"(?:уют\w*|нежн\w*|тепл\w*)", re.IGNORECASE),),
    "partnership": (re.compile(r"(?:близост\w*|взаимн\w*)", re.IGNORECASE),),
    "general_condition": (re.compile(r"(?:самочув\w*|общ\w* состоян\w*|тонус\w*)", re.IGNORECASE),),
    "recovery_isolation": (re.compile(r"отдых\w*", re.IGNORECASE),),
}

_FACET_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    facet: (*_HARD_FACET_PATTERNS.get(facet, ()), *_SOFT_FACET_PATTERNS.get(facet, ()))
    for facet in (*_HARD_FACET_PATTERNS, *_SOFT_FACET_PATTERNS)
}

_FACET_TO_SPHERE: dict[str, str] = {
    facet: sphere
    for sphere, facets in {
        "work": ("daily_work", "career_status"),
        "finance": ("personal_money", "shared_money", "purchases_transactions", "financial_obligations"),
        "documents": ("admin_documents", "legal_foreign_education_documents", "contracts", "financial_documents", "property_documents"),
        "relationships": ("romance", "partnership"),
        "sport": ("physical_energy", "training_routine", "competition_performance"),
        "communication": ("everyday_contacts", "negotiations", "groups_audience", "public_speech_teaching"),
        "health": ("general_condition", "symptoms_routine_treatment", "recovery_isolation"),
        "home_family": ("family_roots", "housing_property", "relocation"),
        "travel": ("local_travel", "long_distance_foreign_travel"),
        "creativity": ("self_expression", "creative_work", "private_inner_creativity"),
        "study": ("skills_courses", "higher_education_worldview"),
        "friends_goals": ("friends_community", "collective_projects", "long_term_goals"),
    }.items()
    for facet in facets
}

_BROAD_SCOPE_RE = re.compile(
    r"(?:\bвс(?:е|ё|я|ю|ем|ех)\b|\bв\s+целом\b|\bцеликом\b|\bпо\s+всей\b|\bобщ\w*\s+сфер\w*)",
    re.IGNORECASE,
)
_POLARITY_SCOPE_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "supportive": (
        re.compile(r"(?:поддерж\w*|гармонич\w*|легк\w*|устойчив\w*|спокойн\w*|благоприят\w*)", re.IGNORECASE),
    ),
    "tense": (
        re.compile(r"(?:напряж\w*|сложн\w*|конфликт\w*|обостр\w*|тревог\w*|давлен\w*|риск\w*)", re.IGNORECASE),
    ),
}
_HEALTH_DIAGNOSIS_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?:диагноз\w*|диагност\w*|заболеван\w*|болезн\w*|медицинск\w* заключен\w*)", re.IGNORECASE),
)

_POLARITY_CONFLICT_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "supportive": (
        re.compile(r"напряж\w*", re.IGNORECASE),
        re.compile(r"конфликт\w*", re.IGNORECASE),
        re.compile(r"обостр\w*", re.IGNORECASE),
    ),
    "tense": (
        re.compile(r"(?:легк|лёгк)\w*", re.IGNORECASE),
        re.compile(r"гармонич\w*", re.IGNORECASE),
    ),
}

# Source: app.services.focus_title_builder.LOT_LABELS_RU. Keep this small
# stdlib-only copy local to the sanitizer so a lot's proper name is not
# mistaken for ordinary facet language.
_LOT_NAME_PATTERN = re.compile(
    r"жреби\w*\s+(?:фортун\w*|дух\w*|эрос\w*|знани\w*|брак\w*|необходимост\w*|побед\w*|немезид\w*)",
    re.IGNORECASE,
)
_POLARITY_NEGATION_MARKER_PATTERN = re.compile(
    r"(?<!\w)(?:не|нет|без|снизи\w*|снижени\w*|сним\w*|снят\w*|избеж\w*|избег\w*|ослаб\w*|уменьш\w*|отпусти\w*|минимиз\w*|против)(?!\w)",
    re.IGNORECASE,
)


# START_BLOCK: GROUNDING_HELPERS
def _mask_lot_names(text: str) -> str:
    # START_FUNCTION_CONTRACT: F-M-NARRATIVE-SANITIZER._mask_lot_names
    # purpose: Replace named lots with neutral text before grounding vocabulary detection.
    # inputs: text — candidate narrative text.
    # returns: text with proper lot names replaced; original text remains untouched by the caller.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: caller validates text type; this pure helper expects a string.
    # END_FUNCTION_CONTRACT: F-M-NARRATIVE-SANITIZER._mask_lot_names
    return _LOT_NAME_PATTERN.sub("жребий", text)


def _has_polarity_conflict(text: str, polarity: str) -> bool:
    # START_FUNCTION_CONTRACT: F-M-NARRATIVE-SANITIZER._has_polarity_conflict
    # purpose: Detect an unmitigated polarity antonym within the selected claim polarity.
    # inputs: text — masked narrative text; polarity — canonical claim polarity.
    # returns: True when a conflict match has no negation or mitigation marker in its sentence window.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: unknown polarity has no configured patterns and returns False; caller validates polarity.
    # END_FUNCTION_CONTRACT: F-M-NARRATIVE-SANITIZER._has_polarity_conflict
    sentence_boundaries = ".!?;\n"
    for pattern in _POLARITY_CONFLICT_PATTERNS.get(polarity, ()):
        for match in pattern.finditer(text):
            if _is_contextual_tense_easy(text, match, polarity):
                continue
            prefix = text[max(0, match.start() - 40) : match.start()]
            boundary = max((prefix.rfind(marker) for marker in sentence_boundaries), default=-1)
            window = prefix[boundary + 1 :]
            if _POLARITY_NEGATION_MARKER_PATTERN.search(window) is None:
                return True
    return False


def _is_contextual_tense_easy(text: str, match: re.Match[str], polarity: str) -> bool:
    """Keep risk wording such as «легко задеть» out of tense false positives."""
    if polarity != "tense" or match.group(0).lower().startswith(("гармони",)):
        return False
    suffix = text[match.end() : match.end() + 36]
    return re.search(
        r"^\s+(?:задет\w*|задеть\w*|вспых\w*|вспыл\w*|перегн\w*|зацеп\w*|потер\w*|приня\w*|оберн\w*|возник\w*|забы\w*|наруш\w*|устат\w*|утом\w*|скат\w*)",
        suffix,
        re.IGNORECASE,
    ) is not None


def _pattern_matches(
    text: str,
    patterns: Mapping[str, tuple[re.Pattern[str], ...]],
    *,
    prefix: str,
) -> dict[str, tuple[str, ...]]:
    return {
        key: tuple(
            f"{prefix}:{key}:{index}"
            for index, pattern in enumerate(patterns_for_key)
            if pattern.search(text) is not None
        )
        for key, patterns_for_key in patterns.items()
        if any(pattern.search(text) is not None for pattern in patterns_for_key)
    }


def _grounding_rule_hits(
    text: str,
    *,
    allowed_spheres: Collection[str],
    polarity: str,
    allowed_facets: Collection[str],
) -> tuple[dict[str, str], ...]:
    """Return safe reason metadata for the current facet-exclusive policy.

    S21's A1 matrix showed that generic body/communication words were being
    treated as hard domain leaks. Soft words now remain available for natural
    copy, while hard domain vocabulary and explicit sphere claims still fail
    closed. This helper is also the single reason source for production claim
    instrumentation; it never returns the candidate text.
    """
    if not isinstance(text, str) or not isinstance(polarity, str):
        return ({"reason_class": "sphere_conflict", "pattern_id": "invalid_input", "pair": "input"},)
    try:
        raw_spheres = tuple(allowed_spheres)
        raw_facets = tuple(allowed_facets)
    except TypeError:
        return ({"reason_class": "sphere_conflict", "pattern_id": "invalid_input", "pair": "input"},)
    normalized_spheres = {
        sphere for sphere in raw_spheres if isinstance(sphere, str) and sphere.strip()
    }
    normalized_facets = {
        facet for facet in raw_facets if isinstance(facet, str) and facet.strip()
    }
    if (
        not normalized_spheres
        or any(not isinstance(sphere, str) or not sphere.strip() for sphere in raw_spheres)
        or not normalized_spheres.issubset(_SPHERE_PATTERNS)
        or polarity not in {"supportive", "tense", "mixed"}
        or any(not isinstance(facet, str) or not facet.strip() for facet in raw_facets)
        or not normalized_facets.issubset(_FACET_TO_SPHERE)
        or any(_FACET_TO_SPHERE[facet] not in normalized_spheres for facet in normalized_facets)
    ):
        return ({"reason_class": "sphere_conflict", "pattern_id": "invalid_input", "pair": "input"},)

    masked_text = _mask_lot_names(text)
    hits: list[dict[str, str]] = []
    hard_facets = _pattern_matches(masked_text, _HARD_FACET_PATTERNS, prefix="facet")
    for facet, pattern_ids in hard_facets.items():
        if facet in normalized_facets:
            continue
        for pattern_id in pattern_ids:
            hits.append(
                {
                    "reason_class": "facet_conflict",
                    "pattern_id": pattern_id,
                    "pair": f"{next(iter(normalized_facets), 'null')}×{facet}",
                }
            )

    hard_spheres = _pattern_matches(masked_text, _HARD_SPHERE_PATTERNS, prefix="sphere")
    allowed_facet_owners = {
        _FACET_TO_SPHERE[facet]
        for facet in hard_facets
        if facet in normalized_facets
    }
    for sphere, pattern_ids in hard_spheres.items():
        if sphere in normalized_spheres or sphere in allowed_facet_owners:
            continue
        for pattern_id in pattern_ids:
            hits.append(
                {
                    "reason_class": "sphere_conflict",
                    "pattern_id": pattern_id,
                    "pair": f"{next(iter(normalized_spheres), 'null')}×{sphere}",
                }
            )

    if "health" in normalized_spheres:
        for index, pattern in enumerate(_HEALTH_DIAGNOSIS_PATTERNS):
            if pattern.search(text) is not None:
                hits.append(
                    {
                        "reason_class": "sphere_conflict",
                        "pattern_id": f"health_diagnosis:{index}",
                        "pair": "health×health_diagnosis",
                    }
                )

    if normalized_facets and any(
        sphere in normalized_spheres for sphere in hard_spheres
    ) and _BROAD_SCOPE_RE.search(masked_text) is not None:
        hits.append(
            {
                "reason_class": "sphere_conflict",
                "pattern_id": "broad_scope",
                "pair": f"{next(iter(normalized_facets), 'null')}×{next(iter(normalized_spheres), 'null')}",
            }
        )

    sentence_boundaries = ".!?;\n"
    for index, pattern in enumerate(_POLARITY_CONFLICT_PATTERNS.get(polarity, ())):
        for match in pattern.finditer(masked_text):
            if _is_contextual_tense_easy(masked_text, match, polarity):
                continue
            prefix = masked_text[max(0, match.start() - 40) : match.start()]
            boundary = max((prefix.rfind(marker) for marker in sentence_boundaries), default=-1)
            window = prefix[boundary + 1 :]
            if _POLARITY_NEGATION_MARKER_PATTERN.search(window) is None:
                hits.append(
                    {
                        "reason_class": "polarity_antonym",
                        "pattern_id": f"polarity:{polarity}:{index}",
                        "pair": f"{polarity}×antonym",
                    }
                )
                break
    return tuple(hits)


# END_BLOCK: GROUNDING_HELPERS


# START_BLOCK: FORBIDDEN_TOKENS
def has_forbidden_narrative_tokens(text: str) -> bool:
    # START_FUNCTION_CONTRACT: F-M-NARRATIVE-SANITIZER.has_forbidden_narrative_tokens
    # purpose: Detect technical identifiers and enumeration artifacts in narrative text.
    # inputs: text — candidate provider-generated text.
    # returns: True when the text must not be published.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: non-string input is treated as forbidden.
    # END_FUNCTION_CONTRACT: F-M-NARRATIVE-SANITIZER.has_forbidden_narrative_tokens
    if not isinstance(text, str):
        return True
    return any(pattern.search(text) is not None for pattern in _FORBIDDEN_PATTERNS)
# END_BLOCK: FORBIDDEN_TOKENS


# START_BLOCK: SANITIZE
def sanitize_narrative_text(text: str) -> str | None:
    # START_FUNCTION_CONTRACT: F-M-NARRATIVE-SANITIZER.sanitize_narrative_text
    # purpose: Return publishable narrative text or fail closed on a forbidden token.
    # inputs: text — candidate provider-generated text.
    # returns: trimmed text, or None when blank/unsafe.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: non-string, blank, or forbidden text returns None.
    # END_FUNCTION_CONTRACT: F-M-NARRATIVE-SANITIZER.sanitize_narrative_text
    if not isinstance(text, str):
        return None
    clean = text.strip()
    if not clean or has_forbidden_narrative_tokens(clean):
        return None
    return clean
# END_BLOCK: SANITIZE


# START_BLOCK: GROUNDING
def has_narrative_grounding_violation(
    text: str,
    *,
    allowed_spheres: Collection[str],
    polarity: str,
    allowed_facets: Collection[str] = (),
) -> bool:
    # START_FUNCTION_CONTRACT: F-M-NARRATIVE-SANITIZER.has_narrative_grounding_violation
    # purpose: Reject a narrative claim that names an unrelated product
    #   sphere/facet, generalizes a facet polarity to its whole sphere, uses a
    #   health diagnosis, or uses an explicit polarity antonym outside a
    #   same-sentence negation/mitigation window.
    # inputs: text — sanitized candidate; allowed_spheres — selected product
    #   sphere(s); allowed_facets — selected facet(s), empty for facet=null;
    #   polarity — canonical claim polarity.
    # returns: True when the claim must be withheld.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: malformed text, unknown spheres, or unknown polarity fail closed.
    # END_FUNCTION_CONTRACT: F-M-NARRATIVE-SANITIZER.has_narrative_grounding_violation
    return bool(
        _grounding_rule_hits(
            text,
            allowed_spheres=allowed_spheres,
            allowed_facets=allowed_facets,
            polarity=polarity,
        )
    )
# END_BLOCK: GROUNDING


def explain_narrative_grounding_violation(
    text: str,
    *,
    allowed_spheres: Collection[str],
    polarity: str,
    allowed_facets: Collection[str] = (),
) -> dict[str, str] | None:
    # START_FUNCTION_CONTRACT: F-M-NARRATIVE-SANITIZER.explain_narrative_grounding_violation
    # purpose: Expose non-PII rule metadata for one grounding decision.
    # inputs: text, allowed sphere/facet collections, and canonical polarity.
    # returns: first reason metadata mapping, or None when the claim passes.
    # side_effects: none; the mapping contains no candidate text.
    # emitted_logs: none.
    # error_behavior: malformed grounding input returns a fail-closed reason.
    # END_FUNCTION_CONTRACT: F-M-NARRATIVE-SANITIZER.explain_narrative_grounding_violation
    """Return non-PII reason metadata for one grounding decision."""
    hits = _grounding_rule_hits(
        text,
        allowed_spheres=allowed_spheres,
        allowed_facets=allowed_facets,
        polarity=polarity,
    )
    return dict(hits[0]) if hits else None


__all__ = [
    "has_forbidden_narrative_tokens",
    "has_narrative_grounding_violation",
    "explain_narrative_grounding_violation",
    "sanitize_narrative_text",
]

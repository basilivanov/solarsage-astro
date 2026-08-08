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
#   grounding violations are reported as booleans without exposing raw text.
# dependencies: Python standard library only.
# side_effects: none; pure validation.
# emitted_logs: none.
# invariants: rejected text is never returned as a sanitized value; an unknown
#   sphere, facet, or polarity fails closed; a nullable facet never authorizes
#   narrow facet language.
# failure_policy: fail closed with None for blank or forbidden text.
# END_MODULE_CONTRACT: M-NARRATIVE-SANITIZER

# START_MODULE_MAP: M-NARRATIVE-SANITIZER
# public_entrypoints:
#   - has_forbidden_narrative_tokens
#   - sanitize_narrative_text
#   - has_narrative_grounding_violation
# semantic_blocks:
#   - FORBIDDEN_TOKENS: machine prefixes, generic Planet labels, and list artifacts.
#   - GROUNDING: canonical sphere/facet vocabulary, scope checks, health safety,
#     and explicit polarity-antonym checks.
#   - SANITIZE: deterministic trim-and-reject boundary.
# owned_tests:
#   - apps/api/tests/test_narrative_sanitizer.py
# END_MODULE_MAP: M-NARRATIVE-SANITIZER

from __future__ import annotations

import re
from collections.abc import Collection


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

_RELATED_SPHERES: dict[str, frozenset[str]] = {
    # The resolver assigns one sphere to one physical signal. Narrative text
    # therefore cannot borrow a neighbouring sphere as an implicit allowance.
    sphere: frozenset() for sphere in _SPHERE_PATTERNS
}


# Narrow language is permitted only when the selected facet explicitly owns
# it. These patterns intentionally avoid generic sphere words such as
# "документы", "деньги" and "отношения", so facet=null can still use a
# general sphere description.
_FACET_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "daily_work": (re.compile(r"(?:служебн\w*|рабоч\w* нагруз\w*|рабоч\w* задач\w*)", re.IGNORECASE),),
    "career_status": (re.compile(r"(?:карьер\w*|продвижен\w*|публичн\w* роль\w*)", re.IGNORECASE),),
    "personal_money": (re.compile(r"(?:доход\w*|расход\w*|накоплен\w*|личн\w* (?:средств\w*|имуще\w*))", re.IGNORECASE),),
    "shared_money": (re.compile(r"(?:общ\w* бюджет\w*|партнёрск\w* средств\w*|страхов\w*|наслед\w*)", re.IGNORECASE),),
    "purchases_transactions": (re.compile(r"(?:покуп\w*|продаж\w*|(?<![а-яёА-ЯЁ])цен\w*|сделк\w*|транзакц\w*|магазин\w*|заказ\w*)", re.IGNORECASE),),
    "financial_obligations": (re.compile(r"(?:кредит\w*|долг(?!осроч)\w*|налог\w*|рассроч\w*|возврат\w*)", re.IGNORECASE),),
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
    "everyday_contacts": (re.compile(r"(?:разговор\w*|переписк\w*|повседневн\w* контакт\w*)", re.IGNORECASE),),
    "negotiations": (re.compile(r"(?:переговор\w*|договорённост\w*|договоренност\w*)", re.IGNORECASE),),
    "groups_audience": (re.compile(r"(?:групп\w*|аудитор\w*|сообществ\w*)", re.IGNORECASE),),
    "public_speech_teaching": (re.compile(r"(?:публичн\w* выступ\w*|преподав\w*|лекц\w*)", re.IGNORECASE),),
    "general_condition": (re.compile(r"(?:самочув\w*|общ\w* состоян\w*|тонус\w*)", re.IGNORECASE),),
    "symptoms_routine_treatment": (re.compile(r"(?:симптом\w*|лечен\w*|восстановительн\w* режим\w*)", re.IGNORECASE),),
    "recovery_isolation": (re.compile(r"(?:отдых\w*|изоляц\w*|стационар\w*)", re.IGNORECASE),),
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
    r"(?:\bвс(?:е|ё|я|ю|ем|ех)\b|\bобщ(?:ий|ая|ее|ем|их)?\b|\bв\s+целом\b|\bцеликом\b|\bпо\s+всей\b)",
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
    #   health diagnosis, or uses an explicit polarity antonym.
    # inputs: text — sanitized candidate; allowed_spheres — selected product
    #   sphere(s); allowed_facets — selected facet(s), empty for facet=null;
    #   polarity — canonical claim polarity.
    # returns: True when the claim must be withheld.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: malformed text, unknown spheres, or unknown polarity fail closed.
    # END_FUNCTION_CONTRACT: F-M-NARRATIVE-SANITIZER.has_narrative_grounding_violation
    if not isinstance(text, str) or not isinstance(polarity, str):
        return True
    try:
        raw_spheres = tuple(allowed_spheres)
        raw_facets = tuple(allowed_facets)
    except TypeError:
        return True
    normalized_spheres = {
        sphere for sphere in raw_spheres if isinstance(sphere, str) and sphere.strip()
    }
    if (
        not normalized_spheres
        or any(not isinstance(sphere, str) or not sphere.strip() for sphere in raw_spheres)
        or not normalized_spheres.issubset(_SPHERE_PATTERNS)
    ):
        return True
    if polarity not in {"supportive", "tense", "mixed"}:
        return True

    normalized_facets = {
        facet for facet in raw_facets if isinstance(facet, str) and facet.strip()
    }
    if any(not isinstance(facet, str) or not facet.strip() for facet in raw_facets):
        return True
    if (
        not normalized_facets.issubset(_FACET_TO_SPHERE)
        or any(_FACET_TO_SPHERE[facet] not in normalized_spheres for facet in normalized_facets)
    ):
        return True

    detected_facets = {
        facet
        for facet, patterns in _FACET_PATTERNS.items()
        if any(pattern.search(text) is not None for pattern in patterns)
    }
    # A nullable facet authorizes only general sphere wording. A selected
    # facet authorizes exactly that facet; all other narrow terms fail closed.
    if detected_facets.difference(normalized_facets):
        return True

    detected_spheres = {
        sphere
        for sphere, patterns in _SPHERE_PATTERNS.items()
        if any(pattern.search(text) is not None for pattern in patterns)
    }
    allowed_facet_owners = {
        _FACET_TO_SPHERE[facet]
        for facet in detected_facets.intersection(normalized_facets)
    }
    for detected_sphere in detected_spheres:
        if detected_sphere in normalized_spheres:
            continue
        # Some facet language is intentionally shared by ordinary product
        # wording (for example correspondence in admin_documents). The
        # explicit facet ownership is the only narrow exception; old related
        # sphere allowances are not restored.
        if detected_sphere in allowed_facet_owners:
            continue
        return True

    if "health" in normalized_spheres and any(
        pattern.search(text) is not None for pattern in _HEALTH_DIAGNOSIS_PATTERNS
    ):
        return True

    if normalized_facets and detected_spheres.intersection(normalized_spheres):
        # A facet-specific claim must not silently become a claim about the
        # whole sphere: both explicit broad quantifiers and direct sphere
        # polarity wording are rejected.
        if _BROAD_SCOPE_RE.search(text) is not None:
            return True
        if any(
            pattern.search(text) is not None
            for pattern in _POLARITY_SCOPE_PATTERNS.get(polarity, ())
        ) and not detected_facets.intersection(normalized_facets):
            return True

    return any(
        pattern.search(text) is not None
        for pattern in _POLARITY_CONFLICT_PATTERNS.get(polarity, ())
    )
# END_BLOCK: GROUNDING


__all__ = [
    "has_forbidden_narrative_tokens",
    "has_narrative_grounding_violation",
    "sanitize_narrative_text",
]

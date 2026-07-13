# ############################################################################
# AI_HEADER: HORIZON_CONTENT_CANON_SCHEMA — strict internal B2B1 content-canon contracts.
# ROLE: Validates language, action, and personal-pattern YAML before pure B2B services consume it.
# ############################################################################

# START_MODULE_CONTRACT: M-HORIZON-CONTENT-CANON-SCHEMA
# purpose: Model the three closed B2B1 content canons and validate their cross-file references.
# owns:
#   - apps/api/app/schemas/horizon_content_canon.py
# inputs: Parsed internal YAML mappings for language, actions, and personal patterns.
# outputs: Frozen typed canon models and a validated HorizonContentCanonBundle.
# dependencies: math/re/typing stdlib, pydantic, B2A canon constants, public literal aliases only.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - Canon keys, action intents, predicate fields, and statement references are closed and exhaustive.
#   - Validation errors are structural and never echo raw reviewed copy or natal values.
# failure_policy: raises Pydantic ValidationError for malformed or inconsistent canon data.
# END_MODULE_CONTRACT: M-HORIZON-CONTENT-CANON-SCHEMA

# START_MODULE_MAP: M-HORIZON-CONTENT-CANON-SCHEMA
# public_entrypoints:
#   - HorizonLanguageCanon
#   - HorizonActionsCanon
#   - PersonalPatternsCanon
#   - HorizonContentCanonBundle
# semantic_blocks:
#   - HORIZON_CONTENT_CANON_TYPES: closed aliases and validation primitives.
#   - HORIZON_CONTENT_CANON_MODELS: file-local and cross-canon typed models.
# owned_tests:
#   - apps/api/tests/test_horizon_content_canon_service.py
# END_MODULE_MAP: M-HORIZON-CONTENT-CANON-SCHEMA

from __future__ import annotations

from typing import Annotated, Literal, Union, get_args

from pydantic import Field, model_validator

from app.schemas.horizon_canon import HORIZON_IDS, PUBLIC_PRODUCT_SPHERES
from app.schemas.horizon_content_canon_types import (
    ALLOWED_PLACEHOLDERS,
    ASPECT_TYPES,
    ActionIntent,
    AvoidActionIntent,
    ClaimSafetyClass,
    ForbiddenPolicyIntent,
    HORIZON_SELECTION_TECHNIQUES,
    HorizonContentCanonModel,
    HorizonSphereVerdict,
    HorizonThemeKey,
    ID_RE,
    PLANET_ORDER,
    PRODUCT_SPHERE_ORDER as PRODUCT_SPHERE_ORDER,
    PersonalFactKind,
    PositiveActionIntent,
    SIGN_KEYS,
    STATEMENT_KEY_RE,
    THEME_KEYS,
    TIMING_STATES,
    TONES,
    VERDICTS,
    _canonical_pair,
    _contains_forbidden_copy,
    _ensure_exact_keys,
    _ensure_finite,
    _ensure_unique_non_blank,
    _normalize_copy,
    _template_placeholders,
    _validate_copy,
)
from app.schemas.today_horizons import (
    TodayV2HorizonId,
    TodayV2HorizonTone,
    TodayV2ProductSphereKey,
    TodayV2TimingState,
)
# START_BLOCK: HORIZON_CONTENT_CANON_MODELS
class HorizonLabels(HorizonContentCanonModel):
    eyebrow: str = Field(min_length=1)
    actions_heading: str = Field(min_length=1)
    avoid_heading: str = Field(min_length=1)


class ThemeHorizonLanguage(HorizonContentCanonModel):
    title: str = Field(min_length=1)
    plain_explanation: str = Field(min_length=1)


class ThemeLanguage(HorizonContentCanonModel):
    label: str = Field(min_length=1)
    headline: str = Field(min_length=1)
    intro_body: str = Field(min_length=1)
    long: ThemeHorizonLanguage
    medium: ThemeHorizonLanguage
    fast: ThemeHorizonLanguage


class TechniqueLanguage(HorizonContentCanonModel):
    label: str = Field(min_length=1)
    what_it_is: str = Field(min_length=1)
    why_it_matters_template: str = Field(min_length=1)


class ProductSphereLanguage(HorizonContentCanonModel):
    label: str = Field(min_length=1)
    manifestation_title: str = Field(min_length=1)
    manifestation_body: str = Field(min_length=1)
    conditional: Literal[True]


class StatementLanguage(HorizonContentCanonModel):
    kind: PersonalFactKind
    text: str = Field(min_length=1)


class SphereFactStatement(HorizonContentCanonModel):
    statement_key: str
    kind: Literal["sphere"]
    text: str = Field(min_length=1)


class ConditionalPolicy(HorizonContentCanonModel):
    required_prefixes: tuple[str, ...]
    forbidden_certainty_fragments: tuple[str, ...]
    forbidden_high_stakes_fragments: tuple[str, ...]


class ToneFeatureWeights(HorizonContentCanonModel):
    strength: float
    contribution: float
    convergence: float
    impact: float


class ToneRules(HorizonContentCanonModel):
    feature_weights: ToneFeatureWeights
    activation_weight: float
    sphere_verdict_weight: float
    verdict_values: dict[HorizonSphereVerdict, float]
    supportive_min: float
    tense_max: float
    mixed_opposing_min: float
    rounding_digits: Literal[6]

    @model_validator(mode="after")
    def validate_rules(self) -> "ToneRules":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SCHEMA.ToneRules.validate_rules
        # purpose: Validate canonical tone aggregation weights, thresholds, and verdict ordering.
        # inputs: self - parsed tone rules.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError on invalid tone configuration.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SCHEMA.ToneRules.validate_rules
        feature_weights = self.feature_weights.model_dump()
        for key, value in feature_weights.items():
            _ensure_finite(value, f"tone_rules.feature_weights.{key}", 0.0, 1.0)
        if abs(sum(feature_weights.values()) - 1.0) > 1e-9:
            raise ValueError("tone_rules.feature_weights: expected sum one")
        _ensure_finite(self.activation_weight, "tone_rules.activation_weight", 0.0, 1.0)
        _ensure_finite(self.sphere_verdict_weight, "tone_rules.sphere_verdict_weight", 0.0, 1.0)
        if abs(self.activation_weight + self.sphere_verdict_weight - 1.0) > 1e-9:
            raise ValueError("tone_rules: aggregate weights must sum one")
        _ensure_exact_keys(
            set(self.verdict_values), {"good", "neutral", "caution", "avoid"}, "tone_rules.verdict_values"
        )
        for value in self.verdict_values.values():
            _ensure_finite(value, "tone_rules.verdict_values", -1.0, 1.0)
        if (
            not self.verdict_values["good"]
            > self.verdict_values["neutral"]
            > self.verdict_values["caution"]
            > self.verdict_values["avoid"]
        ):
            raise ValueError("tone_rules.verdict_values: expected descending values")
        _ensure_finite(self.supportive_min, "tone_rules.supportive_min", 0.0, 1.0)
        _ensure_finite(self.tense_max, "tone_rules.tense_max", -1.0, 0.0)
        _ensure_finite(self.mixed_opposing_min, "tone_rules.mixed_opposing_min", 0.0, 1.0)
        if not self.supportive_min > 0 or not self.tense_max < 0:
            raise ValueError("tone_rules: invalid supportive or tense threshold")
        return self


class HorizonLanguageCanon(HorizonContentCanonModel):
    schema_version: Literal["horizon_language.ru.v1"]
    version: Literal["v1"]
    locale: Literal["ru"]
    horizons: dict[TodayV2HorizonId, HorizonLabels]
    tone_labels: dict[TodayV2HorizonTone, str]
    timing_state_labels: dict[TodayV2TimingState, str]
    timing_templates: dict[str, str]
    allowed_placeholders: tuple[str, ...]
    techniques: dict[str, TechniqueLanguage]
    themes: dict[HorizonThemeKey, ThemeLanguage]
    product_spheres: dict[TodayV2ProductSphereKey, ProductSphereLanguage]
    sphere_fact_statements: dict[TodayV2ProductSphereKey, SphereFactStatement]
    personal_statements: dict[str, StatementLanguage]
    conditional_policy: ConditionalPolicy
    tone_rules: ToneRules

    @model_validator(mode="after")
    def validate_closed_content(self) -> "HorizonLanguageCanon":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SCHEMA.HorizonLanguageCanon.validate_closed_content
        # purpose: Validate all exhaustive language-canon identities and machine statement semantics.
        # inputs: self - parsed language canon.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError for missing, unknown, or inconsistent language entries.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SCHEMA.HorizonLanguageCanon.validate_closed_content
        _ensure_exact_keys(set(self.horizons), set(HORIZON_IDS), "horizons")
        _ensure_exact_keys(set(self.tone_labels), set(TONES), "tone_labels")
        _ensure_exact_keys(set(self.timing_state_labels), set(TIMING_STATES), "timing_state_labels")
        _ensure_exact_keys(set(self.techniques), set(HORIZON_SELECTION_TECHNIQUES), "techniques")
        _ensure_exact_keys(set(self.themes), set(THEME_KEYS), "themes")
        _ensure_exact_keys(set(self.product_spheres), set(PUBLIC_PRODUCT_SPHERES), "product_spheres")
        _ensure_exact_keys(set(self.sphere_fact_statements), set(PUBLIC_PRODUCT_SPHERES), "sphere_fact_statements")
        _ensure_exact_keys(
            set(self.timing_templates),
            {"range", "peak", "valid_until", "long_valid_until", "fast_eases"},
            "timing_templates",
        )
        if set(self.allowed_placeholders) != ALLOWED_PLACEHOLDERS or len(self.allowed_placeholders) != len(
            ALLOWED_PLACEHOLDERS
        ):
            raise ValueError("allowed_placeholders: expected exact vocabulary")
        for horizon, labels in self.horizons.items():
            for field, value in labels.model_dump().items():
                _validate_copy(value, f"horizons.{horizon}.{field}")
        for path, values in (
            ("tone_labels", self.tone_labels),
            ("timing_state_labels", self.timing_state_labels),
        ):
            for key, value in values.items():
                _validate_copy(value, f"{path}.{key}")
        expected_timing_placeholders = {
            "range": {"active_from", "active_until"},
            "peak": {"exact_at"},
            "valid_until": {"active_until"},
            "long_valid_until": {"active_until"},
            "fast_eases": {"active_until"},
        }
        for key, value in self.timing_templates.items():
            _validate_copy(value, f"timing_templates.{key}")
            placeholders = _template_placeholders(value, f"timing_templates.{key}")
            if set(placeholders) != expected_timing_placeholders[key] or len(placeholders) != len(expected_timing_placeholders[key]):
                raise ValueError("timing_templates: expected exact placeholders")
        for key, technique in self.techniques.items():
            for field, value in technique.model_dump().items():
                _validate_copy(value, f"techniques.{key}.{field}")
            if not set(_template_placeholders(technique.why_it_matters_template, "techniques")) <= ALLOWED_PLACEHOLDERS:
                raise ValueError("techniques: unknown placeholder")
        for key, theme in self.themes.items():
            for field in ("label", "headline", "intro_body"):
                _validate_copy(getattr(theme, field), f"themes.{key}.{field}")
            for horizon in HORIZON_IDS:
                for field, value in getattr(theme, horizon).model_dump().items():
                    _validate_copy(value, f"themes.{key}.{horizon}.{field}")
        for key, sphere in self.product_spheres.items():
            for field in ("label", "manifestation_title", "manifestation_body"):
                _validate_copy(getattr(sphere, field), f"product_spheres.{key}.{field}")
        _ensure_unique_non_blank(self.conditional_policy.required_prefixes, "conditional_policy.required_prefixes")
        _ensure_unique_non_blank(
            self.conditional_policy.forbidden_certainty_fragments, "conditional_policy.forbidden_certainty_fragments"
        )
        _ensure_unique_non_blank(
            self.conditional_policy.forbidden_high_stakes_fragments,
            "conditional_policy.forbidden_high_stakes_fragments",
        )
        if not all(
            (
                self.conditional_policy.required_prefixes,
                self.conditional_policy.forbidden_certainty_fragments,
                self.conditional_policy.forbidden_high_stakes_fragments,
            )
        ):
            raise ValueError("conditional_policy: expected non-empty policy lists")
        if any(
            not sphere.manifestation_body.startswith(self.conditional_policy.required_prefixes)
            for sphere in self.product_spheres.values()
        ):
            raise ValueError("product_spheres: conditional body requires allowed prefix")
        for sphere, statement in self.sphere_fact_statements.items():
            expected = f"sphere.active.{sphere}"
            _validate_copy(statement.text, f"sphere_fact_statements.{sphere}.text")
            if statement.statement_key != expected or statement.text != self.product_spheres[sphere].label:
                raise ValueError("sphere_fact_statements: expected matching machine label")
        _ensure_unique_non_blank(tuple(self.personal_statements), "personal_statements")
        if any(
            not STATEMENT_KEY_RE.fullmatch(key) or statement.kind not in {"strength", "risk"}
            for key, statement in self.personal_statements.items()
        ):
            raise ValueError("personal_statements: invalid key or kind")
        for key, statement in self.personal_statements.items():
            _validate_copy(statement.text, f"personal_statements.{key}.text")
        return self


class SafetyClassRule(HorizonContentCanonModel):
    allowed_intents: tuple[ActionIntent, ...]
    compatible_verdicts: tuple[HorizonSphereVerdict, ...]

    @model_validator(mode="after")
    def _validate_rule(self) -> "SafetyClassRule":
        if not self.allowed_intents or not self.compatible_verdicts:
            raise ValueError("safety_class: expected non-empty lists")
        _ensure_unique_non_blank(self.allowed_intents, "safety_class.allowed_intents")
        _ensure_unique_non_blank(self.compatible_verdicts, "safety_class.compatible_verdicts")
        if self.compatible_verdicts != tuple(verdict for verdict in VERDICTS if verdict in self.compatible_verdicts):
            raise ValueError("safety_class.compatible_verdicts: expected canonical order")
        return self


class ActionTemplate(HorizonContentCanonModel):
    id: str
    text: str = Field(min_length=1)
    intent: ActionIntent | ForbiddenPolicyIntent
    safety_class: ClaimSafetyClass
    conditional: bool
    tones: tuple[TodayV2HorizonTone, ...]
    sphere_keys: tuple[TodayV2ProductSphereKey, ...]

    @model_validator(mode="after")
    def validate_template(self) -> "ActionTemplate":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SCHEMA.ActionTemplate.validate_template
        # purpose: Validate template-local machine ids, closed metadata, and safe copy shape.
        # inputs: self - parsed action or avoid template.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError for malformed template metadata or unsafe copy.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SCHEMA.ActionTemplate.validate_template
        if not ID_RE.fullmatch(self.id) or not self.text.strip():
            raise ValueError("template: invalid id or blank text")
        if not self.tones or not self.sphere_keys:
            raise ValueError("template: expected non-empty tones and sphere keys")
        _ensure_unique_non_blank(self.tones, f"template.{self.id}.tones")
        _ensure_unique_non_blank(self.sphere_keys, f"template.{self.id}.sphere_keys")
        if self.intent in {
            "immediate_major_decision",
            "increase_commitment",
            "escalate",
            "replace_everything",
            "increase_intensity",
        }:
            raise ValueError("template: forbidden intent")
        if _template_placeholders(self.text, f"template.{self.id}.text"):
            raise ValueError("template: action body cannot contain placeholders")
        return self


class HorizonActionLists(HorizonContentCanonModel):
    do: tuple[ActionTemplate, ...]
    avoid: tuple[ActionTemplate, ...]


class ThemeActionMatrix(HorizonContentCanonModel):
    long: HorizonActionLists
    medium: HorizonActionLists
    fast: HorizonActionLists


class HorizonActionsCanon(HorizonContentCanonModel):
    schema_version: Literal["horizon_actions.ru.v1"]
    version: Literal["v1"]
    locale: Literal["ru"]
    safety_classes: dict[ClaimSafetyClass, SafetyClassRule]
    forbidden_intent_pairs: tuple[tuple[ForbiddenPolicyIntent, AvoidActionIntent], ...]
    forbidden_intents: tuple[ForbiddenPolicyIntent, ...]
    theme_spheres: dict[HorizonThemeKey, tuple[TodayV2ProductSphereKey, ...]]
    themes: dict[HorizonThemeKey, ThemeActionMatrix]

    @model_validator(mode="after")
    def validate_actions(self) -> "HorizonActionsCanon":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SCHEMA.HorizonActionsCanon.validate_actions
        # purpose: Validate action coverage, metadata, ownership, and global template uniqueness.
        # inputs: self - parsed actions canon.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError for incomplete or unsafe actions canon.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SCHEMA.HorizonActionsCanon.validate_actions
        _ensure_exact_keys(
            set(self.safety_classes),
            {"reflection", "reversible_experiment", "low_stakes_communication", "pacing", "guardrail"},
            "safety_classes",
        )
        _ensure_exact_keys(set(self.theme_spheres), set(THEME_KEYS), "theme_spheres")
        _ensure_exact_keys(set(self.themes), set(THEME_KEYS), "actions.themes")
        if set(self.forbidden_intents) != {
            "immediate_major_decision",
            "increase_commitment",
            "escalate",
            "replace_everything",
            "increase_intensity",
        }:
            raise ValueError("forbidden_intents: expected exact closed set")
        if set(self.forbidden_intent_pairs) != {
            ("immediate_major_decision", "postpone_major_decision"),
            ("increase_commitment", "avoid_overcommitment"),
            ("escalate", "avoid_escalation"),
            ("replace_everything", "avoid_all_at_once"),
            ("increase_intensity", "avoid_extra_intensity"),
        }:
            raise ValueError("forbidden_intent_pairs: expected exact closed set")
        all_ids: list[str] = []
        all_texts: list[str] = []
        minimums = {"long": (1, 1), "medium": (2, 1), "fast": (1, 1)}
        positive_intents = set(get_args(PositiveActionIntent))
        avoid_intents = set(get_args(AvoidActionIntent))
        for theme in THEME_KEYS:
            owned = self.theme_spheres[theme]
            if not owned:
                raise ValueError("theme_spheres: expected non-empty sphere list")
            _ensure_unique_non_blank(owned, f"theme_spheres.{theme}")
            matrix = self.themes[theme]
            for horizon in HORIZON_IDS:
                lists = getattr(matrix, horizon)
                required_do, required_avoid = minimums[horizon]
                if len(lists.do) < required_do or len(lists.avoid) < required_avoid:
                    raise ValueError(f"actions.{theme}.{horizon}: insufficient do/avoid coverage")
                if any(template.intent not in positive_intents for template in lists.do):
                    raise ValueError("actions.do: expected positive action intents")
                if any(template.intent not in avoid_intents for template in lists.avoid):
                    raise ValueError("actions.avoid: expected avoid action intents")
                for template in (*lists.do, *lists.avoid):
                    if not set(template.sphere_keys) & set(owned):
                        raise ValueError("template: sphere set must intersect owning theme")
                    if any(sphere not in owned for sphere in template.sphere_keys):
                        raise ValueError("template: sphere outside owning theme")
                    if template.sphere_keys != tuple(sphere for sphere in owned if sphere in template.sphere_keys):
                        raise ValueError("template: sphere keys must preserve owning order")
                    if template.tones != tuple(tone for tone in TONES if tone in template.tones):
                        raise ValueError("template: tones must preserve canonical order")
                    if template.intent not in self.safety_classes[template.safety_class].allowed_intents:
                        raise ValueError("template: intent incompatible with safety class")
                    all_ids.append(template.id)
                    all_texts.append(_normalize_copy(template.text))
                for tone in TONES:
                    for verdict in VERDICTS:
                        def eligible(template: ActionTemplate) -> bool:
                            # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON.eligible
                            # purpose: Check action-template compatibility for the current tone and verdict.
                            # inputs: template - action template from the current horizon bucket.
                            # returns: True when the template supports the current tone/verdict pair.
                            # side_effects: none.
                            # emitted_logs: none.
                            # error_behavior: propagates missing safety-class lookup errors.
                            # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON.eligible
                            return tone in template.tones and verdict in self.safety_classes[
                                template.safety_class
                            ].compatible_verdicts

                        if sum(eligible(template) for template in lists.do) < required_do or sum(
                            eligible(template) for template in lists.avoid
                        ) < required_avoid:
                            raise ValueError("actions: insufficient tone/verdict safety coverage")
        _ensure_unique_non_blank(all_ids, "actions.template_ids")
        _ensure_unique_non_blank(all_texts, "actions.template_texts")
        return self


class PlanetInSignPredicate(HorizonContentCanonModel):
    type: Literal["planet_in_sign"]
    planet: str
    signs: tuple[str, ...]


class PlanetInHousePredicate(HorizonContentCanonModel):
    type: Literal["planet_in_house"]
    planet: str
    houses: tuple[int, ...]


class AspectPredicate(HorizonContentCanonModel):
    type: Literal["aspect"]
    point_a: str
    point_b: str
    aspect_types: tuple[str, ...]
    max_orb: float


NatalPredicate = Annotated[
    Union[PlanetInSignPredicate, PlanetInHousePredicate, AspectPredicate],
    Field(discriminator="type"),
]


class PersonalPatternRule(HorizonContentCanonModel):
    order: int
    id: str
    kind: Literal["strength", "risk"]
    statement_key: str
    theme_keys: tuple[HorizonThemeKey, ...]
    sphere_keys: tuple[TodayV2ProductSphereKey, ...]
    base_confidence: float
    min_confidence: float
    requirements: tuple[NatalPredicate, ...]

    @model_validator(mode="after")
    def validate_rule(self) -> "PersonalPatternRule":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SCHEMA.PersonalPatternRule.validate_rule
        # purpose: Validate stable pattern identity, closed links, confidence, and predicate uniqueness.
        # inputs: self - parsed personal pattern rule.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError for malformed rule metadata or duplicate predicates.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SCHEMA.PersonalPatternRule.validate_rule
        if self.order < 1 or not ID_RE.fullmatch(self.id) or not STATEMENT_KEY_RE.fullmatch(self.statement_key):
            raise ValueError("personal_pattern: invalid id or statement key")
        if not self.theme_keys or not self.sphere_keys:
            raise ValueError("personal_pattern: expected non-empty theme and sphere links")
        _ensure_unique_non_blank(self.theme_keys, f"personal_pattern.{self.id}.theme_keys")
        _ensure_unique_non_blank(self.sphere_keys, f"personal_pattern.{self.id}.sphere_keys")
        _ensure_finite(self.base_confidence, f"personal_pattern.{self.id}.base_confidence", 0.0, 1.0)
        _ensure_finite(self.min_confidence, f"personal_pattern.{self.id}.min_confidence", 0.0, 1.0)
        if self.base_confidence < self.min_confidence:
            raise ValueError("personal_pattern: base confidence below minimum")
        if not self.requirements:
            raise ValueError("personal_pattern: expected requirements")
        predicate_keys: list[tuple[object, ...]] = []
        for predicate in self.requirements:
            if isinstance(predicate, PlanetInSignPredicate):
                if predicate.planet not in PLANET_ORDER or not predicate.signs or not set(predicate.signs) <= SIGN_KEYS:
                    raise ValueError("planet_in_sign: invalid planet or signs")
                _ensure_unique_non_blank(predicate.signs, "planet_in_sign.signs")
                predicate_keys.append((predicate.type, predicate.planet, tuple(sorted(predicate.signs))))
            elif isinstance(predicate, PlanetInHousePredicate):
                if (
                    predicate.planet not in PLANET_ORDER
                    or not predicate.houses
                    or any(house not in range(1, 13) for house in predicate.houses)
                ):
                    raise ValueError("planet_in_house: invalid planet or houses")
                if len(predicate.houses) != len(set(predicate.houses)):
                    raise ValueError("planet_in_house.houses: expected unique values")
                predicate_keys.append((predicate.type, predicate.planet, tuple(sorted(predicate.houses))))
            else:
                if not predicate.aspect_types or not set(predicate.aspect_types) <= ASPECT_TYPES:
                    raise ValueError("aspect: invalid aspect types")
                _ensure_unique_non_blank(predicate.aspect_types, "aspect.aspect_types")
                _ensure_finite(predicate.max_orb, "aspect.max_orb", 0.0, 10.0)
                if predicate.max_orb == 0:
                    raise ValueError("aspect.max_orb: expected positive value")
                predicate_keys.append(
                    (
                        predicate.type,
                        *_canonical_pair(predicate.point_a, predicate.point_b),
                        tuple(sorted(predicate.aspect_types)),
                        predicate.max_orb,
                    )
                )
        if len(predicate_keys) != len(set(predicate_keys)):
            raise ValueError("personal_pattern: duplicate normalized predicate")
        return self


class PersonalPatternsCanon(HorizonContentCanonModel):
    schema_version: Literal["personal_patterns.ru.v1"]
    version: Literal["v1"]
    locale: Literal["ru"]
    patterns: tuple[PersonalPatternRule, ...]

    @model_validator(mode="after")
    def validate_patterns(self) -> "PersonalPatternsCanon":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SCHEMA.PersonalPatternsCanon.validate_patterns
        # purpose: Require a non-empty globally unique stable v1 rule sequence.
        # inputs: self - parsed personal patterns canon.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError for empty or duplicate rule identities.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SCHEMA.PersonalPatternsCanon.validate_patterns
        if not self.patterns:
            raise ValueError("patterns: expected non-empty v1 catalog")
        _ensure_unique_non_blank(tuple(rule.id for rule in self.patterns), "patterns.ids")
        orders = tuple(rule.order for rule in self.patterns)
        if len(orders) != len(set(orders)) or orders != tuple(range(1, len(self.patterns) + 1)):
            raise ValueError("patterns: expected contiguous self-describing order")
        return self


class HorizonContentCanonBundle(HorizonContentCanonModel):
    language: HorizonLanguageCanon
    actions: HorizonActionsCanon
    patterns: PersonalPatternsCanon

    @model_validator(mode="after")
    def validate_cross_canon(self) -> "HorizonContentCanonBundle":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SCHEMA.HorizonContentCanonBundle.validate_cross_canon
        # purpose: Validate all cross-file statement, theme, action, and locale references before runtime use.
        # inputs: self - loaded three-file bundle.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError for cross-canon inconsistency.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SCHEMA.HorizonContentCanonBundle.validate_cross_canon
        if {self.language.locale, self.actions.locale, self.patterns.locale} != {"ru"}:
            raise ValueError("bundle: locale mismatch")
        if {self.language.version, self.actions.version, self.patterns.version} != {"v1"}:
            raise ValueError("bundle: version mismatch")
        if set(self.actions.themes) != set(self.language.themes):
            raise ValueError("bundle: action themes must equal language themes")
        statements = self.language.personal_statements
        referenced = [rule.statement_key for rule in self.patterns.patterns]
        if set(referenced) != set(statements) or len(referenced) != len(set(referenced)):
            raise ValueError("bundle: every personal statement requires exactly one rule")
        for rule in self.patterns.patterns:
            statement = statements.get(rule.statement_key)
            if statement is None or statement.kind != rule.kind:
                raise ValueError("bundle: pattern statement key/kind mismatch")
            if not set(rule.theme_keys) <= set(self.language.themes) or not set(rule.sphere_keys) <= set(
                self.language.product_spheres
            ):
                raise ValueError("bundle: pattern references unknown theme or sphere")
        prefixes = self.language.conditional_policy.required_prefixes
        conditional_actions = (
            template
            for matrix in self.actions.themes.values()
            for horizon in HORIZON_IDS
            for template in (*getattr(matrix, horizon).do, *getattr(matrix, horizon).avoid)
            if template.conditional
        )
        if any(not template.text.startswith(prefixes) for template in conditional_actions):
            raise ValueError("bundle: conditional action requires loaded language prefix")
        language_copy = [
            *self.language.tone_labels.values(),
            *self.language.timing_state_labels.values(),
            *self.language.timing_templates.values(),
            *(value for labels in self.language.horizons.values() for value in labels.model_dump().values()),
            *(value for item in self.language.techniques.values() for value in item.model_dump().values()),
            *(getattr(item, field) for item in self.language.themes.values() for field in ("label", "headline", "intro_body")),
            *(
                value
                for item in self.language.themes.values()
                for horizon in HORIZON_IDS
                for value in getattr(item, horizon).model_dump().values()
            ),
            *(value for item in self.language.product_spheres.values() for value in item.model_dump().values() if isinstance(value, str)),
            *(item.text for item in self.language.sphere_fact_statements.values()),
            *(item.text for item in self.language.personal_statements.values()),
            *(
                template.text
                for matrix in self.actions.themes.values()
                for horizon in HORIZON_IDS
                for template in (*getattr(matrix, horizon).do, *getattr(matrix, horizon).avoid)
            ),
        ]
        forbidden = (
            *self.language.conditional_policy.forbidden_certainty_fragments,
            *self.language.conditional_policy.forbidden_high_stakes_fragments,
        )
        if _contains_forbidden_copy(language_copy, forbidden):
            raise ValueError("bundle: copy violates loaded language policy")
        return self
# END_BLOCK: HORIZON_CONTENT_CANON_MODELS

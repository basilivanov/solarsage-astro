# ############################################################################
# AI_HEADER: HORIZON_CLAIM_POLICY — deterministic policy checks for B2B2 claims.
# ROLE: Owns action authorization/verdict/intent conflicts, conditional policy,
#       unsupported-life policy, forbidden/high-stakes scans, internal/raw/
#       sentinel leakage scans, and numeric/canonical-copy integrity.
# ############################################################################

# START_MODULE_CONTRACT: M-HORIZON-CLAIM-POLICY
# purpose: Provide pure deterministic policy validation functions consumed by
#          HorizonClaimValidator. All functions are side-effect-free.
# owns:
#   - apps/api/app/services/horizon_claim_policy.py
# inputs: Validated block fields, context maps, canon objects.
# outputs: None; raises HorizonClaimValidationError on policy violation.
# dependencies: re/typing stdlib, B1/B2A/B2B schemas, builders, formatter.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - No import from Today/Semantic or validator internals.
#   - Every policy check raises exact HorizonClaimValidationError code.
# failure_policy: raises HorizonClaimValidationError on first policy violation.
# END_MODULE_CONTRACT: M-HORIZON-CLAIM-POLICY

# START_MODULE_MAP: M-HORIZON-CLAIM-POLICY
# public_entrypoints:
#   - check_action_authorization
#   - check_conditional_and_unsupported_policy
#   - check_no_raw_leakage
#   - check_numeric_integrity
#   - normalize_text
# semantic_blocks:
#   - POLICY_IMPORTS: imports and helpers.
#   - POLICY_ACTION: action authorization, intent conflicts.
#   - POLICY_CONDITIONAL: conditional, forbidden, unsupported-life checks.
#   - POLICY_LEAKAGE: internal/raw/sentinel/snake_case scans.
#   - POLICY_NUMERIC: numeric and canonical-copy integrity.
# owned_tests:
#   - apps/api/tests/test_horizon_claim_validator.py
# END_MODULE_MAP: M-HORIZON-CLAIM-POLICY

# START_BLOCK: POLICY_IMPORTS
from __future__ import annotations

import re
from typing import Any, NoReturn

from app.schemas.horizon_content_canon import (
    ActionTemplate,
    HorizonContentCanonBundle,
)
from app.schemas.horizon_guidance import (
    HorizonClaimValidationError,
    HorizonGuidanceContext,
)
from app.schemas.horizon_selection import (
    HORIZON_ORDER,
    SelectedHorizonAnchor,
)
from app.schemas.today_horizons import (
    TodayV2Horizon,
    TodayV2HorizonsBlock,
    TodayV2ProductSphereKey,
)
from app.services.horizon_guidance_builders import ordered_intersection

_WHITESPACE_RE = re.compile(r"\s+")
_NUMERIC_TOKEN_RE = re.compile(r"\d+")
_SNAKE_CASE_FINDER = re.compile(r"[a-z]+(?:_[a-z]+)+")
_TRANSIT_NATAL_PREFIX_RE = re.compile(r"Transit_|Natal_", re.IGNORECASE)
_BRACE_RE = re.compile(r"[{}]")


# END_BLOCK: POLICY_IMPORTS


# START_BLOCK: POLICY_UTILITY
def normalize_text(value: str) -> str:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CLAIM-POLICY.normalize_text
    # purpose: Collapse whitespace and casefold for comparison.
    # inputs: value - any user-visible string.
    # returns: normalized string for pattern matching.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CLAIM-POLICY.normalize_text
    """Collapse whitespace and casefold for comparison."""
    return " ".join(value.split()).casefold()


def collect_user_visible_strings(
    block: TodayV2HorizonsBlock
) -> list[tuple[str, str]]:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CLAIM-POLICY.collect_user_visible_strings
    # purpose: Collect all user-visible copy fields with their structural path names.
    # inputs: block - horizons block.
    # returns: list of tuples (path, text).
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CLAIM-POLICY.collect_user_visible_strings
    strings: list[tuple[str, str]] = []

    strings.append(("intro.eyebrow", block.intro.eyebrow))
    strings.append(("intro.headline", block.intro.headline))
    strings.append(("intro.body", block.intro.body))

    for idx, item in enumerate(block.items):
        prefix = f"items[{idx}]"
        strings.append((f"{prefix}.eyebrow", item.eyebrow))
        strings.append((f"{prefix}.title", item.title))
        strings.append((f"{prefix}.summary", item.summary))
        strings.append((f"{prefix}.plain_explanation", item.plain_explanation))

        strings.append((f"{prefix}.timing.range_label", item.timing.range_label))
        if item.timing.peak_label:
            strings.append((f"{prefix}.timing.peak_label", item.timing.peak_label))
        strings.append((f"{prefix}.timing.state_label", item.timing.state_label))

        for m_idx, m in enumerate(item.manifestations):
            m_prefix = f"{prefix}.manifestations[{m_idx}]"
            strings.append((f"{m_prefix}.title", m.title))
            if m.condition:
                strings.append((f"{m_prefix}.condition", m.condition))
            strings.append((f"{m_prefix}.body", m.body))

        if item.strength is not None:
            strings.append((f"{prefix}.strength.text", item.strength.text))
        if item.risk is not None:
            strings.append((f"{prefix}.risk.text", item.risk.text))

        strings.append((f"{prefix}.actions.heading", item.actions.heading))
        if item.actions.valid_until_label:
            strings.append((f"{prefix}.actions.valid_until_label", item.actions.valid_until_label))

        for act_idx, act in enumerate(item.actions.do):
            strings.append((f"{prefix}.actions.do[{act_idx}].text", act.text))
        for act_idx, act in enumerate(item.actions.avoid):
            strings.append((f"{prefix}.actions.avoid[{act_idx}].text", act.text))

        for t_idx, t in enumerate(item.technique_explanations):
            t_prefix = f"{prefix}.technique_explanations[{t_idx}]"
            strings.append((f"{t_prefix}.label", t.label))
            strings.append((f"{t_prefix}.what_it_is", t.what_it_is))
            strings.append((f"{t_prefix}.why_it_matters_now", t.why_it_matters_now))

            if t.timing:
                strings.append((f"{t_prefix}.timing.range_label", t.timing.range_label))
                if t.timing.peak_label:
                    strings.append((f"{t_prefix}.timing.peak_label", t.timing.peak_label))
                strings.append((f"{t_prefix}.timing.state_label", t.timing.state_label))

    if block.warnings:
        for w_idx, w in enumerate(block.warnings):
            strings.append((f"warnings[{w_idx}]", w))

    return strings


# END_BLOCK: POLICY_UTILITY


# START_BLOCK: POLICY_ACTION
def check_action_authorization(
    *,
    block: TodayV2HorizonsBlock,
    context: HorizonGuidanceContext,
    anchor_by_horizon: dict[str, SelectedHorizonAnchor],
    canon: HorizonContentCanonBundle,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CLAIM-POLICY.check_action_authorization
    # purpose: Validate each action's theme/bucket/text/conditional/provenance/
    #          tone/verdict/intent against canon. Also detects intent pairs
    #          (forbidden combinations across horizons).
    # inputs: block, context, anchor_by_horizon, canon.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises HorizonClaimValidationError on first violation.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CLAIM-POLICY.check_action_authorization
    normalized_texts: set[str] = set()

    # Collect all intents across all horizons for pair checking
    all_do_intents: dict[str, str] = {}
    all_avoid_intents: dict[str, str] = {}

    for h_idx, horizon_item in enumerate(block.items):
        hid = horizon_item.horizon
        anchor = anchor_by_horizon.get(hid)
        if anchor is None:
            continue
        horizon_theme = (
            context.selection.shared_theme_keys[0]
            if context.selection.shared_theme_keys[0] in anchor.theme_keys
            else anchor.theme_keys[0]
        )
        action_matrix = canon.actions.themes.get(horizon_theme)
        if action_matrix is None:
            _fail(
                "action_not_authorized",
                f"items[{h_idx}].actions",
            )
        lists = getattr(action_matrix, hid)

        do_templates = {t.id: t for t in lists.do}
        avoid_templates = {t.id: t for t in lists.avoid}
        tone = horizon_item.tone

        # Validate do list
        for act_idx, act_item in enumerate(horizon_item.actions.do):
            path = f"items[{h_idx}].actions.do[{act_idx}]"
            template = do_templates.get(act_item.id)
            if template is None:
                _fail("action_not_authorized", path)
            if act_item.kind != "action":
                _fail("action_not_authorized", f"{path}.kind")
            if act_item.text != template.text:
                _fail("action_not_authorized", f"{path}.text")
            if act_item.conditional != template.conditional:
                _fail("action_not_authorized", f"{path}.conditional")
            if act_item.provenance.activation_ids != [anchor.activation_id]:
                _fail("action_not_authorized", f"{path}.provenance.activation_ids")
            if tone not in template.tones:
                _fail("action_not_authorized", f"{path}.tone")

            expected_spheres = ordered_intersection(
                list(anchor.product_spheres),
                list(template.sphere_keys),
            )
            if act_item.provenance.sphere_keys != expected_spheres:
                _fail("action_not_authorized", f"{path}.provenance.sphere_keys")
            if act_item.provenance.profile_fact_ids:
                _fail("action_not_authorized", f"{path}.provenance.profile_fact_ids")

            safety = canon.actions.safety_classes.get(template.safety_class)
            if safety is None:
                _fail("action_verdict_conflict", f"{path}.safety_class")
            for sphere in act_item.provenance.sphere_keys:
                verdict = context.sphere_verdicts.get(sphere)
                if verdict is not None and (
                    verdict not in safety.compatible_verdicts
                ):
                    _fail("action_verdict_conflict", f"{path}.verdict")

            normalized = normalize_text(act_item.text)
            if normalized in normalized_texts:
                _fail("action_not_authorized", path)
            normalized_texts.add(normalized)

            if template.intent in canon.actions.forbidden_intents:
                _fail(
                    "action_intent_conflict",
                    f"{path}.intent",
                )
            all_do_intents[path] = template.intent

        # Validate avoid list
        for act_idx, act_item in enumerate(horizon_item.actions.avoid):
            path = f"items[{h_idx}].actions.avoid[{act_idx}]"
            template = avoid_templates.get(act_item.id)
            if template is None:
                _fail("action_not_authorized", path)
            if act_item.kind != "avoid":
                _fail("action_not_authorized", f"{path}.kind")
            if act_item.text != template.text:
                _fail("action_not_authorized", f"{path}.text")
            if act_item.conditional != template.conditional:
                _fail("action_not_authorized", f"{path}.conditional")
            if act_item.provenance.activation_ids != [anchor.activation_id]:
                _fail("action_not_authorized", f"{path}.provenance.activation_ids")
            if tone not in template.tones:
                _fail("action_not_authorized", f"{path}.tone")

            expected_spheres = ordered_intersection(
                list(anchor.product_spheres),
                list(template.sphere_keys),
            )
            if act_item.provenance.sphere_keys != expected_spheres:
                _fail("action_not_authorized", f"{path}.provenance.sphere_keys")
            if act_item.provenance.profile_fact_ids:
                _fail("action_not_authorized", f"{path}.provenance.profile_fact_ids")

            safety = canon.actions.safety_classes.get(template.safety_class)
            if safety is None:
                _fail("action_verdict_conflict", f"{path}.safety_class")
            for sphere in act_item.provenance.sphere_keys:
                verdict = context.sphere_verdicts.get(sphere)
                if verdict is not None and (
                    verdict not in safety.compatible_verdicts
                ):
                    _fail("action_verdict_conflict", f"{path}.verdict")

            normalized = normalize_text(act_item.text)
            if normalized in normalized_texts:
                _fail("action_not_authorized", path)
            normalized_texts.add(normalized)

            if template.intent in canon.actions.forbidden_intents:
                _fail(
                    "action_intent_conflict",
                    f"{path}.intent",
                )
            all_avoid_intents[path] = template.intent

    # Forbidden intent pairs across all horizons
    for do_intent in all_do_intents.values():
        for avoid_intent in all_avoid_intents.values():
            if (do_intent, avoid_intent) in canon.actions.forbidden_intent_pairs:
                _fail("action_intent_conflict", "actions.intent_pair")


# END_BLOCK: POLICY_ACTION


# START_BLOCK: POLICY_CONDITIONAL
def check_conditional_and_unsupported_policy(
    *,
    block: TodayV2HorizonsBlock,
    canon: HorizonContentCanonBundle,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CLAIM-POLICY.check_conditional_and_unsupported_policy
    # purpose: Validate conditional prefix requirements, forbidden fragments
    #          (certainty + high-stakes) in all user-visible fields, and
    #          unsupported-life assertions in non-exempt user copy.
    # inputs: block, canon.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises HorizonClaimValidationError.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CLAIM-POLICY.check_conditional_and_unsupported_policy
    policy = canon.language.conditional_policy
    forbidden = list(policy.forbidden_certainty_fragments) + list(
        policy.forbidden_high_stakes_fragments
    )
    required_prefixes = policy.required_prefixes
    conditional_action_paths: set[str] = set()

    # 1. Structural Manifestations conditional check
    for h_idx, item in enumerate(block.items):
        for m_idx, mani in enumerate(item.manifestations):
            path = f"items[{h_idx}].manifestations[{m_idx}].condition"
            if not mani.condition:
                _fail("conditional_policy_invalid", path)
            if not any(
                mani.condition.startswith(p) for p in required_prefixes
            ):
                _fail("conditional_policy_invalid", path)

    # 2. Structural Actions conditional check
    for h_idx, item in enumerate(block.items):
        action_groups = (("do", item.actions.do), ("avoid", item.actions.avoid))
        for bucket, actions in action_groups:
            for act_idx, act_item in enumerate(actions):
                if not act_item.conditional:
                    continue
                path = f"items[{h_idx}].actions.{bucket}[{act_idx}].text"
                conditional_action_paths.add(path)
                if not any(act_item.text.startswith(p) for p in required_prefixes):
                    _fail("conditional_policy_invalid", path)

    # 3. Policy scans on all visible strings
    visible_strings = collect_user_visible_strings(block)

    for identifier, text in visible_strings:
        # Forbidden certainty / high-stakes fragments apply everywhere
        _check_forbidden(text, forbidden, identifier)

        # Non-conditional copy must not contain unsupported assertions
        # We exempt:
        # - manifestation condition (if it starts with required prefix)
        # - action text if it is conditional and starts with required prefix
        is_exempt = False
        if ".condition" in identifier:
            if any(text.startswith(p) for p in required_prefixes):
                is_exempt = True
        elif ".actions." in identifier and identifier.endswith(".text"):
            is_exempt = identifier in conditional_action_paths and any(
                text.startswith(p) for p in required_prefixes
            )

        if not is_exempt:
            _check_unsupported(text, identifier)


UNSUPPORTED_ASSERTIONS: list[str] = [
    "у вас есть партнёр",
    "ваш муж",
    "ваша жена",
    "ваша должность",
    "ваш работодатель",
    "у вас есть долг",
    "ваш кредит",
    "ваш доход",
    "у вас болезнь",
    "у вас диагноз",
    "вас уволят",
    "вы увольняетесь",
    "вы переедете",
    "сделка состоится",
    "это уже произошло",
]


def _check_unsupported(text: str, item_id: str) -> None:
    normalized = normalize_text(text)
    for assertion in UNSUPPORTED_ASSERTIONS:
        if assertion in normalized:
            _fail(
                "unsupported_life_claim",
                item_id,
            )


def _check_forbidden(
    text: str, forbidden: list[str], item_id: str
) -> None:
    normalized = normalize_text(text)
    for fragment in forbidden:
        norm_frag = normalize_text(fragment)
        if norm_frag in normalized:
            _fail("forbidden_claim", item_id)


# END_BLOCK: POLICY_CONDITIONAL


# START_BLOCK: POLICY_LEAKAGE
def check_no_raw_leakage(
    *,
    block: TodayV2HorizonsBlock,
    forbidden_ids: set[str] | None = None,
    forbidden_tokens: set[str] | None = None,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CLAIM-POLICY.check_no_raw_leakage
    # purpose: Scan every user-visible string for Transit_/Natal_ prefixes,
    #          embedded activation IDs, fact IDs, privacy sentinels, and
    #          snake_case machine keys.
    # inputs: block, optional forbidden_id/forbidden_token sets for
    #         activation/fact/sentinel detection.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises HorizonClaimValidationError on
    #   internal_copy_leak.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CLAIM-POLICY.check_no_raw_leakage
    all_reject_ids = forbidden_ids or set()
    all_reject_tokens = forbidden_tokens or set()

    strings = collect_user_visible_strings(block)

    for identifier, text in strings:
        if _TRANSIT_NATAL_PREFIX_RE.search(text):
            _fail(
                "internal_copy_leak",
                f"{identifier}.raw_prefix",
            )
        if all_reject_ids:
            for rid in all_reject_ids:
                if rid in text:
                    _fail(
                        "internal_copy_leak",
                        f"{identifier}.embedded_id",
                    )
        if all_reject_tokens:
            for token in all_reject_tokens:
                if token in text:
                    _fail(
                        "internal_copy_leak",
                        f"{identifier}.embedded_token",
                    )
        # Snake_case: find any embedded snake_case token
        for match in _SNAKE_CASE_FINDER.finditer(text):
            token = match.group()
            cleaned = token.strip(".,!?:;—\"'()")
            if _is_snake_case(cleaned):
                _fail(
                    "internal_copy_leak",
                    f"{identifier}.snake_case",
                )


def _is_snake_case(value: str) -> bool:
    """Return True if value is a whole snake_case token."""
    return bool(re.fullmatch(r"[a-z]+(?:_[a-z]+)+", value))


# END_BLOCK: POLICY_LEAKAGE


# START_BLOCK: POLICY_NUMERIC
def check_numeric_integrity(
    *,
    block: TodayV2HorizonsBlock,
    canon: HorizonContentCanonBundle,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CLAIM-POLICY.check_numeric_integrity
    # purpose: Reject any numeric token in non-timing copy that does not
    #          match expected canonical copy (exact reconstructed).
    # inputs: block, canon.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises HorizonClaimValidationError on
    #   numeric_claim_not_grounded.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CLAIM-POLICY.check_numeric_integrity
    non_timing_strings: list[tuple[str, str]] = []

    non_timing_strings.append(("intro.headline", block.intro.headline))
    non_timing_strings.append(("intro.body", block.intro.body))
    for h_idx, item in enumerate(block.items):
        prefix = f"items[{h_idx}]"
        non_timing_strings.append((f"{prefix}.title", item.title))
        non_timing_strings.append((f"{prefix}.summary", item.summary))
        for bucket, actions in (("do", item.actions.do), ("avoid", item.actions.avoid)):
            for act_idx, act_item in enumerate(actions):
                non_timing_strings.append((f"{prefix}.actions.{bucket}[{act_idx}].text", act_item.text))
        for name, grounded in (("strength", item.strength), ("risk", item.risk)):
            if grounded is not None:
                non_timing_strings.append((f"{prefix}.{name}.text", grounded.text))
        for m_idx, mani in enumerate(item.manifestations):
            m_prefix = f"{prefix}.manifestations[{m_idx}]"
            non_timing_strings.append((f"{m_prefix}.title", mani.title))
            non_timing_strings.append((f"{m_prefix}.body", mani.body))
            if mani.condition:
                non_timing_strings.append((f"{m_prefix}.condition", mani.condition))
        for t_idx, t in enumerate(item.technique_explanations):
            t_prefix = f"{prefix}.technique_explanations[{t_idx}]"
            non_timing_strings.append((f"{t_prefix}.label", t.label))
            non_timing_strings.append((f"{t_prefix}.what_it_is", t.what_it_is))

    canonical_texts: set[str] = set()
    for s in canon.language.personal_statements.values():
        canonical_texts.add(normalize_text(s.text))
    for ps in canon.language.product_spheres.values():
        canonical_texts.add(normalize_text(ps.manifestation_title))
        canonical_texts.add(normalize_text(ps.manifestation_body))
    for m in canon.actions.themes.values():
        for hid in HORIZON_ORDER:
            for do_item in getattr(m, hid).do:
                canonical_texts.add(normalize_text(do_item.text))
            for avoid_item in getattr(m, hid).avoid:
                canonical_texts.add(normalize_text(avoid_item.text))
    for theme_lang in canon.language.themes.values():
        canonical_texts.add(normalize_text(theme_lang.headline))
        canonical_texts.add(normalize_text(theme_lang.intro_body))
        for hid in HORIZON_ORDER:
            sub = getattr(theme_lang, hid)
            canonical_texts.add(normalize_text(sub.title))
            canonical_texts.add(normalize_text(sub.plain_explanation))
    for tl in canon.language.techniques.values():
        canonical_texts.add(normalize_text(tl.label))
        canonical_texts.add(normalize_text(tl.what_it_is))

    for identifier, text in non_timing_strings:
        normalized = normalize_text(text)
        if _NUMERIC_TOKEN_RE.search(normalized):
            if normalized not in canonical_texts:
                _fail(
                    "numeric_claim_not_grounded",
                    f"{identifier}.numeric",
                )


# END_BLOCK: POLICY_NUMERIC


def _fail(code: str, detail: str = "") -> NoReturn:
    raise HorizonClaimValidationError(code, detail)


__all__ = [
    "check_action_authorization",
    "check_conditional_and_unsupported_policy",
    "check_no_raw_leakage",
    "check_numeric_integrity",
    "normalize_text",
]

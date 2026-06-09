#!/usr/bin/env bash
# ############################################################################
# Grep guard for W-HORARY-ANSWER-QUALITY-V1.
#
# Fails the build if any of the following forbidden defaults are present:
#   1. hardcoded "2–3 недели" / "2-3 недели" in the horary LLM prompt template.
#   2. generic horary fallback text in answer generation code.
#   3. UI rendering "вероятность" for horary confidence.
# ############################################################################
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT" || exit 2

errors=0

fail() {
  echo "  [horary-quality-guard] $*" >&2
  errors=$((errors + 1))
}

# 1. No hardcoded "2–3 недели" in the horary LLM prompt template as a default.
#    The literal may appear in a *test* (assertion that the prompt is
#    well-formed) or in docs. We restrict the search to LLM prompt building
#    and the production horary code path.
if grep -RIn --color=never \
    -E '"2–3 недели"|"2-3 недели"|time_range.*2.3 недел' \
    apps/api/app/services/llm_service.py \
    apps/api/app/services/horary_engine.py \
    apps/api/app/services/horary_service.py \
    2>/dev/null; then
  fail "hardcoded default '2–3 недели' found in horary prompt/code (TZ §3.3, §6 grep guard)"
fi

# 2. No generic fallback text in horary answer generation.
if grep -RIn --color=never \
    -E 'Звёзды склоняются к положительному ответу|обстоятельства складываются не в твою пользу|ситуация неопределённая, звёзды не дают однозначного' \
    apps/api/app/services/llm_service.py \
    apps/api/app/services/horary_service.py \
    2>/dev/null; then
  fail "generic horary fallback text found in answer generation (TZ §4.4)"
fi

# 3. UI must not contain 'вероятность' for horary confidence.
if grep -RIn --color=never 'вероятность' \
    components/readings/horary/ \
    lib/contracts/horary.ts \
    2>/dev/null; then
  fail "horary UI contains 'вероятность' (TZ §3.1, §5.1, §6 grep guard)"
fi

if [[ "$errors" -gt 0 ]]; then
  echo "[horary-quality-guard] FAIL — $errors violation(s)" >&2
  exit 1
fi

echo "[horary-quality-guard] OK"

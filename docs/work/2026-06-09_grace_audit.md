# GRACE CANON Compliance Audit Report

**Date:** 2026-06-09  
**Target:** All Python, TypeScript, and TSX files (excluding `/legacy`)

## 1. Summary Statistics

- **Total files audited:** 460
- **AI Header present:** 197 (42.8%)
- **Module Contract present:** 60 (13.0%)
- **Module Map present:** 43 (9.3%)
- **Paired Blocks present:** 55 (12.0%)
- **Logging present:** 32 (7.0%)

## 2. Compliance Breakdown by Module / Directory

### __tests__ (48 files)

| File | AI Header | Contract | Map | Blocks | Logs |
| --- | --- | --- | --- | --- | --- |
| `__tests__/api/access.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/api/calendar.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/api/cities.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/api/geo.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/api/grace-client.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/api/onboarding-payload.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/api/profile-meta.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/api/readings.test.ts` | ❌ | ❌ | ❌ | ❌ | ✅ |
| `__tests__/components/ChatScreen.test.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/components/DateHeader.test.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/components/ErrorBoundary.test.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/components/NumField.test.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/components/Paywall.test.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/components/ReadingCard.test.tsx` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/components/TabBar.test.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/components/TodayImportantAccordion.test.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/components/TodayScreen.test.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/components/TrialBanner.test.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/contracts/access.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/contracts/calendar.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/contracts/chat.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/contracts/city.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/contracts/natal.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/contracts/profile.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/contracts/today.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/grace-discipline.test.ts` | ✅ | ✅ | ✅ | ✅ (4) | ❌ |
| `__tests__/hooks/useAccess.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/hooks/useCalendar.test.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/hooks/useChat.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/hooks/useDay.test.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/hooks/useOnboarded.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/hooks/useProfile.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/hooks/useTelegramAuth.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/hooks/useToast.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/lib/access.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/lib/adapt-payload.test.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/lib/calendar.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/lib/chat.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/lib/chatReducer.test.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/lib/date.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/lib/icons.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/lib/loader-progress.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/lib/log-shipper.test.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/lib/logger.test.ts` | ✅ | ❌ | ❌ | ❌ | ✅ |
| `__tests__/lib/profile.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/lib/storage-keys.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/lib/today.test.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `__tests__/reducers/onboarding-reducer.test.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |

### app (17 files)

| File | AI Header | Contract | Map | Blocks | Logs |
| --- | --- | --- | --- | --- | --- |
| `app/(grace)/calendar/page.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `app/(grace)/chat/page.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `app/(grace)/day/[date]/page.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `app/(grace)/debug/page.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `app/(grace)/layout.tsx` | ✅ | ❌ | ❌ | ❌ | ✅ |
| `app/(grace)/onboarding/page.tsx` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `app/(grace)/page.tsx` | ❌ | ❌ | ❌ | ❌ | ✅ |
| `app/(grace)/profile/page.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `app/(grace)/readings/horary/[id]/page.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `app/(grace)/readings/horary/page.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `app/(grace)/readings/natal/page.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `app/(grace)/readings/page.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `app/(grace)/today/page.tsx` | ✅ | ✅ | ✅ | ✅ (3) | ❌ |
| `app/debug-auth/page.tsx` | ❌ | ❌ | ❌ | ❌ | ✅ |
| `app/layout.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `app/reset/page.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `app/test-hook/page.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |

### apps/api (131 files)

| File | AI Header | Contract | Map | Blocks | Logs |
| --- | --- | --- | --- | --- | --- |
| `apps/api/alembic/env.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/alembic/versions/0000_baseline.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/alembic/versions/0001_users.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/alembic/versions/0002_add_access_ledger.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/alembic/versions/0003_add_cache.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/alembic/versions/0004_add_semantic.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/alembic/versions/0005_add_microcopy_misses.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/alembic/versions/0006_add_payments.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/alembic/versions/0007_add_evening_checkins.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/alembic/versions/0008_add_chat_tables.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/alembic/versions/0009_add_chat_quotas.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/alembic/versions/0010_add_profile_locations.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/alembic/versions/0011_add_horary.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/alembic/versions/__init__.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/alembic/versions/dab464195b91_add_is_onboarded_to_user_profiles.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/__init__.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/api/__init__.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/api/_log.py` | ✅ | ✅ | ✅ | ✅ (1) | ✅ |
| `apps/api/app/api/auth.py` | ✅ | ✅ | ✅ | ✅ (3) | ✅ |
| `apps/api/app/api/calendar.py` | ✅ | ✅ | ✅ | ✅ (3) | ❌ |
| `apps/api/app/api/chat.py` | ✅ | ✅ | ❌ | ✅ (4) | ❌ |
| `apps/api/app/api/checkin.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/api/day.py` | ✅ | ✅ | ✅ | ✅ (1) | ❌ |
| `apps/api/app/api/debug.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/api/geo.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/api/health.py` | ✅ | ✅ | ✅ | ✅ (1) | ❌ |
| `apps/api/app/api/health_extended.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/api/horary.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/api/metrics.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/api/microcopy.py` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `apps/api/app/api/natal.py` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `apps/api/app/api/payment.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/api/profile.py` | ✅ | ✅ | ✅ | ✅ (2) | ✅ |
| `apps/api/app/api/referral.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/clients/__init__.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/clients/solarsage_client.py` | ✅ | ✅ | ✅ | ✅ (2) | ❌ |
| `apps/api/app/core/__init__.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/core/config.py` | ✅ | ✅ | ✅ | ✅ (3) | ❌ |
| `apps/api/app/core/dependencies.py` | ✅ | ✅ | ✅ | ✅ (1) | ✅ |
| `apps/api/app/core/logging.py` | ✅ | ✅ | ❌ | ✅ (2) | ✅ |
| `apps/api/app/core/redactor.py` | ✅ | ✅ | ❌ | ✅ (2) | ❌ |
| `apps/api/app/core/security.py` | ✅ | ✅ | ✅ | ✅ (2) | ❌ |
| `apps/api/app/db/__init__.py` | ✅ | ✅ | ✅ | ✅ (1) | ❌ |
| `apps/api/app/db/models.py` | ✅ | ✅ | ✅ | ✅ (14) | ❌ |
| `apps/api/app/db/session.py` | ✅ | ✅ | ✅ | ✅ (4) | ❌ |
| `apps/api/app/main.py` | ✅ | ✅ | ✅ | ✅ (4) | ✅ |
| `apps/api/app/middleware/__init__.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/middleware/correlation.py` | ✅ | ✅ | ❌ | ✅ (1) | ❌ |
| `apps/api/app/schemas/__init__.py` | ✅ | ✅ | ✅ | ✅ (1) | ❌ |
| `apps/api/app/schemas/_base.py` | ✅ | ✅ | ✅ | ✅ (1) | ❌ |
| `apps/api/app/schemas/access.py` | ✅ | ✅ | ✅ | ✅ (1) | ❌ |
| `apps/api/app/schemas/auth.py` | ✅ | ✅ | ✅ | ✅ (3) | ❌ |
| `apps/api/app/schemas/calendar.py` | ✅ | ✅ | ✅ | ✅ (1) | ❌ |
| `apps/api/app/schemas/chat.py` | ✅ | ✅ | ❌ | ✅ (3) | ❌ |
| `apps/api/app/schemas/checkin.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/schemas/geo.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/schemas/horary.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/schemas/natal.py` | ✅ | ✅ | ✅ | ✅ (2) | ❌ |
| `apps/api/app/schemas/normalization.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/schemas/payment.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/schemas/profile.py` | ✅ | ✅ | ✅ | ✅ (4) | ❌ |
| `apps/api/app/schemas/referral.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/schemas/semantic.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/schemas/today.py` | ✅ | ✅ | ✅ | ✅ (7) | ❌ |
| `apps/api/app/services/__init__.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/services/access_service.py` | ✅ | ✅ | ✅ | ✅ (2) | ❌ |
| `apps/api/app/services/astro_utils.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/services/calendar_service.py` | ✅ | ✅ | ✅ | ✅ (3) | ❌ |
| `apps/api/app/services/chat_quota_service.py` | ✅ | ✅ | ❌ | ✅ (4) | ❌ |
| `apps/api/app/services/chat_service.py` | ✅ | ✅ | ❌ | ✅ (4) | ✅ |
| `apps/api/app/services/checkin_service.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/services/day_delta_service.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/services/geonames.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/services/horary_credit_service.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/services/horary_engine.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/services/horary_service.py` | ✅ | ❌ | ❌ | ❌ | ✅ |
| `apps/api/app/services/llm_service.py` | ✅ | ❌ | ❌ | ❌ | ✅ |
| `apps/api/app/services/log_intake.py` | ✅ | ✅ | ✅ | ✅ (1) | ✅ |
| `apps/api/app/services/microcopy_service.py` | ✅ | ✅ | ❌ | ❌ | ✅ |
| `apps/api/app/services/natal_service.py` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `apps/api/app/services/normalization_service.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/services/payment_service.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/services/profile_service.py` | ✅ | ✅ | ✅ | ✅ (5) | ✅ |
| `apps/api/app/services/scoring_service.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/services/semantic_service.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/services/session_service.py` | ✅ | ✅ | ✅ | ✅ (3) | ❌ |
| `apps/api/app/services/telegram_auth.py` | ✅ | ✅ | ✅ | ✅ (2) | ❌ |
| `apps/api/app/services/today_important_service.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/app/services/today_service.py` | ✅ | ✅ | ✅ | ✅ (1) | ✅ |
| `apps/api/app/services/yesterday_service.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/__init__.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/conftest.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/fixtures/regenerate_golden.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/integration/__init__.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/integration/conftest.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/integration/test_cache.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/integration/test_locked_day.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/integration/test_user_flow.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_access_service.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_alembic_roundtrip.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_auth_endpoints.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_calendar_endpoints.py` | ✅ | ✅ | ✅ | ✅ (6) | ❌ |
| `apps/api/tests/test_chat.py` | ✅ | ✅ | ❌ | ✅ (5) | ❌ |
| `apps/api/tests/test_chat_quota.py` | ✅ | ✅ | ❌ | ✅ (3) | ❌ |
| `apps/api/tests/test_checkin.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_critical_gaps.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_day_endpoints.py` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_geonames_timezone.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_health.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_horary_endpoints.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_horary_service.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_llm_context_accuracy.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_llm_fallback.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_llm_service.py` | ✅ | ✅ | ✅ | ✅ (5) | ❌ |
| `apps/api/tests/test_log_intake.py` | ✅ | ✅ | ✅ | ✅ (3) | ❌ |
| `apps/api/tests/test_logging.py` | ✅ | ✅ | ❌ | ✅ (2) | ❌ |
| `apps/api/tests/test_microcopy_misses.py` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_natal.py` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_normalization.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_payment.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_pipeline_golden.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_pipeline_integration.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_pipeline_invariants.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_profile_endpoints.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_referral_endpoints.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_scoring.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_semantic.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_solarsage_client.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_subscription_ledger.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_telegram_hmac.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/api/tests/test_today_important.py` | ✅ | ❌ | ❌ | ❌ | ❌ |

### apps/solarsage (28 files)

| File | AI Header | Contract | Map | Blocks | Logs |
| --- | --- | --- | --- | --- | --- |
| `apps/solarsage/collect_solarsage_western_deep.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/solarsage/__init__.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/solarsage/api/__init__.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/solarsage/api/health.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/solarsage/api/natal.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/solarsage/api/transits.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/solarsage/app.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/solarsage/core/__init__.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/solarsage/core/config.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/solarsage/core/health.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/solarsage/models/__init__.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/solarsage/models/chart.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/solarsage/models/position.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/solarsage/schemas/__init__.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/solarsage/schemas/health.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/solarsage/schemas/natal.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/solarsage/schemas/transits.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/solarsage/services/__init__.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/solarsage/services/calculator.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/solarsage/services/natal.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/solarsage/services/transits.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/solarsage/utils/__init__.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/solarsage/utils/ephemeris.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/tests/test_health.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/tests/test_natal.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/tests/test_parity.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/tests/test_services.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `apps/solarsage/tests/test_transits.py` | ✅ | ❌ | ❌ | ❌ | ❌ |

### components (138 files)

| File | AI Header | Contract | Map | Blocks | Logs |
| --- | --- | --- | --- | --- | --- |
| `components/app-shell.tsx` | ❌ | ❌ | ❌ | ❌ | ✅ |
| `components/calendar/calendar-screen.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/calendar/mood-icon.tsx` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `components/chat/chat-empty.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/chat/chat-screen.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/chat/composer.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/chat/context-pill.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/chat/message-bubble.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/chat/suggested-prompts.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/correlation-init.tsx` | ❌ | ❌ | ❌ | ❌ | ✅ |
| `components/debug-button.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/grace/CalendarGrid.tsx` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `components/grace/CalendarMonth.tsx` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `components/grace/DayNavigation.tsx` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `components/grace/ErrorBoundary.tsx` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `components/grace/LoadingSpinner.tsx` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `components/grace/LockedDay.tsx` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `components/grace/Reading.tsx` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `components/grace/ReadingCard.tsx` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `components/grace/TodayScreen.tsx` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `components/grace/TopFlags.tsx` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `components/grace/WeekStrip.tsx` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `components/locked-feature-card.tsx` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `components/monetization/access-card.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/monetization/paywall.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/monetization/trial-banner.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/onboarding/city-picker.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/onboarding/onboarding-flow.tsx` | ❌ | ❌ | ❌ | ❌ | ✅ |
| `components/onboarding/onboarding-shell.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/onboarding/primary-cta.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/onboarding/step-birth.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/onboarding/step-birthday.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/onboarding/step-done.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/onboarding/step-place.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/onboarding/step-welcome.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/paywall.tsx` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `components/profile-reset.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/profile/access-card.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/profile/avatar.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/profile/dev-mode-switcher.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/profile/edit-sheet.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/profile/horary-card.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/profile/profile-row.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/profile/profile-screen.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/profile/referral-card.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/profile/service-row.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/readings/available-card.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/readings/coming-card.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/readings/horary/horary-answer-view.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/readings/horary/horary-block-renderer.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/readings/horary/horary-form.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/readings/horary/horary-progress.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/readings/horary/horary-purchase-sheet.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/readings/horary/horary-question-card.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/readings/horary/horary-quota-bar.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/readings/horary/horary-screen.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/readings/horary/horary-time-confirm.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/readings/in-dev-overlay.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/readings/natal/block-renderer.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/readings/natal/highlights-strip.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/readings/natal/natal-section.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/readings/natal/natal-toc.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/readings/natal/widgets/planets-widget.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/readings/natal/widgets/spheres-widget.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/readings/readings-screen.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/reset-button.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/shared/cosmic-loader.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/shared/num-field.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/telegram-init.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/theme-provider.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/today-important-accordion.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/today-important-block.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/today/date-header.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/today/day-reading.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/today/placeholder-screen.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/today/tab-bar.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/today/today-notes.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/today/today-screen.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/today/week-strip.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/today/why-expanded.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/trial-banner.tsx` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/accordion.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/alert-dialog.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/alert.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/aspect-ratio.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/avatar.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/badge.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/breadcrumb.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/button-group.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/button.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/calendar.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/card.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/carousel.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/chart.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/checkbox.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/collapsible.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/command.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/context-menu.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/dialog.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/drawer.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/dropdown-menu.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/empty.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/field.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/form.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/hover-card.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/input-group.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/input-otp.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/input.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/item.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/kbd.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/label.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/menubar.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/navigation-menu.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/pagination.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/popover.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/progress.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/radio-group.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/resizable.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/scroll-area.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/select.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/separator.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/sheet.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/sidebar.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/skeleton.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/slider.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/sonner.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/spinner.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/switch.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/table.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/tabs.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/textarea.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/toast.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/toaster.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/toggle-group.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/toggle.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/tooltip.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/use-mobile.tsx` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `components/ui/use-toast.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |

### e2e (8 files)

| File | AI Header | Contract | Map | Blocks | Logs |
| --- | --- | --- | --- | --- | --- |
| `e2e/auth-helper.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `e2e/cross-feature-navigation.spec.ts` | ✅ | ❌ | ❌ | ❌ | ✅ |
| `e2e/edge-cases.spec.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `e2e/fixtures.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `e2e/locked-features.spec.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `e2e/onboarding-real.spec.ts` | ✅ | ❌ | ❌ | ❌ | ✅ |
| `e2e/screenshot-all.ts` | ❌ | ❌ | ❌ | ❌ | ✅ |
| `e2e/today.spec.ts` | ✅ | ❌ | ❌ | ❌ | ✅ |

### grace (5 files)

| File | AI Header | Contract | Map | Blocks | Logs |
| --- | --- | --- | --- | --- | --- |
| `grace/orchestrator/__init__.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `grace/orchestrator/cli.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `grace/orchestrator/core.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `grace/orchestrator/test_orchestrator.py` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `grace/orchestrator/validator.py` | ✅ | ❌ | ❌ | ❌ | ❌ |

### hooks (8 files)

| File | AI Header | Contract | Map | Blocks | Logs |
| --- | --- | --- | --- | --- | --- |
| `hooks/use-access.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `hooks/use-chat.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `hooks/use-mobile.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `hooks/use-onboarded.ts` | ❌ | ❌ | ❌ | ❌ | ✅ |
| `hooks/use-profile.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `hooks/use-telegram-auth.ts` | ✅ | ❌ | ❌ | ❌ | ✅ |
| `hooks/use-telegram-user.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `hooks/use-toast.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |

### lib (55 files)

| File | AI Header | Contract | Map | Blocks | Logs |
| --- | --- | --- | --- | --- | --- |
| `lib/access.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `lib/api/access.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/api/calendar.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `lib/api/chat.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/api/cities.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/api/config.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/api/geo.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/api/horary.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/api/natal.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/api/profile-meta.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/api/profile.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `lib/api/readings.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `lib/api/today.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `lib/calendar.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `lib/chat.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/contracts/access.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/contracts/calendar.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `lib/contracts/chat.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/contracts/city.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/contracts/horary.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/contracts/index.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/contracts/natal.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/contracts/profile.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/contracts/readings.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `lib/contracts/today.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `lib/date.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `lib/demo-data.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/demo-mode.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/grace/api/client.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `lib/grace/hooks/useCalendar.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `lib/grace/hooks/useDay.ts` | ✅ | ❌ | ❌ | ❌ | ✅ |
| `lib/grace/index.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `lib/grace/log.ts` | ✅ | ✅ | ✅ | ✅ (1) | ✅ |
| `lib/hooks/use-share-invite.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/icons.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `lib/loader-progress.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/log/index.ts` | ✅ | ✅ | ✅ | ✅ (1) | ✅ |
| `lib/log/shipper.ts` | ✅ | ✅ | ✅ | ✅ (2) | ❌ |
| `lib/logger.ts` | ❌ | ❌ | ❌ | ❌ | ✅ |
| `lib/mocks/access.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/mocks/calendar.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `lib/mocks/chat.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/mocks/cities.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/mocks/natal.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/mocks/profile-meta.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/mocks/readings.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/mocks/today.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `lib/profile-meta.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/profile.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/readings.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/reducers/chat-reducer.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `lib/reducers/onboarding-reducer.ts` | ❌ | ❌ | ❌ | ❌ | ✅ |
| `lib/storage-keys.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `lib/today.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `lib/utils.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |

### packages (9 files)

| File | AI Header | Contract | Map | Blocks | Logs |
| --- | --- | --- | --- | --- | --- |
| `packages/contracts/_generated.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `packages/contracts/access.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `packages/contracts/auth.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `packages/contracts/calendar.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `packages/contracts/horary.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `packages/contracts/index.ts` | ✅ | ✅ | ✅ | ✅ (1) | ❌ |
| `packages/contracts/natal.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `packages/contracts/profile.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `packages/contracts/today.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |

### root (3 files)

| File | AI Header | Contract | Map | Blocks | Logs |
| --- | --- | --- | --- | --- | --- |
| `next-env.d.ts` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `playwright.config.ts` | ✅ | ✅ | ✅ | ✅ (1) | ❌ |
| `vitest.config.ts` | ✅ | ✅ | ✅ | ✅ (1) | ❌ |

### scripts (9 files)

| File | AI Header | Contract | Map | Blocks | Logs |
| --- | --- | --- | --- | --- | --- |
| `scripts/check_docs_manifest.py` | ✅ | ❌ | ❌ | ✅ (3) | ❌ |
| `scripts/check_frontmatter.py` | ✅ | ❌ | ❌ | ✅ (3) | ❌ |
| `scripts/check_orchestrator_contracts.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `scripts/contracts/__init__.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `scripts/contracts/export_openapi.py` | ✅ | ✅ | ✅ | ✅ (4) | ❌ |
| `scripts/generate-telegram-test-initdata.py` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `scripts/grace_lint.py` | ✅ | ✅ | ✅ | ✅ (6) | ❌ |
| `scripts/test_grace_lint.py` | ✅ | ✅ | ✅ | ✅ (5) | ❌ |
| `scripts/test_orchestrator_contracts.py` | ❌ | ❌ | ❌ | ❌ | ❌ |

### types (1 files)

| File | AI Header | Contract | Map | Blocks | Logs |
| --- | --- | --- | --- | --- | --- |
| `types/telegram-web-app.d.ts` | ✅ | ❌ | ❌ | ❌ | ❌ |

## 3. Analysis of Critical Files (Gaps and Rework)

An audit of our codebase (focusing on the new Horary implementation and core access layers) reveals the following structural compliance gaps against `docs/GRACE_CANON.md`:

### 3.1. Backend Service & API Layers (Python)
- **Horary Service (`apps/api/app/services/horary_service.py`):** Has the correct `AI_HEADER` (pointing to `M-HORARY-SERVICE`), but lacks `START_MODULE_CONTRACT` / `END_MODULE_CONTRACT` and `START_MODULE_MAP`.
  - *Fix:* Define the module contract outlining inputs/outputs/invariants, map the entrypoints (`create_question`, `get_question`, `list_questions`, `_refund_credit_for_failed_question`, `_generate_answer_task`), and wrap each method in `START_BLOCK` / `END_BLOCK` tags.
- **Horary Credit Service (`apps/api/app/services/horary_credit_service.py`):** Lacks module contract, map, and block-level segmentation.
  - *Fix:* Add GRACE markers around `resolve_current_access_week`, `get_or_create_current_weekly_free`, `get_balance`, `select_spendable_credit`, and `spend_credit_for_question`.
- **Horary Engine (`apps/api/app/services/horary_engine.py`):** Lacks contract structure and function-level markers.
  - *Fix:* Define how the engine computes verdicts and aspects inside paired blocks.
- **Horary API Router (`apps/api/app/api/horary.py`):** Only contains `AI_HEADER`. Lacks contracts for route endpoints.
  - *Fix:* Wrap endpoints (`get_horary_quota`, `list_horary_questions`, `create_horary_question`, `get_horary_question`) and the helper `_to_question_read` in formal GRACE blocks.

### 3.2. Frontend Component & Page Layers (TSX / TS)
- **Horary UI Components (`components/readings/horary/*`):** `horary-screen.tsx`, `horary-form.tsx`, `horary-quota-bar.tsx`, `horary-time-confirm.tsx`, `horary-progress.tsx`, `horary-answer-view.tsx`, and `horary-block-renderer.tsx` currently contain **no AI Headers**, **no function contracts**, and **no semantic blocks**.
  - *Fix:* Since React component files are semantic modules, they MUST include a JS-comment-style `AI_HEADER` and paired `START_BLOCK` / `END_BLOCK` markers for major lifecycle/render states.
- **Horary Page Router (`app/(grace)/readings/horary/*`):** `page.tsx` and `[id]/page.tsx` lack headers.
  - *Fix:* Add standard AI headers indicating slice/route coordination.
- **API Client Facade (`lib/api/horary.ts`):** Lacks GRACE header and contracts.
  - *Fix:* Add `AI_HEADER` pointing to `M-WEB-API-HORARY` and function contracts for fetch methods.

### 3.3. Log-Driven Compliance & Logging Gaps
The GRACE CANON mandates that critical path actions (external calls, branching decisions, completion of major business steps, and failure conversion) MUST emit structured logs conforming to a specific envelope:
```json
{
  "module": "M-EXAMPLE",
  "fn": "function_name",
  "block": "BLOCK_NAME",
  "event": "event_name",
  "result": "ok|fail|retry|skip",
  "trace_id": "TRACE-...",
  "timestamp": "ISO-8601"
}
```
- **Current Gaps:** 
  - `LLMService` logs failures with generic warnings (`logger.warning("[LLM] OpenRouter failed")`) but does not use the standard GRACE log structure.
  - `HoraryService` logs generation errors and refunds (`logger.info("[Horary Refund] Refunded...")`) with plain strings.
  - *Fix:* Retrofit logging calls on critical pathways to include structured key-value pairs (or JSON envelopes) identifying the `module`, `fn`, `block`, and `event`.

---

## 4. Compliance Action Plan & Coding Templates

To transition the project to 100% GRACE compliance, future waves and postfix reviews should apply the templates below.

### 4.1. Python Module Template (Backend Services & APIs)
```python
# ############################################################################
# AI_HEADER: MODULE_HORARY_SERVICE
# ROLE: Manage horary question lifecycle and background generators.
# DEPENDENCIES: sqlalchemy, app.db.models
# GRACE_ANCHORS: [QUESTION_CREATE, QUESTION_RESOLVE, ANSWER_GENERATOR]
# ############################################################################

# START_MODULE_CONTRACT: M-HORARY-SERVICE
# purpose: Question CRUD, credit spend checks, and background answer cast tasks.
# owns:
#   - apps/api/app/services/horary_service.py
# inputs:
#   - AsyncSession, User ID, question payloads
# outputs:
#   - HoraryQuestion, HoraryAnswer
# invariants:
#   - spend transaction must commit before generation enqueues.
#   - idempotent submits return same row ID without second credit spend.
# END_MODULE_CONTRACT: M-HORARY-SERVICE

# START_MODULE_MAP: M-HORARY-SERVICE
# public_entrypoints:
#   - create_question
#   - get_question
#   - list_questions
# END_MODULE_MAP: M-HORARY-SERVICE
```

### 4.2. TSX Component Template (Frontend UI)
```tsx
// ############################################################################
// AI_HEADER: COMPONENT_HORARY_FORM
// ROLE: Render category chips, textarea, and confirm button.
// DEPENDENCIES: react, lucide-react, @/lib/contracts/horary
// GRACE_ANCHORS: [CATEGORY_SELECT, SUBMIT_BUTTON]
// ############################################################################

/* START_BLOCK: FORM_COMPONENT */
export function HoraryForm({ hasSpendableCredit, onSubmit }: Props) {
  // ...
}
/* END_BLOCK: FORM_COMPONENT */
```

### 4.3. Structured Logging Example (Python)
```python
# Log envelope matching GRACE CANON:
logger.info(
    "[GRACE-LOG] %s",
    json.dumps({
        "module": "M-HORARY-SERVICE",
        "fn": "create_question",
        "block": "QUESTION_SPEND",
        "event": "credit_spent_successfully",
        "result": "ok",
        "question_id": str(question_id),
        "credit_id": str(spend.credit_id),
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
)
```

--- End of Report ---

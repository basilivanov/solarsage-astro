# ############################################################################
# AI_HEADER: PROMO_RATE_LIMITER — in-memory per-user promo attempt rate limiter.
# ROLE: Enforce rolling 10-minute / 10-attempt limit on preview and redeem endpoints per authenticated user UUID.
# DEPENDENCIES: collections.OrderedDict, math, time, uuid
# GRACE_ANCHORS: [PROMO_RATE_LIMITER]
# WAVE: W-NAMED-PROMO-CAMPAIGN
# ############################################################################

# START_MODULE_CONTRACT: M-PROMO-RATE-LIMITER
# purpose: Provide atomic, non-async per-user rate limiting for promo preview and redeem attempts with LRU eviction and rolling window pruning.
# owns:
#   - apps/api/app/services/promo_rate_limiter.py
# inputs:
#   - user_id: uuid.UUID
# outputs:
#   - RateLimitResult(allowed: bool, retry_after_seconds: int)
# dependencies:
#   - standard library: collections.OrderedDict, math, time, uuid
# side_effects:
#   - mutates in-memory OrderedDict cache
# invariants:
#   - key is strictly internal user UUID; no token, hash, IP or session cookie stored or logged
#   - preview and redeem share the same bucket per user
#   - limit is 10 attempts per 600 seconds (10 minutes)
#   - maximum capacity is 10,000 user keys with LRU eviction
#   - check_and_record is synchronous and atomic within single asyncio event loop
# failure_policy: fail-closed if invalid user_id provided
# scaling_invariant:
#   This rate limiter implementation uses an in-memory OrderedDict suited for single Uvicorn worker MVP deployments.
#   Before scaling to multiple API workers (--workers > 1), multiple container replicas, or multi-region instances,
#   this rate limiter MUST be migrated to a shared store (e.g. Redis sliding window or PostgreSQL bucket).
#   Process restarts reset in-memory rate limit state, which is acceptable for security due to high promo token entropy
#   and upstream Nginx volumetric rate limiting.
# END_MODULE_CONTRACT: M-PROMO-RATE-LIMITER

# START_MODULE_MAP: M-PROMO-RATE-LIMITER
# public_entrypoints:
#   - PromoRateLimiter
#   - RateLimitResult
#   - promo_rate_limiter
# semantic_blocks:
#   - LIMITER_CORE: PromoRateLimiter class with check_and_record and reset methods
# owned_tests:
#   - apps/api/tests/test_promo_rate_limiter.py
# END_MODULE_MAP: M-PROMO-RATE-LIMITER

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import math
import time
from typing import Callable
import uuid


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after_seconds: int = 0


class PromoRateLimiter:
    """In-memory per-user promo attempt limiter with rolling window and LRU eviction."""

    def __init__(
        self,
        limit: int = 10,
        window_seconds: float = 600.0,
        max_keys: int = 10_000,
        clock_fn: Callable[[], float] | None = None,
    ):
        self.limit = limit
        self.window_seconds = window_seconds
        self.max_keys = max_keys
        self.clock_fn = clock_fn or time.monotonic
        self._cache: OrderedDict[uuid.UUID, list[float]] = OrderedDict()

    def check_and_record(self, user_id: uuid.UUID) -> RateLimitResult:
        """Check and record attempt for user_id atomically without await or async locks."""
        if not isinstance(user_id, uuid.UUID):
            raise ValueError("user_id must be a valid UUID")

        now = self.clock_fn()
        cutoff = now - self.window_seconds

        # 1. Retrieve or initialize user timestamps
        if user_id in self._cache:
            self._cache.move_to_end(user_id)
            timestamps = self._cache[user_id]
        else:
            timestamps = []

        # 2. Prune expired timestamps
        valid_timestamps = [t for t in timestamps if t > cutoff]

        # 3. LRU Eviction if capacity exceeded
        while len(self._cache) >= self.max_keys and user_id not in self._cache:
            self._cache.popitem(last=False)

        # 4. Check limit
        if len(valid_timestamps) >= self.limit:
            self._cache[user_id] = valid_timestamps
            oldest_attempt = valid_timestamps[0]
            retry_after = max(1, int(math.ceil(oldest_attempt + self.window_seconds - now)))
            return RateLimitResult(allowed=False, retry_after_seconds=retry_after)

        # 5. Record attempt
        valid_timestamps.append(now)
        self._cache[user_id] = valid_timestamps
        return RateLimitResult(allowed=True, retry_after_seconds=0)

    def reset(self) -> None:
        """Reset state for testing."""
        self._cache.clear()


promo_rate_limiter = PromoRateLimiter()

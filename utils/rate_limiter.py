from __future__ import annotations

import threading
import time


class TokenBucketLimiter:
    """Thread-safe token bucket rate limiter.

    Refills at `rate` tokens/second up to `burst` capacity.
    Call acquire() before each outbound request to stay within limits.
    """

    def __init__(self, rate: float, burst: int = 1) -> None:
        self._rate = rate
        self._burst = float(burst)
        self._tokens = float(burst)
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block until one token is available."""
        while True:
            with self._lock:
                now = time.monotonic()
                self._tokens = min(
                    self._burst,
                    self._tokens + (now - self._last) * self._rate,
                )
                self._last = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                wait = (1.0 - self._tokens) / self._rate
            time.sleep(wait)


# ── Shared module-level limiters ───────────────────────────────────────────────
# Coinbase public REST (api.exchange.coinbase.com + api.coinbase.com):
#   documented limit ~10 req/s; use 6 to leave headroom for oracle_price_feed
coinbase_limiter = TokenBucketLimiter(rate=6.0, burst=4)

# Polymarket Gamma API (gamma-api.polymarket.com): undocumented; 3 req/s is safe
gamma_limiter = TokenBucketLimiter(rate=3.0, burst=2)

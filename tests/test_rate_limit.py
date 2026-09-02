from app.rate_limit import SlidingWindowRateLimiter


def test_rate_limiter_returns_429_equivalent_after_limit():
    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=60)

    assert limiter.allow("widget:1:203.0.113.10") is True
    assert limiter.allow("widget:1:203.0.113.10") is True
    assert limiter.allow("widget:1:203.0.113.10") is False


def test_rate_limit_keys_are_isolated():
    limiter = SlidingWindowRateLimiter(limit=1, window_seconds=60)

    assert limiter.allow("widget:1:ip-a") is True
    assert limiter.allow("widget:1:ip-a") is False
    assert limiter.allow("widget:1:ip-b") is True

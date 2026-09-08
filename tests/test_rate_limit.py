import time
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core import rate_limit


class FakeRequest:
    def __init__(self, host="1.2.3.4"):
        self.client = MagicMock(host=host)


@pytest.fixture(autouse=True)
def reset_redis_key():
    """Ensure a clean rate-limit key before and after each test."""
    key = "rate_limit:test-user"
    rate_limit.redis_client.delete(key)
    yield
    rate_limit.redis_client.delete(key)


def test_allows_requests_under_the_limit(monkeypatch):
    monkeypatch.setattr(rate_limit.settings, "rate_limit_requests", 5)
    monkeypatch.setattr(rate_limit.settings, "rate_limit_window_seconds", 60)

    for _ in range(5):
        rate_limit.check_rate_limit(FakeRequest(), identifier="test-user")  # should not raise


def test_blocks_requests_over_the_limit(monkeypatch):
    monkeypatch.setattr(rate_limit.settings, "rate_limit_requests", 3)
    monkeypatch.setattr(rate_limit.settings, "rate_limit_window_seconds", 60)

    for _ in range(3):
        rate_limit.check_rate_limit(FakeRequest(), identifier="test-user")

    with pytest.raises(HTTPException) as exc_info:
        rate_limit.check_rate_limit(FakeRequest(), identifier="test-user")

    assert exc_info.value.status_code == 429


def test_old_requests_fall_outside_the_window(monkeypatch):
    monkeypatch.setattr(rate_limit.settings, "rate_limit_requests", 2)
    monkeypatch.setattr(rate_limit.settings, "rate_limit_window_seconds", 1)

    rate_limit.check_rate_limit(FakeRequest(), identifier="test-user")
    rate_limit.check_rate_limit(FakeRequest(), identifier="test-user")

    time.sleep(1.1)  # let the 1-second window fully elapse

    rate_limit.check_rate_limit(FakeRequest(), identifier="test-user")  # should not raise

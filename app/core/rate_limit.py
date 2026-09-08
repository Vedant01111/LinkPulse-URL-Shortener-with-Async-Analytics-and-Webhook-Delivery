import time

import redis
from fastapi import HTTPException, Request, status

from app.core.config import settings

redis_client = redis.from_url(settings.redis_url, decode_responses=True)


def check_rate_limit(request: Request, identifier: str = None) -> None:
    """
    Sliding-window rate limiter backed by a Redis sorted set.

    Why sorted-set sliding window instead of a simple fixed-window counter:
    a fixed window (e.g. "max 100 req per clock-minute") lets a client burst
    up to 2x the limit right across a window boundary (100 requests at
    23:00:59 + 100 more at 23:01:00). The sliding window avoids that by
    tracking actual request timestamps and only counting the ones inside
    the trailing N-second window, at the cost of slightly more Redis memory
    per key (one entry per request instead of one counter).

    Each request is a member of a Redis ZSET, scored by its timestamp.
    On every check we:
      1. Drop all entries older than the window (ZREMRANGEBYSCORE)
      2. Count what's left (ZCARD)
      3. Reject if at/over the limit, else record this request (ZADD)
      4. Set a TTL on the key so idle identifiers don't leak memory forever
    """
    key = f"rate_limit:{identifier or request.client.host}"
    now = time.time()
    window_start = now - settings.rate_limit_window_seconds

    pipe = redis_client.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zcard(key)
    pipe.zadd(key, {str(now): now})
    pipe.expire(key, settings.rate_limit_window_seconds)
    _, request_count, _, _ = pipe.execute()

    if request_count >= settings.rate_limit_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: max {settings.rate_limit_requests} "
                   f"requests per {settings.rate_limit_window_seconds}s",
        )

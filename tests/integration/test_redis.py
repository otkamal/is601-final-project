from app.conftest import run_async
from unittest.mock import AsyncMock, patch

import pytest

import app.auth.redis as redis_module


@pytest.fixture(autouse=True)
def reset_redis_cache():
    """Ensure get_redis()'s memoized client (cached as a function attribute)
    doesn't leak between tests."""
    if hasattr(redis_module.get_redis, "redis"):
        delattr(redis_module.get_redis, "redis")
    yield
    if hasattr(redis_module.get_redis, "redis"):
        delattr(redis_module.get_redis, "redis")

def test_get_redis_creates_and_caches_client():
    """Test get_redis() creates a client via aioredis.from_url once, then reuses it."""
    mock_client = AsyncMock()
    with patch(
        "app.auth.redis.aioredis.from_url", new=AsyncMock(return_value=mock_client)
    ) as mock_from_url:
        first = run_async(redis_module.get_redis())
        second = run_async(redis_module.get_redis())

    assert first is mock_client
    assert second is mock_client
    mock_from_url.assert_awaited_once()

def test_add_to_blacklist():
    """Test add_to_blacklist stores the jti under a 'blacklist:' key with the given TTL."""
    mock_client = AsyncMock()
    with patch("app.auth.redis.aioredis.from_url", new=AsyncMock(return_value=mock_client)):
        run_async(redis_module.add_to_blacklist("abc123", 3600))

    mock_client.set.assert_awaited_once_with("blacklist:abc123", "1", ex=3600)

def test_is_blacklisted_true():
    """Test is_blacklisted returns a truthy value when the jti key exists."""
    mock_client = AsyncMock()
    mock_client.exists.return_value = 1
    with patch("app.auth.redis.aioredis.from_url", new=AsyncMock(return_value=mock_client)):
        result = run_async(redis_module.is_blacklisted("abc123"))

    assert result
    mock_client.exists.assert_awaited_once_with("blacklist:abc123")

def test_is_blacklisted_false():
    """Test is_blacklisted returns a falsy value when the jti key doesn't exist."""
    mock_client = AsyncMock()
    mock_client.exists.return_value = 0
    with patch("app.auth.redis.aioredis.from_url", new=AsyncMock(return_value=mock_client)):
        result = run_async(redis_module.is_blacklisted("abc123"))

    assert not result

"""
Unit tests for rate limiter implementation.
"""

import asyncio
import pytest
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.api.rate_limiter import (
    RateLimiter, TokenBucket, RateLimitExceeded, PlanType,
    create_rate_limiter, PLAN_CONFIGS
)


class TestTokenBucket:
    """Test TokenBucket implementation."""
    
    def test_token_bucket_initialization(self):
        """Test token bucket initialization."""
        bucket = TokenBucket(capacity=10, refill_rate=2.0)
        
        assert bucket.capacity == 10
        assert bucket.tokens == 10.0
        assert bucket.refill_rate == 2.0
        assert bucket.available_tokens() == 10
    
    def test_token_consumption(self):
        """Test token consumption."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        
        # Should successfully consume tokens
        assert bucket.consume(3) is True
        assert bucket.available_tokens() == 7
        
        # Should fail to consume more tokens than available
        assert bucket.consume(8) is False
        assert bucket.available_tokens() == 7
        
        # Should consume remaining tokens
        assert bucket.consume(7) is True
        assert bucket.available_tokens() == 0
    
    def test_token_refill(self):
        """Test token refill over time."""
        bucket = TokenBucket(capacity=10, refill_rate=2.0)  # 2 tokens per second
        
        # Consume all tokens
        bucket.consume(10)
        assert bucket.available_tokens() == 0
        
        # Mock time advancement
        with patch('time.monotonic') as mock_time:
            mock_time.side_effect = [bucket.last_refill, bucket.last_refill + 2.5]
            
            # Should refill 5 tokens (2.5 seconds * 2 tokens/second)
            available = bucket.available_tokens()
            assert available == 5
    
    def test_thread_safety(self):
        """Test thread safety of token bucket."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        results = []
        
        def consume_tokens():
            for _ in range(10):
                result = bucket.consume(1)
                results.append(result)
                time.sleep(0.001)  # Small delay
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=consume_tokens)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have consumed tokens successfully
        successful_consumptions = sum(results)
        assert successful_consumptions <= 100  # Can't exceed capacity
        assert successful_consumptions > 40    # Should consume reasonable amount


class TestRateLimiter:
    """Test RateLimiter implementation."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(PlanType.FREE)
        
        assert limiter.plan_type == PlanType.FREE
        assert limiter.config == PLAN_CONFIGS[PlanType.FREE]
        assert limiter.daily_usage == 0
        assert limiter.active_requests == 0
        assert limiter.minute_bucket is None  # Free plan has no per-minute limit
    
    def test_prime_plan_initialization(self):
        """Test Prime plan initialization with per-minute limits."""
        limiter = RateLimiter(PlanType.PRIME)
        
        assert limiter.plan_type == PlanType.PRIME
        assert limiter.minute_bucket is not None
        assert limiter.config.per_minute_limit == 60000
    
    @patch('src.api.rate_limiter.datetime')
    def test_daily_reset_calculation(self, mock_datetime):
        """Test daily reset time calculation."""
        # Mock current time as 8:00 AM Eastern (before reset)
        mock_dt = MagicMock()
        mock_dt.replace.return_value = mock_dt
        mock_datetime.now.return_value = mock_dt
        
        with patch('pytz.timezone') as mock_tz:
            mock_eastern = MagicMock()
            mock_tz.return_value = mock_eastern
            mock_eastern.localize = MagicMock()
            
            limiter = RateLimiter(PlanType.FREE)
            
            # Should calculate next reset time
            assert limiter.daily_reset_time is not None
    
    def test_daily_limit_check(self):
        """Test daily limit checking."""
        limiter = RateLimiter(PlanType.FREE)
        limiter.daily_usage = 95  # Near limit of 100
        
        # Should allow request within limit
        limiter.check_rate_limit(3)  # Would use 98 total
        
        # Should raise exception when exceeding limit
        with pytest.raises(RateLimitExceeded) as exc_info:
            limiter.check_rate_limit(10)  # Would use 105 total
        
        assert "Daily rate limit exceeded" in str(exc_info.value)
        assert exc_info.value.retry_after is not None
    
    def test_concurrent_limit_check(self):
        """Test concurrent request limit checking."""
        limiter = RateLimiter(PlanType.FREE)
        limiter.active_requests = 49  # Near limit of 50
        
        # Should allow request within limit
        limiter.check_rate_limit(1)
        
        # Should raise exception at limit
        limiter.active_requests = 50
        with pytest.raises(RateLimitExceeded) as exc_info:
            limiter.check_rate_limit(1)
        
        assert "Concurrent request limit exceeded" in str(exc_info.value)
    
    def test_prime_plan_per_minute_limit(self):
        """Test per-minute limit for Prime plan."""
        limiter = RateLimiter(PlanType.PRIME)
        
        # Consume all tokens in minute bucket
        limiter.minute_bucket.tokens = 0
        
        with pytest.raises(RateLimitExceeded) as exc_info:
            limiter.check_rate_limit(1)
        
        assert "Per-minute rate limit exceeded" in str(exc_info.value)
        assert exc_info.value.retry_after is not None
    
    def test_usage_recording(self):
        """Test usage recording."""
        limiter = RateLimiter(PlanType.FREE)
        initial_usage = limiter.daily_usage
        
        limiter.record_usage(5)
        assert limiter.daily_usage == initial_usage + 5
        
        limiter.record_usage(3)
        assert limiter.daily_usage == initial_usage + 8
    
    def test_concurrent_slot_management(self):
        """Test concurrent slot management."""
        limiter = RateLimiter(PlanType.FREE)
        initial_requests = limiter.active_requests
        
        # Manually increment active requests (normally done by acquire)
        with limiter._concurrent_lock:
            limiter.active_requests += 1
        
        assert limiter.active_requests == initial_requests + 1
        
        # Release slot
        limiter.release_concurrent_slot()
        assert limiter.active_requests == initial_requests
    
    @pytest.mark.asyncio
    async def test_acquire_context_manager(self):
        """Test rate limit context manager."""
        limiter = RateLimiter(PlanType.FREE)
        
        context = await limiter.acquire(2)
        async with context:
            assert limiter.active_requests == 1
            assert context.credits_needed == 2
            
            # Set actual credits consumed
            context.set_credits_consumed(3)
        
        # After exiting context, should record usage and release slot
        assert limiter.active_requests == 0
        assert limiter.daily_usage == 3
    
    def test_usage_stats(self):
        """Test usage statistics."""
        limiter = RateLimiter(PlanType.FREE)
        limiter.daily_usage = 25
        limiter.active_requests = 3
        
        stats = limiter.get_usage_stats()
        
        assert stats['plan_type'] == 'free'
        assert stats['daily_usage'] == 25
        assert stats['daily_limit'] == 100
        assert stats['active_requests'] == 3
        assert stats['concurrent_limit'] == 50
        assert 'next_reset' in stats
    
    def test_create_rate_limiter_function(self):
        """Test rate limiter factory function."""
        # Test valid plan types
        limiter = create_rate_limiter('starter')
        assert limiter.plan_type == PlanType.STARTER
        
        limiter = create_rate_limiter('TRADER')  # Test case insensitive
        assert limiter.plan_type == PlanType.TRADER
        
        # Test invalid plan type (should default to free)
        with patch('src.api.rate_limiter.logger') as mock_logger:
            limiter = create_rate_limiter('invalid')
            assert limiter.plan_type == PlanType.FREE
            mock_logger.warning.assert_called_once()


class TestRateLimitContext:
    """Test rate limit context manager."""
    
    @pytest.mark.asyncio
    async def test_context_manager_success(self):
        """Test successful context manager usage."""
        limiter = RateLimiter(PlanType.FREE)
        
        context = await limiter.acquire(1)
        async with context:
            assert isinstance(context, type(context))
            assert context.credits_needed == 1
            assert context.credits_consumed == 0
            
            context.set_credits_consumed(2)
            assert context.credits_consumed == 2
        
        # Should record actual usage
        assert limiter.daily_usage == 2
    
    @pytest.mark.asyncio
    async def test_context_manager_exception(self):
        """Test context manager with exception."""
        limiter = RateLimiter(PlanType.FREE)
        
        try:
            context = await limiter.acquire(1)
            async with context:
                context.set_credits_consumed(1)
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Should still record usage and release slot even with exception
        assert limiter.daily_usage == 1
        assert limiter.active_requests == 0


@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test handling of concurrent requests."""
    limiter = RateLimiter(PlanType.FREE)
    
    async def make_request(request_id: int, delay: float = 0.1):
        """Simulate an API request."""
        context = await limiter.acquire(1)
        async with context:
            await asyncio.sleep(delay)
            context.set_credits_consumed(1)
            return request_id
    
    # Create multiple concurrent requests
    tasks = []
    for i in range(10):
        task = asyncio.create_task(make_request(i, 0.05))
        tasks.append(task)
    
    # Wait for all requests to complete
    results = await asyncio.gather(*tasks)
    
    # All requests should complete successfully
    assert len(results) == 10
    assert sorted(results) == list(range(10))
    
    # Should have recorded usage
    assert limiter.daily_usage == 10
    assert limiter.active_requests == 0


@pytest.mark.asyncio 
async def test_rate_limit_exceeded_handling():
    """Test handling when rate limits are exceeded."""
    limiter = RateLimiter(PlanType.FREE)
    limiter.daily_usage = 99  # At daily limit
    
    # First request should succeed
    context = await limiter.acquire(1)
    async with context:
        context.set_credits_consumed(1)  # This will bring us to the daily limit
    
    # Second request should fail
    with pytest.raises(RateLimitExceeded):
        await limiter.acquire(1)
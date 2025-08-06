"""
Rate limiter for MarketData.app API requests.

Implements token bucket algorithm to respect API rate limits:
- Maximum 50 concurrent requests across all plans
- Daily limits: 100 (Free), 10,000 (Starter), 100,000 (Trader), unlimited (Prime)
- Per-minute limit for Prime: 60,000
- Rate limit resets at 9:30 AM Eastern Time for daily plans

Based on MarketData.app API documentation.
"""

import asyncio
import threading
import time
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PlanType(Enum):
    """MarketData.app subscription plan types."""
    FREE = "free"
    STARTER = "starter"
    TRADER = "trader"
    PRIME = "prime"


@dataclass
class RateLimitConfig:
    """Rate limit configuration for different plan types."""
    daily_limit: Optional[int]  # None for unlimited
    per_minute_limit: Optional[int]  # None for no per-minute limit
    concurrent_limit: int = 50  # Same for all plans
    reset_hour: int = 9  # 9:30 AM Eastern
    reset_minute: int = 30


# Rate limit configurations by plan type
PLAN_CONFIGS = {
    PlanType.FREE: RateLimitConfig(daily_limit=100, per_minute_limit=None),
    PlanType.STARTER: RateLimitConfig(daily_limit=10000, per_minute_limit=None),
    PlanType.TRADER: RateLimitConfig(daily_limit=100000, per_minute_limit=None),
    PlanType.PRIME: RateLimitConfig(daily_limit=None, per_minute_limit=60000),
}


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


class TokenBucket:
    """Thread-safe token bucket implementation for rate limiting."""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        with self._lock:
            now = time.monotonic()
            # Add tokens based on elapsed time
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def available_tokens(self) -> int:
        """Get number of available tokens."""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            return int(self.tokens)


class RateLimiter:
    """
    Rate limiter for MarketData.app API that handles multiple rate limit types.
    
    Features:
    - Daily rate limits with Eastern Time reset
    - Per-minute rate limits for Prime plan
    - Concurrent request limiting
    - Automatic retry delay calculation
    - Thread-safe operation
    """
    
    def __init__(self, plan_type: PlanType = PlanType.FREE):
        """
        Initialize rate limiter.
        
        Args:
            plan_type: MarketData.app subscription plan type
        """
        self.plan_type = plan_type
        self.config = PLAN_CONFIGS[plan_type]
        
        # Daily usage tracking
        self.daily_usage = 0
        self.daily_reset_time = self._calculate_next_reset_time()
        
        # Per-minute rate limiting (Prime plan only)
        self.minute_bucket = None
        if self.config.per_minute_limit:
            # Allow burst up to limit, refill at limit/minute rate
            self.minute_bucket = TokenBucket(
                capacity=self.config.per_minute_limit,
                refill_rate=self.config.per_minute_limit / 60.0  # tokens per second
            )
        
        # Concurrent request limiting
        self.concurrent_semaphore = asyncio.Semaphore(self.config.concurrent_limit)
        self.active_requests = 0
        
        # Thread safety
        self._usage_lock = threading.Lock()
        self._concurrent_lock = threading.Lock()
        
        logger.info(f"Rate limiter initialized for {plan_type.value} plan")
    
    def _calculate_next_reset_time(self) -> datetime:
        """Calculate next daily reset time (9:30 AM Eastern)."""
        try:
            import pytz
            eastern = pytz.timezone('America/New_York')
            now = datetime.now(eastern)
        except ImportError:
            # Fallback to UTC if pytz not available
            import logging
            logging.warning("pytz not available, using UTC for rate limit resets")
            now = datetime.utcnow()
        
        # Next reset is at 9:30 AM Eastern
        next_reset = now.replace(
            hour=self.config.reset_hour,
            minute=self.config.reset_minute,
            second=0,
            microsecond=0
        )
        
        # If it's already past 9:30 AM today, reset is tomorrow
        if now >= next_reset:
            next_reset += timedelta(days=1)
        
        return next_reset
    
    def _check_daily_reset(self):
        """Check if daily usage should be reset."""
        with self._usage_lock:
            try:
                import pytz
                eastern = pytz.timezone('America/New_York')
                now = datetime.now(eastern)
            except ImportError:
                now = datetime.utcnow()
            
            if now >= self.daily_reset_time:
                logger.info("Daily rate limit reset")
                self.daily_usage = 0
                self.daily_reset_time = self._calculate_next_reset_time()
    
    def check_rate_limit(self, credits_needed: int = 1) -> Optional[float]:
        """
        Check if request would exceed rate limits.
        
        Args:
            credits_needed: Number of API credits the request will consume
            
        Returns:
            None if request is allowed, float (seconds to wait) if rate limited
            
        Raises:
            RateLimitExceeded: If rate limit is exceeded with retry information
        """
        self._check_daily_reset()
        
        # Check daily limit
        if self.config.daily_limit is not None:
            with self._usage_lock:
                if self.daily_usage + credits_needed > self.config.daily_limit:
                    try:
                        import pytz
                        eastern = pytz.timezone('America/New_York')
                        now = datetime.now(eastern)
                    except ImportError:
                        now = datetime.utcnow()
                    retry_after = (self.daily_reset_time - now).total_seconds()
                    raise RateLimitExceeded(
                        f"Daily rate limit exceeded ({self.daily_usage}/{self.config.daily_limit})",
                        retry_after=retry_after
                    )
        
        # Check per-minute limit (Prime plan)
        if self.minute_bucket and not self.minute_bucket.consume(credits_needed):
            # Calculate retry delay based on refill rate
            retry_after = credits_needed / self.minute_bucket.refill_rate
            raise RateLimitExceeded(
                "Per-minute rate limit exceeded",
                retry_after=retry_after
            )
        
        # Check concurrent limit
        with self._concurrent_lock:
            if self.active_requests >= self.config.concurrent_limit:
                raise RateLimitExceeded(
                    f"Concurrent request limit exceeded ({self.active_requests}/{self.config.concurrent_limit})"
                )
        
        return None
    
    async def acquire(self, credits_needed: int = 1) -> 'RateLimitContext':
        """
        Acquire rate limit permission for a request.
        
        Args:
            credits_needed: Number of API credits the request will consume
            
        Returns:
            Context manager for the request
            
        Raises:
            RateLimitExceeded: If rate limit cannot be satisfied
        """
        # Check rate limits
        self.check_rate_limit(credits_needed)
        
        # Acquire concurrent request slot
        await self.concurrent_semaphore.acquire()
        
        with self._concurrent_lock:
            self.active_requests += 1
        
        return RateLimitContext(self, credits_needed)
    
    def record_usage(self, credits_consumed: int):
        """Record actual API credits consumed."""
        with self._usage_lock:
            self.daily_usage += credits_consumed
            logger.debug(f"API usage: {self.daily_usage} credits consumed")
    
    def release_concurrent_slot(self):
        """Release a concurrent request slot."""
        with self._concurrent_lock:
            self.active_requests = max(0, self.active_requests - 1)
        
        self.concurrent_semaphore.release()
    
    def get_usage_stats(self) -> dict:
        """Get current usage statistics."""
        self._check_daily_reset()
        
        with self._usage_lock:
            stats = {
                "plan_type": self.plan_type.value,
                "daily_usage": self.daily_usage,
                "daily_limit": self.config.daily_limit,
                "active_requests": self.active_requests,
                "concurrent_limit": self.config.concurrent_limit,
                "next_reset": self.daily_reset_time.isoformat(),
            }
            
            if self.minute_bucket:
                stats["minute_tokens_available"] = self.minute_bucket.available_tokens()
                stats["per_minute_limit"] = self.config.per_minute_limit
            
            return stats


class RateLimitContext:
    """Context manager for rate-limited API requests."""
    
    def __init__(self, rate_limiter: RateLimiter, credits_needed: int):
        self.rate_limiter = rate_limiter
        self.credits_needed = credits_needed
        self.credits_consumed = 0
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Record actual usage if credits were consumed
        if self.credits_consumed > 0:
            self.rate_limiter.record_usage(self.credits_consumed)
        
        # Always release concurrent slot
        self.rate_limiter.release_concurrent_slot()
    
    def set_credits_consumed(self, credits: int):
        """Set the actual number of credits consumed by the request."""
        self.credits_consumed = credits


def create_rate_limiter(plan_type: str = "free") -> RateLimiter:
    """
    Create a rate limiter for the specified plan type.
    
    Args:
        plan_type: Plan type string (free, starter, trader, prime)
        
    Returns:
        Configured RateLimiter instance
    """
    try:
        plan_enum = PlanType(plan_type.lower())
        return RateLimiter(plan_enum)
    except ValueError:
        logger.warning(f"Unknown plan type '{plan_type}', defaulting to free")
        return RateLimiter(PlanType.FREE)
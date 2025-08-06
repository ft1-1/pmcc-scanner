"""
Circuit breaker implementation for notification system reliability.
"""

import time
import logging
from enum import Enum
from typing import Callable, Any, Optional
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker for notification channels to prevent cascade failures.
    
    Implements the circuit breaker pattern to automatically disable
    failing notification channels and periodically test for recovery.
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Circuit breaker name for logging
            failure_threshold: Number of failures to trip circuit
            timeout_seconds: Seconds to wait before trying again
            expected_exception: Exception type that counts as failure
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.expected_exception = expected_exception
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.success_count = 0
        
        logger.info(f"Circuit breaker '{name}' initialized")
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function positional arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        # Check if circuit should transition states
        self._update_state()
        
        if self.state == CircuitState.OPEN:
            raise Exception(f"Circuit breaker '{self.name}' is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _update_state(self):
        """Update circuit breaker state based on current conditions."""
        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if (self.last_failure_time and 
                datetime.now() - self.last_failure_time >= timedelta(seconds=self.timeout_seconds)):
                self._transition_to_half_open()
        
        elif self.state == CircuitState.HALF_OPEN:
            # In half-open, one success closes circuit
            if self.success_count > 0:
                self._transition_to_closed()
    
    def _on_success(self):
        """Handle successful function execution."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.info(f"Circuit breaker '{self.name}': Success in HALF_OPEN state")
        
        # Reset failure count on success
        self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed function execution."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        logger.warning(f"Circuit breaker '{self.name}': Failure {self.failure_count}/{self.failure_threshold}")
        
        if self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
            self._transition_to_open()
        elif self.state == CircuitState.HALF_OPEN:
            self._transition_to_open()
    
    def _transition_to_open(self):
        """Transition circuit to OPEN state."""
        self.state = CircuitState.OPEN
        self.success_count = 0
        logger.warning(f"Circuit breaker '{self.name}' opened due to failures")
    
    def _transition_to_half_open(self):
        """Transition circuit to HALF_OPEN state."""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        logger.info(f"Circuit breaker '{self.name}' half-opened for testing")
    
    def _transition_to_closed(self):
        """Transition circuit to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        logger.info(f"Circuit breaker '{self.name}' closed - service recovered")
    
    def is_available(self) -> bool:
        """
        Check if circuit allows requests.
        
        Returns:
            True if requests are allowed
        """
        self._update_state()
        return self.state != CircuitState.OPEN
    
    def reset(self):
        """Reset circuit breaker to initial state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        logger.info(f"Circuit breaker '{self.name}' reset")
    
    def get_status(self) -> dict:
        """
        Get current circuit breaker status.
        
        Returns:
            Dictionary with status information
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "timeout_seconds": self.timeout_seconds,
            "is_available": self.is_available()
        }
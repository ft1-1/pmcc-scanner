"""
Data Provider Factory for the PMCC Scanner.

This module manages the creation and lifecycle of data providers, including:
- Provider instantiation based on configuration
- Automatic fallback between providers when one fails
- Health monitoring and provider selection logic
- Circuit breaker patterns for unreliable providers
- Load balancing and failover coordination

Key features:
- Dynamic provider switching based on health and performance
- Graceful degradation when primary provider fails
- Provider-specific operation routing (e.g., EODHD for screening, MarketData for options)
- Circuit breaker to prevent cascading failures
- Comprehensive logging and monitoring
"""

import logging
import asyncio
from typing import Dict, List, Optional, Union, Any, Type
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import time

from src.api.data_provider import (
    DataProvider, SyncDataProvider, ProviderType, ProviderStatus, 
    ProviderHealth, ScreeningCriteria
)
from src.models.api_models import (
    StockQuote, OptionChain, OptionContract, EODHDScreenerResponse,
    APIResponse, APIError, APIStatus
)

logger = logging.getLogger(__name__)


class FallbackStrategy(Enum):
    """Provider fallback strategies."""
    NONE = "none"  # No fallback, fail if primary provider fails
    ROUND_ROBIN = "round_robin"  # Cycle through available providers
    HEALTH_BASED = "health_based"  # Use healthiest available provider
    OPERATION_SPECIFIC = "operation_specific"  # Route operations to best provider for that operation


@dataclass
class CircuitBreakerState:
    """Circuit breaker state for a provider."""
    is_open: bool = False
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    half_open_attempts: int = 0
    
    # Circuit breaker thresholds
    failure_threshold: int = 5  # Open circuit after 5 failures
    recovery_timeout: int = 300  # Try to recover after 5 minutes
    half_open_max_attempts: int = 3  # Max attempts in half-open state


@dataclass
class ProviderConfig:
    """Configuration for a single provider."""
    provider_type: ProviderType
    provider_class: Type[Union[DataProvider, SyncDataProvider]]
    config: Dict[str, Any]
    priority: int = 0  # Higher priority = preferred provider
    max_concurrent_requests: int = 10
    timeout_seconds: int = 30
    
    # Operation-specific preferences
    preferred_operations: List[str] = field(default_factory=list)
    supported_operations: List[str] = field(default_factory=lambda: [
        "get_stock_quote", "get_stock_quotes", "get_options_chain", 
        "screen_stocks", "get_greeks"
    ])


class DataProviderFactory:
    """
    Factory for creating and managing data providers with fallback support.
    
    This factory handles:
    - Provider instantiation and configuration
    - Health monitoring and provider selection
    - Automatic fallback and circuit breaker patterns
    - Operation routing to optimal providers
    """
    
    def __init__(self, fallback_strategy: FallbackStrategy = FallbackStrategy.HEALTH_BASED):
        """
        Initialize the provider factory.
        
        Args:
            fallback_strategy: Strategy for provider fallback
        """
        self.fallback_strategy = fallback_strategy
        self.providers: Dict[ProviderType, Union[DataProvider, SyncDataProvider]] = {}
        self.provider_configs: Dict[ProviderType, ProviderConfig] = {}
        self.circuit_breakers: Dict[ProviderType, CircuitBreakerState] = {}
        self.provider_health_cache: Dict[ProviderType, ProviderHealth] = {}
        self.last_health_check: Dict[ProviderType, datetime] = {}
        
        # Factory settings
        self.health_check_interval = 60  # Check health every minute
        self.concurrent_request_semaphores: Dict[ProviderType, asyncio.Semaphore] = {}
        
    def register_provider(self, config: ProviderConfig) -> None:
        """
        Register a provider with the factory.
        
        Args:
            config: Provider configuration
        """
        self.provider_configs[config.provider_type] = config
        self.circuit_breakers[config.provider_type] = CircuitBreakerState()
        self.concurrent_request_semaphores[config.provider_type] = asyncio.Semaphore(
            config.max_concurrent_requests
        )
        
        logger.info(f"Registered provider: {config.provider_type.value}")
    
    async def get_provider(
        self, 
        operation: str,
        preferred_provider: Optional[ProviderType] = None
    ) -> Optional[Union[DataProvider, SyncDataProvider]]:
        """
        Get the best available provider for an operation.
        
        Args:
            operation: The operation to perform
            preferred_provider: Preferred provider type (optional)
            
        Returns:
            Provider instance or None if no suitable provider available
        """
        # Check if preferred provider is available and suitable
        if preferred_provider and await self._is_provider_available(preferred_provider, operation):
            provider = await self._get_or_create_provider(preferred_provider)
            if provider:
                return provider
        
        # Use fallback strategy to select provider
        available_providers = await self._get_available_providers_for_operation(operation)
        
        if not available_providers:
            logger.error(f"No available providers for operation: {operation}")
            return None
        
        if self.fallback_strategy == FallbackStrategy.HEALTH_BASED:
            return await self._select_healthiest_provider(available_providers)
        elif self.fallback_strategy == FallbackStrategy.ROUND_ROBIN:
            return await self._select_round_robin_provider(available_providers)
        elif self.fallback_strategy == FallbackStrategy.OPERATION_SPECIFIC:
            return await self._select_operation_specific_provider(available_providers, operation)
        else:
            # Default to first available
            return available_providers[0] if available_providers else None
    
    async def get_stock_quote(
        self, 
        symbol: str,
        preferred_provider: Optional[ProviderType] = None
    ) -> APIResponse:
        """Get stock quote with automatic provider fallback."""
        return await self._execute_with_fallback(
            "get_stock_quote",
            preferred_provider,
            symbol=symbol
        )
    
    async def get_stock_quotes(
        self, 
        symbols: List[str],
        preferred_provider: Optional[ProviderType] = None
    ) -> APIResponse:
        """Get multiple stock quotes with automatic provider fallback."""
        return await self._execute_with_fallback(
            "get_stock_quotes",
            preferred_provider,
            symbols=symbols
        )
    
    async def get_options_chain(
        self, 
        symbol: str,
        expiration_from: Optional[datetime] = None,
        expiration_to: Optional[datetime] = None,
        preferred_provider: Optional[ProviderType] = None
    ) -> APIResponse:
        """Get options chain with automatic provider fallback."""
        return await self._execute_with_fallback(
            "get_options_chain",
            preferred_provider,
            symbol=symbol,
            expiration_from=expiration_from,
            expiration_to=expiration_to
        )
    
    async def screen_stocks(
        self, 
        criteria: ScreeningCriteria,
        preferred_provider: Optional[ProviderType] = None
    ) -> APIResponse:
        """Screen stocks with automatic provider fallback."""
        return await self._execute_with_fallback(
            "screen_stocks",
            preferred_provider,
            criteria=criteria
        )
    
    async def get_greeks(
        self, 
        option_symbol: str,
        preferred_provider: Optional[ProviderType] = None
    ) -> APIResponse:
        """Get option Greeks with automatic provider fallback."""
        return await self._execute_with_fallback(
            "get_greeks",
            preferred_provider,
            option_symbol=option_symbol
        )
    
    async def health_check_all_providers(self) -> Dict[ProviderType, ProviderHealth]:
        """Perform health checks on all registered providers."""
        health_results = {}
        
        for provider_type in self.provider_configs.keys():
            try:
                provider = await self._get_or_create_provider(provider_type)
                if provider:
                    health = await provider.health_check()
                    health_results[provider_type] = health
                    self.provider_health_cache[provider_type] = health
                    self.last_health_check[provider_type] = datetime.now()
                    
                    # Update circuit breaker based on health
                    await self._update_circuit_breaker(provider_type, health.status == ProviderStatus.HEALTHY)
                    
            except Exception as e:
                logger.error(f"Health check failed for {provider_type.value}: {e}")
                health_results[provider_type] = ProviderHealth(
                    status=ProviderStatus.UNHEALTHY,
                    last_check=datetime.now(),
                    error_message=str(e)
                )
                await self._update_circuit_breaker(provider_type, False)
        
        return health_results
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all providers."""
        status = {
            "fallback_strategy": self.fallback_strategy.value,
            "providers": {}
        }
        
        for provider_type, config in self.provider_configs.items():
            circuit_breaker = self.circuit_breakers[provider_type]
            health = self.provider_health_cache.get(provider_type)
            
            status["providers"][provider_type.value] = {
                "priority": config.priority,
                "supported_operations": config.supported_operations,
                "preferred_operations": config.preferred_operations,
                "circuit_breaker": {
                    "is_open": circuit_breaker.is_open,
                    "failure_count": circuit_breaker.failure_count,
                    "last_failure": circuit_breaker.last_failure_time.isoformat() if circuit_breaker.last_failure_time else None
                },
                "health": {
                    "status": health.status.value if health else "unknown",
                    "last_check": health.last_check.isoformat() if health else None,
                    "latency_ms": health.latency_ms if health else None,
                    "error_message": health.error_message if health else None
                } if health else None
            }
        
        return status
    
    # Private methods
    
    async def _execute_with_fallback(
        self, 
        operation: str, 
        preferred_provider: Optional[ProviderType],
        **kwargs
    ) -> APIResponse:
        """Execute an operation with automatic fallback."""
        attempted_providers = []
        last_error = None
        
        # Get ordered list of providers to try
        providers_to_try = await self._get_provider_execution_order(operation, preferred_provider)
        
        for provider in providers_to_try:
            if provider in attempted_providers:
                continue
                
            attempted_providers.append(provider)
            
            try:
                # Check circuit breaker
                if await self._is_circuit_breaker_open(provider.provider_type):
                    logger.warning(f"Circuit breaker open for {provider.provider_type.value}, skipping")
                    continue
                
                # Execute with concurrency control
                async with self.concurrent_request_semaphores[provider.provider_type]:
                    start_time = time.time()
                    
                    # Execute the operation
                    method = getattr(provider, operation)
                    response = await method(**kwargs)
                    
                    latency_ms = (time.time() - start_time) * 1000
                    
                    # Update health and circuit breaker
                    provider._update_health_from_response(response, latency_ms)
                    await self._update_circuit_breaker(provider.provider_type, response.is_success)
                    
                    if response.is_success:
                        logger.debug(f"Operation {operation} succeeded with {provider.provider_type.value}")
                        return response
                    else:
                        last_error = response.error
                        logger.warning(f"Operation {operation} failed with {provider.provider_type.value}: {response.error}")
                        
            except Exception as e:
                last_error = str(e)
                logger.error(f"Exception executing {operation} with {provider.provider_type.value}: {e}")
                await self._update_circuit_breaker(provider.provider_type, False)
        
        # All providers failed
        logger.error(f"All providers failed for operation {operation}")
        return APIResponse(
            status=APIStatus.ERROR,
            error=APIError(
                code=503,
                message=f"All providers failed for {operation}",
                details=str(last_error) if last_error else None
            )
        )
    
    async def _get_provider_execution_order(
        self, 
        operation: str,
        preferred_provider: Optional[ProviderType]
    ) -> List[Union[DataProvider, SyncDataProvider]]:
        """Get ordered list of providers to try for an operation."""
        available_providers = await self._get_available_providers_for_operation(operation)
        
        if preferred_provider:
            # Put preferred provider first if available
            preferred = next((p for p in available_providers if p.provider_type == preferred_provider), None)
            if preferred:
                providers = [preferred] + [p for p in available_providers if p != preferred]
                return providers
        
        # Use fallback strategy ordering
        if self.fallback_strategy == FallbackStrategy.HEALTH_BASED:
            return await self._order_by_health(available_providers)
        elif self.fallback_strategy == FallbackStrategy.OPERATION_SPECIFIC:
            return await self._order_by_operation_preference(available_providers, operation)
        else:
            return available_providers
    
    async def _get_available_providers_for_operation(
        self, 
        operation: str
    ) -> List[Union[DataProvider, SyncDataProvider]]:
        """Get list of providers that support the given operation."""
        available = []
        
        for provider_type, config in self.provider_configs.items():
            if operation in config.supported_operations:
                if not await self._is_circuit_breaker_open(provider_type):
                    provider = await self._get_or_create_provider(provider_type)
                    if provider:
                        available.append(provider)
        
        return available
    
    async def _get_or_create_provider(
        self, 
        provider_type: ProviderType
    ) -> Optional[Union[DataProvider, SyncDataProvider]]:
        """Get existing provider or create new one."""
        if provider_type not in self.providers:
            config = self.provider_configs.get(provider_type)
            if not config:
                logger.error(f"No configuration found for provider: {provider_type.value}")
                return None
                
            try:
                provider = config.provider_class(provider_type, config.config)
                self.providers[provider_type] = provider
                logger.info(f"Created provider instance: {provider_type.value}")
            except Exception as e:
                logger.error(f"Failed to create provider {provider_type.value}: {e}")
                return None
        
        return self.providers.get(provider_type)
    
    async def _is_provider_available(self, provider_type: ProviderType, operation: str) -> bool:
        """Check if a provider is available for an operation."""
        config = self.provider_configs.get(provider_type)
        if not config or operation not in config.supported_operations:
            return False
        
        return not await self._is_circuit_breaker_open(provider_type)
    
    async def _is_circuit_breaker_open(self, provider_type: ProviderType) -> bool:
        """Check if circuit breaker is open for a provider."""
        circuit_breaker = self.circuit_breakers.get(provider_type)
        if not circuit_breaker:
            return False
        
        if not circuit_breaker.is_open:
            return False
        
        # Check if we should try half-open state
        if circuit_breaker.last_failure_time:
            time_since_failure = datetime.now() - circuit_breaker.last_failure_time
            if time_since_failure.total_seconds() >= circuit_breaker.recovery_timeout:
                # Try half-open state
                circuit_breaker.is_open = False
                circuit_breaker.half_open_attempts = 0
                logger.info(f"Circuit breaker entering half-open state for {provider_type.value}")
                return False
        
        return True
    
    async def _update_circuit_breaker(self, provider_type: ProviderType, success: bool) -> None:
        """Update circuit breaker state based on operation result."""
        circuit_breaker = self.circuit_breakers.get(provider_type)
        if not circuit_breaker:
            return
        
        if success:
            # Reset failure count on success
            circuit_breaker.failure_count = 0
            circuit_breaker.half_open_attempts = 0
            if circuit_breaker.is_open:
                circuit_breaker.is_open = False
                logger.info(f"Circuit breaker closed for {provider_type.value}")
        else:
            # Increment failure count
            circuit_breaker.failure_count += 1
            circuit_breaker.last_failure_time = datetime.now()
            
            # Open circuit breaker if threshold exceeded
            if circuit_breaker.failure_count >= circuit_breaker.failure_threshold:
                circuit_breaker.is_open = True
                logger.warning(f"Circuit breaker opened for {provider_type.value} after {circuit_breaker.failure_count} failures")
    
    async def _select_healthiest_provider(
        self, 
        providers: List[Union[DataProvider, SyncDataProvider]]
    ) -> Optional[Union[DataProvider, SyncDataProvider]]:
        """Select provider with best health score."""
        if not providers:
            return None
        
        # Score providers based on health
        scored_providers = []
        for provider in providers:
            health = provider.health
            score = 0
            
            if health.status == ProviderStatus.HEALTHY:
                score += 100
            elif health.status == ProviderStatus.DEGRADED:
                score += 50
            else:
                score += 0
            
            # Factor in latency (lower is better)
            if health.latency_ms:
                score -= min(health.latency_ms / 10, 50)  # Cap latency penalty
            
            # Factor in success rate
            if health.success_rate:
                score += health.success_rate * 50
            
            scored_providers.append((provider, score))
        
        # Return provider with highest score
        scored_providers.sort(key=lambda x: x[1], reverse=True)
        return scored_providers[0][0]
    
    async def _select_round_robin_provider(
        self, 
        providers: List[Union[DataProvider, SyncDataProvider]]
    ) -> Optional[Union[DataProvider, SyncDataProvider]]:
        """Select provider using round-robin strategy."""
        if not providers:
            return None
        
        # Simple round-robin based on current time
        index = int(time.time()) % len(providers)
        return providers[index]
    
    async def _select_operation_specific_provider(
        self, 
        providers: List[Union[DataProvider, SyncDataProvider]],
        operation: str
    ) -> Optional[Union[DataProvider, SyncDataProvider]]:
        """Select provider optimized for specific operation."""
        if not providers:
            return None
        
        # Find providers that prefer this operation
        preferred_providers = []
        for provider in providers:
            config = self.provider_configs.get(provider.provider_type)
            if config and operation in config.preferred_operations:
                preferred_providers.append(provider)
        
        if preferred_providers:
            # Use healthiest among preferred providers
            return await self._select_healthiest_provider(preferred_providers)
        else:
            # Fall back to healthiest available
            return await self._select_healthiest_provider(providers)
    
    async def _order_by_health(
        self, 
        providers: List[Union[DataProvider, SyncDataProvider]]
    ) -> List[Union[DataProvider, SyncDataProvider]]:
        """Order providers by health score."""
        scored_providers = []
        
        for provider in providers:
            health = provider.health
            score = 0
            
            if health.status == ProviderStatus.HEALTHY:
                score = 100
            elif health.status == ProviderStatus.DEGRADED:
                score = 50
            else:
                score = 0
            
            # Factor in latency and success rate
            if health.latency_ms:
                score -= min(health.latency_ms / 10, 50)
            if health.success_rate:
                score += health.success_rate * 50
            
            scored_providers.append((provider, score))
        
        # Sort by score (highest first)
        scored_providers.sort(key=lambda x: x[1], reverse=True)
        return [provider for provider, score in scored_providers]
    
    async def _order_by_operation_preference(
        self, 
        providers: List[Union[DataProvider, SyncDataProvider]],
        operation: str
    ) -> List[Union[DataProvider, SyncDataProvider]]:
        """Order providers by operation preference."""
        preferred = []
        others = []
        
        for provider in providers:
            config = self.provider_configs.get(provider.provider_type)
            if config and operation in config.preferred_operations:
                preferred.append(provider)
            else:
                others.append(provider)
        
        # Order preferred by health, then others by health
        preferred_ordered = await self._order_by_health(preferred)
        others_ordered = await self._order_by_health(others)
        
        return preferred_ordered + others_ordered


# Synchronous version for legacy compatibility
class SyncDataProviderFactory:
    """Synchronous version of DataProviderFactory."""
    
    def __init__(self, fallback_strategy: FallbackStrategy = FallbackStrategy.HEALTH_BASED):
        """Initialize synchronous provider factory."""
        self.fallback_strategy = fallback_strategy
        self.providers: Dict[ProviderType, SyncDataProvider] = {}
        self.provider_configs: Dict[ProviderType, ProviderConfig] = {}
        self.circuit_breakers: Dict[ProviderType, CircuitBreakerState] = {}
    
    def register_provider(self, config: ProviderConfig) -> None:
        """Register a synchronous provider."""
        self.provider_configs[config.provider_type] = config
        self.circuit_breakers[config.provider_type] = CircuitBreakerState()
        logger.info(f"Registered sync provider: {config.provider_type.value}")
    
    def get_provider(
        self, 
        operation: str,
        preferred_provider: Optional[ProviderType] = None
    ) -> Optional[SyncDataProvider]:
        """Get the best available provider for an operation (synchronous)."""
        # Check if preferred provider is available and suitable
        if preferred_provider:
            config = self.provider_configs.get(preferred_provider)
            if config and operation in config.supported_operations:
                if not self._is_circuit_breaker_open(preferred_provider):
                    provider = self._get_or_create_provider(preferred_provider)
                    if provider:
                        logger.info(f"Using preferred provider {preferred_provider.value} for {operation}")
                        return provider
                    else:
                        logger.warning(f"Failed to create preferred provider {preferred_provider.value}")
            else:
                logger.warning(f"Preferred provider {preferred_provider.value} does not support {operation}")
        
        # Fallback to first available provider
        for provider_type, config in self.provider_configs.items():
            if operation in config.supported_operations:
                if not self._is_circuit_breaker_open(provider_type):
                    logger.info(f"Using fallback provider {provider_type.value} for {operation}")
                    return self._get_or_create_provider(provider_type)
        
        return None
    
    def _get_or_create_provider(self, provider_type: ProviderType) -> Optional[SyncDataProvider]:
        """Get or create synchronous provider."""
        if provider_type not in self.providers:
            config = self.provider_configs.get(provider_type)
            if not config:
                return None
            
            try:
                provider = config.provider_class(provider_type, config.config)
                self.providers[provider_type] = provider
            except Exception as e:
                logger.error(f"Failed to create sync provider {provider_type.value}: {e}")
                return None
        
        return self.providers.get(provider_type)
    
    def _is_circuit_breaker_open(self, provider_type: ProviderType) -> bool:
        """Check if circuit breaker is open (simplified synchronous version)."""
        circuit_breaker = self.circuit_breakers.get(provider_type)
        return circuit_breaker.is_open if circuit_breaker else False
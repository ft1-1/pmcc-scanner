"""
Global error handling and monitoring utilities for PMCC Scanner.

Provides centralized error handling, performance monitoring,
and health status reporting across the application.
"""

import os
import sys
import time
import threading
import traceback
import functools
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging

try:
    import psutil
except ImportError:
    psutil = None


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class HealthStatus(str, Enum):
    """System health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class ErrorReport:
    """Error report structure."""
    timestamp: datetime
    error_type: str
    error_message: str
    severity: ErrorSeverity
    component: str
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'error_type': self.error_type,
            'error_message': self.error_message,
            'severity': self.severity.value,
            'component': self.component,
            'stack_trace': self.stack_trace,
            'context': self.context,
            'resolved': self.resolved,
            'resolution_time': self.resolution_time.isoformat() if self.resolution_time else None
        }


@dataclass
class PerformanceMetric:
    """Performance metric data."""
    timestamp: datetime
    component: str
    operation: str
    duration_seconds: float
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'component': self.component,
            'operation': self.operation,
            'duration_seconds': self.duration_seconds,
            'memory_usage_mb': self.memory_usage_mb,
            'cpu_usage_percent': self.cpu_usage_percent,
            'success': self.success,
            'error_message': self.error_message,
            'metadata': self.metadata
        }


@dataclass
class HealthMetrics:
    """System health metrics."""
    timestamp: datetime
    overall_status: HealthStatus
    uptime_seconds: float
    cpu_usage_percent: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    memory_usage_percent: Optional[float] = None
    disk_usage_percent: Optional[float] = None
    api_response_time_ms: Optional[float] = None
    error_rate_percent: Optional[float] = None
    last_successful_scan: Optional[datetime] = None
    active_errors: int = 0
    performance_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'overall_status': self.overall_status.value,
            'uptime_seconds': self.uptime_seconds,
            'cpu_usage_percent': self.cpu_usage_percent,
            'memory_usage_mb': self.memory_usage_mb,
            'memory_usage_percent': self.memory_usage_percent,
            'disk_usage_percent': self.disk_usage_percent,
            'api_response_time_ms': self.api_response_time_ms,
            'error_rate_percent': self.error_rate_percent,
            'last_successful_scan': self.last_successful_scan.isoformat() if self.last_successful_scan else None,
            'active_errors': self.active_errors,
            'performance_score': self.performance_score
        }


class GlobalErrorHandler:
    """Global error handler with monitoring and reporting."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize global error handler."""
        self.logger = logger or logging.getLogger(__name__)
        self.start_time = datetime.now()
        
        # Error tracking
        self.error_reports: List[ErrorReport] = []
        self.performance_metrics: List[PerformanceMetric] = []
        self.health_history: List[HealthMetrics] = []
        
        # Statistics
        self.error_counts = {
            'total': 0,
            'by_severity': {severity.value: 0 for severity in ErrorSeverity},
            'by_component': {},
            'by_hour': {}
        }
        
        # Performance tracking
        self.operation_stats = {}
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Install global exception handler
        self._install_global_handler()
        
        self.logger.info("Global error handler initialized")
    
    def report_error(self, 
                    error: Exception, 
                    component: str,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    context: Optional[Dict[str, Any]] = None) -> ErrorReport:
        """
        Report an error to the global handler.
        
        Args:
            error: The exception that occurred
            component: Component where error occurred
            severity: Error severity level
            context: Additional context information
            
        Returns:
            ErrorReport instance
        """
        with self._lock:
            error_report = ErrorReport(
                timestamp=datetime.now(),
                error_type=type(error).__name__,
                error_message=str(error),
                severity=severity,
                component=component,
                stack_trace=traceback.format_exc(),
                context=context or {}
            )
            
            # Store error report
            self.error_reports.append(error_report)
            
            # Update statistics
            self._update_error_stats(error_report)
            
            # Log the error
            log_level = self._get_log_level_for_severity(severity)
            self.logger.log(
                log_level,
                f"Error in {component}: {error_report.error_message}",
                extra={
                    'component': component,
                    'error_type': error_report.error_type,
                    'severity': severity.value,
                    'context': context
                },
                exc_info=error
            )
            
            return error_report
    
    def record_performance(self,
                          component: str,
                          operation: str,
                          duration_seconds: float,
                          success: bool = True,
                          error_message: Optional[str] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> PerformanceMetric:
        """
        Record a performance metric.
        
        Args:
            component: Component name
            operation: Operation name
            duration_seconds: Operation duration
            success: Whether operation succeeded
            error_message: Error message if failed
            metadata: Additional metadata
            
        Returns:
            PerformanceMetric instance
        """
        with self._lock:
            # Get system metrics if available
            memory_usage_mb = None
            cpu_usage_percent = None
            
            if psutil:
                try:
                    process = psutil.Process()
                    memory_usage_mb = process.memory_info().rss / 1024 / 1024
                    cpu_usage_percent = process.cpu_percent()
                except Exception:
                    pass
            
            metric = PerformanceMetric(
                timestamp=datetime.now(),
                component=component,
                operation=operation,
                duration_seconds=duration_seconds,
                memory_usage_mb=memory_usage_mb,
                cpu_usage_percent=cpu_usage_percent,
                success=success,
                error_message=error_message,
                metadata=metadata or {}
            )
            
            # Store metric
            self.performance_metrics.append(metric)
            
            # Update operation statistics
            self._update_operation_stats(metric)
            
            # Log performance data
            self.logger.debug(
                f"Performance: {component}.{operation} took {duration_seconds:.3f}s",
                extra={
                    'component': component,
                    'operation': operation,
                    'duration_seconds': duration_seconds,
                    'success': success,
                    'memory_usage_mb': memory_usage_mb,
                    'cpu_usage_percent': cpu_usage_percent
                }
            )
            
            return metric
    
    def get_health_status(self) -> HealthMetrics:
        """
        Get current system health status.
        
        Returns:
            HealthMetrics instance
        """
        with self._lock:
            now = datetime.now()
            uptime_seconds = (now - self.start_time).total_seconds()
            
            # Calculate error rate
            recent_errors = [
                error for error in self.error_reports
                if error.timestamp > now - timedelta(hours=1)
            ]
            
            recent_operations = [
                metric for metric in self.performance_metrics
                if metric.timestamp > now - timedelta(hours=1)
            ]
            
            error_rate = 0.0
            if recent_operations:
                failed_operations = len([op for op in recent_operations if not op.success])
                error_rate = (failed_operations / len(recent_operations)) * 100
            
            # Get system metrics
            cpu_usage = None
            memory_usage_mb = None
            memory_usage_percent = None
            disk_usage_percent = None
            
            if psutil:
                try:
                    cpu_usage = psutil.cpu_percent(interval=1)
                    memory = psutil.virtual_memory()
                    memory_usage_mb = memory.used / 1024 / 1024
                    memory_usage_percent = memory.percent
                    disk_usage = psutil.disk_usage('/')
                    disk_usage_percent = disk_usage.percent
                except Exception:
                    pass
            
            # Calculate API response time
            api_response_time = None
            api_metrics = [
                metric for metric in recent_operations
                if 'api' in metric.operation.lower() and metric.success
            ]
            if api_metrics:
                api_response_time = sum(m.duration_seconds for m in api_metrics) / len(api_metrics) * 1000
            
            # Find last successful scan
            last_successful_scan = None
            scan_metrics = [
                metric for metric in self.performance_metrics
                if 'scan' in metric.operation.lower() and metric.success
            ]
            if scan_metrics:
                last_successful_scan = max(scan_metrics, key=lambda m: m.timestamp).timestamp
            
            # Calculate performance score (0-100)
            performance_score = self._calculate_performance_score(
                error_rate, cpu_usage, memory_usage_percent, api_response_time
            )
            
            # Determine overall status
            overall_status = self._determine_health_status(
                error_rate, performance_score, len(recent_errors)
            )
            
            health_metrics = HealthMetrics(
                timestamp=now,
                overall_status=overall_status,
                uptime_seconds=uptime_seconds,
                cpu_usage_percent=cpu_usage,
                memory_usage_mb=memory_usage_mb,
                memory_usage_percent=memory_usage_percent,
                disk_usage_percent=disk_usage_percent,
                api_response_time_ms=api_response_time,
                error_rate_percent=error_rate,
                last_successful_scan=last_successful_scan,
                active_errors=len(recent_errors),
                performance_score=performance_score
            )
            
            # Store in history
            self.health_history.append(health_metrics)
            
            return health_metrics
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get error summary for the specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Error summary dictionary
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_errors = [
            error for error in self.error_reports
            if error.timestamp > cutoff_time
        ]
        
        # Group by severity
        by_severity = {severity.value: 0 for severity in ErrorSeverity}
        for error in recent_errors:
            by_severity[error.severity.value] += 1
        
        # Group by component
        by_component = {}
        for error in recent_errors:
            component = error.component
            if component not in by_component:
                by_component[component] = 0
            by_component[component] += 1
        
        # Group by error type
        by_type = {}
        for error in recent_errors:
            error_type = error.error_type
            if error_type not in by_type:
                by_type[error_type] = 0
            by_type[error_type] += 1
        
        return {
            'total_errors': len(recent_errors),
            'by_severity': by_severity,
            'by_component': by_component,
            'by_type': by_type,
            'recent_errors': [error.to_dict() for error in recent_errors[-10:]]  # Last 10
        }
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get performance summary for the specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Performance summary dictionary
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_metrics = [
            metric for metric in self.performance_metrics
            if metric.timestamp > cutoff_time
        ]
        
        if not recent_metrics:
            return {
                'total_operations': 0,
                'avg_duration_seconds': 0,
                'success_rate': 0,
                'by_component': {},
                'slowest_operations': []
            }
        
        # Calculate averages
        total_duration = sum(m.duration_seconds for m in recent_metrics)
        avg_duration = total_duration / len(recent_metrics)
        
        successful_ops = len([m for m in recent_metrics if m.success])
        success_rate = (successful_ops / len(recent_metrics)) * 100
        
        # Group by component
        by_component = {}
        for metric in recent_metrics:
            component = metric.component
            if component not in by_component:
                by_component[component] = {
                    'count': 0,
                    'avg_duration': 0,
                    'success_rate': 0
                }
            
            by_component[component]['count'] += 1
        
        # Calculate component averages
        for component, stats in by_component.items():
            component_metrics = [m for m in recent_metrics if m.component == component]
            stats['avg_duration'] = sum(m.duration_seconds for m in component_metrics) / len(component_metrics)
            successful = len([m for m in component_metrics if m.success])
            stats['success_rate'] = (successful / len(component_metrics)) * 100
        
        # Find slowest operations
        slowest = sorted(recent_metrics, key=lambda m: m.duration_seconds, reverse=True)[:5]
        
        return {
            'total_operations': len(recent_metrics),
            'avg_duration_seconds': avg_duration,
            'success_rate': success_rate,
            'by_component': by_component,
            'slowest_operations': [
                {
                    'component': m.component,
                    'operation': m.operation,
                    'duration_seconds': m.duration_seconds,
                    'timestamp': m.timestamp.isoformat()
                }
                for m in slowest
            ]
        }
    
    def cleanup_old_data(self, days: int = 7):
        """
        Clean up old error reports and metrics.
        
        Args:
            days: Number of days to keep data
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        
        with self._lock:
            # Clean error reports
            original_error_count = len(self.error_reports)
            self.error_reports = [
                error for error in self.error_reports
                if error.timestamp > cutoff_time
            ]
            
            # Clean performance metrics
            original_metric_count = len(self.performance_metrics)
            self.performance_metrics = [
                metric for metric in self.performance_metrics
                if metric.timestamp > cutoff_time
            ]
            
            # Clean health history
            original_health_count = len(self.health_history)
            self.health_history = [
                health for health in self.health_history
                if health.timestamp > cutoff_time
            ]
            
            removed_errors = original_error_count - len(self.error_reports)
            removed_metrics = original_metric_count - len(self.performance_metrics)
            removed_health = original_health_count - len(self.health_history)
            
            if removed_errors > 0 or removed_metrics > 0 or removed_health > 0:
                self.logger.info(
                    f"Cleaned up old data: {removed_errors} errors, "
                    f"{removed_metrics} metrics, {removed_health} health records"
                )
    
    def _install_global_handler(self):
        """Install global exception handler."""
        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                # Allow keyboard interrupt to propagate normally
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            # Report unhandled exception
            self.report_error(
                exc_value,
                component="global",
                severity=ErrorSeverity.CRITICAL,
                context={
                    'exc_type': exc_type.__name__,
                    'traceback': ''.join(traceback.format_tb(exc_traceback))
                }
            )
            
            # Call the default handler
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
        
        sys.excepthook = handle_exception
    
    def _update_error_stats(self, error_report: ErrorReport):
        """Update error statistics."""
        self.error_counts['total'] += 1
        self.error_counts['by_severity'][error_report.severity.value] += 1
        
        component = error_report.component
        if component not in self.error_counts['by_component']:
            self.error_counts['by_component'][component] = 0
        self.error_counts['by_component'][component] += 1
        
        hour_key = error_report.timestamp.strftime('%Y%m%d_%H')
        if hour_key not in self.error_counts['by_hour']:
            self.error_counts['by_hour'][hour_key] = 0
        self.error_counts['by_hour'][hour_key] += 1
    
    def _update_operation_stats(self, metric: PerformanceMetric):
        """Update operation statistics."""
        key = f"{metric.component}.{metric.operation}"
        
        if key not in self.operation_stats:
            self.operation_stats[key] = {
                'count': 0,
                'total_duration': 0,
                'success_count': 0,
                'min_duration': float('inf'),
                'max_duration': 0
            }
        
        stats = self.operation_stats[key]
        stats['count'] += 1
        stats['total_duration'] += metric.duration_seconds
        
        if metric.success:
            stats['success_count'] += 1
        
        stats['min_duration'] = min(stats['min_duration'], metric.duration_seconds)
        stats['max_duration'] = max(stats['max_duration'], metric.duration_seconds)
    
    def _get_log_level_for_severity(self, severity: ErrorSeverity) -> int:
        """Get logging level for error severity."""
        mapping = {
            ErrorSeverity.LOW: logging.WARNING,
            ErrorSeverity.MEDIUM: logging.ERROR,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }
        return mapping.get(severity, logging.ERROR)
    
    def _calculate_performance_score(self, 
                                   error_rate: float,
                                   cpu_usage: Optional[float],
                                   memory_usage: Optional[float],
                                   api_response_time: Optional[float]) -> float:
        """Calculate overall performance score (0-100)."""
        score = 100.0
        
        # Deduct for error rate
        score -= error_rate * 2  # 2 points per % error rate
        
        # Deduct for high CPU usage
        if cpu_usage is not None:
            if cpu_usage > 80:
                score -= (cpu_usage - 80) * 2
        
        # Deduct for high memory usage
        if memory_usage is not None:
            if memory_usage > 80:
                score -= (memory_usage - 80) * 1.5
        
        # Deduct for slow API responses
        if api_response_time is not None:
            if api_response_time > 1000:  # > 1 second
                score -= (api_response_time - 1000) / 100
        
        return max(0.0, min(100.0, score))
    
    def _determine_health_status(self,
                               error_rate: float,
                               performance_score: float,
                               active_errors: int) -> HealthStatus:
        """Determine overall health status."""
        if active_errors > 10 or error_rate > 50 or performance_score < 30:
            return HealthStatus.CRITICAL
        elif active_errors > 5 or error_rate > 20 or performance_score < 60:
            return HealthStatus.UNHEALTHY
        elif active_errors > 2 or error_rate > 10 or performance_score < 80:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY


# Global error handler instance
_global_error_handler: Optional[GlobalErrorHandler] = None


def initialize_error_handler(logger: Optional[logging.Logger] = None) -> GlobalErrorHandler:
    """
    Initialize the global error handler.
    
    Args:
        logger: Logger instance to use
        
    Returns:
        GlobalErrorHandler instance
    """
    global _global_error_handler
    
    if _global_error_handler is None:
        _global_error_handler = GlobalErrorHandler(logger)
    
    return _global_error_handler


def get_error_handler() -> GlobalErrorHandler:
    """
    Get the global error handler instance.
    
    Returns:
        GlobalErrorHandler instance
    """
    if _global_error_handler is None:
        return initialize_error_handler()
    
    return _global_error_handler


def report_error(error: Exception, 
                component: str,
                severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                context: Optional[Dict[str, Any]] = None) -> ErrorReport:
    """
    Report an error to the global handler.
    
    Args:
        error: The exception that occurred
        component: Component where error occurred
        severity: Error severity level
        context: Additional context information
        
    Returns:
        ErrorReport instance
    """
    return get_error_handler().report_error(error, component, severity, context)


def record_performance(component: str,
                      operation: str,
                      duration_seconds: float,
                      success: bool = True,
                      error_message: Optional[str] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> PerformanceMetric:
    """
    Record a performance metric.
    
    Args:
        component: Component name
        operation: Operation name
        duration_seconds: Operation duration
        success: Whether operation succeeded
        error_message: Error message if failed
        metadata: Additional metadata
        
    Returns:
        PerformanceMetric instance
    """
    return get_error_handler().record_performance(
        component, operation, duration_seconds, success, error_message, metadata
    )


def get_health_status() -> HealthMetrics:
    """
    Get current system health status.
    
    Returns:
        HealthMetrics instance
    """
    return get_error_handler().get_health_status()


# Decorator for automatic error reporting
def handle_errors(component: str, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 reraise: bool = True):
    """
    Decorator for automatic error handling and reporting.
    
    Args:
        component: Component name
        severity: Error severity level
        reraise: Whether to reraise the exception
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                report_error(e, component, severity, {
                    'function': func.__name__,
                    'args': str(args) if args else None,
                    'kwargs': str(kwargs) if kwargs else None
                })
                
                if reraise:
                    raise
                
                return None
        
        return wrapper
    return decorator


# Decorator for automatic performance monitoring
def monitor_performance(component: str, operation: str = None):
    """
    Decorator for automatic performance monitoring.
    
    Args:
        component: Component name
        operation: Operation name (defaults to function name)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation or func.__name__
            start_time = time.perf_counter()
            success = True
            error_message = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            finally:
                duration = time.perf_counter() - start_time
                record_performance(
                    component=component,
                    operation=op_name,
                    duration_seconds=duration,
                    success=success,
                    error_message=error_message
                )
        
        return wrapper
    return decorator


if __name__ == "__main__":
    """Test the error handler."""
    import logging
    
    # Setup basic logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Initialize error handler
    error_handler = initialize_error_handler(logger)
    
    # Test error reporting
    try:
        raise ValueError("Test error")
    except ValueError as e:
        report_error(e, "test_component", ErrorSeverity.HIGH, {"test": True})
    
    # Test performance monitoring
    @monitor_performance("test_component", "test_operation")
    def test_function():
        time.sleep(0.1)
        return "success"
    
    result = test_function()
    
    # Get health status
    health = get_health_status()
    print(f"Health Status: {health.overall_status}")
    print(f"Performance Score: {health.performance_score}")
    
    # Get summaries
    error_summary = error_handler.get_error_summary()
    performance_summary = error_handler.get_performance_summary()
    
    print(f"Total Errors: {error_summary['total_errors']}")
    print(f"Total Operations: {performance_summary['total_operations']}")
    print(f"Success Rate: {performance_summary['success_rate']:.1f}%")
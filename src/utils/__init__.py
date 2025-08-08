"""
Utility modules for PMCC Scanner.
"""

from .logger import (
    setup_logging,
    get_logger,
    get_performance_logger,
    configure_third_party_loggers,
    set_log_level,
    get_log_stats,
    log_performance,
    log_exceptions,
    PerformanceLogger,
    LoggerSetup
)

from .error_handler import (
    initialize_error_handler,
    get_error_handler,
    report_error,
    record_performance,
    get_health_status,
    handle_errors,
    monitor_performance,
    GlobalErrorHandler,
    ErrorSeverity,
    HealthStatus,
    ErrorReport,
    PerformanceMetric,
    HealthMetrics
)

from .scheduler import (
    JobScheduler,
    JobConfig,
    JobStatus,
    JobPriority,
    JobExecution,
    create_daily_scan_scheduler
)

__all__ = [
    # Logger exports
    'setup_logging',
    'get_logger',
    'get_performance_logger',
    'configure_third_party_loggers',
    'set_log_level',
    'get_log_stats',
    'log_performance',
    'log_exceptions',
    'PerformanceLogger',
    'LoggerSetup',
    
    # Error handler exports
    'initialize_error_handler',
    'get_error_handler',
    'report_error',
    'record_performance',
    'get_health_status',
    'handle_errors',
    'monitor_performance',
    'GlobalErrorHandler',
    'ErrorSeverity',
    'HealthStatus',
    'ErrorReport',
    'PerformanceMetric',
    'HealthMetrics',
    
    # Scheduler exports
    'JobScheduler',
    'JobConfig',
    'JobStatus',
    'JobPriority',
    'JobExecution',
    'create_daily_scan_scheduler'
]
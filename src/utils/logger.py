"""
Comprehensive logging system for PMCC Scanner.

Provides structured logging with rotation, monitoring integration,
and production-ready configuration management.
"""

import os
import sys
import logging
import logging.handlers
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, Union
from datetime import datetime
from contextlib import contextmanager

try:
    import structlog
    from pythonjsonlogger import jsonlogger
except ImportError as e:
    print(f"Missing required logging dependencies: {e}")
    print("Please install: pip install structlog python-json-logger")
    sys.exit(1)


class PerformanceLogger:
    """Logger for tracking performance metrics."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    @contextmanager
    def timer(self, operation: str, **kwargs):
        """Context manager for timing operations."""
        start_time = time.perf_counter()
        start_memory = self._get_memory_usage()
        
        try:
            yield
        finally:
            end_time = time.perf_counter()
            end_memory = self._get_memory_usage()
            
            duration = end_time - start_time
            memory_delta = end_memory - start_memory if end_memory and start_memory else None
            
            self.logger.info(
                "Performance metric",
                extra={
                    "operation": operation,
                    "duration_seconds": round(duration, 4),
                    "memory_delta_mb": round(memory_delta / 1024 / 1024, 2) if memory_delta else None,
                    "timestamp": datetime.utcnow().isoformat(),
                    **kwargs
                }
            )
    
    def log_api_call(self, endpoint: str, duration: float, status_code: Optional[int] = None, **kwargs):
        """Log API call performance."""
        self.logger.info(
            "API call performance",
            extra={
                "endpoint": endpoint,
                "duration_seconds": round(duration, 4),
                "status_code": status_code,
                "timestamp": datetime.utcnow().isoformat(),
                **kwargs
            }
        )
    
    def log_scan_metrics(self, scan_id: str, metrics: Dict[str, Any]):
        """Log scan performance metrics."""
        self.logger.info(
            "Scan performance metrics",
            extra={
                "scan_id": scan_id,
                "timestamp": datetime.utcnow().isoformat(),
                **metrics
            }
        )
    
    def _get_memory_usage(self) -> Optional[int]:
        """Get current memory usage in bytes."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss
        except ImportError:
            return None
        except Exception:
            return None


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured data."""
        # Base log data
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add thread/process info if available
        if hasattr(record, 'thread') and record.thread:
            log_data["thread_id"] = record.thread
        
        if hasattr(record, 'process') and record.process:
            log_data["process_id"] = record.process
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if enabled
        if self.include_extra:
            # Get all extra attributes (not standard logging attributes)
            standard_attrs = {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
                'module', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                'thread', 'threadName', 'processName', 'process', 'getMessage',
                'exc_info', 'exc_text', 'stack_info', 'message'
            }
            
            extra_data = {
                key: value for key, value in record.__dict__.items()
                if key not in standard_attrs and not key.startswith('_')
            }
            
            if extra_data:
                log_data["extra"] = extra_data
        
        return json.dumps(log_data, default=str, separators=(',', ':'))


class MultiLineFormatter(logging.Formatter):
    """Formatter for human-readable multi-line logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format record with enhanced readability."""
        formatted = super().format(record)
        
        # Add extra information if available
        extra_info = []
        
        # Add performance data if present
        if hasattr(record, 'duration_seconds'):
            extra_info.append(f"Duration: {record.duration_seconds}s")
        
        if hasattr(record, 'operation'):
            extra_info.append(f"Operation: {record.operation}")
        
        if hasattr(record, 'scan_id'):
            extra_info.append(f"Scan ID: {record.scan_id}")
        
        if hasattr(record, 'symbol'):
            extra_info.append(f"Symbol: {record.symbol}")
        
        if extra_info:
            formatted += f" | {' | '.join(extra_info)}"
        
        return formatted


class LoggerSetup:
    """Main logger setup and configuration."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize logger setup.
        
        Args:
            config: Configuration dictionary (optional, will use environment if None)
        """
        self.config = config or self._load_config_from_env()
        self.performance_loggers: Dict[str, PerformanceLogger] = {}
        self._setup_complete = False
    
    def setup_logging(self) -> logging.Logger:
        """
        Setup comprehensive logging system.
        
        Returns:
            Main application logger
        """
        if self._setup_complete:
            return logging.getLogger("pmcc_scanner")
        
        # Clear any existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        # Set root logger level
        root_logger.setLevel(getattr(logging, self.config['level']))
        
        # Create main logger
        main_logger = logging.getLogger("pmcc_scanner")
        main_logger.setLevel(getattr(logging, self.config['level']))
        
        # Setup file logging
        if self.config.get('enable_file_logging', True):
            self._setup_file_logging(main_logger)
        
        # Setup console logging
        if self.config.get('enable_console_logging', True):
            self._setup_console_logging(main_logger)
        
        # Setup syslog if enabled
        if self.config.get('syslog_enabled', False):
            self._setup_syslog_logging(main_logger)
        
        # Setup structured logging
        if self.config.get('enable_json_logging', False):
            self._setup_structured_logging()
        
        # Create performance logger
        self.performance_loggers['main'] = PerformanceLogger(main_logger)
        
        self._setup_complete = True
        
        # Log initialization
        main_logger.info(
            "Logging system initialized",
            extra={
                "config": {k: v for k, v in self.config.items() if 'password' not in k.lower()}
            }
        )
        
        return main_logger
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger for a specific component.
        
        Args:
            name: Logger name
            
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(f"pmcc_scanner.{name}")
        
        # Create performance logger for this component
        if name not in self.performance_loggers:
            self.performance_loggers[name] = PerformanceLogger(logger)
        
        return logger
    
    def get_performance_logger(self, name: str = 'main') -> PerformanceLogger:
        """
        Get performance logger for a component.
        
        Args:
            name: Component name
            
        Returns:
            PerformanceLogger instance
        """
        if name not in self.performance_loggers:
            logger = self.get_logger(name)
            self.performance_loggers[name] = PerformanceLogger(logger)
        
        return self.performance_loggers[name]
    
    def _setup_file_logging(self, logger: logging.Logger):
        """Setup rotating file logging."""
        log_file = self.config.get('log_file', 'logs/pmcc_scanner.log')
        max_bytes = self.config.get('max_bytes', 10 * 1024 * 1024)
        backup_count = self.config.get('backup_count', 5)
        
        # Create log directory
        log_dir = os.path.dirname(log_file)
        if log_dir:
            Path(log_dir).mkdir(parents=True, exist_ok=True)
        
        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        
        # Set formatter based on JSON logging preference
        if self.config.get('enable_json_logging', False):
            formatter = StructuredFormatter(
                include_extra=self.config.get('include_extra_fields', True)
            )
        else:
            formatter = MultiLineFormatter(
                fmt=self.config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        file_handler.setFormatter(formatter)
        file_handler.setLevel(getattr(logging, self.config['level']))
        
        logger.addHandler(file_handler)
    
    def _setup_console_logging(self, logger: logging.Logger):
        """Setup console logging."""
        console_handler = logging.StreamHandler(sys.stdout)
        
        console_level = self.config.get('console_level', self.config['level'])
        console_handler.setLevel(getattr(logging, console_level))
        
        # Use simpler format for console
        if self.config.get('enable_json_logging', False):
            formatter = StructuredFormatter(include_extra=False)
        else:
            formatter = logging.Formatter(
                fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%H:%M:%S'
            )
        
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    def _setup_syslog_logging(self, logger: logging.Logger):
        """Setup syslog logging for production environments."""
        try:
            syslog_host = self.config.get('syslog_host', 'localhost')
            syslog_port = self.config.get('syslog_port', 514)
            
            syslog_handler = logging.handlers.SysLogHandler(
                address=(syslog_host, syslog_port),
                facility=logging.handlers.SysLogHandler.LOG_LOCAL0
            )
            
            # Use structured format for syslog
            formatter = StructuredFormatter(include_extra=True)
            syslog_handler.setFormatter(formatter)
            syslog_handler.setLevel(getattr(logging, self.config['level']))
            
            logger.addHandler(syslog_handler)
            
        except Exception as e:
            # Don't fail if syslog is not available
            logger.warning(f"Failed to setup syslog logging: {e}")
    
    def _setup_structured_logging(self):
        """Setup structlog for structured logging."""
        try:
            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.processors.JSONRenderer()
                ],
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )
        except Exception as e:
            logging.getLogger().warning(f"Failed to setup structlog: {e}")
    
    def _load_config_from_env(self) -> Dict[str, Any]:
        """Load logging configuration from environment variables."""
        return {
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'format': os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            'enable_file_logging': os.getenv('LOG_ENABLE_FILE_LOGGING', 'true').lower() == 'true',
            'log_file': os.getenv('LOG_FILE', 'logs/pmcc_scanner.log'),
            'max_bytes': int(os.getenv('LOG_MAX_BYTES', str(10 * 1024 * 1024))),
            'backup_count': int(os.getenv('LOG_BACKUP_COUNT', '5')),
            'enable_console_logging': os.getenv('LOG_ENABLE_CONSOLE_LOGGING', 'true').lower() == 'true',
            'console_level': os.getenv('LOG_CONSOLE_LEVEL', 'INFO'),
            'enable_json_logging': os.getenv('LOG_ENABLE_JSON_LOGGING', 'false').lower() == 'true',
            'include_extra_fields': os.getenv('LOG_INCLUDE_EXTRA_FIELDS', 'true').lower() == 'true',
            'syslog_enabled': os.getenv('LOG_SYSLOG_ENABLED', 'false').lower() == 'true',
            'syslog_host': os.getenv('LOG_SYSLOG_HOST', 'localhost'),
            'syslog_port': int(os.getenv('LOG_SYSLOG_PORT', '514')),
        }
    
    def configure_third_party_loggers(self):
        """Configure third-party library loggers."""
        # Reduce verbosity of third-party libraries
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('apscheduler').setLevel(logging.INFO)
        
        # Twilio can be quite verbose
        logging.getLogger('twilio').setLevel(logging.WARNING)
        
        # Email providers (requests is used for Mailgun, keep sendgrid for backward compatibility)
        logging.getLogger('sendgrid').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
    
    def set_log_level(self, level: str):
        """Dynamically change log level."""
        log_level = getattr(logging, level.upper())
        
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Update all handlers
        for handler in root_logger.handlers:
            handler.setLevel(log_level)
        
        # Update config
        self.config['level'] = level.upper()
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get logging system statistics."""
        stats = {
            'handlers': [],
            'level': self.config['level'],
            'performance_loggers': list(self.performance_loggers.keys())
        }
        
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            handler_info = {
                'type': type(handler).__name__,
                'level': logging.getLevelName(handler.level)
            }
            
            if hasattr(handler, 'baseFilename'):
                handler_info['file'] = handler.baseFilename
                if os.path.exists(handler.baseFilename):
                    handler_info['file_size'] = os.path.getsize(handler.baseFilename)
            
            stats['handlers'].append(handler_info)
        
        return stats


# Global logger setup instance
_logger_setup: Optional[LoggerSetup] = None


def setup_logging(config: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """
    Setup application logging.
    
    Args:
        config: Optional logging configuration
        
    Returns:
        Main application logger
    """
    global _logger_setup
    
    if _logger_setup is None:
        _logger_setup = LoggerSetup(config)
    
    return _logger_setup.setup_logging()


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific component.
    
    Args:
        name: Component name
        
    Returns:
        Logger instance
    """
    if _logger_setup is None:
        setup_logging()
    
    return _logger_setup.get_logger(name)


def get_performance_logger(name: str = 'main') -> PerformanceLogger:
    """
    Get performance logger.
    
    Args:
        name: Component name
        
    Returns:
        PerformanceLogger instance
    """
    if _logger_setup is None:
        setup_logging()
    
    return _logger_setup.get_performance_logger(name)


def configure_third_party_loggers():
    """Configure third-party library loggers."""
    if _logger_setup is None:
        setup_logging()
    
    _logger_setup.configure_third_party_loggers()


def set_log_level(level: str):
    """Set global log level."""
    if _logger_setup is None:
        setup_logging()
    
    _logger_setup.set_log_level(level)


def get_log_stats() -> Dict[str, Any]:
    """Get logging system statistics."""
    if _logger_setup is None:
        return {}
    
    return _logger_setup.get_log_stats()


# Convenience decorators
def log_performance(operation: str = None):
    """Decorator to log function performance."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            perf_logger = get_performance_logger()
            op_name = operation or f"{func.__module__}.{func.__name__}"
            
            with perf_logger.timer(op_name):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def log_exceptions(logger_name: str = None):
    """Decorator to log exceptions."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger(logger_name or func.__module__)
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(
                    f"Exception in {func.__name__}",
                    extra={
                        "function": func.__name__,
                        "module": func.__module__,
                        "exception_type": type(e).__name__,
                        "args": str(args) if args else None,
                        "kwargs": str(kwargs) if kwargs else None
                    }
                )
                raise
        
        return wrapper
    return decorator


if __name__ == "__main__":
    """CLI for testing logging system."""
    import argparse
    
    parser = argparse.ArgumentParser(description="PMCC Scanner Logging System")
    parser.add_argument("--test", action="store_true", help="Run logging tests")
    parser.add_argument("--level", default="INFO", help="Log level")
    parser.add_argument("--json", action="store_true", help="Enable JSON logging")
    
    args = parser.parse_args()
    
    # Setup logging with test configuration
    config = {
        'level': args.level,
        'enable_json_logging': args.json,
        'enable_file_logging': True,
        'log_file': 'test.log'
    }
    
    logger = setup_logging(config)
    perf_logger = get_performance_logger()
    
    if args.test:
        # Test various log levels
        logger.debug("This is a debug message")
        logger.info("This is an info message")
        logger.warning("This is a warning message")
        logger.error("This is an error message")
        
        # Test structured logging
        logger.info(
            "Test structured log",
            extra={
                "test_field": "test_value",
                "number": 42,
                "boolean": True
            }
        )
        
        # Test performance logging
        with perf_logger.timer("test_operation", test_param="test_value"):
            time.sleep(0.1)
        
        # Test exception logging
        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("Caught test exception")
        
        print("Logging tests completed. Check test.log file.")
        print("Log stats:", get_log_stats())
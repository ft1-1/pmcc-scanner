"""
Comprehensive scheduler system for PMCC Scanner.

Provides robust job scheduling with error recovery, missed job handling,
and production-ready monitoring capabilities.
"""

import os
import time
import logging
import asyncio
import threading
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import signal
import sys

try:
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED, EVENT_JOB_MAX_INSTANCES
    from apscheduler.job import Job
    from apscheduler.jobstores.memory import MemoryJobStore
    from apscheduler.executors.pool import ThreadPoolExecutor
    import pytz
except ImportError as e:
    print(f"Missing required dependencies: {e}")
    print("Please install: pip install apscheduler pytz")
    sys.exit(1)


class JobStatus(str, Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    MISSED = "missed"
    CANCELLED = "cancelled"


class JobPriority(str, Enum):
    """Job priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class JobExecution:
    """Record of a job execution."""
    job_id: str
    job_name: str
    scheduled_time: datetime
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: JobStatus = JobStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_seconds: Optional[float] = None
    retry_count: int = 0
    next_retry: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_completed(self) -> bool:
        """Check if job completed successfully."""
        return self.status == JobStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Check if job failed."""
        return self.status == JobStatus.FAILED
    
    @property
    def is_running(self) -> bool:
        """Check if job is currently running."""
        return self.status == JobStatus.RUNNING


@dataclass
class JobConfig:
    """Configuration for a scheduled job."""
    name: str
    function: Callable
    trigger_type: str  # 'cron', 'interval', 'date'
    trigger_kwargs: Dict[str, Any]
    timezone: str = "US/Eastern"
    max_instances: int = 1
    misfire_grace_time: int = 300  # 5 minutes
    coalesce: bool = True
    retry_enabled: bool = True
    max_retries: int = 3
    retry_delay_seconds: int = 300  # 5 minutes
    retry_backoff_factor: float = 2.0
    priority: JobPriority = JobPriority.NORMAL
    timeout_seconds: Optional[int] = None
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class JobScheduler:
    """Main job scheduler with comprehensive monitoring and recovery."""
    
    def __init__(self, 
                 timezone: str = "US/Eastern",
                 max_workers: int = 2,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize job scheduler.
        
        Args:
            timezone: Default timezone for scheduling
            max_workers: Maximum number of concurrent jobs
            logger: Logger instance
        """
        self.timezone = pytz.timezone(timezone)
        self.logger = logger or logging.getLogger(__name__)
        
        # Job stores and executors
        jobstores = {
            'default': MemoryJobStore()
        }
        
        executors = {
            'default': ThreadPoolExecutor(max_workers=max_workers)
        }
        
        job_defaults = {
            'coalesce': True,
            'max_instances': 1,
            'misfire_grace_time': 300
        }
        
        # Create scheduler
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=self.timezone
        )
        
        # Job tracking
        self.job_configs: Dict[str, JobConfig] = {}
        self.job_executions: List[JobExecution] = []
        self.running_jobs: Dict[str, JobExecution] = {}
        
        # Stats
        self.stats = {
            'jobs_scheduled': 0,
            'jobs_executed': 0,
            'jobs_failed': 0,
            'jobs_missed': 0,
            'total_execution_time': 0.0,
            'last_reset': datetime.now()
        }
        
        # Setup event listeners
        self._setup_event_listeners()
        
        # Shutdown handling
        self._shutdown_requested = False
        self._setup_signal_handlers()
        
        self.logger.info("Job scheduler initialized")
    
    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            self.logger.info("Job scheduler started")
        else:
            self.logger.warning("Job scheduler is already running")
    
    def shutdown(self, wait: bool = True):
        """
        Shutdown the scheduler.
        
        Args:
            wait: Whether to wait for running jobs to complete
        """
        self._shutdown_requested = True
        
        if self.scheduler.running:
            self.logger.info("Shutting down job scheduler...")
            self.scheduler.shutdown(wait=wait)
            self.logger.info("Job scheduler shutdown complete")
    
    def add_job(self, config: JobConfig) -> str:
        """
        Add a job to the scheduler.
        
        Args:
            config: Job configuration
            
        Returns:
            Job ID
        """
        if not config.enabled:
            self.logger.info(f"Job {config.name} is disabled, skipping")
            return None
        
        # Create trigger
        if config.trigger_type == 'cron':
            trigger = CronTrigger(timezone=config.timezone, **config.trigger_kwargs)
        elif config.trigger_type == 'interval':
            trigger = IntervalTrigger(**config.trigger_kwargs)
        else:
            raise ValueError(f"Unsupported trigger type: {config.trigger_type}")
        
        # Wrap function with error handling and monitoring
        wrapped_function = self._wrap_job_function(config)
        
        # Add job to scheduler
        job = self.scheduler.add_job(
            wrapped_function,
            trigger=trigger,
            id=config.name,
            name=config.name,
            max_instances=config.max_instances,
            misfire_grace_time=config.misfire_grace_time,
            coalesce=config.coalesce,
            replace_existing=True
        )
        
        # Store configuration
        self.job_configs[config.name] = config
        self.stats['jobs_scheduled'] += 1
        
        self.logger.info(
            f"Job '{config.name}' scheduled",
            extra={
                "job_id": job.id,
                "trigger_type": config.trigger_type,
                "next_run": job.next_run_time.isoformat() if hasattr(job, 'next_run_time') and job.next_run_time else None
            }
        )
        
        return job.id
    
    def remove_job(self, job_id: str):
        """Remove a job from the scheduler."""
        try:
            self.scheduler.remove_job(job_id)
            if job_id in self.job_configs:
                del self.job_configs[job_id]
            self.logger.info(f"Job '{job_id}' removed")
        except Exception as e:
            self.logger.error(f"Error removing job '{job_id}': {e}")
    
    def pause_job(self, job_id: str):
        """Pause a job."""
        try:
            self.scheduler.pause_job(job_id)
            self.logger.info(f"Job '{job_id}' paused")
        except Exception as e:
            self.logger.error(f"Error pausing job '{job_id}': {e}")
    
    def resume_job(self, job_id: str):
        """Resume a paused job."""
        try:
            self.scheduler.resume_job(job_id)
            self.logger.info(f"Job '{job_id}' resumed")
        except Exception as e:
            self.logger.error(f"Error resuming job '{job_id}': {e}")
    
    def run_job_now(self, job_id: str) -> bool:
        """
        Run a job immediately.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if job was triggered successfully
        """
        try:
            job = self.scheduler.get_job(job_id)
            if not job:
                self.logger.error(f"Job '{job_id}' not found")
                return False
            
            # Modify the job to run immediately
            job.modify(next_run_time=datetime.now(self.timezone))
            self.logger.info(f"Job '{job_id}' scheduled to run immediately")
            return True
            
        except Exception as e:
            self.logger.error(f"Error running job '{job_id}' immediately: {e}")
            return False
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status information for a job."""
        job = self.scheduler.get_job(job_id)
        if not job:
            return None
        
        # Get latest execution
        latest_execution = None
        for execution in reversed(self.job_executions):
            if execution.job_id == job_id:
                latest_execution = execution
                break
        
        # Check if currently running
        is_running = job_id in self.running_jobs
        
        return {
            'job_id': job_id,
            'name': job.name,
            'next_run_time': job.next_run_time.isoformat() if hasattr(job, 'next_run_time') and job.next_run_time else None,
            'is_running': is_running,
            'latest_execution': {
                'status': latest_execution.status.value if latest_execution else None,
                'start_time': latest_execution.start_time.isoformat() if latest_execution and latest_execution.start_time else None,
                'duration_seconds': latest_execution.duration_seconds if latest_execution else None,
                'error': latest_execution.error if latest_execution else None
            } if latest_execution else None,
            'config': {
                'trigger_type': self.job_configs[job_id].trigger_type if job_id in self.job_configs else None,
                'enabled': self.job_configs[job_id].enabled if job_id in self.job_configs else None,
                'max_retries': self.job_configs[job_id].max_retries if job_id in self.job_configs else None
            }
        }
    
    def get_all_jobs_status(self) -> List[Dict[str, Any]]:
        """Get status for all jobs."""
        return [
            self.get_job_status(job.id) 
            for job in self.scheduler.get_jobs()
        ]
    
    def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        # Calculate success rate
        success_rate = 0.0
        if self.stats['jobs_executed'] > 0:
            successful_jobs = self.stats['jobs_executed'] - self.stats['jobs_failed']
            success_rate = successful_jobs / self.stats['jobs_executed']
        
        # Average execution time
        avg_execution_time = 0.0
        if self.stats['jobs_executed'] > 0:
            avg_execution_time = self.stats['total_execution_time'] / self.stats['jobs_executed']
        
        # Recent execution summary
        recent_executions = [
            e for e in self.job_executions 
            if e.start_time and e.start_time > datetime.now() - timedelta(hours=24)
        ]
        
        return {
            'scheduler_running': self.scheduler.running,
            'total_jobs': len(self.scheduler.get_jobs()),
            'running_jobs': len(self.running_jobs),
            'stats': {
                **self.stats,
                'success_rate': success_rate,
                'avg_execution_time_seconds': avg_execution_time
            },
            'recent_executions': len(recent_executions),
            'last_updated': datetime.now().isoformat()
        }
    
    def _wrap_job_function(self, config: JobConfig) -> Callable:
        """Wrap job function with monitoring and error handling."""
        
        def wrapped_function():
            execution = JobExecution(
                job_id=config.name,
                job_name=config.name,
                scheduled_time=datetime.now(self.timezone)
            )
            
            # Add to tracking
            self.running_jobs[config.name] = execution
            self.job_executions.append(execution)
            
            execution.start_time = datetime.now()
            execution.status = JobStatus.RUNNING
            
            self.logger.info(
                f"Starting job '{config.name}'",
                extra={"job_id": config.name, "scheduled_time": execution.scheduled_time.isoformat()}
            )
            
            try:
                # Execute with timeout if specified
                if config.timeout_seconds:
                    result = self._execute_with_timeout(config.function, config.timeout_seconds)
                else:
                    result = config.function()
                
                # Job completed successfully
                execution.end_time = datetime.now()
                execution.duration_seconds = (execution.end_time - execution.start_time).total_seconds()
                execution.status = JobStatus.COMPLETED
                execution.result = result
                
                # Update stats
                self.stats['jobs_executed'] += 1
                self.stats['total_execution_time'] += execution.duration_seconds
                
                self.logger.info(
                    f"Job '{config.name}' completed successfully",
                    extra={
                        "job_id": config.name,
                        "duration_seconds": execution.duration_seconds,
                        "result": str(result) if result else None
                    }
                )
                
            except Exception as e:
                # Job failed
                execution.end_time = datetime.now()
                execution.duration_seconds = (execution.end_time - execution.start_time).total_seconds()
                execution.status = JobStatus.FAILED
                execution.error = str(e)
                
                # Update stats
                self.stats['jobs_failed'] += 1
                
                self.logger.error(
                    f"Job '{config.name}' failed",
                    extra={
                        "job_id": config.name,
                        "duration_seconds": execution.duration_seconds,
                        "error": str(e)
                    },
                    exc_info=True
                )
                
                # Schedule retry if enabled
                if config.retry_enabled and execution.retry_count < config.max_retries:
                    self._schedule_retry(config, execution)
                
                # Re-raise for APScheduler to handle
                raise
            
            finally:
                # Remove from running jobs
                if config.name in self.running_jobs:
                    del self.running_jobs[config.name]
                
                # Cleanup old executions (keep last 100)
                if len(self.job_executions) > 100:
                    self.job_executions = self.job_executions[-100:]
        
        return wrapped_function
    
    def _execute_with_timeout(self, func: Callable, timeout_seconds: int) -> Any:
        """Execute function with timeout."""
        result = None
        exception = None
        
        def target():
            nonlocal result, exception
            try:
                result = func()
            except Exception as e:
                exception = e
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout_seconds)
        
        if thread.is_alive():
            # Thread is still running, consider it timed out
            raise TimeoutError(f"Job execution timed out after {timeout_seconds} seconds")
        
        if exception:
            raise exception
        
        return result
    
    def _schedule_retry(self, config: JobConfig, execution: JobExecution):
        """Schedule a retry for a failed job."""
        retry_delay = config.retry_delay_seconds * (config.retry_backoff_factor ** execution.retry_count)
        retry_time = datetime.now(self.timezone) + timedelta(seconds=retry_delay)
        
        execution.retry_count += 1
        execution.next_retry = retry_time
        
        # Create retry job
        retry_job_id = f"{config.name}_retry_{execution.retry_count}"
        
        self.scheduler.add_job(
            config.function,
            trigger='date',
            run_date=retry_time,
            id=retry_job_id,
            max_instances=1,
            replace_existing=True
        )
        
        self.logger.info(
            f"Scheduled retry {execution.retry_count}/{config.max_retries} for job '{config.name}'",
            extra={
                "job_id": config.name,
                "retry_job_id": retry_job_id,
                "retry_time": retry_time.isoformat(),
                "retry_delay_seconds": retry_delay
            }
        )
    
    def _setup_event_listeners(self):
        """Setup APScheduler event listeners."""
        
        def job_executed(event):
            self.logger.debug(f"Job executed: {event.job_id}")
        
        def job_error(event):
            self.logger.error(f"Job error: {event.job_id} - {event.exception}")
        
        def job_missed(event):
            self.stats['jobs_missed'] += 1
            self.logger.warning(f"Job missed: {event.job_id} at {event.scheduled_run_time}")
            
            # Record missed execution
            execution = JobExecution(
                job_id=event.job_id,
                job_name=event.job_id,
                scheduled_time=event.scheduled_run_time,
                status=JobStatus.MISSED
            )
            self.job_executions.append(execution)
        
        def max_instances_reached(event):
            self.logger.warning(f"Max instances reached for job: {event.job_id}")
        
        self.scheduler.add_listener(job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(job_error, EVENT_JOB_ERROR)
        self.scheduler.add_listener(job_missed, EVENT_JOB_MISSED)
        self.scheduler.add_listener(max_instances_reached, EVENT_JOB_MAX_INSTANCES)
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.shutdown(wait=True)
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def export_job_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Export job execution history.
        
        Args:
            hours: Number of hours of history to export
            
        Returns:
            List of job execution records
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        return [
            {
                'job_id': execution.job_id,
                'job_name': execution.job_name,
                'scheduled_time': execution.scheduled_time.isoformat(),
                'start_time': execution.start_time.isoformat() if execution.start_time else None,
                'end_time': execution.end_time.isoformat() if execution.end_time else None,
                'status': execution.status.value,
                'duration_seconds': execution.duration_seconds,
                'error': execution.error,
                'retry_count': execution.retry_count
            }
            for execution in self.job_executions
            if execution.start_time and execution.start_time > cutoff_time
        ]
    
    def health_check(self) -> Dict[str, Any]:
        """Perform scheduler health check."""
        is_healthy = True
        issues = []
        
        # Check if scheduler is running
        if not self.scheduler.running:
            is_healthy = False
            issues.append("Scheduler is not running")
        
        # Check for stuck jobs (running longer than expected)
        stuck_jobs = []
        for job_id, execution in self.running_jobs.items():
            if execution.start_time:
                running_time = (datetime.now() - execution.start_time).total_seconds()
                config = self.job_configs.get(job_id)
                
                # Consider job stuck if running longer than timeout + grace period
                max_runtime = (config.timeout_seconds or 3600) + 600  # 10 minute grace
                if running_time > max_runtime:
                    stuck_jobs.append({
                        'job_id': job_id,
                        'running_time_seconds': running_time
                    })
        
        if stuck_jobs:
            is_healthy = False
            issues.append(f"Found {len(stuck_jobs)} stuck jobs")
        
        # Check recent failure rate
        recent_executions = [
            e for e in self.job_executions 
            if e.start_time and e.start_time > datetime.now() - timedelta(hours=1)
        ]
        
        if recent_executions:
            failed_executions = [e for e in recent_executions if e.is_failed]
            failure_rate = len(failed_executions) / len(recent_executions)
            
            if failure_rate > 0.5:  # More than 50% failure rate
                is_healthy = False
                issues.append(f"High failure rate: {failure_rate:.1%}")
        
        return {
            'healthy': is_healthy,
            'issues': issues,
            'running_jobs': len(self.running_jobs),
            'stuck_jobs': stuck_jobs,
            'recent_executions': len(recent_executions),
            'scheduler_running': self.scheduler.running,
            'timestamp': datetime.now().isoformat()
        }


def create_daily_scan_scheduler(scan_function: Callable,
                              scan_time: str = "09:30",
                              timezone: str = "US/Eastern",
                              logger: Optional[logging.Logger] = None) -> JobScheduler:
    """
    Create a scheduler configured for daily PMCC scans.
    
    Args:
        scan_function: Function to execute for scans
        scan_time: Time to run scans (HH:MM format)
        timezone: Timezone for scheduling
        logger: Logger instance
        
    Returns:
        Configured JobScheduler instance
    """
    scheduler = JobScheduler(timezone=timezone, logger=logger)
    
    # Parse scan time
    hour, minute = map(int, scan_time.split(':'))
    
    # Create job configuration
    job_config = JobConfig(
        name="daily_pmcc_scan",
        function=scan_function,
        trigger_type="cron",
        trigger_kwargs={
            'hour': hour,
            'minute': minute,
            'day_of_week': '0-4'  # Monday to Friday only
        },
        timezone=timezone,
        max_instances=1,
        misfire_grace_time=1800,  # 30 minutes grace
        retry_enabled=True,
        max_retries=2,
        retry_delay_seconds=900,  # 15 minutes
        timeout_seconds=3600,  # 1 hour timeout
        priority=JobPriority.HIGH,
        metadata={
            'description': 'Daily PMCC opportunities scan',
            'type': 'scheduled_scan'
        }
    )
    
    scheduler.add_job(job_config)
    
    return scheduler


if __name__ == "__main__":
    """CLI for testing scheduler."""
    import argparse
    
    def test_job():
        """Test job function."""
        print(f"Test job executed at {datetime.now()}")
        time.sleep(2)
        return "Job completed successfully"
    
    def failing_job():
        """Test failing job."""
        raise ValueError("This job always fails")
    
    parser = argparse.ArgumentParser(description="PMCC Scanner Job Scheduler")
    parser.add_argument("--test", action="store_true", help="Run scheduler tests")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Create scheduler
    scheduler = JobScheduler(logger=logger)
    
    if args.test:
        # Add test jobs
        test_config = JobConfig(
            name="test_job",
            function=test_job,
            trigger_type="interval",
            trigger_kwargs={'seconds': 10}
        )
        
        failing_config = JobConfig(
            name="failing_job",
            function=failing_job,
            trigger_type="interval",
            trigger_kwargs={'seconds': 20},
            max_retries=2
        )
        
        scheduler.add_job(test_config)
        scheduler.add_job(failing_config)
        
        scheduler.start()
        
        try:
            # Run for 60 seconds
            time.sleep(60)
        finally:
            scheduler.shutdown()
        
        # Print stats
        print("\nScheduler Stats:")
        print(scheduler.get_scheduler_stats())
        
        print("\nJob History:")
        for execution in scheduler.export_job_history():
            print(f"  {execution['job_name']}: {execution['status']} ({execution.get('duration_seconds', 0):.2f}s)")
    
    elif args.daemon:
        scheduler.start()
        
        try:
            # Keep running until interrupted
            while not scheduler._shutdown_requested:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            scheduler.shutdown()
    
    else:
        print("Use --test to run tests or --daemon to run as daemon")
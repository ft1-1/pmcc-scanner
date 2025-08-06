#!/usr/bin/env python3
"""
Daily scan runner script for PMCC Scanner.

This script is designed to be run by cron or systemd for scheduled execution.
Provides robust error handling, logging, and exit codes for monitoring.
"""

import os
import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Add project root to Python path to enable src package imports
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

# Set working directory to project root
os.chdir(project_root)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"Loaded environment from {env_file}")
except ImportError:
    print("Warning: python-dotenv not installed, using system environment variables only")


def setup_script_logging() -> logging.Logger:
    """Setup logging for the script runner."""
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger("pmcc_daily_scan")
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler
    log_file = log_dir / "daily_scan.log"
    file_handler = logging.FileHandler(log_file)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger


def check_environment() -> bool:
    """
    Check if the environment is properly configured.
    
    Returns:
        True if environment is ready
    """
    logger = logging.getLogger("pmcc_daily_scan")
    
    # Check for required environment variables
    required_env_vars = [
        'MARKETDATA_API_TOKEN'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        return False
    
    # Check if src directory exists
    src_dir = project_root / "src"
    if not src_dir.exists():
        logger.error(f"Source directory not found: {src_dir}")
        return False
    
    # Check if configuration can be loaded
    try:
        from src.config import get_settings
        settings = get_settings()
        logger.info(f"Configuration loaded successfully (env: {settings.environment.value})")
        return True
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return False


def check_lockfile() -> bool:
    """
    Check if another instance is already running.
    
    Returns:
        True if no other instance is running
    """
    logger = logging.getLogger("pmcc_daily_scan")
    
    lockfile = project_root / "tmp" / "daily_scan.lock"
    lockfile.parent.mkdir(exist_ok=True)
    
    if lockfile.exists():
        try:
            # Read PID from lockfile
            pid = int(lockfile.read_text().strip())
            
            # Check if process is still running
            try:
                os.kill(pid, 0)  # Check if process exists
                logger.warning(f"Another instance is already running (PID: {pid})")
                return False
            except (OSError, ProcessLookupError):
                # Process doesn't exist, remove stale lockfile
                logger.info("Removing stale lockfile")
                lockfile.unlink()
        except Exception as e:
            logger.warning(f"Error checking lockfile: {e}")
            lockfile.unlink()
    
    # Create new lockfile
    try:
        lockfile.write_text(str(os.getpid()))
        logger.debug(f"Created lockfile with PID {os.getpid()}")
        return True
    except Exception as e:
        logger.error(f"Failed to create lockfile: {e}")
        return False


def remove_lockfile():
    """Remove the lockfile on exit."""
    lockfile = project_root / "tmp" / "daily_scan.lock"
    try:
        if lockfile.exists():
            lockfile.unlink()
    except Exception:
        pass  # Ignore errors during cleanup


def run_daily_scan() -> Dict[str, Any]:
    """
    Run the daily PMCC scan.
    
    Returns:
        Scan results and metadata
    """
    logger = logging.getLogger("pmcc_daily_scan")
    
    start_time = datetime.now()
    
    try:
        # Import and create application
        from src.main import PMCCApplication
        
        logger.info("Initializing PMCC Scanner application...")
        app = PMCCApplication()
        
        # Initialize application
        if not app.initialize():
            return {
                'success': False,
                'error': 'Failed to initialize application',
                'duration_seconds': (datetime.now() - start_time).total_seconds()
            }
        
        logger.info("Running PMCC scan...")
        
        # Execute scan
        scan_result = app.run_scan()
        
        if scan_result is None:
            return {
                'success': False,
                'error': 'Scan returned no results',
                'duration_seconds': (datetime.now() - start_time).total_seconds()
            }
        
        # Process results
        duration = (datetime.now() - start_time).total_seconds()
        
        result_summary = {
            'success': True,
            'scan_id': scan_result.scan_id,
            'duration_seconds': duration,
            'scan_duration_seconds': scan_result.total_duration_seconds,
            'opportunities_found': scan_result.opportunities_found,
            'stocks_screened': scan_result.stocks_screened,
            'stocks_passed_screening': scan_result.stocks_passed_screening,
            'errors': len(scan_result.errors),
            'warnings': len(scan_result.warnings),
            'top_opportunity': None
        }
        
        # Add top opportunity info if available
        if scan_result.top_opportunities:
            top_opp = scan_result.top_opportunities[0]
            result_summary['top_opportunity'] = {
                'symbol': top_opp.symbol,
                'score': float(top_opp.total_score or 0),
                'max_profit': float(top_opp.analysis.risk_metrics.max_profit or 0) if top_opp.analysis.risk_metrics else 0,
                'risk_reward_ratio': float(top_opp.risk_reward_ratio or 0)
            }
        
        logger.info(
            f"Scan completed successfully: {scan_result.opportunities_found} opportunities found "
            f"in {duration:.1f} seconds"
        )
        
        return result_summary
    
    except Exception as e:
        logger.error(f"Error during scan execution: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'duration_seconds': (datetime.now() - start_time).total_seconds()
        }


def save_run_metadata(result: Dict[str, Any]):
    """Save run metadata for monitoring."""
    try:
        metadata_dir = project_root / "data" / "run_metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metadata_file = metadata_dir / f"daily_scan_{timestamp}.json"
        
        # Add timestamp and hostname
        result['timestamp'] = datetime.now().isoformat()
        result['hostname'] = os.uname().nodename if hasattr(os, 'uname') else 'unknown'
        result['script_version'] = '1.0'
        
        with open(metadata_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        # Also save as "latest" for monitoring
        latest_file = metadata_dir / "latest_run.json"
        with open(latest_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        logging.getLogger("pmcc_daily_scan").info(f"Run metadata saved to {metadata_file}")
        
    except Exception as e:
        logging.getLogger("pmcc_daily_scan").warning(f"Failed to save run metadata: {e}")


def cleanup_old_files():
    """Clean up old log and metadata files."""
    logger = logging.getLogger("pmcc_daily_scan")
    
    try:
        # Clean up old metadata files (keep last 30 days)
        metadata_dir = project_root / "data" / "run_metadata"
        if metadata_dir.exists():
            cutoff_date = datetime.now() - timedelta(days=30)
            
            for file_path in metadata_dir.glob("daily_scan_*.json"):
                try:
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_date:
                        file_path.unlink()
                        logger.debug(f"Removed old metadata file: {file_path}")
                except Exception as e:
                    logger.warning(f"Error removing old file {file_path}: {e}")
        
        # Clean up old export files (keep last 7 days)
        data_dir = project_root / "data"
        if data_dir.exists():
            cutoff_date = datetime.now() - timedelta(days=7)
            
            for file_path in data_dir.glob("pmcc_scan_*.json"):
                try:
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_date:
                        file_path.unlink()
                        logger.debug(f"Removed old export file: {file_path}")
                except Exception as e:
                    logger.warning(f"Error removing old file {file_path}: {e}")
    
    except Exception as e:
        logger.warning(f"Error during cleanup: {e}")


def main() -> int:
    """
    Main entry point for daily scan script.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Setup logging
    logger = setup_script_logging()
    
    try:
        logger.info("=== PMCC Daily Scan Started ===")
        
        # Check environment
        if not check_environment():
            logger.error("Environment check failed")
            return 1
        
        # Check for running instances
        if not check_lockfile():
            logger.error("Another instance is already running")
            return 2
        
        try:
            # Run the scan
            result = run_daily_scan()
            
            # Save metadata
            save_run_metadata(result)
            
            # Cleanup old files
            cleanup_old_files()
            
            # Determine exit code
            if result['success']:
                logger.info("=== PMCC Daily Scan Completed Successfully ===")
                
                # Log summary
                if 'opportunities_found' in result:
                    logger.info(f"Summary: {result['opportunities_found']} opportunities found, "
                              f"processed {result.get('stocks_screened', 0)} stocks")
                
                return 0
            else:
                logger.error(f"=== PMCC Daily Scan Failed: {result.get('error', 'Unknown error')} ===")
                return 3
        
        finally:
            # Always remove lockfile
            remove_lockfile()
    
    except KeyboardInterrupt:
        logger.info("Scan interrupted by user")
        return 130  # Standard exit code for SIGINT
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 4
    
    finally:
        logger.info("=== PMCC Daily Scan Script Exiting ===")


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
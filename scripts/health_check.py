#!/usr/bin/env python3
"""
Health check script for PMCC Scanner.

Performs comprehensive health checks and returns appropriate exit codes
for monitoring systems and load balancers.
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Add src directory to Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

# Set working directory to project root
os.chdir(project_root)


class HealthChecker:
    """Comprehensive health checker for PMCC Scanner."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.checks = {}
    
    def check_environment(self) -> bool:
        """Check if environment is properly configured."""
        try:
            # Check required environment variables
            required_vars = [
                'MARKETDATA_API_TOKEN'
            ]
            
            missing_vars = []
            for var in required_vars:
                if not os.getenv(var):
                    missing_vars.append(var)
            
            if missing_vars:
                self.checks['environment'] = {
                    'healthy': False,
                    'details': f'Missing environment variables: {missing_vars}'
                }
                return False
            
            # Try to load configuration
            from config import get_settings
            settings = get_settings()
            
            self.checks['environment'] = {
                'healthy': True,
                'details': f'Environment configured for {settings.environment.value}'
            }
            return True
            
        except Exception as e:
            self.checks['environment'] = {
                'healthy': False,
                'details': f'Configuration error: {str(e)}'
            }
            return False
    
    def check_dependencies(self) -> bool:
        """Check if all required dependencies are available."""
        try:
            # Test critical imports
            import pandas
            import numpy
            import requests
            import pydantic
            from dotenv import load_dotenv
            from apscheduler.schedulers.background import BackgroundScheduler
            
            # Test optional but important imports
            try:
                import twilio
                twilio_available = True
            except ImportError:
                twilio_available = False
            
            # Check if email sending is available (using requests for Mailgun)
            try:
                import requests
                email_available = True
            except ImportError:
                email_available = False
            
            details = "All required dependencies available"
            if not twilio_available:
                details += " (Twilio not available - WhatsApp notifications disabled)"
            if not email_available:
                details += " (Requests not available - Email notifications disabled)"
            
            self.checks['dependencies'] = {
                'healthy': True,
                'details': details
            }
            return True
            
        except ImportError as e:
            self.checks['dependencies'] = {
                'healthy': False,
                'details': f'Missing dependency: {str(e)}'
            }
            return False
        except Exception as e:
            self.checks['dependencies'] = {
                'healthy': False,
                'details': f'Dependency check error: {str(e)}'
            }
            return False
    
    def check_api_connectivity(self) -> bool:
        """Check MarketData API connectivity."""
        try:
            from api.marketdata_client import MarketDataClient
            from config import get_settings
            
            settings = get_settings()
            
            # Create API client
            client = MarketDataClient(
                api_token=settings.marketdata.api_token,
                base_url=settings.marketdata.base_url,
                timeout_seconds=10  # Short timeout for health check
            )
            
            # Test with a simple quote
            response = client.get_quote('AAPL')
            
            if response.is_success:
                self.checks['api_connectivity'] = {
                    'healthy': True,
                    'details': 'MarketData API accessible'
                }
                return True
            else:
                self.checks['api_connectivity'] = {
                    'healthy': False,
                    'details': f'API error: {response.error_message}'
                }
                return False
                
        except Exception as e:
            self.checks['api_connectivity'] = {
                'healthy': False,
                'details': f'API connectivity error: {str(e)}'
            }
            return False
    
    def check_notifications(self) -> bool:
        """Check notification system connectivity."""
        try:
            from notifications.notification_manager import NotificationManager
            
            # Create notification manager
            manager = NotificationManager.create_from_env()
            
            # Test connectivity
            connectivity = manager.test_connectivity()
            
            active_channels = [channel for channel, status in connectivity.items() if status]
            
            if active_channels:
                self.checks['notifications'] = {
                    'healthy': True,
                    'details': f'Active channels: {active_channels}'
                }
                return True
            else:
                # Notifications not healthy but not critical for health check
                self.checks['notifications'] = {
                    'healthy': False,
                    'details': 'No notification channels available'
                }
                return True  # Don't fail health check for notifications
                
        except Exception as e:
            self.checks['notifications'] = {
                'healthy': False,
                'details': f'Notification system error: {str(e)}'
            }
            return True  # Don't fail health check for notifications
    
    def check_file_system(self) -> bool:
        """Check file system accessibility."""
        try:
            from config import get_settings
            settings = get_settings()
            
            # Check if required directories exist and are writable
            required_dirs = [
                Path(settings.working_dir),
                Path(settings.data_dir),
                Path(settings.temp_dir),
                Path(settings.logging.log_file).parent
            ]
            
            for directory in required_dirs:
                if not directory.exists():
                    directory.mkdir(parents=True, exist_ok=True)
                
                # Test write permissions
                test_file = directory / f".health_check_{int(time.time())}"
                try:
                    test_file.write_text("health check")
                    test_file.unlink()
                except Exception:
                    self.checks['file_system'] = {
                        'healthy': False,
                        'details': f'Cannot write to directory: {directory}'
                    }
                    return False
            
            self.checks['file_system'] = {
                'healthy': True,
                'details': 'All directories accessible and writable'
            }
            return True
            
        except Exception as e:
            self.checks['file_system'] = {
                'healthy': False,
                'details': f'File system error: {str(e)}'
            }
            return False
    
    def check_recent_activity(self) -> bool:
        """Check for recent scan activity."""
        try:
            metadata_dir = project_root / "data" / "run_metadata"
            
            if not metadata_dir.exists():
                self.checks['recent_activity'] = {
                    'healthy': True,
                    'details': 'No previous runs (new installation)'
                }
                return True
            
            # Look for recent successful runs
            latest_file = metadata_dir / "latest_run.json"
            
            if not latest_file.exists():
                # Look for any recent metadata files
                recent_files = []
                cutoff_time = datetime.now() - timedelta(days=2)
                
                for file_path in metadata_dir.glob("daily_scan_*.json"):
                    try:
                        file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_time > cutoff_time:
                            recent_files.append(file_path)
                    except Exception:
                        continue
                
                if not recent_files:
                    self.checks['recent_activity'] = {
                        'healthy': False,
                        'details': 'No recent scan activity found'
                    }
                    return False
                else:
                    self.checks['recent_activity'] = {
                        'healthy': True,
                        'details': f'Found {len(recent_files)} recent runs'
                    }
                    return True
            
            # Check latest run
            try:
                with open(latest_file) as f:
                    latest_run = json.load(f)
                
                run_time = datetime.fromisoformat(latest_run['timestamp'].replace('Z', '+00:00'))
                hours_ago = (datetime.now() - run_time.replace(tzinfo=None)).total_seconds() / 3600
                
                if hours_ago > 48:  # More than 2 days
                    self.checks['recent_activity'] = {
                        'healthy': False,
                        'details': f'Last run was {hours_ago:.1f} hours ago'
                    }
                    return False
                
                # Check if last run was successful
                if latest_run.get('success', False):
                    self.checks['recent_activity'] = {
                        'healthy': True,
                        'details': f'Last successful run {hours_ago:.1f} hours ago'
                    }
                    return True
                else:
                    self.checks['recent_activity'] = {
                        'healthy': False,
                        'details': f'Last run failed {hours_ago:.1f} hours ago: {latest_run.get("error", "Unknown error")}'
                    }
                    return False
                    
            except Exception as e:
                self.checks['recent_activity'] = {
                    'healthy': False,
                    'details': f'Error reading latest run data: {str(e)}'
                }
                return False
                
        except Exception as e:
            self.checks['recent_activity'] = {
                'healthy': False,
                'details': f'Activity check error: {str(e)}'
            }
            return False
    
    def check_http_endpoint(self, port: int = 8080, path: str = "/health") -> bool:
        """Check if HTTP health endpoint is responding."""
        try:
            url = f"http://localhost:{port}{path}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                health_data = response.json()
                if health_data.get('healthy', False):
                    self.checks['http_endpoint'] = {
                        'healthy': True,
                        'details': 'HTTP endpoint responding and healthy'
                    }
                    return True
                else:
                    self.checks['http_endpoint'] = {
                        'healthy': False,
                        'details': 'HTTP endpoint reports unhealthy'
                    }
                    return False
            else:
                self.checks['http_endpoint'] = {
                    'healthy': False,
                    'details': f'HTTP endpoint returned {response.status_code}'
                }
                return False
                
        except requests.exceptions.ConnectionError:
            self.checks['http_endpoint'] = {
                'healthy': False,
                'details': 'HTTP endpoint not accessible (daemon not running)'
            }
            return False
        except Exception as e:
            self.checks['http_endpoint'] = {
                'healthy': False,
                'details': f'HTTP endpoint error: {str(e)}'
            }
            return False
    
    def run_all_checks(self, include_http: bool = False) -> Dict[str, Any]:
        """
        Run all health checks.
        
        Args:
            include_http: Whether to check HTTP endpoint
            
        Returns:
            Health check results
        """
        start_time = datetime.now()
        
        if self.verbose:
            print("Running PMCC Scanner health checks...")
        
        # Run individual checks
        checks_passed = 0
        total_checks = 0
        
        check_methods = [
            ('environment', self.check_environment),
            ('dependencies', self.check_dependencies),
            ('api_connectivity', self.check_api_connectivity),
            ('notifications', self.check_notifications),
            ('file_system', self.check_file_system),
            ('recent_activity', self.check_recent_activity)
        ]
        
        if include_http:
            check_methods.append(('http_endpoint', self.check_http_endpoint))
        
        for check_name, check_method in check_methods:
            total_checks += 1
            try:
                if self.verbose:
                    print(f"  Checking {check_name}...")
                
                if check_method():
                    checks_passed += 1
                    if self.verbose:
                        print(f"    ✅ {self.checks[check_name]['details']}")
                else:
                    if self.verbose:
                        print(f"    ❌ {self.checks[check_name]['details']}")
            except Exception as e:
                if self.verbose:
                    print(f"    💥 Error: {str(e)}")
        
        # Calculate overall health
        # Consider healthy if critical checks pass
        critical_checks = ['environment', 'dependencies', 'file_system']
        critical_passed = all(
            self.checks.get(check, {}).get('healthy', False) 
            for check in critical_checks
        )
        
        # Overall health requires critical checks plus some connectivity
        overall_healthy = (
            critical_passed and 
            (self.checks.get('api_connectivity', {}).get('healthy', False) or
             self.checks.get('recent_activity', {}).get('healthy', False))
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return {
            'healthy': overall_healthy,
            'checks': self.checks,
            'summary': {
                'checks_passed': checks_passed,
                'total_checks': total_checks,
                'success_rate': checks_passed / total_checks if total_checks > 0 else 0
            },
            'duration_seconds': duration,
            'timestamp': datetime.now().isoformat()
        }


def main() -> int:
    """
    Main entry point for health check script.
    
    Returns:
        Exit code (0 for healthy, 1 for unhealthy, 2 for error)
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="PMCC Scanner Health Check")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    parser.add_argument("--include-http", action="store_true", help="Check HTTP endpoint")
    parser.add_argument("--timeout", type=int, default=30, help="Overall timeout in seconds")
    
    args = parser.parse_args()
    
    try:
        # Create health checker
        checker = HealthChecker(verbose=args.verbose and not args.json)
        
        # Run checks with timeout
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Health check timed out")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(args.timeout)
        
        try:
            results = checker.run_all_checks(include_http=args.include_http)
        finally:
            signal.alarm(0)  # Cancel timeout
        
        # Output results
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            # Human-readable output
            print(f"\nPMCC Scanner Health Check Results:")
            print(f"Overall Status: {'✅ HEALTHY' if results['healthy'] else '❌ UNHEALTHY'}")
            print(f"Checks: {results['summary']['checks_passed']}/{results['summary']['total_checks']} passed")
            print(f"Duration: {results['duration_seconds']:.2f} seconds")
            
            if not results['healthy']:
                print("\nFailed Checks:")
                for check_name, check_result in results['checks'].items():
                    if not check_result['healthy']:
                        print(f"  ❌ {check_name}: {check_result['details']}")
        
        # Return appropriate exit code
        return 0 if results['healthy'] else 1
        
    except TimeoutError:
        if args.json:
            print(json.dumps({
                'healthy': False,
                'error': 'Health check timed out',
                'timestamp': datetime.now().isoformat()
            }))
        else:
            print("❌ Health check timed out")
        return 2
        
    except Exception as e:
        if args.json:
            print(json.dumps({
                'healthy': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }))
        else:
            print(f"💥 Health check error: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
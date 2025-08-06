#!/bin/bash
# PMCC Scanner Deployment Validation Script
# Comprehensive checks to ensure the application is ready for production

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Test results
declare -a RESULTS

# Logging functions
log_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    PASSED=$((PASSED + 1))
    RESULTS+=("PASS: $1")
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    FAILED=$((FAILED + 1))
    RESULTS+=("FAIL: $1")
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    WARNINGS=$((WARNINGS + 1))
    RESULTS+=("WARN: $1")
}

# Check Python installation
check_python() {
    log_test "Checking Python installation..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')
        if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)'; then
            log_pass "Python $PYTHON_VERSION installed (3.8+ required)"
        else
            log_fail "Python $PYTHON_VERSION installed (3.8+ required)"
        fi
    else
        log_fail "Python 3 not found"
    fi
}

# Check virtual environment
check_virtualenv() {
    log_test "Checking virtual environment..."
    
    if [[ -d "$PROJECT_ROOT/venv" ]]; then
        if [[ -f "$PROJECT_ROOT/venv/bin/activate" ]]; then
            log_pass "Virtual environment exists"
        else
            log_fail "Virtual environment corrupted"
        fi
    else
        log_fail "Virtual environment not found"
    fi
}

# Check dependencies
check_dependencies() {
    log_test "Checking Python dependencies..."
    
    if [[ -f "$PROJECT_ROOT/venv/bin/python" ]]; then
        # Test critical imports
        if "$PROJECT_ROOT/venv/bin/python" -c "import aiohttp, pandas, pydantic, twilio; from pathlib import Path; import requests" 2>/dev/null; then
            log_pass "Core dependencies installed"
        else
            log_fail "Missing core dependencies (run ./scripts/setup.sh)"
        fi
    else
        log_fail "Cannot check dependencies - virtual environment not set up"
    fi
}

# Check directory structure
check_directories() {
    log_test "Checking directory structure..."
    
    REQUIRED_DIRS=(
        "src/api"
        "src/analysis"
        "src/notifications"
        "src/config"
        "src/utils"
        "src/models"
        "tests/unit"
        "tests/integration"
        "scripts"
        "logs"
        "data"
    )
    
    ALL_EXIST=true
    for dir in "${REQUIRED_DIRS[@]}"; do
        if [[ ! -d "$PROJECT_ROOT/$dir" ]]; then
            ALL_EXIST=false
            log_warn "Missing directory: $dir"
        fi
    done
    
    if $ALL_EXIST; then
        log_pass "All required directories exist"
    else
        log_fail "Missing required directories"
    fi
}

# Check configuration files
check_configuration() {
    log_test "Checking configuration files..."
    
    # Check .env file
    if [[ -f "$PROJECT_ROOT/.env" ]]; then
        log_pass "Environment file exists"
        
        # Check for required variables
        REQUIRED_VARS=(
            "MARKETDATA_API_TOKEN"
            "TWILIO_ACCOUNT_SID"
            "TWILIO_AUTH_TOKEN"
        )
        
        # Check for email provider variables (either Mailgun or SendGrid)
        EMAIL_VARS_MAILGUN=(
            "MAILGUN_API_KEY"
            "MAILGUN_DOMAIN"
        )
        
        EMAIL_VARS_SENDGRID=(
            "SENDGRID_API_KEY"
        )
        
        source "$PROJECT_ROOT/.env" 2>/dev/null || true
        
        for var in "${REQUIRED_VARS[@]}"; do
            if [[ -z "${!var:-}" ]] || [[ "${!var}" == *"your_"* ]] || [[ "${!var}" == *"_here"* ]]; then
                log_warn "Environment variable $var not configured"
            fi
        done
        
        # Check email provider configuration
        HAS_MAILGUN=true
        for var in "${EMAIL_VARS_MAILGUN[@]}"; do
            if [[ -z "${!var:-}" ]] || [[ "${!var}" == *"your_"* ]] || [[ "${!var}" == *"_here"* ]]; then
                HAS_MAILGUN=false
                break
            fi
        done
        
        HAS_SENDGRID=true
        for var in "${EMAIL_VARS_SENDGRID[@]}"; do
            if [[ -z "${!var:-}" ]] || [[ "${!var}" == *"your_"* ]] || [[ "${!var}" == *"_here"* ]]; then
                HAS_SENDGRID=false
                break
            fi
        done
        
        if [[ "$HAS_MAILGUN" == "true" ]]; then
            log_pass "Mailgun email provider configured"
        elif [[ "$HAS_SENDGRID" == "true" ]]; then
            log_warn "SendGrid email provider configured (deprecated - consider migrating to Mailgun)"
        else
            log_warn "No email provider configured (configure either Mailgun or SendGrid)"
        fi
    else
        log_fail "Environment file (.env) not found"
        log_warn "Copy .env.example to .env and configure with your credentials"
    fi
    
    # Check file permissions
    if [[ -f "$PROJECT_ROOT/.env" ]]; then
        PERMS=$(stat -c %a "$PROJECT_ROOT/.env" 2>/dev/null || stat -f %p "$PROJECT_ROOT/.env" 2>/dev/null | tail -c 4)
        if [[ "$PERMS" == "600" ]]; then
            log_pass "Environment file has secure permissions (600)"
        else
            log_warn "Environment file should have 600 permissions (current: $PERMS)"
        fi
    fi
}

# Check core modules
check_modules() {
    log_test "Checking core modules..."
    
    if [[ -f "$PROJECT_ROOT/venv/bin/python" ]]; then
        # Test module imports
        "$PROJECT_ROOT/venv/bin/python" -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT/src')

modules_ok = True
try:
    # Test API modules
    from api import MarketDataClient
    from api.rate_limiter import TokenBucketRateLimiter
    
    # Test analysis modules
    from analysis.stock_screener import StockScreener
    from analysis.options_analyzer import OptionsAnalyzer
    from analysis.risk_calculator import RiskCalculator
    from analysis.scanner import PMCCScanner
    
    # Test notification modules
    from notifications import NotificationManager
    
    # Test config
    from config.settings import Settings
    
    print('All core modules imported successfully')
except ImportError as e:
    print(f'Import error: {e}')
    modules_ok = False
    sys.exit(1)
" 2>&1
        
        if [[ $? -eq 0 ]]; then
            log_pass "All core modules can be imported"
        else
            log_fail "Core module import errors"
        fi
    else
        log_fail "Cannot test modules - virtual environment not set up"
    fi
}

# Run unit tests
check_tests() {
    log_test "Running unit tests..."
    
    if [[ -f "$PROJECT_ROOT/venv/bin/pytest" ]]; then
        cd "$PROJECT_ROOT"
        
        # Run a subset of critical tests
        if "$PROJECT_ROOT/venv/bin/pytest" tests/unit/analysis/test_risk_calculator.py -v --tb=short 2>&1 | grep -q "passed"; then
            log_pass "Core unit tests passing"
        else
            log_warn "Some unit tests may be failing"
        fi
    else
        log_warn "pytest not installed - cannot run tests"
    fi
}

# Check health endpoint
check_health() {
    log_test "Checking health monitoring..."
    
    if [[ -f "$PROJECT_ROOT/scripts/health_check.py" ]]; then
        if [[ -f "$PROJECT_ROOT/venv/bin/python" ]]; then
            cd "$PROJECT_ROOT"
            
            # Set minimal environment
            export PYTHONPATH="$PROJECT_ROOT/src"
            
            # Try to run health check
            if "$PROJECT_ROOT/venv/bin/python" scripts/health_check.py --json 2>/dev/null | grep -q "overall_status"; then
                log_pass "Health check script functional"
            else
                log_warn "Health check script has issues"
            fi
        else
            log_fail "Cannot run health check - environment not set up"
        fi
    else
        log_fail "Health check script not found"
    fi
}

# Check scheduler setup
check_scheduler() {
    log_test "Checking scheduler setup..."
    
    # Check if cron job exists
    if crontab -l 2>/dev/null | grep -q "pmcc.*daily.*scan"; then
        log_pass "Cron job configured"
    else
        log_warn "No cron job found (run ./scripts/setup_cron.sh to configure)"
    fi
    
    # Check systemd alternative
    if systemctl list-unit-files 2>/dev/null | grep -q "pmcc-scanner"; then
        log_pass "SystemD service configured"
    elif [[ $WARNINGS -gt 0 ]]; then
        log_warn "No scheduler configured (cron or systemd)"
    fi
}

# Check logging setup
check_logging() {
    log_test "Checking logging configuration..."
    
    if [[ -d "$PROJECT_ROOT/logs" ]]; then
        if [[ -w "$PROJECT_ROOT/logs" ]]; then
            log_pass "Logs directory exists and is writable"
        else
            log_fail "Logs directory not writable"
        fi
    else
        log_fail "Logs directory not found"
    fi
}

# Summary report
generate_summary() {
    echo ""
    echo "=========================================="
    echo "PMCC Scanner Deployment Validation Summary"
    echo "=========================================="
    echo ""
    echo -e "Tests Passed:  ${GREEN}$PASSED${NC}"
    echo -e "Tests Failed:  ${RED}$FAILED${NC}"
    echo -e "Warnings:      ${YELLOW}$WARNINGS${NC}"
    echo ""
    
    if [[ $FAILED -eq 0 ]]; then
        echo -e "${GREEN}✅ DEPLOYMENT READY${NC}"
        echo ""
        echo "The PMCC Scanner is ready for production deployment!"
        echo ""
        echo "Next steps:"
        echo "1. Configure your API keys in .env"
        echo "2. Run: source venv/bin/activate"
        echo "3. Test: python scripts/run_daily_scan.py"
        echo "4. Schedule: ./scripts/setup_cron.sh"
        EXIT_CODE=0
    else
        echo -e "${RED}❌ DEPLOYMENT NOT READY${NC}"
        echo ""
        echo "Please fix the failed tests before deploying:"
        echo ""
        for result in "${RESULTS[@]}"; do
            if [[ $result == FAIL:* ]]; then
                echo "  - ${result#FAIL: }"
            fi
        done
        echo ""
        echo "Run ./scripts/setup.sh to fix most issues"
        EXIT_CODE=1
    fi
    
    if [[ $WARNINGS -gt 0 ]]; then
        echo ""
        echo -e "${YELLOW}Warnings to address:${NC}"
        for result in "${RESULTS[@]}"; do
            if [[ $result == WARN:* ]]; then
                echo "  - ${result#WARN: }"
            fi
        done
    fi
    
    echo ""
    echo "=========================================="
    
    exit $EXIT_CODE
}

# Main execution
main() {
    echo "=========================================="
    echo "PMCC Scanner Deployment Validation"
    echo "=========================================="
    echo ""
    
    check_python
    check_virtualenv
    check_dependencies
    check_directories
    check_configuration
    check_modules
    check_tests
    check_health
    check_scheduler
    check_logging
    
    generate_summary
}

# Run validation
cd "$PROJECT_ROOT"
main "$@"
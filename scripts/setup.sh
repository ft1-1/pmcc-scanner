#!/bin/bash
# PMCC Scanner Setup Script
# This script sets up the PMCC Scanner application with all dependencies

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "==========================================="
echo "PMCC Scanner Setup Script"
echo "==========================================="

# Function to check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        echo "Error: This script should not be run as root"
        echo "Please run as a regular user with sudo privileges"
        exit 1
    fi
}

# Function to check Python version
check_python() {
    echo "Checking Python version..."
    if ! command -v python3 &> /dev/null; then
        echo "Error: Python 3 is not installed"
        echo "Please install Python 3.8 or higher"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    echo "Found Python $PYTHON_VERSION"
    
    # Check minimum version
    if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)'; then
        echo "Error: Python 3.8 or higher is required"
        exit 1
    fi
}

# Function to create virtual environment
setup_virtualenv() {
    echo "Setting up Python virtual environment..."
    
    cd "$PROJECT_ROOT"
    
    if [[ ! -d "venv" ]]; then
        python3 -m venv venv
        echo "Virtual environment created"
    else
        echo "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
}

# Function to install dependencies
install_dependencies() {
    echo "Installing Python dependencies..."
    
    cd "$PROJECT_ROOT"
    
    # Ensure virtual environment is activated
    if [[ -z "${VIRTUAL_ENV:-}" ]]; then
        source venv/bin/activate
    fi
    
    # Install requirements
    pip install -r requirements.txt
    
    echo "Dependencies installed successfully"
}

# Function to setup environment file
setup_environment() {
    echo "Setting up environment configuration..."
    
    cd "$PROJECT_ROOT"
    
    if [[ ! -f ".env" ]]; then
        cp .env.example .env
        echo "Created .env file from template"
        echo "IMPORTANT: Please edit .env and add your API keys and configuration"
    else
        echo ".env file already exists"
    fi
    
    # Set proper permissions
    chmod 600 .env
}

# Function to create necessary directories
create_directories() {
    echo "Creating necessary directories..."
    
    cd "$PROJECT_ROOT"
    
    # Create logs directory
    mkdir -p logs
    
    # Create data directory for any cached data
    mkdir -p data
    
    echo "Directories created"
}

# Function to validate installation
validate_installation() {
    echo "Validating installation..."
    
    cd "$PROJECT_ROOT"
    
    # Ensure virtual environment is activated
    if [[ -z "${VIRTUAL_ENV:-}" ]]; then
        source venv/bin/activate
    fi
    
    # Run a simple import test
    python3 -c "
import sys
import importlib

required_modules = [
    'aiohttp',
    'pandas',
    'numpy',
    'pydantic',
    'requests',
    'httpx',
    'tenacity',
    'twilio',
    'sendgrid',
    'apscheduler',
    'structlog',
    'pytest'
]

failed = []
for module in required_modules:
    try:
        importlib.import_module(module.split('.')[0])
        print(f'✓ {module}')
    except ImportError:
        failed.append(module)
        print(f'✗ {module}')

if failed:
    print(f'\\nError: Failed to import {len(failed)} modules')
    sys.exit(1)
else:
    print('\\nAll required modules imported successfully')
"
}

# Function to display next steps
show_next_steps() {
    echo ""
    echo "==========================================="
    echo "Setup Complete!"
    echo "==========================================="
    echo ""
    echo "Next steps:"
    echo "1. Edit .env file with your API keys and configuration"
    echo "2. Activate the virtual environment: source venv/bin/activate"
    echo "3. Run tests: pytest"
    echo "4. Run health check: python scripts/health_check.py"
    echo "5. Setup scheduling: ./scripts/setup_cron.sh or ./scripts/setup_systemd.sh"
    echo ""
    echo "For daily operation:"
    echo "- Manual run: python scripts/run_daily_scan.py"
    echo "- Scheduled: Configured via cron or systemd"
    echo ""
}

# Main execution
main() {
    check_root
    check_python
    setup_virtualenv
    install_dependencies
    setup_environment
    create_directories
    validate_installation
    show_next_steps
}

# Run main function
main "$@"
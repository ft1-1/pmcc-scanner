#!/bin/bash
"""
Setup script for systemd service and timer for PMCC Scanner.

This script creates and installs systemd service files for running
PMCC Scanner as a daemon or scheduled service.
"""

set -euo pipefail

# Configuration
SERVICE_NAME="pmcc-scanner"
USER="${PMCC_USER:-pmccuser}"
GROUP="${PMCC_GROUP:-pmccuser}"
PROJECT_ROOT="${PMCC_PROJECT_ROOT:-/opt/pmcc-scanner}"
PYTHON_PATH="${PMCC_PYTHON_PATH:-/usr/bin/python3}"
LOG_LEVEL="${PMCC_LOG_LEVEL:-INFO}"
ENVIRONMENT="${PMCC_ENVIRONMENT:-production}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (or with sudo)"
        exit 1
    fi
}

# Check if user exists
check_user() {
    if ! id "$USER" &>/dev/null; then
        log_warn "User $USER does not exist. Creating user..."
        useradd --system --home "$PROJECT_ROOT" --shell /bin/bash "$USER"
        log_info "Created user: $USER"
    fi
}

# Check if project directory exists
check_project_dir() {
    if [[ ! -d "$PROJECT_ROOT" ]]; then
        log_error "Project directory $PROJECT_ROOT does not exist"
        log_error "Please ensure PMCC Scanner is installed at this location"
        exit 1
    fi
    
    if [[ ! -f "$PROJECT_ROOT/scripts/run_daily_scan.py" ]]; then
        log_error "PMCC Scanner scripts not found in $PROJECT_ROOT"
        exit 1
    fi
}

# Create systemd service file for daemon mode
create_daemon_service() {
    log_info "Creating systemd service file for daemon mode..."
    
    cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=PMCC Scanner Daemon
Documentation=https://github.com/your-org/pmcc-scanner
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=60
StartLimitBurst=3

[Service]
Type=simple
User=$USER
Group=$GROUP
WorkingDirectory=$PROJECT_ROOT
Environment=PYTHONPATH=$PROJECT_ROOT/src
Environment=LOG_LEVEL=$LOG_LEVEL
Environment=ENVIRONMENT=$ENVIRONMENT
ExecStart=$PYTHON_PATH $PROJECT_ROOT/src/main.py --mode daemon
ExecReload=/bin/kill -HUP \$MAINPID
Restart=on-failure
RestartSec=10
TimeoutStartSec=60
TimeoutStopSec=30

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$PROJECT_ROOT

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

[Install]
WantedBy=multi-user.target
EOF

    log_info "Created daemon service file: /etc/systemd/system/${SERVICE_NAME}.service"
}

# Create systemd service file for one-shot scans
create_scan_service() {
    log_info "Creating systemd service file for scheduled scans..."
    
    cat > "/etc/systemd/system/${SERVICE_NAME}-scan.service" << EOF
[Unit]
Description=PMCC Scanner Daily Scan
Documentation=https://github.com/your-org/pmcc-scanner
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$USER
Group=$GROUP
WorkingDirectory=$PROJECT_ROOT
Environment=PYTHONPATH=$PROJECT_ROOT/src
Environment=LOG_LEVEL=$LOG_LEVEL
Environment=ENVIRONMENT=$ENVIRONMENT
ExecStart=$PYTHON_PATH $PROJECT_ROOT/scripts/run_daily_scan.py
TimeoutStartSec=3600
TimeoutStopSec=60

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$PROJECT_ROOT

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${SERVICE_NAME}-scan
EOF

    log_info "Created scan service file: /etc/systemd/system/${SERVICE_NAME}-scan.service"
}

# Create systemd timer for scheduled scans
create_timer() {
    local scan_time="${PMCC_SCAN_TIME:-09:30}"
    
    log_info "Creating systemd timer for scheduled scans..."
    
    cat > "/etc/systemd/system/${SERVICE_NAME}-scan.timer" << EOF
[Unit]
Description=PMCC Scanner Daily Scan Timer
Documentation=https://github.com/your-org/pmcc-scanner
Requires=${SERVICE_NAME}-scan.service

[Timer]
OnCalendar=Mon..Fri $scan_time
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
EOF

    log_info "Created timer file: /etc/systemd/system/${SERVICE_NAME}-scan.timer"
    log_info "Scheduled to run Monday-Friday at $scan_time"
}

# Create health check service
create_health_service() {
    log_info "Creating health check service..."
    
    cat > "/etc/systemd/system/${SERVICE_NAME}-health.service" << EOF
[Unit]
Description=PMCC Scanner Health Check
Documentation=https://github.com/your-org/pmcc-scanner

[Service]
Type=oneshot
User=$USER
Group=$GROUP
WorkingDirectory=$PROJECT_ROOT
Environment=PYTHONPATH=$PROJECT_ROOT/src
ExecStart=$PYTHON_PATH $PROJECT_ROOT/scripts/health_check.py --json
TimeoutStartSec=60
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${SERVICE_NAME}-health
EOF

    log_info "Created health check service: /etc/systemd/system/${SERVICE_NAME}-health.service"
}

# Create environment file template
create_env_template() {
    local env_file="$PROJECT_ROOT/.env.production"
    
    if [[ ! -f "$env_file" ]]; then
        log_info "Creating environment file template..."
        
        cat > "$env_file" << EOF
# PMCC Scanner Production Configuration
ENVIRONMENT=production

# MarketData API Configuration
MARKETDATA_API_TOKEN=your_api_token_here
MARKETDATA_BASE_URL=https://api.marketdata.app
MARKETDATA_TIMEOUT_SECONDS=30
MARKETDATA_REQUESTS_PER_MINUTE=100

# Notification Configuration
NOTIFICATION_WHATSAPP_ENABLED=true
NOTIFICATION_EMAIL_ENABLED=true

# Twilio/WhatsApp Settings
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_whatsapp_number
WHATSAPP_TO_NUMBERS=+1234567890,+0987654321

# Mailgun/Email Settings (preferred)
MAILGUN_API_KEY=your_mailgun_api_key
MAILGUN_DOMAIN=your_mailgun_domain.com
EMAIL_FROM=scanner@yourdomain.com
EMAIL_FROM_NAME=PMCC Scanner
EMAIL_TO=alerts@yourdomain.com

# SendGrid/Email Settings (backward compatibility - deprecated)
# SENDGRID_API_KEY=your_sendgrid_api_key

# Scan Configuration
SCAN_SCHEDULE_ENABLED=true
SCAN_TIME=09:30
SCAN_TIMEZONE=US/Eastern
SCAN_MAX_STOCKS_TO_SCREEN=100
SCAN_MAX_OPPORTUNITIES=25

# Logging Configuration
LOG_LEVEL=INFO
LOG_ENABLE_FILE_LOGGING=true
LOG_FILE=$PROJECT_ROOT/logs/pmcc_scanner.log
LOG_ENABLE_JSON_LOGGING=false

# Monitoring Configuration
MONITORING_HEALTH_CHECK_ENABLED=true
MONITORING_HEALTH_CHECK_PORT=8080
EOF

        chown "$USER:$GROUP" "$env_file"
        chmod 600 "$env_file"
        
        log_warn "Created environment template: $env_file"
        log_warn "Please edit this file with your actual configuration values!"
    else
        log_info "Environment file already exists: $env_file"
    fi
}

# Set correct permissions
set_permissions() {
    log_info "Setting file permissions..."
    
    # Make scripts executable
    chmod +x "$PROJECT_ROOT/scripts/"*.py
    chmod +x "$PROJECT_ROOT/scripts/"*.sh
    
    # Create and set ownership of directories
    mkdir -p "$PROJECT_ROOT"/{logs,data,tmp}
    chown -R "$USER:$GROUP" "$PROJECT_ROOT"/{logs,data,tmp,src}
    
    # Set permissions for log rotation
    if [[ -d "/etc/logrotate.d" ]]; then
        cat > "/etc/logrotate.d/$SERVICE_NAME" << EOF
$PROJECT_ROOT/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 $USER $GROUP
    postrotate
        systemctl reload $SERVICE_NAME || true
    endscript
}
EOF
        log_info "Created logrotate configuration"
    fi
}

# Reload systemd and enable services
setup_systemd() {
    log_info "Reloading systemd daemon..."
    systemctl daemon-reload
    
    # Enable timer by default (not daemon)
    log_info "Enabling scheduled scan timer..."
    systemctl enable "${SERVICE_NAME}-scan.timer"
    
    log_info "Service setup complete!"
    log_info ""
    log_info "Available commands:"
    log_info "  Start daemon:           systemctl start $SERVICE_NAME"
    log_info "  Stop daemon:            systemctl stop $SERVICE_NAME"
    log_info "  Enable daemon:          systemctl enable $SERVICE_NAME"
    log_info "  Start scan timer:       systemctl start ${SERVICE_NAME}-scan.timer"
    log_info "  Stop scan timer:        systemctl stop ${SERVICE_NAME}-scan.timer"
    log_info "  Run manual scan:        systemctl start ${SERVICE_NAME}-scan.service"
    log_info "  Check health:           systemctl start ${SERVICE_NAME}-health.service"
    log_info "  View logs:              journalctl -u $SERVICE_NAME -f"
    log_info "  View scan logs:         journalctl -u ${SERVICE_NAME}-scan -f"
}

# Create monitoring script
create_monitoring_script() {
    log_info "Creating monitoring script..."
    
    cat > "$PROJECT_ROOT/scripts/monitor.sh" << 'EOF'
#!/bin/bash
# PMCC Scanner monitoring script

SERVICE_NAME="pmcc-scanner"

case "${1:-status}" in
    status)
        echo "=== PMCC Scanner Status ==="
        systemctl is-active --quiet ${SERVICE_NAME}-scan.timer && echo "✅ Timer: Active" || echo "❌ Timer: Inactive"
        systemctl is-active --quiet ${SERVICE_NAME} && echo "✅ Daemon: Running" || echo "⏹️  Daemon: Stopped"
        
        echo ""
        echo "=== Recent Scan Activity ==="
        journalctl -u ${SERVICE_NAME}-scan --since "24 hours ago" --no-pager -q | tail -5
        
        echo ""
        echo "=== Health Check ==="
        systemctl start ${SERVICE_NAME}-health.service
        journalctl -u ${SERVICE_NAME}-health --since "1 minute ago" --no-pager -q | tail -1
        ;;
    
    logs)
        echo "=== Recent Logs ==="
        journalctl -u ${SERVICE_NAME}-scan --since "24 hours ago" --no-pager
        ;;
    
    health)
        systemctl start ${SERVICE_NAME}-health.service
        journalctl -u ${SERVICE_NAME}-health --since "1 minute ago" --no-pager -q
        ;;
    
    start-timer)
        systemctl start ${SERVICE_NAME}-scan.timer
        echo "Timer started"
        ;;
    
    stop-timer)
        systemctl stop ${SERVICE_NAME}-scan.timer
        echo "Timer stopped"
        ;;
    
    run-scan)
        echo "Running manual scan..."
        systemctl start ${SERVICE_NAME}-scan.service
        echo "Scan initiated. View logs with: journalctl -u ${SERVICE_NAME}-scan -f"
        ;;
    
    *)
        echo "Usage: $0 {status|logs|health|start-timer|stop-timer|run-scan}"
        exit 1
        ;;
esac
EOF

    chmod +x "$PROJECT_ROOT/scripts/monitor.sh"
    chown "$USER:$GROUP" "$PROJECT_ROOT/scripts/monitor.sh"
    
    log_info "Created monitoring script: $PROJECT_ROOT/scripts/monitor.sh"
}

# Main execution
main() {
    log_info "Setting up PMCC Scanner systemd services..."
    log_info "Project root: $PROJECT_ROOT"
    log_info "User: $USER"
    log_info "Environment: $ENVIRONMENT"
    
    check_root
    check_user
    check_project_dir
    
    create_daemon_service
    create_scan_service
    create_timer
    create_health_service
    create_env_template
    set_permissions
    create_monitoring_script
    setup_systemd
    
    log_info ""
    log_info "🎉 PMCC Scanner systemd setup complete!"
    log_info ""
    log_info "Next steps:"
    log_info "1. Edit $PROJECT_ROOT/.env.production with your configuration"
    log_info "2. Start the scan timer: systemctl start ${SERVICE_NAME}-scan.timer"
    log_info "3. Monitor with: $PROJECT_ROOT/scripts/monitor.sh"
    log_info ""
    log_info "The scanner will run Monday-Friday at the configured time."
}

# Run main function
main "$@"
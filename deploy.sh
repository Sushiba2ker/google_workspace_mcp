#!/bin/bash

# Google Workspace MCP Server Deployment Script
# This script helps deploy the MCP server to a VPS for production use

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="google-workspace-mcp"
APP_DIR="/opt/$APP_NAME"
SERVICE_NAME="$APP_NAME"
NGINX_SITE="$APP_NAME"
USER="mcp"

# Functions
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

install_dependencies() {
    print_status "Installing system dependencies..."
    
    # Update package list
    apt-get update
    
    # Install required packages
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        nginx \
        certbot \
        python3-certbot-nginx \
        ufw \
        curl \
        git \
        supervisor
    
    print_success "System dependencies installed"
}

create_user() {
    print_status "Creating application user..."
    
    if ! id "$USER" &>/dev/null; then
        useradd --system --shell /bin/bash --home-dir "$APP_DIR" --create-home "$USER"
        print_success "User '$USER' created"
    else
        print_warning "User '$USER' already exists"
    fi
}

setup_application() {
    print_status "Setting up application..."
    
    # Create application directory
    mkdir -p "$APP_DIR"
    
    # Copy application files
    if [ -d "$(pwd)" ]; then
        cp -r . "$APP_DIR/"
        chown -R "$USER:$USER" "$APP_DIR"
    else
        print_error "Please run this script from the application directory"
        exit 1
    fi
    
    # Create logs directory
    mkdir -p "$APP_DIR/logs"
    chown -R "$USER:$USER" "$APP_DIR/logs"
    
    # Install Python dependencies
    print_status "Installing Python dependencies..."
    cd "$APP_DIR"
    
    # Create virtual environment
    sudo -u "$USER" python3 -m venv venv
    
    # Install dependencies
    sudo -u "$USER" ./venv/bin/pip install --upgrade pip
    sudo -u "$USER" ./venv/bin/pip install -r requirements.txt || true
    
    # Install using pyproject.toml if requirements.txt doesn't exist
    if [ -f "pyproject.toml" ]; then
        sudo -u "$USER" ./venv/bin/pip install .
    fi
    
    print_success "Application setup completed"
}

setup_environment() {
    print_status "Setting up environment configuration..."
    
    # Create .env file if it doesn't exist
    if [ ! -f "$APP_DIR/.env" ]; then
        cp "$APP_DIR/.env.example" "$APP_DIR/.env"
        print_warning "Created .env file from example. Please edit it with your configuration."
    fi
    
    # Set proper permissions
    chown "$USER:$USER" "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
    
    print_success "Environment configuration setup completed"
}

setup_systemd_service() {
    print_status "Setting up systemd service..."
    
    cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF
[Unit]
Description=Google Workspace MCP Server
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/python main.py --transport streamable-http
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_DIR

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    
    print_success "Systemd service created and enabled"
}

setup_nginx() {
    print_status "Setting up Nginx reverse proxy..."
    
    # Remove default site
    rm -f /etc/nginx/sites-enabled/default
    
    # Create Nginx configuration
    cat > "/etc/nginx/sites-available/$NGINX_SITE" << 'EOF'
server {
    listen 80;
    server_name _;  # Replace with your domain
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    
    location / {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
EOF
    
    # Enable site
    ln -sf "/etc/nginx/sites-available/$NGINX_SITE" "/etc/nginx/sites-enabled/"
    
    # Test Nginx configuration
    nginx -t
    
    print_success "Nginx configuration created"
}

setup_firewall() {
    print_status "Setting up firewall..."
    
    # Reset UFW to defaults
    ufw --force reset
    
    # Set default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH
    ufw allow ssh
    
    # Allow HTTP and HTTPS
    ufw allow 'Nginx Full'
    
    # Enable firewall
    ufw --force enable
    
    print_success "Firewall configured"
}

start_services() {
    print_status "Starting services..."
    
    # Start and enable services
    systemctl start "$SERVICE_NAME"
    systemctl restart nginx
    
    # Check service status
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_success "MCP server is running"
    else
        print_error "Failed to start MCP server"
        systemctl status "$SERVICE_NAME"
        exit 1
    fi
    
    if systemctl is-active --quiet nginx; then
        print_success "Nginx is running"
    else
        print_error "Failed to start Nginx"
        systemctl status nginx
        exit 1
    fi
}

setup_ssl() {
    print_status "Setting up SSL certificate..."
    
    read -p "Enter your domain name (or press Enter to skip SSL setup): " DOMAIN
    
    if [ -n "$DOMAIN" ]; then
        # Update Nginx configuration with domain
        sed -i "s/server_name _;/server_name $DOMAIN;/" "/etc/nginx/sites-available/$NGINX_SITE"
        systemctl reload nginx
        
        # Get SSL certificate
        certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email admin@"$DOMAIN"
        
        print_success "SSL certificate installed for $DOMAIN"
    else
        print_warning "SSL setup skipped. You can run 'certbot --nginx' later to set up SSL."
    fi
}

show_completion_info() {
    print_success "Deployment completed successfully!"
    echo
    echo "=== Deployment Information ==="
    echo "Application Directory: $APP_DIR"
    echo "Service Name: $SERVICE_NAME"
    echo "User: $USER"
    echo
    echo "=== Next Steps ==="
    echo "1. Edit the configuration file: $APP_DIR/.env"
    echo "2. Add your Google OAuth credentials"
    echo "3. Update WORKSPACE_MCP_BASE_URI with your domain/IP"
    echo "4. Restart the service: sudo systemctl restart $SERVICE_NAME"
    echo
    echo "=== Useful Commands ==="
    echo "Check service status: sudo systemctl status $SERVICE_NAME"
    echo "View logs: sudo journalctl -u $SERVICE_NAME -f"
    echo "Restart service: sudo systemctl restart $SERVICE_NAME"
    echo "Check Nginx: sudo nginx -t && sudo systemctl reload nginx"
    echo
    echo "=== MCP Server URL ==="
    if [ -n "$DOMAIN" ]; then
        echo "https://$DOMAIN/mcp"
    else
        echo "http://$(curl -s ifconfig.me)/mcp"
    fi
}

# Main deployment process
main() {
    print_status "Starting Google Workspace MCP Server deployment..."
    
    check_root
    install_dependencies
    create_user
    setup_application
    setup_environment
    setup_systemd_service
    setup_nginx
    setup_firewall
    start_services
    setup_ssl
    show_completion_info
}

# Run main function
main "$@"

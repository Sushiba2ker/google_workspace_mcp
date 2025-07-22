# Google Workspace MCP Server - Production Deployment Guide

This guide will help you deploy the Google Workspace MCP Server to a VPS for production use with Claude Desktop and Claude Web.

## 🚀 Quick Start

### Prerequisites

- VPS with Ubuntu 20.04+ or similar Linux distribution
- Domain name (optional but recommended for HTTPS)
- Google Cloud Console project with OAuth 2.0 credentials
- Root or sudo access to the VPS

### 1. Automated Deployment (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd google_workspace_mcp

# Make deployment script executable
chmod +x deploy.sh

# Run deployment script
sudo ./deploy.sh
```

The script will:
- Install all dependencies
- Create system user and directories
- Setup systemd service
- Configure Nginx reverse proxy
- Setup firewall rules
- Optionally configure SSL with Let's Encrypt

### 2. Manual Configuration

After deployment, edit the configuration:

```bash
sudo nano /opt/google-workspace-mcp/.env
```

Update these essential settings:

```env
# Your VPS domain or IP
WORKSPACE_MCP_BASE_URI=https://your-domain.com

# Google OAuth credentials
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here

# Security (generate a strong random string)
JWT_SECRET=your_secure_jwt_secret_here

# Multi-account settings
MULTI_ACCOUNT_ENABLED=true
ALLOWED_GOOGLE_ACCOUNTS=user1@gmail.com,user2@company.com
```

### 3. Setup Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable required APIs:
   - Gmail API
   - Google Drive API
   - Google Calendar API
   - Google Docs API
   - Google Sheets API
4. Create OAuth 2.0 credentials:
   - Application type: Web application
   - Authorized redirect URIs: `https://your-domain.com/oauth2callback`

### 4. Generate Credentials File

```bash
cd /opt/google-workspace-mcp
sudo -u mcp ./venv/bin/python setup_credentials.py
```

### 5. Start the Service

```bash
sudo systemctl restart google-workspace-mcp
sudo systemctl status google-workspace-mcp
```

## 🐳 Docker Deployment

### Using Docker Compose

1. Copy environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your configuration

3. Start services:
```bash
docker-compose up -d
```

4. With Nginx proxy:
```bash
docker-compose --profile nginx up -d
```

5. With monitoring:
```bash
docker-compose --profile monitoring up -d
```

## 🔧 Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port | `8000` |
| `WORKSPACE_MCP_BASE_URI` | Base URI for server | `http://localhost` |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | Required |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | Required |
| `MULTI_ACCOUNT_ENABLED` | Enable multi-account support | `true` |
| `ALLOWED_GOOGLE_ACCOUNTS` | Comma-separated list of allowed emails | Empty (all allowed) |
| `JWT_SECRET` | JWT signing secret | Required in production |
| `CORS_ORIGINS` | Allowed CORS origins | `https://claude.ai` |

### Multi-Account Configuration

To restrict access to specific Google accounts:

```env
MULTI_ACCOUNT_ENABLED=true
ALLOWED_GOOGLE_ACCOUNTS=admin@company.com,user@company.com
```

For account-specific tool restrictions:

```env
ACCOUNT_CONFIGS={"admin@company.com": {"tools": ["gmail", "drive", "calendar"]}, "user@company.com": {"tools": ["gmail"]}}
```

## 🌐 Claude Web Integration

### Adding MCP Server to Claude Web

1. Go to Claude Web settings
2. Click "Add custom connector"
3. Enter:
   - **Name**: `Google Workspace MCP`
   - **Remote MCP server URL**: `https://your-domain.com/mcp`

### Server URL Format

- **With domain**: `https://your-domain.com/mcp`
- **With IP**: `http://your-vps-ip:8000/mcp`
- **Local development**: `http://localhost:8000/mcp`

## 🖥️ Claude Desktop Integration

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "uvx",
      "args": ["--from", "https://your-domain.com/mcp", "workspace-mcp"]
    }
  }
}
```

Or for direct connection:

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "python",
      "args": ["-m", "workspace_mcp"],
      "env": {
        "WORKSPACE_MCP_BASE_URI": "https://your-domain.com"
      }
    }
  }
}
```

## 🔒 Security Considerations

### SSL/HTTPS Setup

For production, always use HTTPS:

```bash
# Using Let's Encrypt (automated in deploy.sh)
sudo certbot --nginx -d your-domain.com

# Or manually configure SSL
sudo nano /etc/nginx/sites-available/google-workspace-mcp
```

### Firewall Configuration

```bash
# Allow only necessary ports
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### Rate Limiting

Configure in `.env`:

```env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60
```

## 📊 Monitoring and Logging

### View Logs

```bash
# Service logs
sudo journalctl -u google-workspace-mcp -f

# Application logs
sudo tail -f /opt/google-workspace-mcp/logs/mcp_server.log

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Health Check

```bash
curl https://your-domain.com/health
```

### Prometheus Monitoring (Optional)

Enable monitoring with Docker Compose:

```bash
docker-compose --profile monitoring up -d
```

Access Prometheus at `http://your-domain.com:9090`

## 🛠️ Troubleshooting

### Common Issues

1. **Service won't start**:
   ```bash
   sudo systemctl status google-workspace-mcp
   sudo journalctl -u google-workspace-mcp -n 50
   ```

2. **OAuth callback errors**:
   - Check redirect URIs in Google Cloud Console
   - Verify `WORKSPACE_MCP_BASE_URI` in `.env`

3. **Permission denied**:
   ```bash
   sudo chown -R mcp:mcp /opt/google-workspace-mcp
   ```

4. **Port already in use**:
   ```bash
   sudo netstat -tlnp | grep :8000
   sudo systemctl stop google-workspace-mcp
   ```

### Debug Mode

Enable debug logging:

```env
LOG_LEVEL=DEBUG
```

## 🔄 Updates and Maintenance

### Update Application

```bash
cd /opt/google-workspace-mcp
sudo -u mcp git pull
sudo -u mcp ./venv/bin/pip install -r requirements.txt
sudo systemctl restart google-workspace-mcp
```

### Backup Configuration

```bash
sudo cp /opt/google-workspace-mcp/.env /opt/google-workspace-mcp/.env.backup
sudo tar -czf mcp-backup-$(date +%Y%m%d).tar.gz /opt/google-workspace-mcp/credentials /opt/google-workspace-mcp/.env
```

## 📞 Support

For issues and questions:
- Check the logs first
- Verify Google Cloud Console configuration
- Ensure all environment variables are set correctly
- Test with a simple health check: `curl https://your-domain.com/health`

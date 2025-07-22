# 🚀 Quick Setup Guide - Google Workspace MCP Server

## For VPS Production Deployment

### 1. Automated Setup (Recommended)

```bash
# On your VPS
git clone <your-repo-url>
cd google_workspace_mcp
chmod +x deploy.sh
sudo ./deploy.sh
```

### 2. Configure Environment

```bash
# Edit configuration
sudo nano /opt/google-workspace-mcp/.env

# Essential settings:
WORKSPACE_MCP_BASE_URI=https://your-domain.com  # Your VPS domain/IP
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
JWT_SECRET=your_secure_random_string_here
```

### 3. Generate JWT Secret

```bash
cd /opt/google-workspace-mcp
python3 generate_secret.py
# Copy the generated secret to your .env file
```

### 4. Setup Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create OAuth 2.0 credentials
3. Add redirect URI: `https://your-domain.com/oauth2callback`

### 5. Create Credentials File

```bash
cd /opt/google-workspace-mcp
sudo -u mcp ./venv/bin/python setup_credentials.py
```

### 6. Start Service

```bash
sudo systemctl restart google-workspace-mcp
sudo systemctl status google-workspace-mcp
```

## For Claude Web Integration

### Add Custom Connector

1. Go to Claude Web settings
2. Click "Add custom connector"
3. Enter:
   - **Name**: `Google Workspace MCP`
   - **Remote MCP server URL**: `https://your-domain.com/mcp`

## For Claude Desktop Integration

Add to your Claude Desktop config:

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

## Multi-Account Setup

To allow specific Google accounts:

```env
MULTI_ACCOUNT_ENABLED=true
ALLOWED_GOOGLE_ACCOUNTS=user1@gmail.com,user2@company.com,admin@domain.com
```

## Health Check

Test your deployment:

```bash
curl https://your-domain.com/health
```

## Troubleshooting

### Check logs:
```bash
sudo journalctl -u google-workspace-mcp -f
```

### Restart service:
```bash
sudo systemctl restart google-workspace-mcp
```

### Check Nginx:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Docker Alternative

```bash
# Copy environment file
cp .env.example .env
# Edit .env with your settings
nano .env

# Start with Docker Compose
docker-compose up -d

# With Nginx proxy
docker-compose --profile nginx up -d
```

## Important URLs

- **Health Check**: `https://your-domain.com/health`
- **MCP Endpoint**: `https://your-domain.com/mcp`
- **OAuth Callback**: `https://your-domain.com/oauth2callback`

## Security Notes

- Always use HTTPS in production
- Generate a strong JWT secret
- Restrict allowed Google accounts if needed
- Keep your Google OAuth credentials secure
- Regularly update the server

## Support

Check `DEPLOYMENT.md` for detailed instructions and troubleshooting.

#!/usr/bin/env python3
"""
Setup Google OAuth credentials from environment variables
This script creates client_secrets.json from environment variables for production deployment
"""

import os
import json
import sys
from pathlib import Path
from core.config import config

def create_client_secrets():
    """Create client_secrets.json from environment variables"""
    
    if not config.GOOGLE_CLIENT_ID or not config.GOOGLE_CLIENT_SECRET:
        print("ERROR: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in environment variables")
        print("Please set these in your .env file or environment")
        return False
    
    # OAuth redirect URIs
    redirect_uris = [
        f"{config.WORKSPACE_MCP_BASE_URI}:{config.PORT}/oauth2callback",
        "http://localhost:8000/oauth2callback",  # Fallback for development
    ]
    
    # Create client_secrets.json structure
    client_secrets = {
        "installed": {
            "client_id": config.GOOGLE_CLIENT_ID,
            "client_secret": config.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": redirect_uris
        }
    }
    
    # Write to file
    client_secrets_path = Path(__file__).parent / "client_secrets.json"
    
    try:
        with open(client_secrets_path, 'w') as f:
            json.dump(client_secrets, f, indent=2)
        
        print(f"✅ Created client_secrets.json at {client_secrets_path}")
        print(f"   Client ID: {config.GOOGLE_CLIENT_ID[:20]}...")
        print(f"   Redirect URIs: {redirect_uris}")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to create client_secrets.json: {e}")
        return False

def validate_credentials():
    """Validate that credentials file exists and is valid"""
    
    client_secrets_path = Path(__file__).parent / "client_secrets.json"
    
    if not client_secrets_path.exists():
        print("ERROR: client_secrets.json does not exist")
        return False
    
    try:
        with open(client_secrets_path, 'r') as f:
            data = json.load(f)
        
        required_fields = ['client_id', 'client_secret', 'auth_uri', 'token_uri']
        installed = data.get('installed', {})
        
        for field in required_fields:
            if not installed.get(field):
                print(f"ERROR: Missing required field '{field}' in client_secrets.json")
                return False
        
        print("✅ client_secrets.json is valid")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to validate client_secrets.json: {e}")
        return False

def main():
    """Main function"""
    print("🔧 Google Workspace MCP - Credentials Setup")
    print("=" * 50)
    
    # Show current configuration
    print(f"Environment: {config.ENVIRONMENT}")
    print(f"Base URI: {config.WORKSPACE_MCP_BASE_URI}")
    print(f"Port: {config.PORT}")
    print()
    
    # Create credentials file
    if create_client_secrets():
        print()
        if validate_credentials():
            print("✅ Credentials setup completed successfully!")
            
            # Show next steps
            print()
            print("📋 Next Steps:")
            print("1. Make sure your Google Cloud Console OAuth app is configured with these redirect URIs:")
            for uri in [f"{config.WORKSPACE_MCP_BASE_URI}:{config.PORT}/oauth2callback"]:
                print(f"   - {uri}")
            print()
            print("2. Start the MCP server:")
            print("   python main.py --transport streamable-http")
            print()
            print("3. For Claude Web integration, use this MCP server URL:")
            print(f"   {config.MCP_SERVER_URL}")
            
        else:
            sys.exit(1)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()

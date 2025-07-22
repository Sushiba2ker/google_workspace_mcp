"""
Configuration management for Google Workspace MCP Server
Handles environment variables, multi-account settings, and production deployment
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

# Try to load python-dotenv if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

class Config:
    """Configuration class for Google Workspace MCP Server"""
    
    def __init__(self):
        self._load_config()
    
    def _load_config(self):
        """Load configuration from environment variables"""
        
        # Server Configuration
        self.PORT = int(os.getenv("PORT", os.getenv("WORKSPACE_MCP_PORT", 8000)))
        self.WORKSPACE_MCP_PORT = self.PORT
        self.WORKSPACE_MCP_BASE_URI = os.getenv("WORKSPACE_MCP_BASE_URI", "http://localhost")
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        
        # Google OAuth Configuration
        self.GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
        self.GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
        self.USER_GOOGLE_EMAIL = os.getenv("USER_GOOGLE_EMAIL", "")
        
        # Multi-account Configuration
        self.MULTI_ACCOUNT_ENABLED = os.getenv("MULTI_ACCOUNT_ENABLED", "true").lower() == "true"
        allowed_accounts_str = os.getenv("ALLOWED_GOOGLE_ACCOUNTS", "")
        self.ALLOWED_GOOGLE_ACCOUNTS = [
            email.strip() for email in allowed_accounts_str.split(",") 
            if email.strip()
        ] if allowed_accounts_str else []
        
        # Account-specific configurations
        account_configs_str = os.getenv("ACCOUNT_CONFIGS", "{}")
        try:
            self.ACCOUNT_CONFIGS = json.loads(account_configs_str)
        except json.JSONDecodeError:
            logger.warning("Invalid ACCOUNT_CONFIGS JSON, using empty dict")
            self.ACCOUNT_CONFIGS = {}
        
        # Security Configuration
        self.JWT_SECRET = os.getenv("JWT_SECRET", "default_secret_change_in_production")
        self.SESSION_TIMEOUT_HOURS = int(os.getenv("SESSION_TIMEOUT_HOURS", 24))
        self.CORS_ENABLED = os.getenv("CORS_ENABLED", "true").lower() == "true"
        cors_origins_str = os.getenv("CORS_ORIGINS", "")
        self.CORS_ORIGINS = [
            origin.strip() for origin in cors_origins_str.split(",") 
            if origin.strip()
        ] if cors_origins_str else ["*"]
        
        # Logging Configuration
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
        self.FILE_LOGGING_ENABLED = os.getenv("FILE_LOGGING_ENABLED", "true").lower() == "true"
        self.LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "logs/mcp_server.log")
        
        # SSL/TLS Configuration
        self.SSL_ENABLED = os.getenv("SSL_ENABLED", "false").lower() == "true"
        self.SSL_CERT_PATH = os.getenv("SSL_CERT_PATH", "")
        self.SSL_KEY_PATH = os.getenv("SSL_KEY_PATH", "")
        
        # Proxy Configuration
        self.BEHIND_PROXY = os.getenv("BEHIND_PROXY", "false").lower() == "true"
        self.PROXY_HEADERS = os.getenv("PROXY_HEADERS", "true").lower() == "true"
        
        # Rate Limiting
        self.RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
        self.RATE_LIMIT_REQUESTS_PER_MINUTE = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", 60))
        
        # Claude Web Integration
        self.MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", f"{self.WORKSPACE_MCP_BASE_URI}:{self.PORT}/mcp")
        self.MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", "Google Workspace MCP")
        self.MCP_SERVER_DESCRIPTION = os.getenv("MCP_SERVER_DESCRIPTION", "Google Workspace integration for Claude")
        
        # Tools Configuration
        default_tools_str = os.getenv("DEFAULT_TOOLS", "gmail,drive,calendar,docs,sheets")
        self.DEFAULT_TOOLS = [
            tool.strip() for tool in default_tools_str.split(",") 
            if tool.strip()
        ] if default_tools_str else []
        
        # Tool-specific configurations
        self.GMAIL_MAX_RESULTS = int(os.getenv("GMAIL_MAX_RESULTS", 50))
        self.DRIVE_MAX_RESULTS = int(os.getenv("DRIVE_MAX_RESULTS", 100))
        self.CALENDAR_MAX_RESULTS = int(os.getenv("CALENDAR_MAX_RESULTS", 50))
        
        # Database Configuration (optional)
        self.DATABASE_URL = os.getenv("DATABASE_URL", "")
        
        # Monitoring Configuration
        self.HEALTH_CHECK_ENABLED = os.getenv("HEALTH_CHECK_ENABLED", "true").lower() == "true"
        self.METRICS_ENABLED = os.getenv("METRICS_ENABLED", "false").lower() == "true"
        self.PROMETHEUS_ENABLED = os.getenv("PROMETHEUS_ENABLED", "false").lower() == "true"
        self.PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", 9090))
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENVIRONMENT.lower() == "production"
    
    def is_account_allowed(self, email: str) -> bool:
        """Check if a Google account is allowed to use the service"""
        if not self.MULTI_ACCOUNT_ENABLED:
            return True
        
        if not self.ALLOWED_GOOGLE_ACCOUNTS:
            return True  # No restrictions if list is empty
        
        return email.lower() in [account.lower() for account in self.ALLOWED_GOOGLE_ACCOUNTS]
    
    def get_account_config(self, email: str) -> Dict[str, Any]:
        """Get configuration for a specific account"""
        return self.ACCOUNT_CONFIGS.get(email, {})
    
    def get_account_tools(self, email: str) -> List[str]:
        """Get allowed tools for a specific account"""
        account_config = self.get_account_config(email)
        return account_config.get("tools", self.DEFAULT_TOOLS)
    
    def get_account_scopes(self, email: str) -> List[str]:
        """Get OAuth scopes for a specific account"""
        account_config = self.get_account_config(email)
        return account_config.get("scopes", [])
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_level = getattr(logging, self.LOG_LEVEL, logging.INFO)
        
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Setup file logging if enabled
        if self.FILE_LOGGING_ENABLED:
            try:
                log_file_path = Path(self.LOG_FILE_PATH)
                log_file_path.parent.mkdir(parents=True, exist_ok=True)
                
                file_handler = logging.FileHandler(log_file_path, mode='a')
                file_handler.setLevel(logging.DEBUG)
                
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(process)d - %(threadName)s '
                    '[%(module)s.%(funcName)s:%(lineno)d] - %(message)s'
                )
                file_handler.setFormatter(file_formatter)
                
                root_logger = logging.getLogger()
                root_logger.addHandler(file_handler)
                
                logger.info(f"File logging configured to: {log_file_path}")
            except Exception as e:
                logger.error(f"Failed to setup file logging: {e}")
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        if self.is_production():
            if not self.GOOGLE_CLIENT_ID or self.GOOGLE_CLIENT_ID == "your_google_client_id_here":
                errors.append("GOOGLE_CLIENT_ID must be set in production")
            
            if not self.GOOGLE_CLIENT_SECRET or self.GOOGLE_CLIENT_SECRET == "your_google_client_secret_here":
                errors.append("GOOGLE_CLIENT_SECRET must be set in production")
            
            if self.JWT_SECRET == "default_secret_change_in_production":
                errors.append("JWT_SECRET must be changed in production")
            
            if self.SSL_ENABLED and (not self.SSL_CERT_PATH or not self.SSL_KEY_PATH):
                errors.append("SSL_CERT_PATH and SSL_KEY_PATH must be set when SSL is enabled")
        
        return errors
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get server information for health checks and debugging"""
        return {
            "environment": self.ENVIRONMENT,
            "port": self.PORT,
            "base_uri": self.WORKSPACE_MCP_BASE_URI,
            "multi_account_enabled": self.MULTI_ACCOUNT_ENABLED,
            "allowed_accounts_count": len(self.ALLOWED_GOOGLE_ACCOUNTS),
            "default_tools": self.DEFAULT_TOOLS,
            "ssl_enabled": self.SSL_ENABLED,
            "cors_enabled": self.CORS_ENABLED,
            "rate_limit_enabled": self.RATE_LIMIT_ENABLED,
            "mcp_server_url": self.MCP_SERVER_URL
        }

# Global configuration instance
config = Config()

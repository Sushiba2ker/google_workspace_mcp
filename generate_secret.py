#!/usr/bin/env python3
"""
Generate secure JWT secret for Google Workspace MCP Server
"""

import secrets
import string

def generate_jwt_secret(length=64):
    """Generate a secure random JWT secret"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

if __name__ == "__main__":
    secret = generate_jwt_secret()
    print("Generated JWT Secret:")
    print(secret)
    print()
    print("Add this to your .env file:")
    print(f"JWT_SECRET={secret}")

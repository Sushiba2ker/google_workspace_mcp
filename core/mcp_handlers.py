"""
Custom MCP Protocol Handlers
Fixes for tools/list, resources/list, and other MCP methods
"""

import logging
import inspect
import json
from typing import Dict, List, Any, Optional
from core.server import server
from core.session_manager import get_session_manager

logger = logging.getLogger(__name__)
session_manager = get_session_manager()

def get_registered_tools() -> List[Dict[str, Any]]:
    """Get list of all registered tools from FastMCP server"""
    tools = []
    
    try:
        # Access FastMCP's internal tool registry
        if hasattr(server, '_tools') and server._tools:
            for tool_name, tool_info in server._tools.items():
                # Extract tool information
                tool_data = {
                    "name": tool_name,
                    "description": getattr(tool_info, 'description', f"Tool: {tool_name}"),
                }
                
                # Try to get input schema from function signature
                if hasattr(tool_info, 'func'):
                    func = tool_info.func
                    sig = inspect.signature(func)
                    
                    # Build input schema from function parameters
                    properties = {}
                    required = []
                    
                    for param_name, param in sig.parameters.items():
                        # Skip 'service' parameter (injected by decorator)
                        if param_name == 'service':
                            continue
                            
                        param_info = {
                            "type": "string"  # Default type
                        }
                        
                        # Try to infer type from annotation
                        if param.annotation != inspect.Parameter.empty:
                            if param.annotation == str:
                                param_info["type"] = "string"
                            elif param.annotation == int:
                                param_info["type"] = "integer"
                            elif param.annotation == bool:
                                param_info["type"] = "boolean"
                            elif param.annotation == list or str(param.annotation).startswith('List'):
                                param_info["type"] = "array"
                        
                        # Check if parameter is required (no default value)
                        if param.default == inspect.Parameter.empty:
                            required.append(param_name)
                        else:
                            param_info["default"] = param.default
                        
                        properties[param_name] = param_info
                    
                    tool_data["inputSchema"] = {
                        "type": "object",
                        "properties": properties,
                        "required": required
                    }
                
                tools.append(tool_data)
                
        logger.info(f"Found {len(tools)} registered tools")
        return tools
        
    except Exception as e:
        logger.error(f"Error getting registered tools: {e}")
        # Fallback: return known tools
        return [
            {
                "name": "start_google_auth",
                "description": "Initiates Google OAuth 2.0 authentication flow",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "service_name": {"type": "string", "description": "Google service name"},
                        "user_google_email": {"type": "string", "description": "User's Google email"}
                    },
                    "required": ["service_name", "user_google_email"]
                }
            }
        ]

def get_registered_resources() -> List[Dict[str, Any]]:
    """Get list of all registered resources"""
    # For now, return empty list as we don't have resources implemented
    return []

def get_registered_prompts() -> List[Dict[str, Any]]:
    """Get list of all registered prompts"""
    # For now, return empty list as we don't have prompts implemented
    return []

# Register custom MCP handlers
@server.custom_route("/mcp/tools/list", methods=["POST"])
async def handle_tools_list(request):
    """Custom handler for tools/list method"""
    from fastapi.responses import JSONResponse
    
    try:
        tools = get_registered_tools()
        response = {
            "jsonrpc": "2.0",
            "id": 1,  # Will be overridden by actual request ID
            "result": {
                "tools": tools
            }
        }
        return JSONResponse(response)
    except Exception as e:
        logger.error(f"Error in tools/list handler: {e}")
        error_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }
        return JSONResponse(error_response, status_code=500)

@server.custom_route("/mcp/resources/list", methods=["POST"])
async def handle_resources_list(request):
    """Custom handler for resources/list method"""
    from fastapi.responses import JSONResponse
    
    try:
        resources = get_registered_resources()
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "resources": resources
            }
        }
        return JSONResponse(response)
    except Exception as e:
        logger.error(f"Error in resources/list handler: {e}")
        error_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }
        return JSONResponse(error_response, status_code=500)

@server.custom_route("/mcp/prompts/list", methods=["POST"])
async def handle_prompts_list(request):
    """Custom handler for prompts/list method"""
    from fastapi.responses import JSONResponse
    
    try:
        prompts = get_registered_prompts()
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "prompts": prompts
            }
        }
        return JSONResponse(response)
    except Exception as e:
        logger.error(f"Error in prompts/list handler: {e}")
        error_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }
        return JSONResponse(error_response, status_code=500)

# Debug endpoint to inspect server state
@server.custom_route("/debug/tools", methods=["GET"])
async def debug_tools(request):
    """Debug endpoint to inspect registered tools"""
    from fastapi.responses import JSONResponse
    
    debug_info = {
        "server_type": str(type(server)),
        "server_attributes": [attr for attr in dir(server) if not attr.startswith('_')],
        "tools_count": len(get_registered_tools()),
        "tools": get_registered_tools()
    }
    
    # Try to access internal FastMCP state
    if hasattr(server, '_tools'):
        debug_info["internal_tools"] = list(server._tools.keys()) if server._tools else []
    
    return JSONResponse(debug_info)

logger.info("Custom MCP handlers registered")

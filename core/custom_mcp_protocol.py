"""
Complete Custom MCP Protocol Implementation
Replaces FastMCP's buggy MCP protocol handlers to achieve 100% HTTP mode functionality
"""

import json
import logging
import inspect
import asyncio
from typing import Dict, List, Any, Optional, Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from core.server import server
from core.session_manager import get_session_manager

logger = logging.getLogger(__name__)
session_manager = get_session_manager()

class CustomMCPProtocol:
    """Custom MCP Protocol Implementation"""
    
    def __init__(self):
        self.tools_registry: Dict[str, Callable] = {}
        self.resources_registry: Dict[str, Callable] = {}
        self.prompts_registry: Dict[str, Callable] = {}
        self._discover_tools()
    
    def _discover_tools(self):
        """Discover tools from FastMCP server"""
        try:
            # Access FastMCP's internal tool registry
            if hasattr(server, '_tools') and server._tools:
                for tool_name, tool_info in server._tools.items():
                    if hasattr(tool_info, 'func'):
                        self.tools_registry[tool_name] = tool_info.func
                        logger.info(f"Discovered tool: {tool_name}")
            
            # Also check for tools in server attributes
            for attr_name in dir(server):
                attr = getattr(server, attr_name)
                if hasattr(attr, '__mcp_tool__'):
                    self.tools_registry[attr_name] = attr
                    logger.info(f"Discovered tool via attribute: {attr_name}")
            
            logger.info(f"Total tools discovered: {len(self.tools_registry)}")
            
        except Exception as e:
            logger.error(f"Error discovering tools: {e}")
    
    def get_tools_list(self) -> List[Dict[str, Any]]:
        """Get list of available tools with proper schema"""
        tools = []
        
        for tool_name, tool_func in self.tools_registry.items():
            try:
                # Get function signature
                sig = inspect.signature(tool_func)
                
                # Build input schema
                properties = {}
                required = []
                
                for param_name, param in sig.parameters.items():
                    # Skip special parameters
                    if param_name in ['service', 'mcp_session_id']:
                        continue
                    
                    param_info = {
                        "type": "string",
                        "description": f"Parameter: {param_name}"
                    }
                    
                    # Infer type from annotation
                    if param.annotation != inspect.Parameter.empty:
                        if param.annotation == str:
                            param_info["type"] = "string"
                        elif param.annotation == int:
                            param_info["type"] = "integer"
                        elif param.annotation == bool:
                            param_info["type"] = "boolean"
                        elif param.annotation == list or str(param.annotation).startswith('List'):
                            param_info["type"] = "array"
                    
                    # Check if required
                    if param.default == inspect.Parameter.empty:
                        required.append(param_name)
                    
                    properties[param_name] = param_info
                
                # Get description from docstring
                description = tool_func.__doc__ or f"Tool: {tool_name}"
                if description:
                    description = description.strip().split('\n')[0]  # First line only
                
                tool_data = {
                    "name": tool_name,
                    "description": description,
                    "inputSchema": {
                        "type": "object",
                        "properties": properties,
                        "required": required
                    }
                }
                
                tools.append(tool_data)
                
            except Exception as e:
                logger.error(f"Error processing tool {tool_name}: {e}")
                # Add basic tool info as fallback
                tools.append({
                    "name": tool_name,
                    "description": f"Tool: {tool_name}",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                })
        
        return tools
    
    def get_resources_list(self) -> List[Dict[str, Any]]:
        """Get list of available resources"""
        # For now, return empty list as we don't have resources implemented
        return []
    
    def get_prompts_list(self) -> List[Dict[str, Any]]:
        """Get list of available prompts"""
        # For now, return empty list as we don't have prompts implemented
        return []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any], session_id: Optional[str] = None) -> Any:
        """Call a tool with given arguments"""
        if tool_name not in self.tools_registry:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        tool_func = self.tools_registry[tool_name]
        
        try:
            # Prepare arguments
            sig = inspect.signature(tool_func)
            call_args = {}
            
            for param_name, param in sig.parameters.items():
                if param_name == 'mcp_session_id':
                    call_args[param_name] = session_id
                elif param_name in arguments:
                    call_args[param_name] = arguments[param_name]
                elif param.default != inspect.Parameter.empty:
                    call_args[param_name] = param.default
            
            # Call the tool
            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(**call_args)
            else:
                result = tool_func(**call_args)
            
            return result
            
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            raise
    
    def create_mcp_response(self, request_id: Any, result: Any = None, error: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create MCP JSON-RPC response"""
        response = {
            "jsonrpc": "2.0",
            "id": request_id
        }
        
        if error:
            response["error"] = error
        else:
            response["result"] = result
        
        return response
    
    def create_error_response(self, request_id: Any, code: int, message: str, data: Any = None) -> Dict[str, Any]:
        """Create MCP error response"""
        error = {
            "code": code,
            "message": message
        }
        if data is not None:
            error["data"] = data
        
        return self.create_mcp_response(request_id, error=error)

# Global MCP protocol instance
mcp_protocol = CustomMCPProtocol()

async def handle_mcp_request(request: Request) -> Response:
    """Handle MCP protocol requests"""
    try:
        # Get session ID from header
        session_id = request.headers.get('mcp-session-id')
        if not session_id:
            # Try to create or get session
            session = session_manager.get_or_create_session()
            session_id = session.session_id
        
        # Parse JSON-RPC request
        body = await request.body()
        if not body:
            return JSONResponse(
                mcp_protocol.create_error_response(None, -32700, "Parse error: Empty request"),
                status_code=400
            )
        
        try:
            rpc_request = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError as e:
            return JSONResponse(
                mcp_protocol.create_error_response(None, -32700, f"Parse error: {str(e)}"),
                status_code=400
            )
        
        # Validate JSON-RPC format
        if not isinstance(rpc_request, dict) or rpc_request.get('jsonrpc') != '2.0':
            return JSONResponse(
                mcp_protocol.create_error_response(
                    rpc_request.get('id'), -32600, "Invalid Request: Not a valid JSON-RPC 2.0 request"
                ),
                status_code=400
            )
        
        request_id = rpc_request.get('id')
        method = rpc_request.get('method')
        params = rpc_request.get('params', {})
        
        if not method:
            return JSONResponse(
                mcp_protocol.create_error_response(request_id, -32600, "Invalid Request: Missing method"),
                status_code=400
            )
        
        # Handle different MCP methods
        if method == 'initialize':
            # Handle initialize
            session = session_manager.get_or_create_session(session_id)
            client_info = params.get('clientInfo', {})
            capabilities = params.get('capabilities', {})
            
            session_manager.initialize_session(session_id, client_info, capabilities)
            
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                    "prompts": {"listChanged": False},
                    "experimental": {}
                },
                "serverInfo": {
                    "name": "google_workspace",
                    "version": "1.12.0"
                }
            }
            
            response_data = mcp_protocol.create_mcp_response(request_id, result)
            
            # Return with session ID header
            response = JSONResponse(response_data)
            response.headers['mcp-session-id'] = session_id
            return response
        
        elif method == 'tools/list':
            # Handle tools/list
            tools = mcp_protocol.get_tools_list()
            result = {"tools": tools}
            return JSONResponse(mcp_protocol.create_mcp_response(request_id, result))
        
        elif method == 'resources/list':
            # Handle resources/list
            resources = mcp_protocol.get_resources_list()
            result = {"resources": resources}
            return JSONResponse(mcp_protocol.create_mcp_response(request_id, result))
        
        elif method == 'prompts/list':
            # Handle prompts/list
            prompts = mcp_protocol.get_prompts_list()
            result = {"prompts": prompts}
            return JSONResponse(mcp_protocol.create_mcp_response(request_id, result))
        
        elif method == 'tools/call':
            # Handle tools/call
            tool_name = params.get('name')
            arguments = params.get('arguments', {})
            
            if not tool_name:
                return JSONResponse(
                    mcp_protocol.create_error_response(request_id, -32602, "Invalid params: Missing tool name"),
                    status_code=400
                )
            
            try:
                result = await mcp_protocol.call_tool(tool_name, arguments, session_id)
                return JSONResponse(mcp_protocol.create_mcp_response(request_id, {"content": [{"type": "text", "text": str(result)}]}))
            except ValueError as e:
                return JSONResponse(
                    mcp_protocol.create_error_response(request_id, -32601, f"Method not found: {str(e)}"),
                    status_code=404
                )
            except Exception as e:
                return JSONResponse(
                    mcp_protocol.create_error_response(request_id, -32603, f"Internal error: {str(e)}"),
                    status_code=500
                )
        
        else:
            # Unknown method
            return JSONResponse(
                mcp_protocol.create_error_response(request_id, -32601, f"Method not found: {method}"),
                status_code=404
            )
    
    except Exception as e:
        logger.error(f"Error handling MCP request: {e}")
        return JSONResponse(
            mcp_protocol.create_error_response(None, -32603, f"Internal error: {str(e)}"),
            status_code=500
        )

logger.info("Custom MCP Protocol initialized")

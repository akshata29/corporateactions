"""
Azure AI Agent Service tool management for MCP integration
Handles dynamic tool discovery, registration, and execution
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass

try:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

try:
    from azure.ai.agents.models import FunctionTool, ToolSet
    AZURE_AI_AVAILABLE = True
except ImportError:
    AZURE_AI_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class MCPToolInfo:
    """Information about an MCP tool for Azure AI Agent registration"""
    server_name: str
    server_url: str
    tool_name: str
    description: str
    input_schema: Dict[str, Any]
    azure_function_name: str

class MCPToolRegistry:
    """Registry for managing MCP tools in Azure AI Agent Service"""
    
    def __init__(self):
        self.tools: Dict[str, MCPToolInfo] = {}
        self.server_connections: Dict[str, str] = {}
        
    def add_server(self, name: str, url: str):
        """Add an MCP server to the registry"""
        self.server_connections[name] = url
        
    async def discover_tools(self) -> List[MCPToolInfo]:
        """Discover all available tools from registered MCP servers"""
        discovered_tools = []
        
        if not MCP_AVAILABLE:
            logger.warning("MCP not available - cannot discover tools")
            return discovered_tools
            
        for server_name, server_url in self.server_connections.items():
            try:
                server_tools = await self._discover_server_tools(server_name, server_url)
                discovered_tools.extend(server_tools)
                logger.info(f"Discovered {len(server_tools)} tools from {server_name}")
            except Exception as e:
                logger.error(f"Failed to discover tools from {server_name}: {e}")
                
        return discovered_tools
    
    async def _discover_server_tools(self, server_name: str, server_url: str) -> List[MCPToolInfo]:
        """Discover tools from a specific MCP server"""
        tools = []
        
        try:
            async with streamablehttp_client(server_url) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    
                    # List available tools
                    tools_result = await session.list_tools()
                    
                    for tool in tools_result.tools:
                        azure_function_name = f"mcp_{server_name}_{tool.name}"
                        
                        tool_info = MCPToolInfo(
                            server_name=server_name,
                            server_url=server_url,
                            tool_name=tool.name,
                            description=tool.description or f"MCP tool: {tool.name}",
                            input_schema=tool.inputSchema or {},
                            azure_function_name=azure_function_name
                        )
                        
                        tools.append(tool_info)
                        self.tools[azure_function_name] = tool_info
                        
        except Exception as e:
            logger.error(f"Error discovering tools from {server_name}: {e}")
            
        return tools
    
    def create_azure_toolset(self) -> Optional[ToolSet]:
        """Create Azure AI ToolSet from discovered MCP tools"""
        if not AZURE_AI_AVAILABLE:
            logger.error("Azure AI Projects not available")
            return None
            
        if not self.tools:
            logger.warning("No MCP tools discovered - creating empty toolset")
            return ToolSet()
            
        toolset = ToolSet()
        
        for tool_name, tool_info in self.tools.items():
            try:
                # Create function schema for Azure AI Agent
                function_schema = {
                    "name": tool_name,
                    "description": tool_info.description,
                    "parameters": self._convert_mcp_schema_to_openai(tool_info.input_schema)
                }
                
                # Create wrapper function for execution
                wrapper_function = self._create_tool_wrapper(tool_info)
                
                # Create Azure AI FunctionTool
                function_tool = FunctionTool(
                    name=tool_name,
                    description=tool_info.description,
                    function=wrapper_function
                )
                
                toolset.add(function_tool)
                logger.debug(f"Added Azure AI function: {tool_name}")
                
            except Exception as e:
                logger.error(f"Failed to create Azure AI function for {tool_name}: {e}")
                
        logger.info(f"Created Azure AI toolset with {len(toolset.definitions)} functions")
        return toolset
    
    def _convert_mcp_schema_to_openai(self, mcp_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Convert MCP input schema to OpenAI function schema format"""
        if not mcp_schema:
            return {
                "type": "object",
                "properties": {},
                "required": []
            }
            
        # Handle both direct schemas and wrapped schemas
        if "type" in mcp_schema:
            return mcp_schema
        else:
            return {
                "type": "object",
                "properties": mcp_schema.get("properties", {}),
                "required": mcp_schema.get("required", []),
                "additionalProperties": mcp_schema.get("additionalProperties", False)
            }
    
    def _create_tool_wrapper(self, tool_info: MCPToolInfo) -> Callable:
        """Create an async wrapper function for MCP tool execution"""
        
        async def wrapper(**kwargs):
            """Execute MCP tool with given arguments"""
            try:
                result = await self._execute_mcp_tool(tool_info, kwargs)
                return result
            except Exception as e:
                error_msg = f"Error executing MCP tool {tool_info.tool_name}: {str(e)}"
                logger.error(error_msg)
                return error_msg
                
        # Set function metadata for Azure AI Agent
        wrapper.__name__ = tool_info.azure_function_name
        wrapper.__doc__ = tool_info.description
        
        return wrapper
    
    async def _execute_mcp_tool(self, tool_info: MCPToolInfo, arguments: Dict[str, Any]) -> str:
        """Execute an MCP tool with the given arguments"""
        if not MCP_AVAILABLE:
            return "MCP not available - cannot execute tool"
            
        try:
            async with streamablehttp_client(tool_info.server_url) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    
                    # Call the MCP tool
                    result = await session.call_tool(tool_info.tool_name, arguments)
                    
                    # Extract text content from MCP result
                    if hasattr(result, 'content') and result.content:
                        # Handle multiple content blocks
                        content_parts = []
                        for content_block in result.content:
                            if hasattr(content_block, 'text'):
                                content_parts.append(content_block.text)
                            else:
                                content_parts.append(str(content_block))
                        return "\n".join(content_parts)
                    else:
                        return str(result)
                        
        except Exception as e:
            logger.error(f"MCP tool execution failed for {tool_info.tool_name}: {e}")
            raise
    
    def get_tool_info(self, azure_function_name: str) -> Optional[MCPToolInfo]:
        """Get MCP tool information by Azure function name"""
        return self.tools.get(azure_function_name)
    
    def list_available_tools(self) -> List[str]:
        """List all available Azure function names"""
        return list(self.tools.keys())
    
    def get_server_tools(self, server_name: str) -> List[MCPToolInfo]:
        """Get all tools from a specific server"""
        return [tool for tool in self.tools.values() if tool.server_name == server_name]

class ToolExecutionTracker:
    """Track tool execution statistics and performance"""
    
    def __init__(self):
        self.execution_stats = {}
        self.performance_stats = {}
        
    def record_execution(self, tool_name: str, success: bool, duration: float, error: str = None):
        """Record tool execution statistics"""
        if tool_name not in self.execution_stats:
            self.execution_stats[tool_name] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_duration": 0.0,
                "errors": []
            }
            
        stats = self.execution_stats[tool_name]
        stats["total_calls"] += 1
        stats["total_duration"] += duration
        
        if success:
            stats["successful_calls"] += 1
        else:
            stats["failed_calls"] += 1
            if error and len(stats["errors"]) < 10:  # Keep last 10 errors
                stats["errors"].append(error)
                
    def get_tool_stats(self, tool_name: str) -> Dict[str, Any]:
        """Get statistics for a specific tool"""
        if tool_name not in self.execution_stats:
            return {}
            
        stats = self.execution_stats[tool_name]
        
        return {
            "tool_name": tool_name,
            "total_calls": stats["total_calls"],
            "success_rate": stats["successful_calls"] / stats["total_calls"] if stats["total_calls"] > 0 else 0,
            "average_duration": stats["total_duration"] / stats["total_calls"] if stats["total_calls"] > 0 else 0,
            "recent_errors": stats["errors"][-5:]  # Last 5 errors
        }
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all tools"""
        return {tool_name: self.get_tool_stats(tool_name) for tool_name in self.execution_stats.keys()}

# Utility functions for common tool operations
def create_default_registry() -> MCPToolRegistry:
    """Create a registry with default MCP server configurations"""
    registry = MCPToolRegistry()
    
    # Add default servers
    registry.add_server("rag", "http://localhost:8000/mcp")
    registry.add_server("websearch", "http://localhost:8001/mcp")
    registry.add_server("comments", "http://localhost:8002/mcp")
    
    return registry

async def setup_azure_agent_with_mcp(
    registry: MCPToolRegistry,
    agent_manager
) -> bool:
    """Setup Azure AI Agent with discovered MCP tools"""
    try:
        # Discover MCP tools
        logger.info("Discovering MCP tools...")
        discovered_tools = await registry.discover_tools()
        
        if not discovered_tools:
            logger.warning("No MCP tools discovered")
            return False
            
        logger.info(f"Discovered {len(discovered_tools)} MCP tools")
        
        # Create Azure AI ToolSet
        toolset = registry.create_azure_toolset()
        if not toolset:
            logger.error("Failed to create Azure AI ToolSet")
            return False
            
        # Update agent manager with tools
        agent_manager.mcp_tools = {tool.azure_function_name: {
            "server_url": tool.server_url,
            "tool_name": tool.tool_name,
            "schema": tool.input_schema
        } for tool in discovered_tools}
        
        logger.info("Successfully setup Azure AI Agent with MCP tools")
        return True
        
    except Exception as e:
        logger.error(f"Failed to setup Azure AI Agent with MCP: {e}")
        return False

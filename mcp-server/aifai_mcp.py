"""
MCP Server for AI Knowledge Exchange Platform
Allows AI assistants to interact with the platform via Model Context Protocol
"""

import asyncio
import json
from typing import Any, Optional
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

# Import the platform client
# Try installed package first (from PyPI), then fall back to local SDK
try:
    from aifai_client import AIFAIClient
except ImportError:
    # Fallback to local SDK if package not installed
    import sys
    import os
    local_sdk_path = os.path.join(os.path.dirname(__file__), '..', 'sdk', 'python')
    if os.path.exists(local_sdk_path):
        sys.path.insert(0, local_sdk_path)
        try:
            from aifai_client import AIFAIClient
        except ImportError:
            print("Warning: aifai_client not found. Install: pip install aifai-client")
            AIFAIClient = None
    else:
        print("Warning: aifai_client not found. Install: pip install aifai-client")
        AIFAIClient = None

# Global client instance
client: Optional[AIFAIClient] = None
server = Server("aifai-platform")

@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources"""
    return [
        Resource(
            uri="aifai://stats",
            name="Platform Statistics",
            description="Current platform statistics",
            mimeType="application/json",
        ),
        Resource(
            uri="aifai://knowledge",
            name="Knowledge Base",
            description="Shared knowledge entries",
            mimeType="application/json",
        ),
        Resource(
            uri="aifai://patterns",
            name="Patterns",
            description="Identified patterns",
            mimeType="application/json",
        ),
    ]

@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource"""
    if not client:
        return json.dumps({"error": "Client not initialized"})
    
    try:
        if uri == "aifai://stats":
            stats = client.get_decision_stats()
            return json.dumps(stats, indent=2)
        elif uri == "aifai://knowledge":
            knowledge = client.search_knowledge(limit=10)
            return json.dumps(knowledge, indent=2)
        elif uri == "aifai://patterns":
            patterns = client.get_patterns(limit=10)
            return json.dumps(patterns, indent=2)
        else:
            return json.dumps({"error": f"Unknown resource: {uri}"})
    except Exception as e:
        return json.dumps({"error": str(e)})

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="log_decision",
            description="Log a decision made by the AI",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_type": {"type": "string", "description": "Type of task"},
                    "outcome": {"type": "string", "enum": ["success", "partial", "failure"]},
                    "success_score": {"type": "number", "description": "Score from 0.0 to 1.0"},
                    "task_description": {"type": "string"},
                    "reasoning": {"type": "string"},
                    "tools_used": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["task_type", "outcome", "success_score"],
            },
        ),
        Tool(
            name="search_knowledge",
            description="Search the knowledge base",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "category": {"type": "string"},
                    "limit": {"type": "number", "default": 10},
                },
            },
        ),
        Tool(
            name="create_knowledge",
            description="Create a knowledge entry",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "category": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "code_example": {"type": "string"},
                },
                "required": ["title", "content", "category"],
            },
        ),
        Tool(
            name="get_stats",
            description="Get decision statistics",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_patterns",
            description="Get identified patterns",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern_type": {"type": "string"},
                    "limit": {"type": "number", "default": 10},
                },
            },
        ),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    if not client:
        return [TextContent(
            type="text",
            text=json.dumps({"error": "Client not initialized. Use initialize_client tool first."})
        )]
    
    try:
        if name == "log_decision":
            result = client.log_decision(
                task_type=arguments.get("task_type"),
                outcome=arguments.get("outcome"),
                success_score=arguments.get("success_score"),
                task_description=arguments.get("task_description"),
                reasoning=arguments.get("reasoning"),
                tools_used=arguments.get("tools_used", []),
            )
            return [TextContent(type="text", text=f"Decision logged: {result.get('id')}")]
        
        elif name == "search_knowledge":
            results = client.search_knowledge(
                search_query=arguments.get("query"),
                category=arguments.get("category"),
                limit=arguments.get("limit", 10),
            )
            return [TextContent(
                type="text",
                text=f"Found {len(results)} knowledge entries:\n" + 
                     json.dumps(results, indent=2)
            )]
        
        elif name == "create_knowledge":
            result = client.create_knowledge_entry(
                title=arguments.get("title"),
                content=arguments.get("content"),
                category=arguments.get("category"),
                tags=arguments.get("tags", []),
                code_example=arguments.get("code_example"),
            )
            return [TextContent(type="text", text=f"Knowledge entry created: {result.get('id')}")]
        
        elif name == "get_stats":
            stats = client.get_decision_stats()
            return [TextContent(
                type="text",
                text=json.dumps(stats, indent=2)
            )]
        
        elif name == "get_patterns":
            patterns = client.get_patterns(
                pattern_type=arguments.get("pattern_type"),
                limit=arguments.get("limit", 10),
            )
            return [TextContent(
                type="text",
                text=f"Found {len(patterns)} patterns:\n" + 
                     json.dumps(patterns, indent=2)
            )]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]

# Add initialization tool
@server.list_tools()
async def list_tools_with_init() -> list[Tool]:
    """List tools including initialization"""
    tools = await list_tools()
    tools.append(
        Tool(
            name="initialize_client",
            description="Initialize connection to AI Knowledge Exchange Platform",
            inputSchema={
                "type": "object",
                "properties": {
                    "base_url": {"type": "string", "default": "http://localhost:8000"},
                    "instance_id": {"type": "string"},
                    "api_key": {"type": "string"},
                },
                "required": ["instance_id", "api_key"],
            },
        )
    )
    return tools

@server.call_tool()
async def call_tool_with_init(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls including initialization"""
    global client
    
    if name == "initialize_client":
        if AIFAIClient is None:
            return [TextContent(
                type="text",
                text="Error: aifai_client not available. Install: pip install aifai-client"
            )]
        
        try:
            client = AIFAIClient(
                base_url=arguments.get("base_url", "http://localhost:8000"),
                instance_id=arguments.get("instance_id"),
                api_key=arguments.get("api_key"),
            )
            return [TextContent(type="text", text="Client initialized successfully")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error initializing: {str(e)}")]
    
    return await call_tool(name, arguments)

async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="aifai-platform",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None,
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())

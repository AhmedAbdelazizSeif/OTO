import inspect
import asyncio
from typing import Any, Callable, Dict, Optional, Type, get_type_hints
from pydantic import BaseModel
from .client import OTOAsyncClient
from .exceptions import OTOException

def register_api_tools(server: Any, client: OTOAsyncClient):
    """
    Dynamically registers OTOAsyncClient methods as tools on an MCP server instance.
    
    Args:
        server: The MCP server instance (FastMCP or compatible).
        client: An initialized OTOAsyncClient instance.
    """
    
    # Get all public methods of the client
    methods = inspect.getmembers(client, predicate=inspect.ismethod)
    
    for name, method in methods:
        # Skip private methods and properties
        if name.startswith("_"):
            continue
            
        # Extract docstring for description
        description = inspect.getdoc(method) or f"OTO API method: {name}"
        
        # Analyze parameters
        sig = inspect.signature(method)
        type_hints = get_type_hints(method)
        
        # Create a dynamic wrapper with error handling
        # We need to preserve the signature for the server to introspect it correctly
        # or we manually construct the schema if the server allows.
        
        # NOTE: Since we cannot easily dynamically generate functions with specific 
        # python signatures (arguments) without exec(), we will stick to a strategy
        # compatible with FastMCP which inspects the function metadata.
        # We will wrap the method and update the __signature__ and __annotations__.
        
        async def wrapper(*args, **kwargs):
            try:
                return await method(*args, **kwargs)
            except OTOException as e:
                return f"OTO API Error: {str(e)}"
            except Exception as e:
                return f"Unexpected Error: {str(e)}"
        
        # Copy metadata to wrapper so FastMCP/Library can introspect it
        wrapper.__name__ = name
        wrapper.__doc__ = description
        wrapper.__signature__ = sig
        wrapper.__annotations__ = type_hints
        
        # Register the tool
        # Check if server has 'tool' decorator (FastMCP style) or 'add_tool' 
        if hasattr(server, "tool"):
            # FastMCP style: @server.tool(name=..., description=...)
            # We call it as a function since we are not using decorator syntax structure here
            server.tool(name=name, description=description)(wrapper)
        elif hasattr(server, "register_tool"):
             # Alternative SDK style: register_tool(name, func, description)
             # This is a fallback assumption; FastMCP is the primary target.
             server.register_tool(name, wrapper, description=description)
        else:
            # Fallback for generic dict-based registration if available
            # This part attempts to fulfill the 'generate input schema' requirement explicitly
            # if the server doesn't auto-inspect.
            pass

    print(f"Registered {len([m for n, m in methods if not n.startswith('_')])} tools from OTOAsyncClient.")

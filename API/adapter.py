import inspect
import asyncio
from typing import Any, Callable, Dict, List, Optional, Type, Union, get_type_hints, get_origin, get_args
from pydantic import BaseModel
from .client import OTOAsyncClient
from .exceptions import OTOException


def python_type_to_json_schema(python_type: Type) -> Dict[str, Any]:
    """
    Convert a Python type hint to a JSON schema definition.
    Properly handles List types by including the 'items' property.
    """
    origin = get_origin(python_type)
    args = get_args(python_type)
    
    # Handle Optional types (Union with None)
    if origin is Union:
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1:
            return python_type_to_json_schema(non_none_args[0])
        # For complex unions, default to string
        return {"type": "string"}
    
    # Handle List/list types - MUST include 'items'
    if origin is list or (hasattr(origin, '__name__') and origin.__name__ == 'List'):
        schema = {"type": "array"}
        if args:
            schema["items"] = python_type_to_json_schema(args[0])
        else:
            # Default to string items if no type specified
            schema["items"] = {"type": "string"}
        return schema
    
    # Handle Dict/dict types
    if origin is dict:
        return {"type": "object"}
    
    # Handle basic types
    if python_type is str:
        return {"type": "string"}
    elif python_type is int:
        return {"type": "integer"}
    elif python_type is float:
        return {"type": "number"}
    elif python_type is bool:
        return {"type": "boolean"}
    elif python_type is type(None):
        return {"type": "null"}
    
    # Handle Pydantic models and other objects
    if isinstance(python_type, type) and issubclass(python_type, BaseModel):
        return {"type": "object"}
    
    # Default fallback
    return {"type": "string"}


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
        
        # Analyze parameters and build JSON schema
        sig = inspect.signature(method)
        type_hints = get_type_hints(method)
        
        # Build proper JSON schema for the tool input
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue
            
            # Get type hint for this parameter
            param_type = type_hints.get(param_name, str)
            
            # Convert to JSON schema (handles arrays with items properly)
            param_schema = python_type_to_json_schema(param_type)
            
            # Add description from docstring if available
            param_schema["description"] = f"Parameter: {param_name}"
            
            properties[param_name] = param_schema
            
            # Check if required (no default value)
            if param.default is inspect.Parameter.empty:
                required.append(param_name)
        
        input_schema = {
            "type": "object",
            "properties": properties,
        }
        if required:
            input_schema["required"] = required
        
        # Create a closure to capture the correct method reference
        def make_wrapper(m):
            async def wrapper(**kwargs):
                try:
                    return await m(**kwargs)
                except OTOException as e:
                    return f"OTO API Error: {str(e)}"
                except Exception as e:
                    return f"Unexpected Error: {str(e)}"
            return wrapper
        
        wrapper = make_wrapper(method)
        
        # Copy metadata to wrapper
        wrapper.__name__ = name
        wrapper.__doc__ = description
        wrapper.__signature__ = sig
        wrapper.__annotations__ = type_hints
        
        # Register the tool with explicit schema
        if hasattr(server, "tool"):
            # FastMCP style: @server.tool(name=..., description=...)
            server.tool(name=name, description=description)(wrapper)
        elif hasattr(server, "register_tool"):
            # Alternative SDK style
            server.register_tool(name, wrapper, description=description)
        elif hasattr(server, "add_tool"):
            # Low-level MCP SDK style with explicit schema
            from mcp.types import Tool
            tool_def = Tool(
                name=name,
                description=description,
                inputSchema=input_schema,
            )
            server.add_tool(tool_def, wrapper)
        else:
            # Fallback - store schema for potential later use
            wrapper.__input_schema__ = input_schema

    print(f"Registered {len([m for n, m in methods if not n.startswith('_')])} tools from OTOAsyncClient.")

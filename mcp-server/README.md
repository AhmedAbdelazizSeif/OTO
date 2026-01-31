# OTO Docs & API Bot - MCP Server

A production-grade Model Context Protocol (MCP) server for the OTO Logistics API.

## Overview

This MCP server exposes the OTO API through three capability types:

### 🔧 Tools (Active Capabilities)
- **`search_knowledge_base`**: Semantic search across 164 Q&A pairs
- **`oto_*` API tools**: All OTO API methods exposed as executable tools
  - Order management (create, update, cancel, hold/unhold)
  - Shipment operations (create, cancel, track)
  - Return handling (create return, get return link, trigger SMS)
  - Delivery fee checks and coverage verification
  - Pickup location management
  - Product and inventory management
  - And more...

### 📚 Resources (Passive Capabilities)
- **`docs://index`**: Documentation manifest listing all available files
- **`docs://API_DOCUMENTATION.md`**: Main API documentation
- **`docs://<filename>`**: Individual reference documentation files
- **`docs://knowledge_base`**: Raw Q&A knowledge base content

### 💬 Prompts (Context Capabilities)
- **`expert_assist`**: Technical assistance with auto-loaded context
- **`order_workflow`**: Step-by-step workflow guidance
- **`troubleshoot`**: Error diagnosis and resolution help

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your OTO API refresh token:
```bash
# Windows
set OTO_REFRESH_TOKEN=your_token_here

# Linux/macOS
export OTO_REFRESH_TOKEN=your_token_here
```

## Usage

### Running the Server

```bash
python server.py
```

The server communicates via stdio using the MCP protocol.

### MCP Client Configuration

Add to your MCP client configuration (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "oto-api": {
      "command": "python",
      "args": ["path/to/mcp-server/server.py"],
      "env": {
        "OTO_REFRESH_TOKEN": "your_refresh_token"
      }
    }
  }
}
```

## Project Structure

```
mcp-server/
├── server.py           # Main MCP server implementation
├── requirements.txt    # Python dependencies
├── llms.txt           # Knowledge base (164 Q&A pairs)
├── oto.yaml           # OpenAPI specification
└── README.md          # This file
```

## API Wrapper

The server uses the OTO API Python wrapper located in `../API/`:

- `client.py` - Async HTTP client with automatic token refresh
- `models.py` - Pydantic models for all request/response types
- `exceptions.py` - Custom exception hierarchy

## Tool Reference

### Knowledge Base Search

```
Tool: search_knowledge_base
Input: { "query": "How do I create an order?", "top_k": 5 }
Output: Relevant Q&A pairs with relevance scores
```

### API Tools

All API tools are prefixed with `oto_`. Examples:

```
Tool: oto_create_order
Input: { "request": { "order_id": "...", ... } }

Tool: oto_get_orders
Input: { "status": "delivered", "from_date": "2024-01-01" }

Tool: oto_cancel_order
Input: { "order_id": "ORD-123" }
```

## Error Handling

The server provides structured error responses:

- **OTO API Errors**: Wrapped with error type, code, and message
- **Configuration Errors**: Clear messages about missing environment variables
- **Network Errors**: Timeout and connectivity issue reporting

## Development

### Testing the Server

```bash
# Verify syntax
python -m py_compile server.py

# Run with debug output
python server.py
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OTO_REFRESH_TOKEN` | Yes (for API tools) | Your OTO API refresh token |

## License

MIT

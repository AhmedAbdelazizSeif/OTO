"""
OTO API MCP Server - Docs & API Bot

A production-grade Model Context Protocol (MCP) server that exposes the OTO
Logistics API through tools, resources, and prompts for AI assistant integration.

Features:
- Active Capabilities (Tools): All OTO API methods as executable tools
- Passive Capabilities (Resources): Documentation and Q&A knowledge base
- Context Capabilities (Prompts): Expert assistance with pre-loaded context

Usage:
    python server.py

Environment Variables:
    OTO_REFRESH_TOKEN: Your OTO API refresh token (required for API tools)
"""

import asyncio
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from difflib import SequenceMatcher

# Add parent directory to path for API imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    ResourceTemplate,
    Tool,
    TextContent,
    Prompt,
    PromptMessage,
    PromptArgument,
    GetPromptResult,
)
from pydantic import AnyUrl

from API.client import OTOAsyncClient
from API.exceptions import OTOException

# =============================================================================
# CONFIGURATION
# =============================================================================

# Server info
SERVER_NAME = "oto-docs-api-bot"
SERVER_VERSION = "1.0.0"

# Paths
BASE_DIR = Path(__file__).parent.parent
DOCS_DIR = BASE_DIR / "API" / "docs"
API_DOCUMENTATION_FILE = BASE_DIR / "API" / "API_DOCUMENTATION.md"
KNOWLEDGE_BASE_FILE = Path(__file__).parent / "llms.txt"

# =============================================================================
# KNOWLEDGE BASE
# =============================================================================

class KnowledgeBase:
    """Manages the Q&A knowledge base for semantic/keyword search."""
    
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.qa_pairs: List[Dict[str, str]] = []
        self._load()
    
    def _load(self) -> None:
        """Load and parse Q&A pairs from the knowledge base file."""
        if not self.filepath.exists():
            return
        
        content = self.filepath.read_text(encoding="utf-8")
        
        # Parse Q&A pairs using regex
        # Pattern matches Q<number>: <question> followed by A<number>: <answer>
        pattern = r'Q(\d+):\s*(.*?)\nA\1:\s*(.*?)(?=\nQ\d+:|$)'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for num, question, answer in matches:
            self.qa_pairs.append({
                "id": int(num),
                "question": question.strip(),
                "answer": answer.strip(),
            })
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search the knowledge base using keyword and fuzzy matching.
        
        Args:
            query: The search query string.
            top_k: Maximum number of results to return.
        
        Returns:
            List of matching Q&A pairs with relevance scores.
        """
        if not self.qa_pairs:
            return []
        
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored_results = []
        
        for qa in self.qa_pairs:
            question_lower = qa["question"].lower()
            answer_lower = qa["answer"].lower()
            combined_text = f"{question_lower} {answer_lower}"
            
            # Calculate relevance score using multiple factors
            score = 0.0
            
            # 1. Exact phrase match (highest weight)
            if query_lower in question_lower:
                score += 10.0
            if query_lower in answer_lower:
                score += 5.0
            
            # 2. Word overlap (medium weight)
            combined_words = set(combined_text.split())
            word_overlap = len(query_words & combined_words)
            score += word_overlap * 2.0
            
            # 3. Fuzzy string similarity (lower weight)
            similarity = SequenceMatcher(None, query_lower, question_lower).ratio()
            score += similarity * 3.0
            
            # 4. Keyword presence (for common terms)
            keywords = ["how", "create", "order", "shipment", "track", "return",
                       "cancel", "update", "get", "check", "delivery", "fee",
                       "product", "stock", "warehouse", "brand", "error"]
            for kw in keywords:
                if kw in query_lower and kw in combined_text:
                    score += 1.0
            
            if score > 0:
                scored_results.append({
                    "id": qa["id"],
                    "question": qa["question"],
                    "answer": qa["answer"],
                    "score": score,
                })
        
        # Sort by score descending and return top_k
        scored_results.sort(key=lambda x: x["score"], reverse=True)
        return scored_results[:top_k]
    
    def get_all(self) -> List[Dict[str, str]]:
        """Get all Q&A pairs."""
        return self.qa_pairs


# =============================================================================
# DOCUMENTATION MANAGER
# =============================================================================

class DocumentationManager:
    """Manages documentation resources."""
    
    def __init__(self, docs_dir: Path, main_doc: Path):
        self.docs_dir = docs_dir
        self.main_doc = main_doc
    
    def list_documents(self) -> List[Dict[str, str]]:
        """List all available documentation files."""
        docs = []
        
        # Main documentation
        if self.main_doc.exists():
            docs.append({
                "name": "API_DOCUMENTATION.md",
                "uri": "docs://API_DOCUMENTATION.md",
                "description": "Main OTO API Python Wrapper Documentation",
            })
        
        # Docs folder contents
        if self.docs_dir.exists():
            for file in self.docs_dir.glob("*.md"):
                docs.append({
                    "name": file.name,
                    "uri": f"docs://{file.name}",
                    "description": f"Reference documentation: {file.stem}",
                })
        
        return docs
    
    def get_document(self, filename: str) -> Optional[str]:
        """Get the content of a specific documentation file."""
        # Check main doc
        if filename == "API_DOCUMENTATION.md" and self.main_doc.exists():
            return self.main_doc.read_text(encoding="utf-8")
        
        # Check docs directory
        doc_path = self.docs_dir / filename
        if doc_path.exists():
            return doc_path.read_text(encoding="utf-8")
        
        return None
    
    def get_index(self) -> str:
        """Get the documentation index/manifest."""
        docs = self.list_documents()
        
        lines = [
            "# OTO API Documentation Index",
            "",
            "## Available Documentation Files",
            "",
        ]
        
        for doc in docs:
            lines.append(f"- **{doc['name']}** (`{doc['uri']}`)")
            lines.append(f"  {doc['description']}")
            lines.append("")
        
        lines.extend([
            "## Usage",
            "",
            "Use the `docs://` URI scheme to access documentation:",
            "- `docs://index` - This index file",
            "- `docs://API_DOCUMENTATION.md` - Main documentation",
            "- `docs://<filename>` - Specific reference files",
        ])
        
        return "\n".join(lines)


# =============================================================================
# API TOOL REGISTRY
# =============================================================================

class APIToolRegistry:
    """
    Dynamically registers OTOAsyncClient methods as MCP tools.
    
    This is an improved version of the adapter that generates proper
    tool definitions with input schemas for the MCP protocol.
    """
    
    # Method metadata for generating tool descriptions and schemas
    TOOL_METADATA = {
        "health_check": {
            "description": "Check the health status of the OTO API. Returns 'ok' if operational.",
            "parameters": {},
        },
        "get_account_info": {
            "description": "Get account information including name, email, credit balance, and subscription package.",
            "parameters": {},
        },
        "buy_credit": {
            "description": "Initiate a credit purchase. Returns a payment URL.",
            "parameters": {
                "amount": {"type": "number", "description": "Amount of credit to purchase", "required": True},
            },
        },
        "get_credit_transactions": {
            "description": "Get credit transaction history with optional date filters.",
            "parameters": {
                "from_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                "to_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
            },
        },
        "create_order": {
            "description": "Create a new order in OTO. Requires order details, customer info, and items.",
            "parameters": {
                "request": {"type": "object", "description": "CreateOrderRequest object with order_id, payment_method, amount, amount_due, currency, customer, and items", "required": True},
            },
        },
        "update_order": {
            "description": "Update an existing order before shipment creation.",
            "parameters": {
                "request": {"type": "object", "description": "UpdateOrderRequest with order_id and fields to update", "required": True},
            },
        },
        "cancel_order": {
            "description": "Cancel an order that doesn't have an active shipment.",
            "parameters": {
                "order_id": {"type": "string", "description": "The order ID to cancel", "required": True},
            },
        },
        "get_orders": {
            "description": "Get a list of orders with optional filters (status, dates, customer, etc.).",
            "parameters": {
                "status": {"type": "string", "description": "Filter by order status"},
                "from_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                "to_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                "per_page": {"type": "integer", "description": "Results per page"},
                "page": {"type": "integer", "description": "Page number"},
                "customer_phone": {"type": "string", "description": "Filter by customer phone"},
                "order_id": {"type": "string", "description": "Filter by specific order ID"},
            },
        },
        "get_order_details": {
            "description": "Get detailed information about a specific order.",
            "parameters": {
                "order_id": {"type": "string", "description": "The order ID", "required": True},
            },
        },
        "hold_order": {
            "description": "Place an order on hold with a reason.",
            "parameters": {
                "order_id": {"type": "string", "description": "The order ID", "required": True},
                "on_hold_reason": {"type": "string", "description": "Reason for holding", "required": True},
                "on_hold_reason_lang": {"type": "string", "description": "Language code (en, tr, ar)", "default": "en"},
            },
        },
        "unhold_order": {
            "description": "Release an order from hold status.",
            "parameters": {
                "order_id": {"type": "string", "description": "The order ID", "required": True},
            },
        },
        "create_shipment": {
            "description": "Create a shipment for an existing order.",
            "parameters": {
                "request": {"type": "object", "description": "CreateShipmentRequest with order_id and optional delivery_option_id", "required": True},
            },
        },
        "cancel_shipment": {
            "description": "Cancel a shipment that hasn't been picked up yet.",
            "parameters": {
                "order_id": {"type": "string", "description": "The order ID", "required": True},
                "shipment_id": {"type": "string", "description": "The shipment ID", "required": True},
            },
        },
        "get_order_status": {
            "description": "Get the current tracking status of an order.",
            "parameters": {
                "order_id": {"type": "string", "description": "The order ID", "required": True},
            },
        },
        "get_order_history": {
            "description": "Get the status history for one or more orders.",
            "parameters": {
                "order_ids": {"type": "array", "items": {"type": "string"}, "description": "List of order IDs", "required": True},
            },
        },
        "track_shipment": {
            "description": "Track a shipment by tracking number and carrier name.",
            "parameters": {
                "request": {"type": "object", "description": "TrackShipmentRequest with tracking_number, delivery_company_name, status_history", "required": True},
            },
        },
        "print_awb": {
            "description": "Get the shipping label (AWB) URL for an order.",
            "parameters": {
                "order_id": {"type": "string", "description": "The order ID", "required": True},
            },
        },
        "create_return_shipment": {
            "description": "Create a return shipment for a delivered order.",
            "parameters": {
                "request": {"type": "object", "description": "CreateReturnShipmentRequest with order_id", "required": True},
            },
        },
        "get_return_link": {
            "description": "Get a customer self-service return portal link.",
            "parameters": {
                "order_id": {"type": "string", "description": "The order ID", "required": True},
            },
        },
        "get_return_details": {
            "description": "Get details about a return shipment.",
            "parameters": {
                "order_id": {"type": "string", "description": "The order ID", "required": True},
            },
        },
        "trigger_return_sms": {
            "description": "Send a return SMS notification to the customer.",
            "parameters": {
                "order_id": {"type": "string", "description": "The order ID", "required": True},
            },
        },
        "check_oto_delivery_fee": {
            "description": "Check delivery fees from OTO's carrier marketplace.",
            "parameters": {
                "request": {"type": "object", "description": "CheckOTODeliveryFeeRequest with origin_city, destination_city, weight", "required": True},
            },
        },
        "check_delivery_fee": {
            "description": "Check delivery fees for your contracted carriers.",
            "parameters": {
                "request": {"type": "object", "description": "CheckDeliveryFeeRequest with origin_city, destination_city, weight", "required": True},
            },
        },
        "get_delivery_fee": {
            "description": "Get all available delivery fees (OTO + contract carriers).",
            "parameters": {
                "request": {"type": "object", "description": "GetDeliveryFeeRequest with origin_city, destination_city, weight", "required": True},
            },
        },
        "check_coverage": {
            "description": "Check if a delivery route is covered by available carriers.",
            "parameters": {
                "request": {"type": "object", "description": "CheckCoverageRequest with origin_city, destination_city", "required": True},
            },
        },
        "get_cities": {
            "description": "Get the list of cities for a country.",
            "parameters": {
                "country": {"type": "string", "description": "ISO2 country code (e.g., SA, AE)", "required": True},
                "per_page": {"type": "integer", "description": "Results per page"},
                "page": {"type": "integer", "description": "Page number"},
            },
        },
        "create_pickup_location": {
            "description": "Create a new pickup location (warehouse or branch).",
            "parameters": {
                "request": {"type": "object", "description": "CreatePickupLocationRequest with name, code, mobile, city, country, address, contact_name, contact_email", "required": True},
            },
        },
        "update_pickup_location": {
            "description": "Update an existing pickup location.",
            "parameters": {
                "request": {"type": "object", "description": "UpdatePickupLocationRequest with code and fields to update", "required": True},
            },
        },
        "get_pickup_locations": {
            "description": "Get the list of all pickup locations (warehouses and branches).",
            "parameters": {},
        },
        "get_brands": {
            "description": "Get the list of brands/client stores.",
            "parameters": {},
        },
        "create_brand": {
            "description": "Create a new brand/client store.",
            "parameters": {
                "request": {"type": "object", "description": "CreateBrandRequest with store_name", "required": True},
            },
        },
        "create_product": {
            "description": "Create a new product in the catalog.",
            "parameters": {
                "request": {"type": "object", "description": "CreateProductRequest with sku, product_name, price", "required": True},
            },
        },
        "get_products": {
            "description": "Get the list of products in the catalog.",
            "parameters": {
                "page_size": {"type": "integer", "description": "Products per page"},
                "current_page": {"type": "integer", "description": "Page number"},
            },
        },
        "add_box": {
            "description": "Add a new box type for packaging.",
            "parameters": {
                "request": {"type": "object", "description": "AddBoxRequest with name, length, width, height", "required": True},
            },
        },
        "update_box": {
            "description": "Update an existing box type dimensions.",
            "parameters": {
                "request": {"type": "object", "description": "UpdateBoxRequest with name, length, width, height", "required": True},
            },
        },
        "get_boxes": {
            "description": "Get the list of configured box types.",
            "parameters": {},
        },
        "update_stock_quantity": {
            "description": "Update stock quantity for a product (set, increment, or decrement).",
            "parameters": {
                "request": {"type": "object", "description": "UpdateStockQuantityRequest with sku, quantity, action_type", "required": True},
            },
        },
    }
    
    @classmethod
    def get_tool_definitions(cls) -> List[Tool]:
        """Generate MCP Tool definitions for all API methods."""
        tools = []
        
        for method_name, metadata in cls.TOOL_METADATA.items():
            # Build input schema
            properties = {}
            required = []
            
            for param_name, param_info in metadata.get("parameters", {}).items():
                prop = {"type": param_info.get("type", "string")}
                if "description" in param_info:
                    prop["description"] = param_info["description"]
                if "items" in param_info:
                    prop["items"] = param_info["items"]
                properties[param_name] = prop
                
                if param_info.get("required", False):
                    required.append(param_name)
            
            input_schema = {
                "type": "object",
                "properties": properties,
            }
            if required:
                input_schema["required"] = required
            
            tools.append(Tool(
                name=f"oto_{method_name}",
                description=metadata["description"],
                inputSchema=input_schema,
            ))
        
        return tools

# =============================================================================
# MCP SERVER
# =============================================================================

# Initialize managers
knowledge_base = KnowledgeBase(KNOWLEDGE_BASE_FILE)
docs_manager = DocumentationManager(DOCS_DIR, API_DOCUMENTATION_FILE)

# Create MCP server
server = Server(SERVER_NAME)

# Global client (initialized on first use)
_oto_client: Optional[OTOAsyncClient] = None
_client_lock = asyncio.Lock()


async def get_oto_client() -> OTOAsyncClient:
    """Get or create the OTO API client."""
    global _oto_client
    
    async with _client_lock:
        if _oto_client is None:
            refresh_token = os.environ.get("OTO_REFRESH_TOKEN")
            if not refresh_token:
                raise ValueError(
                    "OTO_REFRESH_TOKEN environment variable is required for API tools. "
                    "Set it with your OTO API refresh token."
                )
            
            _oto_client = OTOAsyncClient(refresh_token=refresh_token)
            # Initialize the client (enters context)
            await _oto_client.__aenter__()
        
        return _oto_client


async def cleanup_client():
    """Cleanup the OTO client on shutdown."""
    global _oto_client
    if _oto_client is not None:
        await _oto_client.__aexit__(None, None, None)
        _oto_client = None


# =============================================================================
# TOOLS
# =============================================================================

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List all available tools."""
    tools = []
    
    # Knowledge base search tool
    tools.append(Tool(
        name="search_knowledge_base",
        description="Search the OTO API knowledge base containing 164 Q&A pairs. Use this for 'How-to' questions about using the OTO API, understanding request/response structures, or troubleshooting.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to find relevant Q&A pairs",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    ))
    
    # Add all API tools
    tools.extend(APIToolRegistry.get_tool_definitions())
    
    return tools


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Execute a tool call."""
    
    # Knowledge base search
    if name == "search_knowledge_base":
        query = arguments.get("query", "")
        top_k = arguments.get("top_k", 5)
        
        results = knowledge_base.search(query, top_k)
        
        if not results:
            return [TextContent(
                type="text",
                text="No matching Q&A pairs found. Try different keywords or rephrase your query.",
            )]
        
        output_lines = [f"## Knowledge Base Search Results for: '{query}'", ""]
        
        for i, result in enumerate(results, 1):
            output_lines.append(f"### Result {i} (Q{result['id']}, Score: {result['score']:.2f})")
            output_lines.append(f"**Question:** {result['question']}")
            output_lines.append(f"**Answer:**\n{result['answer']}")
            output_lines.append("")
        
        return [TextContent(type="text", text="\n".join(output_lines))]
    
    # API Tools (prefixed with oto_)
    if name.startswith("oto_"):
        method_name = name[4:]  # Remove "oto_" prefix
        
        try:
            client = await get_oto_client()
            
            # Get the method
            if not hasattr(client, method_name):
                return [TextContent(
                    type="text",
                    text=f"Error: Unknown API method '{method_name}'",
                )]
            
            method = getattr(client, method_name)
            
            # Handle different method signatures
            if "request" in arguments:
                # Methods that take a request object need special handling
                # For now, pass the dict directly and let Pydantic handle it
                result = await method(arguments["request"])
            else:
                # Methods with simple parameters
                result = await method(**arguments)
            
            # Convert result to string
            if hasattr(result, "model_dump"):
                result_str = str(result.model_dump(by_alias=True))
            else:
                result_str = str(result)
            
            return [TextContent(
                type="text",
                text=f"## OTO API Response\n\n```json\n{result_str}\n```",
            )]
            
        except OTOException as e:
            return [TextContent(
                type="text",
                text=f"## OTO API Error\n\n**Type:** {type(e).__name__}\n**Message:** {str(e)}",
            )]
        except ValueError as e:
            return [TextContent(
                type="text",
                text=f"## Configuration Error\n\n{str(e)}",
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"## Unexpected Error\n\n**Type:** {type(e).__name__}\n**Message:** {str(e)}",
            )]
    
    return [TextContent(type="text", text=f"Unknown tool: {name}")]


# =============================================================================
# RESOURCES
# =============================================================================

@server.list_resources()
async def list_resources() -> List[Resource]:
    """List all available documentation resources."""
    resources = []
    
    # Documentation index
    resources.append(Resource(
        uri=AnyUrl("docs://index"),
        name="Documentation Index",
        description="Index of all available OTO API documentation files",
        mimeType="text/markdown",
    ))
    
    # Individual documentation files
    for doc in docs_manager.list_documents():
        resources.append(Resource(
            uri=AnyUrl(doc["uri"]),
            name=doc["name"],
            description=doc["description"],
            mimeType="text/markdown",
        ))
    
    # Knowledge base as a resource
    resources.append(Resource(
        uri=AnyUrl("docs://knowledge_base"),
        name="Knowledge Base (Q&A)",
        description="164 Q&A pairs about the OTO API covering authentication, orders, shipments, and more",
        mimeType="text/plain",
    ))
    
    return resources


@server.read_resource()
async def read_resource(uri: AnyUrl) -> str:
    """Read a documentation resource."""
    uri_str = str(uri)
    
    # Remove the docs:// prefix
    if not uri_str.startswith("docs://"):
        raise ValueError(f"Invalid URI scheme: {uri_str}")
    
    filename = uri_str[7:]  # Remove "docs://"
    
    # Handle special resources
    if filename == "index":
        return docs_manager.get_index()
    
    if filename == "knowledge_base":
        # Return the raw knowledge base content
        if KNOWLEDGE_BASE_FILE.exists():
            return KNOWLEDGE_BASE_FILE.read_text(encoding="utf-8")
        return "Knowledge base file not found."
    
    # Handle documentation files
    content = docs_manager.get_document(filename)
    if content is None:
        raise ValueError(f"Document not found: {filename}")
    
    return content


# =============================================================================
# PROMPTS
# =============================================================================

@server.list_prompts()
async def list_prompts() -> List[Prompt]:
    """List available prompts."""
    return [
        Prompt(
            name="expert_assist",
            description="Expert OTO API assistant with pre-loaded documentation and relevant Q&A context. Use this for technical assistance with the OTO logistics API.",
            arguments=[
                PromptArgument(
                    name="question",
                    description="Your question or task related to the OTO API",
                    required=True,
                ),
            ],
        ),
        Prompt(
            name="order_workflow",
            description="Step-by-step guidance for order management workflows (create, track, cancel, return).",
            arguments=[
                PromptArgument(
                    name="workflow_type",
                    description="Type of workflow: create, track, cancel, return, or update",
                    required=True,
                ),
            ],
        ),
        Prompt(
            name="troubleshoot",
            description="Troubleshooting assistant for OTO API errors and issues.",
            arguments=[
                PromptArgument(
                    name="error_description",
                    description="Description of the error or issue you're experiencing",
                    required=True,
                ),
            ],
        ),
    ]


@server.get_prompt()
async def get_prompt(name: str, arguments: Optional[Dict[str, str]] = None) -> GetPromptResult:
    """Get a prompt with pre-loaded context."""
    
    if name == "expert_assist":
        question = arguments.get("question", "") if arguments else ""
        
        # Get documentation index
        doc_index = docs_manager.get_index()
        
        # Get top 5 relevant Q&A pairs
        qa_results = knowledge_base.search(question, top_k=5)
        qa_context = "\n\n".join([
            f"**Q{r['id']}:** {r['question']}\n**A:** {r['answer']}"
            for r in qa_results
        ]) if qa_results else "No directly relevant Q&A found."
        
        return GetPromptResult(
            description="Expert OTO API assistance with context",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""You are an expert assistant for the OTO Logistics API. Help the user with their question using the context below.

## Available Documentation
{doc_index}

## Relevant Q&A from Knowledge Base
{qa_context}

## User Question
{question}

Please provide a clear, accurate, and helpful response. Include code examples when appropriate.""",
                    ),
                ),
            ],
        )
    
    elif name == "order_workflow":
        workflow_type = arguments.get("workflow_type", "create") if arguments else "create"
        
        # Get relevant Q&A for the workflow
        qa_results = knowledge_base.search(f"{workflow_type} order", top_k=10)
        qa_context = "\n\n".join([
            f"**Q{r['id']}:** {r['question']}\n**A:** {r['answer']}"
            for r in qa_results
        ])
        
        return GetPromptResult(
            description=f"Order {workflow_type} workflow guidance",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""Provide step-by-step guidance for the "{workflow_type}" order workflow in the OTO API.

## Relevant Q&A
{qa_context}

Please provide:
1. Prerequisites and requirements
2. Step-by-step code examples
3. Important considerations and best practices
4. Error handling recommendations""",
                    ),
                ),
            ],
        )
    
    elif name == "troubleshoot":
        error_description = arguments.get("error_description", "") if arguments else ""
        
        # Search for error-related Q&A
        qa_results = knowledge_base.search(f"error {error_description}", top_k=5)
        qa_context = "\n\n".join([
            f"**Q{r['id']}:** {r['question']}\n**A:** {r['answer']}"
            for r in qa_results
        ]) if qa_results else "No directly relevant error handling Q&A found."
        
        return GetPromptResult(
            description="Troubleshooting assistance",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""Help troubleshoot this OTO API issue:

## Problem Description
{error_description}

## Relevant Q&A
{qa_context}

Please provide:
1. Likely cause of the issue
2. Diagnostic steps
3. Solution or workaround
4. Prevention tips""",
                    ),
                ),
            ],
        )
    
    raise ValueError(f"Unknown prompt: {name}")


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Run the MCP server."""
    print(f"Starting {SERVER_NAME} v{SERVER_VERSION}...", file=sys.stderr)
    print(f"Knowledge base loaded: {len(knowledge_base.qa_pairs)} Q&A pairs", file=sys.stderr)
    print(f"Documentation files: {len(docs_manager.list_documents())}", file=sys.stderr)
    
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )
    finally:
        await cleanup_client()


if __name__ == "__main__":
    asyncio.run(main())

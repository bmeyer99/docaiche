"""
MCP Service Endpoint Scaffolding
PRD-015: MCP Service Endpoint

Defines the FastAPI router and Pydantic schemas for MCP protocol messages.
Handles MCP message types: initialize, get_tools, execute_tool.

This file provides only the architectural scaffolding. All business logic
must be implemented by the Implementation Engineer as marked by TODOs.
"""

from fastapi import APIRouter, Request, status, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import logging

from src.api.v1.dependencies import get_anythingllm_client, get_search_orchestrator
from src.clients.anythingllm import AnythingLLMClient
from src.search.orchestrator import SearchOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["MCP"], prefix="")

class InitializeRequest(BaseModel):
    """Schema for MCP 'initialize' message request."""
    message_type: str = Field(..., example="initialize")
    client_name: Optional[str] = Field(None, example="docaiche-client")
    client_version: Optional[str] = Field(None, example="1.0.0")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class Tool(BaseModel):
    """Schema representing an MCP tool definition (e.g., fetch_documentation)."""
    name: str = Field(..., example="fetch_documentation")
    description: str = Field(..., example="Fetches documentation for a given symbol or file.")
    input_schema: Dict[str, Any] = Field(..., example={"type": "object", "properties": {"symbol": {"type": "string"}}})
    output_schema: Dict[str, Any] = Field(..., example={"type": "object", "properties": {"documentation": {"type": "string"}}})

class ExecuteToolRequest(BaseModel):
    """Schema for MCP 'execute_tool' message request."""
    message_type: str = Field(..., example="execute_tool")
    tool: str = Field(..., example="fetch_documentation")
    arguments: Dict[str, Any] = Field(..., example={"symbol": "MyClass"})
    request_id: Optional[str] = Field(None, example="req-123")

class ExecuteToolResponse(BaseModel):
    """Schema for MCP 'execute_tool' message response."""
    request_id: Optional[str] = Field(None, example="req-123")
    result: Optional[Dict[str, Any]] = Field(default_factory=dict)
    error: Optional[str] = Field(None, example="Tool execution failed.")

@router.post(
    "/mcp",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="MCP Service Endpoint",
    description="Handles MCP protocol messages: initialize, get_tools, execute_tool."
)
async def mcp_service_endpoint(
    request: Request,
    anythingllm_client: AnythingLLMClient = Depends(get_anythingllm_client),
    search_orchestrator: SearchOrchestrator = Depends(get_search_orchestrator)
):
    """
    Main MCP endpoint for handling protocol messages.

    Accepts a JSON body with a 'message_type' field and dispatches to the appropriate handler.

    - 'initialize': Returns basic server info.
    - 'get_tools': Returns available tool definitions.
    - 'execute_tool': Executes a tool (cache-aside logic placeholder).

    Implements message dispatch and business logic.
    """
    try:
        body = await request.json()
        message_type = body.get("message_type")
    except Exception as e:
        logger.error(f"Failed to parse MCP request body: {e}")
        return JSONResponse(
            content={"error": "Invalid JSON body."},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if message_type == "initialize":
        return JSONResponse(
            content={
                "server_name": "docaiche-mcp",
                "server_version": "1.0.0",
                "capabilities": ["fetch_documentation"]
            }
        )

    elif message_type == "get_tools":
        fetch_doc_tool = Tool(
            name="fetch_documentation",
            description="Fetches documentation for a given symbol or file.",
            input_schema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Symbol or file to fetch documentation for"}
                },
                "required": ["symbol"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "documentation": {"type": "string", "description": "Fetched documentation"}
                }
            }
        )
        return JSONResponse(content={"tools": [fetch_doc_tool.dict()]})

    elif message_type == "execute_tool":
        # IMPLEMENTATION ENGINEER - Implement cache-aside logic for tool execution
        try:
            tool = body.get("tool")
            arguments = body.get("arguments", {})
            request_id = body.get("request_id")

            if tool != "fetch_documentation":
                logger.warning(f"Unsupported tool requested: {tool}")
                return JSONResponse(
                    content={
                        "request_id": request_id,
                        "result": {},
                        "error": f"Unsupported tool: {tool}"
                    },
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            symbol = arguments.get("symbol")
            if not symbol or not isinstance(symbol, str):
                logger.warning("Missing or invalid 'symbol' argument for fetch_documentation")
                return JSONResponse(
                    content={
                        "request_id": request_id,
                        "result": {},
                        "error": "Missing or invalid 'symbol' argument."
                    },
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
                )

            # 1. Check AnythingLLM for documentation (cache check)
            try:
                # Use a fixed workspace for documentation cache (could be configurable)
                workspace_slug = "documentation"
                search_results = await anythingllm_client.search_workspace(workspace_slug, symbol, limit=1)
            except Exception as e:
                logger.error(f"AnythingLLM search failed: {e}")
                return JSONResponse(
                    content={
                        "request_id": request_id,
                        "result": {},
                        "error": "Documentation cache unavailable. Please try again later."
                    },
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE
                )

            if search_results and isinstance(search_results, list) and len(search_results) > 0:
                doc_content = search_results[0].get("content", "")
                logger.info(f"Cache hit for symbol '{symbol}' in AnythingLLM workspace.")
                return JSONResponse(
                    content={
                        "request_id": request_id,
                        "result": {"documentation": doc_content},
                        "error": None
                    }
                )

            # 2. Cache miss: Use SearchOrchestrator to fetch documentation
            try:
                from src.search.models import SearchQuery
                search_query = SearchQuery(
                    query=symbol,
                    filters=None,
                    strategy=None,
                    limit=1,
                    offset=0,
                    technology_hint=None,
                    workspace_slugs=None
                )
                search_results_obj, _ = await search_orchestrator.execute_search(search_query)
                if search_results_obj.results and len(search_results_obj.results) > 0:
                    doc_content = search_results_obj.results[0].content
                else:
                    doc_content = ""
            except Exception as e:
                logger.error(f"SearchOrchestrator failed for symbol '{symbol}': {e}")
                return JSONResponse(
                    content={
                        "request_id": request_id,
                        "result": {},
                        "error": "Documentation search failed. Please try again later."
                    },
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # 3. Store result in AnythingLLM for future cache hits
            try:
                if doc_content:
                    from src.database.connection import ProcessedDocument, DocumentChunk
                    import uuid
                    doc_id = str(uuid.uuid4())
                    chunk_id = str(uuid.uuid4())
                    chunk = DocumentChunk(
                        id=chunk_id,
                        content=doc_content,
                        chunk_index=0,
                        total_chunks=1
                    )
                    processed_doc = ProcessedDocument(
                        id=doc_id,
                        title=symbol,
                        technology=None,
                        source_url=None,
                        chunks=[chunk]
                    )
                    await anythingllm_client.upload_document(workspace_slug, processed_doc)
                    logger.info(f"Stored documentation for symbol '{symbol}' in AnythingLLM workspace.")
            except Exception as e:
                logger.warning(f"Failed to store documentation in AnythingLLM: {e}")

            return JSONResponse(
                content={
                    "request_id": request_id,
                    "result": {"documentation": doc_content},
                    "error": None if doc_content else "No documentation found."
                }
            )

        except Exception as e:
            logger.error(f"Unhandled error in execute_tool: {e}")
            return JSONResponse(
                content={
                    "request_id": body.get("request_id"),
                    "result": {},
                    "error": "Internal server error during tool execution."
                },
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    else:
        # Unknown message type
        return JSONResponse(
            content={"error": "Invalid or unsupported message_type."},
            status_code=status.HTTP_400_BAD_REQUEST
        )
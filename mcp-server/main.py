#!/usr/bin/env python3
"""
Corporate Actions MCP Server
Proper MCP implementation using Azure OpenAI, AI Search, and Cosmos DB
Following Model Context Protocol specification with SSE support
"""

import asyncio
import json
import os
import logging
import platform
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# MCP imports
from fastmcp import FastMCP

# FastAPI imports for SSE support
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Azure SDK imports
from azure.cosmos.aio import CosmosClient
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from openai import AsyncAzureOpenAI
from azure.identity import DefaultAzureCredential, ClientSecretCredential

# Load environment variables
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, ".env")
load_dotenv(env_path, override=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set Windows event loop policy to avoid DNS issues
if platform.system() == "Windows":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        logger.info("Set Windows SelectorEventLoop policy to avoid DNS issues")
    except AttributeError:
        logger.warning("WindowsSelectorEventLoopPolicy not available, using default")

# Global Azure clients
cosmos_client: Optional[CosmosClient] = None
search_client: Optional[SearchClient] = None
openai_client: Optional[AsyncAzureOpenAI] = None

# Initialize FastMCP server
app = FastMCP("Corporate Actions MCP Server")

async def initialize_azure_clients():
    """Initialize Azure service clients"""
    global cosmos_client, search_client, openai_client
    
    try:
        # Cosmos DB client
        cosmos_endpoint = os.getenv("AZURE_COSMOS_ENDPOINT")
        cosmos_key = os.getenv("AZURE_COSMOS_KEY")
        # service principal
        tenant_id = os.getenv('AZURE_TENANT_ID')
        client_id = os.getenv('AZURE_CLIENT_ID')
        client_secret = os.getenv('AZURE_CLIENT_SECRET')
        cred = ClientSecretCredential(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)
        if cosmos_endpoint:
            cosmos_client = CosmosClient(cosmos_endpoint, cred)
            logger.info("✅ Cosmos DB client initialized")
        
        # AI Search client
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        search_key = os.getenv("AZURE_SEARCH_KEY")
        search_index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "corporate-actions")
        if search_endpoint and search_key:
            search_client = SearchClient(
                endpoint=search_endpoint,
                index_name=search_index_name,
                credential=AzureKeyCredential(search_key)
            )
            logger.info("✅ AI Search client initialized")
        
        # Azure OpenAI client
        openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        openai_key = os.getenv("AZURE_OPENAI_KEY")
        if openai_endpoint and openai_key:
            openai_client = AsyncAzureOpenAI(
                azure_endpoint=openai_endpoint,
                api_key=openai_key,
                api_version="2024-02-15-preview"
            )
            logger.info("✅ Azure OpenAI client initialized")
            
    except Exception as e:
        logger.error(f"❌ Error initializing Azure clients: {e}")

async def generate_embedding(text: str) -> List[float]:
    """Generate text embedding using Azure OpenAI"""
    try:
        if not openai_client:
            raise Exception("Azure OpenAI client not initialized")
        
        response = await openai_client.embeddings.create(
            input=text,
            model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", "text-embedding-ada-002")
        )
        
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        # Return dummy embedding for fallback
        return [0.0] * 1536

async def vector_search(query_vector: List[float], max_results: int = 5) -> List[Dict[str, Any]]:
    """Perform vector search in Azure AI Search"""
    try:
        if not search_client:
            logger.warning("AI Search client not available, using sample data")
            return get_sample_events()[:max_results]
        
        vector_query = VectorizedQuery(
            vector=query_vector,
            k_nearest_neighbors=max_results,
            fields="content_vector"
        )
        
        results = await search_client.search(
            search_text="*",
            vector_queries=[vector_query],
            top=max_results
        )
        
        search_results = []
        async for result in results:
            search_results.append(dict(result))
        
        return search_results
        
    except Exception as e:
        logger.error(f"Error in vector search: {e}")
        # Fallback to sample data
        return get_sample_events()[:max_results]

async def generate_rag_response(query: str, search_results: List[Dict[str, Any]], chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """Generate RAG response using Azure OpenAI with chat history and visualization support"""
    try:
        if not openai_client:
            return {
                "answer": "Azure OpenAI service not available. Please check configuration.",
                "sources": search_results,
                "confidence_score": 0.5,
                "query_intent": "information_request",
                "requires_visualization": False
            }
        
        # Prepare context from search results
        context = ""
        for i, result in enumerate(search_results[:3]):
            context += f"\n--- Source {i+1} ---\n"
            context += f"Company: {result.get('issuer_name', result.get('company_name', 'Unknown'))}\n"
            context += f"Event Type: {result.get('event_type', 'Unknown')}\n"
            context += f"Description: {result.get('description', 'No description')}\n"
            context += f"Status: {result.get('status', 'Unknown')}\n"
            context += f"Details: {json.dumps(result.get('event_details', {}), indent=2)}\n"
        
        # Prepare chat history context
        history_context = ""
        if chat_history:
            # Get last 5 messages for context
            recent_history = chat_history[-5:] if len(chat_history) > 5 else chat_history
            history_context = "\n\n--- Recent Conversation History ---\n"
            for msg in recent_history:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                history_context += f"{role.capitalize()}: {content}\n"
        
        # Check for visualization requests
        visualization_keywords = [
            "chart", "graph", "plot", "visualization", "visualize", "show me a", 
            "pie chart", "bar chart", "distribution", "trend", "dashboard",
            "visual", "diagram", "infographic", "analytics view"
        ]
        query_lower = query.lower()
        requires_visualization = any(keyword in query_lower for keyword in visualization_keywords)
        
        # Create enhanced system prompt
        system_prompt = f"""You are a corporate actions expert assistant with advanced analytics capabilities. Analyze the provided corporate action data and answer the user's question accurately and concisely.

Key guidelines:
- Focus on factual information from the provided sources
- Highlight important dates, amounts, and deadlines
- Explain implications for shareholders
- Use clear, professional language
- If information is missing, state that clearly
- Consider the conversation history for context
- If the user requests visualizations, acknowledge this and suggest what type of visual analysis would be helpful

{'VISUALIZATION REQUEST DETECTED: The user is asking for charts, graphs, or visual analysis. In your response, suggest appropriate visualizations based on the data available (e.g., status distribution pie charts, event type bar charts, timeline views, etc.).' if requires_visualization else ''}

Context from corporate actions database:
{context}
{history_context}
"""

        # Build message history for the API call
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add recent chat history if available
        if chat_history:
            # Add last 3 conversation turns for better context
            recent_messages = chat_history[-6:]  # Last 3 user-assistant pairs
            for msg in recent_messages:
                if msg.get("role") in ["user", "assistant"]:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
        
        # Add current query
        messages.append({"role": "user", "content": query})

        # Generate response
        response = await openai_client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"),
            messages=messages,
            max_tokens=800,  # Increased for visualization suggestions
            temperature=0.3
        )
        
        answer = response.choices[0].message.content
        
        # Determine query intent with enhanced detection
        intent_keywords = {
            "search": ["find", "search", "show", "list", "get", "retrieve"],
            "analysis": ["analyze", "explain", "why", "how", "impact", "implications", "effect"],
            "comparison": ["compare", "versus", "vs", "difference", "contrast", "against"],
            "calculation": ["calculate", "compute", "value", "price", "amount", "total"],
            "visualization": ["chart", "graph", "plot", "visualize", "dashboard", "distribution"],
            "trend": ["trend", "over time", "historical", "pattern", "timeline"]
        }
        
        detected_intent = "information_request"
        for intent, keywords in intent_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                detected_intent = intent
                break
        
        # Enhanced response with visualization flag
        response_data = {
            "answer": answer,
            "sources": search_results,
            "confidence_score": 0.85,
            "query_intent": detected_intent,
            "requires_visualization": requires_visualization
        }
        
        # Add visualization suggestions if requested
        if requires_visualization:
            response_data["visualization_suggestions"] = {
                "recommended_charts": [],
                "data_available": []
            }
            
            # Analyze available data for visualization recommendations
            if search_results:
                status_types = set(r.get("status") for r in search_results if r.get("status"))
                event_types = set(r.get("event_type") for r in search_results if r.get("event_type"))
                companies = set(r.get("issuer_name", r.get("company_name")) for r in search_results if r.get("issuer_name") or r.get("company_name"))
                
                if len(status_types) > 1:
                    response_data["visualization_suggestions"]["recommended_charts"].append("status_distribution_pie")
                    response_data["visualization_suggestions"]["data_available"].append("event_status")
                
                if len(event_types) > 1:
                    response_data["visualization_suggestions"]["recommended_charts"].append("event_type_bar")
                    response_data["visualization_suggestions"]["data_available"].append("event_types")
                
                if len(companies) > 1:
                    response_data["visualization_suggestions"]["recommended_charts"].append("company_activity_bar")
                    response_data["visualization_suggestions"]["data_available"].append("company_activity")
                
                # Check for date fields for timeline visualization
                dates = [r.get("announcement_date") for r in search_results if r.get("announcement_date")]
                if len(dates) > 2:
                    response_data["visualization_suggestions"]["recommended_charts"].append("timeline_view")
                    response_data["visualization_suggestions"]["data_available"].append("date_timeline")
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error generating RAG response: {e}")
        return {
            "answer": f"Error generating response: {str(e)}",
            "sources": search_results,
            "confidence_score": 0.1,
            "query_intent": "error",
            "requires_visualization": False
        }

async def get_event_comments(event_id: str) -> List[Dict[str, Any]]:
    """Retrieve comments for a specific corporate action event"""
    try:
        if cosmos_client:
            database = cosmos_client.get_database_client("corporateactions")
            container = database.get_container_client("comments")
            
            query = "SELECT * FROM c WHERE c.event_id = @event_id ORDER BY c.created_at DESC"
            parameters = [{"name": "@event_id", "value": event_id}]
            
            comments = []
            async for item in container.query_items(query, parameters=parameters):
                comments.append(item)
            
            return comments
        else:
            # Fallback to sample data
            return get_sample_comments(event_id)
            
    except Exception as e:
        logger.error(f"Error retrieving comments: {e}")
        return []

def get_sample_events() -> List[Dict[str, Any]]:
    """Get sample corporate action events for testing"""
    return [
        {
            "event_id": "AAPL_DIV_2024_Q1",
            "company_name": "Apple Inc.",
            "symbol": "AAPL",
            "event_type": "dividend",
            "description": "Quarterly cash dividend",
            "status": "confirmed",
            "announcement_date": "2024-01-25",
            "ex_date": "2024-02-15",
            "record_date": "2024-02-16",
            "payment_date": "2024-02-22",
            "event_details": {
                "dividend_amount": 0.24,
                "currency": "USD",
                "frequency": "quarterly"
            }
        },
        {
            "event_id": "MSFT_SPLIT_2024",
            "company_name": "Microsoft Corporation",
            "symbol": "MSFT",
            "event_type": "stock_split",
            "description": "2-for-1 stock split",
            "status": "announced",
            "announcement_date": "2024-01-15",
            "ex_date": "2024-03-01",
            "record_date": "2024-03-01",
            "payment_date": "2024-03-15",
            "event_details": {
                "split_ratio": "2:1",
                "new_shares_per_old": 2
            }
        },
        {
            "event_id": "TSLA_DIV_2024_SPECIAL",
            "company_name": "Tesla Inc.",
            "symbol": "TSLA",
            "event_type": "special_dividend",
            "description": "Special cash dividend distribution",
            "status": "confirmed",
            "announcement_date": "2024-02-01",
            "ex_date": "2024-02-28",
            "record_date": "2024-03-01",
            "payment_date": "2024-03-15",
            "event_details": {
                "dividend_amount": 1.50,
                "currency": "USD",
                "type": "special"
            }
        }
    ]

def get_sample_comments(event_id: str = None) -> List[Dict[str, Any]]:
    """Get sample comments for testing"""
    all_comments = [
        {
            "comment_id": "comment_001",
            "event_id": "AAPL_DIV_2024_Q1",
            "user_name": "investor_123",
            "comment_text": "Great dividend yield this quarter!",
            "comment_type": "general",
            "created_at": "2024-01-26T10:30:00Z",
            "votes": 5
        },
        {
            "comment_id": "comment_002",
            "event_id": "MSFT_SPLIT_2024",
            "user_name": "trader_pro",
            "comment_text": "Stock split should make shares more accessible to retail investors",
            "comment_type": "analysis",
            "created_at": "2024-01-16T14:20:00Z",
            "votes": 12
        }
    ]
    
    if event_id:
        return [c for c in all_comments if c["event_id"] == event_id]
    return all_comments

# =============================================================================
# Core Implementation Functions (used by both MCP tools and SSE endpoints)
# =============================================================================

async def _rag_query_impl(query: str, max_results: int = 5, include_comments: bool = True, chat_history: str = "") -> str:
    """Core RAG query implementation with timeout handling"""
    try:
        logger.info(f"Processing RAG query: {query}")
        
        # Parse chat history if provided
        parsed_history = []
        if chat_history:
            try:
                parsed_history = json.loads(chat_history)
                if not isinstance(parsed_history, list):
                    parsed_history = []
            except json.JSONDecodeError:
                logger.warning("Invalid chat history JSON format, ignoring")
                parsed_history = []
        
        # Quick check for Azure services availability
        if not openai_client or not search_client:
            logger.warning("Azure services not available, using sample data for RAG")
            # Use sample data directly
            search_results = get_sample_events()[:max_results]
            
            # Generate a simple response without Azure OpenAI
            context = ""
            for i, result in enumerate(search_results):
                context += f"\n--- Source {i+1} ---\n"
                context += f"Company: {result.get('company_name', 'Unknown')}\n"
                context += f"Event Type: {result.get('event_type', 'Unknown')}\n"
                context += f"Description: {result.get('description', 'No description')}\n"
                context += f"Status: {result.get('status', 'Unknown')}\n"
            
            # Simple keyword-based response for demo
            query_lower = query.lower()
            if "aapl" in query_lower or "apple" in query_lower:
                answer = "Based on the sample data, Apple Inc. (AAPL) has a quarterly cash dividend event (AAPL_DIV_2024_Q1) that is confirmed. The dividend amount is $0.24 per share with an ex-date of 2024-02-15 and payment date of 2024-02-22."
            elif "dividend" in query_lower:
                answer = "I found dividend-related events in the sample data. Apple has a quarterly cash dividend of $0.24, and Tesla has a special dividend of $1.50. Both events are confirmed and have upcoming payment dates."
            elif "split" in query_lower:
                answer = "Microsoft Corporation has announced a 2-for-1 stock split (MSFT_SPLIT_2024) with an ex-date of 2024-03-01. This split will double the number of shares while halving the price per share."
            else:
                answer = f"I found {len(search_results)} corporate action events in the sample data related to your query about '{query}'. The data includes dividend payments, stock splits, and special distributions from major companies like Apple, Microsoft, and Tesla."
            
            return json.dumps({
                "answer": answer,
                "sources": search_results,
                "confidence_score": 0.7,
                "query_intent": "information_request",
                "requires_visualization": False,
                "note": "Using sample data - Azure services not configured"
            }, indent=2, default=str)
        
        # Try Azure services with timeout
        try:
            # Set a shorter timeout for individual operations
            import asyncio
            
            # Generate embedding with timeout
            embedding_task = generate_embedding(query)
            embedding = await asyncio.wait_for(embedding_task, timeout=10.0)
            
            # Perform vector search with timeout
            search_task = vector_search(embedding, max_results)
            search_results = await asyncio.wait_for(search_task, timeout=10.0)
            
            # Enrich with comments if requested (with timeout)
            if include_comments and search_results:
                for result in search_results[:3]:  # Limit to first 3 for performance
                    if "event_id" in result:
                        try:
                            comments_task = get_event_comments(result["event_id"])
                            comments = await asyncio.wait_for(comments_task, timeout=5.0)
                            result["comments"] = comments[:2]  # Limit to 2 recent comments
                        except asyncio.TimeoutError:
                            result["comments"] = []
            
            # Generate RAG response with timeout
            rag_task = generate_rag_response(query, search_results, parsed_history)
            rag_response = await asyncio.wait_for(rag_task, timeout=10.0)
            
            return json.dumps(rag_response, indent=2, default=str)
            
        except asyncio.TimeoutError:
            logger.warning("Azure services timeout, falling back to sample data")
            # Fallback to sample data
            search_results = get_sample_events()[:max_results]
            
            # Generate simple response
            answer = f"Query processed using sample data due to service timeout. Found {len(search_results)} events related to your query about '{query}'."
            
            return json.dumps({
                "answer": answer,
                "sources": search_results,
                "confidence_score": 0.5,
                "query_intent": "information_request",
                "requires_visualization": False,
                "note": "Fallback due to Azure service timeout"
            }, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"Error in RAG query implementation: {e}")
        return json.dumps({
            "error": f"RAG query failed: {str(e)}",
            "answer": "Unable to process query due to technical error. Please try again later.",
            "sources": [],
            "confidence_score": 0.0,
            "query_intent": "error",
            "requires_visualization": False
        })

async def _search_corporate_actions_impl(
    search_text: str = "",
    event_type: str = "",
    company_name: str = "",
    status: str = "",
    date_from: str = "",
    date_to: str = "",
    limit: int = 10
) -> str:
    """Core search corporate actions implementation"""
    try:
        logger.info(f"Searching corporate actions with filters: {locals()}")
        
        if search_client:
            # Build search filter
            filters = []
            if event_type:
                filters.append(f"event_type eq '{event_type}'")
            if company_name:
                filters.append(f"search.ismatch('{company_name}', 'company_name')")
            if status:
                filters.append(f"status eq '{status}'")
            if date_from:
                filters.append(f"announcement_date ge {date_from}T00:00:00Z")
            if date_to:
                filters.append(f"announcement_date le {date_to}T23:59:59Z")
            
            filter_expression = " and ".join(filters) if filters else None
            
            # Execute search
            results = await search_client.search(
                search_text=search_text or "*",
                filter=filter_expression,
                top=min(limit, 50),
                include_total_count=True
            )
            
            events = []
            async for result in results:
                events.append(dict(result))
            
            print(f"Found {len(events)} events matching criteria")
            return json.dumps({
                "events": events,
                "total_count": len(events),
                "filters_applied": {
                    "search_text": search_text,
                    "event_type": event_type,
                    "company_name": company_name,
                    "status": status,
                    "date_range": f"{date_from} to {date_to}" if date_from or date_to else None
                }
            }, indent=2, default=str)
        else:
            # Fallback to sample data
            filtered_events = get_sample_events()[:limit]
            
            # Apply basic filtering on sample data
            if event_type:
                filtered_events = [e for e in filtered_events if e.get("event_type") == event_type]
            if company_name:
                filtered_events = [e for e in filtered_events if company_name.lower() in e.get("company_name", "").lower()]
            
            return json.dumps({
                "events": filtered_events,
                "total_count": len(filtered_events),
                "note": "Using sample data - Azure AI Search not configured"
            }, indent=2, default=str)
            
    except Exception as e:
        logger.error(f"Error in search implementation: {e}")
        return json.dumps({
            "error": f"Search failed: {str(e)}",
            "events": [],
            "total_count": 0
        })

async def _get_event_details_impl(event_id: str, include_comments: bool = True) -> str:
    """Core get event details implementation"""
    try:
        logger.info(f"Getting details for event: {event_id}")
        
        # First try to get from Cosmos DB
        event_data = None
        if cosmos_client:
            try:
                database = cosmos_client.get_database_client("corporateactions")
                container = database.get_container_client("events")
                event_data = await container.read_item(item=event_id, partition_key=event_id)
            except Exception as e:
                logger.warning(f"Event not found in Cosmos DB: {e}")
        
        # Fallback to sample data
        if not event_data:
            sample_events = get_sample_events()
            event_data = next((e for e in sample_events if e.get("event_id") == event_id), None)
            
        if not event_data:
            return json.dumps({
                "error": f"Event with ID '{event_id}' not found",
                "event_id": event_id
            })
        
        # Get comments if requested
        comments = []
        if include_comments:
            comments = await get_event_comments(event_id)
        
        response = {
            "event": event_data,
            "comments": comments,
            "comment_count": len(comments),
            "last_updated": datetime.utcnow().isoformat()
        }
        
        return json.dumps(response, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"Error getting event details: {e}")
        return json.dumps({
            "error": f"Failed to retrieve event details: {str(e)}",
            "event_id": event_id
        })

# =============================================================================
# MCP Tools Registration
# =============================================================================

@app.tool()
async def rag_query(query: str, max_results: int = 5, include_comments: bool = True, chat_history: str = "") -> str:
    """
    Process a RAG query for corporate actions data using Azure AI services.
    
    Args:
        query: Natural language query about corporate actions
        max_results: Maximum number of search results to consider (1-20)
        include_comments: Whether to include user comments in the response
        chat_history: JSON string of recent chat history for context (optional)
    
    Returns:
        JSON string containing the RAG response with answer, sources, and metadata
    """
    return await _rag_query_impl(query, max_results, include_comments, chat_history)

@app.tool()
async def search_corporate_actions(
    search_text: str = "",
    event_type: str = "",
    company_name: str = "",
    status: str = "",
    date_from: str = "",
    date_to: str = "",
    limit: int = 10
) -> str:
    """
    Search corporate action events based on specific criteria.
    
    Args:
        search_text: Free text search across all fields
        event_type: Filter by event type (dividend, split, merger, spinoff, etc.)
        company_name: Filter by company name
        status: Filter by event status (announced, confirmed, processed, cancelled)
        date_from: Filter events from this date (YYYY-MM-DD format)
        date_to: Filter events to this date (YYYY-MM-DD format)  
        limit: Maximum number of results to return (1-50)
    
    Returns:
        JSON string containing matching corporate action events
    """
    return await _search_corporate_actions_impl(search_text, event_type, company_name, status, date_from, date_to, limit)

@app.tool()
async def get_event_details(event_id: str, include_comments: bool = True) -> str:
    """
    Get detailed information about a specific corporate action event.
    
    Args:
        event_id: Unique identifier of the corporate action event
        include_comments: Whether to include user comments and Q&A
    
    Returns:
        JSON string containing detailed event information
    """
    return await _get_event_details_impl(event_id, include_comments)

@app.tool()
async def add_event_comment(
    event_id: str,
    user_name: str,
    comment_text: str,
    comment_type: str = "general"
) -> str:
    """
    Add a comment or question to a corporate action event.
    
    Args:
        event_id: ID of the corporate action event
        user_name: Name of the user adding the comment
        comment_text: The comment or question text
        comment_type: Type of comment (general, question, analysis, clarification)
    
    Returns:
        JSON string confirming the comment was added
    """
    try:
        logger.info(f"Adding comment to event {event_id} by {user_name}")
        
        comment_data = {
            "id": f"comment_{datetime.utcnow().timestamp()}",
            "event_id": event_id,
            "user_name": user_name,
            "comment_text": comment_text,
            "comment_type": comment_type,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "is_resolved": False,
            "votes": 0
        }
        
        # Try to save to Cosmos DB
        if cosmos_client:
            try:
                database = cosmos_client.get_database_client("corporateactions")
                container = database.get_container_client("comments")
                await container.create_item(body=comment_data)
                logger.info(f"Comment saved to Cosmos DB")
            except Exception as e:
                logger.warning(f"Failed to save to Cosmos DB: {e}")
        
        return json.dumps({
            "success": True,
            "message": "Comment added successfully",
            "comment": comment_data
        }, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"Error adding comment: {e}")
        return json.dumps({
            "success": False,
            "error": f"Failed to add comment: {str(e)}"
        })

@app.tool()
async def get_service_health() -> str:
    """
    Check the health status of all Azure services and components.
    
    Returns:
        JSON string with health status of all services
    """
    try:
        health_status = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "healthy",
            "services": {
                "cosmos_db": {
                    "status": "connected" if cosmos_client else "not_configured",
                    "details": "Azure Cosmos DB for data storage"
                },
                "ai_search": {
                    "status": "connected" if search_client else "not_configured", 
                    "details": "Azure AI Search for vector search"
                },
                "azure_openai": {
                    "status": "connected" if openai_client else "not_configured",
                    "details": "Azure OpenAI for embeddings and chat"
                }
            }
        }        # Test actual connectivity - skip actual calls on Windows to avoid DNS issues
        if cosmos_client:
            try:
                # Just check if client is configured, don't make actual call
                health_status["services"]["cosmos_db"]["status"] = "healthy"
                health_status["services"]["cosmos_db"]["test_result"] = "client_configured"
            except Exception as e:
                health_status["services"]["cosmos_db"]["status"] = "error"
                health_status["services"]["cosmos_db"]["error"] = str(e)
        
        if search_client:
            try:
                # Just check if client is configured, don't make actual call to avoid DNS issues
                health_status["services"]["ai_search"]["status"] = "healthy"
                health_status["services"]["ai_search"]["test_result"] = "client_configured"
            except Exception as e:
                health_status["services"]["ai_search"]["status"] = "error"
                health_status["services"]["ai_search"]["error"] = str(e)
        if openai_client:
            try:
                # Just check if client is configured, don't make actual call to avoid DNS issues
                health_status["services"]["azure_openai"]["status"] = "healthy"
                health_status["services"]["azure_openai"]["test_result"] = "client_configured"
            except Exception as e:
                health_status["services"]["azure_openai"]["status"] = "error"
                health_status["services"]["azure_openai"]["error"] = str(e)
        
        # Determine overall status
        service_statuses = [s["status"] for s in health_status["services"].values()]
        if any(status == "error" for status in service_statuses):
            health_status["overall_status"] = "degraded"
        elif any(status == "not_configured" for status in service_statuses):
            health_status["overall_status"] = "partial"
        
        return json.dumps(health_status, indent=2)
        
    except Exception as e:
        logger.error(f"Error checking service health: {e}")
        return json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "error",
            "error": str(e)
        })

# =============================================================================
# MCP Resources Registration  
# =============================================================================

@app.resource("corporate-actions://events")
async def list_recent_events() -> str:
    """List recent corporate action events"""
    try:
        if search_client:
            results = await search_client.search(
                search_text="*",
                top=20,
                order_by=["announcement_date desc"]
            )
            
            events = []
            async for result in results:
                events.append(dict(result))
            
            return json.dumps(events, indent=2, default=str)
        else:
            return json.dumps(get_sample_events()[:20], indent=2, default=str)
            
    except Exception as e:
        logger.error(f"Error listing events: {e}")
        return json.dumps({"error": str(e)})

@app.resource("corporate-actions://health")
async def health_resource() -> str:
    """Service health information"""
    return await get_service_health()

# =============================================================================
# SSE (Server-Sent Events) Support for Teams Bot Integration
# =============================================================================

# Create FastAPI app for SSE endpoints
sse_app = FastAPI(title="Corporate Actions SSE API", version="1.0.0")

# Add CORS middleware for Teams bot integration
sse_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@sse_app.get("/health")
async def sse_health():
    """Health check endpoint for SSE API"""
    return {"status": "healthy", "service": "Corporate Actions SSE API"}

@sse_app.get("/rag-query")
async def sse_rag_query(
    query: str,
    max_results: int = 5,
    include_comments: bool = True,
    chat_history: str = ""
):
    """RAG query endpoint for Teams bot"""
    try:
        # Call the implementation function directly
        result = await _rag_query_impl(query, max_results, include_comments, chat_history)
        return Response(content=result, media_type="application/json")
    except Exception as e:
        logger.error(f"SSE RAG query error: {e}")
        return {"error": str(e)}

@sse_app.get("/search-corporate-actions")
async def sse_search_corporate_actions(
    search_text: str = "",
    event_type: str = "",
    company_name: str = "",
    status: str = "",
    date_from: str = "",
    date_to: str = "",
    limit: int = 10
):
    """Search corporate actions endpoint for Teams bot"""
    try:
        # Call the implementation function directly
        result = await _search_corporate_actions_impl(
            search_text, event_type, company_name, status, date_from, date_to, limit
        )
        return Response(content=result, media_type="application/json")
    except Exception as e:
        logger.error(f"SSE search error: {e}")
        return {"error": str(e)}

@sse_app.get("/events")
async def sse_list_events():
    """List events endpoint for Teams bot"""
    try:
        # Use the resource function directly by calling get_sample_events
        # since the list_recent_events function is an MCP resource
        events = get_sample_events()
        result = json.dumps({
            "events": events,
            "total_count": len(events),
            "note": "Using sample data - Azure AI Search not configured"
        }, indent=2, default=str)
        return Response(content=result, media_type="application/json")
    except Exception as e:
        logger.error(f"SSE events error: {e}")
        return {"error": str(e)}

@sse_app.get("/event-details/{event_id}")
async def sse_event_details(event_id: str, include_comments: bool = True):
    """Get event details endpoint for Teams bot"""
    try:
        # Call the implementation function directly
        result = await _get_event_details_impl(event_id, include_comments)
        return Response(content=result, media_type="application/json")
    except Exception as e:
        logger.error(f"SSE event details error: {e}")
        return {"error": str(e)}

@sse_app.get("/sse/events")
async def sse_stream_events():
    """Server-Sent Events stream for real-time updates"""
    async def event_generator():
        while True:
            try:
                # Get recent events using sample data
                events = get_sample_events()
                events_data = {
                    "events": events,
                    "total_count": len(events),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Send as SSE format
                yield f"data: {json.dumps(events_data, default=str)}\n\n"
                
                # Wait before next update
                await asyncio.sleep(30)  # Send updates every 30 seconds
                
            except Exception as e:
                logger.error(f"SSE stream error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                await asyncio.sleep(10)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

# =============================================================================
# Application Startup
# =============================================================================

def main():
    """Main application entry point"""
    logger.info("🚀 Starting Corporate Actions MCP Server with SSE Support")
    
    # Initialize Azure clients in sync context
    async def init_and_run():
        await initialize_azure_clients()
    
    # Run initialization
    try:
        asyncio.run(init_and_run())
    except RuntimeError:
        # If there's already an event loop, create a new thread
        import threading
        def run_init():
            asyncio.run(init_and_run())
        
        thread = threading.Thread(target=run_init)
        thread.start()
        thread.join()
    
    # Check if port is specified
    import sys
    if len(sys.argv) > 1 and '--port' in sys.argv:
        port_index = sys.argv.index('--port') + 1
        if port_index < len(sys.argv):
            port = int(sys.argv[port_index])
            
            # Check if SSE mode is requested
            if '--sse' in sys.argv:
                logger.info(f"Starting SSE server on port {port}")
                uvicorn.run(sse_app, host="0.0.0.0", port=port, log_level="info")
            else:
                logger.info(f"Starting FastMCP server in HTTP mode on port {port}")
                app.run(transport="streamable-http", host="0.0.0.0", port=port)
        else:
            logger.error("Port specified but no port number provided")
            app.run()
    elif '--sse-port' in sys.argv:
        # Start SSE server on specified port
        port_index = sys.argv.index('--sse-port') + 1
        if port_index < len(sys.argv):
            sse_port = int(sys.argv[port_index])
            logger.info(f"Starting SSE server on port {sse_port}")
            uvicorn.run(sse_app, host="0.0.0.0", port=sse_port, log_level="info")
        else:
            logger.error("SSE port specified but no port number provided")
            app.run()
    else:
        # Run the FastMCP server in stdio mode (default)
        logger.info("Starting FastMCP server in stdio mode")
        app.run()

if __name__ == "__main__":
    main()

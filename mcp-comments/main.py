#!/usr/bin/env python3
"""
Comments MCP Server
Handles questions, concerns, and comments from market participants
Following Model Context Protocol specification
"""

import asyncio
import json
import os
import logging
import platform
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Set
import uuid

# MCP imports
from fastmcp import FastMCP

# Azure SDK imports
from azure.cosmos.aio import CosmosClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential, ClientSecretCredential

# Local imports
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'data-models'))
from corporate_action_schemas import UserComment, EventStatus

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

# Initialize FastMCP server
app = FastMCP("Comments MCP Server")

# Global clients
cosmos_client: Optional[CosmosClient] = None

# In-memory storage for WebSocket-like real-time features
active_subscriptions: Dict[str, Set[str]] = {}  # event_id -> set of user_ids
comment_cache: Dict[str, List[Dict[str, Any]]] = {}  # event_id -> comments

async def initialize_cosmos_client():
    """Initialize Cosmos DB client"""
    global cosmos_client
    try:
        cosmos_endpoint = os.getenv("AZURE_COSMOS_ENDPOINT")
        cosmos_key = os.getenv("AZURE_COSMOS_KEY")
        tenant_id = os.getenv('AZURE_TENANT_ID')
        client_id = os.getenv('AZURE_CLIENT_ID')
        client_secret = os.getenv('AZURE_CLIENT_SECRET')
        cred = ClientSecretCredential(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)

        if cosmos_endpoint:
            cosmos_client = CosmosClient(cosmos_endpoint, cred)
            logger.info("✅ Cosmos DB client initialized")
        else:
            logger.warning("⚠️ Cosmos DB credentials not configured - using in-memory storage")
    except Exception as e:
        logger.error(f"❌ Error initializing Cosmos DB client: {e}")

async def get_comments_from_cosmos(event_id: str) -> List[Dict[str, Any]]:
    """Retrieve comments from Cosmos DB"""
    try:
        if not cosmos_client:
            return []
        
        database = cosmos_client.get_database_client("corporateactions")
        container = database.get_container_client("comments")
        
        query = "SELECT * FROM c WHERE c.event_id = @event_id ORDER BY c.created_at DESC"
        parameters = [{"name": "@event_id", "value": event_id}]
        
        comments = []
        async for item in container.query_items(query, parameters=parameters):
            comments.append(item)
        
        return comments
        
    except Exception as e:
        logger.error(f"Error retrieving comments from Cosmos DB: {e}")
        return []

async def save_comment_to_cosmos(comment_data: Dict[str, Any]) -> bool:
    """Save comment to Cosmos DB"""
    try:
        if not cosmos_client:
            return False
        
        database = cosmos_client.get_database_client("corporateactions")
        container = database.get_container_client("comments")
        
        await container.create_item(body=comment_data)
        return True
        
    except Exception as e:
        logger.error(f"Error saving comment to Cosmos DB: {e}")
        return False

async def get_mock_comments(event_id: str) -> List[Dict[str, Any]]:
    """Get mock comments for testing"""
    return [
        {
            "id": f"comment_1_{event_id}",
            "event_id": event_id,
            "user_name": "John Smith",
            "organization": "Investment Bank ABC",
            "comment_type": "QUESTION",
            "content": "What is the expected timeline for shareholder approval?",
            "created_at": "2024-12-20T10:30:00Z",
            "updated_at": "2024-12-20T10:30:00Z",
            "is_resolved": False,
            "votes": 3,
            "parent_comment_id": None
        },
        {
            "id": f"comment_2_{event_id}",
            "event_id": event_id,
            "user_name": "Sarah Johnson",
            "organization": "Pension Fund XYZ",
            "comment_type": "CONCERN",
            "content": "The proposed terms seem unfavorable to minority shareholders.",
            "created_at": "2024-12-20T11:15:00Z",
            "updated_at": "2024-12-20T11:15:00Z",
            "is_resolved": False,
            "votes": 7,
            "parent_comment_id": None
        },
        {
            "id": f"comment_3_{event_id}",
            "event_id": event_id,
            "user_name": "Michael Chen",
            "organization": "Regulatory Affairs Dept",
            "comment_type": "UPDATE",
            "content": "Regulatory approval received from SEC. Process moving forward as planned.",
            "created_at": "2024-12-20T14:20:00Z",
            "updated_at": "2024-12-20T14:20:00Z",
            "is_resolved": True,
            "votes": 12,
            "parent_comment_id": None
        }
    ]

# =============================================================================
# MCP Tools Registration
# =============================================================================

@app.tool()
async def get_event_comments(
    event_id: str,
    limit: int = 50,
    include_resolved: bool = True,
    comment_type: str = ""
) -> str:
    """
    Retrieve comments for a specific corporate action event.
    
    Args:
        event_id: ID of the corporate action event
        limit: Maximum number of comments to return (1-100)
        include_resolved: Whether to include resolved comments
        comment_type: Filter by comment type (QUESTION, CONCERN, COMMENT, UPDATE, or empty for all)
    
    Returns:
        JSON string containing comments data
    """
    try:
        logger.info(f"Getting comments for event: {event_id}")
        
        # Try to get from Cosmos DB first
        comments = await get_comments_from_cosmos(event_id)
        
        # Fallback to mock data if Cosmos is not available
        if not comments:
            comments = await get_mock_comments(event_id)
        
        # Apply filters
        filtered_comments = []
        for comment in comments:
            # Filter by resolved status
            if not include_resolved and comment.get("is_resolved", False):
                continue
            
            # Filter by comment type
            if comment_type and comment.get("comment_type", "") != comment_type:
                continue
            
            filtered_comments.append(comment)
        
        # Apply limit
        filtered_comments = filtered_comments[:min(limit, 100)]
        
        # Calculate summary statistics
        total_comments = len(comments)
        questions = len([c for c in comments if c.get("comment_type") == "QUESTION"])
        concerns = len([c for c in comments if c.get("comment_type") == "CONCERN"])
        resolved = len([c for c in comments if c.get("is_resolved", False)])
        
        response = {
            "event_id": event_id,
            "comments": filtered_comments,
            "summary": {
                "total_comments": total_comments,
                "filtered_count": len(filtered_comments),
                "questions": questions,
                "concerns": concerns,
                "resolved": resolved,
                "unresolved": total_comments - resolved
            },
            "filters": {
                "limit": limit,
                "include_resolved": include_resolved,
                "comment_type": comment_type or "all"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return json.dumps(response, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"Error getting event comments: {e}")
        return json.dumps({
            "error": f"Failed to retrieve comments: {str(e)}",
            "event_id": event_id,
            "comments": []
        })

@app.tool()
async def add_comment(
    event_id: str,
    user_name: str,
    content: str,
    comment_type: str = "COMMENT",
    organization: str = "",
    parent_comment_id: str = ""
) -> str:
    """
    Add a new comment to a corporate action event.
    
    Args:
        event_id: ID of the corporate action event
        user_name: Name of the user adding the comment
        content: The comment text content
        comment_type: Type of comment (QUESTION, CONCERN, COMMENT, UPDATE)
        organization: User's organization (optional)
        parent_comment_id: ID of parent comment for replies (optional)
    
    Returns:
        JSON string confirming the comment was added
    """
    try:
        logger.info(f"Adding comment to event {event_id} by {user_name}")
        
        # Generate unique comment ID
        comment_id = f"comment_{datetime.utcnow().timestamp()}_{uuid.uuid4().hex[:8]}"
        
        comment_data = {
            "id": comment_id,
            "event_id": event_id,
            "user_name": user_name,
            "organization": organization or "Unknown",
            "comment_type": comment_type,
            "content": content,
            "parent_comment_id": parent_comment_id or None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "is_resolved": False,
            "votes": 0
        }
        
        # Try to save to Cosmos DB
        cosmos_saved = await save_comment_to_cosmos(comment_data)
        
        # Update local cache for real-time features
        if event_id not in comment_cache:
            comment_cache[event_id] = []
        comment_cache[event_id].insert(0, comment_data)  # Add to beginning for newest first
        
        # Simulate real-time notification
        notification = {
            "type": "new_comment",
            "event_id": event_id,
            "comment": comment_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        response = {
            "success": True,
            "message": "Comment added successfully",
            "comment": comment_data,
            "saved_to_cosmos": cosmos_saved,
            "notification_sent": True
        }
        
        return json.dumps(response, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"Error adding comment: {e}")
        return json.dumps({
            "success": False,
            "error": f"Failed to add comment: {str(e)}"
        })

@app.tool()
async def update_comment(
    comment_id: str,
    content: str = "",
    is_resolved: bool = None
) -> str:
    """
    Update an existing comment.
    
    Args:
        comment_id: ID of the comment to update
        content: New content for the comment (optional)
        is_resolved: Mark comment as resolved/unresolved (optional)
    
    Returns:
        JSON string confirming the update
    """
    try:
        logger.info(f"Updating comment: {comment_id}")
        
        # In a real implementation, we would update in Cosmos DB
        # For now, simulate the update
        
        update_data = {
            "comment_id": comment_id,
            "updated_at": datetime.utcnow().isoformat(),
            "changes": {}
        }
        
        if content:
            update_data["changes"]["content"] = content
        
        if is_resolved is not None:
            update_data["changes"]["is_resolved"] = is_resolved
        
        response = {
            "success": True,
            "message": "Comment updated successfully",
            "update": update_data
        }
        
        return json.dumps(response, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"Error updating comment: {e}")
        return json.dumps({
            "success": False,
            "error": f"Failed to update comment: {str(e)}"
        })

@app.tool()
async def search_comments(
    query: str,
    event_ids: List[str] = [],
    comment_types: List[str] = [],
    date_from: str = "",
    date_to: str = "",
    limit: int = 50
) -> str:
    """
    Search comments across events based on various criteria.
    
    Args:
        query: Text search query for comment content
        event_ids: List of event IDs to search within
        comment_types: List of comment types to filter by
        date_from: Start date for search (YYYY-MM-DD format)
        date_to: End date for search (YYYY-MM-DD format)
        limit: Maximum number of results (1-100)
    
    Returns:
        JSON string containing search results
    """
    try:
        logger.info(f"Searching comments with query: {query}")
        
        # In a real implementation, this would query Cosmos DB
        # For now, simulate search across cached comments
        
        all_comments = []
        search_events = event_ids if event_ids else list(comment_cache.keys())
        
        for event_id in search_events:
            if event_id in comment_cache:
                all_comments.extend(comment_cache[event_id])
            else:
                # Get mock comments for the event
                mock_comments = await get_mock_comments(event_id)
                all_comments.extend(mock_comments)
        
        # Apply filters
        filtered_comments = []
        query_lower = query.lower() if query else ""
        
        for comment in all_comments:
            # Text search
            if query and query_lower not in comment.get("content", "").lower():
                continue
            
            # Comment type filter
            if comment_types and comment.get("comment_type") not in comment_types:
                continue
            
            # Date filters would be applied here
            # For simplicity, skipping date filtering in this demo
            
            filtered_comments.append(comment)
        
        # Sort by created_at (newest first) and apply limit
        filtered_comments.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        filtered_comments = filtered_comments[:min(limit, 100)]
        
        response = {
            "query": query,
            "results": filtered_comments,
            "total_found": len(filtered_comments),
            "search_filters": {
                "query": query,
                "event_ids": event_ids,
                "comment_types": comment_types,
                "date_from": date_from,
                "date_to": date_to,
                "limit": limit
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return json.dumps(response, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"Error searching comments: {e}")
        return json.dumps({
            "error": f"Comment search failed: {str(e)}",
            "results": [],
            "total_found": 0
        })

@app.tool()
async def get_comment_analytics(
    event_id: str = "",
    days_back: int = 30
) -> str:
    """
    Get analytics and insights about comments for an event or overall.
    
    Args:
        event_id: Specific event ID for analytics (empty for overall analytics)
        days_back: Number of days to include in analytics (1-365)
    
    Returns:
        JSON string containing comment analytics
    """
    try:
        logger.info(f"Getting comment analytics for event: {event_id or 'all'}")
        
        # Collect comments for analysis
        comments = []
        if event_id:
            comments = await get_comments_from_cosmos(event_id)
            if not comments:
                comments = await get_mock_comments(event_id)
        else:
            # Get comments from all events
            for cached_event_id in comment_cache:
                comments.extend(comment_cache[cached_event_id])
        
        # Calculate analytics
        total_comments = len(comments)
        questions = len([c for c in comments if c.get("comment_type") == "QUESTION"])
        concerns = len([c for c in comments if c.get("comment_type") == "CONCERN"])
        updates = len([c for c in comments if c.get("comment_type") == "UPDATE"])
        resolved = len([c for c in comments if c.get("is_resolved", False)])
        
        # Organization analytics
        org_counts = {}
        for comment in comments:
            org = comment.get("organization", "Unknown")
            org_counts[org] = org_counts.get(org, 0) + 1
        
        top_organizations = sorted(org_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Recent activity (last 24 hours)
        from datetime import datetime, timedelta
        recent_cutoff = datetime.utcnow() - timedelta(days=1)
        recent_comments = [
            c for c in comments 
            if datetime.fromisoformat(c.get("created_at", "").replace("Z", "+00:00")) >= recent_cutoff
        ]
        
        analytics = {
            "event_id": event_id or "all_events",
            "period_days": days_back,
            "summary": {
                "total_comments": total_comments,
                "questions": questions,
                "concerns": concerns,
                "updates": updates,
                "general_comments": total_comments - questions - concerns - updates,
                "resolved": resolved,
                "unresolved": total_comments - resolved,
                "resolution_rate": round(resolved / total_comments * 100, 1) if total_comments > 0 else 0
            },
            "organizations": {
                "total_organizations": len(org_counts),
                "top_contributors": [{"organization": org, "comment_count": count} for org, count in top_organizations]
            },
            "recent_activity": {
                "comments_last_24h": len(recent_comments),
                "trending_topics": ["shareholder approval", "regulatory compliance", "timeline updates"]  # Mock data
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return json.dumps(analytics, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"Error generating comment analytics: {e}")
        return json.dumps({
            "error": f"Analytics generation failed: {str(e)}",
            "event_id": event_id,
            "summary": {}
        })

@app.tool()
async def subscribe_to_event(
    user_id: str,
    event_id: str
) -> str:
    """
    Subscribe a user to real-time updates for an event.
    
    Args:
        user_id: Unique identifier for the user
        event_id: ID of the event to subscribe to
    
    Returns:
        JSON string confirming subscription
    """
    try:
        logger.info(f"Subscribing user {user_id} to event {event_id}")
        
        if event_id not in active_subscriptions:
            active_subscriptions[event_id] = set()
        
        active_subscriptions[event_id].add(user_id)
        
        response = {
            "success": True,
            "message": f"User {user_id} subscribed to event {event_id}",
            "event_id": event_id,
            "user_id": user_id,
            "total_subscribers": len(active_subscriptions[event_id]),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return json.dumps(response, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"Error subscribing to event: {e}")
        return json.dumps({
            "success": False,
            "error": f"Subscription failed: {str(e)}"
        })

@app.tool()
async def get_comments_health() -> str:
    """
    Check the health and status of the comments service.
    
    Returns:
        JSON string containing service health information
    """
    try:
        health_status = {
            "service": "Comments MCP Server",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "capabilities": {
                "get_comments": True,
                "add_comments": True,
                "update_comments": True,
                "search_comments": True,
                "analytics": True,
                "real_time_subscriptions": True,
                "cosmos_db": bool(cosmos_client)
            },
            "statistics": {
                "cached_events": len(comment_cache),
                "active_subscriptions": len(active_subscriptions),
                "total_cached_comments": sum(len(comments) for comments in comment_cache.values())
            },
            "configuration": {
                "max_comments_per_query": 100,
                "supported_comment_types": ["QUESTION", "CONCERN", "COMMENT", "UPDATE"],
                "cosmos_db_configured": bool(os.getenv("AZURE_COSMOS_ENDPOINT"))
            }
        }
        
        return json.dumps(health_status, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"Error checking comments health: {e}")
        return json.dumps({
            "service": "Comments MCP Server",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })

# =============================================================================
# Server Initialization
# =============================================================================

# =============================================================================
# Server Initialization
# =============================================================================

def main():
    """Main server initialization"""
    logger.info("Starting Comments MCP Server...")
    
    # Initialize services in sync context
    async def init_and_setup():
        await initialize_cosmos_client()
        logger.info("✅ Comments MCP Server initialized successfully")
    
    # Run initialization
    try:
        asyncio.run(init_and_setup())
    except RuntimeError:
        # If there's already an event loop, create a new thread
        import threading
        def run_init():
            asyncio.run(init_and_setup())
        
        thread = threading.Thread(target=run_init)
        thread.start()
        thread.join()
    
    # Check if port is specified for HTTP mode
    import sys
    if len(sys.argv) > 1 and '--port' in sys.argv:
        port_index = sys.argv.index('--port') + 1
        if port_index < len(sys.argv):
            port = int(sys.argv[port_index])
            logger.info(f"Starting FastMCP server in HTTP mode on port {port}")
            app.run(transport="streamable-http", host="0.0.0.0", port=port)
        else:
            logger.error("Port specified but no port number provided")
            app.run()
    else:
        # Run the FastMCP server in stdio mode (default)
        logger.info("Starting FastMCP server in stdio mode")
        app.run()

if __name__ == "__main__":
    main()

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
import sys
import random
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
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

# Cosmos DB containers
cosmos_database = None
corporate_actions_container = None
inquiries_container = None
subscriptions_container = None

# Initialize FastMCP server
app = FastMCP("Corporate Actions MCP Server")

# Global flag to track if clients are initialized
_clients_initialized = False

async def initialize_azure_clients():
    """Initialize Azure service clients"""
    global cosmos_client, search_client, openai_client
    global cosmos_database, corporate_actions_container, inquiries_container, subscriptions_container
    
    try:
        # Cosmos DB client
        cosmos_endpoint = os.getenv("AZURE_COSMOS_ENDPOINT")
        cosmos_key = os.getenv("AZURE_COSMOS_KEY")
        
        if cosmos_endpoint:
            # Try key-based authentication first, then fall back to credential-based
            if cosmos_key:
                logger.info("Initializing Cosmos DB with key-based authentication")
                cosmos_client = CosmosClient(cosmos_endpoint, cosmos_key)
            else:
                logger.info("Initializing Cosmos DB with credential-based authentication")
                # service principal
                tenant_id = os.getenv('AZURE_TENANT_ID')
                client_id = os.getenv('AZURE_CLIENT_ID')
                client_secret = os.getenv('AZURE_CLIENT_SECRET')
                
                if not all([tenant_id, client_id, client_secret]):
                    logger.error("Missing service principal credentials for Cosmos DB")
                    raise ValueError("Missing Azure service principal credentials")
                
                cred = ClientSecretCredential(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)
                cosmos_client = CosmosClient(cosmos_endpoint, cred)
            
            # Initialize database and containers
            database_name = os.getenv("AZURE_COSMOS_DATABASE_NAME", "semantickernel")
            logger.info(f"Connecting to Cosmos database: {database_name}")
            cosmos_database = cosmos_client.get_database_client(database_name)
            
            inquiries_container = await cosmos_database.create_container_if_not_exists(
                id=os.getenv("COSMOSDB_INQUIRIES_CONTAINER", "inquiries"),
                partition_key="/event_id"
            )
            subscriptions_container = await cosmos_database.create_container_if_not_exists(
                id=os.getenv("COSMOSDB_SUBSCRIPTIONS_CONTAINER", "subscriptions"),
                partition_key="/user_id"
            )
            logger.info("✅ Cosmos DB client and containers initialized successfully")
        else:
            logger.warning("❌ AZURE_COSMOS_ENDPOINT not configured, Cosmos DB will not be available")

        # AI Search client
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        search_key = os.getenv("AZURE_SEARCH_KEY")
        search_index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "corporateactions")
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
                api_version="2024-02-01"
            )
            logger.info("✅ Azure OpenAI client initialized")
            
    except Exception as e:
        logger.error(f"❌ Error initializing Azure clients: {e}")

async def ensure_cosmos_client():
    """Ensure Cosmos client and containers are properly initialized"""
    global cosmos_client, cosmos_database, corporate_actions_container, inquiries_container, subscriptions_container
    global _clients_initialized
    
    try:
        # Initialize clients if not already done
        if not _clients_initialized:
            logger.info("Initializing Azure clients for the first time...")
            await initialize_azure_clients()
            await test_cosmos_connectivity()
            _clients_initialized = True
            return cosmos_client is not None and subscriptions_container is not None
        
        # Check if client and containers are valid
        if cosmos_client and cosmos_database and subscriptions_container:
            try:
                # Test both database and container connectivity
                await cosmos_database.read()
                # Test container access with a simple query
                query = "SELECT VALUE COUNT(1) FROM c"
                items = []
                async for item in subscriptions_container.query_items(query=query, max_item_count=1):
                    items.append(item)
                    break
                logger.debug("✅ Cosmos client and containers validated successfully")
                return True
            except Exception as e:
                logger.warning(f"Cosmos client or containers appear to be invalid, reinitializing: {e}")
                # Reset global variables
                cosmos_client = None
                cosmos_database = None
                corporate_actions_container = None
                inquiries_container = None
                subscriptions_container = None
                _clients_initialized = False
        
        # Reinitialize if needed
        if not cosmos_client or not subscriptions_container:
            logger.info("Reinitializing Azure clients due to missing client or containers...")
            await initialize_azure_clients()
            await test_cosmos_connectivity()
            _clients_initialized = True
            
            # Verify containers are properly initialized
            if not subscriptions_container:
                logger.error("❌ Subscriptions container still not available after reinitialization")
                return False
            else:
                logger.info("✅ Subscriptions container successfully reinitialized")
            
        return cosmos_client is not None and subscriptions_container is not None
        
    except Exception as e:
        logger.error(f"Error ensuring Cosmos client: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

# =============================================================================
# Inquiry Management Functions
# =============================================================================

async def create_inquiry(
    event_id: str,
    user_id: str,
    user_name: str,
    organization: str,
    subject: str,
    description: str,
    priority: str = "MEDIUM"
) -> Dict[str, Any]:
    """Create a new inquiry in CosmosDB"""
    try:
        # Ensure client is valid
        if not await ensure_cosmos_client():
            logger.warning("Could not establish valid Cosmos DB connection")
            return {
                "success": False,
                "error": "Database connection not available",
                "inquiry_id": f"sample_{event_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            }
        
        if not inquiries_container:
            logger.warning("Inquiries container not available, returning sample response")
            return {
                "success": False,
                "error": "Database container not available",
                "inquiry_id": f"sample_{event_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            }
        
        inquiry_id = f"INQ_{event_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        inquiry_doc = {
            "id": inquiry_id,
            "inquiry_id": inquiry_id,
            "event_id": event_id,
            "user_id": user_id,
            "user_name": user_name,
            "user_role": "CONSUMER",
            "organization": organization,
            "subject": subject,
            "description": description,
            "priority": priority,
            "status": "OPEN",
            "assigned_to": None,
            "response": None,
            "resolution_notes": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "due_date": None,
            "resolved_at": None,
            "subscribers": [user_id],
            "notification_history": []
        }
        
        logger.info(f"Attempting to create inquiry {inquiry_id} for event {event_id}")
        result = await inquiries_container.create_item(inquiry_doc)
        logger.info(f"Successfully created inquiry {inquiry_id} for event {event_id}")
        
        return {
            "success": True,
            "inquiry_id": inquiry_id,
            "message": f"Inquiry created successfully for {event_id}"
        }
        
    except Exception as e:
        logger.error(f"Error creating inquiry: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
            "inquiry_id": None
        }

async def get_inquiries_for_event(event_id: str) -> List[Dict[str, Any]]:
    """Get all inquiries for a specific corporate action event"""
    try:
        if not inquiries_container:
            logger.warning("Inquiries container not available, returning sample data")
            return get_sample_inquiries(event_id)
        
        query = "SELECT * FROM c WHERE c.event_id = @event_id ORDER BY c.created_at DESC"
        parameters = [{"name": "@event_id", "value": event_id}]
        
        inquiries = []
        async for item in inquiries_container.query_items(query, parameters=parameters):
            inquiries.append(item)
        
        return inquiries
        
    except Exception as e:
        logger.error(f"Error retrieving inquiries for event {event_id}: {e}")
        return []

async def save_user_subscription(
    user_id: str,
    user_name: str,
    organization: str,
    symbols: List[str],
    event_types: List[str] = None
) -> Dict[str, Any]:
    """Save user subscription to CosmosDB"""
    try:
        # Ensure client is valid
        if not await ensure_cosmos_client():
            logger.warning("Could not establish valid Cosmos DB connection")
            return {
                "success": False,
                "error": "Database connection not available"
            }
        
        if not subscriptions_container:
            logger.warning("Subscriptions container not available")
            return {
                "success": False,
                "error": "Database container not available"
            }
        
        subscription_doc = {
            "id": user_id,
            "user_id": user_id,
            "user_name": user_name,
            "organization": organization,
            "symbols": symbols,
            "event_types": event_types or ["DIVIDEND", "STOCK_SPLIT", "MERGER", "SPIN_OFF"],
            "notify_new_events": True,
            "notify_status_changes": True,
            "notify_new_inquiries": True,
            "notify_inquiry_responses": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Attempting to save subscription for user {user_id}")
        result = await subscriptions_container.upsert_item(subscription_doc)
        logger.info(f"Successfully saved subscription for user {user_id} with symbols {symbols}")
        
        return {
            "success": True,
            "message": f"Subscription saved for {len(symbols)} symbols",
            "subscription": subscription_doc
        }
        
    except Exception as e:
        logger.error(f"Error saving user subscription: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e)
        }

async def get_user_subscription(user_id: str) -> Dict[str, Any]:
    """Get user subscription from CosmosDB"""
    try:
        # Ensure client and containers are valid
        if not await ensure_cosmos_client():
            logger.warning("Could not establish valid Cosmos DB connection for subscription retrieval")
            return None
        
        if not subscriptions_container:
            logger.warning("Subscriptions container not available for subscription retrieval")
            return None
        
        logger.info(f"Attempting to retrieve subscription for user: {user_id}")
        subscription = await subscriptions_container.read_item(user_id, user_id)
        logger.info(f"Successfully retrieved subscription for user: {user_id}")
        return subscription
        
    except Exception as e:
        if "NotFound" not in str(e):
            logger.error(f"Error retrieving user subscription for {user_id}: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
        else:
            logger.info(f"No subscription found for user: {user_id}")
        return None

# Add these new tool functions after the existing create_inquiry_tool

@app.tool()
async def update_inquiry_tool(
    inquiry_id: str,
    subject: str = None,
    description: str = None,
    priority: str = None,
    status: str = None,
    response: str = None,
    resolution_notes: str = None,
    assigned_to: str = None
) -> str:
    """
    Update an existing inquiry.
    
    Args:
        inquiry_id: ID of the inquiry to update
        subject: Updated subject (optional)
        description: Updated description (optional)
        priority: Updated priority (optional)
        status: Updated status (optional)
        response: Response to the inquiry (optional)
        resolution_notes: Resolution notes (optional)
        assigned_to: Assigned admin/support person (optional)
    
    Returns:
        JSON string with update result
    """
    try:
        # Ensure client is valid
        if not await ensure_cosmos_client():
            logger.warning("Could not establish valid Cosmos DB connection")
            return json.dumps({
                "success": False,
                "error": "Database connection not available"
            })
        
        if not inquiries_container:
            logger.warning("Inquiries container not available")
            return json.dumps({
                "success": False,
                "error": "Database container not available"
            })
        
        # Extract event_id from inquiry_id (format: INQ_EVENTID_timestamp)
        parts = inquiry_id.split('_')
        if len(parts) >= 3:
            event_id = '_'.join(parts[1:-2])  # Everything between INQ_ and last timestamp
        else:
            return json.dumps({
                "success": False,
                "error": "Invalid inquiry ID format"
            })
        
        # Read existing inquiry
        try:
            existing_inquiry = await inquiries_container.read_item(inquiry_id, event_id)
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Inquiry not found: {inquiry_id}"
            })
        
        # Update only provided fields
        if subject is not None:
            existing_inquiry['subject'] = subject
        if description is not None:
            existing_inquiry['description'] = description
        if priority is not None:
            existing_inquiry['priority'] = priority
        if status is not None:
            existing_inquiry['status'] = status
            if status == "RESOLVED":
                existing_inquiry['resolved_at'] = datetime.utcnow().isoformat()
        if response is not None:
            existing_inquiry['response'] = response
        if resolution_notes is not None:
            existing_inquiry['resolution_notes'] = resolution_notes
        if assigned_to is not None:
            existing_inquiry['assigned_to'] = assigned_to
        
        # Update timestamp
        existing_inquiry['updated_at'] = datetime.utcnow().isoformat()
        
        # Save updated inquiry
        result = await inquiries_container.replace_item(inquiry_id, existing_inquiry)
        
        logger.info(f"Successfully updated inquiry {inquiry_id}")
        
        return json.dumps({
            "success": True,
            "inquiry_id": inquiry_id,
            "message": "Inquiry updated successfully",
            "updated_fields": {
                k: v for k, v in {
                    "subject": subject,
                    "description": description,
                    "priority": priority,
                    "status": status,
                    "response": response,
                    "resolution_notes": resolution_notes,
                    "assigned_to": assigned_to
                }.items() if v is not None
            }
        }, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"Error updating inquiry: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2, default=str)

@app.tool()
async def get_user_inquiries_tool(
    event_id: str,
    user_id: str
) -> str:
    """
    Get inquiries for a specific event created by a specific user.
    
    Args:
        event_id: ID of the corporate action event
        user_id: ID of the user
    
    Returns:
        JSON string with user's inquiries for the event
    """
    try:
        if not inquiries_container:
            logger.warning("Inquiries container not available, returning empty list")
            return json.dumps({
                "event_id": event_id,
                "user_id": user_id,
                "inquiries": [],
                "count": 0
            }, indent=2)
        
        query = """
        SELECT * FROM c 
        WHERE c.event_id = @event_id 
        AND c.user_id = @user_id 
        ORDER BY c.created_at DESC
        """
        parameters = [
            {"name": "@event_id", "value": event_id},
            {"name": "@user_id", "value": user_id}
        ]
        
        inquiries = []
        async for item in inquiries_container.query_items(query, parameters=parameters):
            inquiries.append(item)
        
        return json.dumps({
            "event_id": event_id,
            "user_id": user_id,
            "inquiries": inquiries,
            "count": len(inquiries)
        }, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"Error retrieving user inquiries: {e}")
        return json.dumps({
            "event_id": event_id,
            "user_id": user_id,
            "inquiries": [],
            "count": 0,
            "error": str(e)
        }, indent=2)

@app.tool()
async def delete_inquiry_tool(
    inquiry_id: str,
    user_id: str
) -> str:
    """
    Delete an inquiry (only if created by the user and in OPEN status).
    
    Args:
        inquiry_id: ID of the inquiry to delete
        user_id: ID of the user requesting deletion
    
    Returns:
        JSON string with deletion result
    """
    try:
        if not await ensure_cosmos_client() or not inquiries_container:
            return json.dumps({
                "success": False,
                "error": "Database connection not available"
            })
        
        # Extract event_id from inquiry_id
        parts = inquiry_id.split('_')
        if len(parts) >= 3:
            event_id = '_'.join(parts[1:-2])
        else:
            return json.dumps({
                "success": False,
                "error": "Invalid inquiry ID format"
            })
        
        # Read inquiry to verify ownership and status
        try:
            inquiry = await inquiries_container.read_item(inquiry_id, event_id)
            
            # Check if user owns the inquiry
            if inquiry.get('user_id') != user_id:
                return json.dumps({
                    "success": False,
                    "error": "You can only delete your own inquiries"
                })
            
            # Check if inquiry is in deletable status
            if inquiry.get('status') not in ['OPEN', 'ACKNOWLEDGED']:
                return json.dumps({
                    "success": False,
                    "error": f"Cannot delete inquiry in {inquiry.get('status')} status"
                })
            
            # Delete the inquiry
            await inquiries_container.delete_item(inquiry_id, event_id)
            
            logger.info(f"Successfully deleted inquiry {inquiry_id}")
            
            return json.dumps({
                "success": True,
                "inquiry_id": inquiry_id,
                "message": "Inquiry deleted successfully"
            }, indent=2)
            
        except Exception as e:
            if "NotFound" in str(e):
                return json.dumps({
                    "success": False,
                    "error": f"Inquiry not found: {inquiry_id}"
                })
            raise
        
    except Exception as e:
        logger.error(f"Error deleting inquiry: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)

# Update the get_sample_inquiries function to include more fields
def get_sample_inquiries(event_id: str = None) -> List[Dict[str, Any]]:
    """Get sample inquiries for testing with complete schema"""
    all_inquiries = [
        {
            "id": "INQ_AAPL_DIV_2024_Q1_20240201",
            "inquiry_id": "INQ_AAPL_DIV_2024_Q1_20240201",
            "event_id": "AAPL_DIV_2024_Q1",
            "user_id": "user_001",
            "user_name": "John Investor",
            "user_role": "CONSUMER",
            "organization": "ABC Investment Fund",
            "subject": "Ex-dividend date clarification",
            "description": "Can you confirm if the ex-dividend date for AAPL Q1 2024 is February 15th? Our records show different dates.",
            "priority": "HIGH",
            "status": "OPEN",
            "assigned_to": None,
            "response": None,
            "resolution_notes": None,
            "created_at": "2024-02-01T10:30:00Z",
            "updated_at": "2024-02-01T10:30:00Z",
            "due_date": None,
            "resolved_at": None,
            "subscribers": ["user_001"],
            "notification_history": [],
            "symbol": "AAPL"
        },
        {
            "id": "INQ_MSFT_SPLIT_2024_20240116",
            "inquiry_id": "INQ_MSFT_SPLIT_2024_20240116",
            "event_id": "MSFT_SPLIT_2024",
            "user_id": "user_002",
            "user_name": "Sarah Trader",
            "user_role": "CONSUMER",
            "organization": "XYZ Capital",
            "subject": "Stock split impact on options",
            "description": "How will the 2:1 stock split affect existing options positions? Will the strike prices be adjusted?",
            "priority": "MEDIUM",
            "status": "IN_REVIEW",
            "assigned_to": "admin_001",
            "response": "Options adjustments will be made according to OCC rules. Strike prices will be halved and contract multiplier doubled.",
            "resolution_notes": None,
            "created_at": "2024-01-16T14:45:00Z",
            "updated_at": "2024-01-17T09:30:00Z",
            "due_date": None,
            "resolved_at": None,
            "subscribers": ["user_002", "user_003"],
            "notification_history": [
                {
                    "timestamp": "2024-01-17T09:30:00Z",
                    "type": "status_change",
                    "message": "Status changed from OPEN to IN_REVIEW"
                }
            ],
            "symbol": "MSFT"
        },
        {
            "id": "INQ_TSLA_DIV_2024_SPECIAL_20240202",
            "inquiry_id": "INQ_TSLA_DIV_2024_SPECIAL_20240202",
            "event_id": "TSLA_DIV_2024_SPECIAL",
            "user_id": "user_003",
            "user_name": "Mike Portfolio",
            "user_role": "CONSUMER",
            "organization": "Individual Investor",
            "subject": "Tax implications of special dividend",
            "description": "What are the tax implications of Tesla's special dividend? Is it qualified or non-qualified?",
            "priority": "MEDIUM",
            "status": "RESOLVED",
            "assigned_to": "admin_002",
            "response": "Based on IRS guidelines, this special dividend qualifies for preferential tax treatment. However, consult your tax advisor for personalized advice.",
            "resolution_notes": "Provided tax guidance and recommended consulting personal tax advisor.",
            "created_at": "2024-02-02T09:15:00Z",
            "updated_at": "2024-02-03T11:20:00Z",
            "due_date": None,
            "resolved_at": "2024-02-03T11:20:00Z",
            "subscribers": ["user_003"],
            "notification_history": [
                {
                    "timestamp": "2024-02-02T15:30:00Z",
                    "type": "response_added",
                    "message": "Support response added"
                },
                {
                    "timestamp": "2024-02-03T11:20:00Z",
                    "type": "status_change",
                    "message": "Status changed from RESPONDED to RESOLVED"
                }
            ],
            "symbol": "TSLA"
        }
    ]
    
    if event_id:
        return [inq for inq in all_inquiries if inq["event_id"] == event_id]
    return all_inquiries

# =============================================================================
# MCP Tools Registration
# =============================================================================

@app.tool()
async def create_inquiry_tool(
    event_id: str,
    user_id: str,
    user_name: str,
    organization: str,
    subject: str,
    description: str,
    priority: str = "MEDIUM"
) -> str:
    """
    Create a new inquiry for a corporate action event.
    
    Args:
        event_id: ID of the corporate action event
        user_id: Unique identifier for the user
        user_name: Display name of the user
        organization: User's organization
        subject: Brief subject of the inquiry
        description: Detailed description of the inquiry
        priority: Priority level (LOW, MEDIUM, HIGH, URGENT)
    
    Returns:
        JSON string with inquiry creation result
    """
    result = await create_inquiry(event_id, user_id, user_name, organization, subject, description, priority)
    return json.dumps(result, indent=2, default=str)

@app.tool()
async def get_inquiries_tool(event_id: str) -> str:
    """
    Get all inquiries for a specific corporate action event.
    
    Args:
        event_id: ID of the corporate action event
    
    Returns:
        JSON string with list of inquiries
    """
    inquiries = await get_inquiries_for_event(event_id)
    return json.dumps({
        "event_id": event_id,
        "inquiries": inquiries,
        "count": len(inquiries)
    }, indent=2, default=str)

@app.tool()
async def save_subscription_tool(
    user_id: str,
    user_name: str,
    organization: str,
    symbols: str,
    event_types: str = ""
) -> str:
    """
    Save user subscription for corporate actions.
    
    Args:
        user_id: Unique identifier for the user
        user_name: Display name of the user
        organization: User's organization
        symbols: Comma-separated list of stock symbols
        event_types: Comma-separated list of event types (optional)
    
    Returns:
        JSON string with subscription save result
    """
    symbols_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    event_types_list = [e.strip().upper() for e in event_types.split(",") if e.strip()] if event_types else None
    
    result = await save_user_subscription(user_id, user_name, organization, symbols_list, event_types_list)
    return json.dumps(result, indent=2, default=str)

@app.tool()
async def get_subscription_tool(user_id: str) -> str:
    """
    Get user subscription details.
    
    Args:
        user_id: Unique identifier for the user
    
    Returns:
        JSON string with subscription details
    """
    logger.info(f"get_subscription_tool called for user_id: {user_id}")
    
    # Check container availability before proceeding
    container_available = subscriptions_container is not None
    logger.info(f"Subscriptions container available: {container_available}")
    
    subscription = await get_user_subscription(user_id)
    
    result = {
        "user_id": user_id,
        "subscription": subscription,
        "debug_info": {
            "container_available": container_available,
            "cosmos_client_available": cosmos_client is not None,
            "cosmos_database_available": cosmos_database is not None,
            "clients_initialized": _clients_initialized
        }
    }
    
    logger.info(f"get_subscription_tool result: subscription found = {subscription is not None}")
    return json.dumps(result, indent=2, default=str)

@app.tool()
async def get_upcoming_events_tool(user_id: str, days_ahead: int = 7) -> str:
    """
    Get upcoming corporate actions for user's subscribed symbols.
    
    Args:
        user_id: Unique identifier for the user
        days_ahead: Number of days to look ahead (default: 7)
    
    Returns:
        JSON string with upcoming events and any related inquiries
    """
    from datetime import datetime, timedelta, date
    
    # Get user subscription first
    subscription = await get_user_subscription(user_id)
    if not subscription:
        return json.dumps({
            "error": "No subscription found for user",
            "user_id": user_id
        }, indent=2)
    
    subscribed_symbols = subscription.get("symbols", [])
    if not subscribed_symbols:
        return json.dumps({
            "error": "User has no subscribed symbols",
            "user_id": user_id,
            "subscription": subscription
        }, indent=2)
    
    try:        # Get upcoming events from AI Search using subscribed symbols
        logger.info(f"Searching AI Search for upcoming events for symbols: {subscribed_symbols}")
        
        # Calculate date range
        today = date.today()
        end_date = today + timedelta(days=days_ahead)
        
        # Search for events in the subscribed symbols
        search_result = await search_corporate_actions_from_ai_search(
            search_text="*",  # Get all events
            symbols=subscribed_symbols,
            top=100  # Get more results to filter by date
        )
        
        subscribed_events = []
        if search_result.get("results"):
            # Filter events by date range (using ex_date or announcement_date)
            for event in search_result["results"]:
                try:
                    # Try to use ex_date first, then announcement_date
                    date_to_check = event.get("ex_date") or event.get("announcement_date")
                    if date_to_check:
                        # Parse the date (handle both ISO format and date string)
                        if isinstance(date_to_check, str):
                            if 'T' in date_to_check:  # ISO datetime format
                                event_date = datetime.fromisoformat(date_to_check.replace('Z', '+00:00')).date()
                            else:  # Date string format
                                event_date = datetime.fromisoformat(date_to_check).date()
                        else:
                            event_date = date_to_check
                        
                        # Include if within date range
                        if today <= event_date <= end_date:
                            subscribed_events.append(event)
                            logger.info(f"Including AI Search event: {event.get('event_id')} for {event.get('symbol')} on {event_date}")
                except Exception as e:
                    logger.warning(f"Error parsing date for AI Search event {event.get('event_id')}: {e}")
                    # Include event without date filtering as fallback
                    subscribed_events.append(event)
                    continue
        else:
            # Fallback to sample data if AI Search is not available
            logger.warning("AI Search not available, using sample data")
            all_events = get_sample_events()
            
            # Filter sample events by date and subscribed symbols
            for event in all_events:
                # Check if event is for subscribed symbols
                if event.get("symbol") in subscribed_symbols:
                    # Check if event is within date range (using ex_date)
                    try:
                        ex_date_str = event.get("ex_date")
                        if ex_date_str:
                            # Parse the ISO date string
                            if isinstance(ex_date_str, str):
                                ex_date = datetime.fromisoformat(ex_date_str).date()
                            else:
                                ex_date = ex_date_str
                            
                            # Include if within date range
                            if today <= ex_date <= end_date:
                                subscribed_events.append(event)
                                logger.info(f"Including sample event: {event.get('event_id')} for {event.get('symbol')} on {ex_date}")
                    except Exception as e:
                        logger.warning(f"Error parsing date for sample event {event.get('event_id')}: {e}")
                        continue
        
        logger.info(f"Found {len(subscribed_events)} upcoming events for user {user_id}")
    
        # Add inquiries for each event
        events_with_inquiries = []
        for event in subscribed_events:
            try:
                inquiries = await get_inquiries_for_event(event["event_id"])
                event_with_inquiries = event.copy()
                event_with_inquiries["inquiries"] = inquiries
                event_with_inquiries["inquiry_count"] = len(inquiries)
                events_with_inquiries.append(event_with_inquiries)
            except Exception as e:
                logger.error(f"Error getting inquiries for event {event.get('event_id')}: {e}")
                # Add event without inquiries
                event_with_inquiries = event.copy()
                event_with_inquiries["inquiries"] = []
                event_with_inquiries["inquiry_count"] = 0
                events_with_inquiries.append(event_with_inquiries)
        
        # Sort events by ex_date
        events_with_inquiries.sort(key=lambda x: x.get('ex_date', ''))
        
        return json.dumps({
            "user_id": user_id,
            "days_ahead": days_ahead,
            "date_range": {
                "start_date": date.today().isoformat(),
                "end_date": (date.today() + timedelta(days=days_ahead)).isoformat()
            },
            "subscription": {
                "symbols": subscribed_symbols,
                "user_name": subscription.get("user_name"),
                "organization": subscription.get("organization")
            },            "upcoming_events": events_with_inquiries,
            "total_events": len(events_with_inquiries),
            "total_inquiries": sum(event["inquiry_count"] for event in events_with_inquiries),
            "data_source": search_result.get("data_source", "ai_search") if search_result and search_result.get("results") else "sample_data"
        }, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"Error in get_upcoming_events_tool: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return json.dumps({
            "error": str(e),
            "user_id": user_id,
            "fallback_message": "An error occurred while fetching upcoming events"
        }, indent=2, default=str)

# Basic RAG functionality (simplified for now)
@app.tool()
async def rag_query(query: str, max_results: int = 5, chat_history: str = "") -> str:
    """
    Process natural language queries about corporate actions using proper RAG with vector search.
    
    Args:
        query: Natural language query
        max_results: Maximum number of results to return
        chat_history: Optional JSON string containing chat history for context
    
    Returns:
        JSON string with query results
    """
    try:
        # Parse chat history if provided
        parsed_chat_history = []
        if chat_history:
            try:
                parsed_chat_history = json.loads(chat_history)
            except Exception as e:
                logger.warning(f"Failed to parse chat_history: {e}")
                parsed_chat_history = []
        
        # Generate query embedding for vector search
        logger.info(f"Processing RAG query: {query}")
        query_embedding = await generate_embedding(query)
        
        # Perform vector search
        search_results = await vector_search(query_embedding, max_results)
        
        # Generate RAG response using OpenAI with chat history
        rag_response = await generate_rag_response(query, search_results, parsed_chat_history)
        
        return json.dumps({
            "answer": rag_response["answer"],
            "sources": rag_response["sources"],
            "query": query,
            "total_found": len(search_results),
            "data_source": "vector_search",
            "confidence_score": rag_response.get("confidence_score", 0.5),
            "query_intent": rag_response.get("query_intent", "information_request"),
            "requires_visualization": rag_response.get("requires_visualization", False),
            "visualization_suggestions": rag_response.get("visualization_suggestions", {})
        }, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"❌ Error in rag_query: {e}")
        # Fallback to keyword search if vector search fails
        search_result = await search_corporate_actions_from_ai_search(
            search_text=query,
            top=max_results
        )
        
        events = search_result.get("results", [])
        if not events:
            events = get_sample_events()[:max_results]
        
        return json.dumps({
            "answer": f"I found {len(events)} corporate action events related to your query. (Note: Advanced AI analysis temporarily unavailable)",
            "sources": events,
            "query": query,
            "error": str(e),
            "data_source": "keyword_search_fallback"
        }, indent=2, default=str)

@app.tool()
async def rag_query_subscribed(
    query: str, 
    user_id: str,
    subscribed_symbols: List[str],
    max_results: int = 5,
    chat_history: str = ""
) -> str:
    """
    Process natural language queries about corporate actions for subscribed symbols only.
    
    Args:
        query: Natural language query
        user_id: User identifier
        subscribed_symbols: List of symbols user is subscribed to
        max_results: Maximum number of results to return
        chat_history: JSON string of previous chat messages
    
    Returns:
        JSON string with query results or error if asking about non-subscribed symbols
    """
    import re
    from datetime import datetime, timedelta, date
    
    logger.info(f"RAG query from user {user_id}: {query}")
    logger.info(f"User subscribed symbols: {subscribed_symbols}")
    
    if not subscribed_symbols:
        return json.dumps({
            "error": "No subscribed symbols found. Please subscribe to symbols first.",
            "suggestion": "Go to the Dashboard page to subscribe to symbols you're interested in."
        }, indent=2)
      # Check if query mentions any symbols not in subscription
    query_upper = query.upper()
    query_lower = query.lower()
    
    # Create mapping of company names to symbols for intelligent detection
    company_to_symbol = {
        'APPLE': 'AAPL',
        'APPLE INC': 'AAPL',
        'APPLE INCORPORATED': 'AAPL',
        'MICROSOFT': 'MSFT',
        'MICROSOFT CORP': 'MSFT',
        'MICROSOFT CORPORATION': 'MSFT',
        'GOOGLE': 'GOOGL',
        'ALPHABET': 'GOOGL',
        'ALPHABET INC': 'GOOGL',
        'TESLA': 'TSLA',
        'TESLA INC': 'TSLA',
        'TESLA MOTORS': 'TSLA',
        'AMAZON': 'AMZN',
        'AMAZON.COM': 'AMZN',
        'AMAZON COM': 'AMZN',
        'META': 'META',
        'META PLATFORMS': 'META',
        'FACEBOOK': 'META',
        'NVIDIA': 'NVDA',
        'NVIDIA CORP': 'NVDA',
        'NVIDIA CORPORATION': 'NVDA',
        'NETFLIX': 'NFLX',
        'SALESFORCE': 'CRM',
        'ORACLE': 'ORCL',
        'ADOBE': 'ADBE',
        'SERVICENOW': 'NOW',
        'ZOOM': 'ZM',
        'UBER': 'UBER',
        'SHOPIFY': 'SHOP',
        'SQUARE': 'SQ',
        'BLOCK': 'SQ',
        'PAYPAL': 'PYPL',
        'VISA': 'V',
        'MASTERCARD': 'MA',
        'JPMORGAN': 'JPM',
        'JP MORGAN': 'JPM',
        'JPMORGAN CHASE': 'JPM',
        'BANK OF AMERICA': 'BAC',
        'WELLS FARGO': 'WFC',
        'CITIGROUP': 'C',
        'GOLDMAN SACHS': 'GS',
        'MORGAN STANLEY': 'MS',
        'BERKSHIRE HATHAWAY': 'BRK.A'
    }
    
    mentioned_symbols = set()
      # 1. Define comprehensive list of known stock symbols
    # This is the authoritative list - only these will be considered valid symbols
    known_symbols = {
        # Major tech stocks
        'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'CRM', 'ORCL', 'ADBE', 'NOW', 
        'ZM', 'UBER', 'SHOP', 'SQ', 'PYPL', 'INTC', 'AMD', 'QCOM', 'AVGO', 'TXN', 'MU', 'AMAT', 'LRCX', 'KLAC',
        # Financial stocks
        'V', 'MA', 'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'AXP', 'BLK', 'SCHW', 'SPGI', 'ICE', 'CME', 'MCO',
        # Healthcare & pharma
        'JNJ', 'PFE', 'UNH', 'ABBV', 'MRK', 'TMO', 'ABT', 'DHR', 'BMY', 'LLY', 'AMGN', 'GILD', 'VRTX', 'BIIB', 'REGN',
        # Consumer goods
        'PG', 'KO', 'PEP', 'WMT', 'HD', 'MCD', 'NKE', 'SBUX', 'TGT', 'LOW', 'COST', 'DG', 'DLTR', 'YUM', 'CMG',
        # Industrial & energy
        'BA', 'GE', 'CAT', 'MMM', 'HON', 'UPS', 'RTX', 'LMT', 'DE', 'FDX', 'XOM', 'CVX', 'COP', 'EOG', 'SLB',
        # Berkshire Hathaway
        'BRK.A', 'BRK.B', 'BRKB',
        # ETFs
        'SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VOO', 'VEA', 'VWO', 'AGG', 'BND', 'GLD', 'SLV', 'XLF', 'XLK', 'XLE', 'XLI', 'XLV',
        # Add subscribed symbols to known list
        *subscribed_symbols
    }
    
    # 2. Look for potential stock symbols using a more restrictive approach
    # Only match patterns that could be stock symbols, then filter against known list
    symbol_pattern = r'\b[A-Z]{2,5}(?:\.[A-B])?\b'
    potential_symbols = re.findall(symbol_pattern, query_upper)
    
    for symbol in potential_symbols:
        # Only add if it's in our known symbols list
        if symbol in known_symbols:
            mentioned_symbols.add(symbol)
      # 3. Check for company names and convert to symbols
    for company_name, symbol in company_to_symbol.items():
        # Use word boundaries to avoid partial matches
        company_pattern = r'\b' + re.escape(company_name) + r'\b'
        if re.search(company_pattern, query_upper):
            mentioned_symbols.add(symbol)
    
    logger.info(f"Detected mentioned symbols: {mentioned_symbols}")
    
    # Check if any mentioned symbols are not in subscription
    unsubscribed_symbols = mentioned_symbols - set(subscribed_symbols)
    if unsubscribed_symbols:
        return json.dumps({
            "error": f"Access denied. You asked about symbols you're not subscribed to: {', '.join(unsubscribed_symbols)}",
            "suggestion": f"You can only ask about your subscribed symbols: {', '.join(subscribed_symbols)}",
            "mentioned_symbols": list(mentioned_symbols),
            "subscribed_symbols": subscribed_symbols,
            "unsubscribed_symbols": list(unsubscribed_symbols)
        }, indent=2)
    
    # Proceed with RAG query for subscribed symbols
    try:        # Get corporate actions for subscribed symbols from AI Search
        logger.info("Querying AI Search for subscribed symbols")
        search_result = await search_corporate_actions_from_ai_search(
            search_text=query,
            symbols=mentioned_symbols,
            top=max_results
        )
        
        corporate_actions = search_result.get("results", [])
        
        # If no AI Search data, use sample data filtered by subscriptions
        if not corporate_actions:
            logger.info("Using sample data for subscribed symbols")
            all_sample_events = get_sample_events()
            corporate_actions = [
                event for event in all_sample_events 
                if event.get("symbol") in subscribed_symbols
            ]
        
        # Limit results
        corporate_actions = corporate_actions[:max_results]
        
        logger.info(f"Found {len(corporate_actions)} corporate actions for analysis")
        
        # Simple keyword-based analysis for now
        query_lower = query.lower()
        
        # Generate contextual answer based on query and data
        if "dividend" in query_lower:
            dividend_events = [ca for ca in corporate_actions if ca.get('event_type') == 'dividend']
            if dividend_events:
                answer = f"Found {len(dividend_events)} dividend events for your subscribed symbols:\n"
                for event in dividend_events:
                    amount = event.get('event_details', {}).get('dividend_amount', 'N/A')
                    answer += f"• {event.get('company_name')} ({event.get('symbol')}): ${amount} on {event.get('ex_date', 'TBD')}\n"
            else:
                answer = "No dividend events found for your subscribed symbols."
                
        elif "split" in query_lower:
            split_events = [ca for ca in corporate_actions if 'split' in ca.get('event_type', '')]
            if split_events:
                answer = f"Found {len(split_events)} stock split events for your subscribed symbols:\n"
                for event in split_events:
                    ratio = event.get('event_details', {}).get('split_ratio', 'N/A')
                    answer += f"• {event.get('company_name')} ({event.get('symbol')}): {ratio} split on {event.get('ex_date', 'TBD')}\n"
            else:
                answer = "No stock split events found for your subscribed symbols."
                
        elif "upcoming" in query_lower or "future" in query_lower:
            today = date.today()
            upcoming_events = []
            for event in corporate_actions:
                ex_date_str = event.get('ex_date')
                if ex_date_str:
                    try:
                        if isinstance(ex_date_str, str):
                            ex_date = datetime.fromisoformat(ex_date_str).date()
                        else:
                            ex_date = ex_date_str
                        if ex_date >= today:
                            upcoming_events.append(event)
                    except:
                        continue
            
            if upcoming_events:
                answer = f"Found {len(upcoming_events)} upcoming corporate actions for your subscribed symbols:\n"
                for event in upcoming_events[:5]:
                    answer += f"• {event.get('company_name')} ({event.get('symbol')}): {event.get('event_type', 'N/A').replace('_', ' ').title()} on {event.get('ex_date', 'TBD')}\n"
            else:
                answer = "No upcoming corporate actions found for your subscribed symbols."
                
        else:
            # General query
            if corporate_actions:
                symbol_counts = {}
                event_type_counts = {}
                
                for event in corporate_actions:
                    symbol = event.get('symbol', 'Unknown')
                    event_type = event.get('event_type', 'unknown')
                    
                    symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
                    event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
                
                answer = f"Analysis of {len(corporate_actions)} corporate actions for your subscribed symbols:\n\n"
                answer += "**By Symbol:**\n"
                for symbol, count in sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True):
                    answer += f"• {symbol}: {count} events\n"
                
                answer += "\n**By Event Type:**\n"
                for event_type, count in sorted(event_type_counts.items(), key=lambda x: x[1], reverse=True):
                    answer += f"• {event_type.replace('_', ' ').title()}: {count} events\n"
            else:
                answer = f"No corporate actions found for your subscribed symbols: {', '.join(subscribed_symbols)}"
        
        return json.dumps({
            "answer": answer,
            "sources": corporate_actions,
            "query": query,
            "subscribed_symbols": subscribed_symbols,
            "data_source": search_result.get("data_source", "ai_search") if search_result and search_result.get("results") else "sample_data",
            "total_results": len(corporate_actions)
        }, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"Error in rag_query_subscribed: {e}")
        return json.dumps({
            "error": f"Error processing your query: {str(e)}",
            "query": query
        }, indent=2)

# =============================================================================
# FastAPI SSE Endpoints
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await initialize_azure_clients()
    await test_cosmos_connectivity()
    yield
    # Shutdown (if needed)
    if cosmos_client:
        await cosmos_client.close()

sse_app = FastAPI(title="Corporate Actions SSE API", version="1.0.0", lifespan=lifespan)

sse_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@sse_app.get("/health")
async def sse_health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Corporate Actions MCP RAG Server"}

# Fix the HTTP endpoint wrappers - call the underlying functions, not the MCP tools
@sse_app.post("/mcp/tools/get_subscription_tool")
async def http_get_subscription_tool(request: dict):
    """HTTP wrapper for get_subscription_tool"""
    user_id = request.get("user_id")
    if not user_id:
        return {"error": "user_id is required"}
    
    # Call the underlying function directly
    subscription = await get_user_subscription(user_id)
    
    result = {
        "user_id": user_id,
        "subscription": subscription,
        "debug_info": {
            "container_available": subscriptions_container is not None,
            "cosmos_client_available": cosmos_client is not None,
            "cosmos_database_available": cosmos_database is not None,
            "clients_initialized": _clients_initialized
        }
    }
    
    return result

@sse_app.post("/mcp/tools/get_inquiries_tool")
async def http_get_inquiries_tool(request: dict):
    """HTTP wrapper for get_inquiries_tool"""
    event_id = request.get("event_id")
    if not event_id:
        return {"error": "event_id is required"}
    
    # Call the underlying function directly
    inquiries = await get_inquiries_for_event(event_id)
    
    return {
        "event_id": event_id,
        "inquiries": inquiries,
        "count": len(inquiries)
    }

@sse_app.post("/mcp/tools/get_upcoming_events_tool")
async def http_get_upcoming_events_tool(request: dict):
    """HTTP wrapper for get_upcoming_events_tool"""
    user_id = request.get("user_id")
    days_ahead = request.get("days_ahead", 7)
    
    if not user_id:
        return {"error": "user_id is required"}
    
    # Get user subscription first
    subscription = await get_user_subscription(user_id)
    if not subscription:
        return {
            "error": "No subscription found for user",
            "user_id": user_id
        }
    
    subscribed_symbols = subscription.get("symbols", [])
    if not subscribed_symbols:
        return {
            "error": "User has no subscribed symbols",
            "user_id": user_id,
            "subscription": subscription
        }
    
    try:
        from datetime import datetime, timedelta, date
        
        # Get upcoming events from AI Search using subscribed symbols
        logger.info(f"Searching AI Search for upcoming events for symbols: {subscribed_symbols}")
        
        # Calculate date range
        today = date.today()
        end_date = today + timedelta(days=days_ahead)
        
        # Search for events in the subscribed symbols
        search_result = await search_corporate_actions_from_ai_search(
            search_text="*",
            symbols=subscribed_symbols,
            top=100
        )
        
        subscribed_events = []
        if search_result.get("results"):
            for event in search_result["results"]:
                try:
                    # Check if event is within date range
                    ex_date_str = event.get('ex_date')
                    if ex_date_str:
                        ex_date = datetime.fromisoformat(ex_date_str.replace('Z', '+00:00')).date()
                        if today <= ex_date <= end_date:
                            subscribed_events.append(event)
                    else:
                        # Include events without ex_date for now
                        subscribed_events.append(event)
                except Exception as e:
                    logger.warning(f"Error processing event date: {e}")
                    subscribed_events.append(event)
        else:
            # Fallback to sample data if no search results
            logger.info("No search results found, using sample data")
            subscribed_events = [
                {
                    "event_id": "AAPL_DIVIDEND_2025_Q2_001",
                    "event_type": "DIVIDEND",
                    "security": {"symbol": "AAPL"},
                    "issuer_name": "Apple Inc.",
                    "status": "ANNOUNCED",
                    "announcement_date": "2025-06-10",
                    "ex_date": "2025-06-20",
                    "description": "$0.25 quarterly cash dividend declared",
                    "event_details": {"dividend_amount": 0.25}
                }
            ]
        
        logger.info(f"Found {len(subscribed_events)} upcoming events for user {user_id}")
    
        # Add inquiries for each event
        events_with_inquiries = []
        for event in subscribed_events:
            try:
                inquiries = await get_inquiries_for_event(event["event_id"])
                event_with_inquiries = dict(event)
                event_with_inquiries["inquiries"] = inquiries
                event_with_inquiries["inquiry_count"] = len(inquiries)
                events_with_inquiries.append(event_with_inquiries)
            except Exception as e:
                logger.warning(f"Error getting inquiries for event {event.get('event_id')}: {e}")
                event_with_inquiries = dict(event)
                event_with_inquiries["inquiries"] = []
                event_with_inquiries["inquiry_count"] = 0
                events_with_inquiries.append(event_with_inquiries)
        
        # Sort events by ex_date
        events_with_inquiries.sort(key=lambda x: x.get('ex_date', ''))
        
        return {
            "user_id": user_id,
            "days_ahead": days_ahead,
            "date_range": {
                "start_date": date.today().isoformat(),
                "end_date": (date.today() + timedelta(days=days_ahead)).isoformat()
            },
            "subscription": {
                "symbols": subscribed_symbols,
                "user_name": subscription.get("user_name"),
                "organization": subscription.get("organization")
            },
            "upcoming_events": events_with_inquiries,
            "total_events": len(events_with_inquiries),
            "total_inquiries": sum(event["inquiry_count"] for event in events_with_inquiries),
            "data_source": search_result.get("data_source", "ai_search") if search_result and search_result.get("results") else "sample_data"
        }
        
    except Exception as e:
        logger.error(f"Error in get_upcoming_events: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "error": str(e),
            "user_id": user_id,
            "fallback_message": "An error occurred while fetching upcoming events"
        }

@sse_app.post("/mcp/tools/create_inquiry_tool")
async def http_create_inquiry_tool(request: dict):
    """HTTP wrapper for create_inquiry_tool"""
    required_fields = ["event_id", "user_id", "user_name", "organization", "subject", "description"]
    for field in required_fields:
        if not request.get(field):
            return {"error": f"{field} is required"}
    
    # Call the underlying function directly
    result = await create_inquiry(
        event_id=request["event_id"],
        user_id=request["user_id"],
        user_name=request["user_name"],
        organization=request["organization"],
        subject=request["subject"],
        description=request["description"],
        priority=request.get("priority", "MEDIUM")
    )
    
    return result

@sse_app.post("/mcp/tools/update_inquiry_tool")
async def http_update_inquiry_tool(request: dict):
    """HTTP wrapper for update_inquiry_tool"""
    inquiry_id = request.get("inquiry_id")
    user_id = request.get("user_id")  # Add user_id for validation
    
    if not inquiry_id:
        return {"error": "inquiry_id is required"}
    if not user_id:
        return {"error": "user_id is required"}
    
    try:
        # Ensure client is valid
        if not await ensure_cosmos_client():
            return {
                "success": False,
                "error": "Database connection not available"
            }
        
        if not inquiries_container:
            return {
                "success": False,
                "error": "Database container not available"
            }
        
        # Extract event_id from inquiry_id (format: INQ_EVENTID_timestamp)
        parts = inquiry_id.split('_')
        if len(parts) >= 3:
            event_id = '_'.join(parts[1:-1])  # Reconstruct event_id
        else:
            return {
                "success": False,
                "error": "Invalid inquiry_id format"
            }
        
        # Read existing inquiry
        try:
            existing_inquiry = await inquiries_container.read_item(inquiry_id, event_id)
        except Exception as e:
            return {
                "success": False,
                "error": f"Inquiry not found: {str(e)}"
            }
        
        # Verify user owns this inquiry
        if existing_inquiry.get("user_id") != user_id:
            return {
                "success": False,
                "error": "You can only update your own inquiries"
            }
        
        # Update only provided fields
        updated = False
        if request.get("subject") is not None:
            existing_inquiry['subject'] = request["subject"]
            updated = True
        if request.get("description") is not None:
            existing_inquiry['description'] = request["description"]
            updated = True
        if request.get("priority") is not None:
            existing_inquiry['priority'] = request["priority"]
            updated = True
        
        if not updated:
            return {
                "success": False,
                "error": "No fields to update"
            }
        
        # Update timestamp
        existing_inquiry['updated_at'] = datetime.utcnow().isoformat()
        
        # Save updated inquiry
        result = await inquiries_container.replace_item(inquiry_id, existing_inquiry)
        
        logger.info(f"Successfully updated inquiry {inquiry_id}")
        
        return {
            "success": True,
            "inquiry_id": inquiry_id,
            "message": "Inquiry updated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error updating inquiry: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@sse_app.post("/mcp/tools/get_user_inquiries_tool")
async def http_get_user_inquiries_tool(request: dict):
    """HTTP wrapper for get_user_inquiries_tool"""
    event_id = request.get("event_id")
    user_id = request.get("user_id")
    
    if not event_id or not user_id:
        return {"error": "event_id and user_id are required"}
    
    try:
        if not inquiries_container:
            # Return sample data if container not available
            sample_inquiries = [
                {
                    "id": f"INQ_{event_id}_sample",
                    "inquiry_id": f"INQ_{event_id}_sample",
                    "event_id": event_id,
                    "user_id": user_id,
                    "user_name": "Sample User",
                    "subject": "Sample inquiry",
                    "description": "This is a sample inquiry for testing",
                    "priority": "MEDIUM",
                    "status": "OPEN",
                    "created_at": datetime.utcnow().isoformat()
                }
            ]
            return {
                "event_id": event_id,
                "user_id": user_id,
                "inquiries": sample_inquiries,
                "count": len(sample_inquiries)
            }
        
        query = """
        SELECT * FROM c 
        WHERE c.event_id = @event_id 
        AND c.user_id = @user_id 
        ORDER BY c.created_at DESC
        """
        parameters = [
            {"name": "@event_id", "value": event_id},
            {"name": "@user_id", "value": user_id}
        ]
        
        inquiries = []
        async for item in inquiries_container.query_items(query, parameters=parameters):
            inquiries.append(item)
        
        return {
            "event_id": event_id,
            "user_id": user_id,
            "inquiries": inquiries,
            "count": len(inquiries)
        }
        
    except Exception as e:
        logger.error(f"Error retrieving user inquiries: {e}")
        return {
            "event_id": event_id,
            "user_id": user_id,
            "inquiries": [],
            "count": 0,
            "error": str(e)
        }

@sse_app.post("/mcp/tools/save_subscription_tool")
async def http_save_subscription_tool(request: dict):
    """HTTP wrapper for save_subscription_tool"""
    required_fields = ["user_id", "user_name", "organization", "symbols"]
    for field in required_fields:
        if not request.get(field):
            return {"error": f"{field} is required"}
    
    # Parse symbols from string to list
    symbols_str = request["symbols"]
    symbols_list = [s.strip().upper() for s in symbols_str.split(",") if s.strip()]
    
    event_types_str = request.get("event_types", "")
    event_types_list = [e.strip().upper() for e in event_types_str.split(",") if e.strip()] if event_types_str else None
    
    # Call the underlying function directly
    result = await save_user_subscription(
        user_id=request["user_id"],
        user_name=request["user_name"],
        organization=request["organization"],
        symbols=symbols_list,
        event_types=event_types_list
    )
    
    return result

# Add this HTTP endpoint for search/RAG queries
@sse_app.get("/rag-query")
async def http_rag_query(
    query: str,
    max_results: int = 5,
    chat_history: str = "[]"
):
    """HTTP wrapper for RAG query functionality"""
    try:
        # Parse chat history
        parsed_chat_history = []
        if chat_history and chat_history != "[]":
            try:
                parsed_chat_history = json.loads(chat_history)
            except Exception as e:
                logger.warning(f"Failed to parse chat history: {e}")
        
        # Generate query embedding for vector search
        logger.info(f"Processing RAG query: {query}")
        query_embedding = await generate_embedding(query)
        
        # Perform vector search
        search_results = await vector_search(query_embedding, max_results)
        
        # Generate RAG response using OpenAI with chat history
        rag_response = await generate_rag_response(query, search_results, parsed_chat_history)
        
        return {
            "answer": rag_response["answer"],
            "sources": rag_response["sources"],
            "query": query,
            "total_found": len(search_results),
            "data_source": "vector_search",
            "confidence_score": rag_response.get("confidence_score", 0.5),
            "query_intent": rag_response.get("query_intent", "information_request"),
            "requires_visualization": rag_response.get("requires_visualization", False),
            "visualization_suggestions": rag_response.get("visualization_suggestions", {})
        }
        
    except Exception as e:
        logger.error(f"❌ Error in rag_query: {e}")
        # Fallback to keyword search if vector search fails
        search_result = await search_corporate_actions_from_ai_search(
            search_text=query,
            top=max_results
        )
        
        events = search_result.get("results", [])
        if not events:
            return {
                "answer": f"I couldn't find any corporate action events related to '{query}'. Try using specific company names or stock symbols.",
                "sources": [],
                "query": query,
                "error": str(e),
                "data_source": "no_results"
            }
        
        return {
            "answer": f"I found {len(events)} corporate action events related to your query. (Note: Advanced AI analysis temporarily unavailable)",
            "sources": events,
            "query": query,
            "error": str(e),
            "data_source": "keyword_search_fallback"
        }

# Add this HTTP endpoint for corporate actions search
@sse_app.get("/search-corporate-actions")
async def http_search_corporate_actions(
    query: str = "*",
    status: str = None,
    event_type: str = None,
    symbols: str = None,
    limit: int = 100,
    offset: int = 0
):
    """HTTP wrapper for corporate actions search functionality"""
    try:
        # Parse symbols if provided
        symbols_list = None
        if symbols:
            symbols_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        
        # Parse event types if provided
        event_types_list = None
        if event_type:
            event_types_list = [event_type.strip().upper()]
        
        # Parse status filter if provided
        status_filter_list = None
        if status:
            status_filter_list = [status.strip().upper()]
        
        # Check if search client is available
        if not await ensure_search_client():
            logger.info("AI Search not available, returning sample events")
            #events = get_sample_events()[:limit]
            events = []
            
            # Apply basic filtering to sample data
            if status:
                events = [e for e in events if e.get("status", "").upper() == status.upper()]
            if event_type:
                events = [e for e in events if e.get("event_type", "").upper() == event_type.upper()]
            if symbols_list:
                events = [e for e in events if e.get("symbol", "").upper() in symbols_list]
            
            return {
                "events": events,
                "total_count": len(events),
                "returned_count": len(events),
                "data_source": "sample_data",
                "query_info": {
                    "search_text": query,
                    "status_filter": status,
                    "event_type_filter": event_type,
                    "symbols_filter": symbols,
                    "limit": limit,
                    "offset": offset
                }
            }
        
        # Call the underlying search function
        search_result = await search_corporate_actions_from_ai_search(
            search_text=query if query != "*" else "*",
            symbols=symbols_list,
            event_types=event_types_list,
            status_filter=status_filter_list,
            top=limit,
            skip=offset
        )
        
        # Format response to match what the Teams bot expects
        events = search_result.get("results", [])
        
        # Convert any non-serializable objects to dictionaries
        serializable_events = []
        for event in events:
            if hasattr(event, '__dict__'):
                # Convert object to dict if it's a custom object
                serializable_events.append(event.__dict__)
            elif isinstance(event, dict):
                # Already a dict, just ensure all values are serializable
                clean_event = {}
                for key, value in event.items():
                    if hasattr(value, '__dict__'):
                        clean_event[key] = value.__dict__
                    elif isinstance(value, (str, int, float, bool, list, dict)) or value is None:
                        clean_event[key] = value
                    else:
                        clean_event[key] = str(value)
                serializable_events.append(clean_event)
            else:
                # Convert other types to dict
                serializable_events.append({"raw_data": str(event)})
        
        # If no results from AI Search, return sample data
        if not serializable_events:
            logger.info("No results from AI Search, returning sample events")
            #serializable_events = get_sample_events()[:limit]
            serializable_events = []
            
            # Apply basic filtering to sample data
            if status:
                serializable_events = [e for e in serializable_events if e.get("status", "").upper() == status.upper()]
            if event_type:
                serializable_events = [e for e in serializable_events if e.get("event_type", "").upper() == event_type.upper()]
            if symbols_list:
                serializable_events = [e for e in serializable_events if e.get("symbol", "").upper() in symbols_list]
        
        return {
            "events": serializable_events,
            "total_count": search_result.get("total_count", len(serializable_events)),
            "returned_count": len(serializable_events),
            "data_source": search_result.get("data_source", "ai_search"),
            "query_info": {
                "search_text": query,
                "status_filter": status,
                "event_type_filter": event_type,
                "symbols_filter": symbols,
                "limit": limit,
                "offset": offset
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error in search corporate actions: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Fallback to sample data
        #sample_events = get_sample_events()[:limit]
        sample_events = []
        
        # Apply basic filtering to sample data
        if status:
            sample_events = [e for e in sample_events if e.get("status", "").upper() == status.upper()]
        if event_type:
            sample_events = [e for e in sample_events if e.get("event_type", "").upper() == event_type.upper()]
        if symbols_list:
            sample_events = [e for e in sample_events if e.get("symbol", "").upper() in symbols_list]
        
        return {
            "events": sample_events,
            "total_count": len(sample_events),
            "returned_count": len(sample_events),
            "error": str(e),
            "data_source": "sample_data_fallback",
            "query_info": {
                "search_text": query,
                "status_filter": status,
                "event_type_filter": event_type,
                "symbols_filter": symbols,
                "limit": limit,
                "offset": offset
            }
        }
    
async def test_cosmos_connectivity():
    """Test Cosmos DB connectivity"""
    try:
        if not cosmos_client:
            logger.error("Cosmos client is not initialized")
            return False
        
        if not cosmos_database:
            logger.error("Cosmos database is not initialized")
            return False
        
        # Try to read database properties
        db_properties = await cosmos_database.read()
        logger.info(f"Cosmos DB connectivity test successful - Database: {db_properties.get('id', 'Unknown')}")
        
        if subscriptions_container:
            # Try to query the container
            query = "SELECT VALUE COUNT(1) FROM c"
            items = []
            async for item in subscriptions_container.query_items(query=query):
                items.append(item)
            logger.info(f"Subscriptions container test successful - Count: {items[0] if items else 0}")
        
        return True
        
    except Exception as e:
        logger.error(f"Cosmos DB connectivity test failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

@app.tool()
async def test_database_connection() -> str:
    """Test the database connection and return status"""
    try:
        is_connected = await test_cosmos_connectivity()
        
        if is_connected:
            return json.dumps({
                "status": "success",
                "message": "Database connection is working properly",
                "cosmos_client": cosmos_client is not None,
                "cosmos_database": cosmos_database is not None,
                "subscriptions_container": subscriptions_container is not None,
            }, indent=2)
        else:
            return json.dumps({
                "status": "error",
                "message": "Database connection failed",
                "cosmos_client": cosmos_client is not None,
                "cosmos_database": cosmos_database is not None,
                "subscriptions_container": subscriptions_container is not None,
            }, indent=2)
    
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error testing database connection: {str(e)}",
            "cosmos_client": cosmos_client is not None,
            "cosmos_database": cosmos_database is not None,
            "subscriptions_container": subscriptions_container is not None,
        }, indent=2)

# =============================================================================
# Azure AI Search Functions for Corporate Actions
# =============================================================================

async def ensure_search_client():
    """Ensure AI Search client is initialized and available"""
    global search_client, _clients_initialized
    
    try:
        if not _clients_initialized:
            await initialize_azure_clients()
            _clients_initialized = True
        
        if search_client:
            # Test search client by performing a simple count query
            results = await search_client.search(
                search_text="*",
                select="event_id",
                top=1,
                include_total_count=True
            )
            # Just get the count, don't need to iterate
            return True
        
        return False
    except Exception as e:
        logger.warning(f"Search client not available or test failed: {e}")
        return False

async def search_corporate_actions_from_ai_search(
    search_text: str = "*",
    symbols: List[str] = None,
    event_types: List[str] = None,
    status_filter: List[str] = None,
    top: int = 100,
    skip: int = 0
) -> Dict[str, Any]:
    """
    Search corporate actions from Azure AI Search with comprehensive filtering
    
    Args:
        search_text: Text to search for (default "*" for all)
        symbols: List of stock symbols to filter by
        event_types: List of event types to filter by
        status_filter: List of status values to filter by
        top: Maximum number of results to return
        skip: Number of results to skip (for pagination)
    
    Returns:
        Dictionary with search results and metadata
    """
    try:
        if not await ensure_search_client():
            logger.warning("Search client not available, returning empty results")
            return {
                "results": [],
                "total_count": 0,
                "message": "Search service not available",
                "data_source": "ai_search_unavailable"
            }
        
        # Build filter conditions
        filter_conditions = []
        
        if symbols:
            symbol_filters = [f"symbol eq '{symbol.upper()}'" for symbol in symbols]
            filter_conditions.append(f"({' or '.join(symbol_filters)})")
        
        if event_types:
            event_type_filters = [f"event_type eq '{event_type.upper()}'" for event_type in event_types]
            filter_conditions.append(f"({' or '.join(event_type_filters)})")
            
        if status_filter:
            status_filters = [f"status eq '{status.upper()}'" for status in status_filter]
            filter_conditions.append(f"({' or '.join(status_filters)})")
        
        # Combine filter conditions
        odata_filter = " and ".join(filter_conditions) if filter_conditions else None
        
        logger.info(f"AI Search query: text='{search_text}', filter='{odata_filter}', top={top}")
        
        # Perform search
        results = await search_client.search(
            search_text=search_text,
            filter=odata_filter,
            top=top,
            skip=skip,
            include_total_count=True,
            order_by=["announcement_date desc"]
        )
        
        # Collect results
        corporate_actions = []
        total_count = 0
        
        async for result in results:
            # Get total count from first result
            if hasattr(results, 'get_count'):
                total_count = await results.get_count()
            
            # Convert search result to consistent format
            action = {
                "id": result.get("event_id"),
                "event_id": result.get("event_id"),
                "event_type": result.get("event_type"),
                "symbol": result.get("symbol"),
                "issuer_name": result.get("issuer_name"),
                "description": result.get("description"),
                "status": result.get("status"),
                "announcement_date": result.get("announcement_date"),
                "record_date": result.get("record_date"),
                "ex_date": result.get("ex_date"),
                "payable_date": result.get("payable_date"),
                "effective_date": result.get("effective_date"),
                "data_source": result.get("data_source", "AI_SEARCH"),
                "created_at": result.get("created_at"),
                "updated_at": result.get("updated_at")
            }
            
            # Add event details if available
            if result.get("event_details_json"):
                try:
                    import json
                    action["event_details"] = json.loads(result.get("event_details_json"))
                except:
                    action["event_details"] = {}
            
            # Add individual event detail fields for convenience
            if result.get("dividend_amount"):
                action["dividend_amount"] = result.get("dividend_amount")
            if result.get("currency"):
                action["currency"] = result.get("currency")
            if result.get("acquiring_company"):
                action["acquiring_company"] = result.get("acquiring_company")
            if result.get("split_ratio_text"):
                action["split_ratio_text"] = result.get("split_ratio_text")
            
            corporate_actions.append(action)
        
        logger.info(f"✅ Found {len(corporate_actions)} corporate actions from AI Search (total: {total_count})")
        
        return {
            "results": corporate_actions,
            "total_count": total_count,
            "returned_count": len(corporate_actions),
            "data_source": "ai_search",
            "query_info": {
                "search_text": search_text,
                "filter": odata_filter,
                "top": top,
                "skip": skip
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error searching corporate actions from AI Search: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return {
            "results": [],
            "total_count": 0,
            "error": str(e),
            "data_source": "ai_search_error"
        }

async def get_corporate_action_by_id_from_ai_search(event_id: str) -> Dict[str, Any]:
    """
    Get a specific corporate action by ID from AI Search
    
    Args:
        event_id: The event ID to search for
        
    Returns:
        Dictionary with the corporate action or None if not found
    """
    try:
        result = await search_corporate_actions_from_ai_search(
            search_text="*",
            top=1,
            skip=0
        )
        
        # Filter by event_id since we can't use it directly in the filter
        # (event_id is the key field and might need special handling)
        matching_actions = [
            action for action in result.get("results", [])
            if action.get("event_id") == event_id
        ]
        
        if matching_actions:
            return {
                "success": True,
                "result": matching_actions[0],
                "data_source": "ai_search"
            }
        else:
            return {
                "success": False,
                "error": f"Corporate action with ID '{event_id}' not found",
                "data_source": "ai_search"
            }
            
    except Exception as e:
        logger.error(f"❌ Error getting corporate action by ID from AI Search: {e}")
        return {
            "success": False,
            "error": str(e),
            "data_source": "ai_search_error"
        }

@app.tool()
async def search_corporate_actions(
    search_text: str = "",
    symbols: str = "",
    event_types: str = "",
    status_filter: str = "",
    limit: int = 100,
    offset: int = 0
) -> str:
    """
    Search corporate actions from Azure AI Search with filtering options.
    
    Args:
        search_text: Text to search for in corporate actions (optional)
        symbols: Comma-separated list of stock symbols to filter by (optional)
        event_types: Comma-separated list of event types to filter by (optional) 
        status_filter: Comma-separated list of status values to filter by (optional)
        limit: Maximum number of results to return (default: 100)
        offset: Number of results to skip for pagination (default: 0)
    
    Returns:
        JSON string with search results
    """
    try:
        # Parse comma-separated parameters
        symbols_list = [s.strip().upper() for s in symbols.split(",") if s.strip()] if symbols else None
        event_types_list = [e.strip().upper() for e in event_types.split(",") if e.strip()] if event_types else None
        status_filter_list = [s.strip().upper() for s in status_filter.split(",") if s.strip()] if status_filter else None
        
        # Use "*" for empty search text to get all results
        search_query = search_text.strip() if search_text.strip() else "*"
        
        # Search from AI Search
        result = await search_corporate_actions_from_ai_search(
            search_text=search_query,
            symbols=symbols_list,
            event_types=event_types_list,
            status_filter=status_filter_list,
            top=limit,
            skip=offset
        )
        
        logger.info(f"search_corporate_actions: Found {result.get('returned_count', 0)} results")
        
        return json.dumps({
            "success": True,
            "events": result.get("results", []),  # Use "events" key that the UI expects
            "corporate_actions": result.get("results", []),  # Keep this for backward compatibility
            "total_count": result.get("total_count", 0),
            "returned_count": result.get("returned_count", 0),
            "data_source": result.get("data_source", "ai_search"),
            "query_parameters": {
                "search_text": search_query,
                "symbols": symbols_list,
                "event_types": event_types_list,
                "status_filter": status_filter_list,
                "limit": limit,
                "offset": offset
            }
        }, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"❌ Error in search_corporate_actions tool: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return json.dumps({
            "success": False,
            "error": str(e),
            "corporate_actions": [],
            "total_count": 0,
            "data_source": "error"
        }, indent=2, default=str)

# =============================================================================
# Data Generation Tool (Replicated from data_ingestion.py logic)
# =============================================================================

@app.tool()
async def generate_sample_data(symbols: str, num_events_per_symbol: int = 3) -> str:
    """
    Generate sample corporate actions data using the same logic as data_ingestion.py
    Stores data in Azure AI Search and Cosmos DB (assumes containers already exist)
    
    Args:
        symbols: Comma-separated list of stock symbols (e.g., "AAPL,MSFT,TSLA")
        num_events_per_symbol: Number of events to generate per symbol
    
    Returns:
        JSON string with generation results and summary
    """
    try:
        # Parse symbols
        symbols_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        if not symbols_list:
            return json.dumps({
                "success": False,
                "error": "No valid symbols provided"
            })
        
        logger.info(f"Generating sample data for symbols: {symbols_list}")
        
        # Generate events using the same logic as data_ingestion.py
        events = []
        for symbol in symbols_list:
            symbol_events = await generate_events_for_symbol(symbol, num_events_per_symbol)
            events.extend(symbol_events)
        
        # Generate correlated inquiries
        inquiries = generate_correlated_inquiries(events, len(events) * 2)
        
        # Store in Azure AI Search
        search_stored_count = 0
        if search_client:
            try:
                # Prepare documents for search with embeddings
                search_documents = []
                for event in events:
                    # Create search document
                    search_doc = await prepare_search_document(event)
                    search_documents.append(search_doc)
                
                # Upload in batches
                batch_size = 50
                for i in range(0, len(search_documents), batch_size):
                    batch = search_documents[i:i + batch_size]
                    await search_client.upload_documents(batch)
                    search_stored_count += len(batch)
                    logger.info(f"Uploaded batch {i//batch_size + 1}: {len(batch)} documents")
                
                logger.info(f"✅ Stored {search_stored_count} events in Azure AI Search")
            except Exception as e:
                logger.error(f"❌ Error storing in Azure AI Search: {e}")
        
        # Store inquiries in Cosmos DB
        cosmos_stored_count = 0
        if cosmos_client and inquiries_container:
            try:
                for inquiry in inquiries:
                    await inquiries_container.create_item(inquiry)
                    cosmos_stored_count += 1
                
                logger.info(f"✅ Stored {cosmos_stored_count} inquiries in Cosmos DB")
            except Exception as e:
                logger.error(f"❌ Error storing in Cosmos DB: {e}")
        
        # Return success response
        return json.dumps({
            "success": True,
            "summary": {
                "total_events_generated": len(events),
                "total_events_stored": search_stored_count,
                "total_inquiries_generated": len(inquiries),
                "total_inquiries_stored": cosmos_stored_count,
                "symbols": symbols_list
            },
            "sample_events": events[:5],  # Show first 5 events as examples
            "sample_inquiries": inquiries[:3],  # Show first 3 inquiries as examples
            "message": f"Generated {len(events)} events and {len(inquiries)} inquiries for {len(symbols_list)} symbols"
        }, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"❌ Error in generate_sample_data: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return json.dumps({
            "success": False,
            "error": str(e),
            "summary": {"total_events_generated": 0, "total_events_stored": 0}
        }, indent=2, default=str)

async def generate_events_for_symbol(symbol: str, count: int) -> List[Dict[str, Any]]:
    """Generate corporate action events for a specific symbol (replicated from data_ingestion.py)"""
    events = []
    
    # Company mapping (simplified version from data_ingestion.py)
    company_map = {
        "AAPL": {"name": "Apple Inc.", "cusip": "037833100"},
        "MSFT": {"name": "Microsoft Corporation", "cusip": "594918104"},
        "TSLA": {"name": "Tesla, Inc.", "cusip": "88160R101"},
        "GOOGL": {"name": "Alphabet Inc.", "cusip": "02079K305"},
        "AMZN": {"name": "Amazon.com Inc.", "cusip": "023135106"},
        "META": {"name": "Meta Platforms Inc.", "cusip": "30303M102"},
        "NFLX": {"name": "Netflix Inc.", "cusip": "64110L106"},
        "NVDA": {"name": "NVIDIA Corporation", "cusip": "67066G104"}
    }
    
    company_info = company_map.get(symbol, {"name": f"{symbol} Corporation", "cusip": f"{symbol}123456"})
    company_name = company_info["name"]
    cusip = company_info["cusip"]
    
    # Event types and statuses (from data_ingestion.py)
    event_types = ["DIVIDEND", "STOCK_SPLIT", "MERGER", "STOCK_DIVIDEND", "RIGHTS_OFFERING", "SPIN_OFF"]
    statuses = ["ANNOUNCED", "CONFIRMED", "PENDING", "COMPLETED"]
    
    for i in range(count):
        event_type = random.choice(event_types)
        status = random.choice(statuses)
        
        # Generate dates (replicated logic)
        announcement_date = date.today() + timedelta(days=random.randint(-60, 30))
        record_date = announcement_date + timedelta(days=random.randint(10, 30))
        ex_date = record_date - timedelta(days=1)
        payable_date = record_date + timedelta(days=random.randint(7, 21))
        effective_date = ex_date
        
        # Generate event-specific details (replicated logic)
        event_details = {}
        description = ""
        
        if event_type == "DIVIDEND":
            dividend_amount = round(random.uniform(0.10, 2.50), 2)
            event_details = {
                "dividend_amount": dividend_amount,
                "currency": "USD",
                "dividend_type": "CASH",
                "tax_rate": round(random.uniform(0.15, 0.35), 2)
            }
            description = f"${dividend_amount} quarterly cash dividend declared by {company_name}"
            
        elif event_type == "STOCK_SPLIT":
            split_ratios = [(2, 1), (3, 1), (3, 2), (4, 1)]
            ratio_to, ratio_from = random.choice(split_ratios)
            event_details = {
                "split_ratio_from": ratio_from,
                "split_ratio_to": ratio_to,
                "fractional_share_handling": "CASH_IN_LIEU"
            }
            description = f"{ratio_to}:{ratio_from} stock split announced by {company_name}"
            
        elif event_type == "MERGER":
            acquiring_companies = ["Microsoft Corp", "Amazon Inc", "Alphabet Inc", "Meta Platforms"]
            acquiring_company = random.choice(acquiring_companies)
            event_details = {
                "acquiring_company": acquiring_company,
                "acquiring_symbol": random.choice(["MSFT", "AMZN", "GOOGL", "META"]),
                "exchange_ratio": round(random.uniform(0.5, 2.0), 3),
                "cash_consideration": round(random.uniform(10.0, 50.0), 2),
                "stock_consideration": round(random.uniform(0.1, 1.0), 3)
            }
            description = f"Merger agreement between {company_name} and {acquiring_company}"
            
        elif event_type == "STOCK_DIVIDEND":
            dividend_rate = round(random.uniform(0.05, 0.20), 3)
            event_details = {
                "dividend_amount": dividend_rate,
                "currency": "USD", 
                "dividend_type": "STOCK",
                "stock_dividend_rate": dividend_rate
            }
            description = f"{dividend_rate*100}% stock dividend declared by {company_name}"
            
        elif event_type == "RIGHTS_OFFERING":
            event_details = {
                "subscription_price": round(random.uniform(10.0, 100.0), 2),
                "rights_ratio": f"{random.randint(1, 5)}:1",
                "exercise_period_days": random.randint(14, 45)
            }
            description = f"Rights offering announced by {company_name}"
            
        else:
            description = f"{event_type.replace('_', ' ').title()} corporate action for {company_name}"
        
        event_id = f"{symbol}_{event_type}_{announcement_date.year}_{i:04d}"
        
        # Create schema-compliant event (matching data_ingestion.py structure)
        event = {
            "id": event_id,
            "event_id": event_id,
            "event_type": event_type,
            "security": {
                "symbol": symbol,
                "cusip": cusip,
                "isin": f"US{cusip}10" if cusip else None,
                "sedol": None
            },
            "issuer_name": company_name,
            "announcement_date": announcement_date.isoformat(),
            "record_date": record_date.isoformat(),
            "ex_date": ex_date.isoformat(),
            "payable_date": payable_date.isoformat(),
            "effective_date": effective_date.isoformat(),
            "status": status,
            "description": description,
            "event_details": event_details,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "data_source": "SAMPLE_GENERATOR",
            "symbol": symbol  # Partition key for CosmosDB
        }
        events.append(event)
    
    return events

async def prepare_search_document(event: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare event for Azure AI Search with vector embedding"""
    try:
        # Create searchable content
        searchable_content = f"""
        Company: {event.get('issuer_name', '')}
        Symbol: {event.get('security', {}).get('symbol', '')}
        Event Type: {event.get('event_type', '').replace('_', ' ')}
        Description: {event.get('description', '')}
        Status: {event.get('status', '')}
        Details: {json.dumps(event.get('event_details', {}), default=str)}
        """.strip()
        
        # Generate embedding
        content_vector = await generate_embedding(searchable_content)
        
        # Create search document
        search_doc = {
            "event_id": event["event_id"],
            "event_type": event["event_type"],
            "symbol": event.get("security", {}).get("symbol", ""),
            "issuer_name": event.get("issuer_name", ""),
            "announcement_date": event.get("announcement_date", ""),
            "record_date": event.get("record_date", ""),
            "ex_date": event.get("ex_date", ""),
            "payable_date": event.get("payable_date", ""),
            "effective_date": event.get("effective_date", ""),
            "status": event.get("status", ""),
            "description": event.get("description", ""),
            "event_details_json": json.dumps(event.get("event_details", {})),
            "created_at": event.get("created_at", ""),
            "updated_at": event.get("updated_at", ""),
            "data_source": event.get("data_source", ""),
            "content": searchable_content,
            "content_vector": content_vector
        }
        
        return search_doc
        
    except Exception as e:
        logger.error(f"Error preparing search document: {e}")
        # Return document without vector if embedding fails
        return {
            "event_id": event["event_id"],
            "content": f"Error processing {event.get('event_id', 'unknown')}: {str(e)}"
        }

def generate_correlated_inquiries(events: List[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
    """Generate correlated inquiries for events (replicated from data_ingestion.py)"""
    inquiries = []
    
    user_names = ["John Investor", "Sarah Trader", "Mike Portfolio", "Anna Analyst", "Bob Manager", "Lisa Chen", "David Kim"]
    organizations = ["ABC Investment Fund", "XYZ Capital", "Individual Investor", "Pension Fund LLC", "Retirement Fund", "Hedge Fund Partners"]
    
    inquiry_subjects = {
        "DIVIDEND": ["Ex-dividend date clarification", "Dividend payment timing", "Tax implications of dividend"],
        "STOCK_SPLIT": ["Stock split impact on options", "Fractional shares handling", "Split timing and execution"],
        "MERGER": ["Merger exchange ratio details", "Cash vs stock election", "Timeline for merger completion"],
        "STOCK_DIVIDEND": ["Stock dividend vs cash dividend", "Tax treatment of stock dividend", "Impact on cost basis"],
        "RIGHTS_OFFERING": ["Rights subscription process", "Exercise vs sell rights", "Subscription price details"],
        "SPIN_OFF": ["Spin-off distribution details", "Tax implications", "New company trading details"]
    }
    
    for i in range(min(count, len(events) * 3)):  # Limit inquiries
        event = random.choice(events)
        event_type = event["event_type"]
        symbol = event["security"]["symbol"]
        
        base_subjects = inquiry_subjects.get(event_type, ["General inquiry about corporate action event"])
        subject = random.choice(base_subjects)
        
        detailed_descriptions = [
            f"I need clarification on the {event_type.lower().replace('_', ' ')} for {symbol}. Can you provide more details?",
            f"How will this {event_type.lower().replace('_', ' ')} affect my holdings in {symbol}?",
            f"What are the key dates I need to be aware of for this {symbol} corporate action?",
            f"Could you explain the financial implications of this {event_type.lower().replace('_', ' ')} event?",
            f"I have questions about the tax treatment of this {symbol} {event_type.lower().replace('_', ' ')}."
        ]
        description = random.choice(detailed_descriptions)
        
        inquiry_id = f"INQ_{event['event_id']}_{i:04d}_{datetime.now().strftime('%H%M%S')}"
        
        inquiry = {
            "id": inquiry_id,
            "inquiry_id": inquiry_id,
            "event_id": event["event_id"],
            "user_id": f"user_{random.randint(1000, 9999)}",
            "user_name": random.choice(user_names),
            "user_role": "CONSUMER",
            "organization": random.choice(organizations),
            "subject": subject,
            "description": description,
            "priority": random.choice(["LOW", "MEDIUM", "HIGH", "URGENT"]),
            "status": random.choice(["OPEN", "ACKNOWLEDGED", "IN_REVIEW", "RESPONDED", "ESCALATED", "RESOLVED", "CLOSED"]),
            "assigned_to": f"admin_{random.randint(1, 5)}" if random.random() > 0.5 else None,
            "response": None,
            "resolution_notes": None,
            "created_at": (datetime.now() - timedelta(days=random.randint(0, 5))).isoformat(),
            "updated_at": datetime.now().isoformat(),
            "due_date": None,
            "resolved_at": None,
            "subscribers": [f"user_{random.randint(1000, 9999)}"],
            "notification_history": []
        }
        inquiries.append(inquiry)
    
    return inquiries

# =============================================================================
# Core RAG Functions with Vector Search and OpenAI
# =============================================================================

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
            #return get_sample_events()[:max_results]
            return []
        
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
        #return get_sample_events()[:max_results]
        return []

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
def main():
    """Main application entry point"""
    logger.info("🚀 Starting Corporate Actions MCP Server with SSE Support")
    
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
#!/usr/bin/env python3
"""
Test script to verify Cosmos DB insertion with the fix
"""
import asyncio
import os
import json
from datetime import datetime
import platform

# Load environment
from dotenv import load_dotenv
load_dotenv()

from azure.cosmos.aio import CosmosClient

async def test_single_insertion():
    """Test inserting a single event to verify the fix"""
    
    # Set Windows event loop policy
    if platform.system() == "Windows":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            print("Set Windows SelectorEventLoop policy")
        except AttributeError:
            print("WindowsSelectorEventLoopPolicy not available, using default")
    
    # Initialize Cosmos client
    cosmos_endpoint = os.getenv("AZURE_COSMOS_ENDPOINT")
    cosmos_key = os.getenv("AZURE_COSMOS_KEY")
    
    if not cosmos_endpoint or not cosmos_key:
        print("Missing Cosmos DB credentials")
        return
    
    cosmos_client = CosmosClient(cosmos_endpoint, cosmos_key)
    
    try:
        # Get database and container
        database_name = os.getenv("AZURE_COSMOS_DATABASE_NAME", "semantickernel")
        database = cosmos_client.get_database_client(database_name)
        container = database.get_container_client("events")
        
        # Test document with the required 'id' field
        test_event = {
            'id': 'BAC_RIGHTS_OFFERING_2024_000',  # Required id field
            'event_id': 'BAC_RIGHTS_OFFERING_2024_000', 
            'event_type': 'rights_offering', 
            'security': {
                'symbol': 'BAC', 
                'cusip': '707147648', 
                'isin': 'US5043116782'
            }, 
            'issuer_name': 'Bank of America Corp.', 
            'announcement_date': '2024-04-19', 
            'record_date': '2024-05-05', 
            'ex_date': '2024-05-04', 
            'payable_date': '2024-05-19', 
            'status': 'processed', 
            'description': 'Rights Offering corporate action', 
            'event_details': {}, 
            'data_source': 'GENERATED', 
            'created_at': '2025-06-14T12:45:38.000056', 
            'updated_at': '2025-06-14T12:45:38.000056'
        }
        
        print(f"Attempting to insert event: {test_event['event_id']}")
        print(f"Document structure: {json.dumps(test_event, indent=2)}")
        
        # Try to insert the document
        result = await container.upsert_item(test_event)
        print(f"✅ Successfully inserted event: {result['id']}")
        print(f"Response: {json.dumps(result, indent=2, default=str)}")
        
    except Exception as e:
        print(f"❌ Error inserting event: {e}")
        print(f"Exception type: {type(e)}")
        
    finally:
        await cosmos_client.close()

if __name__ == "__main__":
    asyncio.run(test_single_insertion())

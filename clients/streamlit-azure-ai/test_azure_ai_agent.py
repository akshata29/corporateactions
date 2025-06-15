#!/usr/bin/env python3
"""
Test script for Azure AI Agent Service with proper authentication
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=== Azure AI Agent Service Test ===")

# Check environment variables
endpoint = os.getenv('AZURE_AI_PROJECT_URL')
print(f"Endpoint: {endpoint}")
print(f"Uses HTTPS: {'✓ Yes' if endpoint and endpoint.startswith('https://') else '✗ No'}")

try:
    from azure.identity import DefaultAzureCredential
    from azure.ai.projects import AIProjectClient
    print("✓ Azure AI SDK imports successful")
except ImportError as e:
    print(f"✗ Azure AI SDK import failed: {e}")
    exit(1)

print("\n=== Testing Authentication ===")
try:
    print("Creating DefaultAzureCredential...")
    credential = DefaultAzureCredential()
    print("✓ DefaultAzureCredential created")
    
    print(f"Creating AIProjectClient with endpoint: {endpoint}")
    project_client = AIProjectClient(
        endpoint=endpoint,
        credential=credential,
        api_version="2024-10-01-preview"
    )
    print("✓ AIProjectClient created successfully")
    
    # Get agents client
    agents_client = project_client.agents
    print("✓ Agents client obtained successfully")
    
except Exception as e:
    print(f"✗ Authentication setup failed: {e}")
    print(f"  Error type: {type(e).__name__}")
    exit(1)

print("\n=== Testing Agent Operations ===")
try:
    print("Testing list_agents()...")
    agents = agents_client.list_agents()
    agent_list = list(agents.value) if hasattr(agents, 'value') else list(agents)
    print(f"✓ Successfully listed {len(agent_list)} agents")
    
    if agent_list:
        for i, agent in enumerate(agent_list[:3]):  # Show first 3 agents
            print(f"  - Agent {i+1}: {agent.name} (ID: {agent.id})")
    else:
        print("  No existing agents found")
        
    print("\n=== Testing Agent Creation ===")
    # Try to create a simple test agent
    test_agent_name = "Test Corporate Actions Agent"
    test_agent = agents_client.create_agent(
        model="gpt-4o-mini",
        name=test_agent_name,
        instructions="You are a helpful assistant for corporate actions analysis.",
        tools=[]
    )
    print(f"✓ Successfully created test agent: {test_agent.name} (ID: {test_agent.id})")
    
    # Clean up - delete the test agent
    print(f"Cleaning up test agent...")
    agents_client.delete_agent(test_agent.id)
    print("✓ Test agent deleted successfully")
        
except Exception as e:
    print(f"✗ Agent operations failed: {e}")
    print(f"  Error type: {type(e).__name__}")
    
    # Additional debug info
    if hasattr(e, 'response'):
        print(f"  Response status: {e.response.status_code if hasattr(e.response, 'status_code') else 'N/A'}")
    if hasattr(e, 'message'):
        print(f"  Error message: {e.message}")

print("\n=== Test Complete ===")

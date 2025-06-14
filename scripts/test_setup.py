"""
Test script to verify Corporate Actions POC setup
"""

import asyncio
import requests
import json
import sys
from datetime import datetime
import time

# Test configuration
SERVICES = {
    "MCP Server (RAG)": "http://localhost:8000",
    "Web Search MCP": "http://localhost:8001", 
    "Comments MCP": "http://localhost:8002",
    "Streamlit UI": "http://localhost:8501"
}

def test_service_health(service_name, base_url):
    """Test if a service is running and healthy"""
    try:
        health_url = f"{base_url}/health"
        response = requests.get(health_url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {service_name}: {data.get('status', 'unknown')}")
            return True
        else:
            print(f"❌ {service_name}: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ {service_name}: Connection failed (service not running)")
        return False
    except requests.exceptions.Timeout:
        print(f"⚠️  {service_name}: Request timeout")
        return False
    except Exception as e:
        print(f"❌ {service_name}: Error - {str(e)}")
        return False

def test_rag_query():
    """Test RAG functionality"""
    try:
        print("\n🧪 Testing RAG Query...")
        
        url = f"{SERVICES['MCP Server (RAG)']}/rag/query"
        params = {
            "query": "Show me Apple dividends",
            "max_results": 3
        }
        
        response = requests.post(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ RAG Query successful")
            print(f"   Answer: {data.get('answer', 'No answer')[:100]}...")
            print(f"   Sources: {len(data.get('sources', []))} found")
            return True
        else:
            print(f"❌ RAG Query failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ RAG Query error: {str(e)}")
        return False

def test_event_search():
    """Test event search functionality"""
    try:
        print("\n🔍 Testing Event Search...")
        
        url = f"{SERVICES['MCP Server (RAG)']}/search"
        search_query = {
            "symbols": ["AAPL"],
            "limit": 5
        }
        
        response = requests.post(url, json=search_query, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            events = data.get('events', [])
            print(f"✅ Event Search successful")
            print(f"   Found {len(events)} events")
            if events:
                print(f"   Sample: {events[0].get('issuer_name', 'N/A')} - {events[0].get('event_type', 'N/A')}")
            return True
        else:
            print(f"❌ Event Search failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Event Search error: {str(e)}")
        return False

def test_web_search():
    """Test web search functionality"""
    try:
        print("\n🌐 Testing Web Search...")
        
        url = f"{SERVICES['Web Search MCP']}/search"
        search_data = {
            "query": "Apple dividend announcement",
            "max_results": 3
        }
        
        response = requests.post(url, json=search_data, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print(f"✅ Web Search successful")
            print(f"   Found {len(results)} results")
            if results:
                print(f"   Sample: {results[0].get('title', 'N/A')[:50]}...")
            return True
        else:
            print(f"❌ Web Search failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Web Search error: {str(e)}")
        return False

def test_comments():
    """Test comments functionality"""
    try:
        print("\n💬 Testing Comments System...")
        
        # Test getting comments for an event
        event_id = "CA-2025-001"
        url = f"{SERVICES['Comments MCP']}/events/{event_id}/comments"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            comments = data.get('comments', [])
            print(f"✅ Comments retrieval successful")
            print(f"   Found {len(comments)} comments for event {event_id}")
            return True
        else:
            print(f"❌ Comments test failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Comments test error: {str(e)}")
        return False

def test_analytics():
    """Test analytics functionality"""
    try:
        print("\n📊 Testing Analytics...")
        
        url = f"{SERVICES['Comments MCP']}/analytics"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Analytics successful")
            print(f"   Total Comments: {data.get('total_comments', 0)}")
            print(f"   Questions: {data.get('questions_count', 0)}")
            print(f"   Resolution Rate: {(data.get('resolved_count', 0) / max(data.get('total_comments', 1), 1) * 100):.1f}%")
            return True
        else:
            print(f"❌ Analytics test failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Analytics test error: {str(e)}")
        return False

def main():
    """Main test function"""
    print("🧪 Corporate Actions POC - System Test")
    print("=" * 50)
    
    # Test service health
    print("\n🏥 Testing Service Health...")
    healthy_services = 0
    
    for service_name, base_url in SERVICES.items():
        if test_service_health(service_name, base_url):
            healthy_services += 1
        time.sleep(0.5)  # Small delay between requests
    
    print(f"\nHealth Check Results: {healthy_services}/{len(SERVICES)} services healthy")
    
    if healthy_services == 0:
        print("\n❌ No services are running. Please start the services first:")
        print("   .\\scripts\\start_services.ps1")
        sys.exit(1)
    
    # Test functionality
    print("\n🔧 Testing Functionality...")
    tests_passed = 0
    total_tests = 0
    
    test_functions = [
        test_rag_query,
        test_event_search,
        test_web_search,
        test_comments,
        test_analytics
    ]
    
    for test_func in test_functions:
        total_tests += 1
        try:
            if test_func():
                tests_passed += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} failed with exception: {str(e)}")
        time.sleep(1)  # Small delay between tests
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary")
    print(f"Services Health: {healthy_services}/{len(SERVICES)} ({'✅' if healthy_services == len(SERVICES) else '⚠️'})")
    print(f"Functionality Tests: {tests_passed}/{total_tests} ({'✅' if tests_passed == total_tests else '⚠️'})")
    
    if healthy_services == len(SERVICES) and tests_passed == total_tests:
        print("\n🎉 All tests passed! Your Corporate Actions POC is ready to use.")
        print("\n🔗 Access Points:")
        print("   📊 Dashboard: http://localhost:8501")
        print("   📚 API Docs: http://localhost:8000/docs")
    elif healthy_services < len(SERVICES):
        print("\n⚠️  Some services are not running. Check the startup script and logs.")
    else:
        print("\n⚠️  Some functionality tests failed. Check Azure service configuration.")
        print("   Make sure your .env file has valid Azure credentials.")
    
    print(f"\nTest completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()

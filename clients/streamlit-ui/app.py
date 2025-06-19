"""
Streamlit UI for Corporate Actions POC - MCP Integration
Interactive dashboard for market participants using MCP protocol
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import asyncio
import threading
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
import sys
import io
import contextlib
from streamlit_modal import Modal
import uuid
# Add dynamic code execution imports
import subprocess
import tempfile
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# MCP Client import - Using official MCP Python SDK
try:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    import asyncio
    USE_MCP = True
except ImportError:
    USE_MCP = False
    st.warning("MCP Python SDK not available. Using sample data.")

# MCP Server URLs (FastMCP servers accessed via official MCP Python SDK client)
MCP_SERVERS = {
    "rag": "http://localhost:8000/mcp",
    "websearch": "http://localhost:8001/mcp"
}

# Page configuration
st.set_page_config(
    page_title="Corporate Actions Dashboard - MCP",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for inquiry management
if "selected_event_for_inquiry" not in st.session_state:
    st.session_state.selected_event_for_inquiry = None
if "current_user_id" not in st.session_state:
    st.session_state.current_user_id = "user_001"
if "current_user_name" not in st.session_state:
    st.session_state.current_user_name = "Demo User"
if "current_organization" not in st.session_state:
    st.session_state.current_organization = "Demo Organization"

# Official MCP client for MCP servers
class SimpleMCPClient:
    """Official MCP Python SDK client to communicate with MCP servers"""
    
    def __init__(self):
        self.servers = MCP_SERVERS
    async def _call_tool_async(self, server_url: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on MCP server using official MCP Client"""
        try:
            async with streamablehttp_client(server_url) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    # Initialize the connection
                    await session.initialize()
                    
                    # Call the tool
                    result = await session.call_tool(tool_name, arguments)
                    
                    # Extract text content from MCP result
                    if hasattr(result, 'content') and result.content:
                        # Get the first content block (should be text)
                        first_content = result.content[0]
                        if hasattr(first_content, 'text'):
                            return first_content.text
                        else:
                            return str(first_content)
                    else:
                        return str(result)
        except Exception as e:
            return {"error": f"MCP error: {str(e)}"}
    
    def _call_tool(self, server_url: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous wrapper for async tool calls"""
        import threading
        
        def run_async_in_thread():
            """Run async call in a separate thread with its own event loop"""
            try:
                # Create a new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(self._call_tool_async(server_url, tool_name, arguments))
                finally:
                    loop.close()
            except Exception as e:
                return {"error": f"Thread execution error: {str(e)}"}
        
        try:
            # Always run in a separate thread to avoid event loop conflicts
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_async_in_thread)
                result = future.result(timeout=30)
                return result
        except concurrent.futures.TimeoutError:
            return {"error": "Request timed out after 30 seconds"}
        except Exception as e:
            return {"error": f"Execution error: {str(e)}"}
    
    def rag_query(self, query: str, max_results: int = 5, chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Query the RAG server with chat history support"""
        # Convert chat history to JSON string if provided
        history_json = ""
        if chat_history:
            try:
                history_json = json.dumps(chat_history)
            except:
                history_json = ""
        
        result = self._call_tool(
            self.servers['rag'],
            "rag_query",
            {
                "query": query,
                "max_results": max_results,
                "chat_history": history_json
            }
        )
        # If result is a string (successful), parse as JSON
        if isinstance(result, str):
            try:
                return json.loads(result)
            except:
                return {"answer": result}
        # If result is a dict, it's an error response
        return result
    
    def search_corporate_actions(self, **kwargs) -> Dict[str, Any]:
        """Search corporate actions"""
        result = self._call_tool(self.servers['rag'], "search_corporate_actions", kwargs)
        # If result is a string (successful), parse as JSON
        if isinstance(result, str):
            try:
                return json.loads(result)
            except:
                return {"events": [], "total_count": 0}
        # If result is a dict, it's an error response
        return result
    def web_search(self, query: str, result_count: int = 10) -> Dict[str, Any]:
        """Web search"""
        result = self._call_tool(
            self.servers['websearch'],
            "web_search",
            {
                "query": query,
                "max_results": result_count
            }
        )
        # If result is a string (successful), parse as JSON
        if isinstance(result, str):
            try:
                return json.loads(result)
            except:
                return {"results": []}
        # If result is a dict, it's an error response
        return result
    
    def news_search(self, query: str, result_count: int = 10) -> Dict[str, Any]:
        """News search"""
        result = self._call_tool(
            self.servers['websearch'],
            "news_search",
            {
                "query": query,
                "max_results": result_count
            }
        )
        # If result is a string (successful), parse as JSON
        if isinstance(result, str):
            try:
                return json.loads(result)
            except:
                return {"results": []}
        # If result is a dict, it's an error response
        return result
    
    def financial_data_search(self, symbol: str, data_type: str = "overview") -> Dict[str, Any]:
        """Financial data search"""
        result = self._call_tool(
            self.servers['websearch'],
            "financial_data_search",
            {
                "symbol": symbol,
                "data_type": data_type
            }
        )
        # If result is a string (successful), parse as JSON
        if isinstance(result, str):
            try:
                return json.loads(result)
            except:                return {"results": []}
        # If result is a dict, it's an error response
        return result
                
    def check_server_health(self, server_name: str) -> Dict[str, Any]:
        """Check health of a specific MCP server"""
        if server_name not in self.servers:
            return {"error": f"Unknown server: {server_name}"}
        
        server_url = self.servers[server_name]
        
        # Test with appropriate health check tool for each server
        if server_name == 'rag':
            result = self._call_tool(server_url, "get_service_health", {})
        elif server_name == 'websearch':
            result = self._call_tool(server_url, "get_search_health", {})
        else:
            return {"error": f"No health check defined for server: {server_name}"}
        
        # Parse JSON result if it's a string
        if isinstance(result, str):
            try:
                return json.loads(result)
            except:
                return {"status": "ok", "response": result}
        # If result is a dict, return as-is (likely an error)
        return result

    # Inquiry Management Functions
    def create_inquiry(self, event_id: str, user_id: str, user_name: str, organization: str, 
                        subject: str, description: str, priority: str = "MEDIUM") -> Dict[str, Any]:
        """Create a new inquiry using MCP client"""
        result = self._call_tool(
            self.servers['rag'],
            "create_inquiry_tool",
            {
                "event_id": event_id,
                "user_id": user_id,
                "user_name": user_name,
                "organization": organization,
                "subject": subject,
                "description": description,
                "priority": priority
            }
        )
        # If result is a string (successful), parse as JSON
        if isinstance(result, str):
            try:
                return json.loads(result)
            except:
                return {"success": False, "error": "Failed to parse response"}
        # If result is a dict, it's an error response
        return result

    def get_inquiries(self, event_id: str) -> Dict[str, Any]:
        """Get all inquiries for a specific event"""
        result = self._call_tool(
            self.servers['rag'],
            "get_inquiries_tool",
            {"event_id": event_id}
        )
        # If result is a string (successful), parse as JSON
        if isinstance(result, str):
            try:
                return json.loads(result)
            except:
                return {"inquiries": [], "count": 0}
        # If result is a dict, it's an error response
        return result

    def get_user_inquiries(self, event_id: str, user_id: str) -> Dict[str, Any]:
        """Get user's inquiries for a specific event"""
        result = self._call_tool(
            self.servers['rag'],
            "get_user_inquiries_tool",
            {
                "event_id": event_id,
                "user_id": user_id
            }
        )
        # If result is a string (successful), parse as JSON
        if isinstance(result, str):
            try:
                return json.loads(result)
            except:
                return {"inquiries": [], "count": 0}
        # If result is a dict, it's an error response
        return result

    def update_inquiry(self, inquiry_id: str, **updates) -> Dict[str, Any]:
        """Update an existing inquiry"""
        result = self._call_tool(
            self.servers['rag'],
            "update_inquiry_tool",
            {
                "inquiry_id": inquiry_id,
                **updates
            }
        )
        # If result is a string (successful), parse as JSON
        if isinstance(result, str):
            try:
                return json.loads(result)
            except:
                return {"success": False, "error": "Failed to parse response"}
        # If result is a dict, it's an error response
        return result

    def delete_inquiry(self, inquiry_id: str, user_id: str) -> Dict[str, Any]:
        """Delete an inquiry (user's own only)"""
        result = self._call_tool(
            self.servers['rag'],
            "delete_inquiry_tool",
            {
                "inquiry_id": inquiry_id,
                "user_id": user_id
            }
        )
        # If result is a string (successful), parse as JSON
        if isinstance(result, str):
            try:
                return json.loads(result)
            except:
                return {"success": False, "error": "Failed to parse response"}
        # If result is a dict, it's an error response
        return result

# Initialize client
@st.cache_resource
def get_client():
    """Get MCP client for MCP servers"""
    if USE_MCP:
        try:
            return SimpleMCPClient()
        except Exception as e:
            st.warning(f"MCP client unavailable: {e}. Using sample data.")
            return None
    return None

def check_server_status():
    """Check the status of MCP servers using official MCP Python SDK client - cached for performance"""
    if not client:
        return {
            "status": "no_client",
            "message": "MCP client not available. Check if MCP Python SDK library is installed."
        }
    
    # Use session state to cache server status for 5 minutes
    cache_duration = 300  # 5 minutes in seconds
    current_time = datetime.now().timestamp()
    
    if "server_status_cache" in st.session_state:
        cache_time = st.session_state.server_status_cache.get("timestamp", 0)
        if current_time - cache_time < cache_duration:
            return st.session_state.server_status_cache["status"]
    
    # Check server status
    try:
        # Quick health check on just one server to avoid multiple slow checks
        result = client.check_server_health('rag')
        #print(f"RAG Server Health Check: {result}")
        if "error" in result:
            status = {
                "status": "disconnected", 
                "message": f"MCP servers not responding: {result['error']}. Please start with: python start_mcp_servers.py"
            }
        else:
            status = {
                "status": "connected",
                "message": "Connected to MCP servers successfully"
            }
    except Exception as e:
        status = {
            "status": "error",
            "message": f"Error connecting to MCP servers: {str(e)}. Start with: python start_mcp_servers.py"
        }
    
    # Cache the result
    st.session_state.server_status_cache = {
        "status": status,
        "timestamp": current_time
    }
    
    return status

client = get_client()

# Custom CSS for enhanced dashboard styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1f4e79, #2e6da4);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #007bff;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .status-confirmed { 
        background: #d4edda !important; 
        color: #155724 !important; 
        font-weight: bold !important;
        border-radius: 5px !important;
        padding: 5px 10px !important;
    }
    .status-announced { 
        background: #fff3cd !important; 
        color: #856404 !important; 
        font-weight: bold !important;
        border-radius: 5px !important;
        padding: 5px 10px !important;
    }
    .status-pending { 
        background: #f8d7da !important; 
        color: #721c24 !important; 
        font-weight: bold !important;
        border-radius: 5px !important;
        padding: 5px 10px !important;
    }
    .status-processed { 
        background: #d1ecf1 !important; 
        color: #0c5460 !important; 
        font-weight: bold !important;
        border-radius: 5px !important;
        padding: 5px 10px !important;
    }
    .insight-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }    .chart-container {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
    }
    
    .chat-message {
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
    }
    .assistant-message {
        background-color: #f3e5f5;
        border-left: 4px solid #9c27b0;
    }
    
    /* Enhanced dataframe styling */
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    /* Streamlit metric styling enhancement */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border: 1px solid #e1e5e9;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    div[data-testid="metric-container"] > div {
        width: fit-content;
        margin: auto;
    }
    div[data-testid="metric-container"] label {
        width: fit-content;
        margin: auto;
    }
                /* Add these inquiry-specific styles */
    .inquiry-card {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #007bff;
    }
    .inquiry-priority-high { border-left-color: #dc3545; }
    .inquiry-priority-urgent { border-left-color: #fd7e14; }
    .inquiry-priority-medium { border-left-color: #ffc107; }
    .inquiry-priority-low { border-left-color: #28a745; }
    
    .inquiry-status-open { background-color: #fff3cd; }
    .inquiry-status-in_review { background-color: #d1ecf1; }
    .inquiry-status-responded { background-color: #d4edda; }
    .inquiry-status-resolved { background-color: #d4edda; }
    .inquiry-status-closed { background-color: #f8d7da; }
    
    .inquiry-button {
        margin: 0.25rem;
        padding: 0.375rem 0.75rem;
        border-radius: 0.375rem;
        border: 1px solid transparent;
        font-size: 0.875rem;
        font-weight: 500;
        text-align: center;
        cursor: pointer;
        text-decoration: none;
        display: inline-block;
    }
    .btn-create { 
        background-color: #28a745; 
        color: white; 
        border-color: #28a745;
    }
    .btn-create:hover {
        background-color: #218838;
        border-color: #1e7e34;
    }
    .btn-view { 
        background-color: #007bff; 
        color: white;
        border-color: #007bff;
    }
    .btn-view:hover {
        background-color: #0069d9;
        border-color: #0062cc;
    }
    .btn-edit { 
        background-color: #ffc107; 
        color: #212529;
        border-color: #ffc107;
    }
    .btn-edit:hover {
        background-color: #e0a800;
        border-color: #d39e00;
    }
            /* Enhanced button styling for disabled state */
    .stButton > button:disabled {
        background-color: #e9ecef !important;
        color: #6c757d !important;
        border-color: #dee2e6 !important;
        cursor: not-allowed !important;
        opacity: 0.65 !important;
    }
    
    .stButton > button:disabled:hover {
        background-color: #e9ecef !important;
        color: #6c757d !important;
        border-color: #dee2e6 !important;
        transform: none !important;
    }
    
    /* Status indicator styling */
    .inquiry-status-indicator {
        font-size: 0.75rem;
        font-style: italic;
        color: #6c757d;
        margin-top: 0.25rem;
    }
    
    .inquiry-status-open {
        color: #28a745;
        font-weight: 500;
    }
    
    .inquiry-status-none {
        color: #6c757d;
    }
    
    .inquiry-status-closed {
        color: #dc3545;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main application function"""
    st.markdown("""
    <div class="main-header">
        <h1>🏦 Corporate Actions Dashboard</h1>
        <p>Real-time Corporate Actions collaborative platform using Model Context Protocol</p>
    </div>
    """, unsafe_allow_html=True)
    
    # MCP Server Status Check
    server_status = check_server_status()
    
    if server_status["status"] == "connected":
        st.success(f"✅ {server_status['message']}")
    elif server_status["status"] == "disconnected":
        st.error(f"❌ {server_status['message']}")
        st.info("💡 **To start MCP servers:** Run `python start_mcp_servers.py` in the project root directory")
        # Server startup instructions
        with st.expander("🚀 How to start MCP servers"):
            st.markdown("""
            **Before using this dashboard, you need to start the MCP servers:**
            
            1. Open a terminal in the project root directory
            2. Run: `python start_mcp_servers.py`
            3. Wait for all three servers to start successfully
            4. Refresh this page
            
            **Alternative - Start individual servers:**
            ```bash
            # Terminal 1 - Main RAG Server
            cd mcp-rag
            python -m fastmcp run main.py --port 8000
            
            # Terminal 2 - Web Search Server  
            cd mcp-websearch
            python -m fastmcp run main.py --port 8001
            
            ```
            """)
    elif server_status["status"] == "error":
        st.warning(f"⚠️ {server_status['message']}")
        st.info("💡 **Troubleshooting:** Check if servers are running with `python start_mcp_servers.py`")
        # Server startup instructions
        with st.expander("🚀 How to start MCP servers"):
            st.markdown("""
            **Before using this dashboard, you need to start the MCP servers:**
            
            1. Open a terminal in the project root directory
            2. Run: `python start_mcp_servers.py`
            3. Wait for all three servers to start successfully
            4. Refresh this page
            
            **Alternative - Start individual servers:**
            ```bash
            # Terminal 1 - Main RAG Server
            cd mcp-rag
            python -m fastmcp run main.py --port 8000
            
            # Terminal 2 - Web Search Server  
            cd mcp-websearch
            python -m fastmcp run main.py --port 8001
            
            ```
            """)
    else:
        st.warning(f"⚠️ {server_status['message']} - Using sample data")
    
      # Sidebar navigation
    with st.sidebar:
        st.header("Navigation")
        page = st.radio(
            "Select Page",
            ["Dashboard", "RAG Assistant", "Search Events", "Process Workflow", "Analytics", "Administrator"]
        )# Server Status Sidebar
        st.header("🖥️ Server Status")
        
        # Use cached status instead of checking each server individually
        cached_status = check_server_status()
        
        if cached_status["status"] == "connected":
            st.success("🟢 All servers online")
            
            # Show simplified status without additional checks
            st.write("**RAG Server:** 🟢")
            st.write("**Web Search:** 🟢") 
            
        elif cached_status["status"] == "disconnected":
            st.error("🔴 Servers offline")
            st.write("**RAG Server:** 🔴")
            st.write("**Web Search:** 🔴")
            
        elif cached_status["status"] == "error":
            st.warning("⚠️ Connection issues")
            st.write("**RAG Server:** ⚠️")
            st.write("**Web Search:** ⚠️")
            
        else:
            st.write("❌ Client not available")
            st.write("Start servers first!")
            
        # Add refresh button for manual status update
        if st.button("🔄 Refresh Status"):
            if "server_status_cache" in st.session_state:
                del st.session_state.server_status_cache
            st.rerun()
      # Route to selected page
    if page == "Dashboard":
        show_dashboard()
    elif page == "RAG Assistant":
        show_rag_assistant()
    elif page == "Search Events":
        show_search_events()
    elif page == "Process Workflow":
        show_process_workflow()
    elif page == "Analytics":
        show_analytics_page()  # Moved old dashboard content here
    elif page == "Administrator":
        show_administrator_page()  
    
# Inquiry Management Functions - Pure MCP Implementation
def get_user_inquiry_status(event_id: str, user_id: str) -> Dict[str, Any]:
    """Get user's inquiry status for a specific event"""
    if not client:
        return {"has_inquiries": False, "open_inquiries": [], "total_count": 0}
    
    try:
        result = client.get_user_inquiries(event_id, user_id)
        inquiries = result.get("inquiries", [])
        
        # Filter for open inquiries (editable status)
        open_inquiries = [inq for inq in inquiries if inq.get('status') not in ['CLOSED', 'RESOLVED']]
        
        return {
            "has_inquiries": len(inquiries) > 0,
            "open_inquiries": open_inquiries,
            "total_count": len(inquiries),
            "editable_count": len(open_inquiries)
        }
    except Exception as e:
        return {"has_inquiries": False, "open_inquiries": [], "total_count": 0, "error": str(e)}
    
def create_inquiry_mcp(event_id: str, subject: str, description: str, priority: str = "MEDIUM") -> Dict[str, Any]:
    """Create a new inquiry using MCP client"""
    if not client:
        return {"success": False, "error": "MCP client not available"}
    
    try:
        result = client.create_inquiry(
            event_id=event_id,
            user_id=st.session_state.current_user_id,
            user_name=st.session_state.current_user_name,
            organization=st.session_state.current_organization,
            subject=subject,
            description=description,
            priority=priority
        )
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_inquiries_mcp(event_id: str) -> List[Dict[str, Any]]:
    """Get inquiries for an event using MCP client"""
    if not client:
        return []
    
    try:
        result = client.get_inquiries(event_id)
        return result.get("inquiries", [])
    except Exception as e:
        st.error(f"Error fetching inquiries: {str(e)}")
        return []

def get_user_inquiries_mcp(event_id: str, user_id: str) -> List[Dict[str, Any]]:
    """Get user's inquiries for an event using MCP client"""
    if not client:
        return []
    
    try:
        result = client.get_user_inquiries(event_id, user_id)
        return result.get("inquiries", [])
    except Exception as e:
        st.error(f"Error fetching user inquiries: {str(e)}")
        return []

def update_inquiry_mcp(inquiry_id: str, **updates) -> Dict[str, Any]:
    """Update an inquiry using MCP client"""
    if not client:
        return {"success": False, "error": "MCP client not available"}
    
    try:
        result = client.update_inquiry(inquiry_id, **updates)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

def delete_inquiry_mcp(inquiry_id: str, user_id: str) -> Dict[str, Any]:
    """Delete an inquiry using MCP client"""
    if not client:
        return {"success": False, "error": "MCP client not available"}
    
    try:
        result = client.delete_inquiry(inquiry_id, user_id)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

def show_inquiry_modal_create(event_data: Dict[str, Any]):
    """Show Create Inquiry modal"""
    st.subheader(f"🆕 Create New Inquiry for {event_data.get('issuer_name', 'N/A')} ({event_data.get('security', {}).get('symbol', 'N/A')})")
    
    with st.form(f"create_inquiry_{event_data['event_id']}"):
        st.info(f"**Event:** {event_data.get('description', 'N/A')}")
        
        col1, col2 = st.columns(2)
        with col1:
            subject = st.text_input("Subject", placeholder="Brief description of your inquiry")
            priority = st.selectbox("Priority", ["LOW", "MEDIUM", "HIGH", "URGENT"], index=1)
        
        with col2:
            st.text_input("Your Name", value=st.session_state.current_user_name, disabled=True)
            st.text_input("Organization", value=st.session_state.current_organization, disabled=True)
        
        description = st.text_area("Detailed Description", height=100, 
                                 placeholder="Provide detailed information about your inquiry...")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.form_submit_button("Create Inquiry", type="primary"):
                if subject and description:
                    with st.spinner("Creating inquiry..."):
                        result = create_inquiry_mcp(
                            event_data['event_id'], subject, description, priority
                        )
                        
                        if result.get("success"):
                            st.success(f"✅ Inquiry created successfully! ID: {result.get('inquiry_id')}")
                            # Close modal and return to dashboard
                            st.session_state.selected_event_for_inquiry = None
                            if 'inquiry_modal_type' in st.session_state:
                                del st.session_state.inquiry_modal_type
                            # Add a small delay to show the success message before redirecting
                            st.balloons()  # Visual feedback
                            # Use st.rerun() to refresh and go back to dashboard
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to create inquiry: {result.get('error')}")
                else:
                    st.error("Please fill in both subject and description")
        
        with col3:
            if st.form_submit_button("Cancel"):
                st.session_state.selected_event_for_inquiry = None
                if 'inquiry_modal_type' in st.session_state:
                    del st.session_state.inquiry_modal_type
                st.rerun()

def show_inquiry_modal_edit(event_data: Dict[str, Any]):
    """Show Edit Inquiry modal for user's own inquiries"""
    st.subheader(f"✏️ Edit Your Inquiries for {event_data.get('issuer_name', 'N/A')} ({event_data.get('security', {}).get('symbol', 'N/A')})")
    
    user_inquiries = get_user_inquiries_mcp(
        event_data['event_id'], 
        st.session_state.current_user_id
    )
    
    if user_inquiries:
        st.info(f"You have {len(user_inquiries)} inquiries for this corporate action")
        
        # Select inquiry to edit
        inquiry_options = {f"{inq['subject']} (ID: {inq['inquiry_id']})": inq for inq in user_inquiries}
        selected_inquiry_key = st.selectbox("Select Inquiry to Edit", list(inquiry_options.keys()))
        
        if selected_inquiry_key:
            selected_inquiry = inquiry_options[selected_inquiry_key]
            
            # Only allow editing if status is OPEN or ACKNOWLEDGED
            if selected_inquiry.get('status') in ['OPEN', 'ACKNOWLEDGED']:
                with st.form(f"edit_inquiry_{selected_inquiry['inquiry_id']}"):
                    st.info(f"**Inquiry ID:** {selected_inquiry['inquiry_id']}")
                    st.info(f"**Current Status:** {selected_inquiry.get('status', 'N/A')}")
                    st.info(f"**Created:** {selected_inquiry.get('created_at', 'N/A')}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        new_subject = st.text_input("Subject", value=selected_inquiry.get('subject', ''))
                        new_priority = st.selectbox("Priority", 
                                                   ["LOW", "MEDIUM", "HIGH", "URGENT"],
                                                   index=["LOW", "MEDIUM", "HIGH", "URGENT"].index(selected_inquiry.get('priority', 'MEDIUM')))
                    
                    with col2:
                        st.text_input("Your Name", value=st.session_state.current_user_name, disabled=True)
                        st.text_input("Organization", value=st.session_state.current_organization, disabled=True)
                    
                    new_description = st.text_area("Description", 
                                                  value=selected_inquiry.get('description', ''),
                                                  height=100)
                    
                    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
                    with col1:
                        if st.form_submit_button("Update Inquiry", type="primary"):
                            if new_subject and new_description:
                                with st.spinner("Updating inquiry..."):
                                    result = update_inquiry_mcp(
                                        selected_inquiry['inquiry_id'],
                                        subject=new_subject,
                                        description=new_description,
                                        priority=new_priority
                                    )
                                    print(result)
                                    if result.get("success"):
                                        st.success("✅ Inquiry updated successfully!")
                                        # Close modal and return to dashboard
                                        st.session_state.selected_event_for_inquiry = None
                                        if 'inquiry_modal_type' in st.session_state:
                                            del st.session_state.inquiry_modal_type
                                        # Visual feedback
                                        st.balloons()
                                        # Return to dashboard
                                        st.rerun()
                                    else:
                                        st.error(f"❌ Failed to update inquiry: {result.get('error')}")
                            else:
                                st.error("Please fill in both subject and description")
                    
                    with col2:
                        if st.form_submit_button("Delete Inquiry", type="secondary"):
                            with st.spinner("Deleting inquiry..."):
                                result = delete_inquiry_mcp(
                                    selected_inquiry['inquiry_id'],
                                    st.session_state.current_user_id
                                )
                                
                                if result.get("success"):
                                    st.success("✅ Inquiry deleted successfully!")
                                    # Close modal and return to dashboard
                                    st.session_state.selected_event_for_inquiry = None
                                    if 'inquiry_modal_type' in st.session_state:
                                        del st.session_state.inquiry_modal_type
                                    # Visual feedback for deletion
                                    st.snow()  # Different visual feedback for deletion
                                    # Return to dashboard
                                    st.rerun()
                                else:
                                    st.error(f"❌ Failed to delete inquiry: {result.get('error')}")
                    
                    with col4:
                        if st.form_submit_button("Cancel"):
                            st.session_state.selected_event_for_inquiry = None
                            if 'inquiry_modal_type' in st.session_state:
                                del st.session_state.inquiry_modal_type
                            st.rerun()
            else:
                st.warning(f"Cannot edit inquiry with status: {selected_inquiry.get('status')}. Only OPEN and ACKNOWLEDGED inquiries can be edited.")
                
                if st.button("Close"):
                    st.session_state.selected_event_for_inquiry = None
                    if 'inquiry_modal_type' in st.session_state:
                        del st.session_state.inquiry_modal_type
                    st.rerun()
    else:
        st.info("You have no inquiries for this corporate action yet.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Create First Inquiry"):
                st.session_state.inquiry_modal_type = 'create'
                st.rerun()
        
        with col2:
            if st.button("Close"):
                st.session_state.selected_event_for_inquiry = None
                if 'inquiry_modal_type' in st.session_state:
                    del st.session_state.inquiry_modal_type
                st.rerun()

def show_inquiry_modal_view(event_data: Dict[str, Any]):
    """Show View Inquiries modal"""
    st.subheader(f"👁️ View All Inquiries for {event_data.get('issuer_name', 'N/A')} ({event_data.get('security', {}).get('symbol', 'N/A')})")
    
    inquiries = get_inquiries_mcp(event_data['event_id'])
    
    if inquiries:
        st.info(f"Found {len(inquiries)} inquiries for this corporate action")
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.selectbox("Filter by Status", 
                                       ["All"] + ["OPEN", "ACKNOWLEDGED", "IN_REVIEW", "RESPONDED", "ESCALATED", "RESOLVED", "CLOSED"])
        with col2:
            priority_filter = st.selectbox("Filter by Priority", 
                                         ["All"] + ["LOW", "MEDIUM", "HIGH", "URGENT"])
        with col3:
            user_filter = st.selectbox("Filter by User", 
                                     ["All"] + list(set([inq.get('user_name', 'Unknown') for inq in inquiries])))
        
        # Apply filters
        filtered_inquiries = inquiries
        if status_filter != "All":
            filtered_inquiries = [inq for inq in filtered_inquiries if inq.get('status') == status_filter]
        if priority_filter != "All":
            filtered_inquiries = [inq for inq in filtered_inquiries if inq.get('priority') == priority_filter]
        if user_filter != "All":
            filtered_inquiries = [inq for inq in filtered_inquiries if inq.get('user_name') == user_filter]
        
        st.markdown("---")
        
        # Display inquiries
        for inquiry in filtered_inquiries:
            with st.container():
                # Color coding based on priority and status
                priority_color = {
                    "LOW": "#28a745", 
                    "MEDIUM": "#ffc107", 
                    "HIGH": "#fd7e14", 
                    "URGENT": "#dc3545"
                }.get(inquiry.get('priority', 'MEDIUM'), "#ffc107")
                
                status_color = {
                    "OPEN": "#17a2b8",
                    "ACKNOWLEDGED": "#6c757d", 
                    "IN_REVIEW": "#007bff",
                    "RESPONDED": "#28a745",
                    "ESCALATED": "#dc3545",
                    "RESOLVED": "#20c997",
                    "CLOSED": "#6c757d"
                }.get(inquiry.get('status', 'OPEN'), "#17a2b8")
                
                st.markdown(f"""
                <div style="border-left: 4px solid {priority_color}; padding: 1rem; margin: 0.5rem 0; background: #f8f9fa; border-radius: 5px;">
                    <h4>📋 {inquiry.get('subject', 'No Subject')}</h4>
                    <p>
                        <span style="background: {priority_color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; font-weight: bold;">
                            {inquiry.get('priority', 'N/A')}
                        </span>
                        <span style="background: {status_color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; font-weight: bold; margin-left: 0.5rem;">
                            {inquiry.get('status', 'N/A')}
                        </span>
                    </p>
                    <p><strong>User:</strong> {inquiry.get('user_name', 'N/A')} ({inquiry.get('organization', 'N/A')})</p>
                    <p><strong>Created:</strong> {inquiry.get('created_at', 'N/A')} | 
                       <strong>Updated:</strong> {inquiry.get('updated_at', 'N/A')}</p>
                    <p><strong>Description:</strong> {inquiry.get('description', 'N/A')}</p>
                    {f"<p><strong>Response:</strong> {inquiry.get('response', '')}</p>" if inquiry.get('response') else ""}
                    {f"<p><strong>Resolution Notes:</strong> {inquiry.get('resolution_notes', '')}</p>" if inquiry.get('resolution_notes') else ""}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No inquiries found for this corporate action")
    
    # Close button
    if st.button("Close View", type="primary"):
        st.session_state.selected_event_for_inquiry = None
        if 'inquiry_modal_type' in st.session_state:
            del st.session_state.inquiry_modal_type
        st.rerun()

def show_rag_assistant():
    """Display RAG assistant interface with enhanced chat history and both general and subscription-based RAG"""
    st.header("🤖 RAG Assistant (MCP)")
    st.markdown("Ask questions about corporate actions using advanced AI-powered search and analysis")

    # RAG Query Mode Selection
    col1, col2 = st.columns(2)
    with col1:
        rag_mode = st.radio(
            "Query Mode:",
            ["General RAG Search", "Subscription-Based Search"],
            help="General RAG searches all corporate actions data. Subscription-based limits to your symbols."
        )
    
    with col2:
        # Display current subscriptions if available
        user_subscriptions = st.session_state.get('user_subscriptions', [])
        if user_subscriptions:
            st.info(f"📈 **Your subscriptions:** {', '.join(user_subscriptions)}")
        else:
            st.warning("⚠️ No subscriptions - only General RAG mode available")
            if rag_mode == "Subscription-Based Search":
                st.info("💡 Go to Dashboard to subscribe to symbols for subscription-based search")
    
    # Force general mode if no subscriptions
    if not user_subscriptions and rag_mode == "Subscription-Based Search":
        rag_mode = "General RAG Search"
        st.info("🔄 Switched to General RAG mode (no subscriptions found)")

    # Initialize chat history
    if "rag_chat_history" not in st.session_state:
        st.session_state.rag_chat_history = []
    
    # Initialize messages for backward compatibility
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history with styled messages
    if st.session_state.rag_chat_history:
        st.markdown("### 💬 Chat History")
        
        for i, msg in enumerate(st.session_state.rag_chat_history):
            if msg["role"] == "user":
                st.markdown(f"""
                <div class="chat-message user-message">
                    <strong>👤 You:</strong>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(msg["content"])
            else:
                st.markdown(f"""
                <div class="chat-message assistant-message">
                    <strong>🤖 RAG Assistant:</strong>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(msg["content"])
                
                # Show confidence score if available
                if msg.get("confidence"):
                    confidence = msg["confidence"]
                    if confidence > 0.8:
                        st.success(f"✅ High confidence response ({confidence:.1%})")
                    elif confidence > 0.6:
                        st.warning(f"⚠️ Medium confidence response ({confidence:.1%})")
                    else:
                        st.info(f"💡 Lower confidence response ({confidence:.1%})")
                
                # Regenerate visualization if it was shown before
                if msg.get("had_visualization") and msg.get("sources"):
                    with st.container():
                        st.caption("🔄 Regenerated Visualization")
                        fig = generate_dynamic_visualization(
                            msg["sources"], 
                            msg["content"] if msg["role"] == "user" else "visualization", 
                            msg.get("visualization_suggestions", {})
                        )
                        if fig:
                            st.plotly_chart(fig, use_container_width=True, key=f"viz_{i}_{hash(str(msg))}")
                
                # Show visualization suggestions if available
                elif msg.get("visualization_suggestions"):
                    with st.expander("📊 Visualization Suggestions"):
                        suggestions = msg["visualization_suggestions"]
                        recommended = suggestions.get("recommended_charts", [])
                        data_available = suggestions.get("data_available", [])
                        
                        if recommended:
                            st.write("**Recommended visualizations for this data:**")
                            for chart_type in recommended:
                                chart_name = chart_type.replace("_", " ").title()
                                st.write(f"• {chart_name}")
                        
                        if data_available:
                            st.write("**Available data dimensions:**")
                            for data_type in data_available:
                                data_name = data_type.replace("_", " ").title()
                                st.write(f"• {data_name}")
                
                # Show sources
                if msg.get("sources"):
                    with st.expander("📋 Sources"):
                        for source in msg["sources"]:
                            st.json(source)
        
        # Clear chat history button
        if st.button("🗑️ Clear Chat History"):
            st.session_state.rag_chat_history = []
            st.session_state.messages = []  # Clear old messages too
            st.rerun()
    
    else:
        st.info("💡 Start a conversation by asking about corporate actions below!")
          # Sample questions        st.markdown("### 💡 Sample Questions You Can Ask:")
        
        # Generate sample questions based on mode and user subscriptions
        user_symbols = st.session_state.get('user_subscriptions', [])
        
        if rag_mode == "General RAG Search":
            sample_questions = [
                "What dividend announcements are available for technology companies?",
                "Show me all recent stock splits and their ratios",
                "Find merger and acquisition events from the last quarter",
                "Create a chart showing event type distribution across all companies",
                "What are the highest dividend yields announced recently?",
                "Analyze trends in corporate action announcements"
            ]
        else:
            sample_questions = [
                f"What are the recent dividend announcements for {user_symbols[0] if user_symbols else 'my subscribed symbols'}?",
                f"Show me all stock splits for {', '.join(user_symbols[:2]) if len(user_symbols) >= 2 else 'my subscribed symbols'}", 
                "Which of my subscribed companies have the most corporate actions?",
                "Create a chart showing event types for my subscribed symbols",
                "What are the upcoming ex-dividend dates for my subscriptions?",
                f"Analyze corporate action trends for {', '.join(user_symbols) if user_symbols else 'my symbols'}"
            ]
        
        for question in sample_questions:
            if st.button(f"📝 {question}", key=f"sample_rag_{question}"):
                st.session_state.rag_chat_history.append({"role": "user", "content": question})
                st.rerun()    # Chat input
    user_input = st.chat_input("Ask about corporate actions, request analysis, or search for specific events...")
    
    if user_input:
        # Add user message to history
        st.session_state.rag_chat_history.append({"role": "user", "content": user_input})
        
        # Get RAG response with chat history
        with st.spinner("🤖 RAG Assistant thinking..."):
            try:                
                if client:
                    # Prepare enhanced chat history (last 6 messages for context)
                    chat_history_for_context = []
                    recent_messages = st.session_state.rag_chat_history[-6:] if len(st.session_state.rag_chat_history) > 6 else st.session_state.rag_chat_history
                    
                    for msg in recent_messages:
                        if msg["role"] == "user":
                            chat_history_for_context.append({
                                "role": "user",
                                "content": msg["content"]
                            })
                        elif msg["role"] == "assistant":
                            # Include sources information in assistant context if available
                            content = msg["content"]
                            if msg.get("sources"):
                                content += f"\n\n[Previous sources: {len(msg['sources'])} corporate action events]"
                            chat_history_for_context.append({
                                "role": "assistant", 
                                "content": content
                            })
                      # Choose the appropriate RAG tool based on mode
                    if rag_mode == "General RAG Search":
                        # Use general RAG query that searches all corporate actions
                        response = client.rag_query(
                            query=user_input,
                            max_results=5,
                            chat_history=chat_history_for_context
                        )
                    else:
                        # Use subscription-based RAG query
                        response = client._call_tool(
                            MCP_SERVERS["rag"],
                            "rag_query_subscribed",
                            {
                                "query": user_input,
                                "user_id": st.session_state.get('user_id', 'user_001'),
                                "subscribed_symbols": st.session_state.get('user_subscriptions', []),
                                "max_results": 5,                                "chat_history": json.dumps(chat_history_for_context) if chat_history_for_context else ""
                            }
                        )
                    
                    if isinstance(response, str):
                        rag_data = json.loads(response)
                    else:
                        rag_data = response
                    
                    # Handle errors differently based on mode
                    if "error" in rag_data:
                        error_msg = rag_data["error"]
                        suggestion = rag_data.get("suggestion", "")
                        
                        st.error(f"🚫 {error_msg}")
                        if suggestion:
                            st.info(f"💡 {suggestion}")
                        
                        # Show subscription-specific error details only for subscription mode
                        if rag_mode == "Subscription-Based Search" and "unsubscribed_symbols" in rag_data:
                            st.warning(f"❌ You asked about: {', '.join(rag_data['unsubscribed_symbols'])}")
                            st.success(f"✅ You can ask about: {', '.join(rag_data['subscribed_symbols'])}")
                        
                        # Add error to chat history
                        st.session_state.rag_chat_history.append({
                            "role": "assistant", 
                            "content": f"❌ {error_msg}\n\n💡 {suggestion}" if suggestion else f"❌ {error_msg}"
                        })
                        st.rerun()
                        return
                    
                    # Process successful response
                    answer = rag_data.get("answer", "I couldn't find relevant information.")
                    sources = rag_data.get("sources", [])
                    confidence = rag_data.get("confidence_score", 0.8)
                    data_source = rag_data.get("data_source", "unknown")
                    total_results = rag_data.get("total_results", len(sources))
                    query_intent = rag_data.get("query_intent", "information_request")
                    requires_visualization = rag_data.get("requires_visualization", False)
                    visualization_suggestions = rag_data.get("visualization_suggestions", {})
                    
                    # Add enhanced data source info to answer based on mode and data source
                    mode_info = f"[{rag_mode}]"
                    if data_source == "vector_search":
                        answer += f"\n\n📊 *{mode_info} AI Search Vector DB ({total_results} events analyzed)*"
                    elif data_source == "cosmosdb":
                        answer += f"\n\n📊 *{mode_info} CosmosDB ({total_results} events analyzed)*"
                    elif data_source == "keyword_search_fallback":
                        answer += f"\n\n📊 *{mode_info} Keyword search fallback ({total_results} events analyzed)*"
                    else:
                        answer += f"\n\n📊 *{mode_info} {data_source} ({total_results} events analyzed)*"
                      # Build assistant message with enhanced metadata
                    assistant_message = {
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                        "confidence": confidence,
                        "data_source": data_source,
                        "query_intent": query_intent,
                        "requires_visualization": requires_visualization,
                        "visualization_suggestions": visualization_suggestions,
                        "rag_mode": rag_mode
                    }
                    
                    st.session_state.rag_chat_history.append(assistant_message)
                    
                    # Also add to old messages for backward compatibility
                    st.session_state.messages.append({"role": "user", "content": user_input})
                    st.session_state.messages.append(assistant_message)
                    
                    st.rerun()
                else:
                    error_msg = "MCP client not available. Please check server connection."
                    st.error(error_msg)
                    st.session_state.rag_chat_history.append({"role": "assistant", "content": error_msg})
                    st.rerun()
                    
            except Exception as e:
                error_msg = f"Error processing query: {str(e)}"
                st.error(error_msg)
                st.session_state.rag_chat_history.append({"role": "assistant", "content": error_msg})
                st.rerun()

def show_search_events():
    """Display event search interface"""
    st.header("🔍 Search Corporate Actions (MCP)")
    
    with st.form("search_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            search_text = st.text_input("Search Text", placeholder="dividend payment")
            event_type = st.selectbox("Event Type", ["", "dividend", "stock_split", "merger", "spinoff"])
            company_name = st.text_input("Company Name", placeholder="Apple Inc.")
        
        with col2:
            status = st.selectbox("Status", ["", "announced", "confirmed", "processed", "cancelled"])
            #date_from = st.date_input("From Date", value=date.today() - timedelta(days=30))
            #date_to = st.date_input("To Date", value=date.today())
        
        limit = st.slider("Max Results", 1, 50, 10)
        submit_button = st.form_submit_button("Search")
    
    if submit_button:
        try:
            if client:
                # Build search parameters
                search_params = {
                    "search_text": search_text,
                    "event_type": event_type,
                    "symbols": company_name,
                    "status_filter": status,
                    "limit": limit
                }
                
                # Remove empty parameters
                search_params = {k: v for k, v in search_params.items() if v}
                
                response = client.search_corporate_actions(**search_params)
                if "error" not in response:
                    if isinstance(response, str):
                        search_results = json.loads(response)
                    else:
                        search_results = response
                        
                    events = search_results.get("events", [])
                    
                    if events:
                        st.success(f"🎯 Found {len(events)} events matching your criteria")
                        
                        # Normalize event data to handle different structures
                        events = normalize_event_data(events)
                        
                        # Create search results overview with metrics
                        col1, col2, col3, col4 = st.columns(4)
                        
                        # Calculate search result metrics
                        total_found = len(events)
                        confirmed_events = len([e for e in events if e.get("status") == "confirmed"])
                        announced_events = len([e for e in events if e.get("status") == "announced"])
                        pending_events = len([e for e in events if e.get("status") == "pending"])
                        
                        with col1:
                            st.metric("📋 Total Found", total_found)
                        with col2:
                            st.metric("✅ Confirmed", confirmed_events)
                        with col3:
                            st.metric("📅 Announced", announced_events)
                        with col4:
                            st.metric("⏳ Pending", pending_events)
                        
                        # Create visualizations for search results
                        if len(events) > 1:  # Only show charts if there are multiple events
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                # Status distribution for search results
                                st.subheader("📊 Search Results - Status Distribution")
                                status_counts = {}
                                for event in events:
                                    status = event.get("status", "Unknown")
                                    status_counts[status] = status_counts.get(status, 0) + 1
                                
                                if status_counts:
                                    fig_pie = px.pie(
                                        values=list(status_counts.values()),
                                        names=list(status_counts.keys()),
                                        title="Results by Status",
                                        color_discrete_map={
                                            'confirmed': '#28a745',    # Green
                                            'announced': '#ffc107',    # Yellow
                                            'pending': '#dc3545',      # Red
                                            'processed': '#17a2b8',    # Blue
                                            'cancelled': '#6c757d'     # Gray
                                        }
                                    )
                                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                                    st.plotly_chart(fig_pie, use_container_width=True)
                            
                            with col2:
                                # Event type distribution for search results
                                st.subheader("🏢 Search Results - Event Type Distribution")
                                type_counts = {}
                                for event in events:
                                    event_type = event.get("event_type", "Unknown")
                                    type_counts[event_type] = type_counts.get(event_type, 0) + 1
                                
                                if type_counts:
                                    fig_bar = px.bar(
                                        x=list(type_counts.keys()),
                                        y=list(type_counts.values()),
                                        title="Results by Event Type",
                                        color=list(type_counts.values()),
                                        color_continuous_scale="viridis"
                                    )
                                    fig_bar.update_layout(xaxis_title="Event Type", yaxis_title="Count")
                                    st.plotly_chart(fig_bar, use_container_width=True)
                        
                        # Enhanced results table with color-coded status
                        st.subheader("📋 Search Results - Detailed View")
                        df = pd.DataFrame(events)
                        
                        # Format the dataframe for display with normalized column names
                        display_columns = ["company_name", "symbol", "event_type", "status", "announcement_date"]
                        available_columns = [col for col in display_columns if col in df.columns]
                        
                        if available_columns:
                            display_df = df[available_columns].copy()
                            
                            # Add status styling function
                            def color_status(val):
                                if val == 'confirmed':
                                    return 'background-color: #d4edda; color: #155724; font-weight: bold;'
                                elif val == 'announced':
                                    return 'background-color: #fff3cd; color: #856404; font-weight: bold;'
                                elif val == 'pending':
                                    return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
                                elif val == 'processed':
                                    return 'background-color: #d1ecf1; color: #0c5460; font-weight: bold;'
                                else:
                                    return 'background-color: #e2e3e5; color: #383d41; font-weight: bold;'
                            
                            # Rename columns for better display
                            column_mapping = {
                                "company_name": "Company",
                                "symbol": "Symbol", 
                                "event_type": "Event Type",
                                "status": "Status",
                                "announcement_date": "Announced"
                            }
                            display_df = display_df.rename(columns=column_mapping)
                            
                            # Apply styling
                            styled_df = display_df.style.applymap(color_status, subset=['Status'])
                            st.dataframe(styled_df, use_container_width=True)
                        
                        # Search insights
                        st.subheader("🔍 Search Insights")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            # Most active companies in search results
                            company_counts = {}
                            for event in events:
                                company = event.get("company_name", "Unknown")
                                company_counts[company] = company_counts.get(company, 0) + 1
                            
                            if company_counts:
                                most_active = max(company_counts, key=company_counts.get)
                                st.metric("🏆 Most Active in Results", most_active, f"{company_counts[most_active]} events")
                        
                        with col2:
                            # Most common event type in search
                            if len(events) > 0:
                                type_counts = {}
                                for event in events:
                                    event_type = event.get("event_type", "Unknown")
                                    type_counts[event_type] = type_counts.get(event_type, 0) + 1
                                
                                if type_counts:
                                    most_common_type = max(type_counts, key=type_counts.get)
                                    st.metric("📈 Most Common Type", most_common_type.replace('_', ' ').title(), f"{type_counts[most_common_type]} events")
                        
                        with col3:
                            # Date range of results
                            date_range_info = "N/A"
                            if events:
                                dates = [e.get("announcement_date", "") for e in events if e.get("announcement_date")]
                                if dates:
                                    min_date = min(dates)
                                    max_date = max(dates)
                                    if min_date == max_date:
                                        date_range_info = min_date
                                    else:
                                        date_range_info = f"{min_date} to {max_date}"
                            st.metric("📅 Date Range", "Results span", date_range_info)
                        
                        # Detailed expandable view for each event
                        st.subheader("📝 Detailed Event Information")
                        for i, event in enumerate(events):
                            # Use normalized company_name field
                            company_display = event.get('company_name', 'Unknown Company')
                            status_emoji = {"confirmed": "✅", "announced": "📅", "pending": "⏳", "processed": "✅", "cancelled": "❌"}.get(event.get('status', ''), "❓")
                            
                            with st.expander(f"{status_emoji} {event.get('event_type', 'Unknown').replace('_', ' ').title()} - {company_display}"):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.write(f"**Event ID:** {event.get('event_id', 'N/A')}")
                                    st.write(f"**Symbol:** {event.get('symbol', 'N/A')}")
                                    st.write(f"**Status:** {event.get('status', 'N/A')}")
                                    st.write(f"**Announcement Date:** {event.get('announcement_date', 'N/A')}")
                                
                                with col2:
                                    st.write(f"**Description:** {event.get('description', 'N/A')}")
                                    if event.get('event_details'):
                                        st.write("**Event Details:**")
                                        st.json(event['event_details'])
                    else:
                        st.info("No events found matching your criteria")
                else:
                    st.error(f"Search failed: {response.get('error', 'Unknown error')}")
            else:
                st.warning("MCP client not available. Showing sample search results.")
                show_sample_search_results()
                
        except Exception as e:
            st.error(f"Error executing search: {str(e)}")
                
        except Exception as e:
            st.error(f"Error executing search: {str(e)}")

def show_web_research():
    """Display web research interface"""
    st.header("🌐 Web Research (MCP)")
    
    tab1, tab2, tab3 = st.tabs(["General Search", "News Search", "Financial Data"])
    
    with tab1:
        st.subheader("General Web Search")
        query = st.text_input("Search Query", placeholder="Apple dividend announcement 2025")
        
        if st.button("Search Web"):
            if query:
                try:
                    if client:
                        response = client.web_search(query, result_count=10)
                        
                        if "error" not in response:
                            if isinstance(response, str):
                                search_data = json.loads(response)
                            else:
                                search_data = response
                                
                            results = search_data.get("results", [])
                            
                            if results:
                                st.success(f"Found {len(results)} results")
                                
                                for result in results:
                                    with st.expander(result.get("title", "No Title")):
                                        st.write(f"**URL:** {result.get('url', 'N/A')}")
                                        st.write(f"**Snippet:** {result.get('snippet', 'N/A')}")
                            else:
                                st.info("No results found")
                        else:
                            st.error(f"Search failed: {response.get('error', 'Unknown error')}")
                    else:
                        st.warning("MCP client not available")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    with tab2:
        st.subheader("News Search")
        news_query = st.text_input("News Search Query", placeholder="Tesla stock split")
        
        if st.button("Search News"):
            if news_query:
                try:
                    if client:
                        response = client.news_search(news_query, result_count=10)
                        
                        if "error" not in response:
                            if isinstance(response, str):
                                news_data = json.loads(response)
                            else:
                                news_data = response
                                
                            news_results = news_data.get("results", [])
                            
                            if news_results:
                                for news in news_results:
                                    st.markdown(f"**{news.get('title', 'No Title')}**")
                                    st.write(news.get('snippet', 'No description'))
                                    st.write(f"Source: {news.get('source', 'N/A')}")
                                    st.markdown("---")
                            else:
                                st.info("No news found")
                        else:
                            st.error(f"News search failed: {response.get('error', 'Unknown error')}")
                    else:
                        st.warning("MCP client not available")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    with tab3:
        st.subheader("Financial Data Search")
        symbol = st.text_input("Stock Symbol", placeholder="AAPL")
        
        if st.button("Search Financial Data"):
            if symbol:
                try:
                    if client:
                        response = client.financial_data_search(symbol, data_type="overview")
                        
                        if "error" not in response:
                            if isinstance(response, str):
                                financial_data = json.loads(response)
                            else:
                                financial_data = response
                                
                            results = financial_data.get("results", [])
                            
                            if results:
                                for result in results:
                                    st.markdown(f"**{result.get('title', 'No Title')}**")
                                    st.write(result.get('snippet', 'No description'))
                                    st.markdown("---")
                            else:
                                st.info("No financial data found")
                        else:
                            st.error(f"Financial search failed: {response.get('error', 'Unknown error')}")
                    else:
                        st.warning("MCP client not available")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

def show_sample_dashboard():
    """Show enhanced sample dashboard when MCP servers are unavailable"""
    st.info("🔧 Showing sample data - MCP servers may be offline")
    
    events = get_sample_upcoming_events()
    
    # Display sample metrics with enhanced styling
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📈 Total Events", len(events))
    with col2:
        st.metric("✅ Active Events", 2)
    with col3:
        st.metric("📅 Upcoming", 1)
    with col4:
        st.metric("⏳ Pending", 0)
    
    # Create sample visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # Sample status distribution pie chart
        st.subheader("📊 Event Status Distribution")
        status_data = {'confirmed': 2, 'announced': 1}
        fig_pie = px.pie(
            values=list(status_data.values()),
            names=list(status_data.keys()),
            title="Events by Status",
            color_discrete_map={
                'confirmed': '#28a745',    # Green
                'announced': '#ffc107',    # Yellow
            }
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Sample event type distribution
        st.subheader("🏢 Event Type Distribution")
        type_data = {'dividend': 1, 'stock_split': 1, 'special_dividend': 1}
        fig_bar = px.bar(
            x=list(type_data.keys()),
            y=list(type_data.values()),
            title="Events by Type",
            color=list(type_data.values()),
            color_continuous_scale="viridis"
        )
        fig_bar.update_layout(xaxis_title="Event Type", yaxis_title="Count")
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # Sample events table with styling
    st.subheader("📋 Recent Corporate Actions")
    df = pd.DataFrame(events)
    
    # Add status styling function
    def color_status(val):
        if val == 'confirmed':
            return 'background-color: #d4edda; color: #155724; font-weight: bold;'
        elif val == 'announced':
            return 'background-color: #fff3cd; color: #856404; font-weight: bold;'
        else:
            return 'font-weight: bold;'
    
    # Apply styling
    styled_df = df.style.applymap(color_status, subset=['status'])
    st.dataframe(styled_df, use_container_width=True)
    
    # Sample insights
    st.subheader("🔍 Quick Insights")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🏆 Most Active Company", "Apple Inc.", "1 event")
    with col2:
        st.metric("📈 Most Common Event", "Dividend", "1 event")
    with col3:
        st.metric("📅 Recent Events (2024)", "3", "events")

def show_sample_search_results():
    """Show sample search results"""
    st.info("Sample search results:")
    events = get_sample_upcoming_events()
    
    for event in events:
        with st.expander(f"{event['event_type']} - {event['company_name']}"):
            st.write(f"**Event ID:** {event['event_id']}")
            st.write(f"**Status:** {event['status']}")
            st.write(f"**Description:** {event['description']}")

def normalize_event_data(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize event data to handle different data structures between AI Search and sample data.
    AI Search uses 'issuer_name', sample data uses 'company_name'.
    """
    normalized_events = []
    
    for event in events:
        # Create a copy of the event
        normalized_event = event.copy()
        
        # Normalize company name field
        if 'issuer_name' in event and 'company_name' not in event:
            normalized_event['company_name'] = event['issuer_name']
        elif 'company_name' not in event and 'issuer_name' not in event:
            normalized_event['company_name'] = 'Unknown Company'
            
        # Normalize symbol field (extract from security object if needed)
        if 'symbol' not in event and 'security' in event and isinstance(event['security'], dict):
            normalized_event['symbol'] = event['security'].get('symbol', 'N/A')
        elif 'symbol' not in event:
            normalized_event['symbol'] = 'N/A'
            
        # Ensure all required fields are present
        for field in ['event_type', 'status', 'announcement_date']:
            if field not in normalized_event:
                normalized_event[field] = 'N/A'
                
        normalized_events.append(normalized_event)
    
    return normalized_events

def generate_dynamic_visualization(sources: List[Dict[str, Any]], query: str, viz_suggestions: Dict[str, Any]) -> Optional[object]:
    """
    Dynamically generate visualizations based on corporate actions data and user query.
    
    Args:
        sources: List of corporate action events/data
        query: User's original query 
        viz_suggestions: Suggested visualization types
        
    Returns:
        Plotly figure object or None if generation fails
    """
    try:
        if not sources:
            return None
            
        # Normalize the data to handle different field structures
        normalized_data = normalize_event_data(sources)
        df = pd.DataFrame(normalized_data)
        
        if df.empty:
            return None
            
        query_lower = query.lower()
        recommended_charts = viz_suggestions.get("recommended_charts", [])
        
        # Determine the best visualization based on query and data
        if any(word in query_lower for word in ["status", "distribution", "breakdown"]):
            # Status distribution pie chart
            if "status" in df.columns:
                status_counts = df['status'].value_counts()
                fig = px.pie(
                    values=status_counts.values,
                    names=status_counts.index,
                    title=f"Corporate Action Status Distribution ({len(df)} events)",
                    color_discrete_map={
                        'confirmed': '#28a745',
                        'announced': '#ffc107', 
                        'pending': '#dc3545',
                        'processed': '#17a2b8',
                        'cancelled': '#6c757d'
                    }
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                return fig
                
        elif any(word in query_lower for word in ["type", "types", "event type", "category"]):
            # Event type bar chart
            if "event_type" in df.columns:
                type_counts = df['event_type'].value_counts()
                fig = px.bar(
                    x=type_counts.index,
                    y=type_counts.values,
                    title=f"Event Types Distribution ({len(df)} events)",
                    labels={'x': 'Event Type', 'y': 'Count'},
                    color=type_counts.values,
                    color_continuous_scale="viridis"
                )
                fig.update_layout(xaxis_title="Event Type", yaxis_title="Count")
                return fig
                
        elif any(word in query_lower for word in ["company", "companies", "issuer", "most active"]):
            # Company activity chart
            if "company_name" in df.columns:
                company_counts = df['company_name'].value_counts().head(10)
                fig = px.bar(
                    x=company_counts.values,
                    y=company_counts.index,
                    orientation='h',
                    title=f"Most Active Companies ({len(df)} total events)",
                    labels={'x': 'Number of Events', 'y': 'Company'},
                    color=company_counts.values,
                    color_continuous_scale="blues"
                )
                return fig
                
        elif any(word in query_lower for word in ["timeline", "over time", "trend", "date", "when"]):
            # Timeline visualization
            if "announcement_date" in df.columns:
                df['announcement_date'] = pd.to_datetime(df['announcement_date'], errors='coerce')
                df_with_dates = df.dropna(subset=['announcement_date'])
                
                if not df_with_dates.empty:
                    # Create monthly aggregation
                    df_with_dates['month_year'] = df_with_dates['announcement_date'].dt.to_period('M')
                    monthly_counts = df_with_dates.groupby('month_year').size()
                    
                    fig = px.line(
                        x=monthly_counts.index.astype(str),
                        y=monthly_counts.values,
                        title=f"Corporate Actions Timeline ({len(df_with_dates)} events)",
                        labels={'x': 'Month', 'y': 'Number of Events'},
                        markers=True
                    )
                    fig.update_layout(xaxis_title="Month", yaxis_title="Number of Events")
                    return fig
                    
        elif any(word in query_lower for word in ["amount", "value", "dividend"]):
            # Value-based visualization for dividends
            dividend_events = df[df['event_type'] == 'dividend'] if 'event_type' in df.columns else df
            
            if not dividend_events.empty and 'event_details' in dividend_events.columns:
                amounts = []
                companies = []
                
                for _, row in dividend_events.iterrows():
                    details = row.get('event_details', {})
                    if isinstance(details, str):
                        try:
                            details = json.loads(details)
                        except:
                            details = {}
                    
                    amount = details.get('dividend_amount', 0)
                    if amount and amount > 0:
                        amounts.append(amount)
                        companies.append(row.get('company_name', 'Unknown'))
                
                if amounts:
                    fig = px.bar(
                        x=companies,
                        y=amounts,
                        title=f"Dividend Amounts ({len(amounts)} dividend events)",
                        labels={'x': 'Company', 'y': 'Dividend Amount ($)'},
                        color=amounts,
                        color_continuous_scale="greens"
                    )
                    fig.update_layout(xaxis_title="Company", yaxis_title="Dividend Amount ($)")
                    return fig
        
        # Default: Create a summary dashboard with multiple small charts
        return create_summary_visualization(df)
        
    except Exception as e:
        st.error(f"Error generating visualization: {str(e)}")
        return None

def create_summary_visualization(df: pd.DataFrame) -> Optional[object]:
    """Create a summary visualization with multiple subplots"""
    try:
        from plotly.subplots import make_subplots
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Status Distribution', 'Event Types', 'Companies (Top 5)', 'Timeline'),
            specs=[[{"type": "pie"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "scatter"}]]
        )
        
        # Status distribution (pie chart)
        if "status" in df.columns:
            status_counts = df['status'].value_counts()
            fig.add_trace(
                go.Pie(labels=status_counts.index, values=status_counts.values, name="Status"),
                row=1, col=1
            )
        
        # Event types (bar chart)
        if "event_type" in df.columns:
            type_counts = df['event_type'].value_counts()
            fig.add_trace(
                go.Bar(x=type_counts.index, y=type_counts.values, name="Types"),
                row=1, col=2
            )
        
        # Top companies (horizontal bar)
        if "company_name" in df.columns:
            company_counts = df['company_name'].value_counts().head(5)
            fig.add_trace(
                go.Bar(x=company_counts.values, y=company_counts.index, 
                      orientation='h', name="Companies"),
                row=2, col=1
            )
        
        # Timeline
        if "announcement_date" in df.columns:
            df['announcement_date'] = pd.to_datetime(df['announcement_date'], errors='coerce')
            df_with_dates = df.dropna(subset=['announcement_date'])
            
            if not df_with_dates.empty:
                df_with_dates['month_year'] = df_with_dates['announcement_date'].dt.to_period('M')
                monthly_counts = df_with_dates.groupby('month_year').size()
                
                fig.add_trace(
                    go.Scatter(x=monthly_counts.index.astype(str), y=monthly_counts.values,
                              mode='lines+markers', name="Timeline"),
                    row=2, col=2
                )
        
        fig.update_layout(
            height=600,
            title_text=f"Corporate Actions Summary Dashboard ({len(df)} events)",
            showlegend=False
        )
        
        return fig
        
    except Exception as e:
        st.error(f"Error creating summary visualization: {str(e)}")
        return None

def execute_dynamic_code(code: str, data: Dict[str, Any]) -> Any:
    """
    Safely execute Python code for dynamic visualization generation.
    
    Args:
        code: Python code to execute
        data: Data context to pass to the code
        
    Returns:
        Result of code execution or None if failed
    """
    try:
        # Create a safe execution environment
        safe_globals = {
            '__builtins__': {
                'len': len, 'max': max, 'min': min, 'sum': sum,
                'dict': dict, 'list': list, 'tuple': tuple,
                'str': str, 'int': int, 'float': float,
                'print': print, 'range': range, 'enumerate': enumerate
            },
            'pd': pd,
            'px': px,
            'go': go,
            'json': json,
            'data': data
        }
        
        # Capture stdout for any print statements
        old_stdout = sys.stdout
        sys.stdout = captured_output = io.StringIO()
        
        try:
            # Execute the code
            exec(code, safe_globals)
            
            # Get the result (look for 'result' variable or return captured output)
            result = safe_globals.get('result', captured_output.getvalue())
            return result
            
        finally:
            sys.stdout = old_stdout
            
    except Exception as e:        return f"Code execution error: {str(e)}"

def show_dashboard():
    """Display new dashboard focused on upcoming actions and subscriptions"""
    st.header("📊 Corporate Actions Dashboard")
    
    # Initialize session state for user subscriptions if not exists
    if "user_subscriptions" not in st.session_state:
        st.session_state.user_subscriptions = []
    if "user_role" not in st.session_state:
        st.session_state.user_role = "CONSUMER"
    if "user_id" not in st.session_state:
        st.session_state.user_id = "user_001"
    if "user_name" not in st.session_state:
        st.session_state.user_name = "Demo User"
    if "subscriptions_loaded" not in st.session_state:
        st.session_state.subscriptions_loaded = False
    
    # Handle inquiry modal display first
    if st.session_state.selected_event_for_inquiry:
        event_data = st.session_state.selected_event_for_inquiry
        modal_type = st.session_state.get('inquiry_modal_type', 'create')
        
        if modal_type == 'create':
            show_inquiry_modal_create(event_data)
            return
        elif modal_type == 'view':
            show_inquiry_modal_view(event_data)
            return
        elif modal_type == 'edit':
            show_inquiry_modal_edit(event_data)
            return

    # Load subscriptions from database on first load
    if not st.session_state.subscriptions_loaded and client:
        try:
            result = client._call_tool(
                MCP_SERVERS["rag"], 
                "get_subscription_tool",
                {"user_id": st.session_state.user_id}
            )
            
            if isinstance(result, str):
                result = json.loads(result)
            
            if isinstance(result, dict) and result.get("subscription"):
                subscription = result["subscription"]
                if subscription and subscription.get("symbols"):
                    st.session_state.user_subscriptions = subscription["symbols"]
                    st.info(f"📊 Loaded {len(st.session_state.user_subscriptions)} subscriptions from database")
            
            st.session_state.subscriptions_loaded = True
        except Exception as e:
            st.warning(f"⚠️ Could not load subscriptions from database: {str(e)}")
            st.session_state.subscriptions_loaded = True
    
    # User role selector
    col1, col2 = st.columns([3, 1])
    with col2:
        st.session_state.user_role = st.selectbox(
            "👤 User Role", 
            ["CONSUMER", "ADMINISTRATOR"], 
            index=0 if st.session_state.user_role == "CONSUMER" else 1
        )
    
    # with col1:
    #     st.markdown("### 🚨 Welcome to the Enhanced Corporate Actions Process Workflow")
    
    # Subscription Management Section
    st.markdown("---")
    st.subheader("📈 My Subscriptions")
      # Subscription input
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        new_symbols = st.text_input(
            "Add Symbols to Subscribe", 
            placeholder="AAPL,MSFT,GOOGL"
        )
    with col2:
        if st.button("➕ Subscribe"):
            if new_symbols:
                symbols = [s.strip().upper() for s in new_symbols.split(",")]
                # Update session state
                for symbol in symbols:
                    if symbol not in st.session_state.user_subscriptions:
                        st.session_state.user_subscriptions.append(symbol)
                
                # Persist to database via MCP tool
                if client:
                    try:
                        result = client._call_tool(
                            MCP_SERVERS["rag"], 
                            "save_subscription_tool",
                            {
                                "user_id": st.session_state.user_id,
                                "user_name": st.session_state.user_name,
                                "organization": "Streamlit User",
                                "symbols": ",".join(st.session_state.user_subscriptions),
                                "event_types": "DIVIDEND,STOCK_SPLIT,MERGER,SPIN_OFF"
                            }
                        )
                        
                        if isinstance(result, dict) and result.get("success", False):
                            st.success(f"✅ Subscribed to: {', '.join(symbols)} (Saved to database)")
                        else:
                            st.warning(f"✅ Subscribed to: {', '.join(symbols)} (Session only - database unavailable)")
                    except Exception as e:
                        st.warning(f"✅ Subscribed to: {', '.join(symbols)} (Session only - {str(e)})")
                else:
                    st.success(f"✅ Subscribed to: {', '.join(symbols)} (Session only)")
                st.rerun()
    
    # Display current subscriptions
    if st.session_state.user_subscriptions:
        st.write("**Current Subscriptions:**")
        subscription_cols = st.columns(min(len(st.session_state.user_subscriptions), 5))
        for i, symbol in enumerate(st.session_state.user_subscriptions):
            with subscription_cols[i % 5]:
                if st.button(f"❌ {symbol}", key=f"unsub_{symbol}"):
                    st.session_state.user_subscriptions.remove(symbol)
                    
                    # Persist to database via MCP tool
                    if client:
                        try:
                            result = client._call_tool(
                                MCP_SERVERS["rag"], 
                                "save_subscription_tool",
                                {
                                    "user_id": st.session_state.user_id,
                                    "user_name": st.session_state.user_name,
                                    "organization": "Streamlit User",
                                    "symbols": ",".join(st.session_state.user_subscriptions),
                                    "event_types": "DIVIDEND,STOCK_SPLIT,MERGER,SPIN_OFF"
                                }
                            )
                            
                            if isinstance(result, dict) and result.get("success", False):
                                st.success(f"🗑️ Unsubscribed from {symbol} (Updated database)")
                            else:
                                st.warning(f"🗑️ Unsubscribed from {symbol} (Session only)")
                        except Exception as e:
                            st.warning(f"🗑️ Unsubscribed from {symbol} (Session only - {str(e)})")
                    else:
                        st.success(f"🗑️ Unsubscribed from {symbol} (Session only)")
                    st.rerun()
    else:
        st.info("📝 No subscriptions yet. Add some symbols above to get started!")
    
    st.markdown("---")
    
    # Upcoming Actions Section    st.subheader("🗓️ Upcoming Corporate Actions (Next 7 Days)")
    
    # Define today outside try block to avoid scope issues
    today = datetime.now().date()
    
    try:
        # Fetch upcoming events using MCP tool
        filtered_events = []
        if client and st.session_state.user_subscriptions:
            try:
                # Use the get_upcoming_events_tool from MCP server
                result = client._call_tool(
                    MCP_SERVERS["rag"], 
                    "get_upcoming_events_tool",
                    {"user_id": st.session_state.user_id, "days_ahead": 7}
                )
                
                #print(f"🔍 MCP Tool Result: {result}")
                if isinstance(result, str):
                    result = json.loads(result)
                    mcp_events = result.get("upcoming_events", [])
                elif isinstance(result, dict) and result.get("upcoming_events"):
                    mcp_events = result["upcoming_events"]
                elif result.get("error"):
                    st.warning(f"⚠️ Error from MCP server: {result['error']}")
                else:
                    st.info("📊 No upcoming events found for your subscriptions")

                # Convert MCP events to the format expected by display logic
                for event in mcp_events:
                    # Extract event date for sorting
                    event_date = None
                    for date_field in ['ex_date', 'effective_date', 'record_date', 'payable_date']:
                        if event.get(date_field):
                            try:
                                if isinstance(event[date_field], str):
                                    event_date = datetime.strptime(event[date_field], '%Y-%m-%dT%H:%M:%SZ').date()
                                else:
                                    event_date = event[date_field]
                                break
                            except:
                                continue
                    
                    if event_date:
                        event['event_date'] = event_date
                        filtered_events.append(event)
                    
            except Exception as e:
                st.error(f"⚠️ Could not fetch upcoming events from MCP server: {str(e)}")
                  # If no MCP data, use sample data as fallback

        #print(f"🔍 Filtered Events: {filtered_events}")
        if not filtered_events:
            st.info("📊 Using sample data.")
            upcoming_events = get_sample_upcoming_events(st.session_state.user_subscriptions)
            upcoming_events = normalize_event_data(upcoming_events)
            
            # Filter for next 7 days and subscribed symbols (existing logic)
            week_from_now = today + timedelta(days=7)
            
            for event in upcoming_events:
                # Check if event is for subscribed symbols
                symbol = event.get('symbol', event.get('company_name', 'Unknown')).replace(' Corporation', '').replace(' Inc.', '').upper()
                
                # Extract symbol from company name if needed
                if symbol in ['UNKNOWN', 'APPLE', 'MICROSOFT', 'ALPHABET', 'TESLA', 'AMAZON']:
                    symbol_map = {
                        'APPLE': 'AAPL',
                        'MICROSOFT': 'MSFT', 
                        'ALPHABET': 'GOOGL',
                        'TESLA': 'TSLA',
                        'AMAZON': 'AMZN'
                    }
                    symbol = symbol_map.get(symbol, symbol)
                
                if not st.session_state.user_subscriptions or symbol in st.session_state.user_subscriptions:
                    # Check if event is upcoming
                    event_date = None
                    for date_field in ['effective_date', 'ex_date', 'record_date', 'payable_date']:
                        if event.get(date_field):
                            try:
                                if isinstance(event[date_field], str):
                                    event_date = datetime.strptime(event[date_field], '%Y-%m-%d').date()
                                else:
                                    event_date = event[date_field]
                                break
                            except:
                                continue
                    
                    if event_date and today <= event_date <= week_from_now:
                        event['symbol'] = symbol
                        event['event_date'] = event_date
                        filtered_events.append(event)

        # Sort by date
        filtered_events.sort(key=lambda x: x.get('event_date', today))
        
        if filtered_events:
            # Display metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📊 Total Upcoming", len(filtered_events))
            with col2:
                dividend_count = len([e for e in filtered_events if 'dividend' in e.get('event_type', '').lower()])
                st.metric("💰 Dividends", dividend_count)
            with col3:
                # Count inquiries from MCP response or sample data
                total_inquiries = sum(len(event.get('inquiries', [])) for event in filtered_events)
                # if total_inquiries == 0:
                #     # Fallback to sample inquiries count
                #     open_inquiries = get_sample_inquiries(filtered_events)
                #     total_inquiries = len(open_inquiries)
                st.metric("❓ Open Inquiries", total_inquiries)
            with col4:
                # Count urgent inquiries from MCP response or sample data  
                urgent_count = 0
                for event in filtered_events:
                    event_inquiries = event.get('inquiries', [])
                    # if not event_inquiries:
                    #     # Fallback to sample inquiries
                    #     event_inquiries = [inq for inq in get_sample_inquiries([event]) 
                    #                      if inq.get('event_id') == event.get('event_id')]
                    urgent_count += len([i for i in event_inquiries if i.get('priority') == 'HIGH'])
                st.metric("🚨 Urgent Issues", urgent_count)
            
            # Display events with inquiry status
            for i, event in enumerate(filtered_events[:20]):  # Show top 20
                with st.expander(
                    f"🎯 **{event.get('symbol', 'Unknown')}** - {event.get('event_type', 'Unknown').replace('_', ' ').title()} "
                    f"({event.get('event_date', 'Unknown')})", 
                    expanded=i < 3
                ):
                    # Event details
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**Company:** {event.get('issuer_name', event.get('company_name', 'Unknown'))}")
                        st.write(f"**Type:** {event.get('event_type', 'Unknown').replace('_', ' ').title()}")
                        st.write(f"**Status:** {event.get('status', 'Unknown').title()}")
                        st.write(f"**Description:** {event.get('description', 'No description available')}")
                    
                    with col2:
                        # Check for existing inquiries from MCP response or sample data
                        event_inquiries = event.get('inquiries', [])
                        if event_inquiries:
                            st.warning(f"⚠️ {len(event_inquiries)} Open Inquiry(ies)")
                            for inquiry in event_inquiries:
                                st.write(f"**{inquiry.get('subject', 'No subject')}**")
                                st.write(f"Status: {inquiry.get('status', 'Unknown')}")
                                st.write(f"Priority: {inquiry.get('priority', 'Unknown')}")
                        else:
                            st.success("✅ No open inquiries")
                        
                        # # Button to create new inquiry
                        # if st.button(f"❓ Create Inquiry", key=f"inquiry_{event.get('event_id', i)}"):
                        #     st.session_state.create_inquiry_for = event
                        #     st.rerun()
                        # Inquiry management buttons
                        # Inquiry management buttons with smart enable/disable logic
                        st.markdown("**🔧 Inquiry Actions**")
                        
                        # Get user's inquiry status for this event
                        user_status = get_user_inquiry_status(
                            event.get('event_id', ''), 
                            st.session_state.current_user_id
                        )
                        
                        has_inquiries = user_status.get("has_inquiries", False)
                        open_inquiries_count = user_status.get("editable_count", 0)
                        total_inquiries_count = user_status.get("total_count", 0)
                        
                        # Create three columns for the buttons
                        btn_col1, btn_col2, btn_col3 = st.columns(3)
                        
                        with btn_col1:
                            # NEW button - disabled if user has open inquiries
                            create_disabled = has_inquiries and open_inquiries_count > 0
                            create_help = "You already have open inquiries for this event" if create_disabled else "Create new inquiry"
                            
                            if st.button("🆕", 
                                    key=f"create_{event.get('event_id', i)}", 
                                    help=create_help, 
                                    use_container_width=True,
                                    disabled=create_disabled):
                                st.session_state.selected_event_for_inquiry = event
                                st.session_state.inquiry_modal_type = 'create'
                                st.rerun()
                        
                        with btn_col2:
                            # VIEW button - always enabled
                            if st.button("👁️", key=f"view_{event.get('event_id', i)}", 
                                    help="View all inquiries", use_container_width=True):
                                st.session_state.selected_event_for_inquiry = event
                                st.session_state.inquiry_modal_type = 'view'
                                st.rerun()
                        
                        with btn_col3:
                            # EDIT button - disabled if user has no open inquiries
                            edit_disabled = not has_inquiries or open_inquiries_count == 0
                            edit_help = "No editable inquiries found" if edit_disabled else f"Edit your {open_inquiries_count} open inquiries"

                            if st.button("✏️", key=f"edit_{event.get('event_id', i)}", 
                                    help=edit_help, 
                                    use_container_width=True,
                                    disabled=edit_disabled):
                                st.session_state.selected_event_for_inquiry = event
                                st.session_state.inquiry_modal_type = 'edit'
                                st.rerun()
                        
                        # Show inquiry status information
                        if has_inquiries:
                            if open_inquiries_count > 0:
                                st.markdown(f"<small>📝 {open_inquiries_count} open, {total_inquiries_count} total</small>", 
                                        unsafe_allow_html=True)
                            else:
                                st.markdown(f"<small>📋 {total_inquiries_count} closed inquiries</small>", 
                                        unsafe_allow_html=True)
                        else:
                            st.markdown("<small>📭 No inquiries yet</small>", unsafe_allow_html=True)
                        
                        # # Show inquiry count if available
                        # if client:
                        #     try:
                        #         inquiries_result = client.get_inquiries(event.get('event_id', ''))
                        #         inquiry_count = len(inquiries_result.get("inquiries", []))
                        #         if inquiry_count > 0:
                        #             st.markdown(f"<small>📋 {inquiry_count} inquiries</small>", unsafe_allow_html=True)
                        #     except:
                        #         pass
                    
                    st.markdown("---")

        else:
            st.info("📭 No upcoming corporate actions found for your subscribed symbols in the next 7 days.")
            
            # Suggestion to add subscriptions
            if not st.session_state.user_subscriptions:
                st.warning("💡 Add some symbol subscriptions above to see relevant corporate actions!")
    
    except Exception as e:
        st.error(f"❌ Error loading upcoming actions: {str(e)}")
        st.info("📊 Using sample data for demonstration")

def get_sample_upcoming_events(subscribed_symbols=None):
    """Get sample upcoming events for the next week"""
    from datetime import timedelta
    import random
    
    # Base events happening in the next 7 days
    today = datetime.now()
    sample_events = []
    
    companies = [
        {"symbol": "AAPL", "company_name": "Apple Inc."},
        {"symbol": "MSFT", "company_name": "Microsoft Corporation"},
        {"symbol": "GOOGL", "company_name": "Alphabet Inc."},
        {"symbol": "TSLA", "company_name": "Tesla Inc."},
        {"symbol": "AMZN", "company_name": "Amazon.com Inc."},
        {"symbol": "META", "company_name": "Meta Platforms Inc."},
        {"symbol": "NVDA", "company_name": "NVIDIA Corporation"},
        {"symbol": "BRK.A", "company_name": "Berkshire Hathaway Inc."},
        {"symbol": "JPM", "company_name": "JPMorgan Chase & Co."},
        {"symbol": "JNJ", "company_name": "Johnson & Johnson"}
    ]
    
    event_types = ["dividend", "stock_split", "special_dividend", "rights_offering"]
    statuses = ["announced", "confirmed", "pending"]
    
    for i, company in enumerate(companies):
        # Create 1-2 events per company for upcoming week
        num_events = random.randint(1, 2)
        for j in range(num_events):
            event_date = today + timedelta(days=random.randint(1, 7))
            event_type = random.choice(event_types)
            
            event = {
                "event_id": f"{company['symbol']}_EVT_{event_date.strftime('%Y%m%d')}_{j+1}",
                "symbol": company["symbol"],
                "company_name": company["company_name"],
                "event_type": event_type,
                "status": random.choice(statuses),
                "announcement_date": (today - timedelta(days=random.randint(1, 5))).strftime('%Y-%m-%d'),                "event_date": event_date.strftime('%Y-%m-%d'),
                "record_date": (event_date - timedelta(days=2)).strftime('%Y-%m-%d'),
                "description": f"{event_type.replace('_', ' ').title()} for {company['company_name']}",
                "details": {
                    "amount": f"${random.uniform(0.5, 3.0):.2f}" if "dividend" in event_type else None,
                    "ratio": f"{random.randint(2, 5)}:1" if "split" in event_type else None
                }
            }
            sample_events.append(event)
    
    # Filter by subscribed symbols if provided
    if subscribed_symbols:
        sample_events = [e for e in sample_events if e.get('symbol') in subscribed_symbols]
    
    # Sort by event date
    sample_events.sort(key=lambda x: x.get('event_date', today.strftime('%Y-%m-%d')))
    
    return sample_events

def get_sample_inquiries(events):
    """Generate sample inquiries for events"""
    inquiries = []
    
    for event in events:
        # 30% chance of having an inquiry
        import random
        if random.random() < 0.3:
            inquiry_id = f"INQ_{event.get('event_id', 'UNKNOWN')}"
            inquiries.append({
                "inquiry_id": inquiry_id,
                "event_id": event.get('event_id'),
                "user_id": "user_001",
                "user_name": "Demo User",
                "subject": f"Question about {event.get('event_type', '').replace('_', ' ')} timing",
                "description": f"Need clarification on the {event.get('event_type')} process and impact on my holdings.",
                "priority": random.choice(["LOW", "MEDIUM", "HIGH"]),
                "status": random.choice(["OPEN", "ACKNOWLEDGED", "IN_REVIEW"]),
                "created_at": datetime.now(),
                "assigned_to": "admin_001" if random.random() < 0.5 else None
            })
    
    return inquiries

def show_process_workflow():
    """Display the inquiry process workflow interface"""
    st.header("🔄 Process Workflow - Inquiry Management")
    
    # Initialize session state for inquiries
    # if "inquiries" not in st.session_state:
    #     st.session_state.inquiries = get_sample_inquiries(get_sample_upcoming_events())
    if "inquiries_loaded" not in st.session_state:
        st.session_state.inquiries_loaded = False
    
    # Load inquiries from database on first load for subscribed events
    if not st.session_state.inquiries_loaded and client and st.session_state.user_subscriptions:
        try:
            # Get upcoming events for user's subscriptions to fetch their inquiries
            result = client._call_tool(
                MCP_SERVERS["rag"], 
                "get_upcoming_events_tool",
                {"user_id": st.session_state.user_id, "days_ahead": 30}
            )
            
            if isinstance(result, str):
                result = json.loads(result)
                mcp_events = result.get("upcoming_events", [])
            elif isinstance(result, dict) and result.get("upcoming_events"):
                mcp_events = result["upcoming_events"]
            
            database_inquiries = []
            for event in mcp_events:
                event_inquiries = event.get("inquiries", [])
                database_inquiries.extend(event_inquiries)
            
            if database_inquiries:
                st.session_state.inquiries = database_inquiries
                st.info(f"📊 Loaded {len(database_inquiries)} inquiries from database")
                
            st.session_state.inquiries_loaded = True
        except Exception as e:
            st.warning(f"⚠️ Could not load inquiries from database: {str(e)}")
            st.session_state.inquiries_loaded = True
    
    # Check if we need to create a new inquiry
    if "create_inquiry_for" in st.session_state:
        event = st.session_state.create_inquiry_for
        st.markdown("### 📝 Create New Inquiry")
        
        with st.form("new_inquiry_form"):
            col1, col2 = st.columns(2)
            with col1:
                subject = st.text_input("Subject", value=f"Question about {event.get('event_type', '').replace('_', ' ')}")
                priority = st.selectbox("Priority", ["LOW", "MEDIUM", "HIGH", "URGENT"])
            with col2:
                user_organization = st.text_input("Organization", value="Demo Corp")
                category = st.selectbox("Category", ["GENERAL", "TIMING", "IMPACT", "PROCESS", "DOCUMENTATION"])
            
            description = st.text_area(
                "Description", 
                value=f"I have questions regarding the {event.get('event_type', '').replace('_', ' ')} for {event.get('symbol')}. Please provide clarification."
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("✅ Submit Inquiry"):
                    new_inquiry = {
                        "inquiry_id": f"INQ_{len(st.session_state.inquiries) + 1:03d}",
                        "event_id": event.get('event_id'),
                        "user_id": st.session_state.user_id,
                        "user_name": st.session_state.user_name,
                        "subject": subject,
                        "description": description,
                        "priority": priority,
                        "status": "OPEN",
                        "created_at": datetime.now(),
                        "organization": user_organization,
                        "category": category
                    }
                    
                    # Try to save via MCP tool
                    if client:
                        try:
                            result = client._call_tool(
                                MCP_SERVERS["rag"], 
                                "create_inquiry_tool",
                                {
                                    "event_id": event.get('event_id'),
                                    "user_id": st.session_state.user_id,
                                    "user_name": st.session_state.user_name,
                                    "organization": user_organization,
                                    "subject": subject,
                                    "description": description,
                                    "priority": priority
                                }
                            )
                            
                            if isinstance(result, str):
                                result = json.loads(result)
                            
                            if isinstance(result, dict) and result.get("success", False):
                                st.success("✅ Inquiry created and saved to database!")
                                new_inquiry["inquiry_id"] = result.get("inquiry_id", new_inquiry["inquiry_id"])
                            else:
                                st.warning("✅ Inquiry created (session only - database unavailable)")
                        except Exception as e:
                            st.warning(f"✅ Inquiry created (session only - {str(e)})")
                    else:
                        st.warning("✅ Inquiry created (session only)")
                    
                    # Add to session state
                    st.session_state.inquiries.append(new_inquiry)
                    del st.session_state.create_inquiry_for
                    st.rerun()
            
            with col2:
                if st.form_submit_button("❌ Cancel"):
                    del st.session_state.create_inquiry_for
                    st.rerun()
    
    # Display existing inquiries
    st.markdown("### 📋 Current Inquiries")
    
    # Filter and search
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox("Filter by Status", ["ALL", "OPEN", "ACKNOWLEDGED", "IN_REVIEW", "RESPONDED", "RESOLVED"])
    with col2:
        priority_filter = st.selectbox("Filter by Priority", ["ALL", "LOW", "MEDIUM", "HIGH", "URGENT"])
    with col3:
        search_term = st.text_input("Search", placeholder="Search inquiries...")
    
    # Filter inquiries
    filtered_inquiries = st.session_state.inquiries
    
    if status_filter != "ALL":
        filtered_inquiries = [i for i in filtered_inquiries if i.get('status') == status_filter]
    if priority_filter != "ALL":
        filtered_inquiries = [i for i in filtered_inquiries if i.get('priority') == priority_filter]
    if search_term:
        filtered_inquiries = [i for i in filtered_inquiries 
                            if search_term.lower() in i.get('subject', '').lower() 
                            or search_term.lower() in i.get('description', '').lower()]
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📊 Total Inquiries", len(filtered_inquiries))
    with col2:
        open_count = len([i for i in filtered_inquiries if i.get('status') in ['OPEN', 'ACKNOWLEDGED']])
        st.metric("🔓 Open", open_count)
    with col3:
        urgent_count = len([i for i in filtered_inquiries if i.get('priority') == 'URGENT'])
        st.metric("🚨 Urgent", urgent_count)
    with col4:
        resolved_count = len([i for i in filtered_inquiries if i.get('status') == 'RESOLVED'])
        st.metric("✅ Resolved", resolved_count)
    
    # Display inquiries
    for inquiry in filtered_inquiries:
        with st.expander(
            f"🎫 **{inquiry.get('inquiry_id')}** - {inquiry.get('subject')} "
            f"[{inquiry.get('priority')} | {inquiry.get('status')}]",
            expanded=True
        ):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Description:** {inquiry.get('description')}")
                st.write(f"**User:** {inquiry.get('user_name')} ({inquiry.get('organization', 'Unknown')})")
                st.write(f"**Created:** {inquiry.get('created_at', datetime.now())}")
                
                # Response form
                response_key = f"response_{inquiry.get('inquiry_id')}"
                response = st.text_area(
                    "Administrator Response", 
                    value=inquiry.get('response', ''),
                    key=response_key
                )
            
            with col2:
                # Status update
                new_status = st.selectbox(
                    "Update Status",
                    ["OPEN", "ACKNOWLEDGED", "IN_REVIEW", "RESPONDED", "ESCALATED", "RESOLVED", "CLOSED"],
                    index=["OPEN", "ACKNOWLEDGED", "IN_REVIEW", "RESPONDED", "ESCALATED", "RESOLVED", "CLOSED"].index(inquiry.get('status', 'OPEN')),
                    key=f"status_{inquiry.get('inquiry_id')}"
                )
                
                # Assignment
                assigned_to = st.selectbox(
                    "Assign To",
                    ["admin_001", "admin_002", "admin_003", "None"],
                    index=0 if inquiry.get('assigned_to') else 3,
                    key=f"assign_{inquiry.get('inquiry_id')}"
                )
                
                # Update buttons
                if st.button(f"💾 Save Changes", key=f"save_{inquiry.get('inquiry_id')}"):
                    # Update inquiry
                    inquiry['status'] = new_status
                    inquiry['response'] = response
                    inquiry['assigned_to'] = assigned_to if assigned_to != "None" else None
                    inquiry['updated_at'] = datetime.now()
                    
                    result = update_inquiry_mcp(
                            inquiry.get('inquiry_id'),
                            status=new_status,
                            response=response if response is not None else "",
                            assigned_to=assigned_to if assigned_to != "None" else "",
                            #updated_at=datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
                        )
                    # Simulate push notification
                    if new_status != inquiry.get('previous_status', 'OPEN'):
                        st.success(f"🔔 Notification sent to {inquiry.get('user_name')} about status change!")
                        inquiry['previous_status'] = new_status
                    
                    st.success("✅ Changes saved successfully!")
                    st.rerun()
                
                if st.button(f"📧 Send Notification", key=f"notify_{inquiry.get('inquiry_id')}"):
                    st.success(f"🔔 Notification sent to {inquiry.get('user_name')}!")

def show_analytics_page():
    """Renamed from old dashboard - now the analytics page"""
    st.header("📊 Analytics & Insights")
    
    try:
        if client:
            # Fetch recent events using MCP client
            events_response = client.search_corporate_actions(limit=1000)
            if "error" not in events_response:
                events = events_response.get("events", [])
                st.success("✅ Connected to MCP servers - showing live data")
            else:
                events = get_sample_upcoming_events()
                st.info("📊 Using sample data - MCP search failed")
        else:
            events = get_sample_upcoming_events()
            st.info("📊 Using sample data - MCP client not available")
            
        # Normalize event data to handle different structures
        events = normalize_event_data(events)
        
        # Calculate metrics
        total_events = len(events)
        active_events = len([e for e in events if e.get("status", "").upper() == "CONFIRMED"])
        upcoming_events = len([e for e in events if e.get("status", "").upper() == "ANNOUNCED"])
        pending_events = len([e for e in events if e.get("status", "").upper() == "PENDING"])

        # Display metrics with color indicators
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📈 Total Events", total_events)
        with col2:
            st.metric("✅ Active Events", active_events, delta=None, delta_color="normal")
        with col3:
            st.metric("📅 Upcoming", upcoming_events, delta=None, delta_color="normal")
        with col4:
            st.metric("⏳ Pending", pending_events, delta=None, delta_color="normal")
        
        # Create visualizations
        if events:
            col1, col2 = st.columns(2)
            
            with col1:
                # Status distribution pie chart
                st.subheader("📊 Event Status Distribution")
                status_counts = {}
                for event in events:
                    status = event.get("status", "Unknown")
                    status_counts[status] = status_counts.get(status, 0) + 1
                
                if status_counts:
                    fig_pie = px.pie(
                        values=list(status_counts.values()),
                        names=list(status_counts.keys()),
                        title="Events by Status",
                        color_discrete_map={
                            'confirmed': '#28a745',    # Green
                            'announced': '#ffc107',    # Yellow
                            'pending': '#dc3545',      # Red
                            'processed': '#17a2b8',    # Blue
                            'cancelled': '#6c757d'     # Gray
                        }
                    )
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                # Event type distribution
                st.subheader("🏢 Event Type Distribution")
                type_counts = {}
                for event in events:
                    event_type = event.get("event_type", "Unknown")
                    type_counts[event_type] = type_counts.get(event_type, 0) + 1
                
                if type_counts:
                    fig_bar = px.bar(
                        x=list(type_counts.keys()),
                        y=list(type_counts.values()),
                        title="Events by Type",
                        color=list(type_counts.values()),
                        color_continuous_scale="viridis"
                    )
                    fig_bar.update_layout(xaxis_title="Event Type", yaxis_title="Count")
                    st.plotly_chart(fig_bar, use_container_width=True)
        
        # Recent events table with color-coded status
        st.subheader("📋 Recent Corporate Actions")
        if events:
            # Create a styled dataframe
            df = pd.DataFrame(events)
            
            # Format the dataframe for display with normalized column names
            display_columns = ["company_name", "symbol", "event_type", "status", "announcement_date"]
            available_columns = [col for col in display_columns if col in df.columns]
            
            if available_columns:
                display_df = df[available_columns].copy()
                
                # Add status styling function
                def color_status(val):
                    if val == 'confirmed':
                        return 'background-color: #d4edda; color: #155724; font-weight: bold;'
                    elif val == 'announced':
                        return 'background-color: #fff3cd; color: #856404; font-weight: bold;'
                    elif val == 'pending':
                        return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
                    elif val == 'processed':
                        return 'background-color: #d1ecf1; color: #0c5460; font-weight: bold;'
                    else:
                        return 'background-color: #e2e3e5; color: #383d41; font-weight: bold;'
                
                # Rename columns for better display
                column_mapping = {
                    "company_name": "Company",
                    "symbol": "Symbol", 
                    "event_type": "Event Type",
                    "status": "Status",
                    "announcement_date": "Announced"
                }
                display_df = display_df.rename(columns=column_mapping)
                
                # Apply styling
                styled_df = display_df.style.applymap(color_status, subset=['Status'])
                st.dataframe(styled_df, use_container_width=True)
            else:
                st.dataframe(df, use_container_width=True)
                
            # Additional insights
            st.subheader("🔍 Quick Insights")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Most active companies
                company_counts = {}
                for event in events:
                    company = event.get("company_name", "Unknown")
                    company_counts[company] = company_counts.get(company, 0) + 1
                
                if company_counts:
                    most_active = max(company_counts, key=company_counts.get)
                    st.metric("🏆 Most Active Company", most_active, f"{company_counts[most_active]} events")
            
            with col2:
                # Most common event type
                if type_counts:
                    most_common_type = max(type_counts, key=type_counts.get)
                    st.metric("📈 Most Common Event", most_common_type.replace('_', ' ').title(), f"{type_counts[most_common_type]} events")
            
            with col3:
                # Event timeline
                recent_events = len([e for e in events if e.get("announcement_date", "").startswith("2024")])
                st.metric("📅 Recent Events (2024)", recent_events, "events")
                
        else:
            st.info("No recent events found")
            
    except Exception as e:
        st.error(f"Error loading dashboard: {str(e)}")
        show_sample_dashboard()

def show_administrator_page():
    """Administrator interface for managing inquiries"""
    st.header("👨‍💼 Administrator Dashboard")
    
    # Check user role
    if st.session_state.get('user_role') != 'ADMINISTRATOR':
        st.warning("⚠️ Access denied. Switch to Administrator role to access this page.")
        return
    
    #Initialize inquiries if not exists
    #if "inquiries" not in st.session_state:
        #st.session_state.inquiries = get_sample_inquiries(get_sample_upcoming_events())
    
    if "inquiries_loaded" not in st.session_state:
        st.session_state.inquiries_loaded = False

    # Load inquiries from database on first load for subscribed events
    if not st.session_state.inquiries_loaded and client and st.session_state.user_subscriptions:
        try:
            # Get upcoming events for user's subscriptions to fetch their inquiries
            result = client._call_tool(
                MCP_SERVERS["rag"], 
                "get_upcoming_events_tool",
                {"user_id": st.session_state.user_id, "days_ahead": 30}
            )
            
            if isinstance(result, str):
                result = json.loads(result)
                mcp_events = result.get("upcoming_events", [])
            elif isinstance(result, dict) and result.get("upcoming_events"):
                mcp_events = result["upcoming_events"]
            
            print(f"🔍 Loaded {len(mcp_events)} MCP events for inquiries")
            database_inquiries = []
            for event in mcp_events:
                event_inquiries = event.get("inquiries", [])
                database_inquiries.extend(event_inquiries)
            
            if database_inquiries:
                st.session_state.inquiries = database_inquiries
                st.info(f"📊 Loaded {len(database_inquiries)} inquiries from database")
                
            st.session_state.inquiries_loaded = True
        except Exception as e:
            st.warning(f"⚠️ Could not load inquiries from database: {str(e)}")
            st.session_state.inquiries_loaded = True

    # Admin metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        pending_count = len([i for i in st.session_state.inquiries if i.get('status') in ['OPEN', 'ACKNOWLEDGED']])
        st.metric("🔄 Pending", pending_count)
    with col2:
        assigned_count = len([i for i in st.session_state.inquiries if i.get('assigned_to')])
        st.metric("👤 Assigned", assigned_count)    
    with col3:
        urgent_count = len([i for i in st.session_state.inquiries if i.get('priority') == 'URGENT'])
        st.metric("🚨 Urgent", urgent_count)
    with col4:
        avg_response_time = "2.3 days"  # Mock data
        st.metric("⏱️ Avg Response", avg_response_time)
    
    st.markdown("### 🛠️ Inquiry Management")
    
    # Data Management Section
    st.markdown("### �️ Data Management")
    with st.expander("📊 Sample Data Generation", expanded=False):
        st.write("Generate sample corporate actions and inquiries for testing purposes")
        
        col1, col2 = st.columns(2)
        with col1:
            symbols_input = st.text_input(
                "Stock Symbols (comma-separated)", 
                value="AAPL,MSFT,TSLA,GOOGL,AMZN",
                help="Enter stock symbols separated by commas"
            )
        with col2:
            events_per_symbol = st.number_input(
                "Events per Symbol", 
                min_value=1, 
                max_value=10, 
                value=3,
                help="Number of corporate action events to generate per symbol"
            )
        
        if st.button("🎲 Generate Sample Data", type="primary"):
            if client:
                with st.spinner("Generating sample data..."):
                    try:
                        # Call the generate_sample_data MCP tool
                        result = client._call_tool(
                            MCP_SERVERS["rag"],
                            "generate_sample_data",
                            {
                                "symbols": symbols_input,
                                "num_events_per_symbol": events_per_symbol
                            }
                        )
                        
                        if isinstance(result, str):
                            try:
                                result = json.loads(result)
                            except json.JSONDecodeError:
                                st.error(f"Failed to parse response: {result}")
                                return
                        
                        if "error" in result:
                            st.error(f"❌ Error generating sample data: {result['error']}")
                        elif result.get("success"):
                            st.success("✅ Sample data generated successfully!")
                            
                            # Display summary
                            summary = result.get("summary", {})
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("📈 Events Created", summary.get("total_events_stored", 0))
                            with col2:
                                st.metric("💬 Inquiries Created", summary.get("total_inquiries_stored", 0))
                            with col3:
                                st.metric("🏢 Symbols", len(summary.get("symbols", [])))
                            
                            # Show sample data
                            if "sample_events" in result and result["sample_events"]:
                                st.write("**Sample Events Generated:**")
                                for event in result["sample_events"]:
                                    st.write(f"• {event.get('event_id')} - {event.get('event_type')} for {event.get('security', {}).get('symbol')}")
                            
                            if "sample_inquiries" in result and result["sample_inquiries"]:
                                st.write("**Sample Inquiries Generated:**")
                                for inquiry in result["sample_inquiries"]:
                                    st.write(f"• {inquiry.get('inquiry_id')} - {inquiry.get('subject')}")
                        else:
                            st.warning(f"⚠️ Unexpected response: {result}")
                            
                    except Exception as e:
                        st.error(f"❌ Failed to generate sample data: {str(e)}")
            else:
                st.error("❌ MCP client not available. Please ensure the RAG server is running.")
        
        # Database status check
        if st.button("🔍 Check Database Status"):
            if client:
                with st.spinner("Checking database status..."):
                    try:
                        result = client._call_tool(
                            MCP_SERVERS["rag"],
                            "check_container_status",
                            {}
                        )
                        
                        if isinstance(result, str):
                            try:
                                result = json.loads(result)
                            except json.JSONDecodeError:
                                st.error(f"Failed to parse response: {result}")
                                return
                        
                        if "error" in result:
                            st.error(f"❌ Database check failed: {result['error']}")
                        else:
                            st.write("**Database Status:**")
                            status = result.get("overall_status", "unknown")
                            if status == "healthy":
                                st.success(f"🟢 Database Status: {status}")
                            else:
                                st.warning(f"⚠️ Database Status: {status}")
                            
                            # Show container details
                            containers = result.get("containers", {})
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                corp_status = "🟢" if containers.get("corporate_actions", {}).get("available") else "🔴"
                                st.write(f"{corp_status} Corporate Actions")
                            with col2:
                                inq_status = "🟢" if containers.get("inquiries", {}).get("available") else "🔴"
                                st.write(f"{inq_status} Inquiries")
                            with col3:
                                sub_status = "🟢" if containers.get("subscriptions", {}).get("available") else "🔴"
                                st.write(f"{sub_status} Subscriptions")
                            
                    except Exception as e:
                        st.error(f"❌ Failed to check database status: {str(e)}")
            else:
                st.error("❌ MCP client not available. Please ensure the RAG server is running.")
    
    # Bulk actions
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📢 Broadcast Update"):
            st.info("Broadcast update feature would notify all subscribers")
    with col2:
        if st.button("📊 Generate Report"):
            st.info("Report generation feature would create analytics report")
    with col3:
        if st.button("🔄 Refresh Data"):
            st.rerun()
    
    # Inquiry management
    for i, inquiry in enumerate(st.session_state.inquiries):
        if inquiry.get('status') not in ['RESOLVED', 'CLOSED']:
            with st.expander(
                f"🎫 **{inquiry.get('inquiry_id')}** - {inquiry.get('subject')} "
                f"[{inquiry.get('priority')} | {inquiry.get('status')}]",
                expanded=i < 2
            ):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Description:** {inquiry.get('description')}")
                    st.write(f"**User:** {inquiry.get('user_name')} ({inquiry.get('organization', 'Unknown')})")
                    st.write(f"**Created:** {inquiry.get('created_at', datetime.now())}")
                    
                    # Response form
                    response_key = f"response_{inquiry.get('inquiry_id')}"
                    response = st.text_area(
                        "Administrator Response", 
                        value=inquiry.get('response', ''),
                        key=response_key
                    )
                
                with col2:
                    # Status update
                    new_status = st.selectbox(
                        "Update Status",
                        ["OPEN", "ACKNOWLEDGED", "IN_REVIEW", "RESPONDED", "ESCALATED", "RESOLVED", "CLOSED"],
                        index=["OPEN", "ACKNOWLEDGED", "IN_REVIEW", "RESPONDED", "ESCALATED", "RESOLVED", "CLOSED"].index(inquiry.get('status', 'OPEN')),
                        key=f"status_{inquiry.get('inquiry_id')}"
                    )
                    
                    # Assignment
                    assigned_to = st.selectbox(
                        "Assign To",
                        ["admin_001", "admin_002", "admin_003", "None"],
                        index=0 if inquiry.get('assigned_to') else 3,
                        key=f"assign_{inquiry.get('inquiry_id')}"
                    )
                    
                    # Update buttons
                    if st.button(f"💾 Save Changes", key=f"save_{inquiry.get('inquiry_id')}"):
                        # Update inquiry
                        inquiry['status'] = new_status
                        inquiry['response'] = response
                        inquiry['assigned_to'] = assigned_to if assigned_to != "None" else None
                        inquiry['updated_at'] = datetime.now()
                        
                        # Simulate push notification
                        if new_status != inquiry.get('previous_status', 'OPEN'):
                            st.success(f"🔔 Notification sent to {inquiry.get('user_name')} about status change!")
                            inquiry['previous_status'] = new_status
                        
                        st.success("✅ Changes saved successfully!")
                        st.rerun()
                    
                    if st.button(f"📧 Send Notification", key=f"notify_{inquiry.get('inquiry_id')}"):
                        st.success(f"🔔 Notification sent to {inquiry.get('user_name')}!")

if __name__ == "__main__":
    main()

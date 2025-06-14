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
    "websearch": "http://localhost:8001/mcp", 
    "comments": "http://localhost:8002/mcp"
}

# Page configuration
st.set_page_config(
    page_title="Corporate Actions Dashboard - MCP",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    def rag_query(self, query: str, max_results: int = 5, include_comments: bool = True, chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
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
                "include_comments": include_comments,
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
    
    def get_event_comments(self, event_id: str, limit: int = 50) -> Dict[str, Any]:
        """Get event comments"""
        result = self._call_tool(
            self.servers['comments'],
            "get_event_comments",
            {
                "event_id": event_id,
                "limit": limit
            }
        )
        # If result is a string (successful), parse as JSON
        if isinstance(result, str):
            try:
                return json.loads(result)
            except:
                return {"comments": []}
        # If result is a dict, it's an error response
        return result
        
    def add_comment(self, event_id: str, user_name: str, comment_text: str, comment_type: str = "general") -> Dict[str, Any]:
        """Add comment"""
        result = self._call_tool(
            self.servers['comments'],
            "add_comment",
            {
                "event_id": event_id,
                "user_name": user_name,
                "comment_text": comment_text,
                "comment_type": comment_type
            }
        )
        # If result is a string (successful), parse as JSON
        if isinstance(result, str):
            try:
                return json.loads(result)
            except:                return {"success": False}
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
        elif server_name == 'comments':
            # Use a simple comment query as health check
            result = self._call_tool(server_url, "get_event_comments", {"event_id": "test", "limit": 1})
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
    """Check the status of MCP servers using official MCP Python SDK client"""
    if not client:
        return {
            "status": "no_client",
            "message": "MCP client not available. Check if MCP Python SDK library is installed."
        }
    
    try:
        # Test RAG server with a simple health check
        result = client.check_server_health('rag')
        #print(f"RAG Server Health Check: {result}")
        if "error" in result:
            return {
                "status": "disconnected", 
                "message": f"MCP servers not responding: {result['error']}. Please start with: python start_mcp_servers.py"
            }
        
        return {
            "status": "connected",
            "message": "Connected to MCP servers successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error connecting to MCP servers: {str(e)}. Start with: python start_mcp_servers.py"
        }

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
    }
    .chart-container {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
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
            cd mcp-server
            python -m fastmcp run main.py --port 8000
            
            # Terminal 2 - Web Search Server  
            cd mcp-websearch
            python -m fastmcp run main.py --port 8001
            
            # Terminal 3 - Comments Server
            cd mcp-comments
            python -m fastmcp run main.py --port 8002
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
            cd mcp-server
            python -m fastmcp run main.py --port 8000
            
            # Terminal 2 - Web Search Server  
            cd mcp-websearch
            python -m fastmcp run main.py --port 8001
            
            # Terminal 3 - Comments Server
            cd mcp-comments
            python -m fastmcp run main.py --port 8002
            ```
            """)
    else:
        st.warning(f"⚠️ {server_status['message']} - Using sample data")
    
    
      # Sidebar navigation
    with st.sidebar:
        st.header("Navigation")
        page = st.radio(
            "Select Page",
            ["Dashboard", "RAG Assistant", "Search Events", "Comments & Q&A", "Web Research"]
        )        # Server Status Sidebar
        st.header("🖥️ Server Status")
        if client:
            # Test individual server components using official MCP client
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write("**RAG Server**")
            with col2:
                try:
                    result = client.check_server_health('rag')
                    if "error" not in result:
                        st.write("🟢")
                    else:
                        st.write("🔴")
                except:
                    st.write("🔴")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write("**Web Search**")
            with col2:
                try:
                    result = client.check_server_health('websearch')
                    if "error" not in result:
                        st.write("🟢")
                    else:
                        st.write("🔴")
                except:
                    st.write("🔴")
                    
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write("**Comments**")
            with col2:
                try:
                    result = client.check_server_health('comments')
                    if "error" not in result:
                        st.write("🟢")
                    else:
                        st.write("🔴")
                except:
                    st.write("🔴")
        else:
            st.write("❌ Client not available")
            st.write("Start servers first!")
    
    # Route to selected page
    if page == "Dashboard":
        show_dashboard()
    elif page == "RAG Assistant":
        show_rag_assistant()
    elif page == "Search Events":
        show_search_events()
    elif page == "Comments & Q&A":
        show_comments_qa()
    elif page == "Web Research":
        show_web_research()

def show_dashboard():
    """Display main dashboard with enhanced visualizations"""
    st.header("📊 Dashboard Overview")
    
    try:
        if client:
            # Fetch recent events using MCP client
            events_response = client.search_corporate_actions(limit=10)
            if "error" not in events_response:
                events = events_response.get("events", [])
                st.success("✅ Connected to MCP servers - showing live data")
            else:
                events = get_sample_events()
                st.info("📊 Using sample data - MCP search failed")
        else:
            events = get_sample_events()
            st.info("📊 Using sample data - MCP client not available")
            
        # Normalize event data to handle different structures
        events = normalize_event_data(events)
        
        # Calculate metrics
        total_events = len(events)
        active_events = len([e for e in events if e.get("status") == "confirmed"])
        upcoming_events = len([e for e in events if e.get("status") == "announced"])
        pending_events = len([e for e in events if e.get("status") == "pending"])
        
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

def show_rag_assistant():
    """Display RAG assistant interface with enhanced chat history and visualization support"""
    st.header("🤖 RAG Assistant (MCP)")
    st.markdown("Ask questions about corporate actions using natural language")

    # Chat interface
    if "messages" not in st.session_state:
        st.session_state.messages = []    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Regenerate visualization if it was shown before
            if message.get("had_visualization") and message.get("sources"):
                with st.container():
                    st.caption("🔄 Regenerated Visualization")
                    fig = generate_dynamic_visualization(
                        message["sources"], 
                        message["content"] if message["role"] == "user" else "visualization", 
                        message.get("visualization_suggestions", {})
                    )
                    if fig:
                        st.plotly_chart(fig, use_container_width=True, key=f"viz_{hash(str(message))}")
            
            # Show visualization suggestions if available
            elif message.get("visualization_suggestions"):
                with st.expander("📊 Visualization Suggestions"):
                    suggestions = message["visualization_suggestions"]
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
            if message.get("sources"):
                with st.expander("📋 Sources"):
                    for source in message["sources"]:
                        st.json(source)

    # Chat input
    if prompt := st.chat_input("Ask about corporate actions"):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get RAG response with chat history
        with st.chat_message("assistant"):
            with st.spinner("Searching corporate actions data..."):
                try:
                    if client:
                        # Prepare chat history (last 5 messages for context)
                        chat_history = st.session_state.messages[-10:] if len(st.session_state.messages) > 10 else st.session_state.messages
                        
                        response = client.rag_query(
                            prompt, 
                            max_results=5, 
                            include_comments=True,
                            chat_history=chat_history                        )
                        
                        if "error" not in response:
                            # Parse JSON response
                            if isinstance(response, str):
                                rag_data = json.loads(response)
                            else:
                                rag_data = response
                                
                            answer = rag_data.get("answer", "I couldn't find relevant information.")
                            sources = rag_data.get("sources", [])
                            confidence = rag_data.get("confidence_score", 0.0)
                            requires_viz = rag_data.get("requires_visualization", False)
                            viz_suggestions = rag_data.get("visualization_suggestions", {})
                            
                            st.markdown(answer)
                            
                            # Generate dynamic visualization if requested
                            if requires_viz and sources:
                                st.subheader("📊 Generated Visualization")
                                
                                with st.spinner("Generating visualization..."):
                                    # Generate dynamic chart based on the data and query
                                    fig = generate_dynamic_visualization(sources, prompt, viz_suggestions)
                                    
                                    if fig:
                                        st.plotly_chart(fig, use_container_width=True)
                                        st.success("✅ Visualization generated successfully!")
                                    else:
                                        st.warning("⚠️ Could not generate visualization for this data. You can check the Dashboard or Search sections for more visualization options.")
                                        
                                        # Show alternative visualization suggestions
                                        if viz_suggestions.get("recommended_charts"):
                                            with st.expander("💡 Visualization Suggestions"):
                                                st.write("**Available visualizations for this data:**")
                                                for chart_type in viz_suggestions["recommended_charts"]:
                                                    chart_name = chart_type.replace("_", " ").title()
                                                    st.write(f"• {chart_name}")
                                                st.info("Visit the Dashboard or Search Events sections to see these visualizations!")
                            
                            elif requires_viz and not sources:
                                st.info("🎨 I detected you're asking for visualizations, but no data was found to visualize. Try searching for specific events or companies first!")
                            
                            if sources:
                                with st.expander(f"📋 Sources (Confidence: {confidence:.1%})"):
                                    for i, source in enumerate(sources):
                                        st.json(source)
                            
                            # Build assistant message with all metadata
                            assistant_message = {
                                "role": "assistant",
                                "content": answer,
                                "sources": sources,
                                "confidence": confidence,
                                "requires_visualization": requires_viz,
                                "had_visualization": requires_viz and sources and len(sources) > 0
                            }
                            
                            if viz_suggestions:
                                assistant_message["visualization_suggestions"] = viz_suggestions
                            
                            st.session_state.messages.append(assistant_message)
                        else:
                            error_msg = f"Error: {response.get('error', 'Unknown error')}"
                            st.error(error_msg)
                            st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    else:
                        error_msg = "MCP client not available. Please check server connection."
                        st.error(error_msg)
                        st.session_state.messages.append({"role": "assistant", "content": error_msg})
                        
                except Exception as e:
                    error_msg = f"Error processing query: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

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
            date_from = st.date_input("From Date", value=date.today() - timedelta(days=30))
            date_to = st.date_input("To Date", value=date.today())
        
        limit = st.slider("Max Results", 1, 50, 10)
        submit_button = st.form_submit_button("Search")
    
    if submit_button:
        try:
            if client:
                # Build search parameters
                search_params = {
                    "search_text": search_text,
                    "event_type": event_type,
                    "company_name": company_name,
                    "status": status,
                    "date_from": date_from.isoformat() if date_from else "",
                    "date_to": date_to.isoformat() if date_to else "",
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

def show_comments_qa():
    """Display comments and Q&A interface"""
    st.header("💬 Comments & Q&A (MCP)")
    
    # Event selector
    event_id = st.selectbox(
        "Select Event",
        ["AAPL_DIV_2024_Q1", "MSFT_SPLIT_2024", "TSLA_DIV_2024_SPECIAL"],
        help="Select an event to view or add comments"
    )
    
    if event_id:
        # Display existing comments
        st.subheader(f"Comments for {event_id}")
        
        try:
            if client:
                response = client.get_event_comments(event_id, limit=50)
                
                if "error" not in response:
                    if isinstance(response, str):
                        comments_data = json.loads(response)
                    else:
                        comments_data = response
                        
                    comments = comments_data.get("comments", [])
                    
                    if comments:
                        for comment in comments:
                            comment_type = comment.get("comment_type", "general")
                            icon = {"question": "❓", "analysis": "📊", "general": "💭"}.get(comment_type, "💭")
                            
                            with st.container():
                                st.markdown(f"""
                                <div style="border-left: 3px solid #007bff; padding-left: 1rem; margin: 1rem 0;">
                                    <strong>{icon} {comment.get('user_name', 'Anonymous')}</strong> 
                                    <small>- {comment_type}</small><br>
                                    <em>{comment.get('created_at', 'Unknown time')}</em><br>
                                    {comment.get('comment_text', 'No content')}
                                </div>
                                """, unsafe_allow_html=True)
                    else:
                        st.info("No comments yet for this event")
                else:
                    st.error(f"Failed to load comments: {response.get('error', 'Unknown error')}")
            else:
                st.warning("MCP client not available. Cannot load comments.")
                
        except Exception as e:
            st.error(f"Error loading comments: {str(e)}")
        
        st.markdown("---")
        
        # Add new comment form
        st.subheader("Add Comment")
        
        with st.form("comment_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                user_name = st.text_input("Your Name", value="Demo User")
            
            with col2:
                comment_type = st.selectbox("Comment Type", ["general", "question", "analysis", "clarification"])
            
            comment_text = st.text_area("Comment Content", height=100)
            
            if st.form_submit_button("Submit Comment"):
                if comment_text and user_name:
                    try:
                        if client:
                            response = client.add_comment(event_id, user_name, comment_text, comment_type)
                            
                            if "error" not in response:
                                if isinstance(response, str):
                                    result = json.loads(response)
                                else:
                                    result = response
                                    
                                if result.get("success"):
                                    st.success("Comment added successfully!")
                                    st.rerun()
                                else:
                                    st.error(f"Failed to add comment: {result.get('error', 'Unknown error')}")
                            else:
                                st.error(f"Error: {response.get('error', 'Unknown error')}")
                        else:
                            st.warning("MCP client not available. Cannot add comment.")
                    except Exception as e:
                        st.error(f"Error adding comment: {str(e)}")
                else:
                    st.error("Please fill in all required fields")

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

def get_sample_events():
    """Get sample events for demo"""
    return [
        {
            "event_id": "AAPL_DIV_2024_Q1",
            "company_name": "Apple Inc.",
            "symbol": "AAPL",
            "event_type": "dividend",
            "description": "Quarterly cash dividend",
            "status": "confirmed",
            "announcement_date": "2024-01-25"
        },
        {
            "event_id": "MSFT_SPLIT_2024",
            "company_name": "Microsoft Corporation",
            "symbol": "MSFT",
            "event_type": "stock_split",
            "description": "2-for-1 stock split",
            "status": "announced",
            "announcement_date": "2024-01-15"
        },
        {
            "event_id": "TSLA_DIV_2024_SPECIAL",
            "company_name": "Tesla Inc.",
            "symbol": "TSLA",
            "event_type": "special_dividend",
            "description": "Special cash dividend distribution",
            "status": "confirmed",
            "announcement_date": "2024-02-01"
        }
    ]

def show_sample_dashboard():
    """Show enhanced sample dashboard when MCP servers are unavailable"""
    st.info("🔧 Showing sample data - MCP servers may be offline")
    
    events = get_sample_events()
    
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
    events = get_sample_events()
    
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
            
    except Exception as e:
        return f"Code execution error: {str(e)}"
        
if __name__ == "__main__":
    main()

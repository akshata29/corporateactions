"""
Streamlit UI for Corporate Actions POC - Azure AI Agent Service Integration
Interactive dashboard for market participants using Azure AI Agent Service with MCP integration
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import asyncio
import threading
import re
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
import sys
import os
import tempfile
import subprocess
from dotenv import load_dotenv
import ast

# Load environment variables
load_dotenv(".env", override=True)

# Page configuration
st.set_page_config(
    page_title="Corporate Actions Dashboard - Azure AI Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Azure AI Agent Service imports
try:    
    from azure.ai.projects import AIProjectClient
    from azure.ai.agents import AgentsClient
    from azure.ai.agents.models import (
        Agent, 
        FunctionTool,
        ToolSet,
        ThreadMessage,
        MessageRole
    )
    from azure.identity import DefaultAzureCredential
    from azure.core.credentials import AzureKeyCredential
    import openai
    USE_AZURE_AI = True
except ImportError:
    USE_AZURE_AI = False
    st.warning("Azure AI Project SDK not available. Using fallback mode.")

# MCP Client imports for agent tool registration
try:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    USE_MCP = True
except ImportError:
    USE_MCP = False
    st.warning("MCP Python SDK not available. Using sample data.")


# Configuration
AZURE_AI_CONFIG = {
    "project_url": os.getenv("AZURE_AI_PROJECT_URL", ""),
    "api_key": os.getenv("AZURE_AI_API_KEY", ""),
    "model_deployment": os.getenv("AZURE_AI_MODEL_DEPLOYMENT", "gpt-4o"),
    "agent_name": "corporate-actions-assistant",
    "agent_instructions": """You are a specialized Corporate Actions AI Assistant with access to real-time financial data through MCP servers.

Your capabilities include:
- Searching corporate actions (dividends, stock splits, mergers, etc.)
- Providing detailed event analysis and insights
- Creating visualizations and charts from financial data
- Answering natural language questions about corporate actions
- Managing user preferences and subscriptions

You have access to the following tools via MCP integration:
- rag_query: Enhanced search with chat history and visualization detection
- search_corporate_actions: Advanced filtering and data normalization
- get_event_details: Comprehensive event information
- web_search: Financial news and market data
- news_search: Corporate actions news with sentiment analysis

Always provide:
1. Clear, actionable insights
2. Visualization suggestions when relevant
3. Context-aware responses based on chat history
4. Confidence scores for your recommendations

Be professional, accurate, and helpful in all interactions."""
}

# MCP Server URLs for tool discovery
MCP_SERVERS = {
    "rag": "http://localhost:8000/mcp",
    "websearch": "http://localhost:8001/mcp"
}

class AzureAIAgentManager:
    """Azure AI Agent Service manager with MCP tool integration"""
    
    def __init__(self):
        self.client = None
        self.project_client = None
        self.agent = None
        self.thread = None
        self.mcp_tools = {}
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize Azure AI Agent Service with MCP tool discovery"""        
        if not USE_AZURE_AI:
            st.error("Azure AI Project SDK not available. Please install: pip install azure-ai-projects")
            return False
        
        try:
            # Get Azure AI configuration
            endpoint = AZURE_AI_CONFIG["project_url"]
            api_key = AZURE_AI_CONFIG["api_key"]
            
            # Ensure endpoint has https protocol
            if not endpoint.startswith("https://"):
                endpoint = f"https://{endpoint}"
            
            st.sidebar.info(f"🔗 Connecting to Azure AI Project: {endpoint}")            # Initialize Azure AI Project Client exactly as shown in quickstart documentation
            # Reference: https://learn.microsoft.com/en-us/azure/ai-services/agents/quickstart?pivots=programming-language-python-azure
            self.project_client = AIProjectClient(
                endpoint=endpoint,
                credential=DefaultAzureCredential()
                # Using default API version instead of specifying "latest"
            )
            
            # Get the agents client from the project client
            self.client = self.project_client.agents
            
            st.sidebar.success(f"✅ Connected to Azure AI Project")
            
            # Discover and register MCP tools
            await self._discover_mcp_tools()
            
            # Create or get agent with MCP tools
            await self._create_agent()
            
            self.is_initialized = True
            return True
            
        except Exception as e:
            st.error(f"Failed to initialize Azure AI Agent: {str(e)}")
            return False
            return False
    
    async def _discover_mcp_tools(self):
        """Discover available tools from MCP servers and register them as Azure AI functions"""
        if not USE_MCP:
            return
            
        for server_name, server_url in MCP_SERVERS.items():
            try:
                async with streamablehttp_client(server_url) as (read_stream, write_stream, _):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        
                        # List available tools
                        tools_result = await session.list_tools()
                        
                        for tool in tools_result.tools:
                            # Create Azure AI function from MCP tool
                            function_def = {
                                "name": f"mcp_{server_name}_{tool.name}",
                                "description": tool.description or f"MCP tool: {tool.name}",
                                "parameters": self._convert_mcp_schema_to_openai(tool.inputSchema)
                            }
                            
                            # Store MCP tool info for execution
                            self.mcp_tools[function_def["name"]] = {
                                "server_url": server_url,
                                "tool_name": tool.name,
                                "schema": tool.inputSchema
                            }
                            
                            st.sidebar.success(f"✅ Registered MCP tool: {tool.name} from {server_name}")
                            
            except Exception as e:
                st.sidebar.warning(f"⚠️ Failed to connect to {server_name}: {str(e)}")
    
    def _convert_mcp_schema_to_openai(self, mcp_schema: dict) -> dict:
        """Convert MCP tool schema to OpenAI function schema"""
        if not mcp_schema:
            return {"type": "object", "properties": {}}        # Basic conversion - adjust as needed for your specific schemas
        return {
            "type": "object",
            "properties": mcp_schema.get("properties", {}),
            "required": mcp_schema.get("required", [])
        }
    
    async def _create_agent(self):
        """Create Azure AI Agent with MCP tool functions following official documentation"""
        try:
            # First, check if an agent with the same name already exists
            st.sidebar.info("🔍 Checking for existing agents...")
            
            try:
                existing_agents = self.project_client.agents.list_agents()
                agent_list = list(existing_agents.value) if hasattr(existing_agents, 'value') else list(existing_agents)
                
                # Look for existing agent with matching name
                target_agent_name = AZURE_AI_CONFIG["agent_name"]
                existing_agent = None
                
                for agent in agent_list:
                    if agent.name == target_agent_name:
                        existing_agent = agent
                        break
                
                if existing_agent:
                    st.sidebar.success(f"✅ Found existing agent: {existing_agent.name} (ID: {existing_agent.id})")
                    self.agent = existing_agent
                    return
                else:
                    st.sidebar.info(f"💡 No existing agent named '{target_agent_name}' found. Creating new agent...")
                    
            except Exception as list_error:
                st.sidebar.warning(f"⚠️ Could not list existing agents: {str(list_error)}. Creating new agent...")
            
            # Create agent following the official Azure AI Agents quickstart pattern
            # Reference: https://learn.microsoft.com/en-us/azure/ai-services/agents/quickstart?pivots=programming-language-python-azure
            self.agent = self.project_client.agents.create_agent(
                model=AZURE_AI_CONFIG["model_deployment"],
                name=AZURE_AI_CONFIG["agent_name"],
                instructions=AZURE_AI_CONFIG["agent_instructions"],
                # Note: For now we create a simple agent without custom tools
                # MCP tools integration will be added in future iterations
                tools=[]  # Start with no tools for basic functionality
            )
            
            st.sidebar.success(f"✅ Agent created successfully: {self.agent.id}")
            
        except Exception as e:
            st.sidebar.error(f"Failed to create agent: {str(e)}")
            raise
    
    def _create_mcp_function_wrapper(self, tool_name: str):
        """Create a wrapper function for MCP tool execution"""
        async def mcp_function(**kwargs):
            tool_info = self.mcp_tools[tool_name]
            server_url = tool_info["server_url"]
            mcp_tool_name = tool_info["tool_name"]
            
            try:
                async with streamablehttp_client(server_url) as (read_stream, write_stream, _):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        result = await session.call_tool(mcp_tool_name, kwargs)
                        
                        # Extract text content from MCP result
                        if hasattr(result, 'content') and result.content:
                            first_content = result.content[0]
                            if hasattr(first_content, 'text'):
                                return first_content.text
                            else:
                                return str(first_content)
                        else:
                            return str(result)
                            
            except Exception as e:
                return f"Error executing MCP tool {mcp_tool_name}: {str(e)}"
        
        return mcp_function
    
    async def send_message(self, message: str, chat_history: List[Dict] = None) -> Dict:
        """Send message to Azure AI Agent with MCP tool integration"""
        if not self.is_initialized:
            return {"error": "Agent not initialized"}
            
        try:
            # Check if message requires MCP tool execution
            mcp_result = await self._try_mcp_tools_first(message)
            if mcp_result:
                # Enhance the user message with MCP tool results
                enhanced_message = f"""
User Query: {message}

Available Corporate Actions Data:
{mcp_result}

Please analyze this data and provide insights based on the user's query.
"""
            else:
                enhanced_message = message
            
            # Follow the official Azure AI Agents quickstart pattern
            # Reference: https://learn.microsoft.com/en-us/azure/ai-services/agents/quickstart?pivots=programming-language-python-azure
            
            # Create a thread for communication
            thread = self.project_client.agents.threads.create()
            
            # Add a message to the thread
            message_obj = self.project_client.agents.messages.create(
                thread_id=thread.id,
                role="user",
                content=enhanced_message
            )
            
            # Create and process an agent run
            run = self.project_client.agents.runs.create_and_process(
                thread_id=thread.id, 
                agent_id=self.agent.id
            )
            
            # Check if the run completed successfully
            if run.status == "completed":
                # Fetch all messages
                messages = self.project_client.agents.messages.list(thread_id=thread.id)
                
                # Find the assistant's response
                for msg in messages:
                    if msg.role == "assistant":
                        content = ""
                        for content_part in msg.content:
                            if hasattr(content_part, 'text'):
                                content += str(content_part.text)
                            else:
                                content += str(content_part)
                        
                        return {
                            "success": True,
                            "answer": content,
                            "confidence_score": 0.9 if mcp_result else 0.7,
                            "requires_visualization": self._detect_visualization_request(message),
                            "sources": ["MCP Tools"] if mcp_result else []
                        }
                
                return {"success": True, "answer": "No response from agent", "confidence_score": 0.5}
                
            elif run.status == "failed":
                return {"error": f"Agent run failed: {run.last_error if hasattr(run, 'last_error') else 'Unknown error'}"}
            else:
                return {"error": f"Agent run status: {run.status}"}
            
        except Exception as e:
            return {"error": f"Agent execution failed: {str(e)}"}
    
    async def _try_mcp_tools_first(self, message: str) -> Optional[str]:
        """Try to execute relevant MCP tools based on the message content"""
        if not USE_MCP:
            return None
            
        # Determine which MCP tools to use based on message content
        tools_to_try = []
        
        message_lower = message.lower()
        
        # Corporate actions search keywords
        if any(keyword in message_lower for keyword in [
            "corporate actions", "dividend", "split", "merger", "acquisition", 
            "recent", "latest", "summary", "events", "stock split", "spinoff"
        ]):
            tools_to_try.append(("rag", "rag_query"))
            tools_to_try.append(("rag", "search_corporate_actions"))
        
        # Web search keywords
        if any(keyword in message_lower for keyword in [
            "news", "market", "financial news", "announcements", "press release"
        ]):
            tools_to_try.append(("websearch", "web_search"))
            tools_to_try.append(("websearch", "news_search"))
        
        # If no specific tools identified, try general search
        if not tools_to_try:
            tools_to_try.append(("rag", "rag_query"))
        
        # Execute MCP tools and collect results
        results = []
        
        for server_name, tool_name in tools_to_try:
            try:
                server_url = MCP_SERVERS.get(server_name)
                if not server_url:
                    continue
                      # Prepare arguments based on tool type
                if tool_name == "rag_query":
                    args = {"query": message, "max_results": 5, "chat_history": ""}
                elif tool_name == "search_corporate_actions":
                    args = {"search_text": message, "limit": 10}
                elif tool_name in ["web_search", "news_search"]:
                    args = {"query": message, "max_results": 5}
                else:
                    args = {"query": message}
                
                # Execute MCP tool
                result = await self._execute_mcp_tool_direct(server_url, tool_name, args)
                if result and "Error" not in result:
                    results.append(f"**{tool_name.replace('_', ' ').title()}:**\n{result}")
                    
            except Exception as e:
                st.sidebar.warning(f"⚠️ MCP tool {tool_name} failed: {str(e)}")
                continue
        
        return "\n\n".join(results) if results else None
    
    async def _execute_mcp_tool_direct(self, server_url: str, tool_name: str, arguments: Dict) -> str:
        """Execute MCP tool directly with given arguments"""
        try:
            async with streamablehttp_client(server_url) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)
                    
                    if hasattr(result, 'content') and result.content:
                        first_content = result.content[0]
                        if hasattr(first_content, 'text'):
                            return first_content.text
                        else:
                            return str(first_content)
                    else:
                        return str(result)
                        
        except Exception as e:
            return f"Error executing MCP tool: {str(e)}"
    
    def _detect_visualization_request(self, message: str) -> bool:
        """Detect if message requests visualization"""
        viz_keywords = [
            "chart", "graph", "plot", "visualize", "visualization", "show", "display",
            "pie chart", "bar chart", "timeline", "dashboard", "metrics"
        ]
        return any(keyword in message.lower() for keyword in viz_keywords)
    
    async def check_existing_agent(self):
        """Check if an agent with the configured name already exists"""
        if not USE_AZURE_AI:
            return False
        
        try:
            # Get Azure AI configuration
            endpoint = AZURE_AI_CONFIG["project_url"]
            
            # Ensure endpoint has https protocol
            if not endpoint.startswith("https://"):
                endpoint = f"https://{endpoint}"
            
            # Initialize minimal project client for checking
            if not self.project_client:
                self.project_client = AIProjectClient(
                    endpoint=endpoint,
                    credential=DefaultAzureCredential()
                )
            
            # Check for existing agents
            existing_agents = self.project_client.agents.list_agents()
            agent_list = list(existing_agents.value) if hasattr(existing_agents, 'value') else list(existing_agents)
            
            # Look for existing agent with matching name
            target_agent_name = AZURE_AI_CONFIG["agent_name"]
            for agent in agent_list:
                if agent.name == target_agent_name:
                    return True
            
            return False
            
        except Exception as e:
            st.sidebar.warning(f"⚠️ Could not check existing agents: {str(e)}")
            return False

# Initialize Azure AI Agent Manager
@st.cache_resource
def get_azure_ai_agent():
    """Get or create Azure AI Agent Manager"""
    return AzureAIAgentManager()

agent_manager = get_azure_ai_agent()

# Helper functions for sample data (when MCP/Azure AI not available)
def get_enhanced_sample_events_from_mcp(mcp_response: str) -> List[Dict]:
    """Generate enhanced sample events based on MCP response content"""
    base_events = get_sample_events()
    
    # Analyze MCP response for insights to enhance sample data
    response_lower = mcp_response.lower()
    
    # Adjust event counts and types based on MCP insights
    enhanced_events = []
    
    # Extract company names mentioned in MCP response
    mentioned_companies = []
    company_patterns = [
        r'apple\s+inc', r'microsoft\s+corp', r'tesla\s+inc', 
        r'alphabet\s+inc', r'nvidia\s+corp', r'amazon\s+com',
        r'meta\s+platforms', r'google', r'apple', r'microsoft',
        r'tesla', r'nvidia', r'amazon', r'meta'
    ]
    
    for pattern in company_patterns:
        if re.search(pattern, response_lower):
            company_name = pattern.replace(r'\s+', ' ').replace('\\', '').title()
            if company_name not in mentioned_companies:
                mentioned_companies.append(company_name)
    
    # Enhanced event types based on MCP content
    event_type_weights = {
        'dividend': 3 if 'dividend' in response_lower else 1,
        'stock_split': 2 if 'split' in response_lower else 1,
        'merger': 2 if 'merger' in response_lower or 'acquisition' in response_lower else 1,
        'spinoff': 1 if 'spinoff' in response_lower else 1,
        'special_dividend': 2 if 'special' in response_lower else 1
    }
    
    # Generate events with MCP-influenced data
    import random
    random.seed(42)  # For consistent results
    
    for i, base_event in enumerate(base_events):
        enhanced_event = base_event.copy()
        
        # Update with mentioned companies if available
        if mentioned_companies and i < len(mentioned_companies):
            enhanced_event['company_name'] = mentioned_companies[i]
            enhanced_event['symbol'] = mentioned_companies[i][:4].upper()
        
        # Add MCP-derived fields
        enhanced_event['data_source'] = 'MCP-Enhanced'
        enhanced_event['confidence_score'] = random.uniform(0.8, 0.95)
        enhanced_event['market_impact'] = random.choice(['High', 'Medium', 'Low'])
        
        # Add description based on MCP insights
        if 'market volatility' in response_lower:
            enhanced_event['market_conditions'] = 'Volatile'
        elif 'stable' in response_lower:
            enhanced_event['market_conditions'] = 'Stable'
        else:
            enhanced_event['market_conditions'] = 'Normal'
        
        enhanced_events.append(enhanced_event)
    
    # Add additional events if MCP suggests high activity
    if 'increased activity' in response_lower or 'busy' in response_lower:
        additional_events = [
            {
                "event_id": "MCP_DERIVED_001",
                "company_name": "Oracle Corporation",
                "symbol": "ORCL",
                "event_type": "dividend",
                "description": "Quarterly dividend increase",
                "status": "announced",
                "announcement_date": "2025-06-12",
                "data_source": "MCP-Derived",
                "confidence_score": 0.85
            },
            {
                "event_id": "MCP_DERIVED_002", 
                "company_name": "Intel Corporation",
                "symbol": "INTC",
                "event_type": "stock_split",
                "description": "3-for-1 stock split announcement",
                "status": "confirmed",
                "announcement_date": "2025-06-13",
                "data_source": "MCP-Derived",
                "confidence_score": 0.92
            }
        ]
        enhanced_events.extend(additional_events)
    
    return enhanced_events

def get_sample_events():
    """Get sample events for demo"""
    return [
        {
            "event_id": "AAPL_DIV_2025_Q2",
            "company_name": "Apple Inc.",
            "symbol": "AAPL",
            "event_type": "dividend",
            "description": "Quarterly cash dividend",
            "status": "confirmed",
            "announcement_date": "2025-06-01"
        },
        {
            "event_id": "MSFT_SPLIT_2025",
            "company_name": "Microsoft Corporation",
            "symbol": "MSFT",
            "event_type": "stock_split",
            "description": "2-for-1 stock split",
            "status": "announced",
            "announcement_date": "2025-05-15"
        },
        {
            "event_id": "TSLA_DIV_2025_SPECIAL",
            "company_name": "Tesla Inc.",
            "symbol": "TSLA",
            "event_type": "special_dividend",
            "description": "Special cash dividend distribution",
            "status": "confirmed",
            "announcement_date": "2025-05-20"
        },
        {
            "event_id": "GOOGL_MERGER_2025",
            "company_name": "Alphabet Inc.",
            "symbol": "GOOGL",
            "event_type": "merger",
            "description": "Strategic acquisition announcement",
            "status": "announced",
            "announcement_date": "2025-05-25"
        },
        {
            "event_id": "NVDA_SPINOFF_2025",
            "company_name": "NVIDIA Corporation",
            "symbol": "NVDA",
            "event_type": "spinoff",
            "description": "AI division spinoff",
            "status": "pending",
            "announcement_date": "2025-06-10"
        }
    ]

def normalize_event_data(events: List[Dict]) -> List[Dict]:
    """Normalize event data to handle different field structures"""
    normalized = []
    
    for event in events:
        # Handle different field name variations
        normalized_event = {}
        
        # Company name normalization - prioritize existing company_name, then try various fallbacks
        company_name = (
            event.get("company_name") or 
            event.get("issuer_name") or 
            event.get("issuer", {}).get("name") if isinstance(event.get("issuer"), dict) else
            event.get("issuer") or
            "Unknown Company"
        )
        normalized_event["company_name"] = event.get("issuer_name")
        
        # Copy all other fields, avoiding duplicates
        for key, value in event.items():
            if key not in ["issuer_name", "issuer"] or key == "company_name":
                normalized_event[key] = value
        
        # Ensure symbol field exists
        if "symbol" not in normalized_event:
            if "security" in event and isinstance(event["security"], dict):
                normalized_event["symbol"] = event["security"].get("symbol", "N/A")
            else:
                normalized_event["symbol"] = "N/A"
                
        # Ensure required fields exist
        for required_field in ["event_type", "status", "announcement_date"]:
            if required_field not in normalized_event:
                normalized_event[required_field] = "N/A"
        
        normalized.append(normalized_event)
    
    return normalized

def extract_events_from_response(response_text: str) -> List[Dict]:
    """Extract event data from AI Agent response - simplified version"""
    # This would parse the AI response to extract structured event data
    # For now, return sample events based on response content
    events = []
    
    # Look for company mentions in response
    import re
    companies = re.findall(r'([A-Z]{2,5})', response_text)
    
    if companies:
        for i, symbol in enumerate(companies[:5]):  # Limit to 5 events
            events.append({
                "event_id": f"EVT_{symbol}_{i}",
                "symbol": symbol,
                "company_name": f"{symbol} Inc.",
                "event_type": "dividend",
                "description": f"Corporate action for {symbol}",
                "status": "announced",
                "event_date": (datetime.now() + timedelta(days=i+1)).date(),
                "inquiries": []
            })
    
    return events

    """Display dashboard metrics and events list"""
    events = st.session_state.dashboard_events
    
    if events:
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 Total Upcoming", len(events))
        with col2:
            dividend_count = len([e for e in events if 'dividend' in e.get('event_type', '').lower()])
            st.metric("💰 Dividends", dividend_count)
        with col3:
            total_inquiries = sum(len(event.get('inquiries', [])) for event in events)
            st.metric("❓ Total Inquiries", total_inquiries)
        with col4:
            urgent_count = sum(len([i for i in event.get('inquiries', []) if i.get('priority') == 'HIGH']) for event in events)
            st.metric("🚨 Urgent Issues", urgent_count)
        
        # Display events
        for i, event in enumerate(events):
            with st.expander(
                f"🎯 **{event.get('symbol', 'Unknown')}** - {event.get('event_type', 'Unknown').replace('_', ' ').title()} "
                f"({event.get('event_date', 'Unknown')})", 
                expanded=i < 3
            ):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Company:** {event.get('company_name', 'Unknown')}")
                    st.write(f"**Type:** {event.get('event_type', 'Unknown').replace('_', ' ').title()}")
                    st.write(f"**Status:** {event.get('status', 'Unknown').title()}")
                    st.write(f"**Description:** {event.get('description', 'No description')}")
                
                with col2:
                    # Inquiry management buttons
                    st.markdown("**🔧 Inquiry Actions**")
                    
                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    
                    with btn_col1:
                        if st.button("🆕", key=f"create_{event.get('event_id', i)}", 
                                help="Create new inquiry", use_container_width=True):
                            st.session_state.selected_event_for_inquiry = event
                            st.session_state.inquiry_modal_type = 'create'
                            st.rerun()
                    
                    with btn_col2:
                        if st.button("👁️", key=f"view_{event.get('event_id', i)}", 
                                help="View all inquiries", use_container_width=True):
                            st.session_state.selected_event_for_inquiry = event
                            st.session_state.inquiry_modal_type = 'view'
                            st.rerun()
                    
                    with btn_col3:
                        if st.button("✏️", key=f"edit_{event.get('event_id', i)}", 
                                help="Edit your inquiries", use_container_width=True):
                            st.session_state.selected_event_for_inquiry = event
                            st.session_state.inquiry_modal_type = 'edit'
                            st.rerun()
                    
                    # Show inquiry count
                    inquiry_count = len(event.get('inquiries', []))
                    if inquiry_count > 0:
                        st.markdown(f"<small>📝 {inquiry_count} inquiries</small>", unsafe_allow_html=True)
                    else:
                        st.markdown("<small>📭 No inquiries</small>", unsafe_allow_html=True)
    else:
        st.info("📭 No upcoming corporate actions found")
        if not st.session_state.user_subscriptions:
            st.warning("💡 Subscribe to symbols above to see relevant events!")

def show_sample_dashboard_overview():
    """Show sample dashboard when agent not available"""
    st.info("📊 Sample Corporate Actions Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📋 Sample Events", 5)
    with col2:
        st.metric("💰 Dividends", 2)
    with col3:
        st.metric("📈 Stock Splits", 1)
    with col4:
        st.metric("🏢 Mergers", 1)
    
    st.info("Initialize the Azure AI Agent to access live data and full functionality.")

def get_sample_upcoming_events(user_subscriptions=None):
    """Get sample upcoming events, filtered by user subscriptions if provided"""
    all_events = [
        {
            "event_id": "AAPL_DIV_2025_Q2",
            "company_name": "Apple Inc.",
            "symbol": "AAPL",
            "event_type": "dividend",
            "description": "Quarterly cash dividend",
            "status": "confirmed",
            "announcement_date": "2025-06-01",
            "ex_date": "2025-06-25",
            "amount": "$0.25"
        },
        {
            "event_id": "MSFT_SPLIT_2025",
            "company_name": "Microsoft Corporation",
            "symbol": "MSFT",
            "event_type": "stock_split",
            "description": "2-for-1 stock split",
            "status": "announced",
            "announcement_date": "2025-05-15",
            "ex_date": "2025-07-01",
            "ratio": "2:1"
        },
        {
            "event_id": "TSLA_DIV_2025_SPECIAL",
            "company_name": "Tesla Inc.",
            "symbol": "TSLA",
            "event_type": "special_dividend",
            "description": "Special cash dividend distribution",
            "status": "confirmed",
            "announcement_date": "2025-05-20",
            "ex_date": "2025-06-30",
            "amount": "$5.00"
        },
        {
            "event_id": "GOOGL_MERGER_2025",
            "company_name": "Alphabet Inc.",
            "symbol": "GOOGL",
            "event_type": "merger",
            "description": "Strategic acquisition announcement",
            "status": "announced",
            "announcement_date": "2025-05-25",
            "effective_date": "2025-08-15"
        },
        {
            "event_id": "NVDA_SPINOFF_2025",
            "company_name": "NVIDIA Corporation",
            "symbol": "NVDA",
            "event_type": "spinoff",
            "description": "AI division spinoff",
            "status": "pending",
            "announcement_date": "2025-06-10",
            "ex_date": "2025-09-01"
        }
    ]
    
    # If user subscriptions are provided, filter events by subscribed symbols
    if user_subscriptions and len(user_subscriptions) > 0:
        subscribed_symbols = []
        for sub in user_subscriptions:
            if isinstance(sub, dict) and 'symbol' in sub:
                subscribed_symbols.append(sub['symbol'])
            elif isinstance(sub, str):
                subscribed_symbols.append(sub)
        
        if subscribed_symbols:
            filtered_events = [event for event in all_events if event['symbol'] in subscribed_symbols]
            return filtered_events if filtered_events else all_events  # Return all if no matches
    
    return all_events

# Inquiry Modal Functions (simplified versions that use AI Agent)
def get_user_inquiry_status(event_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Get user's inquiry status for a specific event using embedded inquiry data"""
    try:
        # Get inquiries from the event data directly (already embedded)
        all_inquiries = event_data.get('inquiries', [])
        
        # Debug: Show what we found
        print(f"DEBUG - Event {event_data.get('event_id', 'unknown')} has {len(all_inquiries)} total inquiries")
        print(f"DEBUG - Looking for user_id: '{user_id}'")
        
        # Show all user_ids in the inquiries for debugging
        if all_inquiries:
            inquiry_user_ids = [inq.get("user_id", "NO_USER_ID") for inq in all_inquiries]
            print(f"DEBUG - Inquiry user_ids found: {inquiry_user_ids}")
        
        # Filter for user's inquiries - try multiple potential user ID formats
        user_inquiries = []
        for inq in all_inquiries:
            inq_user_id = inq.get("user_id", "")
            # Try exact match first
            if inq_user_id == user_id:
                user_inquiries.append(inq)
            # Try with demo_ prefix
            elif inq_user_id == f"demo_{user_id}":
                user_inquiries.append(inq)
            # Try removing demo_ prefix if our user_id has it
            elif user_id.startswith("demo_") and inq_user_id == user_id.replace("demo_", ""):
                user_inquiries.append(inq)
            # Try the base user part (e.g., user_001 matches demo_user_001)
            elif inq_user_id.endswith(user_id.split("_")[-1]) or user_id.endswith(inq_user_id.split("_")[-1]):
                user_inquiries.append(inq)
        
        # Debug: Show user inquiries
        print(f"DEBUG - User {user_id} has {len(user_inquiries)} inquiries for this event")
        if user_inquiries:
            for inq in user_inquiries:
                print(f"DEBUG - Found matching inquiry: {inq.get('subject', 'No subject')} (status: {inq.get('status', 'Unknown')})")
        
        # Count editable inquiries (OPEN or ACKNOWLEDGED status)
        editable_inquiries = [inq for inq in user_inquiries 
                            if inq.get("status", "").upper() in ["OPEN", "ACKNOWLEDGED"]]
        
        result = {
            "has_inquiries": len(user_inquiries) > 0,
            "total_count": len(user_inquiries),
            "editable_count": len(editable_inquiries),
            "all_inquiries": user_inquiries,
            "editable_inquiries": editable_inquiries
        }
        
        # Debug: Show final result
        print(f"DEBUG - Final inquiry status for event {event_data.get('event_id', 'unknown')}: {result}")
        
        return result
        
    except Exception as e:
        print(f"DEBUG - Error getting inquiry status: {str(e)}")
        # Return default status if anything fails
        return {
            "has_inquiries": False,
            "total_count": 0,
            "editable_count": 0,
            "all_inquiries": [],
            "editable_inquiries": []
        }

def show_dashboard_metrics_and_events():
    """Display dashboard metrics and events list"""
    if not st.session_state.dashboard_events:
        st.info("📊 No events to display")
        return
    
    # Debug: Show current user_id
    st.write(f"**Debug - Current User ID:** `{st.session_state.user_id}`")
    
    # Dashboard metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📅 Total Events", len(st.session_state.dashboard_events))
    with col2:
        dividend_count = len([e for e in st.session_state.dashboard_events 
                            if e.get('event_type') == 'dividend'])
        st.metric("💰 Dividends", dividend_count)
    with col3:
        split_count = len([e for e in st.session_state.dashboard_events 
                         if e.get('event_type') == 'stock_split'])
        st.metric("📈 Stock Splits", split_count)
    with col4:
        # Count total inquiries across all events from embedded data
        total_inquiries = 0
        for event in st.session_state.dashboard_events:
            event_inquiries = event.get('inquiries', [])
            total_inquiries += len(event_inquiries)
        st.metric("❓ Total Inquiries", total_inquiries)

    # Events list
    st.markdown("---")
    st.subheader("📋 Upcoming Corporate Actions")
    
    # Add a debug section to show inquiry information
    if st.checkbox("🔍 Debug: Show Inquiry Details"):
        st.write("**Debug Information:**")
        for i, event in enumerate(st.session_state.dashboard_events[:3]):  # Show first 3 for debugging
            with st.expander(f"Debug Event {i}: {event.get('symbol', 'Unknown')}"):
                st.write("**Event Data:**")
                st.json(event)
                
                # Get user inquiry status using embedded data
                user_status = get_user_inquiry_status(event, st.session_state.user_id)
                
                st.write("**User Inquiry Status:**")
                st.json(user_status)
    
    for i, event in enumerate(st.session_state.dashboard_events[:10]):  # Show top 10
        with st.expander(
            f"🎯 **{event.get('symbol', 'Unknown')}** - {event.get('event_type', 'Unknown').replace('_', ' ').title()} "
            f"({event.get('ex_date', event.get('effective_date', 'TBD'))})", 
            expanded=i < 3
        ):
            # Event details
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Company:** {event.get('company_name', 'Unknown')}")
                st.write(f"**Type:** {event.get('event_type', 'Unknown').replace('_', ' ').title()}")
                st.write(f"**Status:** {event.get('status', 'Unknown').title()}")
                st.write(f"**Description:** {event.get('description', 'No description available')}")
                
                # Show dates
                if event.get('ex_date'):
                    st.write(f"**Ex-Date:** {event.get('ex_date')}")
                if event.get('amount'):
                    st.write(f"**Amount:** {event.get('amount')}")
                if event.get('ratio'):
                    st.write(f"**Ratio:** {event.get('ratio')}")
                    
                # Debug: Show raw event inquiries if they exist
                if event.get('inquiries'):
                    st.write(f"**Raw Event Inquiries:** {len(event.get('inquiries', []))}")
                    for inquiry in event.get('inquiries', []):
                        st.write(f"  - {inquiry.get('subject', 'No subject')} ({inquiry.get('status', 'Unknown')}) - User: `{inquiry.get('user_id', 'Unknown')}`")
            
            with col2:
                # Get user's inquiry status for this event using embedded data
                user_status = get_user_inquiry_status(event, st.session_state.user_id)
                
                has_inquiries = user_status.get("has_inquiries", False)
                open_inquiries_count = user_status.get("editable_count", 0)
                total_inquiries_count = user_status.get("total_count", 0)
                
                # Debug: Show inquiry counts
                st.write(f"**Debug:** Has inquiries: {has_inquiries}, Open: {open_inquiries_count}, Total: {total_inquiries_count}")
                
                # Show inquiry status
                if has_inquiries:
                    if open_inquiries_count > 0:
                        st.info(f"📝 {open_inquiries_count} open, {total_inquiries_count} total inquiries")
                    else:
                        st.success(f"✅ {total_inquiries_count} closed inquiries")
                else:
                    st.success("✅ No inquiries yet")
                
                # Inquiry management buttons with smart enable/disable logic
                st.markdown("**🔧 Inquiry Actions**")
                
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

def show_inquiry_modal_create(event_data: Dict[str, Any]):
    """Create inquiry using MCP tools directly"""
    st.subheader(f"🆕 Create New Inquiry - {event_data.get('company_name', 'N/A')}")
    
    with st.form(f"create_inquiry_{event_data.get('event_id', 'unknown')}"):
        st.info(f"**Event:** {event_data.get('description', 'N/A')}")
        
        col1, col2 = st.columns(2)
        with col1:
            subject = st.text_input("Subject", placeholder="Brief description of your inquiry")
            priority = st.selectbox("Priority", ["LOW", "MEDIUM", "HIGH", "URGENT"], index=1)
        
        with col2:
            st.text_input("Your Name", value=st.session_state.user_name, disabled=True)
            st.text_input("Organization", value="Demo Organization", disabled=True)
        
        description = st.text_area("Detailed Description", height=100, 
                                 placeholder="Provide detailed information about your inquiry...")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.form_submit_button("Create Inquiry", type="primary"):
                if subject and description:
                    with st.spinner("🔧 Creating inquiry via MCP tools..."):
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        try:
                            # Call create_inquiry_tool using MCP directly
                            inquiry_response = loop.run_until_complete(
                                agent_manager._execute_mcp_tool_direct(
                                    server_url=MCP_SERVERS["rag"],
                                    tool_name="create_inquiry_tool",
                                    arguments={
                                        "event_id": event_data.get('event_id'),
                                        "user_id": st.session_state.user_id,
                                        "user_name": st.session_state.user_name,
                                        "organization": "Demo Organization",
                                        "subject": subject,
                                        "description": description,
                                        "priority": priority
                                    }
                                )
                            )
                            
                            # Parse the JSON response
                            import json
                            result = json.loads(inquiry_response)
                            
                            if result.get("success"):
                                st.success("✅ Inquiry created successfully!")
                                # Close modal and return to dashboard
                                st.session_state.selected_event_for_inquiry = None
                                if 'inquiry_modal_type' in st.session_state:
                                    del st.session_state.inquiry_modal_type
                                st.balloons()
                                st.rerun()
                            else:
                                st.error(f"❌ Failed to create inquiry: {result.get('error', 'Unknown error')}")
                                
                        except Exception as e:
                            st.error(f"❌ Error creating inquiry: {str(e)}")
                        finally:
                            loop.close()
                else:
                    st.error("Please fill in both subject and description")
        
        with col3:
            if st.form_submit_button("Cancel"):
                st.session_state.selected_event_for_inquiry = None
                if 'inquiry_modal_type' in st.session_state:
                    del st.session_state.inquiry_modal_type
                st.rerun()

def show_inquiry_modal_view(event_data: Dict[str, Any]):
    """View inquiries using MCP tools directly"""
    st.subheader(f"👁️ View Inquiries - {event_data.get('company_name', 'N/A')}")
    
    with st.spinner("🔧 Fetching inquiries via MCP tools..."):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Call get_inquiries_tool using MCP directly
            inquiries_response = loop.run_until_complete(
                agent_manager._execute_mcp_tool_direct(
                    server_url=MCP_SERVERS["rag"],
                    tool_name="get_inquiries_tool",
                    arguments={"event_id": event_data.get('event_id')}
                )
            )
            
            # Parse the JSON response
            import json
            result = json.loads(inquiries_response)
            inquiries = result.get("inquiries", [])
            
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
                
        except Exception as e:
            st.error(f"❌ Error fetching inquiries: {str(e)}")
        finally:
            loop.close()
    
    if st.button("Close View", type="primary"):
        st.session_state.selected_event_for_inquiry = None
        if 'inquiry_modal_type' in st.session_state:
            del st.session_state.inquiry_modal_type
        st.rerun()

def show_inquiry_modal_edit(event_data: Dict[str, Any]):
    """Edit inquiries using MCP tools directly"""
    st.subheader(f"✏️ Edit Inquiries - {event_data.get('company_name', 'N/A')}")
    
    # Get user's inquiries for this event
    with st.spinner("🔧 Loading your inquiries..."):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Call get_inquiries_tool and filter for user
            inquiries_response = loop.run_until_complete(
                agent_manager._execute_mcp_tool_direct(
                    server_url=MCP_SERVERS["rag"],
                    tool_name="get_inquiries_tool",
                    arguments={"event_id": event_data.get('event_id')}
                )
            )
            
            # Parse and filter for user's inquiries
            import json
            result = json.loads(inquiries_response)
            all_inquiries = result.get("inquiries", [])
            user_inquiries = [inq for inq in all_inquiries if inq.get("user_id") == st.session_state.user_id]
            
        except Exception as e:
            st.error(f"❌ Error loading inquiries: {str(e)}")
            user_inquiries = []
        finally:
            loop.close()
    
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
                        st.text_input("Your Name", value=st.session_state.user_name, disabled=True)
                        st.text_input("Organization", value="Demo Organization", disabled=True)
                    
                    new_description = st.text_area("Description", 
                                                  value=selected_inquiry.get('description', ''),
                                                  height=100)
                    
                    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
                    with col1:
                        if st.form_submit_button("Update Inquiry", type="primary"):
                            if new_subject and new_description:
                                with st.spinner("🔧 Updating inquiry..."):
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    
                                    try:
                                        # Use direct MCP tool call to update inquiry
                                        inquiry_response = loop.run_until_complete(
                                            agent_manager._execute_mcp_tool_direct(
                                                server_url=MCP_SERVERS["rag"],
                                                tool_name="update_inquiry_tool",
                                                arguments={
                                                    "inquiry_id": selected_inquiry['inquiry_id'],
                                                    "subject": new_subject,
                                                    "description": new_description,
                                                    "priority": new_priority
                                                }
                                            )
                                        )
                                        
                                        # Parse the JSON response
                                        import json
                                        result = json.loads(inquiry_response)
                                        
                                        if result.get("success"):
                                            st.success("✅ Inquiry updated successfully!")
                                            
                                            # Close modal and return to dashboard
                                            st.session_state.selected_event_for_inquiry = None
                                            if 'inquiry_modal_type' in st.session_state:
                                                del st.session_state.inquiry_modal_type
                                            st.balloons()
                                            st.rerun()
                                        else:
                                            st.error(f"❌ Failed to update inquiry: {result.get('error', 'Unknown error')}")
                                        
                                    except Exception as e:
                                        st.error(f"❌ Error updating inquiry: {str(e)}")
                                    finally:
                                        loop.close()
                            else:
                                st.error("Please fill in both subject and description")
                    
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

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 50%, #06b6d4 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-container {
        background: #f8fafc;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #3b82f6;
        margin: 0.5rem 0;
    }
    
    .status-confirmed { 
        background-color: #d4edda; 
        color: #155724; 
        padding: 0.25rem 0.5rem; 
        border-radius: 4px; 
        font-weight: bold;
    }
    .status-announced { 
        background-color: #fff3cd; 
        color: #856404; 
        padding: 0.25rem 0.5rem; 
        border-radius: 4px; 
        font-weight: bold;
    }
    .status-pending { 
        background-color: #f8d7da; 
        color: #721c24; 
        padding: 0.25rem 0.5rem; 
        border-radius: 4px; 
        font-weight: bold;
    }
    .status-processed { 
        background-color: #d1ecf1; 
        color: #0c5460; 
        padding: 0.25rem 0.5rem; 
        border-radius: 4px; 
        font-weight: bold;
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
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown("""
<div class="main-header">
    <h1>🤖 Corporate Actions Dashboard</h1>
    <h3>Powered by Azure AI Agent Service + MCP Integration</h3>
    <p>AI-driven insights with real-time corporate actions data and advanced analytics</p>
</div>
""", unsafe_allow_html=True)

# Sidebar for navigation and settings
st.sidebar.markdown("## 🎛️ Navigation")

# Initialize session state for chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "agent_initialized" not in st.session_state:
    st.session_state.agent_initialized = False

if "existing_agent_checked" not in st.session_state:
    st.session_state.existing_agent_checked = False

if "existing_agent_found" not in st.session_state:
    st.session_state.existing_agent_found = False

# Check for existing agent on first load
if not st.session_state.existing_agent_checked:
    with st.spinner("🔍 Checking for existing Azure AI Agent..."):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        st.session_state.existing_agent_found = loop.run_until_complete(agent_manager.check_existing_agent())
        loop.close()
        st.session_state.existing_agent_checked = True
        
        # If agent exists, mark as initialized
        if st.session_state.existing_agent_found:
            st.session_state.agent_initialized = True

# Sidebar - Initialize Agent
with st.sidebar:
    st.markdown("### 🤖 Azure AI Agent Status")
    
    if not st.session_state.agent_initialized:
        # Only show initialize button if no existing agent found
        if not st.session_state.existing_agent_found:
            if st.button("🚀 Initialize Azure AI Agent", type="primary"):
                with st.spinner("Initializing Azure AI Agent with MCP tools..."):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    success = loop.run_until_complete(agent_manager.initialize())
                    loop.close()
                    
                    if success:
                        st.session_state.agent_initialized = True
                        st.success("✅ Agent initialized successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to initialize agent")
        else:
            # Show activate button for existing agent
            if st.button("🔗 Connect to Existing Agent", type="primary"):
                with st.spinner("Connecting to existing Azure AI Agent..."):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    success = loop.run_until_complete(agent_manager.initialize())
                    loop.close()
                    
                    if success:
                        st.session_state.agent_initialized = True
                        st.success("✅ Connected to existing agent!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to connect to agent")
    else:
        # Agent is initialized - show status and reinitialize option
        if st.session_state.existing_agent_found:
            st.success("✅ Azure AI Agent Active (Existing Agent)")
        else:
            st.success("✅ Azure AI Agent Active (New Agent)")
        
        if st.button("🔄 Reinitialize Agent"):
            # Reset all agent-related session state
            st.session_state.agent_initialized = False
            st.session_state.existing_agent_checked = False
            st.session_state.existing_agent_found = False
            st.rerun()

# Page selection
page = st.sidebar.selectbox(
    "Choose a page:",
    ["🏠 Dashboard", "🔍 Search Events", "💬 AI Assistant", "📊 Analytics", "⚙️ Settings"]
)

# Dashboard page
if page == "🏠 Dashboard":
        st.header("📊 Corporate Actions Dashboard")
        
        # Initialize session state for dashboard
        if "user_subscriptions" not in st.session_state:
            st.session_state.user_subscriptions = []
        if "user_id" not in st.session_state:
            st.session_state.user_id = "user_001"
        if "user_name" not in st.session_state:
            st.session_state.user_name = "Demo User"
        if "subscriptions_loaded" not in st.session_state:
            st.session_state.subscriptions_loaded = False
        if "dashboard_data_loaded" not in st.session_state:
            st.session_state.dashboard_data_loaded = False
        if "dashboard_events" not in st.session_state:
            st.session_state.dashboard_events = []
        if "selected_event_for_inquiry" not in st.session_state:
            st.session_state.selected_event_for_inquiry = None
        if "inquiry_modal_type" not in st.session_state:
            st.session_state.inquiry_modal_type = None
        
        # Synchronize agent initialization status
        if st.session_state.agent_initialized and not agent_manager.is_initialized:
            st.warning("🔄 Agent status out of sync. Please reinitialize the agent from the sidebar.")
            st.session_state.agent_initialized = False
        
        # Handle inquiry modal display first
        if st.session_state.selected_event_for_inquiry:
            event_data = st.session_state.selected_event_for_inquiry
            modal_type = st.session_state.get('inquiry_modal_type', 'create')
            
            if modal_type == 'create':
                show_inquiry_modal_create(event_data)
            elif modal_type == 'view':
                show_inquiry_modal_view(event_data)
            elif modal_type == 'edit':
                show_inquiry_modal_edit(event_data)
        else:

            if not st.session_state.agent_initialized:
                st.warning("⚠️ Please initialize the Azure AI Agent from the sidebar to access dashboard functionality.")
                st.info("📊 Using sample data for demonstration")
                show_sample_dashboard_overview()
            else:
                # Step 1: Load user subscriptions using MCP tools directly
                if not st.session_state.subscriptions_loaded:
                    with st.spinner("🤖 Retrieving your subscriptions from CosmosDB..."):
                        try:
                            # Use the agent manager's MCP tool execution method
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                            try:
                                # Call get_subscription_tool using the MCP protocol
                                subscription_response = loop.run_until_complete(
                                    agent_manager._execute_mcp_tool_direct(
                                        server_url=MCP_SERVERS["rag"],
                                        tool_name="get_subscription_tool",
                                        arguments={"user_id": st.session_state.user_id}
                                    )
                                )
                                
                                # Debug: Show the raw response
                                #st.write("**Debug - Subscription Response:**")
                                #st.text(subscription_response)
                                
                                # Parse the JSON response
                                import json
                                subscription_data = json.loads(subscription_response)
                                
                                # Extract subscription information
                                subscription = subscription_data.get("subscription")
                                if subscription and subscription.get("symbols"):
                                    symbols = subscription.get("symbols", [])
                                    if symbols:
                                        st.session_state.user_subscriptions = symbols
                                        st.success(f"✅ Found subscriptions: {', '.join(symbols)}")
                                    else:
                                        st.info("📝 No symbols found in subscription")
                                        # Provide fallback option
                                        if st.button("🔧 Use Test Subscriptions"):
                                            st.session_state.user_subscriptions = ["AAPL", "MSFT", "TSLA"]
                                            st.success("✅ Using test subscriptions: AAPL, MSFT, TSLA")
                                else:
                                    st.info("📝 No existing subscriptions found")
                                    # Provide fallback option
                                    if st.button("🔧 Use Test Subscriptions"):
                                        st.session_state.user_subscriptions = ["AAPL", "MSFT", "TSLA"]
                                        st.success("✅ Using test subscriptions: AAPL, MSFT, TSLA")
                                        
                            except json.JSONDecodeError as e:
                                st.error(f"❌ JSON parsing error: {str(e)}")
                                st.text(f"Raw response: {subscription_response}")
                                # Provide fallback option
                                if st.button("🔧 Use Test Subscriptions"):
                                    st.session_state.user_subscriptions = ["AAPL", "MSFT", "TSLA"]
                                    st.success("✅ Using test subscriptions: AAPL, MSFT, TSLA")
                            except Exception as tool_error:
                                st.error(f"❌ MCP Tool Error: {str(tool_error)}")
                                # Provide fallback option
                                if st.button("🔧 Use Test Subscriptions"):
                                    st.session_state.user_subscriptions = ["AAPL", "MSFT", "TSLA"]
                                    st.success("✅ Using test subscriptions: AAPL, MSFT, TSLA")
                            finally:
                                loop.close()
                                
                        except Exception as e:
                            st.error(f"❌ Error loading subscriptions: {str(e)}")
                            # Provide fallback option
                            if st.button("🔧 Use Test Subscriptions"):
                                st.session_state.user_subscriptions = ["AAPL", "MSFT", "TSLA"]
                                st.success("✅ Using test subscriptions: AAPL, MSFT, TSLA")
                        finally:
                            st.session_state.subscriptions_loaded = True
                
                # Step 2: Load dashboard data (corporate actions) using MCP tools
                if not st.session_state.dashboard_data_loaded and st.session_state.user_subscriptions:
                    with st.spinner("🤖 Retrieving corporate actions data..."):
                        try:
                            # Use the agent manager's MCP tool execution method
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                            try:
                                # Call get_upcoming_events_tool using the MCP protocol
                                events_response = loop.run_until_complete(
                                    agent_manager._execute_mcp_tool_direct(
                                        server_url=MCP_SERVERS["rag"],
                                        tool_name="get_upcoming_events_tool",
                                        arguments={"user_id": st.session_state.user_id, "days_ahead": 30}
                                    )
                                )
                                
                                # Debug: Show the raw response
                                #st.write("**Debug - Events Response:**")
                                #st.text(events_response)
                                
                                # Parse the JSON response
                                import json
                                events_data = json.loads(events_response)
                                
                                # Extract events information
                                upcoming_events = events_data.get("upcoming_events", [])
                                if upcoming_events:
                                    st.session_state.dashboard_events = upcoming_events
                                    st.success(f"✅ Found {len(upcoming_events)} upcoming events")
                                else:
                                    st.info("📝 No upcoming events found, using sample data")
                                    st.session_state.dashboard_events = get_sample_upcoming_events(st.session_state.user_subscriptions)
                                    
                            except json.JSONDecodeError as e:
                                st.error(f"❌ JSON parsing error: {str(e)}")
                                st.text(f"Raw response: {events_response}")
                                st.session_state.dashboard_events = get_sample_upcoming_events(st.session_state.user_subscriptions)
                            except Exception as tool_error:
                                st.error(f"❌ MCP Tool Error: {str(tool_error)}")
                                st.session_state.dashboard_events = get_sample_upcoming_events(st.session_state.user_subscriptions)
                            finally:
                                loop.close()
                                
                        except Exception as e:
                            st.error(f"❌ Error loading events: {str(e)}")
                            st.session_state.dashboard_events = get_sample_upcoming_events(st.session_state.user_subscriptions)
                        finally:
                            st.session_state.dashboard_data_loaded = True

                # Subscription Management Section
                st.markdown("---")
                st.subheader("📈 My Subscriptions")
                
                # Show current subscriptions
                if st.session_state.user_subscriptions:
                    st.write("**Current Subscriptions:**")
                    subscription_cols = st.columns(min(len(st.session_state.user_subscriptions), 5))
                    for i, symbol in enumerate(st.session_state.user_subscriptions):
                        with subscription_cols[i % 5]:
                            if st.button(f"❌ {symbol}", key=f"unsub_{symbol}"):
                                # Remove subscription using AI Agent
                                with st.spinner(f"🤖 AI Agent removing {symbol}..."):
                                    remaining_symbols = [s for s in st.session_state.user_subscriptions if s != symbol]
                                    
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    
                                    remove_request = f"""
                                    Please update subscription for user ID {st.session_state.user_id}.
                                    Remove {symbol} from subscription and save to CosmosDB.
                                    New symbols list: {', '.join(remaining_symbols) if remaining_symbols else 'None'}
                                    """
                                    
                                    try:
                                        response = loop.run_until_complete(
                                            agent_manager.send_message(remove_request)
                                        )
                                        if response.get("success"):
                                            st.session_state.user_subscriptions = remaining_symbols
                                            st.session_state.dashboard_data_loaded = False  # Refresh data
                                            st.success(f"🤖 Removed {symbol}")
                                            st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Error: {str(e)}")
                                    finally:
                                        loop.close()
                else:
                    st.info("📝 No subscriptions yet")
                
                # Add new subscription
                col1, col2 = st.columns([3, 1])
                with col1:
                    new_symbols = st.text_input("Add Symbols", placeholder="AAPL,MSFT,GOOGL")
                with col2:
                    if st.button("➕ Subscribe"):
                        if new_symbols:
                            symbols = [s.strip().upper() for s in new_symbols.split(",") if s.strip()]
                            
                            with st.spinner("🤖 AI Agent saving subscription..."):
                                all_symbols = list(set(st.session_state.user_subscriptions + symbols))
                                
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                
                                save_request = f"""
                                Please save subscription for user:
                                - User ID: {st.session_state.user_id}
                                - User Name: {st.session_state.user_name}
                                - Symbols: {', '.join(all_symbols)}
                                - Event Types: DIVIDEND,STOCK_SPLIT,MERGER,SPIN_OFF
                                
                                Save to CosmosDB using appropriate MCP tools.
                                """
                                
                                try:
                                    response = loop.run_until_complete(
                                        agent_manager.send_message(save_request)
                                    )
                                    if response.get("success"):
                                        st.session_state.user_subscriptions = all_symbols
                                        st.session_state.dashboard_data_loaded = False  # Refresh data
                                        st.success(f"✅ Subscribed to: {', '.join(symbols)}")
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Error: {str(e)}")
                                finally:
                                    loop.close()
                
                st.markdown("---")
                
                # Step 2: Get corporate actions for subscribed symbols using AI Agent
                st.subheader("🗓️ Upcoming Corporate Actions (Next 7 Days)")
                
                if not st.session_state.dashboard_data_loaded:
                    with st.spinner("🤖 AI Agent analyzing corporate actions for your subscriptions..."):
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        if st.session_state.user_subscriptions:
                            actions_request = f"""
                            Please find upcoming corporate actions for user ID {st.session_state.user_id} for the next 7 days.
                            
                            User is subscribed to: {', '.join(st.session_state.user_subscriptions)}
                            
                            Tasks:
                            1. Use vector search tools to find corporate actions for these symbols
                            2. Filter for upcoming events (next 7 days)
                            3. For each event, check for existing inquiries from CosmosDB
                            4. Return structured data with event details and inquiry counts
                            
                            Focus on: dividends, stock splits, mergers, spin-offs for subscribed symbols.
                            """
                        else:
                            actions_request = """
                            Please show recent corporate actions examples to help user understand available events.
                            
                            Search for recent corporate actions (last 30 days) including:
                            1. Dividend announcements
                            2. Stock splits
                            3. Merger activities
                            4. Other corporate actions
                            
                            Show variety of companies to demonstrate subscription possibilities.
                            """
                        
                        try:
                            response = loop.run_until_complete(
                                agent_manager.send_message(actions_request)
                            )
                            
                            if response.get("success"):
                                # Display AI Agent analysis
                                st.markdown("### 🤖 AI Agent Analysis")
                                st.markdown(response.get("answer", ""))
                                
                                # Try to extract structured data for display
                                # This is simplified - in reality you'd parse more sophisticated response
                                st.session_state.dashboard_events = extract_events_from_response(response.get("answer", ""))
                                st.session_state.dashboard_data_loaded = True
                                
                            else:
                                st.error(f"❌ AI Agent failed: {response.get('error')}")
                                st.session_state.dashboard_events = get_sample_upcoming_events(st.session_state.user_subscriptions)
                                
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
                            st.session_state.dashboard_events = get_sample_upcoming_events(st.session_state.user_subscriptions)
                        finally:
                            loop.close()
                
                # Display dashboard metrics and events
                show_dashboard_metrics_and_events()
                
                # Step 3: Inquiry Management Section
                st.markdown("---")
                st.subheader("❓ Inquiry Management")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🤖 Analyze My Inquiries", type="primary"):
                        with st.spinner("🤖 AI Agent analyzing your inquiries..."):
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                            inquiry_request = f"""
                            Please analyze all inquiries for user ID {st.session_state.user_id}.
                            
                            Use CosmosDB inquiry tools to:
                            1. Count total open inquiries
                            2. Identify high priority items
                            3. Find inquiries needing attention
                            4. Summarize inquiry status distribution
                            """
                            
                            try:
                                response = loop.run_until_complete(
                                    agent_manager.send_message(inquiry_request)
                                )
                                if response.get("success"):
                                    st.markdown("### 🤖 Inquiry Analysis")
                                    st.markdown(response.get("answer", ""))
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
                            finally:
                                loop.close()
                
                with col2:
                    if st.button("🔍 Find Events Needing Attention"):
                        with st.spinner("🤖 AI Agent finding events needing attention..."):
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                            attention_request = f"""
                            Please identify corporate actions needing attention for user ID {st.session_state.user_id}.
                            
                            Look for:
                            1. Events with upcoming deadlines
                            2. New announcements for subscribed symbols: {', '.join(st.session_state.user_subscriptions)}
                            3. Events with unresolved inquiries
                            4. High-priority items
                            """
                            
                            try:
                                response = loop.run_until_complete(
                                    agent_manager.send_message(attention_request)
                                )
                                if response.get("success"):
                                    st.markdown("### 🚨 Items Requiring Attention")
                                    st.markdown(response.get("answer", ""))
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
                            finally:
                                loop.close()
# Search Events page
elif page == "🔍 Search Events":
    st.header("🔍 Advanced Event Search")
    
    with st.form("search_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            search_text = st.text_input("Search Text", placeholder="dividend, merger, Apple")
            event_type = st.selectbox("Event Type", ["", "dividend", "stock_split", "merger", "spinoff", "special_dividend"])
            company_name = st.text_input("Company Name", placeholder="Apple Inc.")
        
        with col2:
            status = st.selectbox("Status", ["", "announced", "confirmed", "processed", "cancelled", "pending"])
            date_from = st.date_input("From Date", value=date.today() - timedelta(days=30))
            date_to = st.date_input("To Date", value=date.today())
        
        limit = st.slider("Max Results", 1, 50, 10)
        submit_button = st.form_submit_button("🔍 Search with Azure AI Agent", type="primary")
    
    if submit_button:
        if st.session_state.agent_initialized:            # Use Azure AI Agent with MCP tools for search
            search_query = f"Search for corporate actions"
            if search_text:
                search_query += f" containing '{search_text}'"
            if event_type:
                search_query += f" of type '{event_type}'"
            if company_name:
                search_query += f" for company '{company_name}'"
            if status:
                search_query += f" with status '{status}'"
            search_query += f" from {date_from} to {date_to}, limit to {limit} results. Return structured data with event details."
            
            with st.spinner("🤖 Azure AI Agent searching via MCP tools..."):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Get both the AI analysis and raw MCP data
                response = loop.run_until_complete(
                    agent_manager.send_message(search_query)
                )
                
                # Also try to get raw MCP search results
                raw_mcp_data = loop.run_until_complete(
                    agent_manager._try_mcp_tools_first(search_query)
                )
                
                loop.close()
                
                if response.get("success"):
                    st.success("✅ Search completed by Azure AI Agent with MCP integration")
                    
                    # Show AI analysis
                    st.markdown("### 🤖 AI Analysis")
                    st.markdown(response["answer"])
                    
                    # Try to extract and display structured results
                    if raw_mcp_data:
                        st.markdown("### 📊 Search Results")
                        
                        # Try to parse structured data from MCP response
                        json_matches = re.findall(r'\{[^{}]*\}', raw_mcp_data)
                        search_results = []
                        
                        for match in json_matches:
                            try:
                                event_data = json.loads(match)
                                if isinstance(event_data, dict):
                                    search_results.append(event_data)
                            except:
                                continue
                        
                        if search_results:
                            # Apply client-side filtering to the results
                            filtered_results = search_results
                            
                            if event_type:
                                filtered_results = [e for e in filtered_results if e.get('event_type') == event_type]
                            if company_name:
                                filtered_results = [e for e in filtered_results if company_name.lower() in str(e.get('company_name', '')).lower()]
                            if status:
                                filtered_results = [e for e in filtered_results if e.get('status') == status]
                            
                            # Limit results
                            filtered_results = filtered_results[:limit]
                            
                            if filtered_results:
                                st.success(f"📊 Found {len(filtered_results)} matching events")
                                
                                # Display results in expandable cards
                                for i, event in enumerate(filtered_results):
                                    with st.expander(f"📈 {event.get('event_type', 'Unknown').replace('_', ' ').title()} - {event.get('company_name', 'Unknown Company')}"):
                                        col1, col2 = st.columns(2)
                                        
                                        with col1:
                                            st.write(f"**Event ID:** {event.get('event_id', 'N/A')}")
                                            st.write(f"**Symbol:** {event.get('symbol', 'N/A')}")
                                            st.write(f"**Status:** {event.get('status', 'N/A')}")
                                            if event.get('confidence_score'):
                                                st.write(f"**Confidence:** {event['confidence_score']:.1%}")
                                        
                                        with col2:
                                            st.write(f"**Description:** {event.get('description', 'N/A')}")
                                            st.write(f"**Announced:** {event.get('announcement_date', 'N/A')}")
                                            if event.get('market_impact'):
                                                st.write(f"**Market Impact:** {event['market_impact']}")
                                            if event.get('data_source'):
                                                st.write(f"**Source:** {event['data_source']}")
                                
                                # Show summary statistics
                                st.markdown("### 📈 Search Summary")
                                col1, col2, col3, col4 = st.columns(4)
                                
                                with col1:
                                    st.metric("Total Results", len(filtered_results))
                                with col2:
                                    confirmed = len([e for e in filtered_results if e.get('status') == 'confirmed'])
                                    st.metric("Confirmed", confirmed)
                                with col3:
                                    event_types = len(set(e.get('event_type') for e in filtered_results))
                                    st.metric("Event Types", event_types)
                                with col4:
                                    companies = len(set(e.get('company_name') for e in filtered_results))
                                    st.metric("Companies", companies)
                            else:
                                st.info("📭 No events found matching your specific criteria")
                        else:
                            st.info("💡 MCP returned text results rather than structured data")
                            with st.expander("📄 View Raw MCP Response"):
                                st.text(raw_mcp_data)
                    
                    if response.get("requires_visualization"):
                        st.info("💡 This search would benefit from visualizations. Check the Analytics page!")
                        
                else:
                    st.error(f"❌ Search failed: {response.get('error', 'Unknown error')}")
        else:
            # Fallback to sample data filtering
            st.warning("🔧 Azure AI Agent not initialized. Using sample data.")
            sample_events = get_sample_events()
            
            # Apply basic filtering to sample data
            filtered_events = sample_events
            if event_type:
                filtered_events = [e for e in filtered_events if e['event_type'] == event_type]
            if company_name:
                filtered_events = [e for e in filtered_events if company_name.lower() in e['company_name'].lower()]
            if status:
                filtered_events = [e for e in filtered_events if e['status'] == status]
            
            if filtered_events:
                st.success(f"📊 Found {len(filtered_events)} events (sample data)")
                
                # Display results
                for event in filtered_events:
                    with st.expander(f"📈 {event['event_type'].replace('_', ' ').title()} - {event['company_name']}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Event ID:** {event['event_id']}")
                            st.write(f"**Symbol:** {event['symbol']}")
                            st.write(f"**Status:** {event['status']}")
                        
                        with col2:
                            st.write(f"**Description:** {event['description']}")
                            st.write(f"**Announced:** {event['announcement_date']}")
            else:
                st.info("📭 No events found matching your criteria")

# AI Assistant page
elif page == "💬 AI Assistant":
    st.header("🤖 Azure AI Corporate Actions Assistant")
    
    # Chat interface
    if st.session_state.agent_initialized:
        st.success("✅ Azure AI Agent is ready to help!")
          # Display chat history
        for i, msg in enumerate(st.session_state.chat_history):
            if msg["role"] == "user":
                st.markdown(f"""
                <div class="chat-message user-message">
                    <strong>👤 You:</strong>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(msg["content"])
            else:
                parsed = ast.literal_eval(msg["content"]) if isinstance(msg["content"], str) else msg["content"]
                st.markdown(f"""
                <div class="chat-message assistant-message">
                    <strong>🤖 AI Assistant:</strong>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(parsed["value"])

        # Chat input
        user_input = st.chat_input("Ask about corporate actions, request analysis, or search for specific events...")
        
        if user_input:
            # Add user message to history
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            
            # Get AI response
            with st.spinner("🤖 Azure AI Agent thinking..."):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                response = loop.run_until_complete(
                    agent_manager.send_message(user_input, st.session_state.chat_history)
                )
                loop.close()
                
                if response.get("success"):
                    # Add assistant response to history
                    st.session_state.chat_history.append({
                        "role": "assistant", 
                        "content": response["answer"]
                    })
                    
                    # Show confidence score if available
                    if response.get("confidence_score"):
                        confidence = response["confidence_score"]
                        if confidence > 0.8:
                            st.success(f"✅ High confidence response ({confidence:.1%})")
                        elif confidence > 0.6:
                            st.warning(f"⚠️ Medium confidence response ({confidence:.1%})")
                        else:
                            st.info(f"💡 Lower confidence response ({confidence:.1%}) - consider refining your question")
                    
                    st.rerun()
                else:
                    st.error(f"❌ Error: {response.get('error', 'Unknown error')}")
        
        # Clear chat button
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()
            
    else:
        st.warning("⚠️ Please initialize the Azure AI Agent from the sidebar to use the chat assistant.")
        
        # Sample questions
        st.markdown("### 💡 Sample Questions You Can Ask:")
        sample_questions = [
            "What are the recent dividend announcements?",
            "Show me all stock splits from the last month",
            "Which companies have the most corporate actions?",
            "Create a visualization of event status distribution",
            "Analyze merger activity in the technology sector",
            "What are the upcoming ex-dividend dates?",
            "Compare dividend yields across different companies",
            "Show me corporate actions that need attention"
        ]
        
        for question in sample_questions:
            if st.button(f"📝 {question}", key=f"sample_{question}"):
                if st.session_state.agent_initialized:
                    st.session_state.chat_history.append({"role": "user", "content": question})
                    st.rerun()
                else:
                    st.warning("Please initialize the Azure AI Agent first!")

# Analytics page
elif page == "📊 Analytics":
    st.header("📊 Advanced Analytics Dashboard")
    
    # Get the same dynamic data as dashboard
    analytics_data = []
    data_source = "Sample Data"
    
    if st.session_state.agent_initialized:
        # Fetch analytics data via MCP tools
        with st.spinner("🔄 Fetching analytics data from MCP servers..."):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                mcp_data = loop.run_until_complete(
                    agent_manager._try_mcp_tools_first("Get comprehensive corporate actions data for advanced analytics and trend analysis")
                )
                
                if mcp_data:
                    # Try to parse structured data
                    json_matches = re.findall(r'\{[^{}]*\}', mcp_data)
                    parsed_events = []
                    
                    for match in json_matches:
                        try:
                            event_data = json.loads(match)
                            if isinstance(event_data, dict) and 'event_type' in event_data:
                                parsed_events.append(event_data)
                        except:
                            continue
                    
                    if parsed_events:
                        analytics_data = normalize_event_data(parsed_events)
                        data_source = "Live MCP Data"
                    else:
                        analytics_data = get_enhanced_sample_events_from_mcp(mcp_data)
                        data_source = "MCP-Enhanced Data"
                else:
                    raise Exception("No MCP data received")
                    
            except Exception as e:
                st.warning(f"⚠️ MCP analytics data fetch failed: {str(e)}. Using sample data.")
                analytics_data = get_sample_events()
                data_source = "Sample Data"
            
            loop.close()
    else:
        analytics_data = get_sample_events()
        data_source = "Sample Data"
    
    # Show data source and refresh option
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info(f"📊 **Analytics Data Source**: {data_source} | **Events**: {len(analytics_data)} | **Updated**: {datetime.now().strftime('%H:%M:%S')}")
    with col2:
        if st.button("🔄 Refresh Data", type="secondary"):
            st.rerun()
    
    # Get data
    df = pd.DataFrame(analytics_data)
    
    # Key metrics
    st.subheader("📈 Key Performance Indicators")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_events = len(df)
        st.metric("📋 Total Events", total_events)
    
    with col2:
        confirmed_pct = len(df[df['status'] == 'confirmed']) / total_events * 100
        st.metric("✅ Confirmed Rate", f"{confirmed_pct:.1f}%")
    
    with col3:
        unique_companies = df['company_name'].nunique()
        st.metric("🏢 Unique Companies", unique_companies)
    
    with col4:
        avg_events_per_company = total_events / unique_companies
        st.metric("📊 Avg Events/Company", f"{avg_events_per_company:.1f}")
    
    # Advanced visualizations
    st.subheader("📊 Advanced Visualizations")
    
    # Multi-chart layout
    col1, col2 = st.columns(2)
    
    with col1:        # Timeline visualization
        st.markdown("#### 📅 Timeline Analysis")
        df['announcement_date'] = pd.to_datetime(df['announcement_date'], errors='coerce')
        
        # Filter out rows with invalid dates (NaT)
        valid_dates_df = df.dropna(subset=['announcement_date'])
        
        if len(valid_dates_df) > 0:
            timeline_data = valid_dates_df.groupby(['announcement_date', 'event_type']).size().reset_index(name='count')
            
            fig_timeline = px.line(
                timeline_data, 
                x='announcement_date', 
                y='count', 
                color='event_type',
                title="Corporate Actions Timeline",
                markers=True
            )
            fig_timeline.update_layout(xaxis_title="Date", yaxis_title="Number of Events")
            st.plotly_chart(fig_timeline, use_container_width=True)
        else:
            st.warning("⚠️ No valid dates found for timeline visualization")
    
    with col2:
        # Company activity heatmap
        st.markdown("#### 🏢 Company Activity Matrix")
        company_type_matrix = pd.crosstab(df['company_name'], df['event_type'])
        
        fig_heatmap = px.imshow(
            company_type_matrix.values,
            x=company_type_matrix.columns,
            y=company_type_matrix.index,
            title="Company vs Event Type Matrix",
            color_continuous_scale="viridis"
        )
        fig_heatmap.update_layout(
            xaxis_title="Event Type",
            yaxis_title="Company"
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)
    
    # Interactive filters
    st.subheader("🎛️ Interactive Analysis")
    
    # Add filter controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_companies = st.multiselect(
            "Select Companies:",
            options=df['company_name'].unique(),
            default=df['company_name'].unique()[:3]
        )
    
    with col2:
        selected_types = st.multiselect(
            "Select Event Types:",
            options=df['event_type'].unique(),
            default=df['event_type'].unique()
        )
    
    with col3:
        selected_statuses = st.multiselect(
            "Select Statuses:",
            options=df['status'].unique(),
            default=df['status'].unique()
        )
    
    # Filter data
    filtered_df = df[
        (df['company_name'].isin(selected_companies)) &
        (df['event_type'].isin(selected_types)) &
        (df['status'].isin(selected_statuses))
    ]
    
    if len(filtered_df) > 0:
        # Filtered results visualization
        col1, col2 = st.columns(2)
        
        with col1:
            # Filtered status distribution
            filtered_status_counts = filtered_df['status'].value_counts()
            fig_filtered_pie = px.pie(
                values=filtered_status_counts.values,
                names=filtered_status_counts.index,
                title="Filtered Events - Status Distribution"
            )
            st.plotly_chart(fig_filtered_pie, use_container_width=True)
        
        with col2:
            # Filtered company activity
            filtered_company_counts = filtered_df['company_name'].value_counts()
            fig_filtered_bar = px.bar(
                x=filtered_company_counts.values,
                y=filtered_company_counts.index,
                orientation='h',
                title="Filtered Events - Company Activity"
            )
            st.plotly_chart(fig_filtered_bar, use_container_width=True)
        
        # Filtered data table
        st.subheader("📋 Filtered Results")
        st.dataframe(filtered_df, use_container_width=True)
    else:
        st.warning("⚠️ No data matches the current filter criteria")
    
    # AI-generated insights
    if st.session_state.agent_initialized:
        st.subheader("🤖 AI-Generated Insights")
        if st.button("🧠 Generate AI Analysis of Current Data", type="primary"):
            analysis_prompt = f"""
            Analyze the following corporate actions data and provide insights:
            - Total events: {len(filtered_df)}
            - Companies: {', '.join(selected_companies)}
            - Event types: {', '.join(selected_types)}
            - Statuses: {', '.join(selected_statuses)}
            
            Please provide:
            1. Key trends and patterns
            2. Risk assessments
            3. Investment implications
            4. Recommendations for further analysis            """
            
            with st.spinner("🤖 Azure AI Agent analyzing data..."):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                response = loop.run_until_complete(
                    agent_manager.send_message(analysis_prompt)
                )
                loop.close()
                
                if response.get("success"):
                    st.markdown("#### 🧠 AI Analysis Results")
                    parsed = ast.literal_eval(response["answer"]) if isinstance(response["answer"], str) else response["answer"]
                    # Verify if we have "value" key in parsed
                    if "value" not in parsed:
                        st.markdown(parsed)
                    else:
                        st.markdown(parsed["value"])
                else:
                    st.error(f"❌ Analysis failed: {response.get('error', 'Unknown error')}")

# Settings page
elif page == "⚙️ Settings":
    st.header("⚙️ System Configuration")
    
    # Azure AI Configuration
    st.subheader("🤖 Azure AI Agent Service")
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_project_url = st.text_input(
            "Azure AI Project URL:",
            value=AZURE_AI_CONFIG["project_url"],
            type="password"
        )
        
        new_api_key = st.text_input(
            "Azure AI API Key:",
            value=AZURE_AI_CONFIG["api_key"],
            type="password"
        )
    
    with col2:
        new_model = st.selectbox(
            "Model Deployment:",
            ["gpt-4o", "gpt-4", "gpt-35-turbo"],
            index=0 if AZURE_AI_CONFIG["model_deployment"] == "gpt-4o" else 1
        )
        
        agent_name = st.text_input(
            "Agent Name:",
            value=AZURE_AI_CONFIG["agent_name"]
        )
    
    if st.button("💾 Update Azure AI Configuration"):
        AZURE_AI_CONFIG["project_url"] = new_project_url
        AZURE_AI_CONFIG["api_key"] = new_api_key
        AZURE_AI_CONFIG["model_deployment"] = new_model
        AZURE_AI_CONFIG["agent_name"] = agent_name
        st.success("✅ Configuration updated! Please reinitialize the agent.")
    
    # MCP Server Configuration
    st.subheader("🔗 MCP Server Endpoints")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        rag_url = st.text_input("RAG Server URL:", value=MCP_SERVERS["rag"])
    
    with col2:
        search_url = st.text_input("Search Server URL:", value=MCP_SERVERS["websearch"])
        
    if st.button("🔄 Update MCP Configuration"):
        MCP_SERVERS["rag"] = rag_url
        MCP_SERVERS["websearch"] = search_url
        st.success("✅ MCP configuration updated! Please reinitialize the agent.")
    
    # System Status
    st.subheader("📊 System Status")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        azure_status = "✅ Ready" if USE_AZURE_AI else "❌ Not Available"
        st.metric("Azure AI SDK", azure_status)
    
    with col2:
        mcp_status = "✅ Ready" if USE_MCP else "❌ Not Available"
        st.metric("MCP SDK", mcp_status)
    
    with col3:
        agent_status = "✅ Active" if st.session_state.agent_initialized else "⏳ Not Initialized"
        st.metric("AI Agent", agent_status)
    
    # Debug Information
    if st.checkbox("🔧 Show Debug Information"):
        st.subheader("🔍 Debug Information")
        
        debug_info = {
            "Azure AI Config": AZURE_AI_CONFIG,
            "MCP Servers": MCP_SERVERS,
            "Session State": dict(st.session_state),
            "Available Dependencies": {
                "Azure AI Projects": USE_AZURE_AI,
                "MCP Python SDK": USE_MCP
            }
        }
        
        st.json(debug_info)
        
        # Environment variables
        st.subheader("🌍 Environment Variables")
        env_vars = {
            "AZURE_AI_PROJECT_URL": os.getenv("AZURE_AI_PROJECT_URL", "Not set"),
            "AZURE_AI_API_KEY": "***" if os.getenv("AZURE_AI_API_KEY") else "Not set",
            "AZURE_AI_MODEL_DEPLOYMENT": os.getenv("AZURE_AI_MODEL_DEPLOYMENT", "Not set")
        }
        st.json(env_vars)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; margin-top: 2rem;">
    <p>🤖 <strong>Corporate Actions Dashboard</strong> - Powered by Azure AI Agent Service + MCP Integration</p>
    <p>Real-time financial intelligence with advanced AI capabilities</p>
</div>
""", unsafe_allow_html=True)

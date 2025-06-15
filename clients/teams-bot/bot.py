"""
Microsoft Teams Bot for Corporate Actions - Enhanced MCP Integration
Provides proactive notifications and interactive RAG queries using MCP protocol
"""

import asyncio
import json
import os
from datetime import datetime, time, date, timedelta
from typing import Dict, List, Any, Optional
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from botbuilder.core import (
    ActivityHandler, 
    TurnContext, 
    MessageFactory,
    CardFactory,
    ConversationState,
    UserState,
    MemoryStorage
)
from botbuilder.core.conversation_state import ConversationState
from botbuilder.schema import (
    Activity, 
    ActivityTypes, 
    ChannelAccount, 
    SuggestedActions, 
    CardAction,
    ActionTypes,
    Attachment
)
from botbuilder.adapter.teams import TeamsActivityHandler
from aiohttp import web
from aiohttp.web import Request, Response, json_response

# MCP imports for client integration
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleMCPClient:
    """Enhanced MCP client for Teams bot integration"""
    
    def __init__(self):
        self.servers = {
            'rag': StdioServerParameters(
                command="python",
                args=["d:/repos/corporateactions/mcp-server/main.py"],
                env=None
            ),
            'search': StdioServerParameters(
                command="python", 
                args=["d:/repos/corporateactions/mcp-websearch/main.py"],
                env=None
            ),
            'comments': StdioServerParameters(
                command="python",
                args=["d:/repos/corporateactions/mcp-comments/main.py"], 
                env=None
            )
        }
        self.executor = ThreadPoolExecutor(max_workers=3)
    
    def _call_tool(self, server_params: StdioServerParameters, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute MCP tool call synchronously"""
        try:
            # Run the async call in a thread pool
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def async_call():
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool(tool_name, arguments)
                        return result.content[0].text if result.content else "{}"
            
            return loop.run_until_complete(async_call())
        except Exception as e:
            logger.error(f"MCP tool call failed: {e}")
            return {"error": str(e)}
    
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
        
        # Parse JSON response
        if isinstance(result, str):
            try:
                return json.loads(result)
            except:
                return {"answer": result}
        return result
    
    def search_corporate_actions(self, **kwargs) -> Dict[str, Any]:
        """Search corporate actions using enhanced MCP"""
        result = self._call_tool(
            self.servers['rag'],
            "search_corporate_actions",
            kwargs
        )
        
        if isinstance(result, str):
            try:
                return json.loads(result)
            except:
                return {"events": [], "error": "Failed to parse response"}
        return result
    
    def get_event_details(self, event_id: str, include_comments: bool = True) -> Dict[str, Any]:
        """Get detailed event information"""
        result = self._call_tool(
            self.servers['rag'],
            "get_event_details", 
            {"event_id": event_id, "include_comments": include_comments}
        )
        
        if isinstance(result, str):
            try:
                return json.loads(result)
            except:
                return {"error": "Failed to parse response"}
        return result
    
    def add_comment(self, event_id: str, user_name: str, comment_text: str, comment_type: str = "general") -> Dict[str, Any]:
        """Add comment to an event"""
        result = self._call_tool(
            self.servers['comments'],
            "add_comment",
            {
                "event_id": event_id,
                "user_name": user_name,
                "content": comment_text,
                "comment_type": comment_type
            }
        )
        
        if isinstance(result, str):
            try:
                return json.loads(result)
            except:
                return {"success": False, "error": "Failed to parse response"}
        return result
    
    def get_service_health(self) -> Dict[str, Any]:
        """Check MCP server health"""
        result = self._call_tool(
            self.servers['rag'],
            "get_service_health",
            {}
        )
        
        if isinstance(result, str):
            try:
                return json.loads(result)
            except:
                return {"status": "unknown", "error": "Failed to parse response"}
        return result

# Global MCP client instance
mcp_client = SimpleMCPClient()

class CorporateActionsBot(TeamsActivityHandler):
    """Enhanced Teams bot for corporate actions platform with MCP integration"""
    
    def __init__(self, conversation_state: ConversationState, user_state: UserState):
        self.conversation_state = conversation_state
        self.user_state = user_state
        
        # Create state accessors
        self.user_profile_accessor = self.user_state.create_property("UserProfile")
        self.conversation_data_accessor = self.conversation_state.create_property("ConversationData")
        
        # Chat history management
        self.chat_history_accessor = self.conversation_state.create_property("ChatHistory")
    
    async def on_message_activity(self, turn_context: TurnContext):
        """Handle incoming messages with enhanced MCP integration"""
        user_message = turn_context.activity.text.strip()
        logger.info(f"Received message: {user_message}")
        
        # Get or initialize chat history
        chat_history = await self.chat_history_accessor.get(turn_context, lambda: [])
        
        # Add user message to history
        chat_history.append({"role": "user", "content": user_message})
        
        # Keep only last 10 messages for context
        if len(chat_history) > 10:
            chat_history = chat_history[-10:]
        
        # Handle different command types
        if user_message.lower().startswith("/help"):
            await self._send_help_message(turn_context)
        elif user_message.lower().startswith("/search"):
            await self._handle_search_command(turn_context, user_message, chat_history)
        elif user_message.lower().startswith("/events"):
            await self._handle_events_command(turn_context, user_message)
        elif user_message.lower().startswith("/comment"):
            await self._handle_comment_command(turn_context, user_message)
        elif user_message.lower().startswith("/subscribe"):
            await self._handle_subscribe_command(turn_context, user_message)
        elif user_message.lower().startswith("/unsubscribe"):
            await self._handle_unsubscribe_command(turn_context, user_message)
        elif user_message.lower().startswith("/status"):
            await self._handle_status_command(turn_context)
        elif user_message.lower().startswith("/notifications"):
            await self._handle_notifications_command(turn_context, user_message)
        else:
            # Use enhanced RAG for natural language queries
            response_text = await self._handle_rag_query(turn_context, user_message, chat_history)
            chat_history.append({"role": "assistant", "content": response_text})
        
        # Save updated chat history
        await self.conversation_state.save_changes(turn_context)
    
    async def on_members_added_activity(
        self, members_added: List[ChannelAccount], turn_context: TurnContext
    ):
        """Greet new members with enhanced welcome"""
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await self._send_welcome_message(turn_context)
    
    async def _send_welcome_message(self, turn_context: TurnContext):
        """Send enhanced welcome message with MCP capabilities"""
        welcome_text = """
        🏦 **Welcome to Enhanced Corporate Actions Bot!**
        
        I'm powered by advanced MCP (Model Context Protocol) servers and can help you with:
        
        📊 **Enhanced Commands:**
        - `/help` - Show detailed help and capabilities
        - `/search [query]` - Advanced search with AI insights
        - `/events` - Recent corporate actions with smart filtering
        - `/comment [event_id] [message]` - Add structured comments
        - `/subscribe [symbols]` - Smart notifications for specific symbols
        - `/unsubscribe [symbols]` - Manage your subscriptions
        - `/status` - Check MCP server health and capabilities
        - `/notifications` - Manage notification preferences
        
        🤖 **AI-Powered Natural Language:**
        Ask me complex questions like:
        - "Show me all dividend announcements this week with amounts over $1"
        - "What are the upcoming stock splits and their ratios?"
        - "Create a summary of merger activities in the tech sector"
        - "Analyze the dividend trends for FAANG stocks"
        
        📢 **Smart Notifications:**
        I'll proactively notify you about:
        - 🚨 Breaking corporate action announcements
        - 📈 Status updates on your subscribed events
        - 📊 Market open/close summaries with key highlights
        - 💬 Comments and Q&A on events you're following
        
        🎯 **Context-Aware Conversations:**
        I remember our conversation history and can provide contextual follow-ups!
        """
        
        await turn_context.send_activity(MessageFactory.text(welcome_text))
        
        # Send enhanced suggested actions
        suggested_actions = SuggestedActions(
            actions=[
                CardAction(
                    title="📊 Recent Events",
                    type=ActionTypes.im_back,
                    value="/events"
                ),
                CardAction(
                    title="🔍 Smart Search", 
                    type=ActionTypes.im_back,
                    value="/search dividend tech companies"
                ),
                CardAction(
                    title="🔔 Setup Notifications",
                    type=ActionTypes.im_back,
                    value="/subscribe AAPL,MSFT,GOOGL"
                ),
                CardAction(
                    title="❓ Help & Guide",
                    type=ActionTypes.im_back,
                    value="/help"
                )
            ]        )
        
        message = MessageFactory.text("🚀 Choose an action to get started:")
        message.suggested_actions = suggested_actions
        await turn_context.send_activity(message)
    
    async def _send_help_message(self, turn_context: TurnContext):
        """Send enhanced help message with MCP capabilities"""
        help_text = """
        🔍 **Enhanced Corporate Actions Bot - Command Guide**
        
        **🔍 Search & Query (MCP-Powered):**
        - `/search dividend AAPL` - Search with AI-powered insights
        - `/events` - Recent actions with smart filtering
        - `"Show me Tesla stock splits"` - Natural language with context
        
        **💬 Comments & Collaboration:**
        - `/comment CA-2025-001 This needs clarification` - Structured comments
        - `/comment CA-2025-001 question What's the timeline?` - Categorized questions
        
        **🔔 Smart Notifications:**
        - `/subscribe AAPL,MSFT,GOOGL` - Multi-symbol subscriptions
        - `/unsubscribe TSLA` - Remove specific symbols
        - `/notifications settings` - Configure notification preferences
        
        **🛠️ System & Status:**
        - `/status` - Check MCP server health and capabilities
        - `/help` - Show this enhanced help guide
        
        **🤖 AI Features:**
        - **Context Awareness**: I remember our conversation history
        - **Smart Insights**: AI-powered analysis and recommendations  
        - **Dynamic Responses**: Contextual follow-ups and clarifications
        - **Multi-modal Support**: Text responses with rich formatting
        
        **💡 Pro Tips:**
        - Use natural language for complex queries
        - Subscribe to symbols you track regularly
        - Ask follow-up questions - I maintain context!
        - Use specific event IDs for targeted comments
        """
        
        await turn_context.send_activity(MessageFactory.text(help_text))
    
    async def _handle_search_command(self, turn_context: TurnContext, message: str, chat_history: List[Dict[str, str]]):
        """Handle search command with enhanced MCP integration"""
        try:
            # Extract search query
            query = message[7:].strip()  # Remove "/search "
            if not query:
                await turn_context.send_activity(
                    MessageFactory.text("🔍 Please provide a search query. Example: `/search dividend announcements this week`")
                )
                return
            
            await turn_context.send_activity(MessageFactory.text(f"🔍 Searching with AI insights: *{query}*"))
            
            # Use enhanced MCP RAG query with chat history
            try:
                response_data = mcp_client.rag_query(
                    query=query,
                    max_results=5,
                    include_comments=True,
                    chat_history=chat_history[-6:] if len(chat_history) > 6 else chat_history
                )
                
                if "error" not in response_data:
                    answer = response_data.get("answer", "No results found")
                    sources = response_data.get("sources", [])
                    confidence = response_data.get("confidence_score", 0.0)
                    requires_viz = response_data.get("requires_visualization", False)
                    
                    # Format enhanced response
                    formatted_response = f"🤖 **AI-Powered Search Results:**\n\n{answer}"
                    
                    # Add confidence indicator
                    if confidence > 0.8:
                        formatted_response += f"\n\n✅ **High Confidence** ({confidence:.1%})"
                    elif confidence > 0.6:
                        formatted_response += f"\n\n⚠️ **Medium Confidence** ({confidence:.1%})"
                    else:
                        formatted_response += f"\n\n❓ **Lower Confidence** ({confidence:.1%}) - Consider refining your query"
                    
                    # Add visualization note if detected
                    if requires_viz:
                        formatted_response += "\n\n📊 *Note: This query would benefit from visualizations. Try using our Streamlit dashboard for charts and graphs!*"
                    
                    # Add sources with enhanced formatting
                    if sources:
                        formatted_response += "\n\n🔗 **Related Events:**"
                        for i, source in enumerate(sources[:3], 1):
                            company = source.get('issuer_name', source.get('company_name', 'Unknown'))
                            event_type = source.get('event_type', 'Unknown').replace('_', ' ').title()
                            status = source.get('status', 'Unknown')
                            status_emoji = {"confirmed": "✅", "announced": "📅", "pending": "⏳", "processed": "✅", "cancelled": "❌"}.get(status, "❓")
                            
                            formatted_response += f"\n{i}. {status_emoji} **{company}** - {event_type} ({source.get('event_id', 'N/A')})"
                    
                    await turn_context.send_activity(MessageFactory.text(formatted_response))
                else:
                    await turn_context.send_activity(
                        MessageFactory.text(f"❌ Search error: {response_data.get('error', 'Unknown error')}")
                    )
            except Exception as mcp_error:
                logger.error(f"MCP client error: {mcp_error}")
                await turn_context.send_activity(
                    MessageFactory.text("❌ Sorry, I encountered an issue with the search service. Please try again later.")
                )
                
        except Exception as e:
            logger.error(f"Error in search command: {e}")
            await turn_context.send_activity(
                MessageFactory.text("❌ An error occurred while searching. Please try again.")
            )
    
    async def _handle_events_command(self, turn_context: TurnContext, message: str):
        """Handle events command with enhanced MCP integration"""
        try:
            await turn_context.send_activity(MessageFactory.text("📊 Fetching recent corporate actions..."))
            
            # Parse any additional filters from the message
            parts = message.split()
            limit = 5
            status_filter = ""
            
            # Look for modifiers like "/events confirmed" or "/events 10"
            if len(parts) > 1:
                for part in parts[1:]:
                    if part.isdigit():
                        limit = min(int(part), 20)  # Max 20 events
                    elif part.lower() in ["confirmed", "announced", "pending", "processed", "cancelled"]:
                        status_filter = part.lower()
            
            # Use enhanced MCP search
            search_params = {
                "limit": limit,
                "date_from": (date.today() - timedelta(days=30)).isoformat()
            }
            
            if status_filter:
                search_params["status"] = status_filter
            
            try:
                events_data = mcp_client.search_corporate_actions(**search_params)
                
                if "error" not in events_data:
                    events = events_data.get("events", [])
                    
                    if events:
                        # Enhanced formatting with emojis and status indicators
                        events_text = f"📈 **Recent Corporate Actions** ({len(events)} found):\n\n"
                        
                        for i, event in enumerate(events, 1):
                            company = event.get('issuer_name', event.get('company_name', 'Unknown'))
                            symbol = event.get('symbol', 'N/A')
                            event_type = event.get('event_type', 'Unknown').replace('_', ' ').title()
                            status = event.get('status', 'Unknown')
                            announced = event.get('announcement_date', 'Unknown')
                            event_id = event.get('event_id', 'N/A')
                            
                            # Status emoji mapping
                            status_emoji = {
                                "confirmed": "✅", "announced": "📅", "pending": "⏳", 
                                "processed": "✅", "cancelled": "❌"
                            }.get(status, "❓")
                            
                            # Event type emoji mapping
                            type_emoji = {
                                "dividend": "💰", "stock split": "📈", "merger": "🤝",
                                "spinoff": "🔄", "acquisition": "🏢", "rights": "📜"
                            }.get(event_type.lower(), "📊")
                            
                            events_text += f"""**{i}. {type_emoji} {company} ({symbol})**
{status_emoji} Status: {status}
📅 Announced: {announced}
🆔 ID: `{event_id}`
Type: {event_type}

"""
                        
                        # Add helpful actions
                        events_text += "💡 **Actions:**\n"
                        events_text += "• Use `/comment [event_id] [message]` to add comments\n"
                        events_text += "• Ask me natural language questions about these events\n"
                        events_text += "• Use `/subscribe [symbol]` for future notifications"
                        
                        await turn_context.send_activity(MessageFactory.text(events_text))
                    else:
                        filter_msg = f" with status '{status_filter}'" if status_filter else ""
                        await turn_context.send_activity(
                            MessageFactory.text(f"📊 No recent corporate actions found{filter_msg}.")
                        )
                else:
                    await turn_context.send_activity(
                        MessageFactory.text(f"❌ Error retrieving events: {events_data.get('error', 'Unknown error')}")                    )
            except Exception as mcp_error:
                logger.error(f"MCP client error: {mcp_error}")
                await turn_context.send_activity(
                    MessageFactory.text("❌ Could not retrieve events. Please try again later.")
                )
                
        except Exception as e:
            logger.error(f"Error in events command: {e}")
            await turn_context.send_activity(
                MessageFactory.text("❌ An error occurred while fetching events.")
            )
    
    async def _handle_comment_command(self, turn_context: TurnContext, message: str):
        """Handle comment command with MCP integration"""
        try:
            # Parse command: /comment [event_id] [message]
            parts = message[8:].strip().split(' ', 1)  # Remove "/comment "
            
            if len(parts) < 2:
                await turn_context.send_activity(
                    MessageFactory.text("💬 Please provide event ID and comment. Example: `/comment CA-2025-001 This needs clarification`")
                )
                return
            
            event_id = parts[0]
            comment_content = parts[1]
            
            # Detect comment type from content
            comment_type = "general"
            if any(word in comment_content.lower() for word in ["question", "?", "clarification", "unclear"]):
                comment_type = "question"
            elif any(word in comment_content.lower() for word in ["analysis", "impact", "risk"]):
                comment_type = "analysis"
            elif any(word in comment_content.lower() for word in ["alert", "urgent", "important"]):
                comment_type = "alert"
            
            # Get user info
            user_name = turn_context.activity.from_property.name or "Teams User"
            
            await turn_context.send_activity(MessageFactory.text(f"💬 Adding {comment_type} comment to event {event_id}..."))
            
            # Use MCP client to add comment
            try:
                result = mcp_client.add_comment(
                    event_id=event_id,
                    user_name=user_name,
                    comment_text=comment_content,
                    comment_type=comment_type
                )
                
                if result.get("success", False):
                    type_emoji = {"question": "❓", "analysis": "📊", "alert": "🚨", "general": "💭"}.get(comment_type, "💬")
                    await turn_context.send_activity(
                        MessageFactory.text(f"✅ {type_emoji} Comment added to event `{event_id}`\nType: {comment_type.title()}")
                    )
                else:
                    error_msg = result.get("error", "Unknown error")
                    await turn_context.send_activity(
                        MessageFactory.text(f"❌ Failed to add comment: {error_msg}\nPlease check the event ID and try again.")
                    )
            except Exception as mcp_error:
                logger.error(f"MCP client error: {mcp_error}")
                await turn_context.send_activity(
                    MessageFactory.text("❌ Could not add comment. Please try again later.")
                )
                
        except Exception as e:
            logger.error(f"Error in comment command: {e}")
            await turn_context.send_activity(
                MessageFactory.text("❌ An error occurred while adding the comment.")
            )
    
    async def _handle_subscribe_command(self, turn_context: TurnContext, message: str):
        """Handle subscribe command"""
        try:
            symbols = message[10:].strip().upper()  # Remove "/subscribe "
            
            if not symbols:
                await turn_context.send_activity(
                    MessageFactory.text("Please provide symbols to subscribe to. Example: `/subscribe AAPL,MSFT`")
                )
                return
            
            # Store subscription in user state
            user_profile = await self.user_profile_accessor.get(turn_context, lambda: {})
            
            if "subscriptions" not in user_profile:
                user_profile["subscriptions"] = set()
            
            symbol_list = [s.strip() for s in symbols.split(',')]
            user_profile["subscriptions"].update(symbol_list)
            user_profile["subscriptions"] = list(user_profile["subscriptions"])  # Convert to list for JSON serialization
            
            await self.user_state.save_changes(turn_context)
            
            await turn_context.send_activity(
                MessageFactory.text(f"✅ Subscribed to notifications for: {', '.join(symbol_list)}")
            )
            
        except Exception as e:
            logger.error(f"Error in subscribe command: {e}")
            await turn_context.send_activity(
                MessageFactory.text("❌ An error occurred while subscribing.")
            )
    
    async def _handle_unsubscribe_command(self, turn_context: TurnContext, message: str):
        """Handle unsubscribe command"""
        try:
            symbols = message[12:].strip().upper()  # Remove "/unsubscribe "
            
            if not symbols:
                await turn_context.send_activity(
                    MessageFactory.text("Please provide symbols to unsubscribe from. Example: `/unsubscribe AAPL`")
                )
                return
            
            # Update subscription in user state
            user_profile = await self.user_profile_accessor.get(turn_context, lambda: {})
            
            if "subscriptions" not in user_profile:
                user_profile["subscriptions"] = []
            
            symbol_list = [s.strip() for s in symbols.split(',')]
            current_subs = set(user_profile["subscriptions"])
            current_subs.difference_update(symbol_list)
            user_profile["subscriptions"] = list(current_subs)
            
            await self.user_state.save_changes(turn_context)
            
            await turn_context.send_activity(
                MessageFactory.text(f"✅ Unsubscribed from: {', '.join(symbol_list)}")
            )
        except Exception as e:
            logger.error(f"Error in unsubscribe command: {e}")
            await turn_context.send_activity(
                MessageFactory.text("❌ An error occurred while unsubscribing.")
            )
    
    async def _handle_rag_query(self, turn_context: TurnContext, query: str, chat_history: List[Dict[str, str]]):
        """Handle natural language RAG query with enhanced MCP integration"""
        try:
            await turn_context.send_activity(MessageFactory.text("🤖 Let me search that for you..."))
            
            # Use MCP client for RAG query with chat history
            try:
                rag_data = mcp_client.rag_query(
                    query=query,
                    max_results=3,
                    include_comments=True,
                    chat_history=chat_history[-8:] if len(chat_history) > 8 else chat_history
                )
                
                if "error" not in rag_data:
                    answer = rag_data.get("answer", "I couldn't find relevant information.")
                    sources = rag_data.get("sources", [])
                    confidence = rag_data.get("confidence_score", 0.0)
                    context_used = rag_data.get("context_from_history", False)
                    
                    # Format enhanced response with context awareness
                    formatted_response = f"🤖 **AI Assistant Response:**\n\n{answer}"
                    
                    # Add confidence indicator
                    if confidence > 0.7:
                        formatted_response += f"\n\n✅ **High Confidence** ({confidence:.1%})"
                    elif confidence > 0.4:
                        formatted_response += f"\n\n⚠️ **Medium Confidence** ({confidence:.1%})"
                    else:
                        formatted_response += f"\n\n❓ **Lower Confidence** ({confidence:.1%}) - Try being more specific"
                    
                    # Indicate if conversation context was used
                    if context_used:
                        formatted_response += "\n\n🧠 *Used conversation history for context*"
                    
                    # Add related events
                    if sources:
                        formatted_response += "\n\n📋 **Related Events:**"
                        for i, source in enumerate(sources[:3], 1):
                            company = source.get('issuer_name', source.get('company_name', 'Unknown'))
                            symbol = source.get('symbol', 'N/A')
                            event_type = source.get('event_type', 'Unknown').replace('_', ' ').title()
                            event_id = source.get('event_id', 'N/A')
                            formatted_response += f"\n{i}. **{company} ({symbol})** - {event_type} (`{event_id}`)"
                    
                    await turn_context.send_activity(MessageFactory.text(formatted_response))
                    return formatted_response  # Return for chat history
                else:
                    error_response = f"❌ I encountered an issue: {rag_data.get('error', 'Unknown error')}"
                    await turn_context.send_activity(MessageFactory.text(error_response))
                    return error_response
                    
            except Exception as mcp_error:
                logger.error(f"MCP client error: {mcp_error}")
                error_response = "❌ I encountered an issue processing your request. Please try rephrasing your question."
                await turn_context.send_activity(MessageFactory.text(error_response))
                return error_response
                
        except Exception as e:
            logger.error(f"Error in RAG query: {e}")
            error_response = "❌ An error occurred while processing your query."
            await turn_context.send_activity(MessageFactory.text(error_response))
            return error_response
    
    async def _handle_status_command(self, turn_context: TurnContext):
        """Handle status command - check MCP server health"""
        try:
            await turn_context.send_activity(MessageFactory.text("🔍 Checking MCP server status..."))
            
            try:
                health_data = mcp_client.get_service_health()
                
                if "error" not in health_data:
                    status = health_data.get("status", "unknown")
                    timestamp = health_data.get("timestamp", "unknown")
                    servers = health_data.get("servers", {})
                    
                    # Format status response
                    status_emoji = {"healthy": "✅", "degraded": "⚠️", "unhealthy": "❌"}.get(status, "❓")
                    status_text = f"🛠️ **MCP Server Status** {status_emoji}\n\n"
                    status_text += f"**Overall Status:** {status.title()}\n"
                    status_text += f"**Last Check:** {timestamp}\n\n"
                    
                    # Server details
                    if servers:
                        status_text += "**Server Health:**\n"
                        for server_name, server_info in servers.items():
                            server_status = server_info.get("status", "unknown")
                            server_emoji = {"healthy": "✅", "degraded": "⚠️", "unhealthy": "❌"}.get(server_status, "❓")
                            tools_count = len(server_info.get("tools", []))
                            status_text += f"• {server_emoji} **{server_name.title()}**: {server_status} ({tools_count} tools)\n"
                    
                    # Add capabilities summary
                    status_text += "\n**Available Capabilities:**\n"
                    status_text += "• 🔍 Enhanced RAG with chat history\n"
                    status_text += "• 📊 Corporate actions search & analysis\n"
                    status_text += "• 💬 Comment management & collaboration\n"
                    status_text += "• 🌐 Web search integration\n"
                    status_text += "• 📈 Dynamic visualization support\n"
                    
                    await turn_context.send_activity(MessageFactory.text(status_text))
                else:
                    await turn_context.send_activity(
                        MessageFactory.text(f"❌ Status check failed: {health_data.get('error', 'Unknown error')}")
                    )
                    
            except Exception as mcp_error:
                logger.error(f"MCP client error: {mcp_error}")
                await turn_context.send_activity(
                    MessageFactory.text("❌ Could not check server status. MCP servers may be unavailable.")
                )
                
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await turn_context.send_activity(
                MessageFactory.text("❌ An error occurred while checking status.")
            )
    
    async def _handle_notifications_command(self, turn_context: TurnContext, message: str):
        """Handle notifications management command"""
        try:
            parts = message.split()
            
            if len(parts) == 1:  # Just "/notifications"
                # Show current notification settings
                user_profile = await self.user_profile_accessor.get(turn_context, lambda: {})
                subscriptions = user_profile.get("subscriptions", [])
                notification_settings = user_profile.get("notification_settings", {
                    "market_open": True,
                    "market_close": True,
                    "breaking_news": True,
                    "quiet_hours": False
                })
                
                settings_text = "🔔 **Your Notification Settings**\n\n"
                settings_text += f"📈 **Subscribed Symbols:** {', '.join(subscriptions) if subscriptions else 'None'}\n\n"
                settings_text += "**Alert Types:**\n"
                settings_text += f"• 🌅 Market Open: {'✅ Enabled' if notification_settings.get('market_open') else '❌ Disabled'}\n"
                settings_text += f"• 🌇 Market Close: {'✅ Enabled' if notification_settings.get('market_close') else '❌ Disabled'}\n"
                settings_text += f"• 🚨 Breaking News: {'✅ Enabled' if notification_settings.get('breaking_news') else '❌ Disabled'}\n"
                settings_text += f"• 🔇 Quiet Hours: {'✅ Enabled' if notification_settings.get('quiet_hours') else '❌ Disabled'}\n\n"
                
                settings_text += "**Commands:**\n"
                settings_text += "• `/notifications enable [type]` - Enable notification type\n"
                settings_text += "• `/notifications disable [type]` - Disable notification type\n"
                settings_text += "• `/notifications quiet on/off` - Toggle quiet hours\n"
                settings_text += "• `/subscribe [symbols]` - Add symbol subscriptions\n"
                
                await turn_context.send_activity(MessageFactory.text(settings_text))
                
            elif len(parts) >= 3:  # "/notifications enable/disable [type]"
                action = parts[1].lower()
                setting_type = parts[2].lower()
                
                user_profile = await self.user_profile_accessor.get(turn_context, lambda: {})
                if "notification_settings" not in user_profile:
                    user_profile["notification_settings"] = {}
                
                setting_map = {
                    "market_open": "market_open",
                    "market": "market_open", 
                    "open": "market_open",
                    "market_close": "market_close",
                    "close": "market_close",
                    "breaking": "breaking_news",
                    "news": "breaking_news",
                    "breaking_news": "breaking_news"
                }
                
                if setting_type in setting_map:
                    setting_key = setting_map[setting_type]
                    
                    if action == "enable":
                        user_profile["notification_settings"][setting_key] = True
                        await self.user_state.save_changes(turn_context)
                        await turn_context.send_activity(
                            MessageFactory.text(f"✅ Enabled {setting_key.replace('_', ' ').title()} notifications")
                        )
                    elif action == "disable":
                        user_profile["notification_settings"][setting_key] = False
                        await self.user_state.save_changes(turn_context)
                        await turn_context.send_activity(
                            MessageFactory.text(f"❌ Disabled {setting_key.replace('_', ' ').title()} notifications")
                        )
                    else:
                        await turn_context.send_activity(
                            MessageFactory.text("❓ Use 'enable' or 'disable'. Example: `/notifications enable market_open`")
                        )
                else:
                    await turn_context.send_activity(
                        MessageFactory.text("❓ Unknown notification type. Available: market_open, market_close, breaking_news")
                    )
                    
            elif len(parts) == 3 and parts[1].lower() == "quiet":  # "/notifications quiet on/off"
                quiet_setting = parts[2].lower()
                user_profile = await self.user_profile_accessor.get(turn_context, lambda: {})
                
                if "notification_settings" not in user_profile:
                    user_profile["notification_settings"] = {}
                
                if quiet_setting in ["on", "true", "enable"]:
                    user_profile["notification_settings"]["quiet_hours"] = True
                    await self.user_state.save_changes(turn_context)
                    await turn_context.send_activity(
                        MessageFactory.text("🔇 Quiet hours enabled - reduced notifications during off-hours")
                    )
                elif quiet_setting in ["off", "false", "disable"]:
                    user_profile["notification_settings"]["quiet_hours"] = False
                    await self.user_state.save_changes(turn_context)
                    await turn_context.send_activity(
                        MessageFactory.text("🔔 Quiet hours disabled - full notifications enabled")
                    )
                else:
                    await turn_context.send_activity(
                        MessageFactory.text("❓ Use 'on' or 'off'. Example: `/notifications quiet on`")
                    )
            else:
                await turn_context.send_activity(
                    MessageFactory.text("❓ Invalid command. Use `/notifications` to see current settings.")
                )
                
        except Exception as e:
            logger.error(f"Error in notifications command: {e}")
            await turn_context.send_activity(
                MessageFactory.text("❌ An error occurred while managing notifications.")
            )

class EnhancedNotificationService:
    """Enhanced service for proactive Teams notifications with MCP integration"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.scheduled_notifications = []
        self.event_cache = {}  # Cache to track new events
        self.subscribers = {}  # User subscriptions mapping
        
    async def initialize_scheduler(self):
        """Initialize the notification scheduler"""
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from apscheduler.triggers.cron import CronTrigger
            
            self.scheduler = AsyncIOScheduler()
            
            # Schedule market open notification (9:30 AM ET, Mon-Fri)
            self.scheduler.add_job(
                self.send_market_open_notification,
                CronTrigger(hour=9, minute=30, day_of_week='mon-fri'),
                id='market_open'
            )
            
            # Schedule market close notification (4:00 PM ET, Mon-Fri) 
            self.scheduler.add_job(
                self.send_market_close_notification,
                CronTrigger(hour=16, minute=0, day_of_week='mon-fri'),
                id='market_close'
            )
            
            # Check for new corporate actions every 15 minutes during market hours
            self.scheduler.add_job(
                self.check_new_corporate_actions,
                CronTrigger(minute='*/15', hour='9-16', day_of_week='mon-fri'),
                id='check_new_events'
            )
            
            # Weekly summary on Sunday evening
            self.scheduler.add_job(
                self.send_weekly_summary,
                CronTrigger(day_of_week='sun', hour=18, minute=0),
                id='weekly_summary'
            )
            
            self.scheduler.start()
            logger.info("Enhanced notification scheduler initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {e}")
    
    async def send_market_open_notification(self):
        """Send market open notification with AI insights"""
        try:
            # Get market preview using MCP
            preview_query = "What are the key corporate actions and events happening today?"
            preview_data = mcp_client.rag_query(
                query=preview_query,
                max_results=5,
                include_comments=False
            )
            
            notification_text = "🌅 **Market Open - Good Morning!**\n\n"
            notification_text += f"📅 {datetime.now().strftime('%A, %B %d, %Y')}\n\n"
            
            if "error" not in preview_data:
                answer = preview_data.get("answer", "No specific events scheduled for today.")
                notification_text += f"🎯 **Today's Focus:**\n{answer}\n\n"
                
                # Add any urgent events
                sources = preview_data.get("sources", [])
                if sources:
                    notification_text += "⚡ **Key Events Today:**\n"
                    for source in sources[:3]:
                        company = source.get('issuer_name', 'Unknown')
                        event_type = source.get('event_type', 'Unknown').replace('_', ' ').title()
                        notification_text += f"• {company} - {event_type}\n"
            else:
                notification_text += "📊 Markets are open! Check `/events` for recent corporate actions.\n"
            
            notification_text += "\n💡 Use `/help` for commands or ask me questions in natural language!"
            
            # Send to all users with market_open notifications enabled
            await self._broadcast_to_subscribers(notification_text, "market_open")
            
        except Exception as e:
            logger.error(f"Error sending market open notification: {e}")
    
    async def send_market_close_notification(self):
        """Send market close notification with daily summary"""
        try:
            # Get daily summary using MCP
            summary_query = "Summarize today's corporate action announcements and key developments"
            summary_data = mcp_client.rag_query(
                query=summary_query,
                max_results=8,
                include_comments=False
            )
            
            notification_text = "🌇 **Market Close - Daily Wrap-up**\n\n"
            notification_text += f"📅 {datetime.now().strftime('%A, %B %d, %Y')}\n\n"
            
            if "error" not in summary_data:
                answer = summary_data.get("answer", "Quiet day with no major corporate actions.")
                notification_text += f"📊 **Today's Summary:**\n{answer}\n\n"
                
                # Add trending events
                sources = summary_data.get("sources", [])
                if sources:
                    notification_text += "📈 **Today's Activity:**\n"
                    event_types = {}
                    for source in sources:
                        event_type = source.get('event_type', 'Unknown').replace('_', ' ').title()
                        event_types[event_type] = event_types.get(event_type, 0) + 1
                    
                    for event_type, count in event_types.items():
                        notification_text += f"• {count} {event_type} event{'s' if count > 1 else ''}\n"
            else:
                notification_text += "📊 Market closed. Check `/events` for today's corporate actions.\n"
            
            notification_text += "\n🌙 Have a great evening! See you tomorrow for market open."
            
            # Send to all users with market_close notifications enabled
            await self._broadcast_to_subscribers(notification_text, "market_close")
            
        except Exception as e:
            logger.error(f"Error sending market close notification: {e}")
    
    async def check_new_corporate_actions(self):
        """Check for new corporate actions and notify subscribers"""
        try:
            # Get recent events from the last 15 minutes
            current_time = datetime.now()
            check_time = current_time - timedelta(minutes=15)
            
            # Search for very recent events
            recent_events = mcp_client.search_corporate_actions(
                date_from=check_time.date().isoformat(),
                limit=10
            )
            
            if "error" not in recent_events:
                events = recent_events.get("events", [])
                
                for event in events:
                    event_id = event.get("event_id")
                    announcement_date = event.get("announcement_date")
                    
                    # Check if this is a genuinely new event (not in cache)
                    if event_id and event_id not in self.event_cache:
                        # Add to cache
                        self.event_cache[event_id] = current_time
                        
                        # Check if anyone is subscribed to this symbol
                        symbol = event.get("symbol", "").upper()
                        if symbol and await self._has_subscribers_for_symbol(symbol):
                            await self.send_event_notification(event, symbol)
                
                # Clean old entries from cache (older than 24 hours)
                cutoff_time = current_time - timedelta(hours=24)
                self.event_cache = {
                    k: v for k, v in self.event_cache.items() 
                    if v > cutoff_time
                }
                        
        except Exception as e:
            logger.error(f"Error checking new corporate actions: {e}")
    
    async def send_event_notification(self, event_data: Dict[str, Any], symbol: str):
        """Send notification about new corporate action to relevant subscribers"""
        try:
            # Format rich notification
            company = event_data.get('issuer_name', 'Unknown Company')
            event_type = event_data.get('event_type', 'Unknown').replace('_', ' ').title()
            status = event_data.get('status', 'Unknown')
            announced = event_data.get('announcement_date', 'Unknown')
            event_id = event_data.get('event_id', 'N/A')
            description = event_data.get('description', 'No description available.')
            
            # Event type emoji mapping
            type_emoji = {
                "dividend": "💰", "stock split": "📈", "merger": "🤝",
                "spinoff": "🔄", "acquisition": "🏢", "rights": "📜",
                "special dividend": "💎", "stock repurchase": "🔄"
            }.get(event_type.lower(), "📊")
            
            # Status emoji mapping
            status_emoji = {
                "confirmed": "✅", "announced": "📅", "pending": "⏳",
                "processed": "✅", "cancelled": "❌"
            }.get(status, "❓")
            
            notification_text = f"""🚨 **Breaking: New Corporate Action Alert!**

{type_emoji} **{company} ({symbol})**
📋 **Type:** {event_type}
{status_emoji} **Status:** {status}
📅 **Announced:** {announced}
🆔 **Event ID:** `{event_id}`

📝 **Details:**
{description}

💡 **Quick Actions:**
• Use `/comment {event_id} [message]` to add comments
• Ask me questions about this event in natural language
• Share your analysis with the team

🔔 Getting this because you're subscribed to {symbol}
"""
            
            # Send to subscribers of this symbol
            await self._broadcast_to_symbol_subscribers(notification_text, symbol)
            
            logger.info(f"Event notification sent for {symbol} - {event_id}")
            
        except Exception as e:
            logger.error(f"Error sending event notification: {e}")
    
    async def send_weekly_summary(self):
        """Send weekly summary of corporate actions"""
        try:
            # Get weekly summary using MCP
            week_ago = (datetime.now() - timedelta(days=7)).date()
            summary_query = f"Provide a comprehensive weekly summary of corporate actions since {week_ago}"
            
            summary_data = mcp_client.rag_query(
                query=summary_query,
                max_results=15,
                include_comments=False
            )
            
            notification_text = "📅 **Weekly Corporate Actions Summary**\n\n"
            notification_text += f"🗓️ Week of {week_ago.strftime('%B %d')} - {datetime.now().strftime('%B %d, %Y')}\n\n"
            
            if "error" not in summary_data:
                answer = summary_data.get("answer", "Quiet week with minimal corporate action activity.")
                notification_text += f"📊 **Week in Review:**\n{answer}\n\n"
                
                # Add statistics
                sources = summary_data.get("sources", [])
                if sources:
                    # Group by event type
                    event_stats = {}
                    company_list = []
                    
                    for source in sources:
                        event_type = source.get('event_type', 'Unknown').replace('_', ' ').title()
                        company = source.get('issuer_name', 'Unknown')
                        
                        event_stats[event_type] = event_stats.get(event_type, 0) + 1
                        if company not in company_list:
                            company_list.append(company)
                    
                    notification_text += "📈 **This Week's Activity:**\n"
                    for event_type, count in sorted(event_stats.items(), key=lambda x: x[1], reverse=True):
                        notification_text += f"• {count} {event_type} event{'s' if count > 1 else ''}\n"
                    
                    notification_text += f"\n🏢 **Companies Involved:** {len(company_list)} total\n"
                    if len(company_list) <= 5:
                        notification_text += f"📋 {', '.join(company_list)}\n"
            
            notification_text += "\n🚀 **Looking Ahead:**\nCheck `/events` for upcoming corporate actions and stay informed!"
            
            # Send to all users (weekly summary goes to everyone)
            await self._broadcast_to_all_users(notification_text)
            
        except Exception as e:
            logger.error(f"Error sending weekly summary: {e}")
    
    async def _broadcast_to_subscribers(self, message: str, notification_type: str):
        """Broadcast message to users with specific notification type enabled"""
        # In a production environment, this would iterate through actual user conversations
        # For now, we'll log the intended broadcast
        logger.info(f"Broadcasting {notification_type} notification to subscribers: {message[:100]}...")
    
    async def _broadcast_to_symbol_subscribers(self, message: str, symbol: str):
        """Broadcast message to users subscribed to a specific symbol"""
        # In production, this would check user subscriptions and send to relevant conversations
        logger.info(f"Broadcasting symbol {symbol} notification to subscribers: {message[:100]}...")
    
    async def _broadcast_to_all_users(self, message: str):
        """Broadcast message to all users"""
        # In production, this would send to all active conversations
        logger.info(f"Broadcasting to all users: {message[:100]}...")
    
    async def _has_subscribers_for_symbol(self, symbol: str) -> bool:
        """Check if any users are subscribed to the given symbol"""
        # In production, this would check the actual user database
        # For now, return True to simulate having subscribers
        return True

# Bot initialization function
def create_app() -> web.Application:
    """Create the enhanced web application with MCP integration"""
    
    # Create adapter and bot
    memory_storage = MemoryStorage()
    conversation_state = ConversationState(memory_storage)
    user_state = UserState(memory_storage)
    
    bot = CorporateActionsBot(conversation_state, user_state)
    
    # Initialize enhanced notification service
    notification_service = EnhancedNotificationService(bot)
    
    # Create web app
    app = web.Application()
    
    async def messages(req: Request) -> Response:
        """Handle incoming messages with enhanced error handling"""
        try:
            if "application/json" not in req.headers.get("Content-Type", ""):
                return Response(status=415, text="Content-Type must be application/json")
            
            body = await req.json()
            activity = Activity().deserialize(body)
            auth_header = req.headers.get("Authorization", "")
            
            # Process the activity (simplified - in production use proper Teams authentication)
            await bot.on_turn(activity)
            return Response(status=200)
            
        except json.JSONDecodeError:
            logger.error("Invalid JSON in request body")
            return Response(status=400, text="Invalid JSON")
        except Exception as e:
            logger.error(f"Error processing activity: {e}")
            return Response(status=500, text="Internal server error")
    
    async def health(req: Request) -> Response:
        """Enhanced health check endpoint with MCP status"""
        try:
            # Check MCP server health
            mcp_health = mcp_client.get_service_health()
            mcp_status = mcp_health.get("status", "unknown") if "error" not in mcp_health else "unhealthy"
            
            health_data = {
                "status": "healthy" if mcp_status == "healthy" else "degraded",
                "timestamp": datetime.utcnow().isoformat(),
                "service": "teams-bot-enhanced",
                "version": "2.0.0",
                "mcp_integration": {
                    "status": mcp_status,
                    "servers": mcp_health.get("servers", {}) if "error" not in mcp_health else {}
                },
                "features": {
                    "proactive_notifications": True,
                    "enhanced_rag": True,
                    "chat_history": True,
                    "smart_comments": True
                }
            }
            
            status_code = 200 if health_data["status"] == "healthy" else 503
            return json_response(health_data, status=status_code)
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return json_response({
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "service": "teams-bot-enhanced",
                "error": str(e)
            }, status=503)
    
    async def startup_handler(app):
        """Initialize notification service on startup"""
        try:
            await notification_service.initialize_scheduler()
            logger.info("Enhanced Teams bot with MCP integration started successfully")
        except Exception as e:
            logger.error(f"Failed to initialize notification service: {e}")
    
    # Register startup handler
    app.on_startup.append(startup_handler)
    
    # Register routes
    app.router.add_post("/api/messages", messages)
    app.router.add_get("/health", health)
    app.router.add_get("/", lambda req: Response(text="Enhanced Corporate Actions Teams Bot - MCP Enabled"))
    
    return app

if __name__ == "__main__":
    import aiohttp.web
    
    logger.info("Starting Enhanced Corporate Actions Teams Bot with MCP Integration...")
    
    app = create_app()
    
    try:
        logger.info("Bot server starting on port 3978...")
        logger.info("Features enabled: Proactive Notifications, Enhanced RAG, Chat History, Smart Comments")
        logger.info("MCP Servers: RAG, Web Search, Comments")
        
        aiohttp.web.run_app(app, host="0.0.0.0", port=3978)
        
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except Exception as e:
        logger.error(f"Critical error starting bot: {e}")
        raise e

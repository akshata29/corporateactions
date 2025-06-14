"""
Microsoft Teams Bot for Corporate Actions
Provides proactive notifications and interactive queries
"""

import asyncio
import json
import os
from datetime import datetime, time, date, timedelta
from typing import Dict, List, Any
import logging

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
import requests
from aiohttp import web
from aiohttp.web import Request, Response, json_response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MCP Server URLs
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
WEBSEARCH_SERVER_URL = os.getenv("WEBSEARCH_SERVER_URL", "http://localhost:8001")
COMMENTS_SERVER_URL = os.getenv("COMMENTS_SERVER_URL", "http://localhost:8002")

class CorporateActionsBot(TeamsActivityHandler):
    """Teams bot for corporate actions platform"""
    
    def __init__(self, conversation_state: ConversationState, user_state: UserState):
        self.conversation_state = conversation_state
        self.user_state = user_state
        
        # Create state accessors
        self.user_profile_accessor = self.user_state.create_property("UserProfile")
        self.conversation_data_accessor = self.conversation_state.create_property("ConversationData")
    
    async def on_message_activity(self, turn_context: TurnContext):
        """Handle incoming messages"""
        user_message = turn_context.activity.text.strip()
        logger.info(f"Received message: {user_message}")
        
        # Handle different command types
        if user_message.lower().startswith("/help"):
            await self._send_help_message(turn_context)
        elif user_message.lower().startswith("/search"):
            await self._handle_search_command(turn_context, user_message)
        elif user_message.lower().startswith("/events"):
            await self._handle_events_command(turn_context, user_message)
        elif user_message.lower().startswith("/comment"):
            await self._handle_comment_command(turn_context, user_message)
        elif user_message.lower().startswith("/subscribe"):
            await self._handle_subscribe_command(turn_context, user_message)
        elif user_message.lower().startswith("/unsubscribe"):
            await self._handle_unsubscribe_command(turn_context, user_message)
        else:
            # Use RAG for natural language queries
            await self._handle_rag_query(turn_context, user_message)
    
    async def on_members_added_activity(
        self, members_added: List[ChannelAccount], turn_context: TurnContext
    ):
        """Greet new members"""
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await self._send_welcome_message(turn_context)
    
    async def _send_welcome_message(self, turn_context: TurnContext):
        """Send welcome message with introduction"""
        welcome_text = """
        🏦 **Welcome to Corporate Actions Bot!**
        
        I help you stay updated on corporate actions and market events. Here's what I can do:
        
        📊 **Commands:**
        - `/help` - Show this help message
        - `/search [query]` - Search corporate actions
        - `/events` - Show recent events
        - `/comment [event_id] [message]` - Add comment to an event
        - `/subscribe [symbols]` - Subscribe to notifications for specific symbols
        - `/unsubscribe [symbols]` - Unsubscribe from notifications
        
        🤖 **Natural Language:**
        Ask me questions like:
        - "Show me all Apple dividends this month"
        - "What mergers were announced recently?"
        - "Are there any upcoming stock splits?"
        
        📢 **Notifications:**
        I'll send you proactive notifications for:
        - New corporate action announcements
        - Status updates on subscribed events
        - Market open/close summaries
        """
        
        await turn_context.send_activity(MessageFactory.text(welcome_text))
        
        # Send suggested actions
        suggested_actions = SuggestedActions(
            actions=[
                CardAction(
                    title="Recent Events",
                    type=ActionTypes.im_back,
                    value="/events"
                ),
                CardAction(
                    title="Search Actions",
                    type=ActionTypes.im_back,
                    value="/search dividend"
                ),
                CardAction(
                    title="Help",
                    type=ActionTypes.im_back,
                    value="/help"
                )
            ]
        )
        
        message = MessageFactory.text("Choose an action:")
        message.suggested_actions = suggested_actions
        await turn_context.send_activity(message)
    
    async def _send_help_message(self, turn_context: TurnContext):
        """Send help message"""
        help_text = """
        🔍 **Corporate Actions Bot Commands**
        
        **Search & Query:**
        - `/search dividend AAPL` - Search for Apple dividends
        - `/events` - Show recent corporate actions
        - "Show me Tesla stock splits" - Natural language query
        
        **Comments & Collaboration:**
        - `/comment CA-2025-001 This needs clarification` - Add comment
        
        **Notifications:**
        - `/subscribe AAPL,MSFT` - Get notifications for Apple and Microsoft
        - `/unsubscribe TSLA` - Stop Tesla notifications
        
        **Tips:**
        - Use natural language for complex queries
        - Subscribe to symbols you follow regularly
        - Check back for market open/close summaries
        """
        
        await turn_context.send_activity(MessageFactory.text(help_text))
    
    async def _handle_search_command(self, turn_context: TurnContext, message: str):
        """Handle search command"""
        try:
            # Extract search query
            query = message[7:].strip()  # Remove "/search "
            if not query:
                await turn_context.send_activity(
                    MessageFactory.text("Please provide a search query. Example: `/search dividend AAPL`")
                )
                return
            
            await turn_context.send_activity(MessageFactory.text(f"🔍 Searching for: {query}"))
            
            # Call RAG API
            response = requests.post(
                f"{MCP_SERVER_URL}/rag/query",
                params={"query": query, "max_results": 3}
            )
            
            if response.status_code == 200:
                rag_data = response.json()
                answer = rag_data.get("answer", "No results found")
                sources = rag_data.get("sources", [])
                
                # Format response
                formatted_response = f"📊 **Search Results:**\n\n{answer}"
                
                if sources:
                    formatted_response += "\n\n🔗 **Sources:**"
                    for i, source in enumerate(sources[:3], 1):
                        formatted_response += f"\n{i}. {source.get('symbol', 'N/A')} - {source.get('event_type', 'N/A')} (Event: {source.get('event_id', 'N/A')})"
                
                await turn_context.send_activity(MessageFactory.text(formatted_response))
            else:
                await turn_context.send_activity(
                    MessageFactory.text("❌ Sorry, I couldn't complete the search. Please try again later.")
                )
                
        except Exception as e:
            logger.error(f"Error in search command: {e}")
            await turn_context.send_activity(
                MessageFactory.text("❌ An error occurred while searching. Please try again.")
            )
    
    async def _handle_events_command(self, turn_context: TurnContext, message: str):
        """Handle events command"""
        try:
            await turn_context.send_activity(MessageFactory.text("📊 Fetching recent corporate actions..."))
            
            # Call search API for recent events
            search_query = {
                "limit": 5,
                "offset": 0,
                "announcement_date_from": (date.today() - timedelta(days=30)).isoformat()
            }
            
            response = requests.post(f"{MCP_SERVER_URL}/search", json=search_query)
            
            if response.status_code == 200:
                events_data = response.json()
                events = events_data.get("events", [])
                
                if events:
                    events_text = "📈 **Recent Corporate Actions:**\n\n"
                    
                    for event in events[:5]:
                        events_text += f"""
                        🔹 **{event['issuer_name']} ({event['security']['symbol']})**
                        Type: {event['event_type']}
                        Status: {event['status']}
                        Announced: {event['announcement_date']}
                        Event ID: {event['event_id']}
                        
                        """
                    
                    await turn_context.send_activity(MessageFactory.text(events_text))
                else:
                    await turn_context.send_activity(
                        MessageFactory.text("📊 No recent corporate actions found.")
                    )
            else:
                await turn_context.send_activity(
                    MessageFactory.text("❌ Could not retrieve events. Please try again later.")
                )
                
        except Exception as e:
            logger.error(f"Error in events command: {e}")
            await turn_context.send_activity(
                MessageFactory.text("❌ An error occurred while fetching events.")
            )
    
    async def _handle_comment_command(self, turn_context: TurnContext, message: str):
        """Handle comment command"""
        try:
            # Parse command: /comment [event_id] [message]
            parts = message[8:].strip().split(' ', 1)  # Remove "/comment "
            
            if len(parts) < 2:
                await turn_context.send_activity(
                    MessageFactory.text("Please provide event ID and comment. Example: `/comment CA-2025-001 This needs clarification`")
                )
                return
            
            event_id = parts[0]
            comment_content = parts[1]
            
            # Get user info
            user_name = turn_context.activity.from_property.name or "Teams User"
            
            # Create comment
            comment_data = {
                "event_id": event_id,
                "user_name": user_name,
                "organization": "Microsoft Teams",
                "comment_type": "COMMENT",
                "content": comment_content
            }
            
            response = requests.post(f"{COMMENTS_SERVER_URL}/comments", json=comment_data)
            
            if response.status_code == 200:
                await turn_context.send_activity(
                    MessageFactory.text(f"✅ Comment added to event {event_id}")
                )
            else:
                await turn_context.send_activity(
                    MessageFactory.text("❌ Failed to add comment. Please check the event ID and try again.")
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
    
    async def _handle_rag_query(self, turn_context: TurnContext, query: str):
        """Handle natural language RAG query"""
        try:
            await turn_context.send_activity(MessageFactory.text("🤖 Let me search that for you..."))
            
            response = requests.post(
                f"{MCP_SERVER_URL}/rag/query",
                params={"query": query, "max_results": 3, "include_comments": True}
            )
            
            if response.status_code == 200:
                rag_data = response.json()
                answer = rag_data.get("answer", "I couldn't find relevant information.")
                sources = rag_data.get("sources", [])
                confidence = rag_data.get("confidence_score", 0.0)
                
                # Format response
                formatted_response = f"🤖 **AI Assistant Response:**\n\n{answer}"
                
                if confidence > 0.7:
                    formatted_response += f"\n\n✅ Confidence: High ({confidence:.1%})"
                elif confidence > 0.4:
                    formatted_response += f"\n\n⚠️ Confidence: Medium ({confidence:.1%})"
                else:
                    formatted_response += f"\n\n❓ Confidence: Low ({confidence:.1%})"
                
                if sources:
                    formatted_response += "\n\n📋 **Related Events:**"
                    for source in sources[:3]:
                        formatted_response += f"\n• {source.get('symbol', 'N/A')} - {source.get('event_type', 'N/A')}"
                
                await turn_context.send_activity(MessageFactory.text(formatted_response))
            else:
                await turn_context.send_activity(
                    MessageFactory.text("❌ I encountered an issue processing your request. Please try rephrasing your question.")
                )
                
        except Exception as e:
            logger.error(f"Error in RAG query: {e}")
            await turn_context.send_activity(
                MessageFactory.text("❌ An error occurred while processing your query.")
            )

class NotificationService:
    """Service to send proactive notifications"""
    
    def __init__(self):
        self.scheduled_notifications = []
    
    async def schedule_market_notifications(self):
        """Schedule market open/close notifications"""
        # Market open notification (9:30 AM ET)
        market_open_time = time(9, 30)  # 9:30 AM
        market_close_time = time(16, 0)  # 4:00 PM
        
        # This would be implemented with a proper scheduler in production
        logger.info("Notification service initialized")
    
    async def send_event_notification(self, event_data: Dict[str, Any], subscribers: List[str]):
        """Send notification about new corporate action"""
        try:
            notification_text = f"""
            🔔 **New Corporate Action Alert**
            
            **{event_data['issuer_name']} ({event_data['security']['symbol']})**
            Type: {event_data['event_type']}
            Status: {event_data['status']}
            Announced: {event_data['announcement_date']}
            
            Description: {event_data['description']}
            
            Use `/comment {event_data['event_id']} [your message]` to add comments or questions.
            """
            
            # In production, this would send to actual Teams channels/users
            logger.info(f"Notification sent for event {event_data['event_id']} to {len(subscribers)} subscribers")
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")

# Bot initialization function
def create_app() -> web.Application:
    """Create the web application"""
    
    # Create adapter and bot
    memory_storage = MemoryStorage()
    conversation_state = ConversationState(memory_storage)
    user_state = UserState(memory_storage)
    
    bot = CorporateActionsBot(conversation_state, user_state)
    notification_service = NotificationService()
    
    # Create web app
    app = web.Application()
    
    async def messages(req: Request) -> Response:
        """Handle incoming messages"""
        if "application/json" in req.headers["Content-Type"]:
            body = await req.json()
        else:
            return Response(status=415)
        
        activity = Activity().deserialize(body)
        auth_header = req.headers["Authorization"] if "Authorization" in req.headers else ""
        
        try:
            # Process the activity (simplified - in production use proper Teams authentication)
            await bot.on_turn(activity)
            return Response(status=200)
        except Exception as e:
            logger.error(f"Error processing activity: {e}")
            return Response(status=500)
    
    async def health(req: Request) -> Response:
        """Health check endpoint"""
        return json_response({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "teams-bot"
        })
    
    app.router.add_post("/api/messages", messages)
    app.router.add_get("/health", health)
    
    return app

if __name__ == "__main__":
    import aiohttp.web
    
    app = create_app()
    
    try:
        aiohttp.web.run_app(app, host="0.0.0.0", port=3978)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise e

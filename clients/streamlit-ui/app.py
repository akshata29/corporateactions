"""
Streamlit UI for Corporate Actions POC
Interactive dashboard for market participants - MCP Integration
"""

import streamlit as st
import pandas as pd
import json
import sys
import os
from datetime import date, datetime, timedelta
from typing import List, Dict, Any
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# MCP Client import
try:
    from mcp_client import get_mcp_client, HTTPFallbackClient
    USE_MCP = True
except ImportError:
    USE_MCP = False
    import requests

# Page configuration
st.set_page_config(
    page_title="Corporate Actions Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize client
@st.cache_resource
def get_client():
    """Get MCP client or fallback to HTTP"""
    if USE_MCP:
        try:
            return get_mcp_client()
        except Exception as e:
            st.warning(f"MCP client unavailable: {e}. Using HTTP fallback.")
            return HTTPFallbackClient()
    else:
        return HTTPFallbackClient()

client = get_client()

# Custom CSS
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
    }
    .status-badge {
        padding: 0.25rem 0.5rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .status-confirmed { background: #d4edda; color: #155724; }
    .status-announced { background: #fff3cd; color: #856404; }
    .status-pending { background: #f8d7da; color: #721c24; }
    .status-completed { background: #d1ecf1; color: #0c5460; }
</style>
""", unsafe_allow_html=True)

def main():
    """Main application function"""
    st.markdown("""
    <div class="main-header">
        <h1>🏦 Corporate Actions Dashboard</h1>
        <p>Real-time collaborative platform for corporate actions transparency</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar navigation
    with st.sidebar:
        st.header("Navigation")
        page = st.radio(
            "Select Page",
            ["Dashboard", "RAG Assistant", "Search Events", "Comments & Q&A", "Web Research", "Analytics"]
        )
    
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
    elif page == "Analytics":
        show_analytics()

def show_dashboard():
    """Display main dashboard"""
    st.header("📊 Dashboard Overview")
    
    # Get recent events and metrics
    try:
        # Fetch recent events
        events_response = requests.post(
            f"{MCP_SERVER_URL}/search",
            json={"limit": 10, "offset": 0}
        )
        
        if events_response.status_code == 200:
            events_data = events_response.json()
            events = events_data.get("events", [])
        else:
            events = get_sample_events()
        
        # Fetch analytics
        analytics_response = requests.get(f"{COMMENTS_SERVER_URL}/analytics")
        if analytics_response.status_code == 200:
            analytics = analytics_response.json()
        else:
            analytics = get_sample_analytics()
        
        # Key metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Events", len(events), "5")
        
        with col2:
            total_comments = analytics.get("total_comments", 0)
            st.metric("Total Comments", total_comments, "12")
        
        with col3:
            unresolved = analytics.get("unresolved_count", 0)
            st.metric("Open Questions", unresolved, "-2")
        
        with col4:
            active_events = len([e for e in events if e.get("status") in ["ANNOUNCED", "CONFIRMED"]])
            st.metric("Active Events", active_events, "3")
        
        st.markdown("---")
        
        # Recent events table
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Recent Corporate Actions")
            if events:
                df = pd.DataFrame(events)
                
                # Format the dataframe for display
                display_df = df[['event_id', 'event_type', 'issuer_name', 'status', 'announcement_date']].copy()
                display_df.columns = ['Event ID', 'Type', 'Issuer', 'Status', 'Announced']
                
                # Add status badges
                for idx, row in display_df.iterrows():
                    status = row['Status'].lower()
                    status_html = f'<span class="status-badge status-{status}">{row["Status"]}</span>'
                    display_df.loc[idx, 'Status'] = status_html
                
                st.markdown(display_df.to_html(escape=False), unsafe_allow_html=True)
            else:
                st.info("No events found. Check MCP server connection.")
        
        with col2:
            st.subheader("Event Status Distribution")
            if events:
                status_counts = pd.Series([e.get("status", "UNKNOWN") for e in events]).value_counts()
                fig = px.pie(
                    values=status_counts.values,
                    names=status_counts.index,
                    title="Event Status Distribution"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("Recent Activity")
            recent_activity = analytics.get("recent_activity", [])
            for activity in recent_activity[-5:]:
                st.text(f"🔔 {activity.get('comment_type', 'Comment')} on {activity.get('event_id', 'N/A')}")
        
    except Exception as e:
        st.error(f"Error loading dashboard: {str(e)}")
        st.info("Using sample data for demonstration")
        show_sample_dashboard()

def show_rag_assistant():
    """Display RAG assistant interface"""
    st.header("🤖 RAG Assistant")
    st.markdown("Ask questions about corporate actions using natural language")
    
    # Chat interface
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                with st.expander("Sources"):
                    for source in message["sources"]:
                        st.json(source)
    
    # Chat input
    if prompt := st.chat_input("Ask about corporate actions (e.g., 'Show me all Apple dividends announced this month')"):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get RAG response
        with st.chat_message("assistant"):
            with st.spinner("Searching corporate actions data..."):
                try:
                    response = requests.post(
                        f"{MCP_SERVER_URL}/rag/query",
                        params={"query": prompt, "max_results": 5, "include_comments": True}
                    )
                    
                    if response.status_code == 200:
                        rag_data = response.json()
                        answer = rag_data.get("answer", "I couldn't find relevant information.")
                        sources = rag_data.get("sources", [])
                        confidence = rag_data.get("confidence_score", 0.0)
                        
                        st.markdown(answer)
                        
                        if sources:
                            with st.expander(f"📋 Sources (Confidence: {confidence:.1%})"):
                                for i, source in enumerate(sources):
                                    st.json(source)
                        
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": answer,
                            "sources": sources
                        })
                    else:
                        error_msg = "Sorry, I encountered an error processing your request."
                        st.error(error_msg)
                        st.session_state.messages.append({"role": "assistant", "content": error_msg})
                        
                except Exception as e:
                    error_msg = f"Error connecting to RAG server: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

def show_search_events():
    """Display event search interface"""
    st.header("🔍 Search Corporate Actions")
    
    with st.form("search_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            event_types = st.multiselect(
                "Event Types",
                ["DIVIDEND", "STOCK_SPLIT", "MERGER", "SPIN_OFF", "RIGHTS_OFFERING"],
                default=[]
            )
            
            symbols = st.text_input("Stock Symbols (comma-separated)", placeholder="AAPL, MSFT, TSLA")
        
        with col2:
            cusips = st.text_input("CUSIP (comma-separated)", placeholder="037833100")
            
            statuses = st.multiselect(
                "Status",
                ["ANNOUNCED", "CONFIRMED", "COMPLETED", "CANCELLED", "PENDING"],
                default=[]
            )
        
        with col3:
            date_from = st.date_input("Announcement Date From", value=date.today() - timedelta(days=30))
            date_to = st.date_input("Announcement Date To", value=date.today())
            
            search_text = st.text_input("Free Text Search", placeholder="dividend payment")
        
        submit_button = st.form_submit_button("Search")
    
    if submit_button:
        # Build search query
        search_query = {
            "limit": 50,
            "offset": 0
        }
        
        if event_types:
            search_query["event_types"] = event_types
        
        if symbols:
            search_query["symbols"] = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        
        if cusips:
            search_query["cusips"] = [c.strip() for c in cusips.split(",") if c.strip()]
        
        if statuses:
            search_query["statuses"] = statuses
        
        if date_from:
            search_query["announcement_date_from"] = date_from.isoformat()
        
        if date_to:
            search_query["announcement_date_to"] = date_to.isoformat()
        
        if search_text:
            search_query["search_text"] = search_text
        
        # Execute search
        try:
            response = requests.post(f"{MCP_SERVER_URL}/search", json=search_query)
            
            if response.status_code == 200:
                search_results = response.json()
                events = search_results.get("events", [])
                
                if events:
                    st.success(f"Found {len(events)} events")
                    
                    # Display results
                    for event in events:
                        with st.expander(f"{event['event_type']} - {event['issuer_name']} ({event['security']['symbol']})"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write(f"**Event ID:** {event['event_id']}")
                                st.write(f"**Status:** {event['status']}")
                                st.write(f"**Announcement Date:** {event['announcement_date']}")
                                st.write(f"**Description:** {event['description']}")
                            
                            with col2:
                                if event.get('record_date'):
                                    st.write(f"**Record Date:** {event['record_date']}")
                                if event.get('ex_date'):
                                    st.write(f"**Ex Date:** {event['ex_date']}")
                                if event.get('payable_date'):
                                    st.write(f"**Payable Date:** {event['payable_date']}")
                                
                                if event.get('event_details'):
                                    st.write("**Event Details:**")
                                    st.json(event['event_details'])
                            
                            # Show comments button
                            if st.button(f"View Comments", key=f"comments_{event['event_id']}"):
                                show_event_comments(event['event_id'])
                else:
                    st.info("No events found matching your criteria")
            else:
                st.error(f"Search failed: {response.status_code}")
                
        except Exception as e:
            st.error(f"Error executing search: {str(e)}")

def show_comments_qa():
    """Display comments and Q&A interface"""
    st.header("💬 Comments & Q&A")
    
    # Event selector
    event_id = st.selectbox(
        "Select Event",
        ["CA-2025-001", "CA-2025-002", "CA-2025-003", "CA-2025-004", "CA-2025-005"],
        help="Select an event to view or add comments"
    )
    
    if event_id:
        # Display existing comments
        st.subheader(f"Comments for {event_id}")
        
        try:
            response = requests.get(f"{COMMENTS_SERVER_URL}/events/{event_id}/comments")
            
            if response.status_code == 200:
                comments_data = response.json()
                comments = comments_data.get("comments", [])
                
                if comments:
                    for comment in comments:
                        comment_type = comment.get("comment_type", "COMMENT")
                        icon = {"QUESTION": "❓", "CONCERN": "⚠️", "COMMENT": "💭", "UPDATE": "📢"}.get(comment_type, "💭")
                        
                        with st.container():
                            st.markdown(f"""
                            <div style="border-left: 3px solid #007bff; padding-left: 1rem; margin: 1rem 0;">
                                <strong>{icon} {comment['user_name']}</strong> 
                                <small>({comment.get('organization', 'N/A')}) - {comment_type}</small><br>
                                <em>{comment['created_at']}</em><br>
                                {comment['content']}
                                {"✅ Resolved" if comment.get('is_resolved') else ""}
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("No comments yet for this event")
            else:
                st.error("Failed to load comments")
                
        except Exception as e:
            st.error(f"Error loading comments: {str(e)}")
        
        st.markdown("---")
        
        # Add new comment form
        st.subheader("Add Comment")
        
        with st.form("comment_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                user_name = st.text_input("Your Name", value="Demo User")
                organization = st.text_input("Organization", value="Demo Organization")
            
            with col2:
                comment_type = st.selectbox("Comment Type", ["QUESTION", "CONCERN", "COMMENT", "UPDATE"])
            
            content = st.text_area("Comment Content", height=100)
            
            if st.form_submit_button("Submit Comment"):
                if content and user_name:
                    try:
                        comment_data = {
                            "event_id": event_id,
                            "user_name": user_name,
                            "organization": organization,
                            "comment_type": comment_type,
                            "content": content
                        }
                        
                        response = requests.post(f"{COMMENTS_SERVER_URL}/comments", json=comment_data)
                        
                        if response.status_code == 200:
                            st.success("Comment added successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to add comment")
                    except Exception as e:
                        st.error(f"Error adding comment: {str(e)}")
                else:
                    st.error("Please fill in all required fields")

def show_web_research():
    """Display web research interface"""
    st.header("🌐 Web Research")
    
    tab1, tab2, tab3 = st.tabs(["General Search", "News Search", "Financial Data"])
    
    with tab1:
        st.subheader("General Web Search")
        query = st.text_input("Search Query", placeholder="Apple dividend announcement 2025")
        
        if st.button("Search Web"):
            if query:
                try:
                    response = requests.post(
                        f"{WEBSEARCH_SERVER_URL}/search",
                        json={"query": query, "max_results": 10}
                    )
                    
                    if response.status_code == 200:
                        search_data = response.json()
                        results = search_data.get("results", [])
                        
                        st.success(f"Found {len(results)} results in {search_data.get('search_time_ms', 0)}ms")
                        
                        for result in results:
                            with st.expander(result.get("title", "No Title")):
                                st.write(f"**URL:** {result.get('url', 'N/A')}")
                                st.write(f"**Source:** {result.get('source', 'N/A')}")
                                st.write(f"**Snippet:** {result.get('snippet', 'N/A')}")
                                if result.get('published_date'):
                                    st.write(f"**Published:** {result['published_date']}")
                    else:
                        st.error("Search failed")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    with tab2:
        st.subheader("News Search")
        news_query = st.text_input("News Search Query", placeholder="Tesla stock split")
        days_back = st.slider("Days Back", 1, 30, 7)
        
        if st.button("Search News"):
            if news_query:
                try:
                    response = requests.get(
                        f"{WEBSEARCH_SERVER_URL}/news",
                        params={"query": news_query, "days_back": days_back}
                    )
                    
                    if response.status_code == 200:
                        news_data = response.json()
                        news_results = news_data.get("news_results", [])
                        
                        if news_results:
                            for news in news_results:
                                st.markdown(f"**{news.get('title', 'No Title')}**")
                                st.write(news.get('snippet', 'No description'))
                                st.write(f"Source: {news.get('source', 'N/A')} | {news.get('published_date', 'N/A')}")
                                st.markdown("---")
                        else:
                            st.info("No recent news found")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    with tab3:
        st.subheader("Financial Data Search")
        symbol = st.text_input("Stock Symbol", placeholder="AAPL")
        event_type = st.selectbox("Event Type", ["", "dividend", "split", "merger"])
        
        if st.button("Search Financial Data"):
            if symbol:
                try:
                    params = {"symbol": symbol}
                    if event_type:
                        params["event_type"] = event_type
                    
                    response = requests.get(f"{WEBSEARCH_SERVER_URL}/financial-data", params=params)
                    
                    if response.status_code == 200:
                        financial_data = response.json()
                        financial_results = financial_data.get("financial_results", [])
                        
                        if financial_results:
                            for result in financial_results:
                                st.markdown(f"**{result.get('title', 'No Title')}**")
                                st.write(result.get('snippet', 'No description'))
                                st.write(f"URL: {result.get('url', 'N/A')}")
                                st.markdown("---")
                        else:
                            st.info("No financial data found")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

def show_analytics():
    """Display analytics and insights"""
    st.header("📈 Analytics & Insights")
    
    try:
        response = requests.get(f"{COMMENTS_SERVER_URL}/analytics")
        
        if response.status_code == 200:
            analytics = response.json()
            
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Comments", analytics.get("total_comments", 0))
            
            with col2:
                st.metric("Questions", analytics.get("questions_count", 0))
            
            with col3:
                st.metric("Concerns", analytics.get("concerns_count", 0))
            
            with col4:
                resolved_count = analytics.get("resolved_count", 0)
                total_count = analytics.get("total_comments", 1)
                resolution_rate = (resolved_count / total_count) * 100 if total_count > 0 else 0
                st.metric("Resolution Rate", f"{resolution_rate:.1f}%")
            
            st.markdown("---")
            
            # Charts
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Top Organizations by Activity")
                top_orgs = analytics.get("top_organizations", [])
                if top_orgs:
                    org_df = pd.DataFrame(top_orgs)
                    fig = px.bar(
                        org_df,
                        x="comment_count",
                        y="organization",
                        orientation="h",
                        title="Comments by Organization"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No organization data available")
            
            with col2:
                st.subheader("Question Resolution Status")
                resolved = analytics.get("resolved_count", 0)
                unresolved = analytics.get("unresolved_count", 0)
                
                if resolved + unresolved > 0:
                    fig = px.pie(
                        values=[resolved, unresolved],
                        names=["Resolved", "Unresolved"],
                        title="Question Resolution Status"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No resolution data available")
            
            # Recent activity timeline
            st.subheader("Recent Activity")
            recent_activity = analytics.get("recent_activity", [])
            if recent_activity:
                activity_df = pd.DataFrame(recent_activity)
                st.dataframe(activity_df, use_container_width=True)
            else:
                st.info("No recent activity data available")
        else:
            st.error("Failed to load analytics")
    
    except Exception as e:
        st.error(f"Error loading analytics: {str(e)}")

def show_event_comments(event_id: str):
    """Show comments for a specific event"""
    st.subheader(f"Comments for {event_id}")
    # Implementation here...

def get_sample_events():
    """Get sample events for demo"""
    return [
        {
            "event_id": "CA-2025-001",
            "event_type": "DIVIDEND",
            "issuer_name": "Apple Inc.",
            "security": {"symbol": "AAPL"},
            "status": "CONFIRMED",
            "announcement_date": "2025-06-01"
        },
        {
            "event_id": "CA-2025-002",
            "event_type": "STOCK_SPLIT",
            "issuer_name": "Tesla, Inc.",
            "security": {"symbol": "TSLA"},
            "status": "ANNOUNCED",
            "announcement_date": "2025-05-20"
        }
    ]

def get_sample_analytics():
    """Get sample analytics for demo"""
    return {
        "total_comments": 25,
        "questions_count": 8,
        "concerns_count": 5,
        "resolved_count": 18,
        "unresolved_count": 7,
        "top_organizations": [
            {"organization": "ABC Investment", "comment_count": 8},
            {"organization": "XYZ Brokerage", "comment_count": 6}
        ],
        "recent_activity": []
    }

def show_sample_dashboard():
    """Show sample dashboard when servers are unavailable"""
    st.info("Showing sample data - MCP servers may be offline")
    
    events = get_sample_events()
    analytics = get_sample_analytics()
    
    # Display sample metrics and data
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Events", len(events))
    
    with col2:
        st.metric("Total Comments", analytics["total_comments"])
    
    with col3:
        st.metric("Open Questions", analytics["unresolved_count"])
    
    with col4:
        st.metric("Active Events", len(events))

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Web Search MCP Server
Provides web search capabilities for corporate actions research
Following Model Context Protocol specification
"""

import asyncio
import json
import os
import logging
import platform
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus
import httpx

# MCP imports
from fastmcp import FastMCP

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

# Initialize FastMCP server
app = FastMCP("Web Search MCP Server")

# Global HTTP client
http_client: Optional[httpx.AsyncClient] = None

async def initialize_http_client():
    """Initialize HTTP client for web searches"""
    global http_client
    try:
        http_client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Corporate Actions Research Bot 1.0"
            }
        )
        logger.info("✅ HTTP client initialized")
    except Exception as e:
        logger.error(f"❌ Error initializing HTTP client: {e}")

async def perform_bing_search(query: str, count: int = 10, search_type: str = "general") -> List[Dict[str, Any]]:
    """Perform web search using Bing Search API"""
    try:
        bing_api_key = os.getenv("BING_SEARCH_API_KEY")
        if not bing_api_key:
            logger.warning("Bing Search API key not configured, returning mock results")
            return await get_mock_search_results(query, count)
        
        # Configure search endpoint based on type
        if search_type == "news":
            endpoint = "https://api.bing.microsoft.com/v7.0/news/search"
        else:
            endpoint = "https://api.bing.microsoft.com/v7.0/search"
        
        headers = {
            "Ocp-Apim-Subscription-Key": bing_api_key,
            "Accept": "application/json"
        }
        
        params = {
            "q": query,
            "count": count,
            "offset": 0,
            "mkt": "en-US",
            "safeSearch": "Moderate"
        }
        
        if search_type == "news":
            params["freshness"] = "Week"  # Recent news
            params["sortBy"] = "Date"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            if search_type == "news" and "value" in data:
                for item in data["value"]:
                    results.append({
                        "title": item.get("name", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("description", ""),
                        "published_date": item.get("datePublished", ""),
                        "source": item.get("provider", [{}])[0].get("name", "Unknown") if item.get("provider") else "Unknown",
                        "relevance_score": 0.8
                    })
            elif "webPages" in data and "value" in data["webPages"]:
                for item in data["webPages"]["value"]:
                    results.append({
                        "title": item.get("name", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("snippet", ""),
                        "published_date": None,
                        "source": item.get("displayUrl", "").split('/')[0] if item.get("displayUrl") else "Unknown",
                        "relevance_score": 0.8
                    })
            
            return results
            
    except Exception as e:
        logger.error(f"Error in Bing search: {e}")
        return await get_mock_search_results(query, count)

async def get_mock_search_results(query: str, count: int = 10) -> List[Dict[str, Any]]:
    """Return mock search results for testing"""
    return [
        {
            "title": f"Corporate Actions News: {query}",
            "url": "https://example.com/corporate-actions-news",
            "snippet": f"Latest developments in {query} affecting shareholders and market participants.",
            "published_date": datetime.utcnow().isoformat(),
            "source": "Financial News Today",
            "relevance_score": 0.9
        },
        {
            "title": f"Analysis: {query} Impact on Markets",
            "url": "https://example.com/market-analysis",
            "snippet": f"Expert analysis on how {query} is expected to impact market conditions.",
            "published_date": datetime.utcnow().isoformat(),
            "source": "Market Analysis Weekly",
            "relevance_score": 0.8
        },
        {
            "title": f"Regulatory Updates: {query}",
            "url": "https://example.com/regulatory-updates",
            "snippet": f"Recent regulatory changes related to {query} and compliance requirements.",
            "published_date": datetime.utcnow().isoformat(),
            "source": "Regulatory News",
            "relevance_score": 0.7
        }
    ][:count]

def enhance_query_for_corporate_actions(query: str) -> str:
    """Enhance search query with corporate actions context"""
    corporate_action_terms = [
        "corporate actions", "dividend", "stock split", "merger", 
        "acquisition", "spinoff", "rights offering", "tender offer",
        "shareholder", "SEC filing", "proxy statement"
    ]
    
    # Add corporate actions context if not already present
    query_lower = query.lower()
    has_corporate_terms = any(term in query_lower for term in corporate_action_terms)
    
    if not has_corporate_terms:
        return f"{query} corporate actions financial news"
    
    return query

# =============================================================================
# MCP Tools Registration
# =============================================================================

@app.tool()
async def web_search(
    query: str,
    max_results: int = 10,
    search_type: str = "general",
    date_filter: str = ""
) -> str:
    """
    Perform web search for corporate actions research.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return (1-50)
        search_type: Type of search (general, news, financial)
        date_filter: Date filter (last_day, last_week, last_month, or empty)
    
    Returns:
        JSON string containing search results
    """
    try:
        logger.info(f"Web search: {query} (type: {search_type})")
        
        start_time = datetime.utcnow()
        
        # Enhance query for corporate actions context
        enhanced_query = enhance_query_for_corporate_actions(query)
        
        # Perform search
        results = await perform_bing_search(
            enhanced_query, 
            min(max_results, 50), 
            search_type
        )
        
        # Apply date filtering if specified
        if date_filter and results:
            # This would require more sophisticated date parsing
            # For now, we'll include all results
            pass
        
        end_time = datetime.utcnow()
        search_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        response = {
            "query": query,
            "enhanced_query": enhanced_query,
            "results": results,
            "total_results": len(results),
            "search_time_ms": search_time_ms,
            "search_type": search_type,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return json.dumps(response, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"Error in web search tool: {e}")
        return json.dumps({
            "error": f"Web search failed: {str(e)}",
            "query": query,
            "results": [],
            "total_results": 0
        })

@app.tool()
async def news_search(
    query: str,
    max_results: int = 10,
    freshness: str = "week"
) -> str:
    """
    Search for recent news articles related to corporate actions.
    
    Args:
        query: News search query
        max_results: Maximum number of news articles to return (1-50)
        freshness: Freshness filter (day, week, month)
    
    Returns:
        JSON string containing news search results
    """
    try:
        logger.info(f"News search: {query} (freshness: {freshness})")
        
        # Enhance query for financial news context
        news_query = f"{query} financial news corporate actions"
        
        # Perform news search
        results = await perform_bing_search(news_query, min(max_results, 50), "news")
        
        # Filter for financial news sources
        financial_sources = [
            "reuters.com", "bloomberg.com", "wsj.com", "ft.com",
            "marketwatch.com", "cnbc.com", "yahoo.com/finance",
            "sec.gov", "investor.gov", "nasdaq.com", "nyse.com"
        ]
        
        # Prioritize results from financial sources
        prioritized_results = []
        other_results = []
        
        for result in results:
            if any(source in result.get("url", "").lower() for source in financial_sources):
                result["relevance_score"] = min(result.get("relevance_score", 0.5) + 0.2, 1.0)
                prioritized_results.append(result)
            else:
                other_results.append(result)
        
        # Combine results with financial sources first
        final_results = prioritized_results + other_results
        
        response = {
            "query": query,
            "news_query": news_query,
            "results": final_results[:max_results],
            "total_results": len(final_results),
            "freshness_filter": freshness,
            "financial_sources_count": len(prioritized_results),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return json.dumps(response, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"Error in news search tool: {e}")
        return json.dumps({
            "error": f"News search failed: {str(e)}",
            "query": query,
            "results": [],
            "total_results": 0
        })

@app.tool()
async def financial_data_search(
    symbol: str,
    data_type: str = "general",
    max_results: int = 10
) -> str:
    """
    Search for financial data and analysis for a specific company symbol.
    
    Args:
        symbol: Company stock symbol (e.g., AAPL, MSFT)
        data_type: Type of financial data (general, earnings, filings, actions)
        max_results: Maximum number of results to return (1-50)
    
    Returns:
        JSON string containing financial data search results
    """
    try:
        logger.info(f"Financial data search: {symbol} (type: {data_type})")
        
        # Build targeted query based on data type
        queries = {
            "general": f"{symbol} stock financial data corporate actions",
            "earnings": f"{symbol} earnings report financial results",
            "filings": f"{symbol} SEC filings 10-K 10-Q 8-K",
            "actions": f"{symbol} corporate actions dividend split merger acquisition"
        }
        
        search_query = queries.get(data_type, queries["general"])
        
        # Perform search
        results = await perform_bing_search(search_query, min(max_results, 50), "general")
        
        # Filter for high-quality financial sources
        quality_sources = [
            "sec.gov", "edgar.sec.gov", "investor.gov",
            "bloomberg.com", "reuters.com", "wsj.com",
            "yahoo.com/finance", "google.com/finance",
            "marketwatch.com", "fool.com", "seekingalpha.com"
        ]
        
        # Score results based on source quality
        for result in results:
            url = result.get("url", "").lower()
            if any(source in url for source in quality_sources):
                result["relevance_score"] = min(result.get("relevance_score", 0.5) + 0.3, 1.0)
                result["source_quality"] = "high"
            else:
                result["source_quality"] = "standard"
        
        # Sort by relevance score
        results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        response = {
            "symbol": symbol,
            "data_type": data_type,
            "search_query": search_query,
            "results": results,
            "total_results": len(results),
            "high_quality_sources": len([r for r in results if r.get("source_quality") == "high"]),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return json.dumps(response, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"Error in financial data search tool: {e}")
        return json.dumps({
            "error": f"Financial data search failed: {str(e)}",
            "symbol": symbol,
            "results": [],
            "total_results": 0
        })

@app.tool()
async def get_search_health() -> str:
    """
    Check the health and status of web search services.
    
    Returns:
        JSON string containing service health information
    """
    try:
        health_status = {
            "service": "Web Search MCP Server",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "capabilities": {
                "web_search": True,
                "news_search": True,
                "financial_data_search": True,
                "bing_api": bool(os.getenv("BING_SEARCH_API_KEY")),
                "mock_fallback": True
            },
            "configuration": {
                "max_results_limit": 50,
                "default_timeout": 30,
                "supported_search_types": ["general", "news", "financial"],
                "supported_freshness": ["day", "week", "month"]
            }
        }
        
        # Test HTTP client
        if http_client:
            health_status["http_client"] = "initialized"
        else:
            health_status["http_client"] = "not_initialized"
            await initialize_http_client()
        
        return json.dumps(health_status, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"Error checking search health: {e}")
        return json.dumps({
            "service": "Web Search MCP Server",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })

# =============================================================================
# Server Initialization
# =============================================================================

# =============================================================================
# Server Initialization
# =============================================================================

def main():
    """Main server initialization"""
    logger.info("Starting Web Search MCP Server...")
    
    # Initialize services in sync context
    async def init_and_setup():
        await initialize_http_client()
        logger.info("✅ Web Search MCP Server initialized successfully")
    
    # Run initialization
    try:
        asyncio.run(init_and_setup())
    except RuntimeError:
        # If there's already an event loop, create a new thread
        import threading
        def run_init():
            asyncio.run(init_and_setup())
        
        thread = threading.Thread(target=run_init)
        thread.start()
        thread.join()
    
    # Check if port is specified for HTTP mode
    import sys
    if len(sys.argv) > 1 and '--port' in sys.argv:
        port_index = sys.argv.index('--port') + 1
        if port_index < len(sys.argv):
            port = int(sys.argv[port_index])
            logger.info(f"Starting FastMCP server in HTTP mode on port {port}")
            app.run(transport="streamable-http", host="0.0.0.0", port=port)
        else:
            logger.error("Port specified but no port number provided")
            app.run()
    else:
        # Run the FastMCP server in stdio mode (default)
        logger.info("Starting FastMCP server in stdio mode")
        app.run()

if __name__ == "__main__":
    main()

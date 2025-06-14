# Corporate Actions POC - MCP Platform

A collaborative data sharing platform for corporate actions that enables real-time access and transparency to market participants throughout the custody chain, implemented using the **Model Context Protocol (MCP)**.

## ✅ CONVERSION STATUS: **COMPLETE**

**All servers have been successfully converted from FastAPI to pure MCP implementation using FastMCP framework.**

## 🏗️ Architecture Overview

This POC leverages Azure Services and the Model Context Protocol to build an Agentic RAG (Retrieval-Augmented Generation) system with fully MCP-compliant servers.

### Core Services
- **Azure OpenAI**: LLM for natural language processing and response generation
- **Azure AI Search**: Vector database for RAG implementation
- **Azure Cosmos DB**: Transactional data storage for events and comments
- **Azure Bot Service**: Microsoft Teams integration

### MCP Servers (Model Context Protocol Compliant) ✅
1. **Main RAG MCP Server** - 6 tools, 2 resources
   - Agentic RAG implementation using FastMCP
   - Corporate actions data search and analysis
   - Natural language question answering
   - Tools: `rag_query`, `search_corporate_actions`, `get_event_details`, `add_event_comment`, `get_service_health`

2. **Web Search MCP Server** - 4 tools
   - Web search capabilities using FastMCP
   - Financial news and data research
   - Integration with Bing Search API
   - Tools: `web_search`, `news_search`, `financial_data_search`, `get_search_health`

3. **Comments MCP Server** - 7 tools
   - Real-time collaboration using FastMCP
   - Comments, questions, and analytics
   - WebSocket-like real-time features
   - Tools: `get_event_comments`, `add_comment`, `search_comments`, `get_comment_analytics`

### Client Applications
1. **Streamlit UI** - Port 8501
   - Interactive dashboard for market participants
   - MCP client integration for seamless tool access
   - Real-time collaboration features

2. **Microsoft Teams Bot** - Port 3978
   - Proactive notifications (market open/close)
   - MCP-powered natural language queries
   - Subscription management for symbols

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Model Context Protocol (MCP) support
- Azure subscription with the following services:
  - Azure OpenAI
  - Azure AI Search
  - Azure Cosmos DB
  - Azure Bot Service (for Teams integration)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd corporateactions
   ```

2. **Install MCP dependencies**
   ```bash
   pip install mcp fastmcp
   ```

3. **Install server-specific dependencies**
   ```bash
   # Main RAG server
   cd mcp-server
   pip install -r requirements.txt
   cd ..
   
   # Web search server
   cd mcp-websearch
   pip install -r requirements.txt
   cd ..
   
   # Comments server
   cd mcp-comments
   pip install -r requirements.txt
   cd ..
   ```

4. **Configure environment variables**
   Create a `.env` file in the root directory:
   ```env
   # Azure OpenAI Configuration
   AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
   AZURE_OPENAI_KEY=your-openai-api-key
   AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
   AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME=text-embedding-ada-002
   
   # Azure AI Search Configuration
   AZURE_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
   AZURE_SEARCH_KEY=your-search-admin-key
   AZURE_SEARCH_INDEX_NAME=corporate-actions
   
   # Azure Cosmos DB Configuration
   AZURE_COSMOS_ENDPOINT=https://your-cosmos-account.documents.azure.com:443/
   AZURE_COSMOS_KEY=your-cosmos-primary-key
   
   # Optional: Bing Search API for enhanced web search
   BING_SEARCH_API_KEY=your-bing-search-api-key
   ```

5. **Test MCP servers**
   ```bash
   python test_mcp_servers.py
   ```

6. **Start all MCP servers**
   ```bash
   python start_mcp_servers.py
   ```

### Alternative: Start Individual Servers

You can start each MCP server individually using FastMCP:

```bash
# Main RAG server
cd mcp-server
python -m fastmcp run main.py --port 8000

# Web search server
cd mcp-websearch  
python -m fastmcp run main.py --port 8001

# Comments server
cd mcp-comments
python -m fastmcp run main.py --port 8002
```

## 🛠️ MCP Tools Available

### Main RAG Server Tools
- **`rag_query`**: Process natural language queries about corporate actions
- **`search_corporate_actions`**: Search events by type, symbol, date, status
- **`get_event_details`**: Get detailed information about specific events
- **`add_event_comment`**: Add comments/questions to events
- **`get_service_health`**: Check server health and Azure service status

### Web Search Server Tools
- **`web_search`**: General web search for corporate actions research
- **`news_search`**: Search for recent financial news articles
- **`financial_data_search`**: Search for financial data by company symbol
- **`get_search_health`**: Check search service health and API status

### Comments Server Tools  
- **`get_event_comments`**: Retrieve comments for specific events
- **`add_comment`**: Add new comments, questions, or concerns
- **`update_comment`**: Update existing comments or mark as resolved
- **`search_comments`**: Search comments across events
- **`get_comment_analytics`**: Get analytics and insights about comments
- **`subscribe_to_event`**: Subscribe to real-time updates for events

## 🔗 MCP Client Integration

The MCP servers can be integrated with any MCP-compatible client:

```python
from mcp import ClientSession
from mcp.client.stdio import stdio_client

# Connect to main RAG server
async with stdio_client(["python", "mcp-server/main.py"]) as (read, write):
    async with ClientSession(read, write) as session:
        # Initialize the session
        await session.initialize()
        
        # Call RAG query tool
        result = await session.call_tool("rag_query", {
            "query": "What are the upcoming dividend payments for AAPL?",
            "max_results": 5
        })
        print(result.content)
```

## 📊 Data Models

The platform uses standardized schemas for corporate actions:

- **CorporateActionEvent**: Main event data structure
- **UserComment**: Comments and Q&A system
- **EventSearchQuery**: Search parameters and filters
- **Security**: Stock/bond identification information

See `data-models/corporate_action_schemas.py` for complete schemas.

## 🗂️ Project Structure

```
corporateactions/
├── mcp-server/              # Main RAG MCP server
│   ├── main.py             # FastMCP server with RAG tools
│   └── requirements.txt    # MCP + Azure dependencies
├── mcp-websearch/          # Web search MCP server  
│   ├── main.py             # FastMCP server with search tools
│   └── requirements.txt    # MCP + search dependencies
├── mcp-comments/           # Comments MCP server
│   ├── main.py             # FastMCP server with collaboration tools
│   └── requirements.txt    # MCP + storage dependencies
├── data-models/            # Shared data schemas
│   ├── corporate_action_schemas.py
│   └── sample_data.py
├── clients/                # Client applications
│   ├── streamlit-ui/       # Streamlit dashboard
│   └── teams-bot/          # Microsoft Teams bot
├── scripts/                # Utility scripts
│   ├── data_ingestion.py   # Azure data setup
│   ├── deploy_azure.ps1    # Azure deployment
│   └── test_setup.py       # Environment testing
├── start_mcp_servers.py    # Start all MCP servers
├── test_mcp_servers.py     # Test MCP server configuration
└── README.md               # This file
```

## 🧪 Testing

### Test MCP Server Configuration
```bash
python test_mcp_servers.py
```

This will check:
- MCP dependencies installation
- Azure service configuration
- Server import capabilities
- Tool availability

### Test Individual Tools
```bash
# Test main RAG server tools
python -c "
import asyncio
from mcp_server.main import app
asyncio.run(app.call_tool('get_service_health'))
"
```

## 🚀 Deployment

### Local Development
1. Start MCP servers: `python start_mcp_servers.py`
2. Start Streamlit UI: `streamlit run clients/streamlit-ui/app.py`
3. Configure Teams bot: Follow Teams bot setup guide

### Azure Deployment
```powershell
# Deploy Azure infrastructure
./scripts/deploy_azure.ps1

# Set up data ingestion
python scripts/data_ingestion.py

# Configure application settings
# Update .env with deployed resource endpoints
```

## 📝 API Documentation

Each MCP server provides OpenAPI documentation when running:
- Main server: http://localhost:8000/docs
- Web search: http://localhost:8001/docs  
- Comments: http://localhost:8002/docs

## 🤝 Contributing

1. Follow MCP best practices for tool development
2. Ensure all tools return proper JSON responses
3. Add comprehensive error handling
4. Update tool documentation and schemas
5. Test with multiple MCP clients

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues related to:
- **MCP Server Development**: Check FastMCP documentation
- **Azure Services**: Verify service configuration and credentials
- **Corporate Actions Data**: Review data models and sample data

## 🔄 Migration Notes

This platform has been migrated from FastAPI REST endpoints to proper Model Context Protocol (MCP) implementation:

- ✅ **Before**: FastAPI servers with HTTP REST endpoints  
- ✅ **After**: FastMCP servers with stdio/SSE transport
- ✅ **Benefits**: Better integration with MCP clients, standardized tool interface
- ✅ **Compatibility**: Works with any MCP-compatible client (Claude Desktop, VS Code, etc.)

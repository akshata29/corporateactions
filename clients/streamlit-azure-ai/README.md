# Corporate Actions Dashboard - Azure AI Agent Service

## 🎯 Overview

This Streamlit application provides a powerful corporate actions dashboard powered by **Azure AI Agent Service** with **Model Context Protocol (MCP)** integration. It combines the intelligence of Azure AI with real-time financial data through MCP servers.

## 🏗️ Architecture

### Azure AI Agent Service Integration
- **Dynamic Tool Discovery**: Automatically discovers and registers MCP tools as Azure AI Agent functions
- **Intelligent Orchestration**: Azure AI Agent manages tool calls, conversation flow, and response generation
- **Production-Ready**: Built on enterprise-grade Azure infrastructure with security and scalability

### MCP Server Integration
- **RAG Server**: Enhanced search with chat history and visualization detection
- **Web Search Server**: Financial news and market data aggregation
- **Comments Server**: Collaborative discussion and Q&A capabilities

### Features
- 🤖 **AI-Powered Chat Assistant** with conversation context
- 🔍 **Advanced Search Interface** with intelligent filtering
- 📊 **Dynamic Visualizations** generated based on user queries
- 📈 **Analytics Dashboard** with interactive charts and insights
- ⚙️ **Configuration Management** for Azure AI and MCP settings

## 🚀 Setup Instructions

### Prerequisites

1. **Azure AI Foundry Project**
   - Create an Azure AI Foundry project in your Azure subscription
   - Deploy a compatible model (GPT-4o recommended)
   - Note your project URL and API key

2. **MCP Servers Running**
   - Ensure your MCP servers are running on the expected ports:
     - RAG Server: `http://localhost:8000/mcp`
     - Web Search Server: `http://localhost:8001/mcp`

### Installation

1. **Clone and Navigate**
   ```bash
   cd d:\repos\corporateactions\clients\streamlit-azure-ai
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   ```bash
   copy .env.example .env
   # Edit .env with your Azure AI and MCP configurations
   ```

4. **Run the Application**
   ```bash
   streamlit run app.py --server.port 8502
   ```

### Azure AI Agent Service Setup

#### Option 1: Using API Key Authentication
1. Get your Azure AI Project URL and API key from Azure portal
2. Set in `.env`:
   ```
   AZURE_AI_PROJECT_URL=https://your-project.cognitiveservices.azure.com/
   AZURE_AI_API_KEY=your_api_key_here
   ```

#### Option 2: Using Azure Identity (Recommended for Production)
1. Set up service principal or managed identity
2. Set in `.env`:
   ```
   AZURE_CLIENT_ID=your_client_id
   AZURE_CLIENT_SECRET=your_client_secret
   AZURE_TENANT_ID=your_tenant_id
   ```

### MCP Tool Discovery Process

The application automatically:
1. **Connects** to each configured MCP server
2. **Discovers** available tools using MCP's list_tools() method
3. **Registers** each tool as an Azure AI Agent function
4. **Creates** wrapper functions for seamless execution

## 🎯 Usage Guide

### 1. Initialize the Agent
- Use the sidebar "Initialize Azure AI Agent" button
- The system will discover MCP tools and create the Azure AI Agent
- Status indicators show connection health

### 2. Dashboard Overview
- View key metrics and visualizations
- Get AI-generated summaries of recent events
- Interactive charts for status and event type distributions

### 3. Advanced Search
- Use natural language queries powered by Azure AI Agent
- Benefit from intelligent tool selection and execution
- Get confidence scores and visualization recommendations

### 4. AI Assistant Chat
- Natural conversation with context awareness
- Agent automatically selects appropriate MCP tools
- Real-time responses with source attribution

### 5. Analytics Dashboard
- Interactive filtering and visualization
- AI-generated insights and recommendations
- Export capabilities for further analysis

## 🔧 Configuration Options

### Azure AI Agent Instructions
The agent is configured with specialized instructions for corporate actions:
```
You are a specialized Corporate Actions AI Assistant with access to real-time financial data through MCP servers.

Your capabilities include:
- Searching corporate actions (dividends, stock splits, mergers, etc.)
- Providing detailed event analysis and insights
- Creating visualizations and charts from financial data
- Answering natural language questions about corporate actions
- Managing user preferences and subscriptions
```

### MCP Tool Registration
Tools are automatically registered with names like:
- `mcp_rag_rag_query`
- `mcp_rag_search_corporate_actions`
- `mcp_websearch_web_search`

## 🛡️ Security Considerations

### Azure AI Security
- Uses Azure Identity for authentication
- All communications encrypted in transit
- Built-in content filtering and safety measures
- Role-based access control (RBAC) support

### MCP Security
- Local server communications only
- No external API keys exposed in MCP tools
- Secure tool parameter validation

## 🔍 Troubleshooting

### Common Issues

1. **Agent Initialization Fails**
   - Verify Azure AI credentials in `.env`
   - Check model deployment status in Azure portal
   - Ensure proper permissions on Azure AI resource

2. **MCP Tools Not Discovered**
   - Verify MCP servers are running
   - Check server URLs in configuration
   - Review server logs for connection issues

3. **Tool Execution Errors**
   - Check MCP server health endpoints
   - Verify tool parameter schemas match
   - Review Azure AI Agent logs

### Debug Mode
Enable debug information in Settings page to view:
- Current configuration values
- Session state details
- Environment variables
- Available dependencies

## 📊 Performance Optimization

### Azure AI Agent
- Uses latest GPT-4o model for optimal performance
- Implements conversation threading for context
- Efficient tool call batching and parallel execution

### MCP Integration
- Connection pooling for server communications
- Async execution for non-blocking operations
- Smart caching of tool discovery results

## 🚀 Deployment Options

### Local Development
- Run with `streamlit run app.py`
- Use environment variables for configuration
- Enable debug mode for development insights

### Azure Container Apps (Recommended)
1. Create container image with Dockerfile
2. Deploy to Azure Container Apps
3. Configure environment variables in Azure
4. Set up Azure AI resource connections

### Azure App Service
1. Deploy as Python web app
2. Configure startup command: `streamlit run app.py --server.port 8000`
3. Set application settings for environment variables

## 🔗 Integration with Existing Infrastructure

### Corporate Actions Platform
- Seamlessly integrates with existing MCP servers
- Maintains compatibility with Teams bot and other clients
- Shared data sources and business logic

### Azure Ecosystem
- Leverages Azure AI Foundry platform capabilities
- Integrates with Azure Monitor for observability
- Supports Azure Virtual Networks for security

## 📈 Monitoring and Observability

### Application Insights Integration
```python
# Automatic telemetry collection
# Custom metrics and traces
# Performance monitoring
```

### Health Checks
- Azure AI Agent service health
- MCP server connectivity
- Application performance metrics

## 🎯 Next Steps

1. **Enhanced Visualizations**: Add more chart types and interactive features
2. **Real-time Updates**: Implement WebSocket connections for live data
3. **User Management**: Add authentication and personalized experiences
4. **Advanced Analytics**: Machine learning models for predictive insights
5. **Mobile Support**: Responsive design improvements

## 📞 Support

For issues and questions:
- Check troubleshooting section above
- Review Azure AI Foundry documentation
- Consult MCP server logs and health endpoints
- Use debug mode for detailed diagnostics

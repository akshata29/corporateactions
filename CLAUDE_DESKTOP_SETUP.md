# Claude Desktop MCP Integration Setup Guide

## 📋 Overview
This guide will help you connect Claude Desktop to your local Corporate Actions MCP servers for testing and development.

## 🔧 Configuration Setup

### Step 1: Locate Claude Desktop Configuration Directory

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**macOS:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Linux:**
```
~/.config/Claude/claude_desktop_config.json
```

### Step 2: Copy Configuration File

1. **Copy the provided configuration**: Use the `claude_desktop_config.json` file from this repository
2. **Replace existing configuration**: Backup your existing config if you have one, then replace it with our configuration
3. **Verify paths**: Make sure all file paths in the config match your local setup

### Step 3: Prepare Environment

#### Install Python Dependencies
```bash
# Navigate to each MCP server directory and install dependencies
cd d:\repos\corporateactions\mcp-rag
pip install -r requirements.txt

cd d:\repos\corporateactions\mcp-websearch  
pip install -r requirements.txt

cd d:\repos\corporateactions\mcp-comments
pip install -r requirements.txt
```

#### Set Environment Variables
Make sure you have a `.env` file in each MCP server directory with:

**For mcp-rag (.env):**
```env
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_SEARCH_ENDPOINT=your_search_endpoint
AZURE_SEARCH_KEY=your_search_key
COSMOS_ENDPOINT=your_cosmos_endpoint
COSMOS_KEY=your_cosmos_key
COSMOS_DATABASE_NAME=corporate-actions
COSMOS_CONTAINER_NAME=events
```

**For mcp-websearch (.env):**
```env
BING_SEARCH_V7_SUBSCRIPTION_KEY=your_bing_key
BING_SEARCH_V7_ENDPOINT=https://api.bing.microsoft.com/
```

**For mcp-comments (.env):**
```env
COSMOS_ENDPOINT=your_cosmos_endpoint
COSMOS_KEY=your_cosmos_key
COSMOS_DATABASE_NAME=corporate-actions
COSMOS_CONTAINER_NAME=comments
```

## 🚀 Testing Your Setup

### Step 1: Test Individual MCP Servers

Test each server in stdio mode (this is how Claude Desktop will run them):

```bash
# Test RAG Server
cd d:\repos\corporateactions\mcp-rag
python main.py

# Test Web Search Server  
cd d:\repos\corporateactions\mcp-websearch
python main.py

# Test Comments Server
cd d:\repos\corporateactions\mcp-comments
python main.py
```

### Step 2: Restart Claude Desktop

1. **Close Claude Desktop** completely
2. **Wait 5 seconds**
3. **Restart Claude Desktop**
4. **Check for MCP servers** in the interface

### Step 3: Verify Connection

In Claude Desktop, you should see:
- 🔍 **Corporate Actions RAG**: 6 tools for searching, analyzing, and querying corporate actions
- 🌐 **Web Search**: 4 tools for searching web content and financial news
- 💬 **Comments System**: 7 tools for managing participant feedback and concerns

## 🛠️ Available MCP Tools

### Corporate Actions RAG Server (Port 8000)
1. `search_corporate_actions` - Search corporate actions database
2. `analyze_corporate_action` - Analyze specific corporate action
3. `get_corporate_action_details` - Get detailed information
4. `ask_rag_question` - Ask questions with RAG context
5. `get_chat_history` - Retrieve conversation history
6. `generate_visualization` - Create dynamic charts and graphs

### Web Search Server (Port 8001) 
1. `search_web` - General web search
2. `search_financial_news` - Financial news search
3. `get_company_info` - Company information lookup
4. `search_regulatory_filings` - SEC filings search

### Comments Server (Port 8002)
1. `submit_question` - Submit participant questions
2. `submit_concern` - Submit participant concerns  
3. `get_questions` - Retrieve questions
4. `get_concerns` - Retrieve concerns
5. `get_analytics` - Get engagement analytics
6. `get_question_details` - Get detailed question info
7. `get_concern_details` - Get detailed concern info

## 🔍 Troubleshooting

### Common Issues

1. **Servers not appearing in Claude Desktop**
   - Check file paths in `claude_desktop_config.json`
   - Verify Python is in your PATH
   - Check that all dependencies are installed

2. **Environment variable errors**
   - Verify `.env` files exist in each server directory
   - Check that all required variables are set
   - Test Azure service connectivity

3. **Permission errors**
   - Run as administrator (Windows)
   - Check file permissions on config directory
   - Verify Python execution permissions

### Logs and Debugging

Check Claude Desktop logs:
- **Windows**: `%APPDATA%\Claude\logs\`
- **macOS**: `~/Library/Logs/Claude/`
- **Linux**: `~/.local/share/Claude/logs/`

### Test Commands

Verify your setup with these test commands in Claude Desktop:

```
# Test RAG functionality
Can you search for corporate actions related to "dividend"?

# Test web search
Search for recent news about Microsoft corporate actions.

# Test comments system
What questions have been submitted about corporate actions?
```

## 📝 Configuration Files Reference

### Complete claude_desktop_config.json
```json
{
  "mcpServers": {
    "corporate-actions-rag": {
      "command": "python",
      "args": ["d:\\repos\\corporateactions\\mcp-rag\\main.py"],
      "env": {
        "PYTHONPATH": "d:\\repos\\corporateactions\\mcp-rag",
        "PYTHONUNBUFFERED": "1"
      }
    },
    "corporate-actions-websearch": {
      "command": "python",
      "args": ["d:\\repos\\corporateactions\\mcp-websearch\\main.py"],
      "env": {
        "PYTHONPATH": "d:\\repos\\corporateactions\\mcp-websearch", 
        "PYTHONUNBUFFERED": "1"
      }
    },
    "corporate-actions-comments": {
      "command": "python",
      "args": ["d:\\repos\\corporateactions\\mcp-comments\\main.py"],
      "env": {
        "PYTHONPATH": "d:\\repos\\corporateactions\\mcp-comments",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

## 🎯 Next Steps

Once Claude Desktop is connected to your MCP servers, you can:

1. **Test all corporate actions functionality** directly in Claude Desktop
2. **Compare responses** between Claude Desktop and your Streamlit dashboard
3. **Debug MCP tool interactions** in a controlled environment
4. **Develop new MCP tools** and test them immediately
5. **Validate data consistency** across different client implementations

This setup gives you a powerful development environment for testing MCP functionality before deploying to production clients like Teams bot or Azure AI services.

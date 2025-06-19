# Simple Start All Services Script
# Opens each command in a new PowerShell window

$RepoRoot = Get-Location
# stdio MCP Servers
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\mcp-rag'; py main.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\mcp-websearch'; py main.py"

# HTTP MCP Servers
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\mcp-rag'; py main.py --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\mcp-websearch'; py main.py --port 8001" 

# SSE MCP Servers  
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\mcp-rag'; py main.py --sse --port 8003"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\mcp-websearch'; py main.py --sse --port 8004"

# Client Applications
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\clients\streamlit-ui'; streamlit run app_mcp.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\clients\corporate-actions-agent'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\clients\streamlit-azure-ai'; streamlit run app.py"

npx @modelcontextprotocol/inspector

Write-Host "✅ All services starting in separate windows!"

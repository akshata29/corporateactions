# Simple Start All Services Script
# Opens each command in a new PowerShell window

$RepoRoot = Get-Location

# HTTP MCP Servers
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\mcp-server'; py main.py --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\mcp-websearch'; py main.py --port 8001" 
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\mcp-comments'; py main.py --port 8002"

# SSE MCP Servers  
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\mcp-server'; py main.py --sse --port 8003"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\mcp-websearch'; py main.py --sse --port 8004"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\mcp-comments'; py main.py --sse --port 8005"

# Client Applications
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\clients\streamlit-ui'; streamlit run app_mcp.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\clients\corporate-actions-agent'; npm run dev"

Write-Host "✅ All services starting in separate windows!"

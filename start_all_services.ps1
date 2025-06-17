# Start All Corporate Actions Services
# This script opens each service in a separate PowerShell window

Write-Host "🚀 Starting All Corporate Actions Services..." -ForegroundColor Green
Write-Host ""

# Get the current directory (should be the repo root)
$RepoRoot = Get-Location

Write-Host "📂 Repository Root: $RepoRoot" -ForegroundColor Cyan
Write-Host ""

# HTTP MCP Servers (ports 8000-8002)
Write-Host "🌐 Starting HTTP MCP Servers..." -ForegroundColor Yellow

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\mcp-rag'; Write-Host '🔥 MCP RAG Server (HTTP) - Port 8000' -ForegroundColor Green; py main.py --port 8000"

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\mcp-websearch'; Write-Host '🔍 MCP WebSearch Server (HTTP) - Port 8001' -ForegroundColor Green; py main.py --port 8001"

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\mcp-comments'; Write-Host '💬 MCP Comments Server (HTTP) - Port 8002' -ForegroundColor Green; py main.py --port 8002"

# SSE MCP Servers (ports 8003-8005)
Write-Host "⚡ Starting SSE MCP Servers..." -ForegroundColor Yellow

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\mcp-rag'; Write-Host '🔥 MCP RAG Server (SSE) - Port 8003' -ForegroundColor Magenta; py main.py --sse --port 8003"

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\mcp-websearch'; Write-Host '🔍 MCP WebSearch Server (SSE) - Port 8004' -ForegroundColor Magenta; py main.py --sse --port 8004"

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\mcp-comments'; Write-Host '💬 MCP Comments Server (SSE) - Port 8005' -ForegroundColor Magenta; py main.py --sse --port 8005"

# Give servers a moment to start
Start-Sleep -Seconds 3

# Client Applications
Write-Host "🎨 Starting Client Applications..." -ForegroundColor Yellow

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\clients\streamlit-ui'; Write-Host '📊 Streamlit Dashboard - http://localhost:8501' -ForegroundColor Blue; streamlit run app_mcp.py"

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\clients\corporate-actions-agent'; Write-Host '🤖 Teams Bot - http://localhost:3978' -ForegroundColor Blue; npm run dev"

Write-Host ""
Write-Host "✅ All services are starting in separate terminal windows!" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 Service URLs:" -ForegroundColor Cyan
Write-Host "   • MCP RAG Server (HTTP):     http://localhost:8000" -ForegroundColor White
Write-Host "   • MCP WebSearch (HTTP):      http://localhost:8001" -ForegroundColor White
Write-Host "   • MCP Comments (HTTP):       http://localhost:8002" -ForegroundColor White
Write-Host "   • MCP RAG Server (SSE):      http://localhost:8003" -ForegroundColor White
Write-Host "   • MCP WebSearch (SSE):       http://localhost:8004" -ForegroundColor White
Write-Host "   • MCP Comments (SSE):        http://localhost:8005" -ForegroundColor White
Write-Host "   • Streamlit Dashboard:       http://localhost:8501" -ForegroundColor White
Write-Host "   • Teams Bot:                 http://localhost:3978" -ForegroundColor White
Write-Host ""
Write-Host "💡 Tips:" -ForegroundColor Yellow
Write-Host "   • Each service runs in its own terminal window" -ForegroundColor Gray
Write-Host "   • Close individual terminals to stop specific services" -ForegroundColor Gray
Write-Host "   • Use Ctrl+C in each terminal to gracefully stop services" -ForegroundColor Gray
Write-Host "   • Check the Teams bot at http://localhost:3978/api/messages" -ForegroundColor Gray
Write-Host ""
Write-Host "🔧 Troubleshooting:" -ForegroundColor Yellow
Write-Host "   • If a port is busy, close the existing service first" -ForegroundColor Gray
Write-Host "   • Check Python/Node.js installations if services fail to start" -ForegroundColor Gray
Write-Host "   • Ensure all requirements.txt and package.json dependencies are installed" -ForegroundColor Gray
Write-Host ""
Write-Host "Press any key to close this window..." -ForegroundColor Green
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

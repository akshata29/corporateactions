# Start individual MCP Servers (HTTP)
# Run these in separate PowerShell windows

Write-Host "📡 MCP Server Commands (HTTP)" -ForegroundColor Cyan
Write-Host ""

# MCP RAG Server (HTTP)
Write-Host "1️⃣ MCP RAG Server (HTTP - Port 8000):" -ForegroundColor Yellow
Write-Host "cd .\mcp-rag\; py main.py --port 8000" -ForegroundColor White
Write-Host ""

# MCP WebSearch Server (HTTP)  
Write-Host "2️⃣ MCP WebSearch Server (HTTP - Port 8001):" -ForegroundColor Yellow
Write-Host "cd .\mcp-websearch\; py main.py --port 8001" -ForegroundColor White
Write-Host ""

# MCP Comments Server (HTTP)
Write-Host "3️⃣ MCP Comments Server (HTTP - Port 8002):" -ForegroundColor Yellow
Write-Host "cd .\mcp-comments\; py main.py --port 8002" -ForegroundColor White
Write-Host ""

Write-Host "🌊 MCP Server Commands (SSE)" -ForegroundColor Cyan
Write-Host ""

# MCP RAG Server (SSE)
Write-Host "4️⃣ MCP RAG Server (SSE - Port 8003):" -ForegroundColor Yellow
Write-Host "cd .\mcp-rag\; py main.py --sse --port 8003" -ForegroundColor White
Write-Host ""

# MCP WebSearch Server (SSE)
Write-Host "5️⃣ MCP WebSearch Server (SSE - Port 8004):" -ForegroundColor Yellow
Write-Host "cd .\mcp-websearch\; py main.py --sse --port 8004" -ForegroundColor White
Write-Host ""

# MCP Comments Server (SSE)
Write-Host "6️⃣ MCP Comments Server (SSE - Port 8005):" -ForegroundColor Yellow
Write-Host "cd .\mcp-comments\; py main.py --sse --port 8005" -ForegroundColor White
Write-Host ""

Write-Host "🎨 UI & Bot Commands" -ForegroundColor Magenta
Write-Host ""

# Streamlit UI
Write-Host "7️⃣ Streamlit UI (Port 8501):" -ForegroundColor Yellow
Write-Host "cd .\clients\streamlit-ui\; streamlit run app_mcp.py" -ForegroundColor White
Write-Host ""

# Teams Bot
Write-Host "8️⃣ Teams Bot (Port 3978):" -ForegroundColor Yellow
Write-Host "cd .\clients\corporate-actions-agent\; npm run dev" -ForegroundColor White
Write-Host ""

Write-Host "💡 Copy and paste each command into a separate PowerShell window." -ForegroundColor Green

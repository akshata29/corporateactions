# Corporate Actions POC - Startup Script
# This script starts all MCP servers and the Streamlit UI

Write-Host "🏦 Starting Corporate Actions POC..." -ForegroundColor Green

# Function to check if port is available
function Test-Port {
    param([int]$Port)
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $tcpClient.Connect("localhost", $Port)
        $tcpClient.Close()
        return $true
    }
    catch {
        return $false
    }
}

# Function to start a Python service
function Start-PythonService {
    param(
        [string]$ServiceName,
        [string]$Directory,
        [int]$Port,
        [string]$MainFile = "main.py"
    )
    
    Write-Host "Starting $ServiceName on port $Port..." -ForegroundColor Yellow
    
    if (Test-Port -Port $Port) {
        Write-Host "⚠️  Port $Port is already in use. Skipping $ServiceName." -ForegroundColor Red
        return
    }
    
    Push-Location $Directory
    
    # Check if virtual environment exists
    if (!(Test-Path "venv")) {
        Write-Host "Creating virtual environment for $ServiceName..." -ForegroundColor Cyan
        python -m venv venv
    }
    
    # Activate virtual environment
    & ".\venv\Scripts\Activate.ps1"
    
    # Install requirements
    if (Test-Path "requirements.txt") {
        Write-Host "Installing requirements for $ServiceName..." -ForegroundColor Cyan
        pip install -r requirements.txt
    }
    
    # Start the service in background
    Start-Process -FilePath "python" -ArgumentList $MainFile -WindowStyle Minimized
    
    Pop-Location
    
    # Wait a moment for service to start
    Start-Sleep -Seconds 2
    
    if (Test-Port -Port $Port) {
        Write-Host "✅ $ServiceName started successfully on port $Port" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to start $ServiceName on port $Port" -ForegroundColor Red
    }
}

# Check if Python is installed
try {
    $pythonVersion = python --version
    Write-Host "Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

# Create .env file if it doesn't exist
$envFile = ".env"
if (!(Test-Path $envFile)) {
    Write-Host "Creating .env file..." -ForegroundColor Cyan
    Copy-Item "mcp-rag\.env.example" $envFile
    Write-Host "⚠️  Please update the .env file with your Azure credentials before running the servers." -ForegroundColor Yellow
}

Write-Host "`n🚀 Starting MCP Servers..." -ForegroundColor Green

# Start MCP Server (Main RAG server)
Start-PythonService -ServiceName "MCP Server (RAG)" -Directory "mcp-rag" -Port 8000

# Start Web Search MCP Server
Start-PythonService -ServiceName "Web Search MCP Server" -Directory "mcp-websearch" -Port 8001

# Start Comments MCP Server
Start-PythonService -ServiceName "Comments MCP Server" -Directory "mcp-comments" -Port 8002

# Start Streamlit UI
Write-Host "`n🖥️  Starting Streamlit UI..." -ForegroundColor Green
Push-Location "clients\streamlit-ui"

if (!(Test-Path "venv")) {
    Write-Host "Creating virtual environment for Streamlit UI..." -ForegroundColor Cyan
    python -m venv venv
}

& ".\venv\Scripts\Activate.ps1"

if (Test-Path "requirements.txt") {
    Write-Host "Installing requirements for Streamlit UI..." -ForegroundColor Cyan
    pip install -r requirements.txt
}

Write-Host "Starting Streamlit UI on port 8501..." -ForegroundColor Yellow
Start-Process -FilePath "streamlit" -ArgumentList "run", "app.py", "--server.port", "8501" -WindowStyle Normal

Pop-Location

Write-Host "`n✅ Corporate Actions POC started successfully!" -ForegroundColor Green
Write-Host "`nServices running on:" -ForegroundColor White
Write-Host "  🤖 MCP Server (RAG):      http://localhost:8000" -ForegroundColor Cyan
Write-Host "  🌐 Web Search MCP:        http://localhost:8001" -ForegroundColor Cyan
Write-Host "  💬 Comments MCP:          http://localhost:8002" -ForegroundColor Cyan
Write-Host "  🖥️  Streamlit UI:          http://localhost:8501" -ForegroundColor Cyan

Write-Host "`nAPI Documentation:" -ForegroundColor White
Write-Host "  📚 MCP Server API:        http://localhost:8000/docs" -ForegroundColor Gray
Write-Host "  📚 Web Search API:        http://localhost:8001/docs" -ForegroundColor Gray
Write-Host "  📚 Comments API:          http://localhost:8002/docs" -ForegroundColor Gray

Write-Host "`n⚠️  Note: Make sure to update the .env file with your Azure credentials for full functionality." -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop all services." -ForegroundColor Gray

# Keep the script running
try {
    while ($true) {
        Start-Sleep -Seconds 10
        
        # Check if services are still running
        $mcpServerRunning = Test-Port -Port 8000
        $webSearchRunning = Test-Port -Port 8001
        $commentsRunning = Test-Port -Port 8002
        $streamlitRunning = Test-Port -Port 8501
        
        if (!$mcpServerRunning -or !$webSearchRunning -or !$commentsRunning -or !$streamlitRunning) {
            Write-Host "`n⚠️  Some services may have stopped. Check the individual terminal windows." -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "`n🛑 Shutting down Corporate Actions POC..." -ForegroundColor Red
}

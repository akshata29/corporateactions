#!/usr/bin/env pwsh
# Start Azure AI Agent Service Streamlit App
# Enhanced startup script with colorful output and comprehensive checks

param(
    [string]$Port = "8502",
    [switch]$Debug = $false,
    [switch]$SkipMCPCheck = $false
)

# Enable color output
$PSStyle.OutputRendering = 'Host'

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    
    $colorCode = switch ($Color) {
        "Red" { "`e[31m" }
        "Green" { "`e[32m" }
        "Yellow" { "`e[33m" }
        "Blue" { "`e[34m" }
        "Magenta" { "`e[35m" }
        "Cyan" { "`e[36m" }
        "White" { "`e[37m" }
        default { "`e[37m" }
    }
    
    Write-Host "${colorCode}${Message}`e[0m"
}

function Test-PythonPackage {
    param([string]$PackageName)
    
    try {
        $result = python -c "import $PackageName; print('✅ OK')" 2>$null
        return $result -eq "✅ OK"
    }
    catch {
        return $false
    }
}

function Test-ServerConnection {
    param([string]$Url, [string]$Name)
    
    try {
        $response = Invoke-WebRequest -Uri "$Url" -Method GET -TimeoutSec 5 -ErrorAction Stop
        return $true
    }
    catch {
        return $false
    }
}

# Header
Write-ColorOutput "════════════════════════════════════════════════════════════════" "Cyan"
Write-ColorOutput "🤖 AZURE AI AGENT SERVICE STREAMLIT APP STARTUP" "Cyan"
Write-ColorOutput "Corporate Actions Dashboard with MCP Integration" "Cyan"
Write-ColorOutput "════════════════════════════════════════════════════════════════" "Cyan"
Write-ColorOutput ""

# Check current directory
$currentDir = Get-Location
Write-ColorOutput "📁 Current Directory: $currentDir" "Blue"

if (-not (Test-Path "app.py")) {
    Write-ColorOutput "❌ Error: app.py not found in current directory" "Red"
    Write-ColorOutput "💡 Please navigate to the streamlit-azure-ai directory first" "Yellow"
    exit 1
}

Write-ColorOutput "✅ Found app.py - proceeding with startup checks" "Green"
Write-ColorOutput ""

# Python version check
Write-ColorOutput "🐍 Checking Python installation..." "Blue"
try {
    $pythonVersion = python --version 2>&1
    Write-ColorOutput "✅ Python: $pythonVersion" "Green"
}
catch {
    Write-ColorOutput "❌ Python not found or not in PATH" "Red"
    exit 1
}

# Check required Python packages
Write-ColorOutput ""
Write-ColorOutput "📦 Checking Python dependencies..." "Blue"

$requiredPackages = @(
    @{Name="streamlit"; Import="streamlit"},
    @{Name="azure-ai-projects"; Import="azure.ai.projects"},
    @{Name="azure-identity"; Import="azure.identity"},
    @{Name="mcp"; Import="mcp"},
    @{Name="pandas"; Import="pandas"},
    @{Name="plotly"; Import="plotly"}
)

$missingPackages = @()

foreach ($package in $requiredPackages) {
    if (Test-PythonPackage -PackageName $package.Import) {
        Write-ColorOutput "✅ $($package.Name)" "Green"
    }
    else {
        Write-ColorOutput "❌ $($package.Name)" "Red"
        $missingPackages += $package.Name
    }
}

if ($missingPackages.Count -gt 0) {
    Write-ColorOutput ""
    Write-ColorOutput "⚠️  Missing packages detected!" "Yellow"
    Write-ColorOutput "🔧 Installing missing packages..." "Blue"
    
    try {
        pip install -r requirements.txt
        Write-ColorOutput "✅ Package installation completed" "Green"
    }
    catch {
        Write-ColorOutput "❌ Failed to install packages automatically" "Red"
        Write-ColorOutput "💡 Please run: pip install -r requirements.txt" "Yellow"
        exit 1
    }
}

# Check environment configuration
Write-ColorOutput ""
Write-ColorOutput "⚙️  Checking environment configuration..." "Blue"

if (Test-Path ".env") {
    Write-ColorOutput "✅ Found .env file" "Green"
}
else {
    Write-ColorOutput "⚠️  No .env file found" "Yellow"
    if (Test-Path ".env.example") {
        Write-ColorOutput "💡 Copy .env.example to .env and configure your settings" "Yellow"
    }
}

# Check environment variables
$envVars = @(
    "AZURE_AI_PROJECT_URL",
    "AZURE_AI_API_KEY",
    "AZURE_AI_MODEL_DEPLOYMENT"
)

foreach ($var in $envVars) {
    $value = [Environment]::GetEnvironmentVariable($var)
    if ($value) {
        Write-ColorOutput "✅ $var is set" "Green"
    }
    else {
        Write-ColorOutput "⚠️  $var not set" "Yellow"
    }
}

# Check MCP server connectivity (if not skipped)
if (-not $SkipMCPCheck) {
    Write-ColorOutput ""
    Write-ColorOutput "🔗 Checking MCP server connectivity..." "Blue"
    
    $mcpServers = @(
        @{Url="http://localhost:8000/mcp"; Name="RAG Server"},
        @{Url="http://localhost:8001/mcp"; Name="WebSearch Server"}
    )
    
    foreach ($server in $mcpServers) {
        if (Test-ServerConnection -Url $server.Url -Name $server.Name) {
            Write-ColorOutput "✅ $($server.Name) - $($server.Url)" "Green"
        }
        else {
            Write-ColorOutput "❌ $($server.Name) - $($server.Url)" "Red"
        }
    }
    
    Write-ColorOutput ""
    Write-ColorOutput "💡 Note: MCP servers are optional for basic functionality" "Yellow"
    Write-ColorOutput "   The app will use sample data if MCP servers are unavailable" "Yellow"
}

# Port availability check
Write-ColorOutput ""
Write-ColorOutput "🌐 Checking port availability..." "Blue"

try {
    $portInUse = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($portInUse) {
        Write-ColorOutput "⚠️  Port $Port is already in use" "Yellow"
        Write-ColorOutput "🔄 Streamlit will automatically find an available port" "Blue"
    }
    else {
        Write-ColorOutput "✅ Port $Port is available" "Green"
    }
}
catch {
    Write-ColorOutput "✅ Port $Port appears to be available" "Green"
}

# Display startup information
Write-ColorOutput ""
Write-ColorOutput "📊 AZURE AI STREAMLIT APP CONFIGURATION" "Magenta"
Write-ColorOutput "──────────────────────────────────────────" "Magenta"
Write-ColorOutput "🌐 URL: http://localhost:$Port" "Blue"
Write-ColorOutput "📁 App Directory: $currentDir" "Blue"
Write-ColorOutput "🤖 Azure AI Integration: Enabled" "Blue"
Write-ColorOutput "🔗 MCP Integration: Enabled" "Blue"
Write-ColorOutput "📊 Features: Dashboard, Search, AI Assistant, Analytics" "Blue"

if ($Debug) {
    Write-ColorOutput "🔧 Debug Mode: Enabled" "Yellow"
}

Write-ColorOutput ""
Write-ColorOutput "🚀 Starting Azure AI Agent Service Streamlit App..." "Green"
Write-ColorOutput ""

# Build streamlit command
$streamlitArgs = @(
    "run",
    "app.py",
    "--server.port", $Port,
    "--server.address", "localhost",
    "--browser.gatherUsageStats", "false"
)

if ($Debug) {
    $streamlitArgs += @("--logger.level", "debug")
}

# Start the application
try {
    Write-ColorOutput "🎯 Executing: streamlit $($streamlitArgs -join ' ')" "Cyan"
    Write-ColorOutput ""
    Write-ColorOutput "🌟 Azure AI Agent Service Dashboard starting..." "Green"
    Write-ColorOutput "🔗 Open your browser to: http://localhost:$Port" "Green"
    Write-ColorOutput ""
    Write-ColorOutput "💡 Features available:" "Blue"
    Write-ColorOutput "   • 🏠 Dashboard - Overview and metrics" "Blue"
    Write-ColorOutput "   • 🔍 Search Events - AI-powered corporate actions search" "Blue"
    Write-ColorOutput "   • 💬 AI Assistant - Chat with Azure AI Agent" "Blue"
    Write-ColorOutput "   • 📊 Analytics - Interactive data visualization" "Blue"
    Write-ColorOutput "   • ⚙️ Settings - Configure Azure AI and MCP settings" "Blue"
    Write-ColorOutput ""
    Write-ColorOutput "🛑 Press Ctrl+C to stop the application" "Yellow"
    Write-ColorOutput ""
    
    # Execute streamlit
    & streamlit @streamlitArgs
}
catch {
    Write-ColorOutput ""
    Write-ColorOutput "❌ Failed to start Streamlit application" "Red"
    Write-ColorOutput "Error: $($_.Exception.Message)" "Red"
    Write-ColorOutput ""
    Write-ColorOutput "🔧 Troubleshooting steps:" "Yellow"
    Write-ColorOutput "1. Ensure all dependencies are installed: pip install -r requirements.txt" "Yellow"
    Write-ColorOutput "2. Check your .env configuration" "Yellow"
    Write-ColorOutput "3. Verify Azure AI credentials" "Yellow"
    Write-ColorOutput "4. Run with --Debug flag for more information" "Yellow"
    exit 1
}

Write-ColorOutput ""
Write-ColorOutput "👋 Azure AI Agent Service Streamlit App stopped" "Blue"
Write-ColorOutput ""

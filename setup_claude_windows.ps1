# PowerShell script to set up Claude Desktop MCP integration
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Claude Desktop MCP Setup for Windows" -ForegroundColor Cyan  
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Claude config directory exists
$claudeConfigDir = "$env:APPDATA\Claude"
if (-not (Test-Path $claudeConfigDir)) {
    Write-Host "Creating Claude config directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $claudeConfigDir -Force | Out-Null
}

# Backup existing config if it exists
$configPath = "$claudeConfigDir\claude_desktop_config.json"
if (Test-Path $configPath) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupPath = "$claudeConfigDir\claude_desktop_config.json.backup.$timestamp"
    Write-Host "Backing up existing configuration..." -ForegroundColor Yellow
    Copy-Item $configPath $backupPath
    Write-Host "   Backup saved to: $backupPath" -ForegroundColor Gray
}

# Copy new configuration
Write-Host "Copying MCP configuration..." -ForegroundColor Yellow
try {
    Copy-Item "claude_desktop_config.json" $configPath -Force
    Write-Host ""
    Write-Host "✅ Configuration copied successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📍 Configuration location: $configPath" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "🔄 Next steps:" -ForegroundColor Yellow
    Write-Host "   1. Close Claude Desktop completely" -ForegroundColor White
    Write-Host "   2. Wait 5 seconds" -ForegroundColor White
    Write-Host "   3. Restart Claude Desktop" -ForegroundColor White
    Write-Host "   4. Check for MCP servers in the interface" -ForegroundColor White
    Write-Host ""
    Write-Host "🧪 Test the setup by running:" -ForegroundColor Yellow
    Write-Host "   python test_claude_integration.py" -ForegroundColor Gray
    Write-Host ""
} catch {
    Write-Host ""
    Write-Host "❌ Failed to copy configuration file" -ForegroundColor Red
    Write-Host "Please manually copy claude_desktop_config.json to:" -ForegroundColor Yellow
    Write-Host "$configPath" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "Press any key to continue..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

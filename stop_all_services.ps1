# Stop All Corporate Actions Services
# Kills processes running on the service ports

Write-Host "🛑 Stopping All Corporate Actions Services..." -ForegroundColor Red
Write-Host ""

# Define the ports used by services
$ports = @(8000, 8001, 8002, 8003, 8004, 8005, 8501, 3978)

foreach ($port in $ports) {
    Write-Host "🔍 Checking port $port..." -ForegroundColor Yellow
    
    # Find processes using the port
    $processes = netstat -ano | Select-String ":$port " | ForEach-Object {
        $line = $_.Line.Trim()
        $parts = $line -split '\s+'
        if ($parts.Length -ge 5) {
            $parts[4]  # PID is typically the 5th column
        }
    }
    
    if ($processes) {
        foreach ($pid in $processes) {
            try {
                $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
                if ($process) {
                    Write-Host "   ❌ Killing process $($process.ProcessName) (PID: $pid)" -ForegroundColor Red
                    Stop-Process -Id $pid -Force
                }
            }
            catch {
                Write-Host "   ⚠️ Could not kill process $pid" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "   ✅ Port $port is free" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "✅ Stop script completed!" -ForegroundColor Green
Write-Host ""
Write-Host "💡 Note: You can also close individual terminal windows manually" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press any key to close this window..." -ForegroundColor Green
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

Clear-Host

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkGray
Write-Host "                    CRYPTO.BOT ENGINE" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor DarkGray
Write-Host ""

Write-Host "[SYSTEM] " -NoNewline -ForegroundColor Green
Write-Host "Starting trading engine..." -ForegroundColor Gray

Write-Host "[SYSTEM] " -NoNewline -ForegroundColor Green
Write-Host "Initializing runtime environment..." -ForegroundColor Gray

Write-Host ""

python apps/trader/runner.py

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkGray
Write-Host "                    ENGINE STOPPED" -ForegroundColor Red
Write-Host "============================================================" -ForegroundColor DarkGray
Write-Host ""
# ============================================================
# CRYPTO.BOT STARTUP
# ============================================================

$Host.UI.RawUI.WindowTitle = "CRYPTO.BOT"

Clear-Host

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "                    CRYPTO.BOT ENGINE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================
# ROOT
# ============================================================

$ROOT = Split-Path $PSScriptRoot -Parent

Set-Location $ROOT

# ============================================================
# START
# ============================================================

try {

    python -m scripts.bootstrap.launcher

}
catch {

    Write-Host ""
    Write-Host $_ -ForegroundColor Red
    Write-Host ""

}
finally {

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "                 ENGINE STOPPED" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""

}
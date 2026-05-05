$ErrorActionPreference = "Stop"

$originalPath = Get-Location

try {

    Set-Location -Path (Split-Path -Parent $PSScriptRoot)

    $env:PYTHONPATH = Get-Location

    python scripts/bootstrap.py

    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Bootstrap failed" -ForegroundColor Red
        exit $LASTEXITCODE
    }

    pip install -r requirements.txt | Out-Null

    python apps/main.py

}
finally {
    Set-Location $originalPath
}
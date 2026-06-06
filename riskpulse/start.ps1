# Start RiskPulse (use 8090 — port 8081 may be stuck by an old Windows process)
Set-Location $PSScriptRoot\backend
Write-Host "Starting RiskPulse on http://localhost:8090/riskpulse-no-ml"
python -m uvicorn main:app --reload --port 8090

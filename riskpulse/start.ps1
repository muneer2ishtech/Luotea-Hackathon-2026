# Start RiskPulse. Default port 8090; override with $env:PORT=9000; .\start.ps1
$Port = if ($env:PORT) { $env:PORT } else { 8090 }
Set-Location $PSScriptRoot\backend
Write-Host "Starting RiskPulse on http://localhost:$Port/riskpulse-no-ml"
python -m uvicorn main:app --reload --port $Port

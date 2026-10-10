$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    py -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed.' }
}
& '.\.venv\Scripts\python.exe' -m pip install -r backend\requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed.' }
$portableNode = Get-ChildItem -LiteralPath '.tools' -Directory -Filter 'node-*-win-x64' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($portableNode) {
    $env:PATH = $portableNode.FullName + ';' + $env:PATH
    $npmCommand = Join-Path $portableNode.FullName 'npm.cmd'
} else { $npmCommand = 'npm.cmd' }
& $npmCommand --prefix frontend ci
if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed. Install Node.js 22.12+ or 24 LTS.' }
Write-Output 'Moniq is ready. Use scripts/start-backend.ps1 and scripts/start-frontend.ps1 in separate terminals.'

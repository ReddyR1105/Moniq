$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$portableNode = Get-ChildItem -LiteralPath '.tools' -Directory -Filter 'node-*-win-x64' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($portableNode) { $env:PATH = $portableNode.FullName + ';' + $env:PATH; $npmCommand = Join-Path $portableNode.FullName 'npm.cmd' } else { $npmCommand = 'npm.cmd' }
& $npmCommand --prefix frontend run build
if ($LASTEXITCODE -ne 0) { throw 'Production build failed.' }
$env:MONIQ_PUBLIC_DEMO = 'true'
$env:MONIQ_SERVE_FRONTEND = 'true'
$env:MONIQ_COOKIE_SECURE = 'false' # HTTP localhost only; Render uses Secure cookies.
$env:MONIQ_PUBLIC_ORIGIN = 'http://127.0.0.1:8080'
& '.\.venv\Scripts\python.exe' -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8080 --workers 1

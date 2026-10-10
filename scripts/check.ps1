param([switch]$Browser)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$portableNode = Get-ChildItem -LiteralPath '.tools' -Directory -Filter 'node-*-win-x64' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($portableNode) { $env:PATH = $portableNode.FullName + ';' + $env:PATH; $npmCommand = Join-Path $portableNode.FullName 'npm.cmd' } else { $npmCommand = 'npm.cmd' }
& '.\.venv\Scripts\python.exe' -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed.' }
& '.\.venv\Scripts\python.exe' -m ruff check backend tests scripts
if ($LASTEXITCODE -ne 0) { throw 'Python lint failed.' }
& '.\.venv\Scripts\python.exe' scripts/reproduce_ml.py --check
if ($LASTEXITCODE -ne 0) { throw 'Independent ML evaluation failed.' }
& $npmCommand --prefix frontend run typecheck
if ($LASTEXITCODE -ne 0) { throw 'TypeScript check failed.' }
& $npmCommand --prefix frontend run lint
if ($LASTEXITCODE -ne 0) { throw 'Frontend lint failed.' }
& $npmCommand --prefix frontend run build
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
if ($Browser) {
    & $npmCommand --prefix frontend run test:e2e
    if ($LASTEXITCODE -ne 0) { throw 'Browser tests failed.' }
    & $npmCommand --prefix frontend run test:public
    if ($LASTEXITCODE -ne 0) { throw 'Public session browser tests failed.' }
}

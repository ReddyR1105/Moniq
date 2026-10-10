$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$portableNode = Get-ChildItem -LiteralPath '.tools' -Directory -Filter 'node-*-win-x64' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($portableNode) {
    $env:PATH = $portableNode.FullName + ';' + $env:PATH
    & (Join-Path $portableNode.FullName 'npm.cmd') --prefix frontend run dev
} else { & npm.cmd --prefix frontend run dev }

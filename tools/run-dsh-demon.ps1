# 启动 dsh-demon（Node 24 / Fastify）
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$svc = Join-Path $root 'services\dsh-demon'
$node = 'D:\nodejs\node.exe'

if (-not (Test-Path (Join-Path $svc 'node_modules'))) {
    Push-Location $svc
    & 'D:\nodejs\npm.cmd' install --no-audit --no-fund
    Pop-Location
}

& $node (Join-Path $svc 'src\server.js')

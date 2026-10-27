# 打包发布物：Demon / smartdemon / dsh-demon
param(
    [string]$Version = '2.0.0',
    [string]$PluginVersion = '2.1.0',
    [string]$ServiceVersion = '0.1.0',
    [string]$OutDir = ''
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $OutDir) { $OutDir = Join-Path $root 'release' }
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

# Demon：需要先构建，并准备 dist 运行时（windeployqt + Qt 依赖）
$demonDist = Join-Path $root 'apps\demon\dist\Demon'
if (Test-Path $demonDist) {
    $zip = Join-Path $OutDir "Demon-$Version.zip"
    Compress-Archive -Path "$demonDist\*" -DestinationPath $zip -Force
    Write-Host "OK: $zip"
} else {
    Write-Warning "缺少 $demonDist，跳过 Demon 打包（先运行 tools\build-demon.ps1 并 windeployqt）"
}

# smartdemon
$plugin = Join-Path $root 'apps\st-plugin'
$zip = Join-Path $OutDir "smartdemon-$PluginVersion.zip"
Compress-Archive -Path "$plugin\*" -DestinationPath $zip -Force
Write-Host "OK: $zip"

# dsh-demon（不含 node_modules，安装时 npm ci）
$svc = Join-Path $root 'services\dsh-demon'
$tmp = Join-Path $env:TEMP "dsh-demon-$ServiceVersion"
Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
Copy-Item "$svc\src" $tmp -Recurse
Copy-Item "$svc\package.json" $tmp
if (Test-Path "$svc\package-lock.json") { Copy-Item "$svc\package-lock.json" $tmp }
Copy-Item "$root\contracts" (Join-Path $tmp 'contracts') -Recurse
$zip = Join-Path $OutDir "dsh-demon-$ServiceVersion.zip"
Compress-Archive -Path "$tmp\*" -DestinationPath $zip -Force
Remove-Item $tmp -Recurse -Force
Write-Host "OK: $zip"

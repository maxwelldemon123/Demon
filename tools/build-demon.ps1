# 构建 Demon（Qt 6 / MSVC）
param(
    [string]$Qt = 'E:\dshwork\toolchain\Qt\6.8.3\msvc2022_64',
    [string]$Build = ''
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$src = Join-Path $root 'apps\demon'
if (-not $Build) { $Build = Join-Path $src 'build-release' }

$vcvars = 'D:\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
$cmake = 'D:\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe'
$ninja = 'D:\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe'

$cmd = "call `"$vcvars`" >nul && `"$cmake`" -S `"$src`" -B `"$Build`" -G Ninja -DCMAKE_BUILD_TYPE=Release -DDEMON_CONSOLE=OFF -DCMAKE_PREFIX_PATH=`"$Qt`" -DCMAKE_MAKE_PROGRAM=`"$ninja`" && `"$cmake`" --build `"$Build`""
& cmd.exe /c $cmd
if ($LASTEXITCODE -ne 0) { throw "Demon 构建失败（$LASTEXITCODE）" }
Write-Host "OK: $Build\bin\demon.exe"

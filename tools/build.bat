@echo off
setlocal
rem ---------------------------------------------------------------
rem  Demon 一键构建（Windows / MSVC 2022 + Qt 6.8.3）
rem  用法：build.bat            构建 Release
rem        build.bat clean      清空 build 目录后重建
rem ---------------------------------------------------------------

set "VCVARS=D:\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
set "CMAKE=D:\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
set "NINJA=D:\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe"
set "QT=E:\dshwork\toolchain\Qt\6.8.3\msvc2022_64"
set "ROOT=%~dp0.."
set "BUILD=%ROOT%\build"

if /i "%~1"=="clean" (
    if exist "%BUILD%" rmdir /s /q "%BUILD%"
)

call "%VCVARS%" >nul
if errorlevel 1 (
    echo [ERROR] vcvars64.bat 失败，检查 Visual Studio 路径
    exit /b 1
)

"%CMAKE%" -S "%ROOT%" -B "%BUILD%" -G Ninja -DCMAKE_BUILD_TYPE=Release ^
    -DCMAKE_PREFIX_PATH="%QT%" -DCMAKE_MAKE_PROGRAM="%NINJA%"
if errorlevel 1 exit /b 1

"%CMAKE%" --build "%BUILD%"
if errorlevel 1 exit /b 1

echo.
echo [OK] 产物: %BUILD%\bin\demon.exe

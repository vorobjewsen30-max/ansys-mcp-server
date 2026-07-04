@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ╔══════════════════════════════════════════════════════════════════════════════╗
:: ║              ANSYS MCP SERVER — INSTALLER for Claude Code CLI               ║
:: ║                                                                              ║
:: ║  Usage:                                                                      ║
:: ║    install.bat                    Install + configure Claude Code             ║
:: ║    install.bat run                Run the MCP server (stdio mode)             ║
:: ║    install.bat install-fluent     Install with Fluent support                 ║
:: ║    install.bat install-all        Install with ALL Ansys products             ║
:: ╚══════════════════════════════════════════════════════════════════════════════╝

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%"

:: ── Colour helpers ────────────────────────────────────────────────────────────
for /f %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
set "GREEN=%ESC%[32m"
set "YELLOW=%ESC%[33m"
set "CYAN=%ESC%[36m"
set "RED=%ESC%[31m"
set "BOLD=%ESC%[1m"
set "RESET=%ESC%[0m"

echo.
echo %CYAN%╔══════════════════════════════════════════════════════════════╗%RESET%
echo %CYAN%║        ANSYS MCP SERVER — Claude Code CLI Installer         ║%RESET%
echo %CYAN%╚══════════════════════════════════════════════════════════════╝%RESET%
echo.

:: ── Check Python ──────────────────────────────────────────────────────────────
echo %BOLD%[1/4]%RESET% Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%✗ Python not found! Install Python 3.10+ from https://python.org%RESET%
    echo    Make sure "Add Python to PATH" is checked during installation.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version') do echo %GREEN%✓%RESET% Found Python %%v

:: ── Create virtual environment ────────────────────────────────────────────────
echo.
echo %BOLD%[2/4]%RESET% Setting up virtual environment...
if not exist "%PROJECT_DIR%.venv" (
    python -m venv "%PROJECT_DIR%.venv"
    echo %GREEN%✓%RESET% Virtual environment created
) else (
    echo %YELLOW%○%RESET% Virtual environment already exists
)

:: Activate venv
call "%PROJECT_DIR%.venv\Scripts\activate.bat"

:: ── Install dependencies ──────────────────────────────────────────────────────
echo.
echo %BOLD%[3/4]%RESET% Installing dependencies...

:: Check for extra args
set "INSTALL_MODE=base"
if /i "%~1"=="install-fluent" set "INSTALL_MODE=fluent"
if /i "%~1"=="install-mechanical" set "INSTALL_MODE=mechanical"
if /i "%~1"=="install-mapdl" set "INSTALL_MODE=mapdl"
if /i "%~1"=="install-dpf" set "INSTALL_MODE=dpf"
if /i "%~1"=="install-all" set "INSTALL_MODE=all"
if /i "%~1"=="run" set "INSTALL_MODE=run"
if /i "%~1"=="install" set "INSTALL_MODE=base"

if "%INSTALL_MODE%"=="run" goto :run_server

:: Upgrade pip
python -m pip install --upgrade pip --quiet

:: Install base MCP package
pip install mcp --quiet
echo %GREEN%✓%RESET% Base MCP SDK installed

:: Install optional Ansys packages based on mode
if "%INSTALL_MODE%"=="base" (
    echo %YELLOW%○%RESET% Installed base package (no Ansys libs)
    echo    Use %CYAN%install.bat install-fluent%RESET% for CFD support
    echo    Use %CYAN%install.bat install-all%RESET% for all products
    goto :configure
)

if "%INSTALL_MODE%"=="fluent" (
    echo   Installing ansys-fluent-core...
    pip install ansys-fluent-core --quiet
    echo %GREEN%✓%RESET% Fluent support installed
)

if "%INSTALL_MODE%"=="mechanical" (
    echo   Installing ansys-mechanical-core...
    pip install ansys-mechanical-core --quiet
    echo %GREEN%✓%RESET% Mechanical support installed
)

if "%INSTALL_MODE%"=="mapdl" (
    echo   Installing ansys-mapdl-core...
    pip install ansys-mapdl-core --quiet
    echo %GREEN%✓%RESET% MAPDL support installed
)

if "%INSTALL_MODE%"=="dpf" (
    echo   Installing ansys-dpf-core...
    pip install ansys-dpf-core --quiet
    echo %GREEN%✓%RESET% DPF support installed
)

if "%INSTALL_MODE%"=="all" (
    echo   Installing all Ansys packages...
    pip install ansys-fluent-core ansys-mechanical-core ansys-mapdl-core ansys-dpf-core ansys-meshing-prime --quiet
    echo %GREEN%✓%RESET% All Ansys products installed
)

:: ── Configure Claude Code ─────────────────────────────────────────────────────
:configure
echo.
echo %BOLD%[4/4]%RESET% Configuring Claude Code CLI...

:: Determine config paths
set "CLAUDE_DIR=%USERPROFILE%\.claude"
set "SETTINGS_FILE=%CLAUDE_DIR%\claude_desktop_config.json"

:: Create .claude directory if needed
if not exist "%CLAUDE_DIR%" mkdir "%CLAUDE_DIR%"

:: Build server command with absolute paths
set "SERVER_PYTHON=%PROJECT_DIR%.venv\Scripts\python.exe"
set "SERVER_MODULE=ansys_mcp_server.server"
set "SERVER_CWD=%PROJECT_DIR%src"

:: Create/update config
python -c "
import json, sys, os

config_file = r'%SETTINGS_FILE%'
server_config = {
    'ansys': {
        'command': r'%SERVER_PYTHON%',
        'args': ['-m', 'ansys_mcp_server.server'],
        'cwd': r'%SERVER_CWD%'
    }
}

config = {}
if os.path.exists(config_file):
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except:
        config = {}

if 'mcpServers' not in config:
    config['mcpServers'] = {}

config['mcpServers']['ansys'] = server_config['ansys']

with open(config_file, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print('Config written to:', config_file)
"

if %errorlevel% equ 0 (
    echo %GREEN%✓%RESET% Claude Code configured with Ansys MCP server
    echo.
    echo %CYAN%╔══════════════════════════════════════════════════════════════╗%RESET%
    echo %CYAN%║  ✅ INSTALLATION COMPLETE                                   ║%RESET%
    echo %CYAN%╠══════════════════════════════════════════════════════════════╣%RESET%
    echo %CYAN%║                                                              ║%RESET%
    echo %CYAN%║  MCP server added to:                                         ║%RESET%
    echo %CYAN%║  %SETTINGS_FILE:\=/%   %RESET%
    echo %CYAN%║                                                              ║%RESET%
    echo %CYAN%║  Restart Claude Code CLI to use Ansys tools.                  ║%RESET%
    echo %CYAN%║                                                              ║%RESET%
    echo %CYAN%║  Test with: "Проверь какие пакеты Ansys установлены"         ║%RESET%
    echo %CYAN%║                                                              ║%RESET%
    echo %CYAN%╚══════════════════════════════════════════════════════════════╝%RESET%
) else (
    echo %RED%✗ Failed to configure Claude Code%RESET%
)

goto :end

:: ── Run server ────────────────────────────────────────────────────────────────
:run_server
echo.
echo %BOLD%Running Ansys MCP Server (stdio mode)...%RESET%
echo %YELLOW%Press Ctrl+C to stop%RESET%
echo.

:: Check if venv exists
if not exist "%PROJECT_DIR%.venv\Scripts\python.exe" (
    echo %RED%✗ Virtual environment not found. Run install.bat first.%RESET%
    pause
    exit /b 1
)

cd /d "%PROJECT_DIR%src"
"%PROJECT_DIR%.venv\Scripts\python.exe" -m ansys_mcp_server.server

:end
endlocal

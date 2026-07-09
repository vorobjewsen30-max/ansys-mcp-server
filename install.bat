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

::: Check for extra args
set "INSTALL_MODE=base"
if /i "%~1"=="install-fluent" set "INSTALL_MODE=fluent"
if /i "%~1"=="install-mechanical" set "INSTALL_MODE=mechanical"
if /i "%~1"=="install-mapdl" set "INSTALL_MODE=mapdl"
if /i "%~1"=="install-dpf" set "INSTALL_MODE=dpf"
if /i "%~1"=="install-all" set "INSTALL_MODE=all"
if /i "%~1"=="run" set "INSTALL_MODE=run"
if /i "%~1"=="install" set "INSTALL_MODE=base"
if /i "%~1"=="--upgrade" set "INSTALL_MODE=upgrade"
if /i "%2"=="--upgrade" set "UPGRADE_FLAG=1"



if "%INSTALL_MODE%"=="upgrade" goto :upgrade_handler
if "%INSTALL_MODE%"=="run" goto :run_server

REM Upgrade pip
python -m pip install --upgrade pip --quiet
if %errorlevel% neq 0 (
    echo %YELLOW%⚠ pip upgrade skipped (non-critical)%RESET%
)

REM Install base MCP package
echo %BOLD%  Installing MCP SDK...%RESET%
pip install mcp
if %errorlevel% neq 0 (
    echo %RED%✗ Failed to install MCP SDK%RESET%
    echo    Check internet connection or proxy settings.
    pause
    exit /b 1
)
echo %GREEN%✓%RESET% Base MCP SDK installed

REM Install optional Ansys packages based on mode
if "%INSTALL_MODE%"=="base" (
    echo %YELLOW%○%RESET% Installed base package (no Ansys libs)
    echo    Use %CYAN%install.bat install-fluent%RESET% for CFD support
    echo    Use %CYAN%install.bat install-all%RESET% for all products
    goto :configure
)

if "%INSTALL_MODE%"=="fluent" (
    echo %BOLD%  Installing ansys-fluent-core...%RESET%
    pip install ansys-fluent-core
    if %errorlevel% equ 0 (
        echo %GREEN%✓%RESET% Fluent support installed
    ) else (
        echo %YELLOW%⚠ ansys-fluent-core NOT installed (non-fatal)%RESET%
        echo    Server runs without it. Install later: pip install ansys-fluent-core
    )
)

if "%INSTALL_MODE%"=="mechanical" (
    echo %BOLD%  Installing ansys-mechanical-core...%RESET%
    pip install ansys-mechanical-core
    if %errorlevel% equ 0 (
        echo %GREEN%✓%RESET% Mechanical support installed
    ) else (
        echo %YELLOW%⚠ ansys-mechanical-core NOT installed (non-fatal)%RESET%
    )
)

if "%INSTALL_MODE%"=="mapdl" (
    echo %BOLD%  Installing ansys-mapdl-core...%RESET%
    pip install ansys-mapdl-core
    if %errorlevel% equ 0 (
        echo %GREEN%✓%RESET% MAPDL support installed
    ) else (
        echo %YELLOW%⚠ ansys-mapdl-core NOT installed (non-fatal)%RESET%
    )
)

if "%INSTALL_MODE%"=="dpf" (
    echo %BOLD%  Installing ansys-dpf-core...%RESET%
    pip install ansys-dpf-core
    if %errorlevel% equ 0 (
        echo %GREEN%✓%RESET% DPF support installed
    ) else (
        echo %YELLOW%⚠ ansys-dpf-core NOT installed (non-fatal)%RESET%
    )
)

if "%INSTALL_MODE%"=="all" (
    echo %BOLD%  Installing all Ansys packages...%RESET%
    pip install ansys-fluent-core ansys-mechanical-core ansys-mapdl-core ansys-dpf-core ansys-meshing-prime
    if %errorlevel% equ 0 (
        echo %GREEN%✓%RESET% All Ansys products installed
    ) else (
        echo %YELLOW%⚠ Some Ansys packages NOT installed (non-fatal)%RESET%
        echo    Server works without them. Install individually: pip install ansys-fluent-core
    )
)

::: ── Upgrade mode (update files, keep config) ──────────────────────────────
:upgrade_handler
echo.
echo %BOLD%  Upgrading Ansys MCP Server...%RESET%
echo.

REM Git pull to get latest
where git >nul 2>&1
if %errorlevel% equ 0 (
    echo %BOLD%  Pulling latest code from git...%RESET%
    git pull
    if %errorlevel% equ 0 (
        echo %GREEN%✓%RESET% Code updated from git
    ) else (
        echo %YELLOW%⚠ git pull failed — continuing with local files%RESET%
    )
) else (
    echo %YELLOW%○%RESET% Git not found — keeping local files
)

REM Activate venv
if not exist "%PROJECT_DIR%.venv\Scripts\python.exe" (
    echo %YELLOW%○%RESET% No venv found — run install.bat first
    pause
    exit /b 1
)
call "%PROJECT_DIR%.venv\Scripts\activate.bat"

REM Upgrade MCP SDK
echo %BOLD%  Upgrading MCP SDK...%RESET%
pip install --upgrade mcp
if %errorlevel% equ 0 (
    echo %GREEN%✓%RESET% MCP SDK upgraded
) else (
    echo %RED%✗ Failed to upgrade MCP SDK%RESET%
    pause
    exit /b 1
)

REM Upgrade Ansys packages if installed
pip list 2>nul | findstr /i "ansys-fluent-core" >nul
if %errorlevel% equ 0 (
    echo %BOLD%  Upgrading ansys-fluent-core...%RESET%
    pip install --upgrade ansys-fluent-core
)
pip list 2>nul | findstr /i "ansys-mechanical-core" >nul
if %errorlevel% equ 0 (
    echo %BOLD%  Upgrading ansys-mechanical-core...%RESET%
    pip install --upgrade ansys-mechanical-core
)
pip list 2>nul | findstr /i "ansys-mapdl-core" >nul
if %errorlevel% equ 0 (
    echo %BOLD%  Upgrading ansys-mapdl-core...%RESET%
    pip install --upgrade ansys-mapdl-core
)
pip list 2>nul | findstr /i "ansys-dpf-core" >nul
if %errorlevel% equ 0 (
    echo %BOLD%  Upgrading ansys-dpf-core...%RESET%
    pip install --upgrade ansys-dpf-core
)
pip list 2>nul | findstr /i "ansys-meshing-prime" >nul
if %errorlevel% equ 0 (
    echo %BOLD%  Upgrading ansys-meshing-prime...%RESET%
    pip install --upgrade ansys-meshing-prime
)

echo.
echo %GREEN%✓%RESET% Upgrade complete — config unchanged
echo %YELLOW%○%RESET% Claude Code settings were NOT modified
echo.
echo %CYAN%╔══════════════════════════════════════════════════════════════╗%RESET%
echo %CYAN%║  ✅ UPGRADE COMPLETE                                       ║%RESET%
echo %CYAN%║  Config kept as-is — no changes to ~/.claude/settings.json ║%RESET%
echo %CYAN%║                                                              ║%RESET%
echo %CYAN%║  To verify: restart Claude Code CLI                         ║%RESET%
echo %CYAN%╚══════════════════════════════════════════════════════════════╝%RESET%
pause
exit /b 0

:: ── Configure Claude Code ─────────────────────────────────────────────────────
:configure
echo.
echo %BOLD%[4/4]%RESET% Configuring Claude Code CLI...

:: Determine config paths
set "CLAUDE_DIR=%USERPROFILE%\.claude"
set "SETTINGS_FILE=%CLAUDE_DIR%\settings.json"
set "DESKTOP_CONFIG=%CLAUDE_DIR%\claude_desktop_config.json"

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

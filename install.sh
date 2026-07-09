#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║              ANSYS MCP SERVER — INSTALLER for Claude Code CLI               ║
# ║                                                                              ║
# ║  Usage:                                                                      ║
# ║    ./install.sh                    Install + configure Claude Code            ║
# ║    ./install.sh run                Run the MCP server (stdio mode)            ║
# ║    ./install.sh install-fluent     Install with Fluent support                ║
# ║    ./install.sh install-all        Install with ALL Ansys products            ║
# ║    ./install.sh install-mechanical Install with Mechanical FEA support        ║
# ║    ./install.sh install-mapdl      Install with MAPDL support                 ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

set -euo pipefail

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
VENV_DIR="$PROJECT_DIR/.venv"
SRC_DIR="$PROJECT_DIR/src"

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${CYAN}║        ANSYS MCP SERVER — Claude Code CLI Installer         ║${RESET}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${RESET}"
echo ""

# ── Parse command ─────────────────────────────────────────────────────────────
INSTALL_MODE="${1:-base}"

# Parse --upgrade flag (second argument)
UPGRADE_FLAG=0
if [ "${2:-}" = "--upgrade" ] || [ "${1:-}" = "--upgrade" ]; then
    UPGRADE_FLAG=1
fi
if [ "${1:-}" = "--upgrade" ]; then
    INSTALL_MODE="upgrade"
fi

# ── Check Python ──────────────────────────────────────────────────────────────
echo -e "${BOLD}[1/4]${RESET} Checking Python..."
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}✗ Python3 not found! Install Python 3.10+${RESET}"
    echo "    Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    echo "    macOS:         brew install python@3.12"
    exit 1
fi
PYTHON="$(command -v python3)"
PY_VERSION="$($PYTHON --version)"
echo -e "${GREEN}✓${RESET} Found $PY_VERSION ($PYTHON)"

# ── Create virtual environment ────────────────────────────────────────────────
echo ""
echo -e "${BOLD}[2/4]${RESET} Setting up virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    $PYTHON -m venv "$VENV_DIR"
    echo -e "${GREEN}✓${RESET} Virtual environment created at .venv/"
else
    echo -e "${YELLOW}○${RESET} Virtual environment already exists"
fi

# Activate
source "$VENV_DIR/bin/activate"

# ── Install dependencies ──────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}[3/4]${RESET} Installing dependencies..."

# Upgrade pip (non-fatal)
pip install --upgrade pip --quiet || true

# Install base MCP SDK
echo -e "${BOLD}  Installing MCP SDK...${RESET}"
if pip install mcp; then
    echo -e "${GREEN}✓${RESET} Base MCP SDK installed"
else
    echo -e "${RED}✗ Failed to install MCP SDK${RESET}"
    echo "  Check internet connection or proxy settings."
    exit 1
fi

case "$INSTALL_MODE" in
    base)
        echo -e "${YELLOW}○${RESET} Installed base package (no Ansys libs)"
        echo "    Use ${CYAN}./install.sh install-fluent${RESET} for CFD"
        echo "    Use ${CYAN}./install.sh install-all${RESET} for all products"
        ;;
    run)
        ;;
    install-fluent)
        echo "  Installing ansys-fluent-core..."
        if pip install ansys-fluent-core; then
            echo -e "${GREEN}✓${RESET} Fluent CFD support installed"
        else
            echo -e "${YELLOW}⚠ ansys-fluent-core NOT installed (non-fatal)${RESET}"
        fi
        ;;
    install-mechanical)
        echo "  Installing ansys-mechanical-core..."
        if pip install ansys-mechanical-core; then
            echo -e "${GREEN}✓${RESET} Mechanical FEA support installed"
        else
            echo -e "${YELLOW}⚠ ansys-mechanical-core NOT installed (non-fatal)${RESET}"
        fi
        ;;
    install-mapdl)
        echo "  Installing ansys-mapdl-core..."
        if pip install ansys-mapdl-core; then
            echo -e "${GREEN}✓${RESET} MAPDL support installed"
        else
            echo -e "${YELLOW}⚠ ansys-mapdl-core NOT installed (non-fatal)${RESET}"
        fi
        ;;
    install-dpf)
        echo "  Installing ansys-dpf-core..."
        if pip install ansys-dpf-core; then
            echo -e "${GREEN}✓${RESET} DPF support installed"
        else
            echo -e "${YELLOW}⚠ ansys-dpf-core NOT installed (non-fatal)${RESET}"
        fi
        ;;
    install-meshing)
        echo "  Installing ansys-meshing-prime..."
        if pip install ansys-meshing-prime; then
            echo -e "${GREEN}✓${RESET} Meshing support installed"
        else
            echo -e "${YELLOW}⚠ ansys-meshing-prime NOT installed (non-fatal)${RESET}"
        fi
        ;;
    install-all)
        echo "  Installing all Ansys packages..."
        if pip install ansys-fluent-core ansys-mechanical-core ansys-mapdl-core ansys-dpf-core ansys-meshing-prime; then
            echo -e "${GREEN}✓${RESET} All Ansys products installed"
        else
            echo -e "${YELLOW}⚠ Some Ansys packages NOT installed (non-fatal)${RESET}"
        fi
        ;;
    upgrade)
        echo -e "${BOLD}  Upgrading Ansys MCP Server...${RESET}"
        echo ""
        # Git pull
        if command -v git &>/dev/null; then
            echo -e "${BOLD}  Pulling latest code from git...${RESET}"
            git pull || echo -e "${YELLOW}⚠ git pull failed — continuing with local files${RESET}"
        else
            echo -e "${YELLOW}○${RESET} Git not found — keeping local files"
        fi
        # Activate venv
        if [ ! -f "$VENV_DIR/bin/python" ]; then
            echo -e "${RED}✗ No venv found. Run ./install.sh first.${RESET}"
            exit 1
        fi
        source "$VENV_DIR/bin/activate"
        # Upgrade MCP SDK
        echo -e "${BOLD}  Upgrading MCP SDK...${RESET}"
        if pip install --upgrade mcp; then
            echo -e "${GREEN}✓${RESET} MCP SDK upgraded"
        else
            echo -e "${RED}✗ Failed to upgrade MCP SDK${RESET}"
            exit 1
        fi
        # Upgrade any installed Ansys packages
        for pkg in ansys-fluent-core ansys-mechanical-core ansys-mapdl-core ansys-dpf-core ansys-meshing-prime; do
            if pip list 2>/dev/null | grep -qi "$pkg"; then
                echo -e "${BOLD}  Upgrading $pkg...${RESET}"
                pip install --upgrade "$pkg" || echo -e "${YELLOW}⚠ $pkg upgrade skipped${RESET}"
            fi
        done
        echo ""
        echo -e "${GREEN}✓${RESET} Upgrade complete — config unchanged"
        echo -e "${YELLOW}○${RESET} Claude Code settings were NOT modified"
        echo ""
        echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${RESET}"
        echo -e "${CYAN}║  ✅ UPGRADE COMPLETE                                       ║${RESET}"
        echo -e "${CYAN}║  Config kept as-is — no changes to ~/.claude/settings.json ║${RESET}"
        echo -e "${CYAN}║                                                              ║${RESET}"
        echo -e "${CYAN}║  To verify: restart Claude Code CLI                         ║${RESET}"
        echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${RESET}"
        exit 0
        ;;
    *)
        echo -e "${RED}✗ Unknown mode: $INSTALL_MODE${RESET}"
        echo "  Usage: ./install.sh [base|run|install-fluent|install-mechanical|install-mapdl|install-dpf|install-meshing|install-all|--upgrade]"
        exit 1
        ;;
esac

# ── Run server (skip config for run mode) ─────────────────────────────────────
if [ "$INSTALL_MODE" = "run" ]; then
    echo ""
    echo -e "${BOLD}Running Ansys MCP Server (stdio mode)...${RESET}"
    echo -e "${YELLOW}Press Ctrl+C to stop${RESET}"
    echo ""

    if [ ! -f "$VENV_DIR/bin/python" ]; then
        echo -e "${RED}✗ Virtual environment not found. Run ./install.sh first.${RESET}"
        exit 1
    fi

    cd "$SRC_DIR"
    exec "$VENV_DIR/bin/python" -m ansys_mcp_server.server
    # NOTREACHED
fi

# ── Configure Claude Code ─────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}[4/4]${RESET} Configuring Claude Code CLI..."

# Claude Code CLI uses ~/.claude/settings.json
# Claude Desktop uses ~/.claude/claude_desktop_config.json (also supported as fallback)
CLAUDE_DIR="${HOME}/.claude"
SETTINGS_FILE="${CLAUDE_DIR}/settings.json"
DESKTOP_CONFIG="${CLAUDE_DIR}/claude_desktop_config.json"

# Ensure .claude directory exists
mkdir -p "$CLAUDE_DIR"

# Python path in venv
SERVER_PYTHON="$VENV_DIR/bin/python"

# Build server config
SERVER_JSON=$(cat <<END_JSON
{
    "ansys": {
        "command": "$SERVER_PYTHON",
        "args": ["-m", "ansys_mcp_server.server"],
        "cwd": "$SRC_DIR"
    }
}
END_JSON
)

# Write to Claude Code CLI config (~/.claude/settings.json)
python3 -c "
import json, os

config_file = os.path.expanduser('$SETTINGS_FILE')
server_config = json.loads(r'''$SERVER_JSON''')

config = {}
if os.path.exists(config_file):
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
    except:
        config = {}

if 'mcpServers' not in config:
    config['mcpServers'] = {}

config['mcpServers']['ansys'] = server_config['ansys']

with open(config_file, 'w') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print(f'✅ Claude Code CLI config: {config_file}')
"

# Also write to Claude Desktop config (for users who have both)
python3 -c "
import json, os

config_file = os.path.expanduser('$DESKTOP_CONFIG')
server_config = json.loads(r'''$SERVER_JSON''')

config = {}
if os.path.exists(config_file):
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
    except:
        config = {}

if 'mcpServers' not in config:
    config['mcpServers'] = {}

config['mcpServers']['ansys'] = server_config['ansys']

with open(config_file, 'w') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print(f'✅ Claude Desktop config: {config_file}')
" 2>/dev/null || true

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${CYAN}║  ✅ INSTALLATION COMPLETE                                   ║${RESET}"
echo -e "${CYAN}╠══════════════════════════════════════════════════════════════╣${RESET}"
echo -e "${CYAN}║                                                              ║${RESET}"
echo -e "${CYAN}║  MCP server added to:                                        ║${RESET}"
echo -e "${CYAN}║  ${SETTINGS_FILE}${RESET}"
echo -e "${CYAN}║                                                              ║${RESET}"
echo -e "${CYAN}║  Restart Claude Code CLI to use Ansys tools.                 ║${RESET}"
echo -e "${CYAN}║                                                              ║${RESET}"
echo -e "${CYAN}║  Test: "Проверь какие пакеты Ansys установлены"              ║${RESET}"
echo -e "${CYAN}║                                                              ║${RESET}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${RESET}"

# Ansys MCP Server

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-2025.06.18-green.svg)](https://modelcontextprotocol.io/)

🌐 **Language:** &nbsp; **EN** &nbsp;|&nbsp; [РУС](README.ru.md) &nbsp;|&nbsp; [中文](README.zh.md)

---

**Give Claude Code CLI direct control over Ansys engineering simulations.**

This MCP (Model Context Protocol) server wraps PyAnsys into 24 tools that Claude Code can call — run CFD in Fluent, crush FEA in Mechanical, drive MAPDL, post-process with DPF, and mesh with Prime. No more clicking through Workbench. Just describe what you want in plain language.

> 🎯 **What makes this different:** It's not a chatbot wrapper. It's not a documentation scraper. It gives Claude Code real, programmatic access to the Ansys solver process — the same API that PyAnsys uses internally. On a machine with Ansys installed and licensed, it *actually launches and controls the solvers*.

## 🎬 Quick Demo

```
User: "Simulate water flow in a 10cm pipe, 2m long, inlet velocity 5 m/s, steel walls, 300K"

Claude Code (via Ansys MCP):
  1. ansys_examples("pipe_flow")           ← finds the right setup pattern
  2. ansys_mesh_generate(pipe.stp, ...)    ← generates 500k-cell mesh
  3. ansys_set_material(water, steel)      ← assigns materials
  4. ansys_set_boundary_conditions(...)    ← velocity-inlet, pressure-outlet
  5. ansys_set_parameters(k-epsilon, ...)  ← configures turbulence model
  6. ansys_run_simulation(...)             ← launches Fluent with license
  7. ansys_get_convergence()               ← monitors residuals
  8. ansys_get_field_data("velocity")      ← extracts velocity field
  9. ansys_export_results(VTK)             ← exports for ParaView
```

All from *one sentence*. No scripting, no TUI commands, no Workbench clicking.

## 🚀 Installation (2 minutes)

### Prerequisites
- Python 3.10+
- Ansys installed and licensed (Fluent, Mechanical, or MAPDL)
- Claude Code CLI

### Option 1: One-command installer

```bash
# Clone
git clone https://github.com/vorobjewsen30-max/ansys-mcp-server.git
cd ansys-mcp-server

# Install + configure Claude Code automatically
./install.sh                    # Linux / Mac
# install.bat                   # Windows
```

The installer:
1. Creates a `.venv` virtual environment
2. Installs `mcp` SDK
3. Optionally installs PyAnsys packages (`install.sh install-all` for everything)
4. Writes Claude Code config to `~/.claude/claude_desktop_config.json`

### Option 2: Manual

```bash
# 1. Create venv
python3 -m venv .venv && source .venv/bin/activate

# 2. Install MCP SDK
pip install mcp

# 3. Install PyAnsys for your product(s)
pip install ansys-fluent-core        # CFD
pip install ansys-mapdl-core         # Structural / APDL
pip install ansys-dpf-core           # Post-processing
pip install ansys-meshing-prime      # Meshing

# 4. Configure Claude Code
# Add this to ~/.claude/claude_desktop_config.json:
```

```json
{
  "mcpServers": {
    "ansys": {
      "command": "/path/to/ansys-mcp-server/.venv/bin/python",
      "args": ["-m", "ansys_mcp_server.server"],
      "cwd": "/path/to/ansys-mcp-server/src"
    }
  }
}
```

```bash
# 5. Restart Claude Code CLI — done!
```

### Option 3: pip install

```bash
pip install git+https://github.com/vorobjewsen30-max/ansys-mcp-server.git

# Then add to Claude Code config:
# "command": "ansys-mcp-server"
```

## 🧰 Tools (24 total)

### 🚀 Simulation Management
| Tool | What it does |
|------|-------------|
| `ansys_list_packages` | Check which PyAnsys packages are installed |
| `ansys_run_simulation` | Launch a simulation (Fluent / Mechanical / MAPDL) |
| `ansys_get_simulation_status` | Get status of a running simulation |
| `ansys_stop_simulation` | Stop a simulation gracefully |
| `ansys_watch_simulation` | Monitor convergence live |

### 🔧 Mesh Operations
| Tool | What it does |
|------|-------------|
| `ansys_mesh_info` | Get mesh statistics (nodes, elements, quality) |
| `ansys_mesh_generate` | Generate mesh from geometry (STP, IGES, SCDOC) |
| `ansys_mesh_refine` | Refine mesh globally or by region |
| `ansys_mesh_quality` | Run quality diagnostics (skewness, aspect ratio, etc.) |
| `ansys_mesh_convert` | Convert between mesh formats (MSH ↔ CDB ↔ VTU) |

### 📊 Results Processing
| Tool | What it does |
|------|-------------|
| `ansys_get_results_summary` | List all available result fields |
| `ansys_get_field_data` | Extract field data at probe points (stress, velocity, temp…) |
| `ansys_export_results` | Export to CSV / VTK / HDF5 / NPZ |
| `ansys_get_convergence` | Get convergence history (residuals) |
| `ansys_create_report` | Auto-generate simulation report (MD/HTML/PDF) |

### ⚙️ Model Configuration
| Tool | What it does |
|------|-------------|
| `ansys_set_parameters` | Set solver settings, models, numerics |
| `ansys_get_parameters` | Read current simulation parameters |
| `ansys_set_boundary_conditions` | Create/modify BCs (inlet, outlet, wall, force…) |
| `ansys_list_boundary_conditions` | List all BCs in the model |
| `ansys_set_material` | Assign materials from library or custom properties |
| `ansys_list_materials` | Browse Ansys material library |

### 📖 Help & Documentation
| Tool | What it does |
|------|-------------|
| `ansys_get_documentation` | Search Ansys docs (k-epsilon, mesh quality, convergence…) |
| `ansys_list_solvers` | Catalog of available solvers and physics |
| `ansys_validate_setup` | Check setup for common errors before running |
| `ansys_examples` | Get complete worked examples (pipe flow, wing aero, etc.) |

## 📦 Supported Ansys Products

| Product | PyAnsys Package | What it does |
|---------|----------------|--------------|
| **Fluent** | `ansys-fluent-core` | CFD — fluids, heat transfer, turbulence, multiphase |
| **Mechanical** | `ansys-mechanical-core` | FEA — structural, thermal, modal, contact |
| **MAPDL** | `ansys-mapdl-core` | Classic APDL — full FEA + electromagnetics |
| **DPF** | `ansys-dpf-core` | Post-processing — extract/transform result data |
| **Prime Mesh** | `ansys-meshing-prime` | Meshing — tetra, hexcore, poly, boundary layers |

Install what you need:
```bash
pip install ansys-fluent-core        # Fluent only
pip install ansys-mapdl-core         # MAPDL only
# ... or install multiple
pip install ansys-fluent-core ansys-dpf-core ansys-meshing-prime
```

## 🔐 License

**The MCP server does not handle licensing directly.** PyAnsys picks up your Ansys license automatically from the standard environment:

```bash
# Already set by Ansys installation usually:
export ANSYSLI_SERVER="1055@your-license-server"
export ANSYSLMD_LICENSE_FILE="1055@your-license-server"

# Or for enterprise PyPIM:
export ANSYS_PLATFORM_INSTANCEMANAGEMENT_CONFIG="/path/to/config"
```

If `fluent` or `mapdl` work from your terminal, the MCP server will work too.

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────┐
│  Claude Code CLI                                     │
│  "Simulate pipe flow at Re=10000..."                 │
└──────────────┬───────────────────────────────────────┘
               │ stdio (JSON-RPC via MCP protocol)
┌──────────────▼───────────────────────────────────────┐
│  ansys-mcp-server (Python)                           │
│  ┌────────────────────────────────────────────────┐  │
│  │ 24 MCP Tools (Fluent, Mechanical, MAPDL, DPF)  │  │
│  └──────────────────┬─────────────────────────────┘  │
│                     │ Python API calls                │
│  ┌──────────────────▼─────────────────────────────┐  │
│  │ AnsysClient (lazy-loading PyAnsys wrapper)     │  │
│  └──────────────────┬─────────────────────────────┘  │
└─────────────────────┼────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          │      PyAnsys          │
          │  (fluent / mapdl /    │
          │   mechanical / dpf)   │
          └───────────┬───────────┘
                      │
          ┌───────────▼───────────┐
          │   Ansys License Mgr   │
          │   (ANSYSLI_SERVER)    │
          └───────────┬───────────┘
                      │
          ┌───────────▼───────────┐
          │  Ansys Solver Process │
          │  (fluent / mapdl /    │
          │   mechanical)         │
          └───────────────────────┘
```

## ❓ FAQ

**Q: Does it work without a license?**
A: The server runs and all 24 tools respond with guidance and API examples. But actual solver launch requires a licensed Ansys installation.

**Q: What Ansys versions are supported?**
A: PyAnsys supports 2024 R1 and newer (versions 241+). This server targets 2025 R1 (251) by default but accepts any version.

**Q: Can it run on a remote HPC cluster?**
A: Yes — PyAnsys supports connecting to remote Fluent/Mechanical instances. Configure via `ANSYS_PLATFORM_INSTANCEMANAGEMENT_CONFIG` (PyPIM).

**Q: Is this affiliated with Ansys/Synopsys?**
A: No. This is an independent community project. Ansys and Fluent are trademarks of Ansys Inc. / Synopsys.

**Q: Can Claude Code run a full parametric study?**
A: Yes. Describe it: *"Run 10 cases varying inlet velocity from 1 to 10 m/s, collect pressure drop, make a plot"* — Claude Code will call the tools in a loop.

## 🤝 Contributing

```bash
git clone https://github.com/vorobjewsen30-max/ansys-mcp-server.git
cd ansys-mcp-server
# Create a branch, make changes, send a PR
```

## 📄 License

MIT — use it, fork it, ship it.

---

🤖 Built for [Claude Code](https://claude.ai/code) · Powered by [PyAnsys](https://docs.pyansys.com) · MCP Protocol

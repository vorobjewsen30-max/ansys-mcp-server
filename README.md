<!-- mcp-name: io.github.vorobjewsen30-max/ansys-mcp-server -->

# Ansys MCP Server

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![MCP Registry](https://img.shields.io/badge/MCP-Registry-green.svg)](https://registry.modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-2025.06.18-green.svg)](https://modelcontextprotocol.io/)

🌐 **Language:** &nbsp; **EN** &nbsp;|&nbsp; [РУС](README.ru.md) &nbsp;|&nbsp; [中文](README.zh.md)

---

**Give Claude Code CLI direct control over Ansys engineering simulations.**

This MCP (Model Context Protocol) server wraps PyAnsys into **30 tools** that Claude Code can call — run CFD in Fluent, crush FEA in Mechanical, drive MAPDL, post-process with DPF, and mesh with Prime. The AI understands the **full simulation pipeline** across products: load geometry → mesh → set materials → apply BCs → solve → post-process → export. It knows which tool to call next, and it can reason across CFD, FEA, thermal, and FSI workflows.

No more clicking through Workbench. Just describe what you want in plain language.

> 🎯 **What makes this different:** It's not a chatbot wrapper, not a documentation scraper. It gives Claude Code real, programmatic access to the Ansys solver process — the same API that PyAnsys uses internally. On a machine with Ansys installed and licensed, it *actually launches and controls the solvers*. The solver window stays open — you watch mesh generation, convergence plots, and field data render **in real time**.

## 🎬 Quick Demo

```
User: "Simulate water flow in a 10cm pipe, 2m long, inlet velocity 5 m/s, steel walls, 300K"

Claude Code (via Ansys MCP):
  1. ansys_list_workflows("cfd")            ← understands which workflow to use
  2. ansys_open_gui(solver="fluent")        ← opens Fluent GUI (one persistent window)
  3. ansys_load_geometry("pipe.stp")        ← loads CAD → visible in Fluent window
  4. ansys_mesh_generate(element_size=0.5)  ← mesh builds in real-time on screen
  5. ansys_set_material("fluid", "water")   ← material colors update in GUI
  6. ansys_set_material("solid", "steel")
  7. ansys_set_boundary_conditions(...)     ← inlets, outlets highlighted on mesh
  8. ansys_set_parameters({"viscous_model": "k-epsilon"})
  9. ansys_run_simulation(iterations=500)   ← convergence plot updates live
  10. ansys_get_convergence()               ← residual history
  11. ansys_get_field_data("velocity")      ← probe points
  12. ansys_export_results(...)             ← CSV/VTK for ParaView
```

All from *one sentence*. No scripting, no TUI commands, no Workbench clicking. The AI knows the sequence.

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
3. Optionally installs PyAnsys packages (`./install.sh install-all` for everything)
4. Writes Claude Code config to `~/.claude/settings.json`

**Non-fatal errors:** If PyAnsys packages fail to install (no internet, missing build tools, etc.), the installer continues with a warning. The server works without them — you can install `pip install ansys-fluent-core` later.

### Upgrade without touching Claude config

```bash
# Pull latest code + upgrade packages, keep ~/.claude/settings.json intact
./install.sh --upgrade
install.bat --upgrade       # Windows
```

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

# 4. Configure Claude Code CLI (~/.claude/settings.json)
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

## 🧰 Tools (30 total)

### 🚀 Simulation Management (NEW — persistent GUI)
| Tool | What it does |
|------|-------------|
| `ansys_open_gui` | Launch Ansys Fluent GUI **once**. All subsequent commands render in this same window. Watch mesh, convergence, and results in real-time. |
| `ansys_session_status` | Show current session: PID, solver, uptime, commands sent |
| `ansys_close_session` | Close the Ansys window and end the session |
| `ansys_connect` | Attach to an already-running Ansys window (auto-detected via psutil) |
| `ansys_send_commands` | Send raw TUI/Scheme commands to the active Fluent window |
| `ansys_list_packages` | Check which PyAnsys packages are installed |

### 🔧 Mesh Operations
| Tool | What it does |
|------|-------------|
| `ansys_mesh_info` | Get mesh statistics (nodes, elements, quality) from the active window |
| `ansys_mesh_generate` | Generate mesh from loaded geometry. **Step 2** in the pipeline. Mesh renders in real-time. |
| `ansys_mesh_refine` | Refine mesh globally, by boundary, or by region |
| `ansys_mesh_quality` | Run quality diagnostics (skewness, aspect ratio, orthogonal quality) |

### ⚙️ Model Configuration
| Tool | What it does |
|------|-------------|
| `ansys_set_parameters` | Set solver settings, models, turbulence schemes |
| `ansys_get_parameters` | Read current simulation parameters |
| `ansys_set_boundary_conditions` | Create/modify BCs (velocity-inlet, pressure-outlet, wall, symmetry, etc.) |
| `ansys_list_boundary_conditions` | List all BCs in the model |
| `ansys_set_material` | Assign materials from library or custom properties |
| `ansys_list_materials` | Browse Ansys material library |

### 🚀 Run & Monitor
| Tool | What it does |
|------|-------------|
| `ansys_run_simulation` | Start calculation **in the active window**. Convergence plot updates iteration by iteration. |
| `ansys_get_convergence` | Get residual history (live) |
| `ansys_stop_simulation` | Stop a running calculation |

### 📊 Results Processing
| Tool | What it does |
|------|-------------|
| `ansys_get_results_summary` | List all available result fields in the active window |
| `ansys_get_field_data` | Extract field data at probe points (velocity, pressure, temperature, stress...) |
| `ansys_export_results` | Export to CSV / VTK / HDF5 / NPZ |
| `ansys_create_report` | Auto-generate simulation report (MD/HTML/PDF) |

### 🔄 Cross-Product Workflow (NEW)
| Tool | What it does |
|------|-------------|
| `ansys_list_workflows` | **Use this first.** Lists full simulation pipelines: CFD, FEA, Thermal, FSI. Tells you exactly which tools to call in which order. |
| `ansys_transfer_mesh` | Transfer mesh between Ansys products: Prime → Fluent, Fluent → Mechanical, MAPDL → DPF, etc. |

### 📖 Help & Documentation
| Tool | What it does |
|------|-------------|
| `ansys_get_documentation` | Search Ansys documentation |
| `ansys_list_solvers` | Catalog of solvers with **pipeline awareness** — shows what to do before and after each solver |
| `ansys_validate_setup` | Check setup for common errors before running |
| `ansys_examples` | Get complete worked examples (pipe flow, heat exchanger, wing aero, structural) |

## 🔄 Workflow-aware AI

The LLM doesn't just call random tools — it **understands the engineering pipeline**.

When you say *"Run a CFD analysis on this pipe"*, the AI knows:

1. **First:** load geometry (`ansys_load_geometry` — "FIRST STEP")
2. **Then:** generate mesh (`ansys_mesh_generate` — "SECOND STEP")
3. **Then:** materials, BCs, solver settings
4. **Then:** solve, monitor convergence
5. **Finally:** export results

When you say *"Fluid-structure interaction on a valve"*, the AI knows:
- CFD in Fluent → export pressures → FEA in Mechanical → map results back
- It calls `ansys_list_workflows("fsi")` to get the full pipeline step-by-step

When you say *"How do I set up a thermal analysis?"*, the AI calls `ansys_list_workflows("thermal")` and shows you the pipeline.

The tool descriptions are written with **pipeline context** — every tool knows what comes before and after it.

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
pip install ansys-fluent-core ansys-dpf-core ansys-meshing-prime  # Multiple
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
┌───────────────────────────────────────────────────────────────┐
│  Claude Code CLI                                              │
│  "Simulate pipe flow, then transfer to FEA for stress"        │
└──────────────────────┬────────────────────────────────────────┘
                       │ stdio (JSON-RPC via MCP protocol)
┌──────────────────────▼────────────────────────────────────────┐
│  ansys-mcp-server (Python)                                    │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ 30 MCP Tools + Workflow Awareness                        │  │
│  │ ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ │  │
│  │ │ Session │ │  Mesh    │ │  Solve   │ │  Workflow    │ │  │
│  │ │  Mgmt   │ │  Ops     │ │  & Post  │ │  Pipeline    │ │  │
│  │ └─────────┘ └──────────┘ └──────────┘ └──────────────┘ │  │
│  │                      │                                   │  │
│  │      execute_tui() / scheme.exec() / journal fallback    │  │
│  └──────────────────────┬────────────────────────────────────┘  │
│                          │ 3-tier delivery                       │
│  ┌──────────────────────▼────────────────────────────────────┐  │
│  │               LiveAnsysSession (singleton)                │  │
│  │  One persistent Fluent window — never duplicated          │  │
│  │  PID: 12345 | Commands: 47 | Uptime: 12 min              │  │
│  └──────────────────────┬────────────────────────────────────┘  │
└─────────────────────────┼──────────────────────────────────────┘
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
              │  ┌─────────────────┐  │
              │  │ GUI Window      │  │
              │  │ • Mesh renders  │  │
              │  │ • Convergence   │  │
              │  │ • Field data    │  │
              │  └─────────────────┘  │
              └───────────────────────┘
```

**Delivery tiers** (per command):
1. `session.execute_tui()` — direct TUI command via gRPC (preferred)
2. `session.scheme.exec()` — Scheme evaluation (fallback)
3. Journal file + auto-load (last resort)

## ❓ FAQ

**Q: Does it work without a license?**
A: The server runs and all tools respond with guidance and API examples. But actual solver launch requires a licensed Ansys installation. On a machine with a valid license, PyAnsys picks it up automatically.

**Q: What Ansys versions are supported?**
A: PyAnsys supports 2024 R1 and newer (versions 241+). This server targets 2025 R1 (251) by default but accepts any version.

**Q: Can it run on a remote HPC cluster?**
A: Yes — PyAnsys supports connecting to remote Fluent/Mechanical instances. Configure via `ANSYS_PLATFORM_INSTANCEMANAGEMENT_CONFIG` (PyPIM). For Slurm-based clusters, use `ansys-mapdl-core` with `launch_mapdl(start_instance=False)` and point to the cluster's solver binary.

**Q: Is this affiliated with Ansys/Synopsys?**
A: No. This is an independent community project. Ansys and Fluent are trademarks of Ansys Inc. / Synopsys.

**Q: Does the AI understand multiphysics workflows?**
A: Yes. The server includes `ansys_list_workflows` which describes the full pipeline for CFD, FEA, thermal, and FSI. The LLM understands which product handles what, and in which order to call tools. For example, FSI = Fluent (fluid) → Mechanical (structure) with mesh transfer in between.

**Q: Can Claude Code run a full parametric study?**
A: Yes. Describe it: *"Run 10 cases varying inlet velocity from 1 to 10 m/s, collect pressure drop, make a plot"* — Claude Code calls the tools in a loop automatically.

**Q: Can it work with my existing .cas/.dat/.mechdb/.inp files?**
A: Yes. Use `ansys_run_simulation` with the `input_file` parameter pointing to your existing file. For CAD geometry (.stp, .iges, .scdoc), use `ansys_load_geometry` first.

**Q: Does it save result files automatically?**
A: Yes. After each simulation, result files are saved to the output directory: Fluent writes `.cas.h5` + `.dat.h5`, Mechanical writes `.rst`, MAPDL writes `.rst/.rth`. You can also manually export with `ansys_export_results` in CSV, VTK, HDF5, or NPZ format.

**Q: What result formats can I get?**
A: `ansys_export_results` supports: **CSV** (Excel/Python analysis), **VTK/VTU** (ParaView visualization), **HDF5** (efficient binary for ML pipelines), **NPZ** (NumPy-compatible). Plus auto-generated reports in Markdown/HTML/PDF.

**Q: Can it handle transient simulations?**
A: Yes. Set time-stepping via `ansys_set_parameters` with `{"time": "transient", "time_step_size": 0.01, "num_time_steps": 100}`.

**Q: What turbulence models are available?**
A: Through Fluent/MAPDL: k-epsilon (standard, RNG, realizable), k-omega (standard, SST), Spalart-Allmaras, Reynolds Stress, LES, DES. Describe what you need and Claude Code will configure the right one.

**Q: Can it do multiphase?**
A: Yes — VOF, Eulerian, Mixture, DPM. Tell Claude Code: *"set up a VOF model for water-air free surface"*.

**Q: Can I use it on Windows while Ansys runs on Linux?**
A: Yes. The MCP server runs wherever Claude Code runs. If Ansys is on a Linux workstation, install the server there and connect Claude Code to it.

**Q: What if the simulation diverges?**
A: Claude Code can diagnose and fix it. `ansys_get_convergence` shows which equations are problematic. Claude Code adjusts under-relaxation, switches to first-order, or refines the mesh.

**Q: After rebooting, do I need to restart the MCP server?**
A: No. If configured via `settings.json` (which `install.sh` does automatically), Claude Code CLI starts the MCP server on launch.

**Q: Is there a `--upgrade` flag?**
A: Yes. `./install.sh --upgrade` or `install.bat --upgrade` pulls the latest code and upgrades packages without touching `~/.claude/settings.json`.

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

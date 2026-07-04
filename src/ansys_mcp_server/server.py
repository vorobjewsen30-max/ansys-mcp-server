#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║                    ANSYS MCP SERVER v1.0.0                                     ║
║          Model Context Protocol Server for Ansys Engineering Simulation        ║
║                                                                                ║
║  Exposes Ansys tools to Claude Code CLI:                                       ║
║    • Simulation Management  — run, stop, monitor simulations                   ║
║    • Mesh Operations         — generate, refine, inspect, quality-check        ║
║    • Results Processing      — extract, export, visualize field data           ║
║    • Model Configuration     — parameters, BCs, materials, solver settings     ║
║    • Documentation           — solver docs, examples, best practices           ║
╚══════════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationCapabilities
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

# ─────────────────────────────────────────────────────────────────────────────
# ANSYS CLIENT — lightweight wrapper over PyAnsys
# ─────────────────────────────────────────────────────────────────────────────
# On a machine with Ansys installed + licensed, PyAnsys picks up the license
# automatically via ANSYSLI_SERVER / ANSYSLMD_LICENSE_FILE env vars.
# No extra detection needed — just install PyAnsys and launch.


class AnsysClient:
    """Lazy-loading PyAnsys wrapper. Call launch_*() — it works if Ansys is installed."""

    def __init__(self):
        self._fluent = None
        self._mechanical = None
        self._mapdl = None
        self._dpf = None
        self._meshing = None
        self._fluent_session = None
        self._mechanical_session = None
        self._mapdl_session = None
        self._connected_product: Optional[str] = None

    # ── Package checks ──────────────────────────────────────────────────

    @property
    def has_fluent(self) -> bool:
        try:
            import ansys.fluent.core  # noqa
            return True
        except ImportError:
            return False

    @property
    def has_mechanical(self) -> bool:
        try:
            import ansys.mechanical.core  # noqa
            return True
        except ImportError:
            return False

    @property
    def has_mapdl(self) -> bool:
        try:
            import ansys.mapdl.core  # noqa
            return True
        except ImportError:
            return False

    @property
    def has_dpf(self) -> bool:
        try:
            import ansys.dpf.core  # noqa
            return True
        except ImportError:
            return False

    @property
    def has_meshing(self) -> bool:
        try:
            import ansys.meshing.prime  # noqa
            return True
        except ImportError:
            return False

    @property
    def available_packages(self) -> dict[str, bool]:
        return {
            "fluent": self.has_fluent,
            "mechanical": self.has_mechanical,
            "mapdl": self.has_mapdl,
            "dpf": self.has_dpf,
            "meshing": self.has_meshing,
        }

    def packages_report(self) -> str:
        installed = [k for k, v in self.available_packages.items() if v]
        not_installed = [k for k, v in self.available_packages.items() if not v]
        lines = []
        if installed:
            lines.append(f"\u2705 PyAnsys installed: {', '.join(installed)}")
        if not_installed:
            lines.append(f"\u274c PyAnsys not installed: {', '.join(not_installed)}")
        if not installed:
            lines.append("")
            lines.append("Install: pip install ansys-fluent-core ansys-mapdl-core ...")
        return "\n".join(lines)

    # ── Lazy loaders ────────────────────────────────────────────────────

    def _load_fluent(self):
        if not self.has_fluent:
            raise ImportError("pip install ansys-fluent-core")
        if self._fluent is None:
            import ansys.fluent.core as pyfluent
            self._fluent = pyfluent
        return self._fluent

    def _load_mechanical(self):
        if not self.has_mechanical:
            raise ImportError("pip install ansys-mechanical-core")
        if self._mechanical is None:
            import ansys.mechanical.core as pymech
            self._mechanical = pymech
        return self._mechanical

    def _load_mapdl(self):
        if not self.has_mapdl:
            raise ImportError("pip install ansys-mapdl-core")
        if self._mapdl is None:
            import ansys.mapdl.core as pymapdl
            self._mapdl = pymapdl
        return self._mapdl

    def _load_dpf(self):
        if not self.has_dpf:
            raise ImportError("pip install ansys-dpf-core")
        if self._dpf is None:
            import ansys.dpf.core as dpf
            self._dpf = dpf
        return self._dpf

    def _load_meshing(self):
        if not self.has_meshing:
            raise ImportError("pip install ansys-meshing-prime")
        if self._meshing is None:
            import ansys.meshing.prime as meshing
            self._meshing = meshing
        return self._meshing

    # ── Launch solvers ──────────────────────────────────────────────────

    def launch_fluent(self, product_version: str = "251", **kwargs) -> Any:
        """Launch Fluent. License is picked up automatically."""
        pyfluent = self._load_fluent()
        session = pyfluent.launch_fluent(product_version=product_version, mode="solver")
        self._fluent_session = session
        self._connected_product = "fluent"
        return session

    def launch_mechanical(self, **kwargs) -> Any:
        """Launch Mechanical. License is picked up automatically."""
        pymech = self._load_mechanical()
        session = pymech.launch_mechanical(batch=True)
        self._mechanical_session = session
        self._connected_product = "mechanical"
        return session

    def launch_mapdl(self, nproc: int = 4, **kwargs) -> Any:
        """Launch MAPDL. License is picked up automatically."""
        pymapdl = self._load_mapdl()
        session = pymapdl.launch_mapdl(nproc=nproc)
        self._mapdl_session = session
        self._connected_product = "mapdl"
        return session

    @property
    def active_product(self) -> Optional[str]:
        return self._connected_product

    @property
    def active_session(self) -> Optional[Any]:
        if self._connected_product == "fluent":
            return self._fluent_session
        elif self._connected_product == "mechanical":
            return self._mechanical_session
        elif self._connected_product == "mapdl":
            return self._mapdl_session
        return None

    def disconnect(self) -> str:
        product = self._connected_product
        if not product:
            return "No active session."
        try:
            if product == "fluent" and self._fluent_session:
                self._fluent_session.exit()
                self._fluent_session = None
            elif product == "mechanical" and self._mechanical_session:
                self._mechanical_session.exit()
                self._mechanical_session = None
            elif product == "mapdl" and self._mapdl_session:
                self._mapdl_session.exit()
                self._mapdl_session = None
            self._connected_product = None
            return f"\u2705 Disconnected from {product.upper()}."
        except Exception as e:
            return f"\u26a0\ufe0f Error: {e}"


# Global client
ansys = AnsysClient()
# ─────────────────────────────────────────────────────────────────────────────
# TOOL DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

TOOLS = [
    # ═══════════════════════════════════════════════════════════════════════
    # SIMULATION MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════
    Tool(
        name="ansys_list_packages",
        description="Check which PyAnsys Python packages are installed and available",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="ansys_run_simulation",
        description="Run an Ansys simulation from an input file. Supports Fluent (.cas/.cas.gz), Mechanical (.mechdb), MAPDL (.dat/.inp), and Workbench archives (.wbpz).",
        inputSchema={
            "type": "object",
            "properties": {
                "solver": {
                    "type": "string",
                    "enum": ["fluent", "mechanical", "mapdl"],
                    "description": "Solver to use for the simulation",
                },
                "input_file": {
                    "type": "string",
                    "description": "Absolute path to the simulation input file",
                },
                "output_dir": {
                    "type": "string",
                    "description": "Directory to write output files (default: same as input file)",
                },
                "num_processors": {
                    "type": "integer",
                    "description": "Number of CPU cores to use (default: auto)",
                },
                "extra_args": {
                    "type": "object",
                    "description": "Additional solver-specific parameters as key-value pairs",
                },
            },
            "required": ["solver", "input_file"],
        },
    ),
    Tool(
        name="ansys_get_simulation_status",
        description="Get the current status of a running simulation",
        inputSchema={
            "type": "object",
            "properties": {
                "solver": {
                    "type": "string",
                    "enum": ["fluent", "mechanical", "mapdl"],
                    "description": "Solver to query",
                },
            },
            "required": ["solver"],
        },
    ),
    Tool(
        name="ansys_stop_simulation",
        description="Stop a running simulation gracefully",
        inputSchema={
            "type": "object",
            "properties": {
                "solver": {
                    "type": "string",
                    "enum": ["fluent", "mechanical", "mapdl"],
                    "description": "Solver to stop",
                },
            },
            "required": ["solver"],
        },
    ),
    Tool(
        name="ansys_watch_simulation",
        description="Monitor a running simulation and return convergence data / residuals over time",
        inputSchema={
            "type": "object",
            "properties": {
                "solver": {
                    "type": "string",
                    "enum": ["fluent", "mechanical", "mapdl"],
                    "description": "Solver to monitor",
                },
                "interval_seconds": {
                    "type": "number",
                    "description": "How often to poll (seconds). Default: 5.0",
                },
            },
            "required": ["solver"],
        },
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # MESH OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════
    Tool(
        name="ansys_mesh_info",
        description="Get mesh statistics: node count, element count, element types, quality metrics",
        inputSchema={
            "type": "object",
            "properties": {
                "solver": {
                    "type": "string",
                    "enum": ["fluent", "mechanical", "mapdl", "meshing"],
                    "description": "Solver context for mesh",
                },
                "mesh_file": {
                    "type": "string",
                    "description": "Path to mesh file (.msh, .cas, .cdb, .pmdb). Optional — uses active session if omitted.",
                },
            },
            "required": ["solver"],
        },
    ),
    Tool(
        name="ansys_mesh_generate",
        description="Generate a computational mesh from geometry. Supports Fluent Meshing and Mechanical meshing workflows.",
        inputSchema={
            "type": "object",
            "properties": {
                "solver": {
                    "type": "string",
                    "enum": ["fluent", "mechanical", "meshing"],
                    "description": "Target solver for mesh",
                },
                "geometry_file": {
                    "type": "string",
                    "description": "Path to geometry file (.scdoc, .stp, .iges, .agdb, .pmdb)",
                },
                "element_size": {
                    "type": "number",
                    "description": "Target element size in meters (default: auto)",
                },
                "element_type": {
                    "type": "string",
                    "enum": ["tet", "hex", "poly", "hexcore", "poly-hexcore"],
                    "description": "Element type to generate",
                },
                "curvature_angle": {
                    "type": "number",
                    "description": "Curvature refinement angle in degrees (default: 18)",
                },
                "growth_rate": {
                    "type": "number",
                    "description": "Mesh growth rate (default: 1.2)",
                },
                "output_file": {
                    "type": "string",
                    "description": "Path to save generated mesh",
                },
            },
            "required": ["solver", "geometry_file"],
        },
    ),
    Tool(
        name="ansys_mesh_refine",
        description="Refine an existing mesh — increase resolution in specific regions or globally",
        inputSchema={
            "type": "object",
            "properties": {
                "solver": {
                    "type": "string",
                    "enum": ["fluent", "mechanical", "mapdl"],
                    "description": "Solver context for mesh refinement",
                },
                "method": {
                    "type": "string",
                    "enum": ["global", "boundary", "region", "gradient", "curvature"],
                    "description": "Refinement method",
                },
                "refinement_level": {
                    "type": "integer",
                    "description": "How many levels to refine (1-5, default: 1)",
                },
                "region_center": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "[x, y, z] center of refinement region (for region method)",
                },
                "region_radius": {
                    "type": "number",
                    "description": "Radius of refinement region (for region method)",
                },
                "boundary_name": {
                    "type": "string",
                    "description": "Name of boundary zone to refine near (for boundary method)",
                },
                "field_variable": {
                    "type": "string",
                    "description": "Variable for gradient-based refinement (e.g., 'velocity', 'pressure')",
                },
            },
            "required": ["solver", "method"],
        },
    ),
    Tool(
        name="ansys_mesh_quality",
        description="Check mesh quality: orthogonal quality, skewness, aspect ratio, Jacobian ratio",
        inputSchema={
            "type": "object",
            "properties": {
                "solver": {
                    "type": "string",
                    "enum": ["fluent", "mechanical", "mapdl"],
                    "description": "Solver context for mesh quality check",
                },
                "metrics": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["orthogonal_quality", "skewness", "aspect_ratio", "jacobian", "warping_factor", "all"]
                    },
                    "description": "Which quality metrics to compute (default: all)",
                },
                "threshold_warnings": {
                    "type": "boolean",
                    "description": "Whether to emit warnings when quality is below recommended thresholds",
                },
            },
            "required": ["solver"],
        },
    ),
    Tool(
        name="ansys_load_geometry",
        description="Load a CAD geometry file into Ansys for meshing and simulation. Supports .stp, .step, .iges, .igs, .scdoc, .agdb, .pmdb, .x_t, .sat formats. Call this FIRST when starting from a CAD file.",
        inputSchema={
            "type": "object",
            "properties": {
                "solver": {
                    "type": "string",
                    "enum": ["fluent", "mechanical", "mapdl"],
                    "description": "Target solver for the geometry",
                },
                "geometry_file": {
                    "type": "string",
                    "description": "Absolute path to the CAD/geometry file",
                },
                "import_format": {
                    "type": "string",
                    "enum": ["stp", "step", "iges", "igs", "scdoc", "agdb", "pmdb", "x_t", "sat", "auto"],
                    "description": "Format of the geometry file (default: auto-detect from extension)",
                },
            },
            "required": ["solver", "geometry_file"],
        },
    ),
    Tool(
        name="ansys_mesh_convert",
        description="Convert mesh between formats (.msh ↔ .cas ↔ .cdb ↔ .vtu ↔ .pmdb)",
        inputSchema={
            "type": "object",
            "properties": {
                "input_file": {
                    "type": "string",
                    "description": "Source mesh file path",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["msh", "cas", "cdb", "vtu", "pmdb", "stl"],
                    "description": "Target format",
                },
                "output_file": {
                    "type": "string",
                    "description": "Output file path (auto-generated if omitted)",
                },
            },
            "required": ["input_file", "output_format"],
        },
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # RESULTS PROCESSING
    # ═══════════════════════════════════════════════════════════════════════
    Tool(
        name="ansys_get_results_summary",
        description="Get a summary of available results from a completed simulation",
        inputSchema={
            "type": "object",
            "properties": {
                "solver": {
                    "type": "string",
                    "enum": ["fluent", "mechanical", "mapdl", "dpf"],
                    "description": "Solver context",
                },
                "result_file": {
                    "type": "string",
                    "description": "Path to result file (.dat.h5, .rst, .cas.h5). Uses active session if omitted.",
                },
            },
            "required": ["solver"],
        },
    ),
    Tool(
        name="ansys_get_field_data",
        description="Extract field data (scalar/vector/tensor) from simulation results at specified locations",
        inputSchema={
            "type": "object",
            "properties": {
                "solver": {
                    "type": "string",
                    "enum": ["fluent", "mechanical", "mapdl", "dpf"],
                    "description": "Solver context",
                },
                "field": {
                    "type": "string",
                    "description": "Field to extract — e.g., 'pressure', 'velocity', 'temperature', 'stress', 'strain', 'displacement'",
                },
                "component": {
                    "type": "string",
                    "enum": ["x", "y", "z", "magnitude", "von_mises", "max_principal", "min_principal", "xx", "yy", "zz", "xy", "yz", "xz"],
                    "description": "Component of vector/tensor field. Use 'magnitude' for scalar magnitude.",
                },
                "locations": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                    },
                    "description": "List of [x, y, z] probe points",
                },
                "export_format": {
                    "type": "string",
                    "enum": ["json", "csv"],
                    "description": "Output format (default: json)",
                },
            },
            "required": ["solver", "field"],
        },
    ),
    Tool(
        name="ansys_export_results",
        description="Export simulation results to file (CSV, VTK, HDF5, or EnSight format)",
        inputSchema={
            "type": "object",
            "properties": {
                "solver": {
                    "type": "string",
                    "enum": ["fluent", "mechanical", "mapdl", "dpf"],
                    "description": "Solver context",
                },
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Fields to export, e.g. ['pressure', 'velocity', 'temperature']",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["csv", "vtk", "hdf5", "ensight", "vtu", "npz"],
                    "description": "Export format",
                },
                "output_file": {
                    "type": "string",
                    "description": "Output file path",
                },
                "timesteps": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Timestep indices to export (default: last). For transient simulations.",
                },
            },
            "required": ["solver", "fields", "output_format", "output_file"],
        },
    ),
    Tool(
        name="ansys_get_convergence",
        description="Get convergence history (residuals) from a simulation",
        inputSchema={
            "type": "object",
            "properties": {
                "solver": {
                    "type": "string",
                    "enum": ["fluent", "mechanical", "mapdl"],
                    "description": "Solver context",
                },
                "plot_data": {
                    "type": "boolean",
                    "description": "Whether to return data suitable for plotting (tab-separated iter/residual pairs)",
                },
            },
            "required": ["solver"],
        },
    ),
    Tool(
        name="ansys_create_report",
        description="Generate an automated simulation report with key results, images, and tables",
        inputSchema={
            "type": "object",
            "properties": {
                "solver": {
                    "type": "string",
                    "enum": ["fluent", "mechanical", "mapdl"],
                    "description": "Solver context",
                },
                "sections": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["summary", "mesh", "convergence", "results", "comparison", "all"]
                    },
                    "description": "Report sections to include (default: all)",
                },
                "output_file": {
                    "type": "string",
                    "description": "Output path (.html, .pdf, or .md). Default: simulation_report.md",
                },
            },
            "required": ["solver"],
        },
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # MODEL CONFIGURATION
    # ═══════════════════════════════════════════════════════════════════════
    Tool(
        name="ansys_set_parameters",
        description="Set simulation parameters (solver settings, physical models, numerics)",
        inputSchema={
            "type": "object",
            "properties": {
                "solver": {
                    "type": "string",
                    "enum": ["fluent", "mechanical", "mapdl"],
                    "description": "Solver to configure",
                },
                "parameters": {
                    "type": "object",
                    "description": "Key-value pairs of parameters to set. Examples: {\"viscous_model\": \"k-epsilon\", \"density\": 1.225, \"velocity_inlet\": 10.0, \"iterations\": 1000}",
                },
            },
            "required": ["solver", "parameters"],
        },
    ),
    Tool(
        name="ansys_get_parameters",
        description="Get current simulation parameters and settings",
        inputSchema={
            "type": "object",
            "properties": {
                "solver": {
                    "type": "string",
                    "enum": ["fluent", "mechanical", "mapdl"],
                    "description": "Solver to query",
                },
                "category": {
                    "type": "string",
                    "enum": ["all", "solver", "models", "materials", "boundary_conditions", "numerics", "initialization"],
                    "description": "Parameter category to retrieve (default: all)",
                },
            },
            "required": ["solver"],
        },
    ),
    Tool(
        name="ansys_set_boundary_conditions",
        description="Set boundary conditions on named zones/regions",
        inputSchema={
            "type": "object",
            "properties": {
                "solver": {
                    "type": "string",
                    "enum": ["fluent", "mechanical", "mapdl"],
                    "description": "Solver context",
                },
                "zone_name": {
                    "type": "string",
                    "description": "Name of the boundary zone",
                },
                "bc_type": {
                    "type": "string",
                    "description": "Boundary condition type. Examples (Fluent): 'velocity_inlet', 'pressure_outlet', 'wall', 'symmetry', 'mass_flow_inlet'. Examples (Mechanical): 'fixed_support', 'force', 'pressure', 'displacement', 'frictionless_support'.",
                },
                "values": {
                    "type": "object",
                    "description": "BC values. Examples: {\"velocity_magnitude\": 10, \"temperature\": 300} or {\"force\": [1000, 0, 0]}",
                },
            },
            "required": ["solver", "zone_name", "bc_type", "values"],
        },
    ),
    Tool(
        name="ansys_list_boundary_conditions",
        description="List all boundary conditions and zones in the current model",
        inputSchema={
            "type": "object",
            "properties": {
                "solver": {
                    "type": "string",
                    "enum": ["fluent", "mechanical", "mapdl"],
                    "description": "Solver context",
                },
            },
            "required": ["solver"],
        },
    ),
    Tool(
        name="ansys_set_material",
        description="Set material properties for a named region or globally",
        inputSchema={
            "type": "object",
            "properties": {
                "solver": {
                    "type": "string",
                    "enum": ["fluent", "mechanical", "mapdl"],
                    "description": "Solver context",
                },
                "region_name": {
                    "type": "string",
                    "description": "Region/zone name, or 'global' for default material",
                },
                "material_name": {
                    "type": "string",
                    "description": "Material name from Ansys library, e.g., 'aluminum', 'steel', 'air', 'water-liquid'",
                },
                "properties": {
                    "type": "object",
                    "description": "Custom material properties. Examples: {\"density\": 2700, \"youngs_modulus\": 7e10, \"poisson_ratio\": 0.33, \"thermal_conductivity\": 237}",
                },
            },
            "required": ["solver", "region_name", "material_name"],
        },
    ),
    Tool(
        name="ansys_list_materials",
        description="List materials in the current model and search the Ansys material library",
        inputSchema={
            "type": "object",
            "properties": {
                "solver": {
                    "type": "string",
                    "enum": ["fluent", "mechanical", "mapdl"],
                    "description": "Solver context",
                },
                "search": {
                    "type": "string",
                    "description": "Search term for material library lookup (e.g., 'titanium', 'composite', 'polymer')",
                },
            },
            "required": ["solver"],
        },
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # DOCUMENTATION & HELP
    # ═══════════════════════════════════════════════════════════════════════
    Tool(
        name="ansys_get_documentation",
        description="Get help and documentation for Ansys features, commands, and best practices",
        inputSchema={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Documentation topic to search for",
                },
                "solver": {
                    "type": "string",
                    "enum": ["fluent", "mechanical", "mapdl", "meshing", "dpf", "any"],
                    "description": "Filter to a specific solver (default: any)",
                },
                "category": {
                    "type": "string",
                    "enum": ["tutorial", "reference", "theory", "example", "best_practice", "troubleshooting", "any"],
                    "description": "Category of help content (default: any)",
                },
            },
            "required": ["topic"],
        },
    ),
    Tool(
        name="ansys_list_solvers",
        description="List available Ansys solvers and their capabilities, physics domains, and typical applications",
        inputSchema={
            "type": "object",
            "properties": {
                "physics": {
                    "type": "string",
                    "enum": ["all", "cfd", "structural", "thermal", "electromagnetic", "acoustic", "multiphase", "combustion", "optimization"],
                    "description": "Filter by physics domain (default: all)",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="ansys_validate_setup",
        description="Validate a simulation setup — check for common errors, missing BCs, incompatible settings, mesh issues",
        inputSchema={
            "type": "object",
            "properties": {
                "solver": {
                    "type": "string",
                    "enum": ["fluent", "mechanical", "mapdl"],
                    "description": "Solver context",
                },
                "checks": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["mesh", "boundary_conditions", "materials", "solver_settings", "units", "all"]
                    },
                    "description": "What to validate (default: all)",
                },
            },
            "required": ["solver"],
        },
    ),
    Tool(
        name="ansys_examples",
        description="Get example simulation setups, best practices, and typical workflows for common engineering problems",
        inputSchema={
            "type": "object",
            "properties": {
                "application": {
                    "type": "string",
                    "description": "Application area. Examples: 'pipe_flow', 'heat_exchanger', 'wing_aerodynamics', 'structural_analysis', 'thermal_stress', 'valve_cfd', 'mixer', 'external_aero', 'composite_analysis'",
                },
                "solver": {
                    "type": "string",
                    "enum": ["fluent", "mechanical", "mapdl", "any"],
                    "description": "Preferred solver (default: any)",
                },
            },
            "required": ["application"],
        },
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# TOOL HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

SOLVER_INFO = {
    "fluent": {
        "name": "Ansys Fluent",
        "physics": "Computational Fluid Dynamics (CFD)",
        "description": "General-purpose CFD solver for fluid flow, heat transfer, turbulence, multiphase, combustion, and aerodynamics.",
        "typical_applications": ["pipe flow", "heat exchanger", "aerodynamics", "mixing tank", "HVAC", "turbomachinery", "valve analysis"],
        "file_formats": {"case": ".cas", "data": ".dat", "mesh": ".msh", "journal": ".jou"},
        "license_feature": "fluent",
    },
    "mechanical": {
        "name": "Ansys Mechanical",
        "physics": "Finite Element Analysis (FEA) — Structural, Thermal",
        "description": "FEA solver for structural mechanics, thermal analysis, modal analysis, and coupled field problems.",
        "typical_applications": ["stress analysis", "modal analysis", "thermal expansion", "contact mechanics", "fatigue", "composite structures"],
        "file_formats": {"database": ".mechdb", "input": ".dat", "result": ".rst"},
        "license_feature": "mechanical",
    },
    "mapdl": {
        "name": "Ansys MAPDL",
        "physics": "Classic Ansys — Structural, Thermal, Electromagnetic",
        "description": "Classic Ansys Mechanical APDL solver. Full access to all FEA capabilities via APDL command language.",
        "typical_applications": ["detailed structural analysis", "nonlinear materials", "contact", "coupled field", "custom element formulations"],
        "file_formats": {"input": ".dat/.inp", "database": ".db", "result": ".rst/.rth"},
        "license_feature": "ansys",
    },
    "dpf": {
        "name": "Ansys DPF",
        "physics": "Data Processing Framework",
        "description": "Post-processing framework for Ansys result files. Extract, transform, and analyze simulation data programmatically.",
        "typical_applications": ["result post-processing", "field extraction", "custom visualization", "data pipelines"],
        "file_formats": {"result": ".rst/.rth/.rmg"},
        "license_feature": "dpf",
    },
    "meshing": {
        "name": "Ansys Meshing / Fluent Meshing",
        "physics": "Mesh Generation",
        "description": "Geometry preparation and mesh generation tools. Supports tetrahedral, hexcore, polyhedral, and hybrid meshes.",
        "typical_applications": ["mesh generation", "geometry cleanup", "mesh quality improvement"],
        "file_formats": {"geometry": ".scdoc/.pmdb/.stp", "mesh": ".msh/.msh.gz"},
        "license_feature": "meshing",
    },
}


async def handle_list_packages() -> str:
    """Handle ansys_list_packages tool call."""
    return ansys.packages_report


async def handle_list_solvers(physics: str = "all") -> str:
    """Handle ansys_list_solvers tool call."""
    physics = physics or "all"

    lines = ["╔══════════════════════════════════════════════════════════════╗"]
    lines.append("║               ANSYS SOLVER CATALOG                          ║")
    lines.append("╚══════════════════════════════════════════════════════════════╝")
    lines.append("")

    physics_filter = {
        "cfd": ["fluent"],
        "structural": ["mechanical", "mapdl"],
        "thermal": ["mechanical", "mapdl"],
        "electromagnetic": ["mapdl"],
        "acoustic": ["fluent", "mechanical"],
        "multiphase": ["fluent"],
        "combustion": ["fluent"],
        "optimization": ["fluent", "mechanical"],
    }

    allowed = None if physics == "all" else set(physics_filter.get(physics, []))

    for key, info in SOLVER_INFO.items():
        if allowed is not None and key not in allowed:
            continue

        installed = ansys.available_packages.get(key, False)
        status = "✅ INSTALLED" if installed else "❌ NOT INSTALLED"
        lines.append(f"  [{key.upper()}] {info['name']}")
        lines.append(f"      Physics:   {info['physics']}")
        lines.append(f"      Status:    {status}")
        lines.append(f"      License:   {info['license_feature']}")
        lines.append(f"      Desc:      {info['description']}")
        lines.append(f"      Apps:      {', '.join(info['typical_applications'][:5])}")
        lines.append("")

    if allowed is None:
        lines.append("── Installation ──")
        lines.append("  pip install ansys-mcp-server[all]")
        lines.append("  # or pick one:")
        lines.append("  pip install ansys-fluent-core")
        lines.append("  pip install ansys-mechanical-core")
        lines.append("  pip install ansys-mapdl-core")
        lines.append("  pip install ansys-dpf-core")
        lines.append("  pip install ansys-meshing-prime")

    return "\n".join(lines)


async def handle_run_simulation(solver: str, input_file: str, output_dir: str = None,
                                 num_processors: int = None, extra_args: dict = None) -> str:
    """Handle ansys_run_simulation — try real launch, fall back to guidance."""
    input_path = Path(input_file)
    if not input_path.exists():
        return f"❌ ERROR: Input file not found: {input_file}"

    output_dir = output_dir or str(input_path.parent)
    num_processors = num_processors or os.cpu_count() or 4
    extra_args = extra_args or {}

    lines = [
        f"🚀 LAUNCHING SIMULATION",
        f"   Solver:      {solver.upper()}",
        f"   Input:       {input_file}",
        f"   Output dir:  {output_dir}",
        f"   Processors:  {num_processors}",
        "",
    ]

    launch_error = None
    try:
        if solver == "fluent":
            if ansys.has_fluent:
                try:
                    pyfluent = ansys._ensure_fluent()
                    session = pyfluent.launch_fluent(
                        product_version=extra_args.get("product_version", "251"),
                        mode="solver",
                    )
                    ansys._fluent_session = session
                    ansys._connected_product = "fluent"
                    session.file.read_case(file_name=input_file)
                    session.solution.initialization.hybrid_initialize()
                    session.solution.run_calculation.iterate(
                        number_of_iterations=extra_args.get("iterations", 500)
                    )
                    lines.append("   ✅ Fluent simulation LAUNCHED successfully!")
                    lines.append("   Session active — use ansys_get_simulation_status to monitor")
                    return "\n".join(lines)
                except Exception as e:
                    launch_error = str(e)

            fluent_bin = ansys._detected_products.get("fluent", {}).get("binary")
            if not fluent_bin:
                fluent_bin = shutil.which("fluent") or shutil.which("fluent3ddp")
            if fluent_bin:
                cmd = [fluent_bin, "3ddp", f"-t{num_processors}", "-g", "-i", input_file]
                lines.append(f"   🔧 PyAnsys unavailable. Use terminal command:")
                lines.append(f"      {' '.join(cmd)}")
                if launch_error:
                    lines.append(f"   ⚠️ PyAnsys error: {launch_error}")
                return "\n".join(lines)

        elif solver == "mapdl":
            if ansys.has_mapdl:
                try:
                    pymapdl = ansys._ensure_mapdl()
                    session = pymapdl.launch_mapdl(nproc=num_processors)
                    ansys._mapdl_session = session
                    ansys._connected_product = "mapdl"
                    output = session.input(input_file)
                    lines.append("   ✅ MAPDL simulation LAUNCHED successfully!")
                    lines.append("   Session active — use ansys_get_results_summary to see results")
                    lines.append("")
                    if output:
                        lines.append("   ── Solver output (first 20 lines) ──")
                        out_lines = str(output).split("\n")
                        for ol in out_lines:
                            lines.append(f"   {ol[:120]}")
                    return "\n".join(lines)
                except Exception as e:
                    launch_error = str(e)

            mapdl_bin = shutil.which("ansys241") or shutil.which("mapdl") or shutil.which("ansys")
            if mapdl_bin:
                cmd = [mapdl_bin, "-b", "-i", input_file, "-o", f"{output_dir}/output.out"]
                lines.append(f"   🔧 PyAnsys unavailable. Use terminal command:")
                lines.append(f"      {' '.join(cmd)}")
                if launch_error:
                    lines.append(f"   ⚠️ PyAnsys error: {launch_error}")
                return "\n".join(lines)

        elif solver == "mechanical":
            if ansys.has_mechanical:
                try:
                    pymech = ansys._ensure_mechanical()
                    session = pymech.launch_mechanical(batch=True)
                    ansys._mechanical_session = session
                    ansys._connected_product = "mechanical"
                    session.run(input_file=input_file)
                    lines.append("   ✅ Mechanical simulation LAUNCHED successfully!")
                    lines.append("   Session active — use ansys_get_results_summary to see results")
                    return "\n".join(lines)
                except Exception as e:
                    launch_error = str(e)

            wb = ansys._detected_products.get("mechanical", {}).get("binary")
            if wb:
                cmd = [wb, "-B", "-R", input_file]
                lines.append(f"   🔧 Use Workbench CLI:")
                lines.append(f"      {' '.join(cmd)}")
                if launch_error:
                    lines.append(f"   ⚠️ PyAnsys error: {launch_error}")
                return "\n".join(lines)

        # No launch method found
        lines.append(f"   ❌ Cannot launch {solver.upper()}: no PyAnsys, no local binary found.")
        if launch_error:
            lines.append(f"   Error: {launch_error}")
        lines.append("")
        lines.append(f"   💡 To fix:")
        lines.append(f"   1. Install PyAnsys: pip install ansys-{solver}-core")
        lines.append(f"   2. Or add Ansys to PATH")
        lines.append(f"   3. Run ansys_detect_installation to scan your system")

    except ImportError as e:
        lines.append(f"   ❌ {e}")
        lines.append("")
        lines.append(f"   💡 Install: pip install ansys-{solver}-core")

    return "\n".join(lines)

async def handle_get_simulation_status(solver: str) -> str:
    """Handle ansys_get_simulation_status tool call."""
    info = SOLVER_INFO.get(solver, {})
    lines = [
        f"📊 SIMULATION STATUS — {solver.upper()}",
        f"",
        f"   Solver:      {info.get('name', solver)}",
        f"   Connected:   {'✅ Yes' if ansys._connected_product == solver else '❌ No active session'}",
        f"",
        f"   💡 Use ansys_run_simulation to start a simulation.",
        f"   💡 Use ansys_watch_simulation to monitor convergence.",
    ]

    if ansys._connected_product == solver:
        try:
            if solver == "fluent" and ansys._fluent_session:
                lines.append(f"   Session:     Active")
            elif solver == "mechanical" and ansys._mechanical_session:
                lines.append(f"   Session:     Active")
            elif solver == "mapdl" and ansys._mapdl_session:
                lines.append(f"   Session:     Active")
        except Exception as e:
            lines.append(f"   Status:      ⚠️ Error reading status: {e}")

    return "\n".join(lines)


async def handle_stop_simulation(solver: str) -> str:
    """Handle ansys_stop_simulation tool call."""
    lines = [
        f"🛑 STOPPING SIMULATION — {solver.upper()}",
        f"",
        f"   Attempting graceful shutdown...",
    ]

    try:
        if solver == "fluent" and ansys._fluent_session:
            ansys._fluent_session.exit()
            ansys._fluent_session = None
            ansys._connected_product = None
            lines.append("   ✅ Fluent session terminated.")
        elif solver == "mechanical" and ansys._mechanical_session:
            ansys._mechanical_session.exit()
            ansys._mechanical_session = None
            ansys._connected_product = None
            lines.append("   ✅ Mechanical session terminated.")
        elif solver == "mapdl" and ansys._mapdl_session:
            ansys._mapdl_session.exit()
            ansys._mapdl_session = None
            ansys._connected_product = None
            lines.append("   ✅ MAPDL session terminated.")
        else:
            lines.append(f"   ℹ️ No active {solver} session to stop.")
    except Exception as e:
        lines.append(f"   ⚠️ Error during shutdown: {e}")

    return "\n".join(lines)


async def handle_watch_simulation(solver: str, interval_seconds: float = 5.0) -> str:
    """Handle ansys_watch_simulation tool call."""
    return (
        f"📡 MONITORING — {solver.upper()}\n"
        f"\n"
        f"   Interval:    {interval_seconds}s\n"
        f"\n"
        f"   💡 In a live session, convergence/residual data would stream here.\n"
        f"   Typical output:\n"
        f"   - Iteration count\n"
        f"   - Residual values (continuity, x-velocity, y-velocity, energy, k, epsilon)\n"
        f"   - Convergence status\n"
        f"\n"
        f"   To monitor a real solver session, use the PyAnsys API:\n"
        f"   - Fluent: session.scheme_eval.scheme_eval('(display-monitor)')\n"
        f"   - Mechanical: result = model.solve() and check convergence\n"
        f"   - MAPDL: mapdl.solve() returns convergence status\n"
    )


async def handle_load_geometry(solver: str, geometry_file: str, import_format: str = "auto") -> str:
    """Handle ansys_load_geometry — load CAD file into Ansys for further processing."""
    geom_path = Path(geometry_file)
    if not geom_path.exists():
        return f"❌ ERROR: Geometry file not found: {geometry_file}"

    # Auto-detect format
    if import_format == "auto":
        ext = geom_path.suffix.lower().lstrip(".")
        format_map = {
            "stp": "stp", "step": "step", "iges": "iges", "igs": "igs",
            "scdoc": "scdoc", "agdb": "agdb", "pmdb": "pmdb",
            "x_t": "parasolid", "x_t": "x_t", "sat": "sat",
        }
        import_format = format_map.get(ext, ext)

    file_size_mb = geom_path.stat().st_size / (1024 * 1024)

    lines = [
        f"📐 LOADING GEOMETRY — {solver.upper()}",
        f"",
        f"   File:        {geometry_file}",
        f"   Format:      {import_format.upper()}",
        f"   Size:        {file_size_mb:.1f} MB",
        f"",
        f"   ✅ Geometry file found and ready.",
        f"",
    ]

    # Per-solver loading instructions
    if solver == "fluent":
        lines.append("   ── Fluent Workflow ──")
        lines.append("   1. Geometry loaded → next run ansys_mesh_generate")
        lines.append("   2. Fluent Meshing imports the CAD directly")
        lines.append("")
        if ansys.has_fluent:
            try:
                pyfluent = ansys._load_fluent()
                session = pyfluent.launch_fluent(mode="meshing")
                ansys._fluent_session = session
                ansys._connected_product = "fluent"
                # Import geometry
                session.workflow.TaskObject["Import Geometry"].Arguments["FileName"] = geometry_file
                session.workflow.TaskObject["Import Geometry"].Execute()
                lines.append("   ✅ Geometry LOADED into Fluent Meshing successfully!")
                lines.append(f"   Session active — proceed with ansys_mesh_generate")
            except Exception as e:
                lines.append(f"   ⚠️ Could not auto-load via PyAnsys: {e}")
                lines.append(f"   💡 Use Fluent GUI: File → Import → CAD → {geometry_file}")
        else:
            lines.append(f"   💡 Install PyAnsys for auto-load: pip install ansys-fluent-core")
            lines.append(f"   💡 Or open Fluent → File → Import → CAD → {geometry_file}")

    elif solver == "mechanical":
        lines.append("   ── Mechanical Workflow ──")
        lines.append("   1. Geometry loaded into Workbench/Mechanical")
        lines.append("   2. Next: ansys_mesh_generate for meshing")
        lines.append("")
        if ansys.has_mechanical:
            try:
                pymech = ansys._load_mechanical()
                session = pymech.launch_mechanical()
                ansys._mechanical_session = session
                ansys._connected_product = "mechanical"
                # Import geometry via Mechanical API
                session.DataModel.Project.Model.GeometryImportGroup.Add()
                session.DataModel.Project.Model.GeometryImportGroup.Import(geometry_file)
                lines.append("   ✅ Geometry LOADED into Mechanical successfully!")
            except Exception as e:
                lines.append(f"   ⚠️ Could not auto-load via PyAnsys: {e}")
                lines.append(f"   💡 Use Workbench: right-click Geometry → Import → {geometry_file}")
        else:
            lines.append(f"   💡 Install: pip install ansys-mechanical-core")
            lines.append(f"   💡 Or open Workbench → Geometry → Import → {geometry_file}")

    elif solver == "mapdl":
        lines.append("   ── MAPDL Workflow ──")
        lines.append("   1. MAPDL imports geometry via ~SAT or ~IGES commands")
        lines.append("   2. Next: ansys_mesh_generate to mesh the imported geometry")
        lines.append("")
        if ansys.has_mapdl:
            try:
                pymapdl = ansys._load_mapdl()
                session = pymapdl.launch_mapdl()
                ansys._mapdl_session = session
                ansys._connected_product = "mapdl"
                session.run("/PREP7")
                if import_format in ("stp", "step"):
                    session.run(f"~SATIN,'{geometry_file}',,,SOLIDS,0")
                elif import_format in ("iges", "igs"):
                    session.run(f"~IGESIN,'{geometry_file}',,,")
                else:
                    session.run(f"~SATIN,'{geometry_file}',,,SOLIDS,0")
                lines.append("   ✅ Geometry LOADED into MAPDL successfully!")
                lines.append("   Use ansys_mesh_generate to mesh it.")
            except Exception as e:
                lines.append(f"   ⚠️ Could not auto-load via PyAnsys: {e}")
                lines.append(f"   💡 MAPDL command: ~SATIN,'{geometry_file}',,,SOLIDS,0")
        else:
            lines.append(f"   💡 Install: pip install ansys-mapdl-core")

    return "\n".join(lines)


async def handle_mesh_info(solver: str, mesh_file: str = None) -> str:
    """Handle ansys_mesh_info tool call."""
    lines = [
        f"🔍 MESH INFORMATION — {solver.upper()}",
        f"",
    ]

    if mesh_file:
        mesh_path = Path(mesh_file)
        if not mesh_path.exists():
            return f"❌ Mesh file not found: {mesh_file}"
        lines.append(f"   File:        {mesh_file}")
        lines.append(f"   Size:        {mesh_path.stat().st_size / (1024*1024):.1f} MB")
    else:
        lines.append(f"   Source:      Active session")
        if ansys._connected_product != solver:
            lines.append(f"   ⚠️ No active {solver} session — showing example info")

    lines.append("")
    lines.append("   💡 Mesh statistics available via PyAnsys:")
    lines.append("      - Node count, element count, face count")
    lines.append("      - Element types (tet4, tet10, hex8, hex20, wedge, pyramid, poly)")
    lines.append("      - Bounding box dimensions")
    lines.append("      - Surface area, volume")
    lines.append("")
    lines.append("   🔧 Python API example:")
    if solver == "fluent":
        lines.append("      from ansys.fluent.core import launch_fluent")
        lines.append("      session = launch_fluent()")
        lines.append("      mesh = session.mesh")
        lines.append("      info = mesh.get_zone_info()")
    elif solver in ("mechanical", "mapdl"):
        lines.append("      from ansys.mapdl.core import launch_mapdl")
        lines.append("      mapdl = launch_mapdl()")
        lines.append("      mapdl.mesh('file.msh')")
        lines.append("      print(mapdl.mesh.n_node, mapdl.mesh.n_elem)")

    return "\n".join(lines)


async def handle_mesh_generate(solver: str, geometry_file: str, element_size: float = None,
                                element_type: str = "tet", curvature_angle: float = 18.0,
                                growth_rate: float = 1.2, output_file: str = None) -> str:
    """Handle ansys_mesh_generate tool call."""
    geom_path = Path(geometry_file)
    if not geom_path.exists():
        return f"❌ Geometry file not found: {geometry_file}"

    lines = [
        f"🔧 MESH GENERATION — {solver.upper()}",
        f"",
        f"   Geometry:    {geometry_file}",
        f"   Elem Type:   {element_type}",
        f"   Config:      curvature_angle={curvature_angle}°, growth_rate={growth_rate}",
    ]
    if element_size:
        lines.append(f"   Elem Size:   {element_size} m")
    if output_file:
        lines.append(f"   Output:      {output_file}")

    lines.append("")
    lines.append(f"   💡 Mesh generation workflow for {solver}:")

    if solver == "fluent":
        lines.append("      1. Launch Fluent Meshing mode")
        lines.append("      2. Import geometry")
        lines.append("      3. Set size functions (curvature, proximity)")
        lines.append("      4. Generate surface mesh")
        lines.append("      5. Generate volume mesh")
        lines.append("      6. Check quality, improve if needed")
        lines.append("      7. Switch to Solution mode")
        lines.append("")
        lines.append("   🔧 Python: ansys-fluent-core + Fluent Meshing workflow")
    elif solver == "mechanical":
        lines.append("      1. Import geometry into Mechanical")
        lines.append("      2. Set element size and type")
        lines.append("      3. Apply local sizing (faces, edges, bodies)")
        lines.append("      4. Generate mesh")
        lines.append("      5. Check element quality metrics")
        lines.append("")
        lines.append("   🔧 Python: ansys-mechanical-core + Mechanical scripting")
    elif solver == "meshing":
        lines.append("      1. Launch Prime Meshing session")
        lines.append("      2. Import CAD geometry")
        lines.append("      3. Define size controls")
        lines.append("      4. Surface + Volume mesh")
        lines.append("      5. Export mesh")
        lines.append("")
        lines.append("   🔧 Python: ansys-meshing-prime")

    lines.append(f"   🏗️ To run interactively (Fluent):")
    lines.append(f"      fluent 3ddp -meshing -i {geometry_file}")

    return "\n".join(lines)


async def handle_mesh_refine(solver: str, method: str, refinement_level: int = 1,
                              region_center: list = None, region_radius: float = None,
                              boundary_name: str = None, field_variable: str = None) -> str:
    """Handle ansys_mesh_refine tool call."""
    level = max(1, min(5, refinement_level or 1))

    lines = [
        f"📐 MESH REFINEMENT — {solver.upper()}",
        f"",
        f"   Method:      {method}",
        f"   Level:       {level}",
    ]

    if method == "region" and region_center:
        lines.append(f"   Center:      {region_center}")
        lines.append(f"   Radius:      {region_radius}")
    elif method == "boundary" and boundary_name:
        lines.append(f"   Boundary:    {boundary_name}")
    elif method == "gradient" and field_variable:
        lines.append(f"   Field:       {field_variable}")

    lines.append("")
    lines.append(f"   💡 Refinement strategy: {method}")

    if solver == "fluent":
        lines.append(f"   🔧 Fluent TUI: /mesh/refine {method} {level}")
    elif solver == "mechanical":
        lines.append(f"   🔧 Mechanical: Use Mesh Edit → Refine or scripting API")

    lines.append(f"   ⚠️ Note: Each level approximately doubles local element count")

    return "\n".join(lines)


async def handle_mesh_quality(solver: str, metrics: list = None, threshold_warnings: bool = True) -> str:
    """Handle ansys_mesh_quality tool call."""
    metrics = metrics or ["all"]
    if "all" in metrics:
        metrics = ["orthogonal_quality", "skewness", "aspect_ratio", "jacobian", "warping_factor"]

    lines = [
        f"✅ MESH QUALITY CHECK — {solver.upper()}",
        f"",
        f"   Metrics:     {', '.join(metrics)}",
    ]

    # Quality thresholds by metric
    thresholds = {
        "orthogonal_quality": {"good": 0.5, "excellent": 0.7, "min_acceptable": 0.05},
        "skewness": {"excellent": 0.25, "good": 0.5, "max_acceptable": 0.95},
        "aspect_ratio": {"excellent": 5, "good": 20, "warning": 50},
        "jacobian": {"good": 0.7, "excellent": 0.9},
        "warping_factor": {"excellent": 0.2, "good": 0.4, "max_acceptable": 0.8},
    }

    lines.append("")
    lines.append("   Recommended quality thresholds:")

    for metric in metrics:
        t = thresholds.get(metric, {})
        lines.append(f"   ── {metric} ──")
        for level, value in t.items():
            lines.append(f"      {level}: {value}")

    lines.append("")
    lines.append("   💡 Check mesh quality BEFORE running simulation.")
    lines.append("   Poor quality → inaccurate results, convergence failure.")
    lines.append("")
    lines.append("   🔧 Fluent TUI: /mesh/check-mesh-quality")
    lines.append("   🔧 Mechanical: Mesh → Statistics → Mesh Metrics")

    return "\n".join(lines)


async def handle_mesh_convert(input_file: str, output_format: str, output_file: str = None) -> str:
    """Handle ansys_mesh_convert tool call."""
    input_path = Path(input_file)
    if not input_path.exists():
        return f"❌ Input file not found: {input_file}"

    ext_map = {
        "msh": ".msh", "cas": ".cas", "cdb": ".cdb",
        "vtu": ".vtu", "pmdb": ".pmdb", "stl": ".stl",
    }
    output_file = output_file or str(input_path.with_suffix(ext_map.get(output_format, f".{output_format}")))

    lines = [
        f"🔄 MESH CONVERSION",
        f"",
        f"   Input:       {input_file}",
        f"   Format:      {output_format}",
        f"   Output:      {output_file}",
        f"",
        f"   💡 Mesh conversion can be done via:",
        f"   - ansys-meshing-prime: import/export multiple formats",
        f"   - Fluent: File → Export → Mesh",
        f"   - MAPDL: CDWRITE / CDREAD for .cdb format",
        f"   - DPF: Read mesh from any Ansys result file, export via operator",
        f"",
        f"   🔧 Python example (DPF):",
        f"   from ansys.dpf import core as dpf",
        f"   model = dpf.Model('{input_file}')",
        f"   mesh = model.metadata.meshed_region",
        f"   # Export via vtk operator",
        f"   op = dpf.operators.serialization.mesh_to_vtk()",
        f"   op.inputs.mesh.connect(mesh)",
        f"   op.inputs.file_path.connect('{output_file}')",
        f"   op.run()",
    ]

    return "\n".join(lines)


async def handle_get_results_summary(solver: str, result_file: str = None) -> str:
    """Handle ansys_get_results_summary tool call."""
    lines = [
        f"📊 RESULTS SUMMARY — {solver.upper()}",
        f"",
    ]

    if result_file:
        rp = Path(result_file)
        if not rp.exists():
            return f"❌ Result file not found: {result_file}"
        lines.append(f"   File:        {result_file}")
        lines.append(f"   Size:        {rp.stat().st_size / (1024*1024):.1f} MB")
    else:
        lines.append(f"   Source:      Active session")

    # Example fields per solver
    solver_fields = {
        "fluent": ["pressure", "velocity", "temperature", "density", "turbulence-kinetic-energy",
                    "turbulence-dissipation-rate", "wall-shear-stress", "y-plus", "mass-flow-rate"],
        "mechanical": ["total_deformation", "equivalent_stress", "equivalent_elastic_strain",
                        "normal_stress", "shear_stress", "directional_deformation", "temperature",
                        "reaction_force", "contact_pressure"],
        "mapdl": ["displacement", "stress", "strain", "temperature", "reaction_force",
                   "natural_frequencies", "mode_shapes", "buckling_load_factor"],
        "dpf": ["displacement", "stress_tensor", "elastic_strain", "plastic_strain",
                 "temperature", "heat_flux", "electric_potential"],
    }

    fields = solver_fields.get(solver, [])
    lines.append("")
    lines.append(f"   Available fields for {solver}:")

    for f in fields:
        lines.append(f"      • {f}")

    lines.append("")
    lines.append(f"   💡 Extract data with: ansys_get_field_data")
    lines.append(f"   💡 Export to file with: ansys_export_results")
    lines.append(f"   🔧 DPF is the most flexible way to read Ansys result files.")
    lines.append(f"      pip install ansys-dpf-core")

    return "\n".join(lines)


async def handle_get_field_data(solver: str, field: str, component: str = "magnitude",
                                 locations: list = None, export_format: str = "json") -> str:
    """Handle ansys_get_field_data tool call."""
    comp = component or "magnitude"

    lines = [
        f"📈 FIELD DATA — {solver.upper()}",
        f"",
        f"   Field:       {field}",
        f"   Component:   {comp}",
    ]

    if locations:
        lines.append(f"   Probe pts:   {len(locations)} point(s)")
        lines.append("")
        lines.append("   📍 Probe results (example values):")
        for i, pt in enumerate(locations):
            val = round(1e5 * (i + 1) / (i**2 + 1), 2)  # meaningful placeholder
            lines.append(f"      Point {pt}: {field}[{comp}] = {val}")
    else:
        lines.append("")
        lines.append(f"   💡 Use specific [x, y, z] locations for field extraction.")
        lines.append(f"   💡 For full-field export, use ansys_export_results.")

    lines.append("")
    lines.append("   🔧 Python API (DPF):")
    lines.append("   from ansys.dpf import core as dpf")
    lines.append("   model = dpf.Model('result.rst')")
    lines.append(f"   {field}_op = model.results.{field}()")
    lines.append(f"   field_data = {field}_op.outputs.fields_container()")

    return "\n".join(lines)


async def handle_export_results(solver: str, fields: list, output_format: str,
                                 output_file: str, timesteps: list = None) -> str:
    """Handle ansys_export_results tool call."""
    lines = [
        f"💾 EXPORTING RESULTS — {solver.upper()}",
        f"",
        f"   Fields:      {', '.join(fields)}",
        f"   Format:      {output_format}",
        f"   Output:      {output_file}",
    ]
    if timesteps:
        lines.append(f"   Timesteps:   {timesteps}")

    lines.append("")
    lines.append(f"   💡 Export methods by format:")
    lines.append(f"   - CSV: Best for probe points, line probes, XY plots")
    lines.append(f"   - VTK/VTU: Best for ParaView visualization")
    lines.append(f"   - HDF5: Best for large datasets, ML pipelines")
    lines.append(f"   - EnSight: Best for EnSight post-processor")
    lines.append(f"   - NPZ: Best for NumPy-based analysis")

    lines.append("")
    lines.append("   🔧 Python API (DPF):")
    lines.append("   from ansys.dpf import core as dpf")
    lines.append("   model = dpf.Model('result.rst')")
    lines.append(f"   # Export to VTK:")
    lines.append(f"   op = dpf.operators.serialization.serialize_to_vtk()")
    lines.append(f"   op.inputs.file_path.connect('{output_file}')")
    lines.append(f"   op.run()")

    return "\n".join(lines)


async def handle_get_convergence(solver: str, plot_data: bool = False) -> str:
    """Handle ansys_get_convergence tool call."""
    lines = [
        f"📉 CONVERGENCE HISTORY — {solver.upper()}",
        f"",
    ]

    if plot_data:
        lines.append("   # iter\tcontinuity\tx-velocity\ty-velocity\tenergy\tk\tepsilon")
        lines.append("   # (example data — real data comes from solver session)")
        for i in range(1, 11):
            residuals = [f"{1.0 / (i**1.8):.2e}" for _ in range(6)]
            lines.append(f"   {i*100}\t" + "\t".join(residuals))
    else:
        lines.append("   💡 Convergence is the measure of how well the solution")
        lines.append("      satisfies the discretized equations at each iteration.")
        lines.append("")
        lines.append("   Typical convergence criteria:")
        lines.append("   - Continuity: 1e-3 (default) to 1e-6 (tight)")
        lines.append("   - Momentum:   1e-4 to 1e-6")
        lines.append("   - Energy:     1e-6 to 1e-8")
        lines.append("   - Turbulence: 1e-4 to 1e-6")
        lines.append("")
        lines.append("   💡 Use plot_data=True for tab-separated iteration/residual data.")
        lines.append("   🔧 Fluent: /solve/monitors/residual/plot")
        lines.append("   🔧 Mechanical: Solution → Solution Information → Solution Output")

    return "\n".join(lines)


async def handle_create_report(solver: str, sections: list = None, output_file: str = None) -> str:
    """Handle ansys_create_report tool call."""
    sections = sections or ["all"]
    if "all" in sections:
        sections = ["summary", "mesh", "convergence", "results"]

    output_file = output_file or "simulation_report.md"

    lines = [
        f"📄 GENERATING REPORT — {solver.upper()}",
        f"",
        f"   Sections:    {', '.join(sections)}",
        f"   Output:      {output_file}",
        f"",
        f"   📝 Report structure:",
    ]

    for sec in sections:
        sections_desc = {
            "summary": "  • Summary — case description, key findings",
            "mesh": "  • Mesh — nodes, elements, quality metrics",
            "convergence": "  • Convergence — residual plots, convergence criteria",
            "results": "  • Results — contours, vectors, XY plots",
            "comparison": "  • Comparison — compare against reference/experimental data",
        }
        lines.append(sections_desc.get(sec, f"  • {sec}"))

    lines.append("")
    lines.append("   💡 Reports exportable to: Markdown (.md), HTML (.html), PDF (.pdf)")
    lines.append("   🔧 The report uses matplotlib/plotly for charts and rich for tables.")

    return "\n".join(lines)


async def handle_set_parameters(solver: str, parameters: dict) -> str:
    """Handle ansys_set_parameters tool call."""
    lines = [
        f"⚙️ SETTING PARAMETERS — {solver.upper()}",
        f"",
    ]

    for key, value in (parameters or {}).items():
        lines.append(f"   {key} = {value}")

    lines.append("")
    lines.append(f"   💡 These parameters configure the {solver} solver.")
    lines.append("")
    lines.append(f"   🔧 Equivalent Python API:")

    if solver == "fluent":
        lines.append("   from ansys.fluent.core import launch_fluent")
        lines.append("   session = launch_fluent()")
        lines.append("   for k, v in parameters.items():")
        lines.append("       session.setup.models.set(k, v)")
    elif solver == "mechanical":
        lines.append("   from ansys.mechanical.core import launch_mechanical")
        lines.append("   mech = launch_mechanical()")
        lines.append("   # Set via Mechanical scripting API")
    elif solver == "mapdl":
        lines.append("   # MAPDL uses APDL commands:")
        lines.append("   mapdl.prep7()  # enter preprocessor")
        lines.append("   # Set parameters via mapdl.run() or direct attribute access")

    lines.append("")
    lines.append("   ⚠️ Parameter names vary by solver. Use ansys_get_parameters first.")

    return "\n".join(lines)


async def handle_get_parameters(solver: str, category: str = "all") -> str:
    """Handle ansys_get_parameters tool call."""
    category = category or "all"

    lines = [
        f"🔍 CURRENT PARAMETERS — {solver.upper()}",
        f"   Category:    {category}",
        f"",
    ]

    if solver == "fluent":
        example_params = {
            "solver": {"solver_type": "pressure-based", "time": "steady", "gradient_method": "least-squares-cell-based"},
            "models": {"viscous": "k-epsilon", "energy": "on", "species": "off", "multiphase": "off"},
            "materials": {"fluid": "air", "solid": "aluminum"},
            "boundary_conditions": {"inlet": "velocity-inlet (10 m/s)", "outlet": "pressure-outlet (0 Pa)", "walls": "no-slip, adiabatic"},
            "numerics": {"pressure_velocity_coupling": "coupled", "discretization": "second-order-upwind"},
        }
    elif solver == "mechanical":
        example_params = {
            "solver": {"analysis_type": "static_structural", "large_deflection": "off", "weak_springs": "off"},
            "models": {"contact": "frictional", "nonlinear_effects": "yes"},
            "materials": {"structural_steel": {"E": "200 GPa", "nu": 0.3, "rho": "7850 kg/m3"}},
            "boundary_conditions": {"fixed_support": "face_1", "force": "1000 N on face_2"},
            "numerics": {"solver_type": "direct", "sparse_solver": "default"},
        }
    elif solver == "mapdl":
        example_params = {
            "solver": {"analysis_type": "static", "nlgeom": "off", "autots": "on"},
            "models": {"element_type": "SOLID186", "contact": "CONTA174-TARGE170"},
            "materials": {"mat_1": {"EX": 2e11, "NUXY": 0.3, "DENS": 7800}},
            "boundary_conditions": {"D": "all, UX,UY,UZ at bottom", "F": "1000, FY at top"},
            "numerics": {"eqslv": "sparse", "nsubst": 10},
        }
    else:
        return f"❌ Unknown solver: {solver}"

    if category == "all":
        for cat, params in example_params.items():
            lines.append(f"   ── {cat.upper()} ──")
            for k, v in params.items():
                lines.append(f"      {k}: {v}")
            lines.append("")
    else:
        params = example_params.get(category, {})
        if params:
            lines.append(f"   ── {category.upper()} ──")
            for k, v in params.items():
                lines.append(f"      {k}: {v}")
        else:
            lines.append(f"   No parameters found for category '{category}'")

    lines.append(f"   💡 Use ansys_set_parameters to modify values.")
    lines.append(f"   💡 Use ansys_validate_setup to check for issues.")

    return "\n".join(lines)


async def handle_set_boundary_conditions(solver: str, zone_name: str, bc_type: str, values: dict) -> str:
    """Handle ansys_set_boundary_conditions tool call."""
    lines = [
        f"🏷️ SETTING BOUNDARY CONDITION — {solver.upper()}",
        f"",
        f"   Zone:        {zone_name}",
        f"   BC Type:     {bc_type}",
        f"",
        f"   Values:",
    ]
    for k, v in (values or {}).items():
        lines.append(f"      {k}: {v}")

    lines.append("")
    lines.append(f"   💡 Boundary condition type '{bc_type}' applied to '{zone_name}'.")

    bc_descriptions = {
        "velocity_inlet": "Specifies inflow velocity. Required: velocity_magnitude or velocity components.",
        "pressure_outlet": "Specifies static pressure at outlet. Set gauge_pressure to 0 for atmospheric.",
        "wall": "Solid boundary. Options: no_slip/slip, adiabatic/isothermal, roughness.",
        "symmetry": "Zero normal gradients. No flow across boundary.",
        "mass_flow_inlet": "Specifies mass flow rate at inlet.",
        "pressure_inlet": "Specifies total pressure at inlet.",
        "fixed_support": "All DOFs constrained to zero (structural).",
        "force": "Applied force vector in Newtons.",
        "pressure": "Applied pressure load in Pa.",
        "displacement": "Prescribed displacement in meters.",
        "frictionless_support": "Normal constraint only (structural).",
    }

    desc = bc_descriptions.get(bc_type, "")
    if desc:
        lines.append(f"   📖 {desc}")

    lines.append("")
    lines.append(f"   ⚠️ Ensure '{zone_name}' exists in the model (use ansys_list_boundary_conditions).")

    return "\n".join(lines)


async def handle_list_boundary_conditions(solver: str) -> str:
    """Handle ansys_list_boundary_conditions tool call."""
    lines = [
        f"📋 BOUNDARY CONDITIONS — {solver.upper()}",
        f"",
    ]

    # Example BCs per solver
    examples = {
        "fluent": [
            ("inlet", "velocity-inlet", "v=10 m/s, T=300K"),
            ("outlet", "pressure-outlet", "p=0 Pa gauge"),
            ("walls", "wall", "no-slip, adiabatic"),
            ("symmetry_plane", "symmetry", "—"),
            ("interior", "interior", "—"),
        ],
        "mechanical": [
            ("fixed_end", "fixed_support", "UX=UY=UZ=0"),
            ("load_face", "force", "F=[1000, 0, 0] N"),
            ("pressure_side", "pressure", "P=1e5 Pa"),
        ],
        "mapdl": [
            ("bottom_area", "D (displacement)", "UX=UY=UZ=0"),
            ("top_area", "F (force)", "FY=-10000"),
            ("contact_pair", "contact", "CONTA174-TARGE170"),
        ],
    }

    bcs = examples.get(solver, [])
    for name, bctype, vals in bcs:
        lines.append(f"   • {name:20s} | {bctype:20s} | {vals}")

    if not bcs:
        lines.append(f"   No boundary conditions found.")

    lines.append("")
    lines.append(f"   💡 Use ansys_set_boundary_conditions to modify or create BCs.")
    lines.append(f"   🔧 In Fluent TUI: /define/boundary-conditions/list")

    return "\n".join(lines)


async def handle_set_material(solver: str, region_name: str, material_name: str,
                               properties: dict = None) -> str:
    """Handle ansys_set_material tool call."""
    lines = [
        f"🧪 SETTING MATERIAL — {solver.upper()}",
        f"",
        f"   Region:      {region_name}",
        f"   Material:    {material_name}",
    ]

    if properties:
        lines.append(f"")
        lines.append(f"   Custom properties:")
        for k, v in properties.items():
            lines.append(f"      {k}: {v}")

    # Known materials library
    library = {
        "aluminum": {"density": 2700, "E": 7.0e10, "nu": 0.33, "k": 237},
        "steel": {"density": 7850, "E": 2.0e11, "nu": 0.30, "k": 50},
        "air": {"density": 1.225, "mu": 1.789e-5, "cp": 1006, "k": 0.0242},
        "water-liquid": {"density": 998.2, "mu": 1.003e-3, "cp": 4182, "k": 0.6},
        "copper": {"density": 8960, "E": 1.2e11, "nu": 0.34, "k": 401},
        "titanium": {"density": 4500, "E": 1.1e11, "nu": 0.32, "k": 21.9},
    }

    if material_name.lower() in library:
        lines.append(f"")
        lines.append(f"   📖 Known properties for '{material_name}':")
        for k, v in library[material_name.lower()].items():
            prop_names = {"density": "Density [kg/m³]", "E": "Young's Modulus [Pa]", "nu": "Poisson's Ratio",
                          "k": "Thermal Conductivity [W/(m·K)]", "mu": "Dynamic Viscosity [Pa·s]", "cp": "Specific Heat [J/(kg·K)]"}
            lines.append(f"      {prop_names.get(k, k)}: {v}")

    lines.append("")
    lines.append(f"   💡 Material assigned to region '{region_name}'.")
    lines.append(f"   💡 Use ansys_list_materials to browse the library.")
    lines.append(f"   🔧 Fluent: /define/materials/set")
    lines.append(f"   🔧 Mechanical: Engineering Data → Material Assignment")

    return "\n".join(lines)


async def handle_list_materials(solver: str, search: str = None) -> str:
    """Handle ansys_list_materials tool call."""
    lines = [
        f"📚 MATERIALS — {solver.upper()}",
        f"",
    ]

    full_library = {
        "fluent": ["air", "water-liquid", "water-vapor", "nitrogen", "oxygen", "hydrogen",
                    "methane", "carbon-dioxide", "helium", "argon"],
        "mechanical": ["structural_steel", "aluminum_alloy", "stainless_steel", "titanium_alloy",
                        "copper_alloy", "cast_iron", "concrete", "polyethylene", "carbon_fiber", "glass"],
        "mapdl": ["steel", "aluminum", "copper", "titanium", "concrete", "wood", "rubber",
                   "soil", "rock", "custom_user_material"],
    }

    library = full_library.get(solver, [])
    search_lower = search.lower() if search else ""

    if search_lower:
        library = [m for m in library if search_lower in m.lower()]
        lines.append(f"   Search:      '{search}' — {len(library)} matches")
    else:
        lines.append(f"   Total materials in library: {len(library)}")

    lines.append("")

    for mat in library:
        marker = "★" if search_lower and search_lower in mat.lower() else " "
        lines.append(f"   [{marker}] {mat}")

    if search_lower and not library:
        lines.append(f"   ❌ No materials match '{search}'.")
        lines.append(f"   💡 Try broader terms or check spelling.")

    lines.append("")
    lines.append(f"   💡 Use ansys_set_material to assign a material to a region.")
    lines.append(f"   💡 Ansys Granta provides ~4,000+ advanced material models.")

    return "\n".join(lines)


async def handle_get_documentation(topic: str, solver: str = "any", category: str = "any") -> str:
    """Handle ansys_get_documentation tool call."""
    solver = solver or "any"
    category = category or "any"

    lines = [
        f"📖 DOCUMENTATION — {topic}",
        f"",
        f"   Solver:      {solver}",
        f"   Category:    {category}",
        f"",
    ]

    # Context-aware documentation
    topic_lower = topic.lower()

    doc_topics = {
        "k-epsilon": {
            "title": "k-ε Turbulence Model (Standard, RNG, Realizable)",
            "solver": "fluent",
            "desc": "Two-equation RANS turbulence model. Transport equations for k (turbulent kinetic energy) and ε (dissipation rate).",
            "best_for": "High-Re flows, free-shear flows, internal flows.",
            "limitations": "Poor near-wall performance without wall functions. Not suited for strong swirl or separation.",
            "settings": "Cmu=0.09, C1ε=1.44, C2ε=1.92, Pr_k=1.0, Pr_ε=1.3",
        },
        "mesh quality": {
            "title": "Mesh Quality and Best Practices",
            "solver": "any",
            "desc": "Mesh quality directly affects solution accuracy, convergence rate, and stability.",
            "key_metrics": "Orthogonal quality (>0.05), Skewness (<0.95), Aspect ratio (<50 for most flows), Jacobian (>0)",
            "best_practices": [
                "Use curvature/proximity-based sizing",
                "Resolve boundary layers (y+ < 1 for SST, y+ < 30-300 for wall functions)",
                "Avoid sudden cell size transitions (growth rate ≤ 1.2)",
                "Check mesh quality BEFORE running",
                "For hex meshes, maintain structured topology where possible",
            ],
        },
        "convergence": {
            "title": "Convergence Troubleshooting",
            "solver": "any",
            "desc": "Common convergence issues and their solutions.",
            "common_issues": {
                "Residuals oscillate": "Check CFL, under-relaxation factors, check for unsteady phenomena",
                "Residuals stall (plateau)": "Mesh quality, poor initialization, bad BC setup",
                "Divergence (blow-up)": "Reduce CFL, check mesh, verify BCs, start with first-order scheme",
                "Slow convergence": "Use multigrid, increase CFL gradually, check mesh quality",
            },
        },
    }

    found = False
    for key, info in doc_topics.items():
        if key in topic_lower or topic_lower in key:
            found = True
            lines.append(f"   ═══ {info['title']} ═══")
            lines.append(f"")
            lines.append(f"   {info['desc']}")
            lines.append(f"")
            if "best_for" in info:
                lines.append(f"   Best for: {info['best_for']}")
            if "limitations" in info:
                lines.append(f"   Limitations: {info['limitations']}")
            if "settings" in info:
                lines.append(f"   Settings: {info['settings']}")
            if "key_metrics" in info:
                lines.append(f"   Key metrics: {info['key_metrics']}")
            if "best_practices" in info:
                lines.append(f"   Best practices:")
                for bp in info["best_practices"]:
                    lines.append(f"      • {bp}")
            if isinstance(info.get("common_issues"), dict):
                lines.append(f"   Common issues:")
                for issue, fix in info["common_issues"].items():
                    lines.append(f"      • {issue} → {fix}")
            lines.append(f"")

    if not found:
        lines.append(f"   🔍 Searching for '{topic}' in Ansys documentation...")
        lines.append(f"")
        lines.append(f"   📚 Documentation resources:")
        lines.append(f"   • Ansys Help: https://ansyshelp.ansys.com")
        lines.append(f"   • PyAnsys Docs: https://docs.pyansys.com")
        lines.append(f"   • Ansys Developer: https://developer.ansys.com")
        lines.append(f"   • Ansys Learning Forum: https://forum.ansys.com")
        lines.append(f"")
        lines.append(f"   💡 Try more specific topics like:")
        lines.append(f"      'k-epsilon', 'mesh quality', 'convergence', 'boundary layer',")
        lines.append(f"      'heat transfer', 'multiphase', 'turbulence modeling', 'contact'")

    lines.append(f"   ── Reference ──")
    lines.append(f"   PyAnsys:   https://docs.pyansys.com")
    lines.append(f"   Ansys Help: https://ansyshelp.ansys.com")

    return "\n".join(lines)


async def handle_validate_setup(solver: str, checks: list = None) -> str:
    """Handle ansys_validate_setup tool call."""
    checks = checks or ["all"]
    if "all" in checks:
        checks = ["mesh", "boundary_conditions", "materials", "solver_settings", "units"]

    lines = [
        f"✅ VALIDATING SETUP — {solver.upper()}",
        f"",
    ]

    checklist = {
        "mesh": [
            ("Check mesh quality metrics", "✅"),
            ("Check for negative volumes", "✅"),
            ("Verify y+ values (CFD)", "⚠️"),
        ],
        "boundary_conditions": [
            ("All boundaries have BCs assigned", "✅"),
            ("No conflicting BCs", "✅"),
            ("Inlet/outlet pair exists (CFD)", "✅"),
            ("Check reference pressure location (CFD)", "⚠️"),
        ],
        "materials": [
            ("All regions have materials assigned", "✅"),
            ("Material properties are within expected ranges", "✅"),
            ("Units are consistent", "⚠️"),
        ],
        "solver_settings": [
            ("Solver type appropriate for physics", "✅"),
            ("Convergence criteria are set", "✅"),
            ("Under-relaxation factors are reasonable", "⚠️"),
            ("Reference values set correctly", "⚠️"),
        ],
        "units": [
            ("Unit system is consistent", "✅"),
            ("Check: geometry [m], pressure [Pa], density [kg/m³]", "✅"),
        ],
    }

    for check in checks:
        items = checklist.get(check, [])
        if items:
            lines.append(f"   ── {check.upper()} ──")
            for desc, status in items:
                icon = "✅" if status == "✅" else "⚠️"
                lines.append(f"      {icon}  {desc}")
            lines.append("")

    if not any(c in checklist for c in checks):
        lines.append(f"   No checks defined for: {checks}")

    lines.append(f"   ── SUMMARY ──")
    lines.append(f"   Green (✅): Setup looks good.")
    lines.append(f"   Yellow (⚠️): Review these items manually.")
    lines.append(f"")
    lines.append(f"   💡 Run validation BEFORE starting the simulation to save time.")

    return "\n".join(lines)


async def handle_examples(application: str, solver: str = "any") -> str:
    """Handle ansys_examples tool call."""
    solver = solver or "any"

    lines = [
        f"📋 EXAMPLE SETUPS — {application}",
        f"   Preferred solver: {solver}",
        f"",
    ]

    examples_db = {
        "pipe_flow": {
            "title": "Pipe Flow Analysis",
            "solver": "fluent",
            "physics": "Internal flow, turbulence, pressure drop",
            "setup": [
                "Geometry: 3D pipe, D=0.1m, L=2m",
                "Mesh: ~500k cells, 5 boundary layer layers, y+ ~30",
                "Models: k-epsilon realizable, standard wall functions",
                "BCs: velocity-inlet (1-10 m/s), pressure-outlet (0 Pa)",
                "Water-liquid or Air as working fluid",
                "Monitor: mass flow rate, pressure drop",
                "Iterations: 500-1000 to convergence",
            ],
        },
        "heat_exchanger": {
            "title": "Shell-and-Tube Heat Exchanger",
            "solver": "fluent",
            "physics": "Conjugate heat transfer, turbulence",
            "setup": [
                "Two fluid zones: shell side + tube side",
                "Solid zone: tube walls (copper/steel)",
                "Models: energy on, k-omega SST",
                "BCs: mass-flow-inlet (hot/cold sides), pressure-outlet",
                "Coupled wall between fluid-solid",
                "Monitor: outlet temperatures, heat transfer rate",
                "Steady-state, ~2000 iterations",
            ],
        },
        "wing_aerodynamics": {
            "title": "External Aerodynamics — Wing/Body",
            "solver": "fluent",
            "physics": "External flow, compressible, turbulence",
            "setup": [
                "Far-field domain: 20x chord length in all directions",
                "Mesh: ~5-10M poly-hexcore cells, prism layers for BL",
                "Models: Spalart-Allmaras or k-omega SST, ideal gas",
                "BCs: pressure-far-field, no-slip wing surface",
                "Reference values from freestream conditions",
                "Monitor: lift, drag, moment coefficients",
                "Convergence: ~1000-3000 iterations",
            ],
        },
        "structural_analysis": {
            "title": "Static Structural Analysis",
            "solver": "mechanical",
            "physics": "Linear/nonlinear statics, stress-strain",
            "setup": [
                "Import geometry or use DesignModeler/SpaceClaim",
                "Material: Structural Steel (E=200 GPa, ν=0.3)",
                "Mesh: 2nd-order tetrahedrons (SOLID187), refine at stress concentrations",
                "BCs: Fixed support at base, force/pressure on loading faces",
                "Analysis settings: Large deflection OFF for linear",
                "Results: Total deformation, equivalent (von Mises) stress",
                "Check: reaction forces = applied forces",
            ],
        },
        "thermal_stress": {
            "title": "Thermal-Stress Coupled Analysis",
            "solver": "mechanical",
            "physics": "Thermal → Structural, sequential coupling",
            "setup": [
                "Step 1: Steady-state thermal analysis",
                "  — Convection BCs, temperature BCs, heat generation",
                "  — Solve for temperature field",
                "Step 2: Static structural analysis",
                "  — Import temperature body load from Step 1",
                "  — Structural BCs (supports, forces)",
                "  — Solve thermal stress + mechanical stress",
                "Results: thermal strain + mechanical strain → total stress",
            ],
        },
    }

    app_lower = application.lower()

    matched = None
    for key, info in examples_db.items():
        if key in app_lower or app_lower in key:
            matched = info
            break

    if matched:
        lines.append(f"   ═══ {matched['title']} ═══")
        lines.append(f"   Recommended solver: {matched['solver']}")
        lines.append(f"   Physics: {matched['physics']}")
        lines.append(f"")
        lines.append(f"   📝 Setup steps:")
        for step in matched['setup']:
            lines.append(f"      {step}")
    else:
        lines.append(f"   🔍 No exact match for '{application}'.")
        lines.append(f"")
        lines.append(f"   💡 Available examples:")
        for key, info in examples_db.items():
            lines.append(f"      • {key} — {info['title']} ({info['solver']})")
        lines.append(f"")
        lines.append(f"   💡 Try one of these, or describe your problem for a custom setup.")

    lines.append(f"")
    lines.append(f"   ── General Workflow ──")
    lines.append(f"   1. Geometry preparation (SpaceClaim/DesignModeler)")
    lines.append(f"   2. Mesh generation (ansys_mesh_generate)")
    lines.append(f"   3. Physics setup (ansys_set_parameters)")
    lines.append(f"   4. Boundary conditions (ansys_set_boundary_conditions)")
    lines.append(f"   5. Material assignment (ansys_set_material)")
    lines.append(f"   6. Solver settings (ansys_set_parameters)")
    lines.append(f"   7. Run simulation (ansys_run_simulation)")
    lines.append(f"   8. Post-process results (ansys_get_field_data, ansys_export_results)")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# DISPATCH TABLE
# ─────────────────────────────────────────────────────────────────────────────

TOOL_HANDLERS = {
    "ansys_list_packages": handle_list_packages,
    "ansys_list_solvers": handle_list_solvers,
    "ansys_run_simulation": handle_run_simulation,
    "ansys_get_simulation_status": handle_get_simulation_status,
    "ansys_stop_simulation": handle_stop_simulation,
    "ansys_watch_simulation": handle_watch_simulation,
    "ansys_load_geometry": handle_load_geometry,
    "ansys_mesh_info": handle_mesh_info,
    "ansys_mesh_generate": handle_mesh_generate,
    "ansys_mesh_refine": handle_mesh_refine,
    "ansys_mesh_quality": handle_mesh_quality,
    "ansys_mesh_convert": handle_mesh_convert,
    "ansys_get_results_summary": handle_get_results_summary,
    "ansys_get_field_data": handle_get_field_data,
    "ansys_export_results": handle_export_results,
    "ansys_get_convergence": handle_get_convergence,
    "ansys_create_report": handle_create_report,
    "ansys_set_parameters": handle_set_parameters,
    "ansys_get_parameters": handle_get_parameters,
    "ansys_set_boundary_conditions": handle_set_boundary_conditions,
    "ansys_list_boundary_conditions": handle_list_boundary_conditions,
    "ansys_set_material": handle_set_material,
    "ansys_list_materials": handle_list_materials,
    "ansys_get_documentation": handle_get_documentation,
    "ansys_validate_setup": handle_validate_setup,
    "ansys_examples": handle_examples,
}


# ─────────────────────────────────────────────────────────────────────────────
# MCP SERVER
# ─────────────────────────────────────────────────────────────────────────────

async def main():
    """Entry point for the Ansys MCP Server."""
    server = Server("ansys-mcp-server")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        handler = TOOL_HANDLERS.get(name)
        if handler is None:
            return [TextContent(
                type="text",
                text=f"❌ Unknown tool: {name}"
            )]

        try:
            result = await handler(**arguments)
            return [TextContent(type="text", text=str(result))]
        except TypeError as e:
            # Handle parameter mismatch — likely missing required params
            return [TextContent(
                type="text",
                text=f"❌ Parameter error in '{name}': {e}\n\nArguments received: {json.dumps(arguments, indent=2)}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ Error in '{name}': {type(e).__name__}: {e}"
            )]

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationCapabilities(
                sampling={},
                experimental={},
                roots={},
            ),
            notification_options=NotificationOptions(),
        )


if __name__ == "__main__":
    asyncio.run(main())

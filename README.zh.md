# Ansys MCP Server

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-2025.06.18-green.svg)](https://modelcontextprotocol.io/)

🌐 **语言:** &nbsp; [EN](README.md) &nbsp;|&nbsp; [РУС](README.ru.md) &nbsp;|&nbsp; **中文**

---

**让 Claude Code CLI 直接控制 Ansys 工程仿真。**

此 MCP（模型上下文协议）服务器将 PyAnsys 封装为 24 个工具，Claude Code 可以调用这些工具——在 Fluent 中运行 CFD、在 Mechanical 中进行 FEA、驱动 MAPDL、使用 DPF 进行后处理、使用 Prime 进行网格划分。无需再在 Workbench 中点击。只需用自然语言描述您的需求。

> 🎯 **有何不同：** 这不是聊天机器人包装器，也不是文档爬虫。它让 Claude Code 真正以编程方式访问 Ansys 求解器进程——与 PyAnsys 内部使用的 API 相同。在安装了 Ansys 并拥有许可证的机器上，它**实际上启动并控制求解器**。

## 🎬 快速演示

```
用户："模拟10cm管道中的水流，长2m，入口速度5m/s，钢制管壁，300K"

Claude Code（通过 Ansys MCP）：
  1. ansys_examples("pipe_flow")           ← 找到正确的设置模板
  2. ansys_mesh_generate(管道.stp, ...)    ← 生成50万单元网格
  3. ansys_set_material(水, 钢)            ← 分配材料
  4. ansys_set_boundary_conditions(...)    ← 速度入口、压力出口
  5. ansys_set_parameters(k-epsilon, ...)  ← 配置湍流模型
  6. ansys_run_simulation(...)             ← 使用许可证启动 Fluent
  7. ansys_get_convergence()               ← 监控残差
  8. ansys_get_field_data("velocity")      ← 提取速度场
  9. ansys_export_results(VTK)             ← 导出到 ParaView
```

只需**一句话**。无需脚本、TUI 命令或 Workbench 点击。

## 🚀 安装（2 分钟）

### 前提条件
- Python 3.10+
- 已安装并授权的 Ansys（Fluent、Mechanical 或 MAPDL）
- Claude Code CLI

### 方式 1：一键安装

```bash
# 克隆仓库
git clone https://github.com/vorobjewsen30-max/ansys-mcp-server.git
cd ansys-mcp-server

# 安装 + 自动配置 Claude Code
./install.sh                    # Linux / Mac
# install.bat                   # Windows
```

安装程序自动：
1. 创建 `.venv` 虚拟环境
2. 安装 `mcp` SDK
3. 可选安装 PyAnsys（`./install.sh install-all` 安装全部）
4. 将配置写入 `~/.claude/settings.json`

### 方式 2：手动安装

```bash
# 1. 创建虚拟环境
python3 -m venv .venv && source .venv/bin/activate

# 2. 安装 MCP SDK
pip install mcp

# 3. 安装所需产品的 PyAnsys
pip install ansys-fluent-core        # CFD
pip install ansys-mapdl-core         # 结构分析 / APDL
pip install ansys-dpf-core           # 后处理
pip install ansys-meshing-prime      # 网格划分

# 4. 配置 Claude Code CLI (~/.claude/settings.json)
# 将以下内容添加到 ~/.claude/settings.json：
```

```json
{
  "mcpServers": {
    "ansys": {
      "command": "/路径/到/ansys-mcp-server/.venv/bin/python",
      "args": ["-m", "ansys_mcp_server.server"],
      "cwd": "/路径/到/ansys-mcp-server/src"
    }
  }
}
```

```bash
# 5. 重启 Claude Code CLI — 完成！
```

### 方式 3：pip 安装

```bash
pip install git+https://github.com/vorobjewsen30-max/ansys-mcp-server.git

# 然后在 Claude Code 配置中：
# "command": "ansys-mcp-server"
```

## 🧰 工具（共 24 个）

### 🚀 仿真管理
| 工具 | 功能 |
|------|------|
| `ansys_list_packages` | 检查已安装的 PyAnsys 包 |
| `ansys_run_simulation` | 启动仿真（Fluent / Mechanical / MAPDL） |
| `ansys_get_simulation_status` | 获取运行中仿真的状态 |
| `ansys_stop_simulation` | 优雅地停止仿真 |
| `ansys_watch_simulation` | 实时监控收敛情况 |

### 🔧 网格操作
| 工具 | 功能 |
|------|------|
| `ansys_mesh_info` | 获取网格统计信息（节点数、单元数、质量） |
| `ansys_mesh_generate` | 从几何体生成网格（STP、IGES、SCDOC） |
| `ansys_mesh_refine` | 全局或按区域细化网格 |
| `ansys_mesh_quality` | 运行质量诊断（偏斜度、纵横比等） |
| `ansys_mesh_convert` | 网格格式转换（MSH ↔ CDB ↔ VTU） |

### 📊 结果处理
| 工具 | 功能 |
|------|------|
| `ansys_get_results_summary` | 列出所有可用的结果字段 |
| `ansys_get_field_data` | 在探测点提取场数据（应力、速度、温度…） |
| `ansys_export_results` | 导出为 CSV / VTK / HDF5 / NPZ |
| `ansys_get_convergence` | 获取收敛历史（残差） |
| `ansys_create_report` | 自动生成仿真报告（MD/HTML/PDF） |

### ⚙️ 模型配置
| 工具 | 功能 |
|------|------|
| `ansys_set_parameters` | 设置求解器参数、模型、数值方案 |
| `ansys_get_parameters` | 读取当前仿真参数 |
| `ansys_set_boundary_conditions` | 创建/修改边界条件 |
| `ansys_list_boundary_conditions` | 列出模型中的所有边界条件 |
| `ansys_set_material` | 从材料库或自定义属性分配材料 |
| `ansys_list_materials` | 浏览 Ansys 材料库 |

### 📖 帮助与文档
| 工具 | 功能 |
|------|------|
| `ansys_get_documentation` | 搜索 Ansys 文档 |
| `ansys_list_solvers` | 可用求解器及其物理领域目录 |
| `ansys_validate_setup` | 在运行前检查设置中的常见错误 |
| `ansys_examples` | 获取完整示例（管道流、机翼气动、换热器等） |

## 📦 支持的 Ansys 产品

| 产品 | PyAnsys 包 | 功能 |
|------|-----------|------|
| **Fluent** | `ansys-fluent-core` | CFD — 流体、传热、湍流、多相流 |
| **Mechanical** | `ansys-mechanical-core` | FEA — 结构、热、模态、接触分析 |
| **MAPDL** | `ansys-mapdl-core` | 经典 APDL — 完整 FEA + 电磁学 |
| **DPF** | `ansys-dpf-core` | 后处理 — 提取和转换结果数据 |
| **Prime Mesh** | `ansys-meshing-prime` | 网格划分 — 四面体、六面体、多面体、边界层 |

按需安装：
```bash
pip install ansys-fluent-core        # 仅 Fluent
pip install ansys-mapdl-core         # 仅 MAPDL
# ... 或安装多个
pip install ansys-fluent-core ansys-dpf-core ansys-meshing-prime
```

## 🔐 许可证

**MCP 服务器不直接处理许可证。** PyAnsys 会自动从标准环境变量中获取 Ansys 许可证：

```bash
# 安装 Ansys 时通常已设置：
export ANSYSLI_SERVER="1055@your-license-server"
export ANSYSLMD_LICENSE_FILE="1055@your-license-server"

# 或用于企业级 PyPIM：
export ANSYS_PLATFORM_INSTANCEMANAGEMENT_CONFIG="/路径/到/配置"
```

如果 `fluent` 或 `mapdl` 在您的终端中能正常工作，MCP 服务器也能正常工作。

## 🏗️ 架构

```
┌──────────────────────────────────────────────────────┐
│  Claude Code CLI                                     │
│  "在 Re=10000 下模拟管道流动..."                      │
└──────────────┬───────────────────────────────────────┘
               │ stdio（通过 MCP 协议的 JSON-RPC）
┌──────────────▼───────────────────────────────────────┐
│  ansys-mcp-server (Python)                           │
│  ┌────────────────────────────────────────────────┐  │
│  │ 24 个 MCP 工具（Fluent、Mechanical、MAPDL、DPF）│  │
│  └──────────────────┬─────────────────────────────┘  │
│                     │ Python API 调用                  │
│  ┌──────────────────▼─────────────────────────────┐  │
│  │ AnsysClient（PyAnsys 懒加载包装器）             │  │
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
          │   Ansys 许可证管理器   │
          │   (ANSYSLI_SERVER)    │
          └───────────┬───────────┘
                      │
          ┌───────────▼───────────┐
          │  Ansys 求解器进程      │
          │  (fluent / mapdl /    │
          │   mechanical)         │
          └───────────────────────┘
```

## ❓ 常见问题

**问：没有许可证能使用吗？**
答：服务器可以运行，所有工具会返回指导和 API 示例。但实际启动求解器需要已授权的 Ansys 安装。在有有效许可证的机器上，PyAnsys 会自动获取。

**问：支持哪些 Ansys 版本？**
答：PyAnsys 支持 2024 R1 及以上版本（版本号 241+）。本服务器默认使用 2025 R1 (251)，但接受任何版本。

**问：能否在远程 HPC 集群上运行？**
答：可以 — PyAnsys 支持连接到远程 Fluent/Mechanical 实例。通过 `ANSYS_PLATFORM_INSTANCEMANAGEMENT_CONFIG` (PyPIM) 配置。对于 Slurm 集群，使用 `ansys-mapdl-core` 配合 `launch_mapdl(start_instance=False)`。

**问：这是 Ansys/Synopsys 的官方产品吗？**
答：不是。这是一个独立的社区项目。Ansys 和 Fluent 是 Ansys Inc. / Synopsys 的商标。

**问：Claude Code 能运行完整的参数化研究吗？**
答：能。描述您需要的："运行10个案例，入口速度从1到10 m/s，收集压降数据，绘制图表" — Claude Code 会循环调用工具。

**问：能使用现有的 .cas/.dat/.mechdb/.inp 文件吗？**
答：能。使用 `ansys_run_simulation` 并将 `input_file` 参数指向您的文件。对于 CAD 几何体（.stp、.iges、.scdoc），先使用 `ansys_load_geometry`。

**问：结果文件会自动保存吗？**
答：是的。每次仿真后，结果文件会保存到输出目录：Fluent 写入 `.cas.h5` + `.dat.h5`，Mechanical 写入 `.rst`，MAPDL 写入 `.rst/.rth`。您也可以通过 `ansys_export_results` 手动导出为 CSV、VTK、HDF5 或 NPZ 格式。

**问：可以获得哪些结果格式？**
答：`ansys_export_results` 支持：**CSV**（Excel/Python 分析）、**VTK/VTU**（ParaView 可视化）、**HDF5**（机器学习的高效二进制格式）、**EnSight**（专业后处理器）、**NPZ**（NumPy 兼容）。外加自动生成的 Markdown/HTML/PDF 报告。

**问：支持瞬态（时间相关）仿真吗？**
答：支持。通过 `ansys_set_parameters` 设置时间步参数：`{"time": "transient", "time_step_size": 0.01, "num_time_steps": 100}`。然后使用 `ansys_get_field_data` 或 `ansys_export_results` 配合 `timesteps` 参数提取特定时间步的数据。

**问：有哪些湍流模型可用？**
答：通过 Fluent/MAPDL：k-epsilon（标准、RNG、realizable）、k-omega（标准、SST）、Spalart-Allmaras、Reynolds Stress、LES、DES。描述您的需求，Claude Code 会配置正确的模型。

**问：能做多相流仿真吗？**
答：能 — Fluent 支持 VOF、Eulerian、Mixture 和 DPM 模型。告诉 Claude Code："设置水-空气自由表面的 VOF 模型"，它将通过 `ansys_set_parameters` 配置。

**问：支持 SolidWorks / Catia / NX / Fusion 360 的 CAD 几何体吗？**
答：支持。将 CAD 导出为 `.stp` 或 `.iges`（标准交换格式），然后使用 `ansys_load_geometry`。所有主流 CAD 工具都支持 STEP/IGES 导出。

**问：可以在 Windows 上使用，而 Ansys 在 Linux 上运行吗？**
答：可以。MCP 服务器在 Claude Code 所在位置运行。如果 Ansys 在 Linux 工作站上，在那里安装服务器并让 Claude Code 连接到它。也可以使用 SSH 隧道。

**问：如果仿真发散怎么办？**
答：Claude Code 可以诊断并修复。如果收敛失败，`ansys_get_convergence` 会显示哪些方程有问题。然后 Claude Code 可以调整欠松弛因子、切换到一阶格式或细化网格——全部通过现有工具。

**问：多个用户可以共享一个 Ansys 许可证吗？**
答：服务器不管理许可证队列——这是 Ansys 许可证管理器的工作。如果许可证服务器有 N 个席位，最多 N 个仿真可以同时运行。超出限制时 PyAnsys 会返回许可证错误。

**问：有速率限制或使用配额吗？**
答：没有——MCP 服务器没有人为限制。唯一的限制是您的硬件（CPU 核心、RAM）和 Ansys 许可证数量。如果您要求 Claude Code 运行 100 个仿真，它会照做——所以请明确说明您想要什么。

**问：可以在笔记本电脑上运行吗？**
答：可以，适用于中小型模型。16GB RAM 的笔记本可以处理约 2-5 百万 CFD 单元或约 50 万 FEA 节点的网格。学生许可证与此服务器兼容。

**问：重启电脑后需要手动启动 MCP 服务器吗？**
答：不需要。如果通过 `settings.json` 配置（`install.sh` 会自动完成），Claude Code CLI 会在启动时自动启动 MCP 服务器。只需打开 Claude Code 即可。手动测试：`./install.sh run`（或 `source .venv/bin/activate && cd src && python -m ansys_mcp_server.server`）。

**问：如何检查服务器是否在运行？**
答：在 Claude Code 中问：*"安装了哪些 Ansys 包？"* — 如果回复了，服务器就在运行。也可以检查进程：`ps aux | grep ansys_mcp_server`。如有问题，验证 `~/.claude/settings.json` 中的路径指向正确的 `.venv/bin/python`。

## 🤝 贡献

```bash
git clone https://github.com/vorobjewsen30-max/ansys-mcp-server.git
cd ansys-mcp-server
# 创建分支，进行修改，发送 PR
```

## 📄 许可证

MIT — 使用它，复刻它，交付它。

---

🤖 为 [Claude Code](https://claude.ai/code) 构建 · 基于 [PyAnsys](https://docs.pyansys.com) · MCP 协议

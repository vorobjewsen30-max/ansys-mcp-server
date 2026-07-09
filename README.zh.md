# Ansys MCP Server

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)(https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-2025.06.18-green.svg)](https://modelcontextprotocol.io/)

🌐 **语言:** &nbsp; [EN](README.md) &nbsp;|&nbsp; [РУС](README.ru.md) &nbsp;|&nbsp; **中文**

---

**让 Claude Code CLI 直接控制 Ansys 工程仿真。**

此 MCP（模型上下文协议）服务器将 PyAnsys 封装为 **30 个工具**，Claude Code 可以调用这些工具——在 Fluent 中运行 CFD、在 Mechanical 中进行 FEA、驱动 MAPDL、使用 DPF 进行后处理、使用 Prime 进行网格划分。AI 理解**完整的仿真流程**，从几何到导出，并自行决定下一步调用哪个工具。

> 🎯 **有何不同：** 这不是聊天机器人包装器，也不是文档爬虫。它让 Claude Code 真正以编程方式访问 Ansys 求解器进程——与 PyAnsys 内部使用的 API 相同。在安装了 Ansys 并拥有许可证的机器上，它**实际启动并控制求解器**。求解器窗口保持打开——您可以**实时**观看网格生成、收敛曲线和场数据渲染。

## 🎬 快速演示

```
用户："模拟10cm管道中的水流，长2m，入口速度5m/s，钢制管壁，300K"

Claude Code（通过 Ansys MCP）：
  1. ansys_list_workflows("cfd")              ← 确定使用哪个 workflow
  2. ansys_open_gui(solver="fluent")          ← 打开 Fluent GUI（单窗口）
  3. ansys_load_geometry("管道.stp")           ← 加载 CAD → 窗口中可见
  4. ansys_mesh_generate(element_size=0.5)     ← 网格实时构建
  5. ansys_set_material("fluid", "water")      ← 材料颜色在 GUI 中更新
  6. ansys_set_material("solid", "steel")
  7. ansys_set_boundary_conditions(...)        ← 边界条件在网格上高亮
  8. ansys_set_parameters({"viscous_model": "k-epsilon"})
  9. ansys_run_simulation(iterations=500)      ← 收敛曲线实时更新
  10. ansys_get_convergence()                  ← 残差历史
  11. ansys_get_field_data("velocity")         ← 探针点
  12. ansys_export_results(...)                ← CSV/VTK 导出到 ParaView
```

只需**一句话**。无需脚本、TUI 命令或 Workbench 点击。AI 知道执行顺序。

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

**错误非致命：** 如果 PyAnsys 包安装失败（无网络、缺少构建工具等），安装将继续进行并给出警告。服务器可以在没有它们的情况下工作——稍后可以运行 `pip install ansys-fluent-core`。

### 升级而不修改 Claude 配置

```bash
# 拉取最新代码 + 升级包，保留 ~/.claude/settings.json
./install.sh --upgrade
install.bat --upgrade       # Windows
```

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

## 🧰 工具（共 30 个）

### 🚀 会话管理（新增 — 持久窗口）
| 工具 | 功能 |
|------|------|
| `ansys_open_gui` | 打开 Fluent GUI **一次**。所有命令都发往同一窗口。实时观看网格、收敛曲线和结果。 |
| `ansys_session_status` | 当前会话状态：PID、求解器、运行时间、发送命令数 |
| `ansys_close_session` | 关闭 Ansys 窗口 |
| `ansys_connect` | 连接到已在运行的 Ansys 窗口（通过 psutil 自动检测） |
| `ansys_send_commands` | 向活动 Fluent 窗口发送原始 TUI/Scheme 命令 |
| `ansys_list_packages` | 检查已安装的 PyAnsys 包 |

### 🔧 网格操作
| 工具 | 功能 |
|------|------|
| `ansys_mesh_info` | 从活动窗口获取网格统计信息（节点数、单元数、质量） |
| `ansys_mesh_generate` | 从加载的几何体生成网格。**流程第 2 步。** 网格实时渲染。 |
| `ansys_mesh_refine` | 全局、按边界或按区域细化网格 |
| `ansys_mesh_quality` | 质量诊断（偏斜度、纵横比、正交质量） |

### ⚙️ 模型配置
| 工具 | 功能 |
|------|------|
| `ansys_set_parameters` | 设置求解器参数、模型、湍流方案 |
| `ansys_get_parameters` | 读取当前仿真参数 |
| `ansys_set_boundary_conditions` | 创建/修改边界条件（速度入口、压力出口、壁面等） |
| `ansys_list_boundary_conditions` | 列出模型中的所有边界条件 |
| `ansys_set_material` | 从材料库分配材料 |
| `ansys_list_materials` | 浏览 Ansys 材料库 |

### 🚀 运行与监控
| 工具 | 功能 |
|------|------|
| `ansys_run_simulation` | **在活动窗口中**开始计算。收敛曲线逐迭代更新。 |
| `ansys_get_convergence` | 获取残差历史（实时） |
| `ansys_stop_simulation` | 停止正在运行的计算 |

### 📊 结果处理
| 工具 | 功能 |
|------|------|
| `ansys_get_results_summary` | 列出所有可用的结果字段 |
| `ansys_get_field_data` | 在探针点提取场数据（速度、压力、温度、应力...） |
| `ansys_export_results` | 导出为 CSV / VTK / HDF5 / NPZ |
| `ansys_create_report` | 自动生成仿真报告（MD/HTML/PDF） |

### 🔄 跨产品工作流（新增）
| 工具 | 功能 |
|------|------|
| `ansys_list_workflows` | **首先使用这个。** 列出完整仿真流程：CFD、FEA、Thermal、FSI。告诉您以什么顺序调用哪些工具。 |
| `ansys_transfer_mesh` | 在 Ansys 产品间传递网格：Prime → Fluent、Fluent → Mechanical、MAPDL → DPF 等。 |

### 📖 帮助与文档
| 工具 | 功能 |
|------|------|
| `ansys_get_documentation` | 搜索 Ansys 文档 |
| `ansys_list_solvers` | 求解器目录，**含流程意识**——显示每个求解器前后应做什么 |
| `ansys_validate_setup` | 运行前检查设置中的常见错误 |
| `ansys_examples` | 获取完整示例（管道流、换热器、机翼气动、结构分析） |

## 🔄 AI 理解工作流程

当您说"对这个管道进行 CFD 分析"时，AI 知道：

1. **首先：** 加载几何体（`ansys_load_geometry` — "第一步"）
2. **然后：** 生成网格（`ansys_mesh_generate` — "第二步"）
3. **然后：** 材料、边界条件、求解器设置
4. **然后：** 求解、监控收敛
5. **最后：** 导出结果

当您说"阀门的流固耦合"时，AI 知道：
- Fluent 中的 CFD → 导出压力 → Mechanical 中的 FEA → 映射结果返回
- 它会调用 `ansys_list_workflows("fsi")` 获取完整的分步说明

当您问"如何设置热分析？"时，AI 会调用 `ansys_list_workflows("thermal")` 并显示流程。

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
┌───────────────────────────────────────────────────────────────┐
│  Claude Code CLI                                              │
│  "做 CFD 然后传到 Mechanical 做应力分析"                      │
└──────────────────────┬────────────────────────────────────────┘
                       │ stdio（通过 MCP 协议的 JSON-RPC）
┌──────────────────────▼────────────────────────────────────────┐
│  ansys-mcp-server (Python)                                    │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ 30 个 MCP 工具 + 工作流意识                               │  │
│  │ ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ │  │
│  │ │ 会话    │ │  网格    │ │  求解    │ │  工作流      │ │  │
│  │ │  管理   │ │  操作    │ │  后处理  │ │  管道        │ │  │
│  │ └─────────┘ └──────────┘ └──────────┘ └──────────────┘ │  │
│  │                      │                                   │  │
│  │      execute_tui() / scheme.exec() / journal fallback    │  │
│  └──────────────────────┬────────────────────────────────────┘  │
│                          │ 3 层递送                              │
│  ┌──────────────────────▼────────────────────────────────────┐  │
│  │               LiveAnsysSession（单例）                    │  │
│  │  一个持久的 Fluent 窗口——从不重复创建                      │  │
│  │  PID: 12345 | 命令: 47 | 运行时间: 12 分钟                │  │
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
              │   Ansys 许可证管理器   │
              │   (ANSYSLI_SERVER)    │
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │  Ansys 求解器进程      │
              │  (fluent / mapdl /    │
              │   mechanical)         │
              │  ┌─────────────────┐  │
              │  │ GUI 窗口        │  │
              │  │ • 网格渲染      │  │
              │  │ • 收敛曲线      │  │
              │  │ • 场数据        │  │
              │  └─────────────────┘  │
              └───────────────────────┘
```

**命令递送层级**（每条命令）：
1. `session.execute_tui()` — 通过 gRPC 直接 TUI 命令（首选）
2. `session.scheme.exec()` — Scheme 求值（备用）
3. Journal 文件 + 自动加载（最后手段）

## ❓ 常见问题

**问：没有许可证能使用吗？**
答：服务器可以运行，所有工具会返回指导和示例。但实际启动求解器需要已授权的 Ansys 安装。

**问：支持哪些 Ansys 版本？**
答：PyAnsys 支持 2024 R1 及以上版本（版本号 241+）。本服务器默认使用 2025 R1 (251)。

**问：AI 能理解多物理场工作流吗？**
答：能。服务器包含 `ansys_list_workflows`，描述 CFD、FEA、thermal 和 FSI 的完整流程。AI 知道哪个产品负责什么，以及以什么顺序调用工具。例如，FSI = Fluent（流体）→ Mechanical（结构）中间有网格传递。

**问：有没有 `--upgrade` 标志？**
答：有。`./install.sh --upgrade` 或 `install.bat --upgrade` 拉取最新代码并升级包，**不会修改** `~/.claude/settings.json`。

**问：Claude Code 能运行完整的参数化研究吗？**
答：能。描述："运行10个案例，入口速度从1到10 m/s，收集压降数据，绘制图表"——Claude Code 会循环调用工具。

**问：如果仿真发散怎么办？**
答：Claude Code 可以诊断并修复。`ansys_get_convergence` 会显示哪些方程有问题。Claude Code 可以调整欠松弛因子、切换到一阶格式或细化网格。

**问：重启电脑后需要手动启动 MCP 服务器吗？**
答：不需要。如果通过 `settings.json` 配置，Claude Code CLI 会在启动时自动启动 MCP 服务器。

**问：这是 Ansys/Synopsys 的官方产品吗？**
答：不是。这是一个独立的社区项目。

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

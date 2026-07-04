# Ansys MCP Server

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-2025.06.18-green.svg)](https://modelcontextprotocol.io/)

🌐 **Язык:** &nbsp; [EN](README.md) &nbsp;|&nbsp; **РУС** &nbsp;|&nbsp; [中文](README.zh.md)

---

**Дайте Claude Code CLI прямой контроль над инженерными симуляциями Ansys.**

Этот MCP-сервер оборачивает PyAnsys в 24 инструмента, которые Claude Code может вызывать — CFD во Fluent, прочностной анализ в Mechanical, расчёты в MAPDL, пост-обработка в DPF, сетки в Prime. Больше никаких кликов в Workbench. Просто опишите задачу словами.

> 🎯 **Чем это отличается:** Это не чат-обёртка. Это не парсер документации. Это реальный программный доступ к процессу решателя Ansys — через тот же API, который PyAnsys использует внутри. На машине с установленным и лицензированным Ansys сервер **реально запускает и управляет решателями**.

## 🎬 Быстрая демонстрация

```
Пользователь: "Смоделируй течение воды в трубе 10см, длина 2м, скорость на входе 5 м/с,
              стальные стенки, температура 300K"

Claude Code (через Ansys MCP):
  1. ansys_examples("pipe_flow")           ← находит подходящий шаблон настройки
  2. ansys_mesh_generate(труба.stp, ...)   ← генерирует сетку 500k ячеек
  3. ansys_set_material(вода, сталь)       ← назначает материалы
  4. ansys_set_boundary_conditions(...)    ← velocity-inlet, pressure-outlet
  5. ansys_set_parameters(k-epsilon, ...)  ← настраивает модель турбулентности
  6. ansys_run_simulation(...)             ← запускает Fluent с лицензией
  7. ansys_get_convergence()               ← мониторит невязки
  8. ansys_get_field_data("velocity")      ← извлекает поле скоростей
  9. ansys_export_results(VTK)             ← экспорт для ParaView
```

Всё — с **одного предложения**. Без скриптов, TUI-команд и кликов в Workbench.

## 🚀 Установка (2 минуты)

### Требования
- Python 3.10+
- Установленный и лицензированный Ansys (Fluent, Mechanical или MAPDL)
- Claude Code CLI

### Способ 1: Автоустановщик

```bash
# Клонировать
git clone https://github.com/vorobjewsen30-max/ansys-mcp-server.git
cd ansys-mcp-server

# Установка + авто-настройка Claude Code
./install.sh                    # Linux / Mac
# install.bat                   # Windows
```

Установщик сам:
1. Создаст виртуальное окружение `.venv`
2. Установит `mcp` SDK
3. Опционально установит PyAnsys (`./install.sh install-all` для всего)
4. Пропишет конфиг в `~/.claude/settings.json`

### Способ 2: Вручную

```bash
# 1. Создать venv
python3 -m venv .venv && source .venv/bin/activate

# 2. Установить MCP SDK
pip install mcp

# 3. Установить PyAnsys для ваших продуктов
pip install ansys-fluent-core        # CFD
pip install ansys-mapdl-core         # Прочность / APDL
pip install ansys-dpf-core           # Пост-обработка
pip install ansys-meshing-prime      # Сетки

# 4. Настроить Claude Code CLI (~/.claude/settings.json)
# Добавить в ~/.claude/settings.json:
```

```json
{
  "mcpServers": {
    "ansys": {
      "command": "/путь/к/ansys-mcp-server/.venv/bin/python",
      "args": ["-m", "ansys_mcp_server.server"],
      "cwd": "/путь/к/ansys-mcp-server/src"
    }
  }
}
```

```bash
# 5. Перезапустить Claude Code CLI — готово!
```

### Способ 3: pip install

```bash
pip install git+https://github.com/vorobjewsen30-max/ansys-mcp-server.git

# В конфиге Claude Code:
# "command": "ansys-mcp-server"
```

## 🧰 Инструменты (24 всего)

### 🚀 Управление симуляциями
| Инструмент | Что делает |
|-----------|-------------|
| `ansys_list_packages` | Проверить установленные PyAnsys пакеты |
| `ansys_run_simulation` | Запустить симуляцию (Fluent / Mechanical / MAPDL) |
| `ansys_get_simulation_status` | Статус запущенной симуляции |
| `ansys_stop_simulation` | Корректно остановить симуляцию |
| `ansys_watch_simulation` | Мониторить сходимость в реальном времени |

### 🔧 Операции с сеткой
| Инструмент | Что делает |
|-----------|-------------|
| `ansys_mesh_info` | Статистика сетки (узлы, элементы, качество) |
| `ansys_mesh_generate` | Генерация сетки из геометрии (STP, IGES, SCDOC) |
| `ansys_mesh_refine` | Измельчение сетки глобально или по области |
| `ansys_mesh_quality` | Диагностика качества (skewness, aspect ratio, ...) |
| `ansys_mesh_convert` | Конвертация форматов (MSH ↔ CDB ↔ VTU) |

### 📊 Обработка результатов
| Инструмент | Что делает |
|-----------|-------------|
| `ansys_get_results_summary` | Список доступных полей результатов |
| `ansys_get_field_data` | Извлечь поля в точках (напряжения, скорость, температура...) |
| `ansys_export_results` | Экспорт в CSV / VTK / HDF5 / NPZ |
| `ansys_get_convergence` | История сходимости (невязки) |
| `ansys_create_report` | Авто-генерация отчёта (MD/HTML/PDF) |

### ⚙️ Настройка модели
| Инструмент | Что делает |
|-----------|-------------|
| `ansys_set_parameters` | Установить параметры решателя, модели, численные схемы |
| `ansys_get_parameters` | Прочитать текущие параметры симуляции |
| `ansys_set_boundary_conditions` | Создать/изменить граничные условия |
| `ansys_list_boundary_conditions` | Список всех ГУ в модели |
| `ansys_set_material` | Назначить материалы из библиотеки или свои свойства |
| `ansys_list_materials` | Поиск по библиотеке материалов Ansys |

### 📖 Помощь и документация
| Инструмент | Что делает |
|-----------|-------------|
| `ansys_get_documentation` | Поиск по документации Ansys |
| `ansys_list_solvers` | Каталог доступных решателей и их физик |
| `ansys_validate_setup` | Проверка настроек на типовые ошибки |
| `ansys_examples` | Готовые примеры (течение в трубе, крыло, теплообменник...) |

## 📦 Поддерживаемые продукты Ansys

| Продукт | PyAnsys пакет | Что делает |
|---------|--------------|------------|
| **Fluent** | `ansys-fluent-core` | CFD — жидкости, теплообмен, турбулентность, многофазные течения |
| **Mechanical** | `ansys-mechanical-core` | МКЭ — статика, динамика, контакт, усталость |
| **MAPDL** | `ansys-mapdl-core` | Классический APDL — полный МКЭ + электромагнетизм |
| **DPF** | `ansys-dpf-core` | Пост-обработка — извлечение и трансформация результатов |
| **Prime Mesh** | `ansys-meshing-prime` | Сетки — тетраэдры, гексаэдры, полиэдры, призматические слои |

Установите что нужно:
```bash
pip install ansys-fluent-core        # Только Fluent
pip install ansys-mapdl-core         # Только MAPDL
# ... или всё сразу
pip install ansys-fluent-core ansys-dpf-core ansys-meshing-prime
```

## 🔐 Лицензия

**Сервер сам не управляет лицензиями.** PyAnsys автоматически подхватывает лицензию Ansys из стандартных переменных окружения:

```bash
# Обычно уже установлены при инсталляции Ansys:
export ANSYSLI_SERVER="1055@your-license-server"
export ANSYSLMD_LICENSE_FILE="1055@your-license-server"

# Или для корпоративного PyPIM:
export ANSYS_PLATFORM_INSTANCEMANAGEMENT_CONFIG="/путь/к/конфигу"
```

Если `fluent` или `mapdl` работают из терминала — MCP-сервер тоже заработает.

## 🏗️ Архитектура

```
┌──────────────────────────────────────────────────────┐
│  Claude Code CLI                                     │
│  "Смоделируй течение в трубе при Re=10000..."        │
└──────────────┬───────────────────────────────────────┘
               │ stdio (JSON-RPC через MCP протокол)
┌──────────────▼───────────────────────────────────────┐
│  ansys-mcp-server (Python)                           │
│  ┌────────────────────────────────────────────────┐  │
│  │ 24 MCP инструмента (Fluent, Mechanical, MAPDL) │  │
│  └──────────────────┬─────────────────────────────┘  │
│                     │ Python API                      │
│  ┌──────────────────▼─────────────────────────────┐  │
│  │ AnsysClient (lazy-load обёртка над PyAnsys)    │  │
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
          │  Процесс решателя     │
          │  Ansys (fluent/mapdl  │
          │  /mechanical)         │
          └───────────────────────┘
```

## ❓ Часто задаваемые вопросы

**В: Работает ли без лицензии?**
О: Сервер запускается и все инструменты отвечают с примерами и подсказками. Но реальный запуск решателя требует лицензионный Ansys. На машине с действующей лицензией PyAnsys подхватывает её автоматически.

**В: Какие версии Ansys поддерживаются?**
О: PyAnsys поддерживает 2024 R1 и новее (версии 241+). Сервер по умолчанию нацелен на 2025 R1 (251), но принимает любую версию.

**В: Можно ли запускать на удалённом HPC кластере?**
О: Да — PyAnsys поддерживает подключение к удалённым экземплярам Fluent/Mechanical. Настройте через `ANSYS_PLATFORM_INSTANCEMANAGEMENT_CONFIG` (PyPIM). Для Slurm-кластеров используйте `ansys-mapdl-core` с `launch_mapdl(start_instance=False)`.

**В: Это официальный продукт Ansys/Synopsys?**
О: Нет. Это независимый community-проект. Ansys и Fluent — торговые марки Ansys Inc. / Synopsys.

**В: Может ли Claude Code провести параметрическое исследование?**
О: Да. Опишите: *"Запусти 10 случаев с разной скоростью на входе от 1 до 10 м/с, собери перепад давления, построй график"* — Claude Code вызовет инструменты в цикле.

**В: Работает ли с моими существующими файлами .cas/.dat/.mechdb/.inp?**
О: Да. Используйте `ansys_run_simulation` с параметром `input_file`, указывающим на ваш файл. Для CAD-геометрии (.stp, .iges, .scdoc) сначала вызовите `ansys_load_geometry`.

**В: Сохраняются ли файлы результатов автоматически?**
О: Да. После каждой симуляции результаты сохраняются в выходную директорию: Fluent пишет `.cas.h5` + `.dat.h5`, Mechanical — `.rst`, MAPDL — `.rst/.rth`. Также можно вручную экспортировать через `ansys_export_results` в CSV, VTK, HDF5 или NPZ.

**В: Какие форматы результатов доступны?**
О: `ansys_export_results` поддерживает: **CSV** (анализ в Excel/Python), **VTK/VTU** (визуализация в ParaView), **HDF5** (эффективный бинарный для ML), **EnSight** (профессиональный пост-процессор), **NPZ** (совместимость с NumPy). Плюс авто-отчёты в Markdown/HTML/PDF.

**В: Поддерживает ли переходные (нестационарные) симуляции?**
О: Да. Настройте параметры времени через `ansys_set_parameters` с `{"time": "transient", "time_step_size": 0.01, "num_time_steps": 100}`. Затем используйте `ansys_get_field_data` с параметром `timesteps` для извлечения данных на конкретных шагах.

**В: Какие модели турбулентности доступны?**
О: Через Fluent/MAPDL: k-epsilon (standard, RNG, realizable), k-omega (standard, SST), Spalart-Allmaras, Reynolds Stress, LES, DES. Опишите что нужно, и Claude Code настроит правильную модель.

**В: Поддерживает ли многофазные течения?**
О: Да — Fluent поддерживает VOF, Eulerian, Mixture и DPM модели. Скажите Claude Code: *"настрой VOF модель для поверхности вода-воздух"* — и он сконфигурирует через `ansys_set_parameters`.

**В: Поддерживает ли геометрию из SolidWorks / Catia / NX / Fusion 360?**
О: Да. Экспортируйте CAD как `.stp` или `.iges` (стандартные обменные форматы), затем используйте `ansys_load_geometry`. Все основные CAD-системы поддерживают экспорт STEP/IGES.

**В: Можно ли использовать на Windows, пока Ansys работает на Linux?**
О: Да. MCP-сервер запускается там, где Claude Code. Если Ansys на Linux-рабочей станции — установите сервер там и подключите Claude Code к нему. Также можно использовать SSH-туннелирование.

**В: Что если симуляция расходится?**
О: Claude Code может диагностировать и исправить это. Если сходимость не достигается, `ansys_get_convergence` покажет проблемные уравнения. Claude Code может скорректировать under-relaxation factors, переключиться на first-order схемы или измельчить сетку — всё через существующие инструменты.

**В: Могут ли несколько пользователей делить одну лицензию Ansys?**
О: Сервер не управляет очередью лицензий — это делает менеджер лицензий Ansys. Если у сервера N мест, до N симуляций могут работать одновременно. При превышении PyAnsys вернёт ошибку лицензии.

**В: Есть ли ограничения по частоте или квотам?**
О: Нет — у MCP-сервера нет искусственных лимитов. Единственные ограничения — ваше железо (CPU, RAM) и количество лицензий Ansys. Claude Code запустит 100 симуляций, если попросите — поэтому формулируйте запросы конкретно.

**В: Можно ли запускать на ноутбуке?**
О: Да, для моделей малого и среднего размера. Ноутбук с 16 ГБ RAM осилит сетки до ~2-5 млн ячеек для CFD или ~500k узлов для МКЭ. Студенческие лицензии работают с этим сервером.

**В: После перезагрузки ПК нужно вручную запускать MCP-сервер?**
О: Нет. Если настроено через `settings.json` (что `install.sh` делает автоматически), Claude Code CLI сам запускает MCP-сервер при старте. Просто откройте Claude Code и работайте. Для ручного теста: `./install.sh run` (или `source .venv/bin/activate && cd src && python -m ansys_mcp_server.server`).

**В: Как проверить, что сервер работает?**
О: Спросите в Claude Code: *"Какие пакеты Ansys установлены?"* — если отвечает, сервер жив. Можно также проверить процессы: `ps aux | grep ansys_mcp_server`. Если проблемы — проверьте путь в `~/.claude/settings.json`, он должен указывать на `.venv/bin/python`.

## 🤝 Участие в разработке

```bash
git clone https://github.com/vorobjewsen30-max/ansys-mcp-server.git
cd ansys-mcp-server
# Создайте ветку, внесите изменения, отправьте PR
```

## 📄 Лицензия

MIT — используйте, форкайте, внедряйте.

---

🤖 Создано для [Claude Code](https://claude.ai/code) · На базе [PyAnsys](https://docs.pyansys.com) · Протокол MCP

# Ansys MCP Server

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-2025.06.18-green.svg)](https://modelcontextprotocol.io/)

🌐 **Язык:** &nbsp; [EN](README.md) &nbsp;|&nbsp; **РУС** &nbsp;|&nbsp; [中文](README.zh.md)

---

**Дайте Claude Code CLI прямой контроль над инженерными симуляциями Ansys.**

Этот MCP-сервер оборачивает PyAnsys в **30 инструментов**, которые Claude Code может вызывать — CFD во Fluent, прочностной анализ в Mechanical, расчёты в MAPDL, пост-обработка в DPF, сетки в Prime. Нейросеть понимает **полный пайплайн симуляции** от геометрии до экспорта, и сама решает, какой инструмент вызвать следующим.

> 🎯 **Чем это отличается:** Это не чат-обёртка и не парсер документации. Это реальный программный доступ к процессу решателя Ansys. На машине с установленным и лицензированным Ansys сервер **запускает и управляет решателями**. Окно решателя остаётся открытым — вы видите, как строится сетка, рисуется график сходимости и отображаются поля **в реальном времени**.

## 🎬 Быстрая демонстрация

```
Пользователь: "Смоделируй течение воды в трубе 10см, длина 2м,
              скорость на входе 5 м/с, стальные стенки, температура 300K"

Claude Code (через Ansys MCP):
  1. ansys_list_workflows("cfd")               ← определяет нужный workflow
  2. ansys_open_gui(solver="fluent")            ← открывает Fluent GUI (одно окно)
  3. ansys_load_geometry("труба.stp")           ← загружает CAD → видно в окне
  4. ansys_mesh_generate(element_size=0.5)      ← сетка строится на экране
  5. ansys_set_material("fluid", "water")       ← цвета материалов в GUI
  6. ansys_set_material("solid", "steel")
  7. ansys_set_boundary_conditions(...)         ← ГУ подсвечиваются на сетке
  8. ansys_set_parameters({"viscous_model": "k-epsilon"})
  9. ansys_run_simulation(iterations=500)       ← график сходимости живьём
  10. ansys_get_convergence()                   ← история невязок
  11. ansys_get_field_data("velocity")          ← точки-зонды
  12. ansys_export_results(...)                 ← CSV/VTK для ParaView
```

Всё — с **одного предложения**. Ни скриптов, ни TUI-команд, ни кликов в Workbench.

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

**Ошибки нефатальны:** Если PyAnsys пакеты не установились (нет интернета, не хватает build tools), установка продолжается с предупреждением. Сервер работает и без них — `pip install ansys-fluent-core` можно выполнить позже.

### Обновление без изменения конфига Claude

```bash
# Скачать последний код + обновить пакеты, ~/.claude/settings.json не трогается
./install.sh --upgrade
install.bat --upgrade       # Windows
```

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

## 🧰 Инструменты (30 всего)

### 🚀 Управление сессией (НОВОЕ — постоянное окно)
| Инструмент | Что делает |
|-----------|-------------|
| `ansys_open_gui` | Открыть Fluent GUI **один раз**. Все команды идут в это же окно. Сетка, сходимость, поля — в реальном времени. |
| `ansys_session_status` | Статус сессии: PID, решатель, время работы, количество команд |
| `ansys_close_session` | Закрыть окно Ansys |
| `ansys_connect` | Подключиться к уже запущенному окну (авто-детект через psutil) |
| `ansys_send_commands` | Отправить сырые TUI/Scheme команды в активное окно |
| `ansys_list_packages` | Проверить установленные PyAnsys пакеты |

### 🔧 Операции с сеткой
| Инструмент | Что делает |
|-----------|-------------|
| `ansys_mesh_info` | Статистика сетки из активного окна (узлы, элементы, качество) |
| `ansys_mesh_generate` | Генерация сетки из геометрии. **Шаг 2** в пайплайне. Сетка строится на экране. |
| `ansys_mesh_refine` | Измельчение сетки глобально, по границе или по области |
| `ansys_mesh_quality` | Диагностика качества (skewness, aspect ratio, orthogonal quality) |

### ⚙️ Настройка модели
| Инструмент | Что делает |
|-----------|-------------|
| `ansys_set_parameters` | Параметры решателя, модели, турбулентность |
| `ansys_get_parameters` | Прочитать текущие параметры |
| `ansys_set_boundary_conditions` | Создать/изменить ГУ (velocity-inlet, pressure-outlet, wall и т.д.) |
| `ansys_list_boundary_conditions` | Список всех ГУ в модели |
| `ansys_set_material` | Назначить материалы из библиотеки |
| `ansys_list_materials` | Поиск по библиотеке материалов |

### 🚀 Запуск и мониторинг
| Инструмент | Что делает |
|-----------|-------------|
| `ansys_run_simulation` | Запустить расчёт **в активном окне**. График сходимости обновляется на каждом шаге. |
| `ansys_get_convergence` | История невязок (live) |
| `ansys_stop_simulation` | Остановить расчёт |

### 📊 Обработка результатов
| Инструмент | Что делает |
|-----------|-------------|
| `ansys_get_results_summary` | Список доступных полей результатов |
| `ansys_get_field_data` | Извлечь поля в точках (скорость, давление, температура, напряжения...) |
| `ansys_export_results` | Экспорт в CSV / VTK / HDF5 / NPZ |
| `ansys_create_report` | Авто-генерация отчёта (MD/HTML/PDF) |

### 🔄 Кросс-продуктовые workflow (НОВОЕ)
| Инструмент | Что делает |
|-----------|-------------|
| `ansys_list_workflows` | **Используйте первым.** Показывает полный пайплайн для CFD, FEA, Thermal, FSI. Какие инструменты и в каком порядке вызывать. |
| `ansys_transfer_mesh` | Передача сетки между продуктами: Prime → Fluent, Fluent → Mechanical, MAPDL → DPF и т.д. |

### 📖 Помощь и документация
| Инструмент | Что делает |
|-----------|-------------|
| `ansys_get_documentation` | Поиск по документации Ansys |
| `ansys_list_solvers` | Каталог решателей с **осведомлённостью о пайплайне** — что делать до и после каждого |
| `ansys_validate_setup` | Проверка настроек перед запуском |
| `ansys_examples` | Готовые примеры (pipe flow, heat exchanger, wing aero, structural) |

## 🔄 Нейросеть понимает пайплайн

Когда вы говорите *"Сделай CFD анализ этой трубы"*, ИИ знает:

1. **Сначала:** загрузить геометрию (`ansys_load_geometry` — "ПЕРВЫЙ ШАГ")
2. **Потом:** построить сетку (`ansys_mesh_generate` — "ВТОРОЙ ШАГ")
3. **Потом:** материалы, ГУ, параметры решателя
4. **Потом:** расчёт, мониторинг сходимости
5. **В конце:** экспорт результатов

Когда вы говорите *"FSI клапана"*, ИИ знает:
- CFD во Fluent → экспорт давлений → FEA в Mechanical → обратное отображение результатов
- Он вызывает `ansys_list_workflows("fsi")` для пошаговых инструкций

Когда вы спрашиваете *"Как настроить тепловой расчёт?"*, ИИ вызывает `ansys_list_workflows("thermal")` и показывает пайплайн.

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
┌───────────────────────────────────────────────────────────────┐
│  Claude Code CLI                                              │
│  "Сделай CFD, потом передай в Mechanical на прочность"        │
└──────────────────────┬────────────────────────────────────────┘
                       │ stdio (JSON-RPC через MCP протокол)
┌──────────────────────▼────────────────────────────────────────┐
│  ansys-mcp-server (Python)                                    │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ 30 MCP инструментов + осведомлённость о пайплайне       │  │
│  │ ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ │  │
│  │ │ Session │ │  Mesh    │ │  Solve   │ │  Workflow    │ │  │
│  │ │  Mgmt   │ │  Ops     │ │  & Post  │ │  Pipeline    │ │  │
│  │ └─────────┘ └──────────┘ └──────────┘ └──────────────┘ │  │
│  │                      │                                   │  │
│  │      execute_tui() / scheme.exec() / journal fallback    │  │
│  └──────────────────────┬────────────────────────────────────┘  │
│                          │ 3-уровневая доставка                  │
│  ┌──────────────────────▼────────────────────────────────────┐  │
│  │               LiveAnsysSession (синглтон)                 │  │
│  │  Одно окно Fluent — никогда не дублируется                │  │
│  │  PID: 12345 | Команд: 47 | Время работы: 12 мин          │  │
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
              │  │ GUI Окно        │  │
              │  │ • Сетка рисуется│  │
              │  │ • Сходимость    │  │
              │  │ • Поля данных   │  │
              │  └─────────────────┘  │
              └───────────────────────┘
```

**Уровни доставки команд** (на каждую команду):
1. `session.execute_tui()` — прямая TUI-команда через gRPC (предпочтительно)
2. `session.scheme.exec()` — Scheme-вычисление (запасной)
3. Journal-файл + автозагрузка (последний шанс)

## ❓ Часто задаваемые вопросы

**В: Работает ли без лицензии?**
О: Сервер запускается и все инструменты отвечают с примерами. Но реальный запуск решателя требует лицензию. На машине с действующей лицензией PyAnsys подхватывает её автоматически.

**В: Какие версии Ansys поддерживаются?**
О: PyAnsys поддерживает 2024 R1 и новее (241+). Сервер целится на 2025 R1 (251), но принимает любую версию.

**В: Понимает ли нейросеть мультифизику?**
О: Да. Сервер включает `ansys_list_workflows` с полным пайплайном для CFD, FEA, thermal и FSI. ИИ знает, какой продукт за что отвечает, и в каком порядке вызывать инструменты. Например, FSI = Fluent (жидкость) → Mechanical (конструкция) с передачей сетки между ними.

**В: Можно ли запускать на удалённом HPC кластере?**
О: Да — PyAnsys поддерживает подключение к удалённым экземплярам. Настройте через `ANSYS_PLATFORM_INSTANCEMANAGEMENT_CONFIG` (PyPIM).

**В: Это официальный продукт Ansys/Synopsys?**
О: Нет. Это независимый community-проект.

**В: Есть ли флаг `--upgrade`?**
О: Да. `./install.sh --upgrade` или `install.bat --upgrade` скачивает последний код и обновляет пакеты, **не трогая** `~/.claude/settings.json`.

**В: Может ли Claude Code провести параметрическое исследование?**
О: Да. Опишите: *"Запусти 10 случаев с разной скоростью от 1 до 10 м/с, собери перепад давления, построй график"* — Claude Code вызовет инструменты в цикле.

**В: Что если симуляция расходится?**
О: Claude Code может диагностировать и исправить. `ansys_get_convergence` покажет проблемные уравнения. Claude Code скорректирует under-relaxation, переключится на first-order или измельчит сетку.

**В: После перезагрузки ПК нужно вручную запускать MCP-сервер?**
О: Нет. Если настроено через `settings.json`, Claude Code CLI сам запускает сервер при старте.

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

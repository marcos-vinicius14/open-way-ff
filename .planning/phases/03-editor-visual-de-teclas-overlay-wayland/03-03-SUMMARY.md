---
phase: 03-editor-visual-de-teclas-overlay-wayland
plan: "03"
subsystem: core
tags: [macro, macro-scheduler, keymap-engine, widget-views, gg-mouse-pro, osd, multi-touch]

# Dependency graph
requires:
  - phase: 03-editor-visual-de-teclas-overlay-wayland
    plan: "02"
    provides: OverlayCanvas, FloatingTopBar and ProfileDebounceSaver
provides:
  - MacroStep and MacroWidget polymorphic schema serialization and factory support
  - NonBlockingMacroScheduler event-driven multi-touch sequencer with zero thread sleeping
  - Canonical key converters and compact HUD OSD labels (key_codes.py)
  - KeymapEngine low-latency physical evdev to uinput multi-touch translator (slots 2–9, D-Pad 8-way)
  - GG Mouse Pro styled widget views (TapWidgetView, DPadWidgetView, AimWidgetView, FireWidgetView, MacroSequenceView)
  - Full OSD opacity control (0% to 100%) and instant F3 toggle
affects: [04-launcher]

actuals:
  tokens: 28000
  tasks: 2
  commits: 1

tech-stack:
  added: []
  patterns: [Monotonic non-blocking macro queue, GLib.idle_add cross-thread UI marshaling, 8-way normalized vector D-Pad]

key-files:
  created:
    - src/wayfire/core/keymap_engine.py
    - src/wayfire/core/macro_scheduler.py
    - src/wayfire/ui/key_codes.py
    - src/wayfire/ui/widget_views.py
    - tests/test_key_codes.py
    - tests/test_macro_widget.py
    - tests/test_keymap_engine.py
    - tests/test_widget_views.py
  modified:
    - src/wayfire/config/widgets.py
    - src/wayfire/cli/main.py
    - src/wayfire/core/mouse_capture.py

key-decisions:
  - "D-09: Widget views adopt the GG Mouse Pro aesthetic with 48x48px translucent circular buttons, fine borders, and compact bold labels."
  - "D-10: OSD opacity is fully adjustable from 0% (100% invisible for competitive match play) to 100%, with F3 instant toggle."
  - "D-11: Visual press feedback (.pressed) provides orange competitive glow (#ff5000) only while physical keys are held, remaining invisible at 0.0 opacity."
  - "D-14: Canonical JSON naming (Space, Shift_L, Mouse_4) cleanly maps to compact 1-3 char HUD labels (SPC, SHF, M4)."
  - "D-16: MacroWidget and NonBlockingMacroScheduler execute sequential uinput touches using monotonic timestamps without time.sleep, protecting <1ms input latency."

patterns-established:
  - "Cross-Thread UI Dispatch: evdev event thread marshals visual state updates to GTK exclusively via GLib.idle_add."
  - "Strict Slot Isolation: Slot 0 reserved for AimEngine, Slot 1 for FireWidget, Slot 2 for DPadWidget, and Slots 3–9 for dynamic multi-touch and macros."

requirements-completed: ["MAP-02"]

## Self-Check: PASSED
---

# Plan 03-03: Mapeamento Polimórfico de Widgets, Macros Sequenciais, Rótulos Canônicos/OSD, OSD HUD & Keymap Engine - Summary

Finalização completa da camada de mapeamento e OSD da Fase 3:
- **`MacroStep` e `MacroWidget` (`src/wayfire/config/widgets.py`)**: Suporte a macros sequenciais numerados com intervalos configuráveis serializados no JSON do perfil.
- **`NonBlockingMacroScheduler` (`src/wayfire/core/macro_scheduler.py`)**: Escalonador temporal monotônico que enfileira toques e pulsos de soltura (15ms) em slots dedicados sem invocar chamadas bloqueantes `time.sleep`, preservando latência <1ms.
- **`key_codes.py` (`src/wayfire/ui/key_codes.py`)**: Mapeamento bidirecional padronizando nomes canônicos no perfil e rótulos compactos de 1 a 3 caracteres no HUD (`SPC`, `SHF`, `M4`, `RMB`).
- **`KeymapEngine` (`src/wayfire/core/keymap_engine.py`)**: Despachador de eventos com cálculo vetorial normalizado de 8 direções para o analógico WASD (slot 2), multi-touch simultâneo em slots dinâmicos (slots 3–9) e gatilho de fogo (slot 1), notificando a interface GTK de forma segura via `GLib.idle_add`.
- **`widget_views.py` (`src/wayfire/ui/widget_views.py`)**: Visões visuais translúcidas estilo GG Mouse Pro com feedback alaranjado suave (`#ff5000`) ao pressionar e controle contínuo de opacidade de 0% (invisibilidade total para jogo competitivo) a 100%, integrado ao atalho de toggle rápido `F3`.
- **Testes Herméticos**: 12 novos testes cobrindo conversores canônicos, scheduler não-bloqueante, despacho uinput multitouch, analógico 8-way, gatilho, visões gráficas e invisibilidade a 0% de opacidade.

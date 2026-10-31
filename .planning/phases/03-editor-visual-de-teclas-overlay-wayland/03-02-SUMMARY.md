---
phase: 03-editor-visual-de-teclas-overlay-wayland
plan: "02"
subsystem: ui
tags: [canvas, gg-mouse-pro, double-click, debounce, gestures, singletons, floating-bar]

# Dependency graph
requires:
  - phase: 03-editor-visual-de-teclas-overlay-wayland
    plan: "01"
    provides: WayFireOverlayWindow and StatusPill
provides:
  - ProfileDebounceSaver with 500ms continuous auto-save and flush capability
  - FloatingTopBar retractable toolbar with DPad, Aim, Fire, Tap actions and OSD opacity scale
  - OverlayCanvas absolute layout with double-click GG Mouse Pro widget creation [ ? ]
  - Unified key and mouse peripheral capture (M4, M5, RMB, MMB) with ESC cancel
  - Friendly system hotkey blocking for F1, F2, F3 via Adw.Toast
  - Strict singleton enforcement for AimWidget and DPadWidget with repositioning
  - Widget drag positioning, area resizing, and deletion (Delete/Backspace)
affects: [03-03, 04-launcher]

actuals:
  tokens: 24000
  tasks: 2
  commits: 1

tech-stack:
  added: []
  patterns: [Debounced I/O coalescing via GLib.timeout_add, Absolute canvas layout with Gtk.Fixed and GestureDrag, Singleton widget clamping]

key-files:
  created:
    - src/wayfire/ui/debounce_saver.py
    - src/wayfire/ui/floating_bar.py
    - src/wayfire/ui/overlay_canvas.py
    - tests/test_debounce_saver.py
    - tests/test_overlay_canvas.py
  modified:
    - src/wayfire/ui/overlay.py

key-decisions:
  - "D-03: ProfileDebounceSaver coalesces rapid visual editing events into atomic disk writes with 500ms debounce, preventing I/O thrashing during drag gestures."
  - "D-05: Double click anywhere on free canvas creates a new TapWidget in listening mode [ ? ] immediately."
  - "D-06 & D-07: Widgets are draggable, support area resizing (radius/width/height), and can be removed via Delete/Backspace keys or explicit deletion."
  - "D-08: AimWidget and DPadWidget are restricted to 1 instance per profile; duplicate creations reposition the existing widget with an Adw.Toast notice."
  - "D-13: Unified peripheral capture maps mouse buttons (Mouse_Middle, Mouse_Right, Mouse_4, Mouse_5) to listening widgets, with Escape canceling."
  - "D-15: System keys F1, F2, F3 are protected with an informative toast and prevented from in-game binding."

patterns-established:
  - "Debounced Persistence: Component updates state in-memory immediately and schedules background disk sync via ProfileDebounceSaver."
  - "Toast Notifications: Clean user feedback via Adw.ToastOverlay for validation constraints."

requirements-completed: ["UI-02"]

## Self-Check: PASSED
---

# Plan 03-02: Editor Visual Estilo GG Mouse Pro — Summary

Implementação da infraestrutura visual interativa do editor de mapeamento do WayFire:
- **`ProfileDebounceSaver` (`src/wayfire/ui/debounce_saver.py`)**: Serviço de persistência reativa com temporizador de 500ms via `GLib.timeout_add` que agrupa eventos de arraste de mouse e mudanças contínuas de sliders em uma única gravação atômica em disco, com suporte a `flush()` imediato ao sair do modo de edição.
- **`FloatingTopBar` (`src/wayfire/ui/floating_bar.py`)**: Barra de ferramentas flutuante ancorada no topo do modo de edição com botões para adicionar D-Pad, Mira FPS, Gatilho e Botão, slider de controle de opacidade OSD (0% a 100%) e botão de conclusão.
- **`OverlayCanvas` (`src/wayfire/ui/overlay_canvas.py`)**: Canvas de layout absoluto construído sobre `Gtk.Fixed` com controle de gestos:
  - Criação rápida por duplo clique com botão esquerdo em estado pulsante `[ ? ]`.
  - Captura unificada de teclado e periféricos de mouse (M4, M5, RMB, MMB) com cancelamento seguro por `ESC`.
  - Bloqueio amigável de teclas reservadas do sistema (`F1`, `F2`, `F3`) com alerta via `Adw.Toast`.
  - Validação rigorosa de instância única para `AimWidget` e `DPadWidget`, reposicionando a instância existente e emitindo aviso toast.
  - Alças de redimensionamento e atalhos de exclusão rápida (`Delete`, `Backspace`).
- **Testes Herméticos**: 9 novos testes cobrindo debounce, flush, barra de ferramentas, duplo clique, captura de teclas/mouse, bloqueio de hotkeys de sistema, singletons e redimensionamento/deleção.

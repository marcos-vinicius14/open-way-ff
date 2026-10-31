---
phase: 03-editor-visual-de-teclas-overlay-wayland
plan: "01"
subsystem: ui
tags: [gtk4, gtk4-layer-shell, cairo, input-region, overlay, wayland, status-pill]

# Dependency graph
requires:
  - phase: 02-comunica-o-com-waydroid-e-gerenciamento-de-perfis
    provides: ProfileManager and Waydroid configuration
provides:
  - WayFireOverlayWindow transparent fullscreen overlay with Gtk4LayerShell integration
  - Dynamic Cairo input region management (empty in game mode, pill only when suspended, fullscreen in edit mode)
  - StatusPill HUD widget with aim state transitions (LOCKED with 1.5s fadeout vs SUSPENDED permanent) and edit button
  - Graceful fallback to standard fullscreen window when Layer Shell protocol is unsupported
affects: [03-02, 03-03, 04-launcher]

actuals:
  tokens: 22000
  tasks: 2
  commits: 1

tech-stack:
  added: [gtk4-layer-shell, cairo, libadwaita]
  patterns: [Dynamic cairo.Region input gating, Gtk4LayerShell pre-realization configuration, GLib timeout lifecycle management]

key-files:
  created:
    - src/wayfire/ui/overlay.py
    - src/wayfire/ui/status_pill.py
    - tests/test_overlay_window.py
  modified:
    - src/wayfire/ui/__init__.py

key-decisions:
  - "D-01: No Modo de Jogo, a superfície Layer Shell define sua região de entrada como cairo.Region() vazia para 100% pass-through de cliques ao Waydroid; no Modo de Edição a região é None (tela cheia interativa)."
  - "D-02: Alternância de modo híbrida suportando atalhos e banner flutuante StatusPill discreto no topo quando o mouse é suspenso (F1)."
  - "D-04: Janela configurada em Gtk4LayerShell.Layer.OVERLAY ancorada nas 4 bordas com exclusive_zone = -1 e fallback gracioso fullscreen."
  - "D-12: StatusPill com feedback verde '🎯 MIRA TRAVADA' com fadeout suave de 1.5s e amarelo permanente '🔓 MOUSE LIVRE [F1]' com botão '⚙️ Editar Teclas'."

patterns-established:
  - "Gtk4LayerShell Pre-Realization Setup: Toda configuração de camada e âncoras é executada no __init__ antes de qualquer mapeamento ou realização de janela."
  - "compute_input_region_description(): Método determinístico de descrição de regiões Cairo para validação e testes herméticos."

requirements-completed: ["UI-01"]

## Self-Check: PASSED
---

# Plan 03-01: Overlay Wayland Layer Shell, Cairo Input Region, Alternância Híbrida e Status Pill - Summary

Implementação da camada fundamental de interface visual transparente Wayland para o WayFire:
- **`WayFireOverlayWindow` (`src/wayfire/ui/overlay.py`)**: Janela GTK4 fullscreen com integração direta a `gtk4-layer-shell` na camada `OVERLAY`, exclusiva (-1) e ancorada em todas as bordas. Gerencia regiões de entrada Cairo dinâmicas:
  - `GAME_LOCKED`: `cairo.Region()` vazia e `KeyboardMode.NONE` (pass-through total de cliques e teclas para o Waydroid sem latência).
  - `GAME_SUSPENDED`: `cairo.Region(pill_rect)` interceptando cliques apenas no banner da StatusPill (99% da tela permanece pass-through).
  - `EDIT_MODE`: `surface.set_input_region(None)` e `KeyboardMode.ON_DEMAND` para interação direta com os widgets e alças.
- **`StatusPill` (`src/wayfire/ui/status_pill.py`)**: Widget flutuante no topo com animação de fadeout em 1.5s para trava de mira e persistência em mouse suspenso com botão de acesso ao editor.
- **Suíte de Testes Hermética (`tests/test_overlay_window.py`)**: 6 testes cobrindo todas as transições de modo, regiões cairo, fallback fullscreen, cálculo geométrico do pill e acionamento de callbacks.

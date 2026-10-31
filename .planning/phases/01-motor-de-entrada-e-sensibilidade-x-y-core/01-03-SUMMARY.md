---
phase: 01-motor-de-entrada-e-sensibilidade-x-y-core
plan: 03
status: complete
tasks_completed: 2
tasks_total: 2
files_created:
  - src/wayfire/config/__init__.py
  - src/wayfire/config/profile.py
  - src/wayfire/ui/__init__.py
  - src/wayfire/ui/terminal_hud.py
  - src/wayfire/cli/__init__.py
  - src/wayfire/cli/main.py
  - src/wayfire/__main__.py
  - tests/test_config.py
  - tests/test_cli.py
files_modified:
  - src/wayfire/core/aim_engine.py
  - tests/test_aim_engine.py
requirements:
  - CORE-01
  - CORE-02
  - CORE-03
  - CORE-04
---

# Plan 01-03: Algoritmo Anti-Borda 360°, TUI de Calibração e Ferramenta CLI - Summary

## Overview

Este plano concluiu a implementação do motor da Fase 1, integrando todas as camadas de entrada em uma ferramenta competitiva pronta para uso em partidas:
1. Componente `AimEngine` com algoritmo anti-borda disparando ciclo atômico de recentralização invisível de 1ms ao atingir 75% do raio virtual da tela (D-05, D-06), garantindo giro contínuo de 360° sem travar nas bordas físicas nem causar puxões reversos de mira.
2. Coordenadas da zona de mira e âncora normalizadas em valores percentuais (0.0 a 1.0) para suporte universal a qualquer resolução nativa ou esticada (D-07).
3. Integração de disparo no clique do botão esquerdo (`BTN_LEFT`) injetado via Slot 1 multitouch no botão de tiro do HUD de forma isolada da mira no Slot 0 (D-16, D-08).
4. Gerenciamento e serialização de perfis JSON em `~/.config/wayfire/profiles/default_freefire.json` via modelo dataclass `WayFireProfile`.
5. Interface TUI em tempo real no terminal (`TerminalHUD`) com formatação ANSI in-place (`\r\033[K`) exibindo status `[🟢 AIM LOCKED]`, sensibilidades X/Y, deltas de mouse e contador de resets anti-borda (D-13).
6. Calibração ao vivo da sensibilidade durante o jogo via atalhos de teclado `F7`/`F8` ($Sens_X$) e `F9`/`F10` ($Sens_Y$) em passos de 0.05 com auto-persistência no JSON ativo (D-14).
7. Ponto de entrada CLI modular `wayfire run` e `wayfire test` com suporte a execução direta (`python -m wayfire`) (D-15).

## Tasks Executed

### Task 1: Algoritmo anti-borda de 360° infinito com gatilho a 75% e disparo no botão esquerdo (Slot 1)
- Implementada classe `AimEngine` em `src/wayfire/core/aim_engine.py`.
- Integrada chamada de `reset_slot_cycle` na âncora aos 75% do raio virtual da tela touch.
- Mapeado clique esquerdo do mouse para o Slot 1 multitouch nas coordenadas do botão de tiro.
- Expandida suíte `tests/test_aim_engine.py` com testes de anti-borda a 75%, rotação contínua em 150 ciclos e concorrência Slot 0/Slot 1.
- **Commit:** `c92f82e feat(01-03): implement 360 anti-border reset and fire button trigger`

### Task 2: Gerenciamento de perfil JSON, painel TUI ao vivo com calibração F7-F10 e comandos CLI (wayfire)
- Criado pacote `src/wayfire/config` e classe `WayFireProfile` com persistência JSON.
- Criado pacote `src/wayfire/ui` e classe `TerminalHUD` com renderização ANSI in-place.
- Implementada rotina `handle_calibration_hotkey` com passos de 0.05 e clamp inferior em 0.05.
- Criado pacote `src/wayfire/cli` e ponto de entrada `src/wayfire/__main__.py` com subcomandos `run` e `test`.
- Criadas suítes de teste `tests/test_config.py` e `tests/test_cli.py`.
- **Commit:** `9513eb4 feat(01-03): implement profile persistence, interactive terminal hud and cli`

## Verification & Test Results

Comando executado: `.venv/bin/pytest tests/ -v`
Resultado: 27/27 testes passaram em toda a suíte do projeto com 100% de sucesso.
- `tests/test_aim_engine.py`: 8/8 PASSED
- `tests/test_cli.py`: 6/6 PASSED
- `tests/test_config.py`: 2/2 PASSED
- `tests/test_mouse_capture.py`: 5/5 PASSED
- `tests/test_touch_injector.py`: 6/6 PASSED

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

---
phase: 01-motor-de-entrada-e-sensibilidade-x-y-core
plan: 02
status: complete
tasks_completed: 2
tasks_total: 2
files_created:
  - src/wayfire/core/mouse_capture.py
  - src/wayfire/core/aim_engine.py
  - tests/test_mouse_capture.py
  - tests/test_aim_engine.py
requirements:
  - CORE-02
  - CORE-03
---

# Plan 01-02: Captura de Periféricos (Mouse/Teclado) e Motor de Sensibilidade X/Y - Summary

## Overview

Este plano entregou a camada de controle de hardware e o processamento matemático de mira:
1. Autodetecção inteligente de mouse físico e teclado em `/dev/input/event*`, rejeitando automaticamente touchpads, trackpoints e tablets com `EV_ABS` (D-02).
2. Gerenciador de captura e multiplexação I/O com `selectors.DefaultSelector` sobre descritores epoll e controle de trava exclusiva via `ioctl EVIOCGRAB` (`mouse_dev.grab()` / `ungrab()`) (D-03).
3. Alternância instantânea de cursor através da hotkey configurável `F1` (D-01), iniciando estritamente no estado suspenso para navegação em menus (D-04).
4. Proteção contra host lockout através de handlers de terminação para `SIGINT` e `SIGTERM` garantindo `ungrab()` defensivo incondicional.
5. Motor matemático `AimProcessor` em `src/wayfire/core/aim_engine.py` com multiplicadores assimétricos independentes $Sens_X$ e $Sens_Y$ calibrados para Free Fire ("puxada de capa") (D-09).
6. Acumulador fracionário de subpixel para eliminação de pixel-skipping em micro-mira (D-11), filtro de atenuação de jitter exponencial (EMA) (D-10) e suporte a inversão vertical de eixo (D-12).

## Tasks Executed

### Task 1: Captura de baixo nível com detecção inteligente de periféricos e ciclo resiliente de trava/destrava (F1)
- Implementada função `detect_input_devices()` em `src/wayfire/core/mouse_capture.py`.
- Implementada classe `InputCaptureManager` com callbacks para movimento, botões e hotkeys.
- Desenvolvida suíte unitária `tests/test_mouse_capture.py` cobrindo filtragem de touchpads, estado suspenso inicial, alternância no F1, descarte de deltas quando suspenso e cleanup seguro.
- **Commit:** `3fb9881 feat(01-02): implement peripheral capture and exclusive grab management`

### Task 2: Motor matemático de sensibilidade independente X/Y, acumulador de subpixel e filtro EMA anti-jitter
- Implementada classe `AimProcessor` em `src/wayfire/core/aim_engine.py` com pipeline: Inversão Y -> Filtro EMA -> Sensibilidade X/Y -> Acumulador de Subpixel -> Truncamento inteiro -> Preservação de resto decimal.
- Desenvolvida suíte unitária `tests/test_aim_engine.py` validando proporcionalidade assimétrica X/Y, preservação fracionária subpixel, atenuação de jitter EMA, inversão de eixo Y e limpeza de resíduo.
- **Commit:** `4d7f3e5 feat(01-02): implement independent x/y sensitivity, subpixel and ema filter`

## Verification & Test Results

Comando executado: `.venv/bin/pytest tests/test_mouse_capture.py tests/test_aim_engine.py -v`
Resultado: 10/10 testes passaram com 100% de sucesso.
- `test_detect_input_devices_filters_touchpads`: PASSED
- `test_initial_state_is_suspended`: PASSED
- `test_f1_toggle_grab_ungrab`: PASSED
- `test_mouse_deltas_ignored_when_suspended`: PASSED
- `test_cleanup_guarantees_ungrab`: PASSED
- `test_sensitivity_scaling_independent`: PASSED
- `test_subpixel_accumulation_preserves_micro_movements`: PASSED
- `test_ema_smoothing_attenuates_jitter`: PASSED
- `test_invert_y_toggle`: PASSED
- `test_reset_state_clears_residue`: PASSED

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

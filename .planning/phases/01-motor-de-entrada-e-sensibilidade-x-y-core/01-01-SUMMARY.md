---
phase: 01-motor-de-entrada-e-sensibilidade-x-y-core
plan: 01
status: complete
tasks_completed: 2
tasks_total: 2
files_created:
  - pyproject.toml
  - src/wayfire/__init__.py
  - src/wayfire/core/__init__.py
  - src/wayfire/core/touch_injector.py
  - tests/__init__.py
  - tests/conftest.py
  - tests/test_touch_injector.py
requirements:
  - CORE-01
---

# Plan 01-01: Dispositivo Virtual Multitouch (/dev/uinput) e Injetor de Toque - Summary

## Overview

Este plano implementou a fundação estrutural e de baixo nível do WayFire:
1. Scaffold completo do projeto Python conforme PEP 621 em `pyproject.toml` com empacotamento modular (`src/wayfire`) e dependências fixadas (`evdev>=1.7.0,<=2.0.0`, `pytest>=8.0.0`).
2. Abstração de injeção de toques com protocolo Multi-Touch Type B nativo do Linux Kernel via `/dev/uinput` com propriedade direta `INPUT_PROP_DIRECT` e slots 0 a 9.
3. Isolamento arquitetural estrito do Slot 0 para controle contínuo da mira (D-08) e alocação dinâmica dos slots 1 a 9 para botões de disparo e ação.
4. Primitiva de reset atômico anti-borda com ciclo UP -> sleep(1ms) -> DOWN em novo ponto de âncora (D-05), garantindo ausência de puxão reverso brusco no subsistema de entrada do Android.
5. Suíte de testes unitários herméticos com mock de `UInput` em `tests/test_touch_injector.py`.

## Tasks Executed

### Task 1: Tracer — Scaffold do projeto e injeção ponta a ponta de eventos multitouch virtuais
- Criado `pyproject.toml` com setuptools e configuração do pytest.
- Criada a árvore de pacotes `src/wayfire`, `src/wayfire/core` e `tests`.
- Implementada a interface `UInputSink`, `MockUInputSink` e classe `TouchInjector` em `src/wayfire/core/touch_injector.py`.
- Criado teste tracer `test_tracer_touch_injection_lifecycle` em `tests/test_touch_injector.py`.
- **Commit:** `7f29b19 feat(01-01): scaffold project and multitouch injection`

### Task 2: Gerenciamento completo de slots multitouch, isolamento do Slot 0 e primitiva de reset atômico de 1ms
- Adicionados métodos `allocate_slot()` e `release_slot()` isolando `CAMERA_SLOT = 0` e gerenciando slots 1 a 9.
- Implementado `reset_slot_cycle(slot, anchor_x, anchor_y, pause_sec=0.001)` para reset invisível de 1ms.
- Implementado clamp de coordenadas nas bordas `[0, width]` e `[0, height]`.
- Adicionado suporte a context manager (`__enter__`/`__exit__`) para liberação segura de todos os toques ativos.
- Expandida suíte de testes cobrindo concorrência multislot, alocação/reserva, timing de reset, clamp e context manager.

## Verification & Test Results

Comando executado: `.venv/bin/pytest tests/test_touch_injector.py -v`
Resultado: 6/6 testes passaram com 100% de sucesso.
- `test_tracer_touch_injection_lifecycle`: PASSED
- `test_multislot_concurrent_touches`: PASSED
- `test_slot_reservation_and_allocation`: PASSED
- `test_reset_slot_cycle_timing_and_events`: PASSED
- `test_coordinate_clamping`: PASSED
- `test_context_manager_cleanup`: PASSED

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

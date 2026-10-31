---
phase: 02-comunica-o-com-waydroid-e-gerenciamento-de-perfis
plan: "01"
subsystem: waydroid
tags: [waydroid, lifecycle, uinput, scaling, spoofing, cli]

# Dependency graph
requires:
  - phase: 01-motor-de-entrada-e-sensibilidade-x-y-core
    provides: TouchInjector and AimEngine core modules
provides:
  - WaydroidController lifecycle management with clean environment isolation
  - Stretched resolution presets (1440x1080 4:3) with idempotent switching and automatic session restart
  - ASUS ROG Phone 5 hardware spoofing with automatic backup and restore
  - Dynamic screen dimension scaling in TouchInjector and AimEngine
  - CLI subcommands wayfire launch, wayfire stop, and wayfire spoof
affects: [02-02, 03-overlay, 04-launcher]

actuals:
  tokens: 18500
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns: [Decoupled CommandRunner protocol with hermetic MockCommandRunner, environment sanitation stripping virtualenv pollution]

key-files:
  created:
    - src/wayfire/waydroid/__init__.py
    - src/wayfire/waydroid/controller.py
    - tests/test_waydroid_controller.py
    - tests/test_scaling.py
  modified:
    - src/wayfire/core/touch_injector.py
    - src/wayfire/core/aim_engine.py
    - src/wayfire/cli/main.py
    - tests/test_cli.py

key-decisions:
  - "D-01..D-04: WaydroidController supervisiona contêiner e sessão com polling e comandos desacoplados, isolando chamadas do host do virtualenv Python."
  - "D-05..D-08: Resoluções esticadas 4:3 (1440x1080) aplicadas de forma idempotente com reinício transparente de sessão e reescalonamento dinâmico em tempo de execução no TouchInjector e AimEngine."
  - "D-09..D-12: Injeção de 5 propriedades ASUS ROG Phone 5 com backup automático em ~/.config/wayfire/device_backup.json e capacidade de restauração."

patterns-established:
  - "CommandRunner Protocol: Desacoplamento de subprocessos permitindo testes herméticos sem dependência de Waydroid em tempo de CI/teste."
  - "get_clean_env(): Remoção sistemática de poluição de virtualenv para invocação confiável do executável de sistema /usr/bin/waydroid."

requirements-completed: ["WAY-01", "WAY-02", "WAY-03"]

coverage:
  - id: D1
    description: "WaydroidController supervisiona inicialização assíncrona, parada graciosa e detecção automática de pacotes Free Fire"
    requirement: "WAY-01"
    verification:
      - kind: unit
        ref: "tests/test_waydroid_controller.py#test_tracer_waydroid_controller_lifecycle"
        status: pass
    human_judgment: false
  - id: D2
    description: "Aplicação idempotente de resoluções esticadas e escalonamento dinâmico no TouchInjector e AimEngine"
    requirement: "WAY-02"
    verification:
      - kind: unit
        ref: "tests/test_scaling.py#test_touch_injector_dynamic_dimensions"
        status: pass
      - kind: unit
        ref: "tests/test_scaling.py#test_aim_engine_dynamic_dimensions"
        status: pass
      - kind: unit
        ref: "tests/test_waydroid_controller.py#test_set_resolution_idempotent"
        status: pass
    human_judgment: false
  - id: D3
    description: "Hardware spoofing ASUS ROG Phone 5 com backup automático e restauração"
    requirement: "WAY-03"
    verification:
      - kind: unit
        ref: "tests/test_waydroid_controller.py#test_spoofing_backup_and_apply"
        status: pass
      - kind: unit
        ref: "tests/test_waydroid_controller.py#test_restore_spoofing"
        status: pass
    human_judgment: false
  - id: D4
    description: "Subcomandos CLI wayfire launch, stop e spoof expostos e operacionais"
    requirement: "WAY-01"
    verification:
      - kind: unit
        ref: "tests/test_cli.py#test_cli_launch_stop_spoof_argument_parsing"
        status: pass
      - kind: unit
        ref: "tests/test_cli.py#test_cmd_launch_execution_order"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-10-31
status: complete
---

# Plan 02-01: Waydroid Controller, Resoluções Esticadas, Spoofing ROG Phone e Escalonamento Dinâmico Summary

**Controlador completo do ciclo de vida do Waydroid implementado com isolamento de ambiente virtualenv, resoluções esticadas 4:3 idempotentes, hardware spoofing ASUS ROG Phone 5 com backup, escalonamento dinâmico de coordenadas e novos subcomandos na CLI.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-10-31T13:16:00Z
- **Completed:** 2026-10-31T13:24:00Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments

- Desenvolvido `WaydroidController` com protocolo desacoplado `CommandRunner` e sanitização de variáveis de ambiente (`get_clean_env`), viabilizando supervisão assíncrona de sessão, verificação de contêiner e detecção automática de variantes do Free Fire (Standard/MAX).
- Implementadas resoluções esticadas competitivas (1440x1080 e 1024x768 4:3) com verificação idempotente e reinício transparente de sessão gráfica Waydroid.
- Adicionado método `set_screen_dimensions` em `TouchInjector` e `AimEngine` para recálculo instantâneo em tempo de execução de limites de pixels e âncoras normalizadas.
- Implementado hardware spoofing ASUS ROG Phone 5 (`ASUS_I005D`) com backup prévio automático em `~/.config/wayfire/device_backup.json` e rotina de restauração.
- Integrados subcomandos `wayfire launch`, `wayfire stop` e `wayfire spoof` na CLI com suporte completo a flags e mensagens limpas no terminal.

## Task Commits

Each task was committed atomically:

1. **Task 1: Tracer — CommandRunner Protocol, Mock hermético e ciclo de vida do WaydroidController (WAY-01)** - `1d1f277` (feat)
2. **Task 2: Resoluções esticadas competitivas (WAY-02), spoofing ROG Phone (WAY-03) e escalonamento dinâmico no Core** - `d917486` (feat)
3. **Task 3: Subcomandos CLI (launch, stop, spoof) e integração de inicialização** - `0f9f09e` (feat)

**Plan metadata:** `docs(02-01): complete plan 02-01 summary` (docs)

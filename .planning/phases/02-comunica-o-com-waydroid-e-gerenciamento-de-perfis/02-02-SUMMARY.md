---
phase: 02-comunica-o-com-waydroid-e-gerenciamento-de-perfis
plan: "02"
subsystem: config
tags: [profile, widgets, polymorphic, crud, security, cli]

# Dependency graph
requires:
  - phase: 02-01
    provides: WaydroidController and stretched resolutions
provides:
  - Polymorphic widget modeling (BaseWidget, TapWidget, DPadWidget, AimWidget, FireWidget) with WidgetFactory
  - WayFireProfile hierarchical schema with transparent Phase 1 backward compatibility and auto-migration
  - Game-ready factory default profile default_freefire.json with 14 essential competitive buttons
  - ProfileManager providing complete CRUD operations, active profile tracking, and path traversal protection
  - CLI subcommands wayfire profile list, active, show, import, export, and delete
affects: [03-overlay, 04-launcher]

actuals:
  tokens: 21000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns: [Polymorphic serialization using WidgetFactory registry, strict path traversal defense via regex stem sanitization]

key-files:
  created:
    - src/wayfire/config/widgets.py
    - src/wayfire/config/profile_manager.py
    - tests/test_profile_manager.py
  modified:
    - src/wayfire/config/profile.py
    - src/wayfire/cli/main.py
    - tests/test_cli.py

key-decisions:
  - "D-13..D-15: Hierarchical profile schema with ResolutionConfig, MouseSettingsConfig, UISettingsConfig, and 14-button factory default profile default_freefire.json, retaining 100% Phase 1 property backward compatibility."
  - "D-14: Polymorphic widgets (TapWidget, DPadWidget, AimWidget, FireWidget) serialized and deserialized via WidgetFactory discriminated by 'type'."
  - "D-16: ProfileManager providing CRUD, active profile selection, and directory traversal defense in ~/.config/wayfire/profiles/."

patterns-established:
  - "WidgetFactory: Registry-based discriminator pattern allowing dynamic registration and type validation of on-screen HUD widgets."
  - "sanitize_profile_name: Regex stem extraction stripping path traversal sequences and invalid characters."

requirements-completed: ["MAP-01"]

coverage:
  - id: D1
    description: "Hierarquia polimórfica de widgets e fábrica discriminada por tipo"
    requirement: "MAP-01"
    verification:
      - kind: unit
        ref: "tests/test_profile_manager.py#test_polymorphic_widgets_serialization"
        status: pass
      - kind: unit
        ref: "tests/test_profile_manager.py#test_widget_factory_validation_errors"
        status: pass
    human_judgment: false
  - id: D2
    description: "Perfil de fábrica default_freefire.json com 14 botões essenciais e retrocompatibilidade com Fase 1"
    requirement: "MAP-01"
    verification:
      - kind: unit
        ref: "tests/test_profile_manager.py#test_default_profile_structure"
        status: pass
      - kind: unit
        ref: "tests/test_profile_manager.py#test_legacy_profile_migration"
        status: pass
      - kind: unit
        ref: "tests/test_config.py#test_profile_serialization"
        status: pass
    human_judgment: false
  - id: D3
    description: "ProfileManager com CRUD completo, active profile e proteção contra path traversal"
    requirement: "MAP-01"
    verification:
      - kind: unit
        ref: "tests/test_profile_manager.py#test_profile_manager_crud_and_factory_default"
        status: pass
      - kind: unit
        ref: "tests/test_profile_manager.py#test_profile_manager_factory_protection"
        status: pass
      - kind: unit
        ref: "tests/test_profile_manager.py#test_profile_manager_path_traversal_protection"
        status: pass
      - kind: unit
        ref: "tests/test_profile_manager.py#test_profile_manager_active_profile_switching"
        status: pass
      - kind: unit
        ref: "tests/test_profile_manager.py#test_profile_manager_import_export"
        status: pass
    human_judgment: false
  - id: D4
    description: "Subcomandos CLI wayfire profile list, active, show, import, export, delete"
    requirement: "MAP-01"
    verification:
      - kind: unit
        ref: "tests/test_cli.py#test_cli_profile_subcommands"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-10-31
status: complete
---

# Plan 02-02: Widgets Polimórficos, Perfil de Fábrica default_freefire.json, ProfileManager e Migração de Schema Summary

**Arquitetura polimórfica de widgets para o HUD implementada com schema hierárquico moderno, migração transparente da Fase 1, perfil de fábrica default_freefire.json com 14 botões essenciais, gerenciador ProfileManager com proteção contra path traversal e subcomandos CLI de perfil.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-10-31T13:24:00Z
- **Completed:** 2026-10-31T13:31:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Modelagem tipada de widgets polimórficos (`BaseWidget`, `TapWidget`, `DPadWidget`, `AimWidget`, `FireWidget`) com validação estrita e fábrica discriminada `WidgetFactory.from_dict()`.
- Refatoração do modelo `WayFireProfile` para schema hierárquico (`resolution`, `mouse_settings`, `ui_settings`, `widgets`), com suporte bidirecional completo e retrocompatibilidade com atributos da Fase 1 (`test_config.py` passa 100% sem alterações).
- Construção do perfil de fábrica `default_freefire.json` em 1440x1080 com todos os 14 botões de jogo competitivo mapeados (mira, tiro, dpad WASD, pular, agachar, deitar, recarregar, mira telescópica, kit, granada, interagir e 3 slots de arma).
- Implementação da classe `ProfileManager` em `~/.config/wayfire/profiles/` com sanitização regex contra path traversal, proteção contra remoção do perfil padrão de fábrica e gestão de perfil ativo.
- Exposição dos subcomandos CLI `wayfire profile` (`list`, `active`, `show`, `import`, `export`, `delete`) e integração automática com `wayfire run` para carregar o perfil ativo do usuário.

## Task Commits

Each task was committed atomically:

1. **Task 1: Modelagem de widgets polimórficos, schema hierárquico e perfil de fábrica default_freefire.json (MAP-01)** - `cdea5b2` (feat)
2. **Task 2: ProfileManager (CRUD, active profile, import/export sanitizado) e subcomandos CLI (MAP-01)** - `a5ee661` (feat)

**Plan metadata:** `docs(02-02): complete plan 02-02 summary` (docs)

---
phase: "04"
plan: "02"
subsystem: ui
tags: [gtk4, libadwaita, launcher, desktop, hero-banner, sliders, capa-badge, diagnostics, waydroid, logs]

requires:
  - phase: "04"
    plan: "01"
    provides: "GameSessionCoordinator e proteção anti-bug do analógico"
provides:
  - "Janela principal WayFireLauncherWindow em GTK4 e Libadwaita com tema Dark forçado"
  - "Hero Banner com botão dinâmico Jogar/Parar, animação de spinner e status do boot"
  - "Sliders contínuos de Sensibilidade X e Y sincronizados bidirecionalmente com SpinButtons"
  - "Badge dinâmico de Proporção de Capa em tempo real com destaque para razões >= 2.0x"
  - "Botões estilo Pill para seleção de resolução nativa 1080p e esticada 1440x1080 / 1024x768"
  - "Painel de saúde do sistema monitorando os 4 pilares (Waydroid, uinput, ROG Phone, Resolução) com auto-fix"
  - "Diálogo WayFireLogDialog para visualização de logs e cópia para área de transferência"
  - "Subcomando CLI 'wayfire launcher' e inicialização padrão sem argumentos"
affects: ["distribution", "packaging"]

actuals:
  tokens: 22000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Janela Adw.ApplicationWindow com ToolbarView, Clamp e estilos CSS customizados"
    - "Sincronização bidirecional entre Gtk.Scale e Gtk.SpinButton com precisão de 0.05"
    - "Cálculo reativo da proporção de sensibilidade vertical/horizontal (Y/X) com badge visual de capa"
    - "Ocultação da janela durante partida e restauração limpa ao finalizar"
    - "Diagnóstico periódico não bloqueante dos 4 pilares essenciais do sistema"

key-files:
  created:
    - "src/wayfire/ui/launcher_window.py"
    - "src/wayfire/ui/log_dialog.py"
    - "tests/test_launcher_window.py"
    - "tests/test_launcher_diagnostics.py"
    - "tests/test_log_dialog.py"
  modified:
    - "src/wayfire/ui/__init__.py"
    - "src/wayfire/cli/main.py"
    - "tests/test_cli.py"

key-decisions:
  - "Tema Dark forçado e gradiente de fogo WayFire (#ff5722 a #e64a19) para o botão principal de ação"
  - "Sliders contínuos X e Y sincronizados com SpinButtons com precisão de 0.05 e hot-reload imediato per D-02 e D-08"
  - "Badge dinâmico de Proporção de Capa classificando a razão Y/X em Ideal (>=2.0x), Equilibrada (>=1.4x) e Padrão (<1.4x)"
  - "Pills de resolução com 1 clique (1080p Nativo, 1440x1080 Esticado [Comp] e 1024x768 Esticado) destacando a opção ativa"
  - "Ocultação automática da janela principal ao entrar em RUNNING e restauração imediata ao retornar para STOPPED per D-05"
  - "Painel de integridade com 4 pilares (serviço Waydroid, uinput, spoofing ROG e resolução) com auto-fix e instruções modais"
  - "Diálogo WayFireLogDialog integrado com cópia 1-clique para clipboard per D-16"
  - "Entrada padrão 'wayfire' ou 'wayfire launcher' abrindo a Central de Jogos GTK4"

patterns-established:
  - "Despacho assíncrono thread-safe entre GameSessionCoordinator e widgets GTK via GLib"
  - "Detecção e sanitização de logs com isolamento contra travamento da UI"

requirements-completed: ["UI-03"]

coverage:
  - id: D-04-02-HERO-SLIDERS
    description: "Hero Banner com botão dinâmico Jogar/Parar, sliders X/Y sincronizados e badge de capa"
    requirement: "UI-03"
    verification:
      - kind: unit
        ref: "tests/test_launcher_window.py#test_launcher_window_initialization"
        status: pass
      - kind: unit
        ref: "tests/test_launcher_window.py#test_sensitivity_sliders_and_spinbuttons_sync"
        status: pass
      - kind: unit
        ref: "tests/test_launcher_window.py#test_capa_badge_calculation"
        status: pass
      - kind: unit
        ref: "tests/test_launcher_window.py#test_action_button_state_transitions"
        status: pass
      - kind: unit
        ref: "tests/test_launcher_window.py#test_window_hides_on_play_and_restores_on_stop"
        status: pass
    human_judgment: false
  - id: D-04-02-PILLS-PROFILES
    description: "Pills de resolução e dropdown de perfis"
    requirement: "UI-03"
    verification:
      - kind: unit
        ref: "tests/test_launcher_window.py#test_resolution_pill_selection_updates_profile"
        status: pass
    human_judgment: false
  - id: D-04-02-HEALTH-LOGS-CLI
    description: "Painel de saúde em 4 pilares com auto-fix, diálogo de logs e CLI wayfire launcher"
    requirement: "UI-03"
    verification:
      - kind: unit
        ref: "tests/test_launcher_diagnostics.py#test_health_card_pillars_status_green"
        status: pass
      - kind: unit
        ref: "tests/test_launcher_diagnostics.py#test_health_card_waydroid_inactive_shows_auto_fix"
        status: pass
      - kind: unit
        ref: "tests/test_launcher_diagnostics.py#test_health_card_uinput_permission_shows_instructions_dialog"
        status: pass
      - kind: unit
        ref: "tests/test_log_dialog.py#test_log_dialog_appends_and_copies_to_clipboard"
        status: pass
      - kind: unit
        ref: "tests/test_cli.py#test_cli_launcher_subcommand_and_default"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-10-31
status: complete
---

# Plan 04-02: Launcher Desktop em GTK4 / Libadwaita Summary

**Central de Jogos WayFire implementada em GTK4 e Libadwaita com Hero Banner 1-clique Jogar/Parar, sliders X/Y sincronizados com badge de capa em tempo real, botões de resolução pill, painel de saúde em 4 pilares com auto-fix, visualizador de logs e integração CLI.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-10-31T19:25:00Z
- **Completed:** 2026-10-31T19:45:00Z
- **Tasks:** 2 completed
- **Files modified:** 3 modified, 5 created

## Accomplishments

- **WayFireLauncherWindow:** Janela moderna em Libadwaita com tema Dark forçado e paleta de fogo (#ff5722 / #e64a19), integrando todos os motores do WayFire em uma experiência unificada.
- **Hero Banner Interativo:** Botão dinâmico que alterna entre `"🔥 JOGAR FREE FIRE"` (com spinner animado e mensagens de boot) e `"⏹ PARAR JOGO"`, com minimização automática da janela durante a partida e restauração imediata ao término.
- **Sliders X/Y e Badge de Capa:** Sliders contínuos sincronizados com precisão de 0.05 com SpinButtons, calculando em tempo real a razão vertical/horizontal com badge destacando a faixa ideal para subida de capa (>=2.0x) e hot-reload ao vivo no `AimProcessor`.
- **Resolução em Pills e Seletor de Perfis:** Seleção com 1 clique de resolução 1080p Nativa, 1440x1080 Esticado [Comp] e 1024x768 Esticado, além de gerenciamento e carregamento de perfis.
- **Diagnóstico de Saúde em 4 Pilares:** Monitoramento visual de status (Waydroid, uinput, Spoofing ROG Phone e Resolução) com botões de auto-correção e diálogos com comandos copiáveis.
- **Visualizador de Logs e CLI:** Diálogo `WayFireLogDialog` com cópia 1-clique para o clipboard e suporte aos comandos `wayfire launcher` e `wayfire` (sem argumentos).

## Task Commits

Each task was committed atomically:

1. **Task 1: Launcher Desktop UI em GTK4 / Libadwaita** - `ea565c7` (feat)
2. **Task 2: Painel de Saúde do Sistema, Diálogo de Logs e Integração CLI** - `2405a89` (feat)

**Plan metadata:** `pending commit` (docs: complete plan 04-02)

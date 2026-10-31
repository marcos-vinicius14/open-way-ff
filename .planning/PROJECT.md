# WayFire 🔥

## What This Is

WayFire é uma camada de software nativa em Python projetada para transformar o ecossistema do Waydroid em uma experiência de emulação Android completa, especializada em jogos competitivos de tiro — com foco primário no Free Fire. O projeto opera como um companion/wrapper de alto desempenho sobre o kernel Linux, eliminando a sobrecarga de VMs tradicionais e fornecendo latência quase zero (<1ms), resposta direta de GPU e taxa máxima de FPS.

## Core Value

Emulação competitiva de Free Fire no Linux com controle absoluto de Sensibilidade X e Y independente ("puxada de capa"), injeção direta de toques via `/dev/uinput` com latência instantânea (<1ms) e editor visual de mapeamento de teclas intuitivo estilo GG Mouse Pro.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] **CORE-01**: Injetor de toque virtual multitouch de baixa latência (<1ms) via Linux Kernel `/dev/uinput` (`python-evdev`).
- [ ] **CORE-02**: Captura de baixo nível de mouse e teclado com hotkey de trava/destrava do cursor (suspender mouse).
- [ ] **CORE-03**: Motor de sensibilidade horizontal (X) e vertical (Y) com multiplicador independente para subida de capa.
- [ ] **CORE-04**: Algoritmo anti-borda com recentralização invisível de toque (1ms) para rotação contínua e infinita de câmera 360°.
- [ ] **WAY-01**: Controlador de ciclo de vida do Waydroid (iniciar, parar contêiner e sessão, lançamento direto de app).
- [ ] **WAY-02**: Gerenciamento dinâmico de resoluções de tela competitivas (1920x1080 16:9, 1440x1080 e 1024x768 esticado 4:3).
- [ ] **WAY-03**: Spoofing de propriedades de hardware (ASUS ROG Phone) para desbloquear 90/120 FPS e gráficos no Ultra no Free Fire.
- [ ] **MAP-01**: Gerenciador de perfis JSON em `~/.config/wayfire/profiles/` com importação, exportação e perfil padrão competitivo.
- [ ] **MAP-02**: Componentes de mapeamento customizáveis: TapButton (Single/Hold/Turbo), DPad analógico WASD, AimController (mira/câmera) e FireButton (gatilho).
- [ ] **MAP-03**: Algoritmo de proteção contra o bug do analógico com reset suave ao suspender mouse.
- [ ] **UI-01**: Overlay transparente Wayland (GTK4 / Layer Shell) para visualização OSD com controle de opacidade (0% a 100%).
- [ ] **UI-02**: Modo de edição interativo estilo GG Mouse Pro (duplo clique cria bolinha em escuta, captura instantânea da próxima tecla física, arrastar/soltar, exclusão e redimensionamento).
- [ ] **UI-03**: Launcher principal estilo central de jogos com sliders de sensibilidade X/Y, seletor de resolução em 1 clique, seletor de perfis e botão "Jogar Free Fire".
- [ ] **PKG-01**: Script de instalação automatizada em um comando (`install.sh`) com configuração de permissões udev para `/dev/uinput`.
- [ ] **PKG-02**: Empacotamento oficial para Arch Linux / AUR (`PKGBUILD`).

### Out of Scope

- **Máquinas virtuais QEMU/VirtualBox**: Rejeitado — o foco exclusivo é contêiner LXC nativo via Waydroid para latência zero.
- **Injeção de toque via ADB (`adb shell input tap`)**: Rejeitado — latência inaceitável (~100-200ms) para jogos competitivos.
- **Servidores Scrcpy**: Rejeitado — dependência de conexão ADB e overhead desnecessário comparado ao uinput nativo.
- **Compositores X11 legados**: Rejeitado — foco exclusivo em compositores modernos Wayland (Hyprland, Sway, GNOME Wayland, KDE Wayland).
- **Cheats / Hacks de memória**: Rejeitado — o software atua estritamente como mapeador de periféricos e orquestrador do sistema.

## Context

- **Arquitetura**: Companion no host Linux comunicando-se com Waydroid via CLI/propriedades e com o kernel Linux via `/dev/uinput`.
- **Compositor**: Wayland repassa eventos de dispositivos virtuais do kernel diretamente para o contêiner LXC sem intermediários.
- **Mapeamento GG Mouse Pro**: Padrão de ouro de ergonomia móvel onde o usuário dá duplo clique no HUD e pressiona a tecla física desejada.
- **Free Fire**: Mecânica competitiva fortemente dependente da proporção entre Sensibilidade X (movimento) e Sensibilidade Y (subida de mira para tiros na cabeça / capa).

## Constraints

- **Tecnologia**: Python 3 com `python-evdev`, GTK4, Libadwaita e `gtk4-layer-shell`.
- **Permissões**: Acesso de escrita em `/dev/uinput` e leitura em `/dev/input/event*` (configurado via regras udev / grupo `input`).
- **Desempenho**: Latência de processamento de input <1ms, sem drops de FPS.
- **Compatibilidade**: Waydroid rodando sobre Linux x86_64 com aceleração de hardware (Mesa/VA-API).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Linux `/dev/uinput` multitouch virtual | Latência direta no kernel < 1ms sem overhead de rede ou ADB | — Pending |
| Editor visual com fluxo GG Mouse Pro | Interface mais rápida e intuitiva para mapear teclas sobre o jogo | — Pending |
| Spoofing de ASUS ROG Phone via props | Habilita modos 90 FPS e 120 FPS nas configurações do Free Fire | — Pending |
| Resoluções esticadas 4:3 (1440x1080 / 1024x768) | Alvos e modelos de personagens maiores na tela, padrão competitivo | — Pending |
| Algoritmo anti-borda com reset invisível de 1ms | Permite giro 360° infinito sem esbarrar no limite físico da tela touch | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-10-30 after initialization*

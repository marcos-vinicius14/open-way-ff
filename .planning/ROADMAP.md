# Roadmap: WayFire 🔥

## Overview

O WayFire transforma o Waydroid em uma plataforma de emulação competitiva de alta performance para Free Fire no Linux. A jornada de desenvolvimento segue uma abordagem Vertical MVP em 5 fases: começa no nível mais baixo garantindo injeção de toque ultrarrápida (<1ms) via `/dev/uinput` com calibração de sensibilidade X/Y para puxada de capa (Fase 1); avança para o controle programático do contêiner Waydroid, resolução esticada e spoofing ROG Phone (Fase 2); introduz o editor visual transparente de mapeamento sobre o jogo estilo GG Mouse Pro (Fase 3); consolida um Launcher desktop completo com proteção contra bug do analógico (Fase 4); e finaliza com empacotamento automatizado para distribuições Linux e AUR (Fase 5).

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3, 4, 5): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: Motor de Entrada e Sensibilidade X/Y (Core)** - Injeção de toques virtuais multitouch via `/dev/uinput` e controle de mira com sensibilidade X/Y independente (completed 2026-10-31)
- [x] **Phase 2: Comunicação com Waydroid e Gerenciamento de Perfis** - Orquestração do contêiner Waydroid, resolução esticada, spoofing de 90/120 FPS e perfis JSON (completed 2026-10-31)
- [ ] **Phase 3: Editor Visual de Teclas (Overlay Wayland)** - Overlay transparente GTK4/Layer Shell com criação intuitiva de botões estilo GG Mouse Pro
- [ ] **Phase 4: Launcher Desktop e Polimento Competitivo** - Central estilo BlueStacks em GTK4/Libadwaita e algoritmo de proteção anti-bug do analógico
- [ ] **Phase 5: Empacotamento, Permissões e Distribuição** - Script de instalação automatizada `install.sh`, regras udev e pacote `PKGBUILD` para Arch Linux / AUR

## Phase Details

### Phase 1: Motor de Entrada e Sensibilidade X/Y (Core)

**Goal**: Injetar toques virtuais via `/dev/uinput` com latência instantânea (<1ms) e movimentar a mira com o mouse no Free Fire com sensibilidade X e Y ajustáveis via script CLI.
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: CORE-01, CORE-02, CORE-03, CORE-04
**Success Criteria** (what must be TRUE):
  1. Dispositivo virtual multitouch criado com sucesso em `/dev/uinput` via `python-evdev` e reconhecido pelo sistema e Waydroid como touchscreen nativa.
  2. Cursor do mouse pode ser travado e destravado instantaneamente através de uma tecla configurável de suspender.
  3. Movimento do mouse é convertido em eventos de toque contínuos com Sensibilidade X e Sensibilidade Y ajustáveis independentemente (calibradas para puxada de capa).
  4. Algoritmo anti-borda executa reset de toque invisível em 1ms no centro da tela touch, permitindo rotação 360° infinita da mira sem travar nas bordas.

**Plans**: 3/3 plans complete

Plans:
- [ ] **Wave 1**
  - [x] 01-01: Configuração do ambiente Python e implementação do injetor de toque virtual multitouch via `/dev/uinput` (`touch_injector.py`).
- [ ] **Wave 2** *(blocked on Wave 1 completion)*
  - [x] 01-02: Implementação da captura de mouse de baixo nível, trava de cursor (hotkey suspender) e cálculo de sensibilidade X/Y (`mouse_capture.py` & `aim_engine.py`).
- [ ] **Wave 3** *(blocked on Wave 2 completion)*
  - [x] 01-03: Implementação do algoritmo anti-borda para rotação contínua 360°, disparo integrado e script CLI de teste interativo no Free Fire (`aim_engine.py` & `main.py`).

### Phase 2: Comunicação com Waydroid e Gerenciamento de Perfis

**Goal**: Controlar o ciclo de vida do Waydroid programaticamente, aplicar resoluções esticadas competitivas, aplicar spoofing de dispositivo gamer (ASUS ROG Phone) e gerenciar perfis JSON.
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: WAY-01, WAY-02, WAY-03, MAP-01
**Success Criteria** (what must be TRUE):
  1. Waydroid Controller inicia e finaliza a sessão/contêiner Waydroid e lança o pacote do Free Fire diretamente sem interação manual.
  2. Resolução do contêiner Waydroid é alternada via propriedades do sistema entre Full HD (1920x1080) e resolução competitiva esticada 4:3 (1440x1080 / 1024x768).
  3. Propriedades de hardware do ASUS ROG Phone injetadas com sucesso, liberando opções de 90/120 FPS no menu gráfico do Free Fire.
  4. Profile Manager carrega, valida, salva e exporta perfis em `~/.config/wayfire/profiles/`, incluindo o perfil de fábrica `default_freefire.json`.

**Plans**: 2/2 plans complete

Plans:
**Wave 1**
- [x] 02-01: Implementação da classe `WaydroidController` com controle de sessão, troca de resolução esticada e spoofing ROG Phone.

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 02-02: Implementação do `ProfileManager` com serialização JSON, validação de schema e geração do `default_freefire.json`.

### Phase 3: Editor Visual de Teclas (Overlay Wayland)

**Goal**: Fornecer um overlay transparente Wayland em GTK4 / Layer Shell com modo de edição interativo estilo GG Mouse Pro para criar e ajustar teclas diretamente sobre a tela do jogo.
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: MAP-02, UI-01, UI-02
**Success Criteria** (what must be TRUE):
  1. Janela de overlay renderizada com fundo transparente sobre a janela do Waydroid utilizando Wayland Layer Shell sem bloquear cliques no modo de jogo.
  2. Alternância suave entre Modo de Jogo e Modo de Edição via tecla de atalho global (`F1`).
  3. No Modo de Edição, duplo clique cria instantaneamente uma bolinha em estado de escuta (`[ ? ]`) e a próxima tecla física pressionada é vinculada à posição.
  4. Suporte a componentes visuais: TapButton (Single/Hold/Turbo), DPad analógico WASD, AimController (área de mira) e FireButton.
  5. Arrastar, soltar, redimensionar áreas e excluir bolinhas funciona em tempo real com persistência no perfil ativo.
  6. Indicador OSD na tela exibe as teclas mapeadas durante o jogo com opacidade configurável de 0% a 100%.

**Plans**: 3 plans

Plans:
**Wave 1**
- [ ] 03-01: Criação da janela overlay transparente GTK4 com suporte a Layer Shell Wayland e toggle de modo F1.

**Wave 2** *(blocked on Wave 1 completion)*
- [ ] 03-02: Implementação do fluxo de criação e edição estilo GG Mouse Pro (duplo clique, captura de tecla, arrastar e remover).

**Wave 3** *(blocked on Wave 2 completion)*
- [ ] 03-03: Renderização dos widgets de mapeamento (Tap, DPad, Aim, Fire) com controle de opacidade OSD e sincronização com o Profile Manager.

### Phase 4: Launcher Desktop e Polimento Competitivo

**Goal**: Construir o Launcher principal em GTK4 / Libadwaita com controles competitivos completos e proteção contra bug do analógico.
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: MAP-03, UI-03
**Success Criteria** (what must be TRUE):
  1. Launcher desktop moderno em GTK4 / Libadwaita oferece botão de 1 clique "Jogar Free Fire", sliders de Sensibilidade X e Y e seletor de resolução/perfil.
  2. Algoritmo de proteção contra o bug do analógico realiza reset suave do analógico virtual ao suspender o mouse, impedindo travamento de boneco correndo em linha reta.
  3. Integração completa ponta a ponta: iniciar pelo launcher aplica resolução, inicia Waydroid, aplica spoofing, ativa o engine de toque e exibe o overlay.

**Plans**: 2 plans

Plans:
- [ ] 04-01: Implementação do algoritmo anti-bug de analógico integrado ao loop de eventos de suspensão do mouse.
- [ ] 04-02: Desenvolvimento da interface do Launcher em GTK4/Libadwaita integrando todas as camadas em uma experiência unificada.

### Phase 5: Empacotamento, Permissões e Distribuição

**Goal**: Empacotar o WayFire para instalação simplificada no Linux com regras udev automáticas e pacote oficial para Arch Linux / AUR.
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: PKG-01, PKG-02
**Success Criteria** (what must be TRUE):
  1. Script `install.sh` instala todas as dependências Python/sistema, configura permissões de udev para `/dev/uinput` sem exigir root em tempo de execução e cria atalho de desktop `.desktop`.
  2. `PKGBUILD` funcional gerando pacote instalável no Arch Linux via `makepkg` / gerenciadores AUR.
  3. Guia de uso e documentação de contribuição testados em ambiente limpo.

**Plans**: 2 plans

Plans:
- [ ] 05-01: Criação do script de instalação automatizada `install.sh` e regras de permissão udev para uinput e input.
- [ ] 05-02: Criação do `PKGBUILD` para Arch Linux / AUR e documentação final de lançamento.

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Motor de Entrada e Sensibilidade X/Y (Core) | 3/3 | Complete    | 2026-10-31 |
| 2. Comunicação com Waydroid e Gerenciamento de Perfis | 2/2 | Complete    | 2026-10-31 |
| 3. Editor Visual de Teclas (Overlay Wayland) | 0/3 | Not started | - |
| 4. Launcher Desktop e Polimento Competitivo | 0/2 | Not started | - |
| 5. Empacotamento, Permissões e Distribuição | 0/2 | Not started | - |

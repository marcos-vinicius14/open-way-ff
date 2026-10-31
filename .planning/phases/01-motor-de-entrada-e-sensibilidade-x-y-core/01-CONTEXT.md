# Phase 1: Motor de Entrada e Sensibilidade X/Y (Core) - Context

**Gathered:** 2026-10-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Esta fase entrega o motor fundamental de entrada de baixo nível para emulação competitiva de Free Fire no Linux:
1. Injeção de toques virtuais de tela via Linux Kernel `/dev/uinput` com latência instantânea (<1ms) e suporte a múltiplos slots multitouch.
2. Captura direta de mouse e teclado em `/dev/input/event*` com trava e destrava de cursor (suspender) via `evdev.grab()`.
3. Motor de sensibilidade horizontal (X) e vertical (Y) independente para puxada de capa, com acumulador de subpixel e filtro anti-jitter.
4. Algoritmo anti-borda com ciclo de reset invisível de 1ms no centro da tela touch para giro 360° infinito.
5. Ferramenta CLI modular `wayfire` para testes e calibração ao vivo em partidas reais de Free Fire.

</domain>

<decisions>
## Implementation Decisions

### Captura e Tecla de Suspender
- **D-01:** Tecla padrão de suspender/destravar o cursor do mouse é `F1`, com total liberdade para o usuário remapear livremente no menu ou perfil JSON. — **Reversibility:** reversible — valor configurável no perfil.
- **D-02:** Detecção automática inteligente de periféricos em `/dev/input/event*` (inspeção de `EV_REL` para mouse e `EV_KEY` para teclado, descartando touchpads e dispositivos irrelevantes), permitindo override manual via flags CLI (`--mouse`, `--keyboard`) ou arquivo de configuração. — **Reversibility:** reversible.
- **D-03:** Captura exclusiva do mouse via `evdev.grab()` enquanto a mira estiver travada (impede drift do cursor no desktop host e cliques acidentais fora da janela); ao apertar `F1` para suspender, executa `ungrab()` instantaneamente, devolvendo o controle normal do cursor para navegar nos menus. — **Reversibility:** reversible.
- **D-04:** O motor inicia no estado Suspenso (cursor livre para navegação inicial do jogador nos menus do Free Fire), exibindo feedback visual claro no terminal (`[🟢 AIM LOCKED]` / `[🟡 SUSPENDED]`). — **Reversibility:** reversible.

### Algoritmo Anti-Borda
- **D-05:** Mecanismo de reset invisível executado como ciclo rápido em 1 slot com intervalo de 1ms (`TRACKING_ID = -1`, sleep 1ms, toque no centro de âncora $X_0, Y_0$), impedindo que o motor do jogo interprete o retorno como puxão reverso de mira. — **Reversibility:** costly — define a estabilidade da rotação da câmera.
- **D-06:** Limiar de acionamento do reset definido em 75% do raio/limite da área de mira virtual, provendo margem de segurança ideal contra flick shots e movimentos bruscos. — **Reversibility:** reversible.
- **D-07:** Coordenadas e limites da zona de mira normalizados em valores percentuais (0.0 a 1.0) para adaptação automática a qualquer resolução nativa ou esticada (1080p, 1440x1080, 1024x768). — **Reversibility:** costly — afeta a lógica de posicionamento em todas as resoluções.
- **D-08:** Slot 0 do `/dev/uinput` reservado exclusivamente para a câmera e movimentação contínua da mira; Slots 1 a 9 alocados dinamicamente para botões de ação e tiro. — **Reversibility:** costly — afeta a arquitetura de eventos multitouch.

### Curva de Sensibilidade e Suavização
- **D-09:** Multiplicadores diretos e independentes ($Sens_X$ e $Sens_Y$) armazenados como ponto flutuante no perfil (ex: $Sens_X = 1.45$, $Sens_Y = 3.20$), permitindo calibração fina e desproporcional da "puxada de capa". — **Reversibility:** reversible.
- **D-10:** Filtro de suavização exponencial leve (EMA) com toggle no perfil (`smoothing: true/false`, padrão `true`) para eliminar ruído e tremor (*jitter*) em mouses de alto DPI (1600+ DPI) com latência desprezível (<0.5ms). — **Reversibility:** reversible.
- **D-11:** Acumulador fracionário de subpixel para preservar restos decimais entre frames, garantindo micro-mira suave em snipers e tiros de longa distância sem perda de precisão. — **Reversibility:** reversible.
- **D-12:** Parâmetro `invert_y: false` por padrão com suporte a inversão vertical opcional. — **Reversibility:** reversible.

### Interface CLI e Teste Prático
- **D-13:** Painel interativo de terminal (TUI) com status ao vivo (`[🟢 AIM LOCKED]` / `[🟡 SUSPENDED]`), valores de sensibilidade X/Y, deltas do mouse em tempo real e contador de resets anti-borda. — **Reversibility:** reversible.
- **D-14:** Calibração ao vivo da sensibilidade durante o jogo via atalhos do teclado (`F7`/`F8` para $Sens_X$, `F9`/`F10` para $Sens_Y$ em passos de 0.05 ou 0.1), persistindo automaticamente no perfil JSON. — **Reversibility:** reversible.
- **D-15:** Ponto de entrada modular estruturado como pacote `wayfire` (`python -m wayfire` e comandos CLI `wayfire test`, `wayfire run`), estruturado para distribuição e empacotamento no sistema. — **Reversibility:** costly — define a estrutura de módulos do projeto Python.
- **D-16:** Disparo integrado no botão esquerdo do mouse (clique esquerdo aciona botão de tiro no HUD em slot multitouch separado) enquanto a mira estiver travada (`F1`), permitindo testar a puxada de capa completa na Fase 1. — **Reversibility:** reversible.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & Kernel Input
- `docs/ARCHITECTURE.md` §2 — Pipeline de entrada com Linux `uinput` virtual multitouch (<1ms) e especificação das capabilities evdev
- `docs/ARCHITECTURE.md` §3 — Matemática da mira, conversão de deltas relativos para coordenadas absolutas e algoritmo anti-borda

### Keymapping & Components
- `docs/KEYMAPPING.md` §2 — Fluxo de criação de botões e comportamentos de input
- `docs/KEYMAPPING.md` §3 — Estrutura do arquivo de perfil JSON e tipos de componentes (`AimController`, `FireButton`)

### Project Roadmap
- `docs/ROADMAP.md` §Fase 1 — Objetivos e critérios de sucesso da Fase 1

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Greenfield: projeto limpo sem código legado. Toda a base técnica será estruturada a partir da biblioteca `python-evdev` e kernel Linux `/dev/uinput`.

### Established Patterns
- Padrão modular em Python 3 com tipagem estática (`typing`), encapsulamento por responsabilidades (`touch_injector.py`, `mouse_capture.py`, `aim_engine.py`, `cli.py`).

### Integration Points
- `/dev/uinput` (Kernel Linux) — criação do dispositivo virtual touchscreen.
- `/dev/input/event*` (Kernel Linux) — leitura de baixo nível e `grab()` de mouse e teclado.

</code_context>

<specifics>
## Specific Ideas

- **Visão do Usuário para o Overlay (Fase 3):** Botão flutuante em formato de "Bolinha" com logo de controle de videogame suspensa no canto superior da tela (estilo Panda Mouse Pro / Game Booster móvel), que ao ser clicada abre instantaneamente o menu de mapeamento e ajustes de sensibilidade sobre o jogo.
- **Puxada de Capa:** Sensibilidade vertical $Sens_Y$ calibrada com multiplicador maior que $Sens_X$ para facilitar a subida de mira em direção à cabeça do adversário com esforço físico mínimo do mouse.

</specifics>

<deferred>
## Deferred Ideas

- **Overlay Visual Flutuante com Ícone de Controle (Fase 3):** Criação da janela transparente Wayland Layer Shell com o botão flutuante e editor visual intuitivo.
- **Proteção Anti-Bug do Analógico Virtual (Fase 4):** Algoritmo de reset suave do analógico WASD ao suspender o mouse, evitando travamento de corrida contínua.
- **Launcher Desktop GTK4 / Libadwaita (Fase 4):** Central estilo BlueStacks para gerenciamento de perfis e resoluções.

</deferred>

---

*Phase: 01-motor-de-entrada-e-sensibilidade-x-y-core*

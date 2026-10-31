# Phase 3: Editor Visual de Teclas (Overlay Wayland) - Context

**Gathered:** 2026-10-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Esta fase entrega a camada visual de mapeamento em tempo real sobre o Waydroid utilizando GTK4, Libadwaita e Wayland Layer Shell:
1. Janela de overlay fullscreen transparente renderizada via `gtk4-layer-shell` com pass-through total de cliques em modo de jogo (input region vazia no compositor).
2. Alternância suave entre Modo de Jogo e Modo de Edição via atalho dedicado (`F2`) e por banner/pill clicável discreto no topo da tela ao suspender o mouse (`F1`).
3. Editor visual interativo estilo GG Mouse Pro: duplo clique na tela cria instantaneamente um `TapWidget` em estado de escuta `[ ? ]`, vinculando a próxima tecla física pressionada.
4. Suporte visual a widgets avançados: barra de ferramentas retrátil para arrastar e posicionar Analógico Virtual WASD (`DPadWidget`), Área de Mira FPS (`AimWidget`) e Gatilho (`FireWidget`).
5. Redimensionamento direto de áreas (raio do analógico e dimensões de mira) por alças nos cantos com popover flutuante de ajustes finos, e exclusão rápida via `Delete`/`Backspace` ou botão de lixeira.
6. OSD de HUD com círculos translúcidos e rótulos compactos, controle de opacidade pelo usuário de 0% a 100% (com toggle rápido `F3` / 👁️), feedback suave ao pressionar teclas e suporte a múltiplos toques simultâneos e Macros Sequenciais numerados.
7. Sincronização e persistência contínua e transparente no perfil ativo (`~/.config/wayfire/profiles/`) via debounce de 500ms no `ProfileManager`.

</domain>

<decisions>
## Implementation Decisions

### Pass-through Wayland e Gatilho do Editor
- **D-01:** No Modo de Jogo, a superfície Layer Shell define sua região de entrada como vazia (`cairo_region_create()` vazio ou GdkSurface empty input region), permitindo que 100% dos cliques e toques passem direto para o jogo/Waydroid sem intermediários. No Modo de Edição, a região de entrada cobre a tela inteira para capturar cliques, duplo clique e arrastes. — **Reversibility:** costly — define a arquitetura de interação Wayland do overlay.
- **D-02:** Alternância de modo híbrida: tecla dedicada (`F2`) para abrir/fechar o Modo de Edição diretamente, combinada a uma barra/pill discreta no topo da tela que surge quando o mouse é suspenso via `F1` ("⚙️ Editar Teclas"), permitindo ativar tanto via teclado quanto via clique. — **Reversibility:** reversible — valores e atalhos configuráveis no perfil.
- **D-03:** Persistência automática contínua (auto-save com debounce de 500ms) diretamente no `ProfileManager`, salvando alterações no perfil ativo em disco e atualizando o motor de toque em tempo de execução sem exigir botão manual de salvar. — **Reversibility:** reversible.
- **D-04:** Configuração da superfície Wayland Layer Shell no nível `LAYER_OVERLAY` ancorada nas 4 bordas com `exclusive_zone = -1` (ignora gaps e tiling do Hyprland/Sway), com fallback automático gracioso para janela GTK4 fullscreen transparente caso o compositor não suporte o protocolo Layer Shell. — **Reversibility:** costly — define a compatibilidade com compositores Wayland.

### Criação de Widgets Especiais
- **D-05:** Barra de ferramentas retrátil e flutuante no topo do Modo de Edição com ícones de arrastar/adicionar para componentes especiais (`[🕹️ DPad]`, `[🎯 Mira FPS]`, `[🔥 Tiro]`, `[+ Botão]`), mantendo o duplo clique direto na tela para criação instantânea de botões de toque simples (`TapWidget`). — **Reversibility:** reversible.
- **D-06:** Redimensionamento de áreas (raio do `DPadWidget` e largura/altura do `AimWidget`) através de alças interativas nos cantos/bordas com mini popover contextual para ajuste de propriedades finas (sensibilidade X/Y da mira, deadzone do analógico, modo do botão). — **Reversibility:** reversible.
- **D-07:** Exclusão de componentes via teclas `Delete` / `Backspace` ao selecionar o widget, além de um botão de lixeira `[ 🗑️ ]` no popover/HUD do elemento selecionado. — **Reversibility:** reversible.
- **D-08:** Validação de instância única para `AimWidget` e `DPadWidget`: apenas uma instância de cada é permitida por perfil; tentar adicionar uma segunda exibe um toast explicativo e recentraliza a instância existente na nova coordenada. `TapWidget` e `FireWidget` são ilimitados. — **Reversibility:** costly — garante integridade do loop de toque e câmera.

### Estilo Visual OSD e Feedback
- **D-09:** Visual dos botões no HUD inspirado no GG Mouse Pro / Panda Mouse Pro: círculo translúcido com fundo escuro semi-transparente, borda fina e texto centralizado em negrito com o identificador da tecla. — **Reversibility:** reversible.
- **D-10:** Controle total de opacidade de 0% a 100% pelo usuário (`ui_settings.osd_opacity`): slider visual contínuo na barra do editor e atalho de toggle rápido (`F3` / botão olho 👁️) para ocultar/exibir o OSD instantaneamente. Em 0%, as teclas ficam 100% invisíveis na partida para jogadores experientes. — **Reversibility:** reversible.
- **D-11:** Feedback de pressão suave: círculos visíveis acendem/pulsam suavemente enquanto a tecla física correspondente estiver pressionada, retornando ao estado normal ao soltar (permanece 100% invisível se a opacidade estiver em 0%). — **Reversibility:** reversible.
- **D-12:** Badge/Pill flutuante no topo informando o estado da mira (`🎯 MIRA TRAVADA` em verde com fade out suave após 1.5s; `🔓 MOUSE LIVRE [F1]` em amarelo permanente enquanto suspenso, junto com o acesso ao editor). — **Reversibility:** reversible.

### Captura de Teclas, Periféricos e Macros Sequenciais
- **D-13:** Captura unificada no estado `[ ? ]` aceitando teclado completo e botões do mouse (botões laterais `M4`/`M5`, clique direito `RMB`, clique do meio `MMB`), com tecla `ESC` para cancelamento seguro (descarta bolinhas recém-criadas sem tecla). — **Reversibility:** reversible.
- **D-14:** Padronização de rótulos: nomes canônicos no schema JSON (`Space`, `Shift_L`, `Control_L`, `Mouse_4`, `Mouse_5`, `Mouse_Right`) e rótulos compactos e legíveis no OSD (`SPC`, `SHF`, `CTRL`, `M4`, `M5`, `RMB`). — **Reversibility:** costly — afeta a serialização e visualização dos perfis.
- **D-15:** Bloqueio com aviso amigável ao tentar mapear teclas de controle do sistema (`F1`, `F2`, `F3`), orientando o usuário a reconfigurar os atalhos globais do WayFire se desejar utilizá-las no jogo. — **Reversibility:** reversible.
- **D-16:** Suporte a múltiplos toques simultâneos (mesma tecla em mais de um botão) e suporte oficial a **Macros Sequenciais numerados**: o jogador pode criar uma sequência de toques (1, 2, 3...) disparados por uma única tecla de gatilho, clicando em ordem rápida com intervalo configurável entre os toques via slots independentes de uinput. — **Reversibility:** costly — expande a modelagem de widgets e o motor de injeção de toques.

### the agent's Discretion
- Intervalo de delay padrão para macros sequenciais (30ms entre toques).
- Cores exatas dos badges de feedback visual e gradientes CSS do Libadwaita no overlay.
- Tolerância de detecção para duplo clique (400ms padrão GTK).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Keymapping & Editor Architecture
- `docs/KEYMAPPING.md` §1 — O Editor Visual (Overlay Transparente): Modos de Operação (Edit Mode vs Mapping Mode) e atalhos globais
- `docs/KEYMAPPING.md` §2 — Fluxo de Criação de Botões (Estilo GG Mouse Pro): duplo clique, escuta [ ? ], captura imediata e reposicionamento
- `docs/KEYMAPPING.md` §3 — Tipos de Componentes Suportados: `TapButton`, `DPad`, `AimController`, `FireButton` e estrutura JSON de `ui_settings` e `widgets`
- `docs/ARCHITECTURE.md` §1 — Visão Geral da Arquitetura: Camada visual Keymap Editor (Overlay Wayland) e integração com Core Engine

### Profile Schema & Widgets Modeling
- `src/wayfire/config/widgets.py` — Modelagem de `BaseWidget`, `TapWidget`, `DPadWidget`, `AimWidget`, `FireWidget` e `WidgetFactory`
- `src/wayfire/config/profile.py` — Schema hierárquico `WayFireProfile` com `UISettings` (`show_keys_on_screen`, `osd_opacity`) e serialização
- `src/wayfire/config/profile_manager.py` — CRUD de perfis, persistência e perfil ativo

### Project Roadmap
- `docs/ROADMAP.md` §Fase 3 — Requisitos MAP-02, UI-01, UI-02 e critérios de sucesso da Fase 3

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/wayfire/config/widgets.py`: Hierarquia tipada polimórfica pronta; será estendida para suportar o novo modo de macro sequencial ou numeração de sequência.
- `src/wayfire/config/profile.py`: Suporta `UISettings` com `osd_opacity` e `show_keys_on_screen`; pronto para integração com o slider visual.
- `src/wayfire/config/profile_manager.py`: CRUD completo e métodos `save_profile()`, `load_profile()`, `get_active_profile()` prontos para o auto-save.
- `src/wayfire/core/aim_engine.py`: Motor de mira com controle de sensibilidade e trava de cursor (`F1`).
- `src/wayfire/core/touch_injector.py`: Injetor uinput multitouch com 10 slots (0 a 9) capaz de disparar múltiplos toques simultâneos ou sequenciais.

### Established Patterns
- Python 3.12 com `from __future__ import annotations`, dataclasses tipadas e fábrica polimórfica.
- Integração GTK4 com `PyGObject` (`gi.repository.Gtk`, `Gdk`, `Adw`) e `gtk4-layer-shell`.
- Coordenadas de tela sempre normalizadas (0.0 a 1.0) para independência de resolução.

### Integration Points
- Compositor Wayland via `gtk4-layer-shell` e `Gdk.Surface` (input region transparente vs interativa).
- `src/wayfire/config/profile_manager.py` para carregar o perfil ativo no boot do overlay e persistir edições.
- `src/wayfire/core/touch_injector.py` para injeção física dos toques correspondentes às teclas mapeadas.

</code_context>

<specifics>
## Specific Ideas

- **Estilo GG Mouse Pro:** Círculos translúcidos com texto centralizado nítido (`SPC`, `M4`, `E`), duplo clique para criar bolinha em estado de escuta piscando `[ ? ]` e captura instantânea da próxima tecla física.
- **Macros Sequenciais:** O jogador pode criar bolinhas enumeradas (1, 2, 3...) associadas a uma única tecla de gatilho (ex: `G` ou `Mouse_4`), acionando os toques em sequência com intervalo configurável.
- **Invisibilidade Total:** Possibilidade de ajustar a opacidade OSD em 0% para jogar com tela 100% limpa após memorizar as teclas.

</specifics>

<deferred>
## Deferred Ideas

- **Launcher Desktop GTK4 / Libadwaita (Fase 4):** Janela principal estilo BlueStacks para gerenciamento de perfis, resoluções e botão "Jogar Free Fire".
- **Proteção Anti-Bug do Analógico Virtual (Fase 4):** Algoritmo de reset suave do analógico WASD ao suspender o mouse.
- **Empacotamento e Regras udev (Fase 5):** Script `install.sh` e pacote PKGBUILD para Arch Linux.

</deferred>

---

*Phase: 03-editor-visual-de-teclas-overlay-wayland*
*Context gathered: 2026-10-31*

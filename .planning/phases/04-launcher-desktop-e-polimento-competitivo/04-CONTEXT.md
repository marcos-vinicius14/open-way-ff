# Phase 4: Launcher Desktop e Polimento Competitivo - Context

**Gathered:** 2026-10-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Esta fase entrega a interface gráfica desktop oficial do WayFire ("Central de Jogos") construída em GTK4 e Libadwaita, integrando todo o ecossistema desenvolvido nas Fases 1 a 3, juntamente com o algoritmo de proteção e polimento competitivo contra o bug do analógico:
1. Janela principal do Launcher moderna em GTK4 / Libadwaita com Hero Banner no topo, botão em destaque "JOGAR FREE FIRE" / "PARAR JOGO" e cards de acesso rápido para Sensibilidade X e Y, seleção de resolução e perfis.
2. Sliders contínuos de Sensibilidade X e Y (0.1 a 10.0) com campos numéricos editáveis e badge dinâmico indicando a proporção de subida de capa (Y/X) em tempo real, com suporte a hot-reload durante a partida.
3. Seletor de Resolução em 1 clique com botões tipo Pill (1080p Nativo 16:9, 1440x1080 4:3 Esticado [Comp] e 1024x768 4:3 Esticado) e dropdown de Perfis com atalhos de gerenciamento.
4. Orquestração integrada do ciclo de vida: validação de ambiente, aplicação de resolução e spoofing ROG Phone, lançamento supervisionado da sessão do Waydroid e do Free Fire (Standard ou MAX), inicialização dos motores de toque/mira e overlay.
5. Minimização automática da janela do Launcher para segundo plano durante o jogo e restauração automática ao encerrar a partida.
6. Painel de status do sistema com indicadores coloridos de saúde (Serviço Waydroid, `/dev/uinput`, Spoofing ROG Phone e Resolução), botão de auto-correção / 1 clique com `pkexec` e visualizador de logs integrado.
7. Algoritmo anti-bug do analógico no `KeymapEngine`: reset limpo imediato ao suspender o mouse (`F1`) ou alternar modo de edição (`F2`), micro-pulso de recentralização (1ms) no centro do DPad ao reativar mira, atalho de pânico via duplo toque em `F1`, e resolução direcional SOCD Last Win (Snap Tap) para strafe ágil sem travamento.

</domain>

<decisions>
## Implementation Decisions

### Layout e Estrutura do Launcher (Libadwaita)
- **D-01:** Estrutura principal baseada em Dashboard Moderno com Hero Banner do Free Fire no topo com botão em destaque "JOGAR FREE FIRE", seguido de cards inferiores compactos para ajustes rápidos (sliders X/Y, resolução, perfil) e status. — **Reversibility:** costly — define a hierarquia visual e layout dos widgets da janela principal GTK4/Adw.
- **D-02:** Sliders de Sensibilidade X e Sensibilidade Y contínuos (0.1 a 10.0) acompanhados de campos numéricos (SpinButton/Entry) para digitação exata e badge indicando em tempo real a proporção Y/X ("proporção de capa"). — **Reversibility:** reversible — componentes de interface conectados ao ProfileManager.
- **D-03:** Seleção de Resolução via botões agrupados em 1 clique estilo Pill ("1080p Nativo", "1440x1080 Esticado [Comp]", "1024x768 Esticado") com badge competitivo destacando 1440x1080, e seleção de Perfil via AdwComboRow com botão rápido de gerenciar/importar perfis ao lado. — **Reversibility:** reversible — componentes de interface conectados ao WaydroidController e ProfileManager.
- **D-04:** Identidade visual e estética em Libadwaita Dark com acentos personalizados WayFire 🔥 (fundo escuro nativo com detalhes e botão de ação principal em gradiente laranja/vermelho fogo), mantendo consistência com o overlay. — **Reversibility:** reversible — regras CSS sobre os widgets Libadwaita.

### Comportamento do Launcher ao Iniciar o Jogo (Ciclo de Vida)
- **D-05:** Ao clicar em "JOGAR FREE FIRE", a janela do Launcher é automaticamente minimizada/ocultada para segundo plano para não disputar foco com a janela do jogo nem consumir recursos gráficos desnecessários do compositor Wayland, sendo restaurada automaticamente quando o jogo for encerrado. — **Reversibility:** reversible.
- **D-06:** Botão dinâmico de ação no Launcher: enquanto o jogo estiver em execução, o botão principal transforma-se em "⏹ PARAR JOGO" (em vermelho), permitindo encerrar a sessão do Free Fire, parar o motor de toque e fechar o overlay com segurança e de forma limpa. — **Reversibility:** reversible.
- **D-07:** Sequência de boot supervisionada com feedback visual em tempo real no Launcher (spinner e texto descritivo passo a passo: Validação de Serviços -> Resolução -> Spoofing ROG Phone -> Motor de Toque -> Lançamento do Free Fire). — **Reversibility:** reversible.
- **D-08:** Hot-reload instantâneo de sensibilidade: alterações nos sliders de Sensibilidade X ou Y no Launcher enquanto o jogo está aberto refletem imediatamente no `AimEngine` ativo sem necessidade de reiniciar o jogo, com persistência debounced no perfil. — **Reversibility:** costly — exige canal de comunicação direto entre o Launcher UI e a instância do AimEngine em execução.

### Estratégia do Algoritmo Anti-Bug do Analógico
- **D-09:** Reset automático do analógico: ao suspender o mouse (`F1`) ou alternar para o Modo de Edição (`F2`), o `KeymapEngine` limpa instantaneamente todas as teclas WASD ativas (`active_dpad_keys`) e injeta `touch_up` no slot 2 do uinput, garantindo parada imediata do personagem e evitando corrida involuntária em linha reta. — **Reversibility:** costly — afeta a máquina de estados do motor de entrada no kernel.
- **D-10:** Micro-pulso invisível de recentralização (1ms) no centro do DPad: ao destravar a mira (`F1`) para retomar o controle do mouse, o motor injeta um toque instantâneo de 1ms no centro exato $(X, Y)$ do `DPadWidget` antes de aceitar novo movimento direcional, forçando o HUD do Free Fire a recentralizar o joystick virtual e eliminando drift residual. — **Reversibility:** costly — garante integridade do loop de toque contra bugs do motor do jogo.
- **D-11:** Atalho de emergência via duplo toque rápido em `F1` (duplo clique na tecla de suspender): caso ocorra descalibração do analógico durante tiroteio intenso, acionar `F1` duas vezes rapidamente força a liberação de todos os slots de toque e recentraliza o analógico. — **Reversibility:** reversible.
- **D-12:** Resolução inteligente de direções opostas com prioridade para a última tecla pressionada (estilo 'Snap Tap' / SOCD Last Win): ao pressionar A e depois D (ou W e depois S) sem soltar a anterior, o analógico assume imediatamente a nova direção; ao soltar a segunda tecla, retorna imediatamente para a direção ainda pressionada, sem parar no centro neutro. — **Reversibility:** costly — altera o cálculo do vetor direcional 8-way no KeymapEngine.

### Monitoramento e Diagnóstico de Sistema no Launcher
- **D-13:** Card de status de integridade no Launcher com indicadores coloridos (Verde/Amarelo/Vermelho) para os 4 pilares: Serviço Waydroid (`waydroid-container.service`), Permissões uinput (`/dev/uinput` rw), Spoofing ROG Phone (`ASUS_I005D` ativo) e Resolução atual. — **Reversibility:** reversible.
- **D-14:** Ação de reparo/auto-fix em 1 clique: se o serviço do Waydroid estiver inativo ou faltar permissão em `/dev/uinput`, o Launcher exibe botão de ação para tentar iniciar via `pkexec` ou abre diálogo amigável orientando o comando exato de terminal. — **Reversibility:** reversible.
- **D-15:** Detecção inteligente de versões instaladas (Free Fire Standard `com.dts.freefireth` vs Free Fire MAX `com.dts.freefiremax`) com seletor sutil no cabeçalho caso ambos estejam instalados, respeitando a configuração do perfil ativo. — **Reversibility:** reversible.
- **D-16:** Diálogo de Logs integrado ("Ver Logs do WayFire") acessível pelo menu do Launcher, exibindo a saída em tempo real do Launcher, Waydroid e Core Engine com botão para copiar para a área de transferência. — **Reversibility:** reversible.

### the agent's Discretion
- Cores exatas dos badges Libadwaita (acentos laranjas/vermelhos em CSS).
- Timeout e tolerância de tempo para detecção de duplo clique em `F1` (300ms a 400ms).
- Taxa de amostragem do polling do monitor de saúde do sistema em repouso (1s a 2s).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & System Integration
- `docs/ARCHITECTURE.md` §1 — Visão Geral da Arquitetura: Launcher UI (GTK4 / Libadwaita), WayFire Core Engine e comunicação com Waydroid
- `docs/ARCHITECTURE.md` §2 — Pipeline de Entrada: Injeção de Toque no uinput e ciclo de vida do contêiner LXC
- `docs/ARCHITECTURE.md` §3 — Matemática da Mira e Sensibilidade X/Y

### Keymapping, Widgets & Profiles
- `docs/KEYMAPPING.md` §3 — Tipos de Componentes Suportados (`DPad`, `AimController`, `FireButton`, `TapButton`) e estrutura de perfis
- `src/wayfire/config/profile.py` — Estrutura `WayFireProfile`, `MouseSettings`, `ResolutionSettings` e `UISettings`
- `src/wayfire/config/profile_manager.py` — Persistência, CRUD de perfis e gerenciamento de perfil ativo

### Waydroid & Input Core
- `src/wayfire/waydroid/controller.py` — `WaydroidController` para verificação de serviço, sessão, spoofing ROG Phone e resolução
- `src/wayfire/core/keymap_engine.py` — `KeymapEngine` para gerenciamento do D-Pad (slot 2) e vetores analógicos
- `src/wayfire/core/aim_engine.py` — `AimEngine` para sensibilidade X/Y e controle de trava do mouse
- `src/wayfire/core/touch_injector.py` — Injetor `/dev/uinput` para toques e micro-pulsos de recentralização

### Project Roadmap
- `docs/ROADMAP.md` §Fase 4 — Requisitos MAP-03, UI-03 e critérios de sucesso da Fase 4

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/wayfire/waydroid/controller.py`: Possui `is_service_active()`, `start_session()`, `stop_session()`, `set_resolution()`, `apply_rog_phone_spoofing()` e `launch_app()`.
- `src/wayfire/config/profile_manager.py`: Métodos prontos para listar, salvar e carregar perfis, além de trocar o perfil ativo.
- `src/wayfire/core/aim_engine.py`: Gerencia a trava do cursor e sensibilidade X/Y (`set_sensitivity(x, y)` pronto para hot-reload).
- `src/wayfire/core/keymap_engine.py`: Gerencia a injeção do analógico no slot 2 e detecção de teclas WASD.
- `src/wayfire/ui/overlay.py`: Overlay GTK4 transparente com Layer Shell Wayland pronto para ser iniciado em conjunto com a partida.

### Established Patterns
- Aplicação desktop GTK4 moderna com `Adw.Application`, `Adw.ApplicationWindow`, `Adw.PreferencesGroup` e CSS customizado do Libadwaita.
- Thread safety entre captura evdev e UI GTK4 utilizando `GLib.idle_add`.
- Persistência assíncrona debounced de configurações no `ProfileManager`.

### Integration Points
- Launcher UI dispara o ciclo orquestrado chamando `WaydroidController` e inicializando a thread do `AimEngine` / `KeymapEngine` e a janela do `Overlay`.
- Interface gráfica altera parâmetros de sensibilidade no `AimEngine` ativo diretamente via chamadas de método ou sinais GLib.
- `KeymapEngine._update_dpad_vector` receberá o algoritmo anti-bug (SOCD Last Win, reset ao suspender mouse, micro-pulso no slot 2).

</code_context>

<specifics>
## Specific Ideas

- **Dashboard Estilo GG Mouse Pro / BlueStacks Moderno:** Uma central imersiva e elegante onde o jogador abre o WayFire, visualiza de imediato a sensibilidade configurada com o multiplicador de capa destacado (ex: "X: 1.2 | Y: 2.8 | Capa: 2.3x"), escolhe a resolução com 1 clique (1440x1080 [Comp]) e clica no botão "JOGAR FREE FIRE" em destaque.
- **Anti-Bug do Analógico Profissional:** Resolução limpa de direções opostas com Snap Tap / SOCD Last Win e micro-pulso de 1ms no centro da tela ao sair do mouse livre, garantindo que o personagem nunca continue correndo sozinho ao fechar a mochila ou saquear caixas de loot.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-Launcher Desktop e Polimento Competitivo*
*Context gathered: 2026-10-31*

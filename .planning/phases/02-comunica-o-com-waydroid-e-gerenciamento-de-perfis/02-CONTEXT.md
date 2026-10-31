# Phase 2: Comunicação com Waydroid e Gerenciamento de Perfis - Context

**Gathered:** 2026-10-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Esta fase entrega a infraestrutura de orquestração do ambiente Waydroid e a gestão completa de configurações do jogador:
1. Controle programático do ciclo de vida do Waydroid (`WaydroidController`): gerenciamento do serviço do contêiner, inicialização supervisionada da sessão gráfica e lançamento direto do Free Fire (Standard ou MAX).
2. Gerenciamento e aplicação de resoluções competitivas esticadas (1440x1080 e 1024x768 4:3) via propriedades do Waydroid com reinício transparente da sessão gráfica e reescalonamento dinâmico do motor de toque.
3. Injeção de hardware spoofing (ASUS ROG Phone 5 - `ASUS_I005D`) para desbloquear 90/120 FPS e gráficos no Ultra no Free Fire, com backup e capacidade de restauração das propriedades originais.
4. Gerenciador de perfis JSON (`ProfileManager`) em `~/.config/wayfire/profiles/` com schema hierárquico tipado, suporte a widgets polimórficos (`TapWidget`, `DPadWidget`, `AimWidget`, `FireWidget`), migração transparente de perfis da Fase 1, exportação/importação e geração do perfil de fábrica `default_freefire.json`.

</domain>

<decisions>
## Implementation Decisions

### Ciclo de Vida e Lançamento do Waydroid
- **D-01:** Verificação inteligente de `waydroid-container.service` via `systemctl is-active`, com tentativa de ativação automática (`systemctl start` / `pkexec`) e mensagem clara orientando o comando manual exato caso falte permissão. — **Reversibility:** reversible
- **D-02:** Inicialização de sessão gráfica em processo assíncrono em segundo plano (`waydroid session start`) com polling supervisionado de status (`waydroid status`) até que contêiner e sessão atinjam o estado `RUNNING` antes de abrir o jogo. — **Reversibility:** reversible
- **D-03:** Auto-detecção inteligente do pacote do Free Fire instalado no contêiner (`com.dts.freefireth` para Standard e `com.dts.freefiremax` para MAX via `waydroid app list`), com suporte a override manual via campo `game_package` no perfil JSON. — **Reversibility:** reversible
- **D-04:** Encerramento gracioso do jogo via `waydroid shell am force-stop <package>` mantendo a sessão Waydroid ativa por padrão para rápida reabertura, provendo flag e comando explícito (`--full` / `wayfire stop --full`) para desligamento completo da sessão (`waydroid session stop`). — **Reversibility:** reversible

### Resolução Esticada e Comportamento de Reinício
- **D-05:** Resolução de tela integrada ao perfil JSON (`width` e `height`), com presets competitivos predefinidos (`1920x1080` 16:9 Nativo, `1440x1080` 4:3 Esticado Competitivo, `1024x768` 4:3 Esticado Leve). — **Reversibility:** costly — define o contrato de resolução dos perfis e a geometria do HUD.
- **D-06:** Verificação idempotente prévia das propriedades `persist.waydroid.width` e `persist.waydroid.height` antes de aplicar; se os valores já forem iguais aos do perfil ativo, evita escritas redundantes e reinícios desnecessários. — **Reversibility:** reversible
- **D-07:** Reinício transparente e automático da sessão Waydroid se a sessão gráfica já estiver em execução no momento da troca de resolução, garantindo que o compositor Wayland renderize as novas dimensões sem exigir intervenção manual do usuário. — **Reversibility:** reversible
- **D-08:** Atualização dinâmica de `screen_width` e `screen_height` no `TouchInjector` e `AimEngine` ao carregar o perfil/resolução, convertendo coordenadas percentuais normalizadas (0.0 a 1.0) diretamente na resolução ativa ($X = pct\_x \times width$, $Y = pct\_y \times height$). — **Reversibility:** costly — consolida o modelo matemático de toques em qualquer proporção de tela.

### Injeção de Spoofing ASUS ROG Phone
- **D-09:** Injeção das propriedades do ROG Phone via comandos nativos `waydroid prop set` no host Linux, preservando a integridade das imagens do sistema Android e compatibilidade com atualizações do Waydroid. — **Reversibility:** reversible
- **D-10:** Backup automático prévio das propriedades originais do contêiner em `~/.config/wayfire/device_backup.json` antes da primeira aplicação de spoofing, com comando CLI dedicado (`wayfire spoof --restore`) para restauração a qualquer momento. — **Reversibility:** reversible
- **D-11:** Verificação automática e transparente durante a inicialização do jogo: verifica se `ro.product.model` já é `ASUS_I005D`; se sim, prossegue com zero delay; se não, aplica o spoofing antes de iniciar a sessão do jogo. — **Reversibility:** reversible
- **D-12:** Conjunto essencial de 5 propriedades injetadas: `ro.product.brand=asus`, `ro.product.manufacturer=asus`, `ro.product.model=ASUS_I005D`, `ro.product.name=ASUS_I005D`, `ro.product.device=ASUS_I005D` para desbloquear 90/120 FPS e gráficos no Ultra no Free Fire. — **Reversibility:** reversible

### Schema e Validação de Perfis JSON
- **D-13:** Schema hierárquico moderno estruturado conforme `docs/KEYMAPPING.md` (`mouse_settings`, `resolution`, `widgets`, `ui_settings`) com migração automática transparente de perfis planos da Fase 1 no método `from_dict()`. — **Reversibility:** costly — define o contrato de dados consumido pelo Overlay da Fase 3 e Launcher da Fase 4.
- **D-14:** Modelagem polimórfica tipada de widgets (`TapWidget`, `DPadWidget`, `AimWidget`, `FireWidget`) derivada de `BaseWidget`, com validação de campos obrigatórios e fábrica `WidgetFactory.from_dict()` discriminando pelo atributo `"type"`. — **Reversibility:** costly — estabelece a estrutura de dados para manipulação visual no editor interativo.
- **D-15:** Perfil de fábrica `default_freefire.json` completo e pronto para partida: `AimController` (mira FPS), `FireButton` (`Mouse_Left`), `DPad` (WASD) e botões essenciais pré-mapeados (`Space` para pular, `C` para agachar, `Z` para deitar, `R` para recarregar, `Mouse_Right` para mira telescópica, `4` para kit, `E` para granada, `F` para interagir/loot, `1, 2, 3` para armas). — **Reversibility:** reversible
- **D-16:** Classe `ProfileManager` com CRUD completo (`list_profiles`, `load_profile`, `save_profile`, `get_active_profile`, `set_active_profile`), importação/exportação sanitizada com validação de schema e comandos CLI dedicados (`wayfire profile list/active/import/export`). — **Reversibility:** reversible

### the agent's Discretion
- Definição do intervalo de polling (0.5s) e timeout máximo (30s) para detecção de prontidão da sessão do Waydroid.
- Tratamento de exceções específicas de subprocess ao chamar comandos `waydroid` e mensagens de erro no terminal.
- Sanitização de caminhos de arquivos ao importar perfis externos para evitar directory traversal.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Waydroid Lifecycle & Architecture
- `docs/ARCHITECTURE.md` §1 — Controle de Ciclo de Vida e Configurações (CLI / Props) do Waydroid: resolução dinâmica, spoofing ASUS ROG Phone e lançamento de pacote
- `docs/ARCHITECTURE.md` §2 — Pipeline de Entrada: Como os Toques Chegam no Android via Linux Kernel `/dev/uinput`
- `docs/ARCHITECTURE.md` §3 — Matemática da Mira: Coordenadas normalizadas e atualização dinâmica de resolução

### Keymapping & Profiles Schema
- `docs/KEYMAPPING.md` §3 — Estrutura do Arquivo de Perfil (JSON): especificação das seções `resolution`, `mouse_settings`, `ui_settings` e lista de `widgets`
- `docs/KEYMAPPING.md` §4 — Compartilhamento e Perfis: diretrizes de importação, exportação e múltiplos perfis

### Project Roadmap
- `docs/ROADMAP.md` §Fase 2 — Comunicação com Waydroid e Gerenciamento de Perfis: requisitos WAY-01, WAY-02, WAY-03, MAP-01 e critérios de sucesso

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/wayfire/config/profile.py`: Implementação existente do `WayFireProfile` da Fase 1; será expandida e refatorada com o novo schema hierárquico e migração transparente.
- `src/wayfire/core/touch_injector.py`: Gerencia a criação e injeção no `/dev/uinput`; suportará redefinição dinâmica de dimensões de tela (`set_screen_dimensions(w, h)`).
- `src/wayfire/core/aim_engine.py`: Motor de mira com sensibilidade X/Y e anti-borda; atualizará limites normalizados baseados nas dimensões ativas.
- `src/wayfire/cli/main.py`: CLI modular baseada em `argparse`; receberá os novos subcomandos de ciclo de vida (`wayfire launch`, `wayfire stop`), spoofing (`wayfire spoof`) e perfis (`wayfire profile`).

### Established Patterns
- Dataclasses Python tipadas com tipagem estática rigorosa (`typing`, `from __future__ import annotations`).
- Serialização bidirecional em JSON com `to_dict()` e `from_dict()`.
- Criação automática de diretórios de configuração em `~/.config/wayfire/`.

### Integration Points
- Binário `waydroid` no sistema host (`waydroid prop get/set`, `waydroid session start/stop`, `waydroid app launch/list`, `waydroid status`, `waydroid shell`).
- Gerenciador systemd (`systemctl is-active/start waydroid-container.service`).
- Diretório de perfis local `~/.config/wayfire/profiles/` e arquivo de backup de hardware `~/.config/wayfire/device_backup.json`.

</code_context>

<specifics>
## Specific Ideas

- **Resolução Esticada Competitiva (1440x1080 4:3):** Preferência consolidada no cenário de Free Fire competitivo por ampliar visualmente a hitbox aparente e os modelos de adversários na tela, tornando a puxada de capa (Sensibilidade Y) significativamente mais consistente.
- **ASUS ROG Phone 5 (`ASUS_I005D`):** Identificação de hardware selecionada por ser a mais estável e universalmente aceita pelo Free Fire para liberar 90 e 120 FPS sem risco de restrições de conta.

</specifics>

<deferred>
## Deferred Ideas

- **Overlay Visual Wayland Layer Shell (Fase 3):** Criação da janela transparente sobre o Waydroid com o botão flutuante e editor interativo estilo GG Mouse Pro.
- **Proteção Anti-Bug do Analógico Virtual (Fase 4):** Mecanismo de reset suave do analógico WASD ao suspender o mouse.
- **Launcher Desktop Moderno GTK4 / Libadwaita (Fase 4):** Central estilo BlueStacks para gerenciamento de perfis, sliders visuais e inicialização em 1 clique.

</deferred>

---

*Phase: 02-comunicacao-com-waydroid-e-gerenciamento-de-perfis*
*Context gathered: 2026-10-31*

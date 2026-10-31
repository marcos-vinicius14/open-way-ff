# Phase 3: Editor Visual de Teclas (Overlay Wayland) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-31
**Phase:** 03-Editor Visual de Teclas (Overlay Wayland)
**Areas discussed:** Pass-through Wayland e Gatilho do Editor, Criação de Widgets Especiais, Estilo Visual OSD e Feedback, Captura de Teclas e Periféricos

---

## Pass-through Wayland e Gatilho do Editor

| Option | Description | Selected |
|--------|-------------|----------|
| Pass-through total transparente via Input Region vazia | Superfície Layer Shell com cairo_region_create() vazio no modo jogo; cliques passam 100% para o jogo; input region fullscreen no modo edição | ✓ |
| Pass-through com Botão Flutuante Permanente | Tela transparente exceto por um botão de controle no topo estilo Panda Mouse Pro | |
| Janela de controle separada | Janela GTK flutuante em vez de overlay Layer Shell fullscreen | |

**User's choice:** Pass-through total transparente via Input Region vazia.
**Notes:** Garante latência zero e nenhuma interferência nos cliques do mouse durante a partida de Free Fire.

| Option | Description | Selected |
|--------|-------------|----------|
| Atalho separado para Edição (F2/Ctrl+F1) + Banner discreto ao suspender | F1 apenas suspende mouse; F2 abre editor; banner pill surge ao suspender com F1 | ✓ |
| Atalho F1 unificado | Apertar F1 sempre abre o editor de teclas | |
| Submenu flutuante fixo | Banner permanente na tela o tempo todo | |

**User's choice:** Opção 1 e 3 combinadas.
**Notes:** O usuário escolheu atalho dedicado (`F2`) com opção de clicar no banner/pill que surge no topo quando o mouse está suspenso via `F1`.

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-save transparente com Debounce (500ms) | Gravação contínua no perfil ativo no disco com debounce de 500ms sem botão salvar | ✓ |
| Botões manuais [Salvar] e [Descartar] | Cópia temporária exigindo clique em Salvar | |
| Auto-save com Ctrl+Z | Pilha de desfazer | |

**User's choice:** Auto-save transparente com Debounce.
**Notes:** Elimina a fricção de esquecer de salvar alterações antes de voltar para o jogo.

| Option | Description | Selected |
|--------|-------------|----------|
| Camada OVERLAY com fallback para GTK fullscreen | LAYER_OVERLAY com exclusive_zone = -1 e fallback caso o compositor não suporte Layer Shell | ✓ |
| Camada TOP padrão | Permite que notificações do desktop fiquem acima do jogo | |
| Restrito a Layer Shell | Bloqueia execução em ambientes sem wlr-layer-shell | |

**User's choice:** Camada OVERLAY com fallback transparente.
**Notes:** Compatibilidade máxima com Hyprland, Sway, KDE e outros compositores Wayland.

---

## Criação de Widgets Especiais (DPad, Mira, Tiro)

| Option | Description | Selected |
|--------|-------------|----------|
| Barra de Ferramentas Retrátil no topo/lateral | Barra com botões rápidos para DPad, Mira FPS, Botão de Tiro e Botão Simples via drag-and-drop, mantendo duplo clique para TapWidget | ✓ |
| Menu de Contexto no Botão Direito | Clicar com botão direito em área vazia abre menu de adição | |
| Conversão de tipo na bolinha | Todo elemento começa como tap e pode ser convertido | |

**User's choice:** Barra de Ferramentas Retrátil.
**Notes:** Ergonomia limpa e acesso visual imediato a todos os tipos de componentes.

| Option | Description | Selected |
|--------|-------------|----------|
| Alças Visuais de Redimensionar + Mini Popover | Alças interativas nos cantos/bordas + popover com sliders de raio, sensibilidade e deadzone | ✓ |
| Ajuste por Roda do Mouse (Scroll) | Scroll sobre o widget altera o tamanho | |
| Painel lateral fixo | Sliders em barra lateral estática | |

**User's choice:** Alças Visuais nos Cantos + Mini Popover.
**Notes:** Ajuste gráfico intuitivo direto no HUD do jogo.

| Option | Description | Selected |
|--------|-------------|----------|
| Teclas Delete / Backspace + Botão de Lixeira no Popover | Atalhos de teclado diretos e ícone vermelho de lixeira no HUD do widget | ✓ |
| Arrastar para Área de Lixeira no rodapé | Arraste até a borda inferior para excluir | |
| Menu de Contexto | Botão direito -> Excluir | |

**User's choice:** Teclas Delete / Backspace + Botão de Lixeira no Popover.
**Notes:** Agilidade para limpar ou reorganizar botões.

| Option | Description | Selected |
|--------|-------------|----------|
| Instância Única Inteligente para Mira e Analógico | Apenas 1 AimWidget e 1 DPadWidget permitidos; alerta e move o existente caso tente adicionar outro | ✓ |
| Totalmente Livre | Sem restrições de quantidade | |
| Substituição Silenciosa | Apaga o anterior sem aviso | |

**User's choice:** Instância Única Inteligente.
**Notes:** Evita conflitos de toques simultâneos de câmera ou movimentação no kernel.

---

## Estilo Visual OSD e Feedback

| Option | Description | Selected |
|--------|-------------|----------|
| Círculo translúcido estilo GG Mouse Pro com opacidade 0% a 100% | Círculos com rótulo centralizado nítido e opacidade ajustável até 0% (totalmente invisível) | ✓ |
| Apenas Texto Flutuante | Sem fundo circular | |
| Wireframe | Apenas anéis ocos | |

**User's choice:** Círculo translúcido estilo GG Mouse Pro com opacidade controlável de 0% a 100%.
**Notes:** O usuário enfatizou que a transparência deve poder ser reduzida até 0% para quem prefere jogar sem nenhum elemento visual na tela.

| Option | Description | Selected |
|--------|-------------|----------|
| Slider na Barra do Editor + Toggle Rápido F3 | Slider contínuo de 0% a 100% com tecla de atalho F3 (ou botão 👁️) para alternar visibilidade | ✓ |
| Apenas Slider na Barra | Sem atalho rápido | |
| Presets rápidos | Botões de 0%, 25%, 50%, 75%, 100% | |

**User's choice:** Slider visual na Barra + Toggle Rápido F3.
**Notes:** Controle fino e atalho instantâneo durante partidas.

| Option | Description | Selected |
|--------|-------------|----------|
| Feedback de Pressão Suave (Iluminação/Pulso) | Círculo acende suavemente enquanto a tecla física estiver pressionada (permanece invisível em 0%) | ✓ |
| Animado apenas no Modo de Edição | Estático durante o jogo | |
| Totalmente estático | Sem nenhuma reação de pressão | |

**User's choice:** Feedback de Pressão Suave.
**Notes:** Confirmação visual em tempo real de que o input foi registrado.

| Option | Description | Selected |
|--------|-------------|----------|
| Badge/Pill Discreto no Topo com Fade Out | Etiqueta flutuante com fade out em 1.5s ao travar a mira; fixa ao suspender | ✓ |
| Apenas presença/ausência do cursor | Sem indicadores na tela | |
| Ícone fixo no canto | Permanente na tela | |

**User's choice:** Badge/Pill Discreto no Topo com Fade Out.
**Notes:** Tela limpa em combate, visibilidade clara ao navegar nos menus.

---

## Captura de Teclas e Periféricos

| Option | Description | Selected |
|--------|-------------|----------|
| Captura Unificada Teclado + Mouse com ESC | Aceita teclas, M4/M5, RMB, MMB e cancela via ESC | ✓ |
| Apenas Teclado | Mouse reservado para mira e tiro | |
| Menu suspenso de seleção | Seleção em lista | |

**User's choice:** Captura Unificada com ESC para Cancelar.
**Notes:** Permite usar botões laterais do mouse (ex: granada, agachar) com facilidade.

| Option | Description | Selected |
|--------|-------------|----------|
| Identificadores Canônicos no JSON + Rótulos Compactos no Círculo | JSON padronizado (Space, Mouse_4) e OSD compacto (SPC, M4) | ✓ |
| Ícones Gráficos | Símbolos vetoriais | |
| Texto Literal | Nomes completos com fonte reduzida | |

**User's choice:** Identificadores Canônicos + Rótulos Compactos.
**Notes:** Legibilidade máxima em resoluções altas e esticadas.

| Option | Description | Selected |
|--------|-------------|----------|
| Bloqueio com Aviso Explicativo para Teclas de Sistema | Bloqueia vincular F1, F2 ou F3 diretamente a uma bolinha do HUD com aviso explicativo | ✓ |
| Permissão Total | Sem restrições | |
| Ignorar silenciosamente | Não faz nada | |

**User's choice:** Bloqueio com Aviso Explicativo.
**Notes:** Protege o usuário de perder o controle do mouse e do editor acidentalmente.

| Option | Description | Selected |
|--------|-------------|----------|
| Permitir Toques Simultâneos e Suporte a Macros Sequenciais | Múltiplos toques e suporte oficial a bolinhas enumeradas (1, 2, 3...) disparadas sequencialmente por tecla gatilho | ✓ |
| Transferência Automática | Desvincula tecla anterior | |
| Bloqueio Rígido | Impede teclas repetidas | |

**User's choice:** Permitir Toques Simultâneos e Suporte a Macros Sequenciais.
**Notes:** O usuário solicitou explicitamente suporte a macros sequenciais onde toques são enumerados e disparados em ordem com delay ao pressionar a tecla gatilho.

---

## the agent's Discretion

- Delay padrão entre toques de macros sequenciais (30ms).
- Cores de destaque e paleta Adwaita para badges e círculos OSD.
- Tempo de tolerância para clique duplo (400ms).

## Deferred Ideas

- **Launcher Desktop GTK4 / Libadwaita (Fase 4):** Janela principal estilo BlueStacks.
- **Proteção Anti-Bug do Analógico Virtual (Fase 4):** Reset suave do analógico WASD ao suspender o mouse.
- **Empacotamento e Distribuição (Fase 5):** Script `install.sh` e PKGBUILD AUR.

# Phase 4: Launcher Desktop e Polimento Competitivo - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-31
**Phase:** 04-Launcher Desktop e Polimento Competitivo
**Areas discussed:** Layout e Estrutura do Launcher (Libadwaita), Comportamento do Launcher ao Iniciar o Jogo, Estratégia do Algoritmo Anti-Bug do Analógico, Monitoramento e Diagnóstico de Sistema no Launcher

---

## Layout e Estrutura do Launcher (Libadwaita)

| Option | Description | Selected |
|--------|-------------|----------|
| Dashboard moderno com Hero Banner | Banner no topo com botão em destaque "JOGAR FREE FIRE" e cards de acesso rápido abaixo (sliders X/Y, resolução, perfil) | ✓ |
| Sidebar com navegação lateral (AdwNavigationSplitView) | Abas separadas: "Jogar", "Sensibilidade", "Resolução" e "Perfis" | |
| Janela única em estilo AdwPreferencesWindow | Lista vertical limpa e minimalista padrão GNOME | |

**User's choice:** Dashboard moderno com Hero Banner

| Option | Description | Selected |
|--------|-------------|----------|
| Sliders com ajuste numérico e indicador de proporção de capa (Y/X) | Sliders contínuos (0.1 a 10.0) com campos numéricos editáveis e badge exibindo a proporção Y/X em tempo real | ✓ |
| Sliders simples com valor textual | Sliders contínuos com exibição do valor ao lado, sem entrada manual digitada | |
| Presets rápidos combinados com sliders | Botões de 1 clique ("Equilibrado", "Capa Competitivo 2.0x", "Capa Extremo") além do slider manual | |

**User's choice:** Sliders com ajuste numérico e indicador de proporção de capa (Y/X)

| Option | Description | Selected |
|--------|-------------|----------|
| Botões agrupados em 1 clique para Resolução + Dropdown para Perfis | Botões tipo Pill para trocar resolução instantaneamente com badge [Comp] no 1440x1080, e seletor com botão de gerenciar perfis | ✓ |
| Dropdowns padrão (AdwComboRow) para ambos | Menus suspensos limpos tanto para Resolução quanto para Perfis | |
| Cards horizontais clicáveis | Cards visuais com ícones para resoluções e perfis disponíveis | |

**User's choice:** Botões agrupados em 1 clique para Resolução + Dropdown para Perfis

| Option | Description | Selected |
|--------|-------------|----------|
| Libadwaita Dark com acentos WayFire 🔥 | Fundo escuro nativo com detalhes e botão de ação em gradiente laranja/vermelho fogo, alinhado à identidade visual do projeto | ✓ |
| Libadwaita puro do sistema | Cores e estilos estritamente nativos do GNOME (Adwaita clássico sem CSS customizado) | |
| Você decide | Escolha a melhor aparência visual que mantenha o Launcher moderno e rápido | |

**User's choice:** Libadwaita Dark com acentos WayFire 🔥

---

## Comportamento do Launcher ao Iniciar o Jogo

| Option | Description | Selected |
|--------|-------------|----------|
| Minimizar/Ocultar automaticamente para background | A janela do Launcher sai da frente ao abrir o Free Fire e reaparece caso o jogo seja fechado | ✓ |
| Permanecer aberta em segundo plano | A janela continua aberta na tela (útil para multi-monitores ou consultas) | |
| Fechar completamente o processo do Launcher | O processo do Launcher encerra após disparar os serviços de jogo | |

**User's choice:** Minimizar/Ocultar automaticamente para background

| Option | Description | Selected |
|--------|-------------|----------|
| Botão dinâmico "⏹ PARAR JOGO" no Launcher | O botão principal vira "Parar Jogo" (em vermelho) enquanto o jogo estiver em execução, encerrando o Free Fire, engine de toque e overlay de forma limpa | ✓ |
| Detecção automática ao fechar a janela do Waydroid | O Launcher apenas monitora o processo do jogo e limpa os recursos quando a janela do Waydroid é fechada pelo usuário | |
| Notificação desktop persistente com ação de Parar | Exibe uma notificação no sistema com botão "Encerrar Sessão" | |

**User's choice:** Botão dinâmico "⏹ PARAR JOGO" no Launcher

| Option | Description | Selected |
|--------|-------------|----------|
| Sequência supervisionada com barra de progresso e etapas visuais | Spinner e texto de status indicando cada etapa (Serviço Waydroid -> Resolução -> Spoofing -> Motor de Toque -> Lançando Free Fire) | ✓ |
| Spinner simples de carregamento | Apenas um indicador giratório "Iniciando Free Fire..." até a janela aparecer | |
| Você decide | Adote a abordagem que forneça feedback rápido e transparente caso ocorra alguma falha | |

**User's choice:** Sequência supervisionada com barra de progresso e etapas visuais

| Option | Description | Selected |
|--------|-------------|----------|
| Hot-reload instantâneo em tempo real | Mover os sliders no Launcher reflete imediatamente no AimEngine em execução e salva no perfil, sem reiniciar nada | ✓ |
| Botão explícito "Aplicar Mudanças" | O usuário ajusta os sliders e clica em um botão para enviar ao motor de mira ativo | |
| Bloquear ajustes no Launcher enquanto o jogo roda | Sliders ficam desativados no Launcher durante a partida para evitar conflitos com o Overlay (F2) | |

**User's choice:** Hot-reload instantâneo em tempo real

---

## Estratégia do Algoritmo Anti-Bug do Analógico

| Option | Description | Selected |
|--------|-------------|----------|
| Reset automático ao suspender o mouse (F1) e alternar edição (F2) | Limpa imediatamente teclas ativas de WASD e injeta touch_up no slot 2 do uinput, garantindo parada instantânea do personagem | ✓ |
| Reset contínuo por Watchdog | Se o mouse estiver suspenso por mais de 50ms, qualquer toque analógico remanescente é limpo automaticamente | |
| Apenas reset manual sob demanda | O usuário aperta uma tecla de pânico quando o analógico bugar | |

**User's choice:** Reset automático ao suspender o mouse (F1) e alternar edição (F2)

| Option | Description | Selected |
|--------|-------------|----------|
| Micro-pulso invisível de recentralização (1ms) no centro do DPad | Ao travar o mouse para jogar novamente, injeta um toque instantâneo no centro exato do analógico para forçar a HUD do Free Fire a recalibrar a posição neutra | ✓ |
| Apenas liberação simples de touch_up | Apenas solta o toque no slot 2 sem enviar toques adicionais para a tela | |
| Você decide | Implemente a técnica mais estável que elimine o drift sem interferir nos outros toques | |

**User's choice:** Micro-pulso invisível de recentralização (1ms) no centro do DPad

| Option | Description | Selected |
|--------|-------------|----------|
| Atalho duplo na tecla de suspender (duplo clique rápido em F1) | Se o analógico bugar em partida intensa, apertar F1 rapidamente duas vezes limpa e recentraliza todos os slots de toque uinput | ✓ |
| Tecla dedicada configurável de pânico no perfil | Uma tecla exclusiva (ex: X ou F4) para forçar reset imediato do joystick | |
| Sem atalho extra de emergência | Confiar exclusivamente no reset automático que já acontece no F1/F2 | |

**User's choice:** Atalho duplo na tecla de suspender (duplo clique rápido em F1)

| Option | Description | Selected |
|--------|-------------|----------|
| Prioridade da última tecla pressionada (Snap Tap / SOCD Last Win) | Se apertar A e depois D sem soltar o A, o analógico vira para D instantaneamente, garantindo strafe ágil sem travar o boneco parado | ✓ |
| Cancelamento neutro tradicional (A + D = parada imediata) | Pressionar duas direções opostas cancela o movimento e zera o vetor analógico | |
| Você decide | Aplique a mecânica mais competitiva para o cenário de Free Fire | |

**User's choice:** Prioridade da última tecla pressionada (Snap Tap / SOCD Last Win)

---

## Monitoramento e Diagnóstico de Sistema no Launcher

| Option | Description | Selected |
|--------|-------------|----------|
| Card com indicadores coloridos de status (Verde/Amarelo/Vermelho) | Status do serviço Waydroid, permissão /dev/uinput, spoofing ROG Phone e resolução atual exibidos de forma clara | ✓ |
| Status simplificado único ("Sistema Pronto" / "Atenção") | Uma única badge resumida no cabeçalho do Launcher | |
| Diagnóstico silencioso | Só exibe aviso caso algum componente essencial esteja com erro | |

**User's choice:** Card com indicadores coloridos de status (Verde/Amarelo/Vermelho)

| Option | Description | Selected |
|--------|-------------|----------|
| Botão de auto-correção / 1 clique com pkexec | Se o serviço do Waydroid estiver inativo ou faltar permissão uinput, o Launcher oferece botão para iniciar ou instrui via diálogo amigável | ✓ |
| Apenas mensagem com o comando de terminal | Exibe um banner orientando o usuário a rodar 'sudo systemctl start waydroid-container' no terminal | |
| Você decide | Opte pelo fluxo que ofereça a melhor usabilidade sem comprometer a segurança do Linux | |

**User's choice:** Botão de auto-correção / 1 clique com pkexec

| Option | Description | Selected |
|--------|-------------|----------|
| Detecção inteligente de versões (Standard vs MAX) | O Launcher verifica quais pacotes estão instalados e exibe um seletor visual sutil caso ambos existam, lembrando a preferência no perfil | ✓ |
| Usar estritamente o pacote do perfil ativo | Lança o pacote definido em game_package sem checagem dinâmica de outros pacotes | |
| Você decide | Implemente a detecção mais conveniente para o usuário | |

**User's choice:** Detecção inteligente de versões (Standard vs MAX)

| Option | Description | Selected |
|--------|-------------|----------|
| Diálogo de Logs integrado ("Ver Logs do WayFire") | Janela acessível pelo menu do cabeçalho que exibe logs em tempo real do Launcher, Waydroid e Core Engine com botão de copiar/salvar | ✓ |
| Arquivo de log silencioso em disco (~/.config/wayfire/wayfire.log) | Sem interface gráfica para logs, apenas arquivo para consulta avançada | |
| Apenas saída de terminal (stdout/stderr) | Logs enviados apenas para o console | |

**User's choice:** Diálogo de Logs integrado ("Ver Logs do WayFire")

---

## the agent's Discretion

- Tolerância de detecção para duplo clique no atalho F1 (300-400ms).
- Cores exatas do tema CSS escuro com detalhes em laranja/vermelho fogo.
- Intervalo de atualização periódica dos status de serviços (1.5s).

## Deferred Ideas

None — discussion stayed within phase scope.

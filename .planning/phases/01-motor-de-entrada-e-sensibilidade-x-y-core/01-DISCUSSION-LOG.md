# Phase 1: Motor de Entrada e Sensibilidade X/Y (Core) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-30
**Phase:** 01-motor-de-entrada-e-sensibilidade-x-y-core
**Areas discussed:** Captura e Tecla de Suspender, Algoritmo Anti-Borda, Curva de Sensibilidade e Suavização, Interface CLI de Calibração

---

## Captura e Tecla de Suspender

| Option | Description | Selected |
|--------|-------------|----------|
| Control_L (Ctrl Esquerdo) | Padrão mais utilizado em emuladores competitivos | |
| Alt_L (Alt Esquerdo) | Ergonomia para alternar com o polegar | |
| Caps_Lock | Acesso rápido pelo dedo mínimo | |
| F1 (livremente reconfigurável) | Atalho F1 como tecla padrão, com liberdade total para mudar no menu/perfil | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| Detecção Automática Inteligente | Inspeciona EV_REL / EV_KEY, ignora touchpads, suporta override CLI/config | ✓ |
| Seleção Interativa no Terminal | Lista periféricos e grava no config | |
| Escuta Simultânea | Escuta todos os mouses ao mesmo tempo | |

| Option | Description | Selected |
|--------|-------------|----------|
| Captura Exclusiva (evdev.grab()) | Cursor do Linux oculto/preso ao travar a mira, solta no F1 | ✓ |
| Modo Híbrido sem Grab | Mouse emite toques mas move o ponteiro do host | |

| Option | Description | Selected |
|--------|-------------|----------|
| Iniciar Suspenso com Feedback | Inicia destravado para menus, feedback claro no terminal ([AIM LOCKED] / [SUSPENDED]) | ✓ |
| Iniciar Travado Imediatamente | Assume o controle direto na inicialização | |
| Iniciar Suspenso com Sinal Sonoro | Feedback sonoro com beep | |

---

## Algoritmo Anti-Borda

| Option | Description | Selected |
|--------|-------------|----------|
| Ciclo Rápido de 1 Slot (1ms) | Levanta o toque, espera 1ms e abaixa no centro para evitar puxão reverso | ✓ |
| Alternância com 2 Slots | Slot 1 no centro e encerra Slot 0 instantaneamente | |

| Option | Description | Selected |
|--------|-------------|----------|
| 75% do Raio / Limite da Área | Margem de segurança ideal para rotação e flick shots rápidos | ✓ |
| 85% do Raio / Limite da Área | Maximiza a distância percorrida antes de resetar | |

| Option | Description | Selected |
|--------|-------------|----------|
| Coordenadas Normalizadas (0.0 a 1.0) | Adaptação automática a qualquer resolução nativa ou esticada (4:3) | ✓ |
| Coordenadas em Pixels Absolutos | Pixels fixos por perfil | |

| Option | Description | Selected |
|--------|-------------|----------|
| Slot 0 Exclusivo para Câmera | Slot 0 para mira contínua; Slots 1 a 9 dinâmicos para botões de ação e tiro | ✓ |
| Pool Dinâmico Total | Qualquer ação pega o primeiro slot livre | |

---

## Curva de Sensibilidade e Suavização

| Option | Description | Selected |
|--------|-------------|----------|
| Multiplicadores Diretos Independentes | Sens_X e Sens_Y decimais diretos no perfil para calibração da puxada de capa | ✓ |
| Sensibilidade Geral + Multiplicador Y | Base única com ratio vertical | |

| Option | Description | Selected |
|--------|-------------|----------|
| Filtro Exponencial Leve (EMA) | Suaviza tremores sem latência perceptível (<0.5ms), com toggle no perfil | ✓ |
| Entrada Bruta Sempre (Raw Input) | Repassa deltas puros sem filtro | |

| Option | Description | Selected |
|--------|-------------|----------|
| Acumulador de Subpixel | Preserva restos decimais para precisão milimétrica em micro-ajustes | ✓ |
| Arredondamento Padrão (round()) | Arredonda para inteiro mais próximo a cada frame | |

| Option | Description | Selected |
|--------|-------------|----------|
| Sim, incluir invert_y: false | Padrão normal com suporte a inversão vertical opcional | ✓ |
| Apenas modo normal | Sem suporte a inversão de eixo vertical | |

---

## Interface CLI de Calibração

| Option | Description | Selected |
|--------|-------------|----------|
| Dashboard Interativo ao Vivo (TUI) | Painel limpo com status, sensibilidade, deltas e resets em tempo real | ✓ |
| Logs em Linhas Contínuas | Imprime texto a cada evento | |
| Modo Silencioso | Execução em segundo plano | |

| Option | Description | Selected |
|--------|-------------|----------|
| Atalhos no Teclado em Tempo Real | F7/F8 para Sens X, F9/F10 para Sens Y durante a partida | ✓ |
| Configuração Apenas por CLI/JSON | Passar argumentos na inicialização | |

| Option | Description | Selected |
|--------|-------------|----------|
| Comando Estruturado wayfire | CLI modular pronto para empacotamento no sistema | ✓ |
| Script Python Direto | Script direto python core/test_aim.py | |

| Option | Description | Selected |
|--------|-------------|----------|
| Sim, incluir Disparo no Botão Esquerdo | Clique esquerdo atira enquanto mira estiver travada (F1) | ✓ |
| Apenas Câmera na Fase 1 | Apenas rotação sem tiro | |

---

## the agent's Discretion

- Estrutura de classes e modularização interna da engine Python (`TouchInjector`, `MouseCapture`, `AimEngine`, `CliApp`).
- Seleção de constantes de timing e intervalos de polling em microssegundos no loop evdev.

## Deferred Ideas

- **Widget Flutuante do Overlay (Fase 3):** Bolinha flutuante com logo de controle suspensa no topo da tela (estilo Panda Mouse Pro) que abre o menu de configurações e mapeamento ao clicar.
- **Proteção Anti-Bug de Analógico (Fase 4):** Reset suave do joystick analógico WASD ao suspender mouse.

# Roadmap de Desenvolvimento — WayFire 🔥

Este documento apresenta o planejamento em fases para a construção completa do **WayFire**.

---

## 📅 Visão Geral das Fases

```
[Fase 1: Motor de Entrada e Sensibilidade X/Y]
                 │
                 ▼
[Fase 2: Comunicação com Waydroid e Resoluções]
                 │
                 ▼
[Fase 3: Editor Visual de Teclas (Overlay)]
                 │
                 ▼
[Fase 4: Launcher e Otimização para Free Fire]
                 │
                 ▼
[Fase 5: Empacotamento e Distribuição]
```

---

## 🚀 Fase 1: Motor de Entrada e Sensibilidade X/Y (Core)
*Objetivo: Conseguir movimentar a mira com o mouse dentro do Free Fire com sensibilidade X e Y ajustáveis via script de terminal.*

- [ ] Configurar ambiente virtual Python e dependências (`python-evdev`).
- [ ] Criar o injetor de toque virtual via `/dev/uinput` com suporte a múltiplos slots de toque simultâneos (*multitouch*).
- [ ] Implementar a captura de mouse de baixo nível:
  - Trava e destrava do cursor (tecla de suspender).
  - Cálculo de Sensibilidade X (horizontal) e Sensibilidade Y (vertical para subida de capa).
  - Algoritmo de recentralização contínua do toque para rotação infinita de câmera (sem travar na borda da tela).
- [ ] Teste prático do protótipo no Free Fire aberto.

---

## ⚙️ Fase 2: Módulo de Comunicação com Waydroid e Perfis
*Objetivo: Controlar o Waydroid programaticamente e gerenciar configurações salvas.*

- [ ] Criar classe controladora do Waydroid em Python (`waydroid_controller.py`):
  - Iniciar / parar contêiner e sessão.
  - Aplicar resolução dinâmica (Full HD vs Resolução Esticada 4:3).
  - Injetar propriedades de FPS alto (ASUS ROG Phone).
  - Lançar o aplicativo do Free Fire diretamente.
- [ ] Desenvolver o sistema de carregamento e salvamento de perfis JSON (`profile_manager.py`).
- [ ] Criar o perfil de fábrica (`default_freefire.json`) com os botões padrão já posicionados.

---

## 🎨 Fase 3: Editor Visual de Mapeamento (Overlay Estilo GG Mouse Pro)
*Objetivo: Permitir que o usuário crie, posicione e personalize 100% das teclas visualmente sobre o jogo de forma instantânea.*

- [ ] Criar janela transparente sobreposta via Wayland (GTK4 / Layer Shell):
  - Fundo transparente com passagem de cliques para o jogo no modo ativo.
- [ ] Implementar o **Modo de Edição** ativado por tecla (ex: `F1`):
  - **Fluxo GG Mouse Pro**: Clique duplo em qualquer lugar cria uma "bolinha" no ponto exato esperando a próxima tecla.
  - Captura imediata do próximo evento de tecla/mouse físico e vinculação à bolinha.
  - Arrastar e soltar livremente para microajustes de posição.
  - Exclusão rápida (tecla `Del` ou clique direito -> Remover).
  - Redimensionamento visual de áreas especiais (Analógico WASD e Área de Mira FPS).
- [ ] Indicador OSD na tela (exibição discreta das teclas sobre o jogo, com controle de opacidade de 0% a 100%).

---

## 🏆 Fase 4: Launcher e Polimento Competitivo
*Objetivo: Criar a central "estilo BlueStacks" simples e bonita.*

- [ ] Desenvolver a janela principal do Launcher:
  - Botão grande "Jogar Free Fire".
  - Sliders visuais para Sensibilidade X e Sensibilidade Y.
  - Seletor de Resolução com 1 clique (1920x1080 / 1440x1080 esticado).
  - Seletor de Perfis (ex: Rush, Sniping, Clássico).
- [ ] Implementar o algoritmo de proteção contra o "bug do analógico" (reset suave do analógico virtual ao suspender o mouse).
- [ ] Testes de estabilidade em partidas reais de Free Fire.

---

## 📦 Fase 5: Empacotamento e Comunidade
*Objetivo: Tornar o projeto fácil de instalar por qualquer usuário Linux.*

- [ ] Criar script de instalação automática em 1 comando (`install.sh`).
- [ ] Criar pacote para o Arch Linux / AUR (`PKGBUILD`).
- [ ] Documentação de contribuição e guia de criação de perfis para outros jogos (COD Mobile, PUBG, etc.).

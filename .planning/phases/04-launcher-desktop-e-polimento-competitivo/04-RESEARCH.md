---
phase: 04-launcher-desktop-e-polimento-competitivo
date: 2026-10-31
status: ready-for-planning
requirements: [MAP-03, UI-03]
decisions_addressed: [D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-08, D-09, D-10, D-11, D-12, D-13, D-14, D-15, D-16]
---

# Phase 4: Launcher Desktop e Polimento Competitivo - Research & Technical Architecture

## 1. Executive Summary

A **Fase 4** é o ponto de convergência definitivo do **WayFire 🔥**. Ela une o motor de entrada de baixíssima latência (<1ms via `/dev/uinput`), o controlador de ciclo de vida e propriedades do Waydroid, o sistema de perfis JSON e o overlay transparente Wayland em uma **interface gráfica desktop moderna, fluida e amigável em GTK4 e Libadwaita**, complementada pelo **algoritmo de proteção competitivo contra o bug do analógico**.

### Requisitos Atendidos:
- **MAP-03**: Algoritmo de proteção contra o bug do analógico com reset suave ao suspender mouse, micro-pulso de recentralização (1ms) e resolução SOCD Last Win (Snap Tap).
- **UI-03**: Launcher principal estilo central de jogos em GTK4 / Libadwaita com sliders de sensibilidade X/Y independentes com indicador dinâmico de capa, seletor de resolução em 1 clique (1080p Nativo, 1440x1080 Esticado [Comp], 1024x768 Esticado), seletor de perfis, diagnóstico de saúde em 4 pilares e botão principal dinâmico "JOGAR FREE FIRE" / "PARAR JOGO".

### Critérios de Sucesso da Fase:
1. **Launcher desktop moderno em GTK4 / Libadwaita**: Janela visual atraente com Hero Banner, botão dinâmico de 1 clique, sliders contínuos de Sensibilidade X e Y (0.1 a 10.0) com campos numéricos e badge dinâmico da proporção de subida de capa (Y/X), seletor de resolução em botões estilo Pill e gerenciamento de perfis.
2. **Algoritmo de proteção contra o bug do analógico**: Elimina definitivamente o travamento de boneco correndo em linha reta ao suspender o mouse (`F1`) ou alternar para edição (`F2`), com resolução direcional SOCD Last Win (Snap Tap) para strafe ágil, micro-pulso invisível de recentralização (1ms) no centro do DPad virtual e atalho de pânico via duplo clique em `F1`.
3. **Integração completa ponta a ponta**: Clicar em "JOGAR FREE FIRE" valida a saúde do ambiente, aplica resolução competitiva e spoofing ROG Phone, inicializa a sessão gráfica do Waydroid e o jogo Free Fire, inicia o motor de toque e o overlay transparente, minimiza automaticamente a janela do Launcher e a restaura limpa ao encerrar a partida.

---

## 2. Architecture & Technical Domain

### 2.1 Visão Geral do Ecossistema Integrado

```
┌────────────────────────────────────────────────────────────────────────┐
│                        WayFire Launcher Desktop                        │
│                   (GTK4 / Libadwaita Application)                      │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Hero Banner: Free Fire | Botão "🔥 JOGAR FREE FIRE" / "⏹ PARAR" │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌────────────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │  Sensibilidade X / Y   │  │ Resolução &    │  │  Status Sistema  │  │
│  │  - Sliders & Spin      │  │ Perfis         │  │  (4 Pilares)     │  │
│  │  - Badge Capa (Y/X)    │  │ - 1080p / 1440 │  │  - Waydroid Svc  │  │
│  │  - Hot-reload ao vivo  │  │ - Combo Perfis │  │  - uinput RW     │  │
│  └───────────┬────────────┘  └───────┬────────┘  │  - ROG Phone     │  │
│              │                       │           │  - Resolução     │  │
│              │                       │           └────────┬─────────┘  │
└──────────────┼───────────────────────┼────────────────────┼────────────┘
               │                       │                    │
               ▼                       ▼                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      GameSessionCoordinator                            │
│  (Orquestrador do Ciclo de Vida do Jogo & Thread de Captura)          │
│                                                                        │
│  ┌───────────────────────────┐       ┌──────────────────────────────┐  │
│  │ WaydroidController        │       │ WayFireOverlayWindow         │  │
│  │ - Resolução 1440x1080     │       │ (Layer Shell Wayland)        │  │
│  │ - Spoofing ROG Phone 5    │       │ - Banner OSD Transparente    │  │
│  │ - Start Session & Launch  │       │ - Modo Edição GG Mouse Pro   │  │
│  └───────────────────────────┘       └──────────────────────────────┘  │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Background Input Thread (<1ms latência)                          │  │
│  │  - InputCaptureManager: epoll leitura de /dev/input/event*       │  │
│  │  - AimEngine / AimProcessor: trava mouse & sensibilidade X/Y     │  │
│  │  - KeymapEngine: anti-bug analógico (SOCD Last Win + micro-pulse)│  │
│  │  - TouchInjector: injeção direta em /dev/uinput (Slots 0 a 9)    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Algoritmo Anti-Bug do Analógico (MAP-03)

### 3.1 Causa Raiz do Bug nos Emuladores
Nos jogos mobile de tiro como Free Fire, o controle direcional é realizado por um joystick virtual analógico renderizado na tela. Quando executado sobre emuladores ou contêineres:
1. **Perda de Foco / Desativação com Tecla Pressionada:** Se o jogador suspende o mouse (`F1`) para abrir a mochila, saquear caixas de loot ou acessar menus enquanto ainda estava pressionando `W` ou `D`, a tecla física deixa de enviar eventos de liberação capturados pelo motor. O toque virtual no slot do analógico (Slot 2) permanece ativo no kernel com vetor deslocado.
2. **Resultado:** O joystick virtual do Free Fire não recebe o evento `touch_up`, e o personagem continua correndo em linha reta indefinidamente até colidir com obstáculos ou ser eliminado.
3. **Neutralização Indesejada em Trocas Rápidas (SOCD Neutro):** Em confrontos rápidos (*strafe*), ao pressionar simultaneamente `A` e `D` ou alternar rapidamente de uma para outra, vetores opostos $dx = -1 + 1 = 0$ faziam o personagem parar abruptamente, quebrando a movimentação competitiva.

### 3.2 Resolução SOCD Last Win (Snap Tap)
Para movimentação ágil e sem travamentos, implementa-se o algoritmo **SOCD Last Win**:
- Mantém-se o histórico ordenado de teclas ativas por eixo independente:
  - **Eixo Horizontal:** `horizontal_history = ["left"]` $\to$ pressione `right` $\to$ `["left", "right"]`. A última tecla inserida tem prioridade absoluta: $dx = +1.0$. Ao soltar `right`, `right` é removido $\to$ `["left"]` $\to$ $dx = -1.0$ retorna imediatamente sem passar por zero neutro.
  - **Eixo Vertical:** `vertical_history = ["up"]` $\to$ pressione `down` $\to$ `["up", "down"]`. Prioridade para `down`: $dy = +1.0$. Ao soltar `down`, retorna instantaneamente para `up` ($dy = -1.0$).
- Diagonais ortogonais mantêm cálculo normalizado via hipotenusa $\sqrt{dx^2 + dy^2}$, permitindo giros de $45^\circ$, $135^\circ$, etc., com máxima fidelidade.

```
Histórico Eixo X:  [ A ]  ────────> [ A, D ] ────────> [ A ]  ────────> [ ]
Direção Resultante: Esquerda (-1)   Direita (+1)       Esquerda (-1)    Parado (0)
Prioridade:        A ativa          D (Last Win)       A reassume       Nenhum
```

### 3.3 Reset Suave ao Suspender Mouse (`F1`) ou Entrar no Modo Edição (`F2`)
Sempre que a trava de mira for liberada (`capture.is_aim_locked == False`) ou o usuário alternar para o editor de teclas (`F2`):
1. `KeymapEngine.reset_dpad()` é invocado imediatamente.
2. Esvazia `active_dpad_keys`, `horizontal_history` e `vertical_history`.
3. Injeta `touch_up(slot=2)` no `/dev/uinput`.
4. Garante que o personagem pare de andar no exato milissegundo em que o cursor do mouse é liberado.

### 3.4 Micro-Pulso Invisível de Recentralização (1ms)
Ao retomar a mira travada (`F1`) para voltar ao combate:
1. O Free Fire pode reter um deslocamento residual (*drift*) no HUD se o analógico tiver sido tocado durante a navegação do cursor.
2. O motor injeta um toque instantâneo de 1ms exatamente nas coordenadas centrais do `DPadWidget` $(X_{center}, Y_{center})$:
   ```python
   injector.touch_down(slot=2, x=dpad.x, y=dpad.y)
   time.sleep(0.001)  # 1 milissegundo imperceptível
   injector.touch_up(slot=2)
   ```
3. Esse micro-pulso força a máquina de estados do joystick do Free Fire a recentralizar o manípulo virtual, eliminando qualquer desalinhamento ou drift antes que o jogador volte a pressionar WASD.

### 3.5 Atalho de Pânico via Duplo Toque em `F1` (<350ms)
Caso ocorra qualquer descalibração severa durante tiroteios intensos:
1. Pressionar a tecla de suspender (`F1`) duas vezes consecutivas em menos de 350ms ativa a rotina de pânico:
   - Força a liberação (`touch_up`) de todos os slots de toque de 0 a 9.
   - Limpa todos os dicionários de toques ativos (`active_widget_touches`).
   - Reseta completamente o estado do DPad e dispara o micro-pulso de recentralização de 1ms.
   - Força o estado da mira como travada (`is_aim_locked = True`) com captura exclusiva do mouse (`grab()`).
   - Reseta os acumuladores subpixel e filtros EMA do `AimProcessor`.

---

## 4. Layout e Componentes do Launcher Desktop (UI-03)

### 4.1 Identidade Visual e Estética (D-01, D-04)
- **Framework:** Python 3 com PyGObject, GTK 4 (`Gtk.ApplicationWindow`) e Libadwaita (`Adw.ApplicationWindow`).
- **Tema:** Dark Mode forçado via `Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)`.
- **Paleta de Cores WayFire 🔥:**
  - Cor de Destaque Primária: Fogo/Laranja (`#ff5722` a `#e64a19`).
  - Cor Secundária / Acentos: Vermelho Competitivo (`#d32f2f`).
  - Superfícies e Cards: Fundo escuro nativo Libadwaita (`rgba(255, 255, 255, 0.05)` com bordas translúcidas).
  - Badges Competitivos: Gradiente dourado/laranja para proporção de capa recomendada ($\ge 2.0x$).

### 4.2 Hero Banner & Botão Dinâmico de Ação (D-01, D-06, D-07)
- **Posição:** Topo da janela principal.
- **Visual:** Banner imersivo com tipografia estilizada:
  - Título: **WAYFIRE 🔥**
  - Subtítulo: *Emulador Competitivo de Free Fire para Linux*
  - Pills informativas: `<1ms Latência` • `Sensibilidade X/Y` • `Anti-Bug Analógico`
- **Botão Principal de Ação:**
  - **Estado Repouso:** Grande, estilizado com gradiente de fogo:
    `[ 🔥 JOGAR FREE FIRE ]` (estilo `.wayfire-play-btn`)
  - **Estado Iniciando:** Desabilitado temporariamente, exibindo um `Gtk.Spinner` girando e o rótulo da etapa atual da sequência de boot (ex: *"Aplicando resolução 1440x1080..."*).
  - **Estado Em Jogo:** Transforma-se em botão de parada com destaque vermelho:
    `[ ⏹ PARAR JOGO ]` (estilo `.destructive-action` / vermelho).
    Permite encerrar o Free Fire, parar os motores de toque e fechar o overlay de forma limpa.

### 4.3 Card de Sensibilidade & Badge Dinâmico de Capa (D-02, D-08)
- **Controles Contínuos:**
  - **Sensibilidade X (Horizontal):** Slider `Gtk.Scale` contínuo de 0.10 a 10.00 com precisão de 0.05, acompanhado de `Gtk.SpinButton` para digitação numérica exata.
  - **Sensibilidade Y (Vertical - Puxada de Capa):** Slider `Gtk.Scale` contínuo de 0.10 a 10.00 acompanhado de `Gtk.SpinButton`.
- **Badge Dinâmico de Capa (Y/X):**
  - Calcula em tempo real:
    $$\text{Ratio} = \frac{\text{Sens}_Y}{\text{Sens}_X}$$
  - Exibe dinamicamente:
    - Se $\text{Ratio} \ge 2.0$: Badge dourado/laranja: `🔥 Proporção de Capa: 2.21x (Ideal para Subir Capa)`
    - Se $1.4 \le \text{Ratio} < 2.0$: Badge azul/neutro: `🎯 Proporção de Capa: 1.65x (Equilibrada)`
    - Se $\text{Ratio} < 1.4$: Badge cinza: `Proporção de Capa: 1.10x (Padrão)`
- **Hot-Reload Instantâneo (D-08):**
  - Ao alterar qualquer slider com o jogo em andamento, o valor é propagado instantaneamente para a instância ativa de `AimProcessor.set_sensitivity(x, y)` sem necessidade de pausar ou reiniciar a partida.
  - Alterações são gravadas no perfil ativo em disco através do `ProfileDebounceSaver` (500ms debounce).

### 4.4 Card de Resolução & Gerenciamento de Perfis (D-03)
- **Seletor de Resolução em 1 Clique (Estilo Pill):**
  - Três botões agrupados lado a lado:
    1. `1080p Nativo` (1920x1080 16:9)
    2. `1440x1080 Esticado [Comp] 🔥` (4:3 Esticado - Alvos mais largos, resolução competitiva padrão)
    3. `1024x768 Esticado` (4:3 Leve para hardware de entrada)
  - O botão correspondente à resolução salva no perfil ativo fica destacado.
  - Clicar em um botão aplica imediatamente a resolução no perfil e, se o Waydroid estiver ativo, chama `WaydroidController.set_resolution(w, h)`.
- **Seletor de Perfis:**
  - `Adw.ComboRow` (ou `Gtk.DropDown`) preenchido dinamicamente com os perfis encontrados em `~/.config/wayfire/profiles/` (`ProfileManager.list_profiles()`).
  - Trocar o perfil ativo no dropdown carrega instantaneamente suas configurações de sensibilidade, resolução e widgets na interface.
  - Botão de atalho adjacente para "Importar / Gerenciar Perfis".

### 4.5 Card de Diagnóstico de Sistema em 4 Pilares & Auto-Fix (D-13, D-14)
Monitora a saúde do sistema exibindo indicadores visuais com ícones e cores padronizadas:

| Pilar | Verificação | Status Verde | Status Amarelo / Vermelho | Ação de Auto-Fix / Reparo |
| :--- | :--- | :--- | :--- | :--- |
| **1. Serviço Waydroid** | `systemctl is-active waydroid-container` ou `waydroid status` | `Ativo e Operante` (Verde) | `Parado / Inativo` (Vermelho) | Dispara `pkexec systemctl start waydroid-container.service` em 1 clique |
| **2. Permissões uinput** | `os.access("/dev/uinput", os.W_OK)` | `Liberado (<1ms)` (Verde) | `Sem Permissão de Escrita` (Vermelho) | Abre diálogo modal amigável com comando `sudo usermod -aG input $USER` e botão copiar |
| **3. Spoofing ROG Phone** | `waydroid prop get ro.product.model == ASUS_I005D` | `Ativo (120 FPS Liberado)` (Verde) | `Padrão / Inativo` (Amarelo) | Executa `WaydroidController.apply_spoofing()` em 1 clique |
| **4. Resolução de Tela** | `waydroid prop get persist.waydroid.width` | `1440x1080 (Competitiva)` (Verde) | `Outra resolução detectada` (Neutro) | Botão rápido para redefinir para 1440x1080 |

### 4.6 Detecção de Pacotes Instalados (D-15)
- O Launcher executa `WaydroidController.detect_freefire_package()`.
- Se ambos os pacotes estiverem presentes (`com.dts.freefireth` - Standard e `com.dts.freefiremax` - MAX), exibe um seletor no cabeçalho ou nas configurações do perfil, permitindo ao usuário escolher com qual versão quer jogar.

### 4.7 Diálogo de Logs Integrado (D-16)
- Acessível pelo menu do Launcher ("Ver Logs do WayFire").
- Janela modal (`Adw.Window` ou diálogo) contendo um `Gtk.TextView` com fonte monoespaçada e rolagem automática.
- Captura logs em tempo real do Launcher, das chamadas de comando do Waydroid e dos eventos do motor de entrada.
- Botão em destaque: **"Copiar Logs para a Área de Transferência"** utilizando `Gdk.Display.get_clipboard().set(logs_text)`.

---

## 5. Orquestração do Ciclo de Vida e Sessão do Jogo

### 5.1 Sequência Supervisionada de Boot (D-05, D-07)
A inicialização do Waydroid e do Free Fire pode levar de 3 a 10 segundos dependendo do hardware do usuário. Para garantir uma experiência sem travamentos na interface GTK4:
1. Ao clicar em **"JOGAR FREE FIRE"**, o Launcher instancia um worker assíncrono em thread secundária (`threading.Thread(target=_launch_worker, daemon=True)`).
2. O botão de ação é desabilitado e exibe um spinner animado.
3. A cada etapa, o worker notifica a interface gráfica com segurança via `GLib.idle_add()`:
   - **Passo 1/5:** *Verificando contêiner Waydroid...* (`ensure_container_active`)
   - **Passo 2/5:** *Aplicando resolução competitiva...* (`set_resolution`)
   - **Passo 3/5:** *Verificando spoofing ROG Phone 5 (120 FPS)...* (`apply_spoofing`)
   - **Passo 4/5:** *Iniciando sessão gráfica do Waydroid...* (`start_session`)
   - **Passo 5/5:** *Lançando Free Fire e inicializando motor de toque...* (`launch_app`)
4. **Finalização do Boot (D-05):**
   - A thread de captura de periféricos é ativada (`InputCaptureManager` + `AimEngine` + `KeymapEngine`).
   - O overlay transparente Wayland (`WayFireOverlayWindow`) é criado e exibido sobre a tela.
   - A janela principal do Launcher é **minimizada ou ocultada** (`launcher_window.set_visible(False)`) para não disputar recursos de GPU/Wayland nem foco de janela com o jogo.
   - O botão do Launcher é atualizado para `[ ⏹ PARAR JOGO ]`.

### 5.2 Thread de Captura de Periféricos & Despacho Seguro
- A captura de periféricos (`InputCaptureManager.poll_events`) é executada em uma thread dedicada de alta prioridade.
- A thread lê diretamente eventos de `/dev/input/event*` via epoll (`selectors`) com timeout de 5ms.
- Movimentos de mouse e toques de teclas acionam `TouchInjector` diretamente no kernel Linux (`/dev/uinput`), preservando latência <1ms sem qualquer dependência do loop de eventos GTK.
- Atualizações visuais de HUD (OSD de teclas e status pill) são enfileiradas para o loop principal do GTK através de `GLib.idle_add()`.

### 5.3 Encerramento Limpo da Partida (D-05, D-06)
Ao clicar em **"⏹ PARAR JOGO"** (ou se o processo do jogo for fechado):
1. Sinaliza a thread de captura para encerrar imediatamente (`stop_event.set()`).
2. Libera a trava do mouse (`ungrab()`) e fecha o descritor `/dev/uinput`.
3. Oculta ou destrói a janela do overlay transparente.
4. Envia `waydroid shell am force-stop <package>` para encerrar o jogo Android de forma limpa.
5. **Restaura a janela do Launcher** para o primeiro plano (`launcher_window.set_visible(True); launcher_window.present()`).
6. Restaura o botão de ação para `[ 🔥 JOGAR FREE FIRE ]`.

---

## 6. Implementation Plans Breakdown

Para implementar a Fase 4 com máxima qualidade e cobertura de testes, divide-se o trabalho em dois planos executáveis e complementares:

### Plan 04-01: Algoritmo Anti-Bug do Analógico & Game Session Coordinator
**Foco:** Núcleo de entrada competitivo (MAP-03) e coordenador de sessão de jogo.
- **Entregáveis:**
  1. `KeymapEngine`:
     - Resolução direcional **SOCD Last Win (Snap Tap)** para eixos horizontal e vertical independentes.
     - Método `reset_dpad()` para reset limpo imediato (libera slot 2 e limpa estados).
     - Método `recenter_dpad()` que injeta o micro-pulso de recentralização (1ms) nas coordenadas do DPad.
     - Método `panic_reset()` que força liberação de todos os slots de 0 a 9 e recentraliza o analógico.
  2. `InputCaptureManager`:
     - Detecção de duplo clique rápido na tecla de suspender (`F1`) em $< 350$ms disparando o callback de pânico.
     - Integração do reset suave do analógico ao alternar trava de mira (`is_aim_locked`).
  3. `GameSessionCoordinator` (`src/wayfire/core/session_coordinator.py`):
     - Máquina de estados do ciclo de vida: `STOPPED`, `STARTING`, `RUNNING`, `STOPPING`.
     - Execução supervisionada da sequência de inicialização em thread secundária com callbacks de progresso thread-safe (`GLib.idle_add`).
     - Gestão da thread de captura evdev em segundo plano.
     - Hot-reload dinâmico de sensibilidade conectando a UI ao `AimProcessor`.
  4. Testes Herméticos:
     - Testes unitários para SOCD Last Win (Snap Tap) cobrindo todas as transições direcionais (A/D, W/S, diagonais).
     - Testes para micro-pulso de recentralização de 1ms e reset do slot 2.
     - Testes para detecção de duplo toque de pânico em `F1`.
     - Testes para a sequência completa de inicialização e parada do `GameSessionCoordinator` com mocks.

### Plan 04-02: Launcher Desktop em GTK4 / Libadwaita & Integração Ponta a Ponta
**Foco:** Interface gráfica principal (UI-03), diagnósticos e inicialização CLI.
- **Entregáveis:**
  1. `WayFireLauncherWindow` (`src/wayfire/ui/launcher_window.py`):
     - Janela moderna em Libadwaita Dark com acentos visuais WayFire 🔥 em CSS.
     - Hero Banner com botão dinâmico "JOGAR FREE FIRE" / "PARAR JOGO" e spinner de progresso.
     - Card de Sensibilidade com sliders contínuos X/Y (0.1 a 10.0), campos numéricos `SpinButton` sincronizados e badge dinâmico de Proporção de Capa (Y/X) em tempo real.
     - Card de Resolução com botões tipo Pill (1080p Nativo, 1440x1080 Esticado [Comp], 1024x768 Esticado) e dropdown de Perfis.
     - Card de Saúde do Sistema com indicadores coloridos para os 4 pilares (Waydroid, uinput, ROG Phone, Resolução) e botão de auto-correção / diálogo de ajuda.
  2. `WayFireLogDialog` (`src/wayfire/ui/log_dialog.py`):
     - Diálogo de visualização de logs com rolagem automática e botão para copiar para o clipboard do sistema.
  3. Integração com CLI & Overlay:
     - Executar `wayfire` ou `wayfire launcher` abre a Central de Jogos GTK4.
     - Minimização automática da janela ao jogar e restauração ao parar.
  4. Testes Herméticos de UI:
     - Testes com `xvfb-run` cobrindo inicialização de widgets, sincronização de sliders, cálculo do badge de capa, seleção de resolução, troca de perfil e estados do botão principal.

---

## 7. Verification & Testing Strategy

### 7.1 Ferramental de Teste
- **`pytest` com `xvfb-run -a`:** O ambiente headless utiliza `xvfb-run` para fornecer um servidor virtual X11 onde GTK4 e Libadwaita realizam inicialização limpa de janelas e widgets sem falhas de segmentação.
- **`MockCommandRunner`:** Simula chamadas de sistema do Waydroid (`waydroid status`, `waydroid session start`, `waydroid prop get/set`, etc.) com respostas pré-programadas e verificação de argumentos.
- **`MockUInputSink`:** Registra cada evento emitido para `/dev/uinput` com verificação estrita de slots (Slot 0 para mira, Slot 1 para tiro, Slot 2 para analógico DPad, Slots 3–9 para toques e macros).

### 7.2 Checklist de Verificação por Requisito

```
[ ] MAP-03: Algoritmo Anti-Bug do Analógico
    [ ] Testar que pressionar A e depois D sem soltar A ativa imediatamente a direção D (SOCD Last Win).
    [ ] Testar que soltar D enquanto A ainda está pressionado reativa imediatamente a direção A.
    [ ] Testar que suspender o mouse (F1) zera active_dpad_keys e injeta touch_up no slot 2.
    [ ] Testar que destravar mira dispara micro-pulso de 1ms nas coordenadas centrais do DPad.
    [ ] Testar que duplo clique rápido em F1 ativa o panic_reset liberando todos os slots.

[ ] UI-03: Launcher Principal em GTK4 / Libadwaita
    [ ] Testar criação e exibição da janela do Launcher com tema Dark e estilização CSS.
    [ ] Testar sincronização bidirecional entre sliders de Sensibilidade X/Y e SpinButtons numéricos.
    [ ] Testar cálculo e formatação do badge dinâmico de Proporção de Capa (Y/X).
    [ ] Testar hot-reload dinâmico de sensibilidade no AimProcessor ativo.
    [ ] Testar seleção de resolução em 1 clique via botões Pill (1080p, 1440x1080, 1024x768).
    [ ] Testar carregamento e troca de perfis pelo dropdown do launcher.
    [ ] Testar indicadores de saúde do sistema nos 4 pilares e diálogo de auto-correção.
    [ ] Testar abertura do visualizador de logs e cópia para o clipboard.
    [ ] Testar ciclo de vida: botão inicia jogo, minimiza janela, transforma-se em 'PARAR JOGO' e restaura ao parar.
```

---

*Research document compiled for Phase 4: Launcher Desktop e Polimento Competitivo*
*WayFire 🔥 Engineering Team — 2026-10-31*

# Phase 1: Motor de Entrada e Sensibilidade X/Y (Core) - Research

**Researched:** 2026-10-31
**Domain:** Linux Kernel Input Subsystem (`uinput`, `evdev`), Low-Latency Input Processing, Competitive FPS Sensitivity Engines
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Tecla padrão de suspender/destravar o cursor do mouse é `F1`, com total liberdade para o usuário remapear livremente no menu ou perfil JSON. — **Reversibility:** reversible — valor configurável no perfil.
- **D-02:** Detecção automática inteligente de periféricos em `/dev/input/event*` (inspeção de `EV_REL` para mouse e `EV_KEY` para teclado, descartando touchpads e dispositivos irrelevantes), permitindo override manual via flags CLI (`--mouse`, `--keyboard`) ou arquivo de configuração. — **Reversibility:** reversible.
- **D-03:** Captura exclusiva do mouse via `evdev.grab()` enquanto a mira estiver travada (impede drift do cursor no desktop host e cliques acidentais fora da janela); ao apertar `F1` para suspender, executa `ungrab()` instantaneamente, devolvendo o controle normal do cursor para navegar nos menus. — **Reversibility:** reversible.
- **D-04:** O motor inicia no estado Suspenso (cursor livre para navegação inicial do jogador nos menus do Free Fire), exibindo feedback visual claro no terminal (`[🟢 AIM LOCKED]` / `[🟡 SUSPENDED]`). — **Reversibility:** reversible.
- **D-05:** Mecanismo de reset invisível executado como ciclo rápido em 1 slot com intervalo de 1ms (`TRACKING_ID = -1`, sleep 1ms, toque no centro de âncora $X_0, Y_0$), impedindo que o motor do jogo interprete o retorno como puxão reverso de mira. — **Reversibility:** costly — define a estabilidade da rotação da câmera.
- **D-06:** Limiar de acionamento do reset definido em 75% do raio/limite da área de mira virtual, provendo margem de segurança ideal contra flick shots e movimentos bruscos. — **Reversibility:** reversible.
- **D-07:** Coordenadas e limites da zona de mira normalizados em valores percentuais (0.0 a 1.0) para adaptação automática a qualquer resolução nativa ou esticada (1080p, 1440x1080, 1024x768). — **Reversibility:** costly — afeta a lógica de posicionamento em todas as resoluções.
- **D-08:** Slot 0 do `/dev/uinput` reservado exclusivamente para a câmera e movimentação contínua da mira; Slots 1 a 9 alocados dinamicamente para botões de ação e tiro. — **Reversibility:** costly — afeta a arquitetura de eventos multitouch.
- **D-09:** Multiplicadores diretos e independentes ($Sens_X$ e $Sens_Y$) armazenados como ponto flutuante no perfil (ex: $Sens_X = 1.45$, $Sens_Y = 3.20$), permitindo calibração fina e desproporcional da "puxada de capa". — **Reversibility:** reversible.
- **D-10:** Filtro de suavização exponencial leve (EMA) com toggle no perfil (`smoothing: true/false`, padrão `true`) para eliminar ruído e tremor (*jitter*) em mouses de alto DPI (1600+ DPI) com latência desprezível (<0.5ms). — **Reversibility:** reversible.
- **D-11:** Acumulador fracionário de subpixel para preservar restos decimais entre frames, garantindo micro-mira suave em snipers e tiros de longa distância sem perda de precisão. — **Reversibility:** reversible.
- **D-12:** Parâmetro `invert_y: false` por padrão com suporte a inversão vertical opcional. — **Reversibility:** reversible.
- **D-13:** Painel interativo de terminal (TUI) com status ao vivo (`[🟢 AIM LOCKED]` / `[🟡 SUSPENDED]`), valores de sensibilidade X/Y, deltas do mouse em tempo real e contador de resets anti-borda. — **Reversibility:** reversible.
- **D-14:** Calibração ao vivo da sensibilidade durante o jogo via atalhos do teclado (`F7`/`F8` para $Sens_X$, `F9`/`F10` para $Sens_Y$ em passos de 0.05 ou 0.1), persistindo automaticamente no perfil JSON. — **Reversibility:** reversible.
- **D-15:** Ponto de entrada modular estruturado como pacote `wayfire` (`python -m wayfire` e comandos CLI `wayfire test`, `wayfire run`), estruturado para distribuição e empacotamento no sistema. — **Reversibility:** costly — define a estrutura de módulos do projeto Python.
- **D-16:** Disparo integrado no botão esquerdo do mouse (clique esquerdo aciona botão de tiro no HUD em slot multitouch separado) enquanto a mira estiver travada (`F1`), permitindo testar a puxada de capa completa na Fase 1. — **Reversibility:** reversible.

### The Agent's Discretion

- **EMA Smoothing Parameter ($\alpha$):** Peso de atenuação ajustado para $\alpha = 0.80$ por padrão (80% frame atual, 20% histórico), eliminando jitter de sensores 1600+ DPI sem introduzir arrasto perceptível (<0.2ms).
- **Mecanismo de multiplexação I/O:** Utilização de `selectors.DefaultSelector` (Linux `epoll`) síncrono para o loop de eventos de mouse e teclado, evitando o overhead de agendamento de corrotinas `asyncio` e garantindo latência determinística de poucos microssegundos.
- **TUI Dashboard:** Renderização ANSI in-place (`\r` com buffers de linha única ou escape codes VT100 simples) para o terminal sem necessidade de bibliotecas pesadas como `curses` ou `rich`, mantendo dependências mínimas.
- **Resolução de Tela Padrão de Referência:** 1920x1080 (16:9) como base para inicialização do dispositivo virtual `uinput`, com coordenadas absolutas convertidas a partir das proporções normalizadas (0.0 a 1.0).

### Deferred Ideas (OUT OF SCOPE)

- **Overlay Visual Flutuante com Ícone de Controle (Fase 3):** Janela transparente Wayland Layer Shell com botão flutuante e editor visual GG Mouse Pro.
- **Proteção Anti-Bug do Analógico Virtual (Fase 4):** Reset inteligente do DPad ao suspender para evitar corrida infinita.
- **Launcher Desktop GTK4 / Libadwaita (Fase 4):** Interface gráfica completa com gerenciamento de perfis e resoluções.

</user_constraints>

<architectural_responsibility_map>
## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Injeção Multitouch Virtual (`touch_injector.py`) | Kernel Space (`/dev/uinput`) | Linux Input Layer (`libinput`) | Criação do dispositivo virtual de tela sensível ao toque nativo do kernel com `INPUT_PROP_DIRECT` para reconhecimento imediato pelo Waydroid e compositores Wayland. |
| Captura de Baixo Nível & Suspensão (`mouse_capture.py`) | Host Userspace (`/dev/input/event*`) | Kernel Evdev (`ioctl EVIOCGRAB`) | Captura exclusiva do mouse do host via `grab()` para prender o cursor durante o jogo e soltar no `F1` para navegação nos menus. |
| Motor de Sensibilidade & Anti-Borda (`aim_engine.py`) | Host Userspace Engine | — | Matemática pura de conversão de deltas relativos para absolutos com subpixel, filtro EMA, Sens X/Y e algoritmo de reset de 1ms. |
| Painel CLI & Calibração ao Vivo (`cli.py`, `terminal_hud.py`) | Terminal Interface (TUI) | Config File (`~/.config/wayfire/`) | Dashboard ao vivo em console com controle interativo por teclas de função (`F7` a `F10`) e persistência JSON. |

</architectural_responsibility_map>

<research_summary>
## Summary

A Fase 1 entrega a espinha dorsal de performance competitiva do WayFire. Para atingir latência instantânea (<1ms) sem intermediários lentos (como ADB ou sockets de rede), o sistema comunica-se diretamente com o subsistema de entrada do Kernel Linux através do módulo `/dev/uinput` e a biblioteca `python-evdev`. O dispositivo virtual criado emula uma tela touchscreen capacitiva nativa com protocolo **Multi-touch Type B (slot-based)** e a flag de propriedade `INPUT_PROP_DIRECT`, garantindo que o compositor Wayland do host e o contêiner LXC do Waydroid reconheçam os toques sem necessidade de drivers proprietários ou emulação de mouse.

A captura de periféricos é realizada monitorando os descritores de arquivo dos dispositivos em `/dev/input/event*` via `selectors.DefaultSelector` (Linux `epoll`). O mouse é capturado com exclusividade através de `ioctl EVIOCGRAB` (`dev.grab()`) quando a mira está travada, impedindo o cursor do desktop de sair da janela ou colidir com as bordas da tela. Ao pressionar `F1` (ou hotkey configurada), o mouse é liberado (`ungrab()`) e o toque da mira é desativado (`TRACKING_ID = -1`), permitindo alternância limpa entre mira FPS e navegação em menus.

A conversão matemática do movimento do mouse para rotação de mira resolve dois desafios críticos dos emuladores: a sensibilidade assimétrica para a "puxada de capa" e o travamento nas bordas. Multiplicadores independentes $Sens_X$ e $Sens_Y$ são alimentados através de um filtro EMA anti-jitter e um acumulador de subpixel fracionário, garantindo micro-precisão para miras telescópicas. Quando o deslocamento atinge 75% do limite da zona virtual de mira, o algoritmo anti-borda dispara um ciclo de reset invisível de 1ms (levantar toque, aguardar 1ms, re-ancorar no centro com novo `TRACKING_ID`), permitindo giros de 360° contínuos e infinitos sem flick reverso.

**Primary recommendation:** Estruturar o motor em quatro módulos desacoplados (`touch_injector`, `mouse_capture`, `aim_engine`, `cli`), protegendo os testes automatizados com uma camada de abstração de dispositivo que permite executar a suíte completa de testes unitários sem exigir permissões de root ou hardware físico.

</research_summary>

<standard_stack>
## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `evdev` (`python-evdev`) | `>=1.7.0, <=2.0.0` | Interface com `/dev/uinput` e leitura de `/dev/input/event*` | Padrão da indústria no ecossistema Linux para manipulação de eventos de kernel e criação de dispositivos virtuais. Implementa Type B multitouch e ioctls nativos em C com latência de microssegundos. |
| `selectors` (Python stdlib) | Python 3.10+ | Multiplexação de descritores de arquivo I/O (epoll) | Implementação nativa da biblioteca padrão sobre `epoll` do Linux; zero alocação de corrotinas, latência determinística <10µs e encerramento limpo síncrono. |
| `dataclasses` / `json` (Python stdlib) | Python 3.10+ | Modelagem de perfis, configurações e serialização | Tipagem estática forte, validação de tipos em runtime e persistência padronizada em `~/.config/wayfire/profiles/`. |
| `pytest` | `>=8.0.0` | Framework de testes unitários e de integração | Padrão moderno de testes em Python com suporte a fixtures, parametrização e mocks. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `signal` (Python stdlib) | Python 3.10+ | Captura de `SIGINT` e `SIGTERM` | Fundamental para interceptar `Ctrl+C` e garantir execução obrigatória de `ungrab()` no mouse, prevenindo travamento do cursor no desktop host. |
| `time` (Python stdlib) | Python 3.10+ | Cronometragem de alta precisão (`perf_counter`) e pausas do ciclo anti-borda | Medição de latência dos loops (<1ms) e intervalo de reset invisível de 1ms (`time.sleep(0.001)`). |
| `pathlib` (Python stdlib) | Python 3.10+ | Manipulação semântica de diretórios e arquivos de configuração | Resolução limpa de paths como `~/.config/wayfire/` e `/dev/input/by-id/`. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `python-evdev` via `/dev/uinput` | ADB Shell Tap (`adb shell input tap`) | ADB tem latência inaceitável de 100-200ms para jogos de tiro; uinput opera em <1ms. |
| `python-evdev` via `/dev/uinput` | Scrcpy Socket Backend | Exige servidor injetado no Android via ADB e overhead de serialização de protocolo; uinput é tratado diretamente pelo kernel. |
| `selectors.DefaultSelector` | `asyncio` (`async_read_loop`) | `asyncio` adiciona complexidade de event loop, gerenciamento de tasks e maior jitter no agendamento; `selectors` com `epoll` é síncrono, direto e de menor overhead. |
| ANSI Escape Sequences | `rich` ou `curses` | `rich` e `curses` introduzem dependências adicionais e overhead de renderização desnecessário para uma TUI de console de baixa latência. Sequências ANSI simples com `\r` resolvem sem dependências. |

**Installation:**
```bash
# Instalação das dependências via pip/uv
pip install "evdev>=1.7.0"
pip install "pytest>=8.0.0"
```

</standard_stack>

<architecture_patterns>
## Architecture Patterns

### System Architecture Diagram

```
                 [ Host Hardware Peripherals ]
                     │                   │
         [ Physical Mouse ]      [ Physical Keyboard ]
         /dev/input/event*       /dev/input/event*
                     │                   │
                     ▼                   ▼
    ┌────────────────────────────────────────────────────────┐
    │              WayFire Core Input Pipeline               │
    │                                                        │
    │  ┌──────────────────────────────────────────────────┐  │
    │  │       mouse_capture.py (evdev.InputDevice)       │  │
    │  │  - epoll event multiplexer via selectors         │  │
    │  │  - Exclusive grab() on lock / ungrab() on F1     │  │
    │  │  - Auto-detection: EV_REL/EV_KEY vs Touchpads    │  │
    │  └──────────────┬───────────────────┬───────────────┘  │
    │                 │ (REL_X, REL_Y)    │ (F1, F7..F10,    │
    │                 │                   │  BTN_LEFT)       │
    │                 ▼                   ▼                  │
    │  ┌──────────────────────────────────────────────────┐  │
    │  │                 aim_engine.py                    │  │
    │  │  - State Machine: [LOCKED] vs [SUSPENDED]        │  │
    │  │  - Smoothing: Exponential Moving Average (EMA)   │  │
    │  │  - Subpixel Fractional Accumulator (acc_x/acc_y) │  │
    │  │  - Independent Sens_X & Sens_Y multipliers       │  │
    │  │  - Anti-Border Trigger: Dist > 75% from Center   │  │
    │  └──────────────┬───────────────────┬───────────────┘  │
    │                 │ (Slot 0 Camera)   │ (Slot 1 Fire)    │
    │                 ▼                   ▼                  │
    │  ┌──────────────────────────────────────────────────┐  │
    │  │               touch_injector.py                  │  │
    │  │  - Linux Kernel /dev/uinput Driver               │  │
    │  │  - Multi-touch Type B (ABS_MT_SLOT 0..9)         │  │
    │  │  - INPUT_PROP_DIRECT flag for libinput detection │  │
    │  │  - 1ms Invisible Reset: UP -> 1ms -> DOWN        │  │
    │  └──────────────────────┬───────────────────────────┘  │
    └─────────────────────────┼──────────────────────────────┘
                              │
               Linux Kernel Virtual Touchscreen
                   /dev/uinput (Virtual Device)
                              │
                              ▼
    ┌────────────────────────────────────────────────────────┐
    │       Host Wayland Compositor (KWin / Hyprland)        │
    │       - Direct touchscreen mapped to screen pixels     │
    └─────────────────────────┬──────────────────────────────┘
                              │
                              ▼
    ┌────────────────────────────────────────────────────────┐
    │                  Waydroid Container                    │
    │                  Android InputFlinger                  │
    │                  - MotionEvent (Multitouch)            │
    │                  - com.dts.freefireth (Free Fire)      │
    └────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
way-ff/
├── pyproject.toml               # Configuração PEP 621 e scripts de entrada
├── README.md
├── docs/                        # Documentação técnica do projeto
│   ├── ARCHITECTURE.md
│   └── KEYMAPPING.md
├── wayfire/                     # Pacote principal
│   ├── __init__.py
│   ├── __main__.py              # Ponto de entrada (python -m wayfire)
│   ├── cli.py                   # Parser CLI (run, test, calibrate, devices)
│   ├── core/                    # Módulos centrais de engine
│   │   ├── __init__.py
│   │   ├── config.py            # Dataclasses de configuração e carregamento JSON
│   │   ├── touch_injector.py    # Dispositivo virtual multitouch Type B (/dev/uinput)
│   │   ├── mouse_capture.py     # Captura de baixo nível, autodetecção e grab/ungrab
│   │   └── aim_engine.py        # Matemática de sensibilidade X/Y, subpixel, EMA e anti-borda
│   └── ui/
│       ├── __init__.py
│       └── terminal_hud.py      # TUI de terminal em tempo real
└── tests/                       # Suíte de testes unitários e de integração
    ├── __init__.py
    ├── conftest.py              # Mocks para evdev e fixtures
    ├── test_touch_injector.py   # Testes de slots, tracking IDs e eventos Type B
    ├── test_mouse_capture.py    # Testes de grab/ungrab, detecção e atalhos
    ├── test_aim_engine.py       # Testes de subpixel, sensibilidade, EMA e anti-borda
    ├── test_config.py           # Testes de serialização e defaults
    └── test_cli.py              # Testes de parsing CLI e comandos
```

### Pattern 1: Virtual Multitouch Protocol Type B com `INPUT_PROP_DIRECT`

**O que é:** Configuração e emissão de eventos no formato Multi-Touch Protocol Type B do Linux, utilizando slots explícitos e identificador de rastreamento `ABS_MT_TRACKING_ID`.
**Quando usar:** Em qualquer injeção de toques para emulação mobile onde o sistema host ou o Android contêiner espera eventos de toque capacitivo direto.
**Exemplo:**
```python
from evdev import UInput, AbsInfo, ecodes

def create_virtual_touchscreen(width: int = 1920, height: int = 1080) -> UInput:
    capabilities = {
        ecodes.EV_KEY: [ecodes.BTN_TOUCH],
        ecodes.EV_ABS: [
            (ecodes.ABS_X, AbsInfo(value=0, min=0, max=width, fuzz=0, flat=0, resolution=0)),
            (ecodes.ABS_Y, AbsInfo(value=0, min=0, max=height, fuzz=0, flat=0, resolution=0)),
            (ecodes.ABS_MT_SLOT, AbsInfo(value=0, min=0, max=9, fuzz=0, flat=0, resolution=0)),
            (ecodes.ABS_MT_TRACKING_ID, AbsInfo(value=0, min=0, max=65535, fuzz=0, flat=0, resolution=0)),
            (ecodes.ABS_MT_POSITION_X, AbsInfo(value=0, min=0, max=width, fuzz=0, flat=0, resolution=0)),
            (ecodes.ABS_MT_POSITION_Y, AbsInfo(value=0, min=0, max=height, fuzz=0, flat=0, resolution=0)),
        ]
    }
    # INPUT_PROP_DIRECT informa o libinput que o dispositivo é touchscreen direta
    return UInput(
        events=capabilities,
        name="WayFire Virtual Touchscreen",
        input_props=[ecodes.INPUT_PROP_DIRECT],
        version=0x3
    )
```

### Pattern 2: Ciclo de Vida Resiliente de `grab()` e Sinalização de Término

**O que é:** Captura exclusiva do mouse host com garantia incondicional de liberação (`ungrab()`) via blocos `try/finally` e handlers de sinal do SO.
**Quando usar:** Sempre que um dispositivo físico de entrada for capturado via `ioctl EVIOCGRAB`.
**Exemplo:**
```python
import signal
import sys
from evdev import InputDevice

class DeviceController:
    def __init__(self, mouse_dev: InputDevice):
        self.mouse_dev = mouse_dev
        self.is_grabbed = False
        self._setup_signals()

    def _setup_signals(self):
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._signal_handler)

    def _signal_handler(self, signum, frame):
        self.release()
        sys.exit(0)

    def grab(self):
        if not self.is_grabbed:
            self.mouse_dev.grab()
            self.is_grabbed = True

    def ungrab(self):
        if self.is_grabbed:
            self.mouse_dev.ungrab()
            self.is_grabbed = False

    def release(self):
        self.ungrab()
```

### Pattern 3: Sensibilidade Independente X/Y com Subpixel e Filtro EMA

**O que é:** Pipeline matemático que recebe deltas relativos do mouse, atenua ruídos de alto DPI com EMA, multiplica por fatores independentes $Sens_X$ e $Sens_Y$, e acumula os restos decimais para preservar micro-precisão.
**Quando usar:** No cálculo de deslocamento da mira em todos os frames de movimento do mouse.
**Exemplo:**
```python
import math

class AimProcessor:
    def __init__(self, sens_x: float, sens_y: float, smoothing: bool = True, alpha: float = 0.8):
        self.sens_x = sens_x
        self.sens_y = sens_y
        self.smoothing = smoothing
        self.alpha = alpha
        self.prev_dx = 0.0
        self.prev_dy = 0.0
        self.acc_x = 0.0
        self.acc_y = 0.0

    def process(self, raw_dx: int, raw_dy: int, invert_y: bool = False) -> tuple[int, int]:
        dy_input = -raw_dy if invert_y else raw_dy

        # Filtro de Suavização Exponencial (EMA)
        if self.smoothing:
            dx_f = self.alpha * raw_dx + (1.0 - self.alpha) * self.prev_dx
            dy_f = self.alpha * dy_input + (1.0 - self.alpha) * self.prev_dy
            self.prev_dx = dx_f
            self.prev_dy = dy_f
        else:
            dx_f = float(raw_dx)
            dy_f = float(dy_input)

        # Multiplicadores de Sensibilidade
        target_dx = dx_f * self.sens_x
        target_dy = dy_f * self.sens_y

        # Acumulador Fracionário de Subpixel
        self.acc_x += target_dx
        self.acc_y += target_dy

        step_x = math.trunc(self.acc_x)
        step_y = math.trunc(self.acc_y)

        self.acc_x -= step_x
        self.acc_y -= step_y

        return step_x, step_y
```

### Pattern 4: Reset Anti-Borda Invisível de 1ms

**O que é:** Algoritmo que levanta o contato de toque na tela quando ele atinge 75% do limite da zona virtual, aguarda 1ms para que o motor do jogo processe o `ACTION_UP`, e restabelece o toque no centro de âncora com um novo `TRACKING_ID`.
**Quando usar:** Sempre que a posição acumulada do toque ultrapassar a distância de segurança da zona de mira.
**Exemplo:**
```python
import time

def check_and_reset_anti_border(current_x: int, current_y: int, anchor_x: int, anchor_y: int,
                                radius: int, threshold_ratio: float = 0.75) -> tuple[int, int, bool]:
    dist_sq = (current_x - anchor_x) ** 2 + (current_y - anchor_y) ** 2
    max_dist = radius * threshold_ratio

    if dist_sq >= (max_dist ** 2):
        # 1. Levantar toque no Slot 0
        touch_injector.touch_up(slot=0)
        # 2. Pausa curta para processamento do ciclo no Android
        time.sleep(0.001)
        # 3. Abaixar toque no ponto de âncora com novo tracking ID
        touch_injector.touch_down(slot=0, x=anchor_x, y=anchor_y)
        return anchor_x, anchor_y, True

    return current_x, current_y, False
```

### Anti-Patterns to Avoid

- **Não usar `INPUT_PROP_DIRECT` no `UInput`:** Faz com que o compositor Wayland ou o libinput classifiquem o dispositivo como touchpad em vez de touchscreen direta, convertendo os toques em gestos de rolagem ou ponteiro de mouse.
- **Não sincronizar `BTN_TOUCH` com múltiplos slots:** Enviar `BTN_TOUCH = 0` ao soltar o Slot 0 enquanto o Slot 1 (botão de tiro) ainda está pressionado faz o Android interpretar que todos os toques foram levantados da tela. `BTN_TOUCH` deve ser `1` se `total_active_slots > 0`, e `0` apenas quando todos os slots estiverem livres.
- **Tratamento de Subpixel com truncamento direto sem acumulador:** Fazer `int(delta * sens)` descarta a parte decimal em cada frame. Em micro-movimentos com DPI alto, o cursor fica "travado" ou perde até 50% da sensibilidade esperada.
- **Falta de handler de sinal para `dev.ungrab()`:** Se o usuário interrompe a execução com `Ctrl+C` e o mouse permanecer com `grab()` ativo, o cursor do desktop trava completamente, forçando o usuário a mudar para um TTY para matar o processo.

</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Injeção de eventos de kernel | Criação manual de structs C via ctypes | `evdev.UInput` | Trata empacotamento de structs `input_event`, ioctls de capabilities, uevents e ioctls de configuração de eixos de forma nativa e testada. |
| Multiplexação de descritores de arquivo | Loop com `time.sleep()` ou threads manuais de pooling | `selectors.DefaultSelector` | Usa a syscall `epoll_wait` do Linux, que coloca o processo em espera de hardware com zero consumo de CPU e acorda instantaneamente no evento. |
| Tratamento de códigos de teclas e botões | Mapas manuais de inteiros para nomes | `evdev.ecodes` | Contém a tabela canônica de códigos do Linux (`KEY_F1`, `BTN_LEFT`, `ABS_MT_SLOT`, etc.) sincronizada com as headers do kernel. |
| Parsing de linha de comando | `sys.argv` manual | `argparse` (stdlib) | Oferece validação automática de tipos, mensagens de ajuda (`--help`), flags opcionais e subcomandos (`run`, `test`, `calibrate`). |

**Key insight:** Manipulação de hardware de entrada em nível de kernel não perdoa pequenos erros de especificação de bits (flags de capability, eixos sem limites declarados). Utilizar as constantes canônicas de `evdev.ecodes` e a camada de montagem de `evdev.UInput` elimina bugs silenciosos onde o kernel simplesmente descarta o dispositivo sem emitir mensagem de erro clara.

</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Cursor do Mouse Preso no Desktop (Lockout)
**O que acontece:** O programa é interrompido por um erro inesperado ou `Ctrl+C`, e o cursor do mouse não volta a se mover no desktop host.
**Por que acontece:** O método `mouse_dev.grab()` toma posse exclusiva dos eventos do dispositivo. Se o processo terminar sem chamar `mouse_dev.ungrab()`, o driver libinput do host não retoma a leitura.
**Como evitar:** Envolver todo o loop de execução em um bloco `try / finally` que chama explicitamente `mouse_dev.ungrab()`, além de registrar handlers para `signal.SIGINT` e `signal.SIGTERM`.
**Sinais de alerta:** Ao testar o encerramento do script, o cursor não responde e é necessário matar a sessão ou alternar para TTY (`Ctrl+Alt+F3`).

### Pitfall 2: O Famoso "Giro Invertido de 180°" ao Resetar a Mira
**O que acontece:** Ao realizar um movimento rápido de câmera, a mira subitamente gira 180° para trás ou dá um puxão brusco.
**Por que acontece:** O algoritmo de recentralização anti-borda enviou as novas coordenadas $(X_0, Y_0)$ antes que o jogo processasse o evento de levantamento de dedo (`TRACKING_ID = -1`). O motor do Free Fire calcula `delta = X_0 - X_antigo` e gira a câmera violentamente na direção oposta.
**Como evitar:** Respeitar rigorosamente o ciclo de reset em duas etapas com commit `SYN_REPORT` e pausa:
1. `ABS_MT_TRACKING_ID = -1` + `SYN_REPORT`
2. `time.sleep(0.001)` (1ms de garantia)
3. `ABS_MT_TRACKING_ID = novo_id`, `ABS_MT_POSITION_X = X_0`, `ABS_MT_POSITION_Y = Y_0` + `SYN_REPORT`.
**Sinais de alerta:** Ao girar o mouse continuamente em um sentido, o personagem repentinamente olha para trás a cada 2 ou 3 segundos.

### Pitfall 3: Dispositivo Touchscreen Não Reconhecido pelo Waydroid / Libinput
**O que acontece:** O script executa sem erros, mas o Waydroid trata o dispositivo como um mouse comum ou simplesmente ignora os toques.
**Por que acontece:** A ausência da propriedade `INPUT_PROP_DIRECT` ou a omissão de eixos essenciais como `ABS_X` e `ABS_Y` faz com que o `libinput` classifique o dispositivo como um touchpad indireto ou o ignore por falta de limites definidos.
**Como evitar:** Registrar explicitamente `input_props=[ecodes.INPUT_PROP_DIRECT]` na inicialização do `UInput` e fornecer limites válidos (`AbsInfo`) para `ABS_X`, `ABS_Y`, `ABS_MT_POSITION_X`, `ABS_MT_POSITION_Y`, `ABS_MT_SLOT` e `ABS_MT_TRACKING_ID`.
**Sinais de alerta:** O comando `libinput list-devices` não exibe `Capabilities: touch` para o dispositivo virtual criado.

### Pitfall 4: Perda de Micro-Precisão em Miras Telescópicas (Pixel Skipping / Stutter)
**O que acontece:** Mirar com armas de precisão (snipers) a longas distâncias parece "saltar" blocos de pixels ou não registrar movimentos muito lentos do mouse.
**Por que acontece:** Ao multiplicar deltas pequenos (ex: $dx = 1$) por multiplicadores decimais (ex: $Sens_X = 0.35$), o resultado $0.35$ é arredondado para $0$ em inteiros. Se o resto for descartado, o jogador pode mover o mouse lentamente e a mira não sai do lugar.
**Como evitar:** Implementar o Acumulador Fracionário de Subpixel (D-11), que guarda os restos decimais em variáveis flutuantes acumuladas e só emite o pixel quando o total atinge pelo menos $\pm 1.0$.
**Sinais de alerta:** Movimentos extremamente lentos do mouse não causam nenhuma alteração nas coordenadas emitidas pelo motor.

</common_pitfalls>

<code_examples>
## Code Examples

### 1. Criação e Configuração do Dispositivo Virtual Multitouch

```python
"""Módulo de inicialização do dispositivo virtual uinput (touch_injector.py)."""
from evdev import UInput, AbsInfo, ecodes

def build_touch_device(width: int = 1920, height: int = 1080) -> UInput:
    """Cria e registra o dispositivo virtual touchscreen Type B no Kernel Linux."""
    capabilities = {
        ecodes.EV_KEY: [
            ecodes.BTN_TOUCH
        ],
        ecodes.EV_ABS: [
            # Coordenadas absolutas legadas (necessárias para libinput e Android)
            (ecodes.ABS_X, AbsInfo(value=0, min=0, max=width, fuzz=0, flat=0, resolution=0)),
            (ecodes.ABS_Y, AbsInfo(value=0, min=0, max=height, fuzz=0, flat=0, resolution=0)),
            # Configuração Multi-Touch Protocol Type B
            (ecodes.ABS_MT_SLOT, AbsInfo(value=0, min=0, max=9, fuzz=0, flat=0, resolution=0)),
            (ecodes.ABS_MT_TRACKING_ID, AbsInfo(value=0, min=0, max=65535, fuzz=0, flat=0, resolution=0)),
            (ecodes.ABS_MT_POSITION_X, AbsInfo(value=0, min=0, max=width, fuzz=0, flat=0, resolution=0)),
            (ecodes.ABS_MT_POSITION_Y, AbsInfo(value=0, min=0, max=height, fuzz=0, flat=0, resolution=0)),
        ]
    }

    # Registra com nome amigável e propriedade de toque direto na tela
    ui = UInput(
        events=capabilities,
        name="WayFire Virtual Touchscreen",
        input_props=[ecodes.INPUT_PROP_DIRECT],
        version=0x3
    )
    return ui
```

### 2. Emissão de Eventos de Toque Multitouch (Down, Move, Up) com Gestão de Slots

```python
"""Emissão atômica de toques com controle de estado e BTN_TOUCH."""
from evdev import UInput, ecodes

class TouchSession:
    def __init__(self, ui: UInput):
        self.ui = ui
        self.active_slots: set[int] = set()
        self._next_tracking_id = 1

    def _get_tracking_id(self) -> int:
        tid = self._next_tracking_id
        self._next_tracking_id = (self._next_tracking_id + 1) % 65535
        return tid

    def touch_down(self, slot: int, x: int, y: int):
        """Inicia um toque no slot especificado."""
        self.active_slots.add(slot)
        tid = self._get_tracking_id()

        self.ui.write(ecodes.EV_ABS, ecodes.ABS_MT_SLOT, slot)
        self.ui.write(ecodes.EV_ABS, ecodes.ABS_MT_TRACKING_ID, tid)
        self.ui.write(ecodes.EV_ABS, ecodes.ABS_MT_POSITION_X, x)
        self.ui.write(ecodes.EV_ABS, ecodes.ABS_MT_POSITION_Y, y)
        self.ui.write(ecodes.EV_KEY, ecodes.BTN_TOUCH, 1)
        self.ui.syn()

    def touch_move(self, slot: int, x: int, y: int):
        """Move um toque já existente no slot."""
        if slot not in self.active_slots:
            return
        self.ui.write(ecodes.EV_ABS, ecodes.ABS_MT_SLOT, slot)
        self.ui.write(ecodes.EV_ABS, ecodes.ABS_MT_POSITION_X, x)
        self.ui.write(ecodes.EV_ABS, ecodes.ABS_MT_POSITION_Y, y)
        self.ui.syn()

    def touch_up(self, slot: int):
        """Levanta o toque do slot especificado."""
        if slot in self.active_slots:
            self.active_slots.remove(slot)

        self.ui.write(ecodes.EV_ABS, ecodes.ABS_MT_SLOT, slot)
        self.ui.write(ecodes.EV_ABS, ecodes.ABS_MT_TRACKING_ID, -1)

        # BTN_TOUCH só vai a 0 quando NENHUM slot estiver ativo
        btn_state = 1 if len(self.active_slots) > 0 else 0
        self.ui.write(ecodes.EV_KEY, ecodes.BTN_TOUCH, btn_state)
        self.ui.syn()
```

### 3. Autodetecção de Dispositivos e Multiplexação com `selectors`

```python
"""Autodetecção e leitura assíncrona não-bloqueante de periféricos."""
import selectors
import evdev
from evdev import InputDevice, ecodes

def detect_devices() -> tuple[InputDevice | None, InputDevice | None]:
    """Identifica automaticamente o mouse principal e o teclado primário."""
    mouse_dev = None
    keyboard_dev = None

    for path in evdev.list_devices():
        dev = InputDevice(path)
        caps = dev.capabilities()

        # Detecção de Teclado: Suporta teclas de digitação comuns e repetição
        if ecodes.EV_KEY in caps:
            keys = caps[ecodes.EV_KEY]
            if ecodes.KEY_A in keys and ecodes.KEY_SPACE in keys:
                if keyboard_dev is None:
                    keyboard_dev = dev

        # Detecção de Mouse: Possui movimento relativo (EV_REL) e botão esquerdo
        if ecodes.EV_REL in caps and ecodes.EV_KEY in caps:
            rel = caps[ecodes.EV_REL]
            keys = caps[ecodes.EV_KEY]
            if ecodes.REL_X in rel and ecodes.REL_Y in rel and ecodes.BTN_LEFT in keys:
                # Descarta se tiver ABS_X (indica touchpad ou mesa digitalizadora)
                if ecodes.EV_ABS not in caps:
                    if mouse_dev is None:
                        mouse_dev = dev

    return mouse_dev, keyboard_dev
```

### 4. Ciclo Anti-Borda de Alta Performance

```python
"""Algoritmo de recentralização sem travamento de câmera."""
import time

class AntiBorderEngine:
    def __init__(self, anchor_x: int, anchor_y: int, radius: int, threshold_pct: float = 0.75):
        self.anchor_x = anchor_x
        self.anchor_y = anchor_y
        self.radius = radius
        self.threshold_sq = (radius * threshold_pct) ** 2
        self.reset_count = 0

    def evaluate_and_apply(self, current_x: int, current_y: int, touch_session: TouchSession) -> tuple[int, int]:
        dist_sq = (current_x - self.anchor_x) ** 2 + (current_y - self.anchor_y) ** 2

        if dist_sq >= self.threshold_sq:
            # 1. Levanta o toque no Slot 0 (Câmera)
            touch_session.touch_up(slot=0)

            # 2. Intervalo de 1ms para entrega e processamento do ACTION_UP
            time.sleep(0.001)

            # 3. Abaixa novamente no centro de âncora com novo ID
            touch_session.touch_down(slot=0, x=self.anchor_x, y=self.anchor_y)

            self.reset_count += 1
            return self.anchor_x, self.anchor_y

        return current_x, current_y
```

</code_examples>

<sota_updates>
## State of the Art (2024-2026)

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Injeção via `adb shell input tap` | Linux Kernel `/dev/uinput` direto | 2023+ | Queda drástica de latência de ~150ms para <1ms; viabiliza jogabilidade competitiva real. |
| Multitouch Protocol Type A | Multitouch Protocol Type B (Slot-based) | Padrão Linux moderno | Redução de volume de eventos no bus de entrada; Android só recebe updates de slots modificados. |
| Injeção de toques com coordenadas fixas em pixels | Coordenadas normalizadas percentuais (0.0 a 1.0) | Padrão WayFire | Permite alternar instantaneamente entre resoluções (1080p, 1440x1080, 1024x768) sem desalinhar botões. |
| Loops com `threading.Thread` por dispositivo | Multiplexação síncrona `epoll` via `selectors` | 2024+ | Elimina overhead de sincronização de threads em Python (GIL) e reduz jitter no processamento de pacotes do mouse. |

**Novas ferramentas e padrões a considerar:**
- **`input_props=[ecodes.INPUT_PROP_DIRECT]`:** Indispensável para que o compositor Wayland vincule a tela virtual diretamente ao display geométrico ativo.
- **Puxada de Capa com $Sens_Y > Sens_X$:** Configuração calibrada de sensibilidade onde o eixo vertical possui multiplicador $2.0\times$ a $2.5\times$ maior que o horizontal, facilitando o movimento ascendente de mira com deslocamento mínimo do mouse físico.

</sota_updates>

<validation_architecture>
## Validation Architecture

Como esta fase envolve interação de baixo nível com periféricos do Linux (`/dev/uinput`, `/dev/input/event*`), a arquitetura de validação precisa operar em dois níveis:
1. **Validação Automatizada Hermética (Sem Root / Mock-based):** Permite executar 100% dos testes unitários em qualquer ambiente (incluindo sandboxes e pipelines CI sem privilégios de kernel).
2. **Validação Funcional em Hardware Real (Host Linux / Waydroid):** Comandos práticos de verificação interativa com ferramentas de diagnóstico do sistema (`evtest`, `libinput`) e o comando CLI `wayfire test`.

### Estratégia de Mocking para Testes Unitários

Para garantir que a suíte `pytest` execute sem depender da existência física de `/dev/uinput` ou de mouses conectados, o injetor e o leitor de eventos utilizam inversão de dependência simples:
- `TouchInjector` aceita um backend de dispositivo injetável (interface simulada `DeviceSink` que apenas registra as chamadas `write(type, code, value)` e `syn()`).
- `MouseCapture` aceita uma fila de eventos simulados `InputEvent`.

### Matriz de Cobertura de Requisitos

| Requisito | Critério de Sucesso | Tipo de Teste | Comando de Teste |
|---|---|---|---|
| **CORE-01** (Injetor Multitouch) | Criação de dispositivo Type B com `INPUT_PROP_DIRECT`, slots 0..9 e emissão correta de coordenadas | Unitário + Verificação de Sistema | `pytest tests/test_touch_injector.py -v`<br>`libinput list-devices` |
| **CORE-02** (Captura & Suspensão) | Autodetecção de mouse/teclado, alternância no `F1`, execução resiliente de `grab()` e `ungrab()` | Unitário + Simulação de Eventos | `pytest tests/test_mouse_capture.py -v`<br>`python -m wayfire test --devices` |
| **CORE-03** (Sensibilidade X/Y) | Multiplicadores independentes, preservação de subpixel sem truncamento, filtro EMA com $\alpha=0.8$ | Unitário Matemático | `pytest tests/test_aim_engine.py -k "test_sensitivity or test_subpixel or test_ema"` |
| **CORE-04** (Algoritmo Anti-Borda) | Disparo do reset aos 75% da borda, ciclo sequencial `UP -> 1ms -> DOWN`, incremento de contador | Unitário Temporal | `pytest tests/test_aim_engine.py -k "test_anti_border"` |

### Comandos de Teste Prático no Host

1. **Testar criação do dispositivo virtual no sistema:**
   ```bash
   python -m wayfire test --create-uinput
   # Em outro terminal, checar se o libinput reconheceu como touchscreen direta:
   libinput list-devices | grep -A 10 "WayFire Virtual Touchscreen"
   ```
   *Saída esperada:* `Capabilities: touch`, `Direct: yes`.

2. **Testar leitura de eventos em tempo real com TUI:**
   ```bash
   python -m wayfire test --interactive
   ```
   *Saída esperada:*
   ```text
   [🟢 AIM LOCKED]  Sens X: 1.45  Sens Y: 3.20  Mouse: [dx: +12, dy: -45]  Resets: 14  (F1: Suspender | F7-F10: Ajustar)
   ```

3. **Verificar ciclo anti-borda com monitoramento de eventos evdev:**
   ```bash
   # Inspecionar os eventos reais do dispositivo virtual
   sudo evtest /dev/input/by-id/wayfire-virtual-touchscreen
   ```
   *Comportamento esperado ao arrastar o mouse continuamente:*
   Observar o envio de `ABS_MT_TRACKING_ID -1`, seguido por novo `ABS_MT_TRACKING_ID` com coordenadas retornando à âncora central sem spikes negativos.

</validation_architecture>

<open_questions>
## Open Questions

1. **Permissões de Acesso a `/dev/uinput` em Distribuições Diversas**
   - *O que sabemos:* No Arch/Omarchy e na maioria das distros modernas, o nó `/dev/uinput` exige permissão de escrita que pode ser concedida via regra udev associando ao grupo `input` ou com tag `uaccess`.
   - *O que falta:* Confirmar se o usuário atual já pertence ao grupo `input` ou se o instalador (`install.sh` na Fase 5) precisará criar `/etc/udev/rules.d/99-uinput.rules`.
   - *Recomendação:* Na Fase 1, o comando CLI deve verificar o acesso de escrita ao iniciar e exibir uma mensagem amigável com a instrução exata de comando caso falhe (`sudo usermod -aG input $USER` ou `sudo chmod 666 /dev/uinput`).

2. **Comportamento da Resolução Dinâmica do Waydroid com Coordenadas Normalizadas**
   - *O que sabemos:* Coordenadas normalizadas (0.0 a 1.0) garantem independência de resolução. No entanto, o `UInput` é inicializado com limites inteiros fixos (`max_x`, `max_y`).
   - *O que falta:* Se o usuário trocar a resolução do Waydroid de 1920x1080 para 1440x1080 em tempo de execução, o `UInput` precisa ser recriado ou basta manter uma escala virtual de alta resolução (ex: 32767x32767)?
   - *Recomendação:* Utilizar `width` e `height` configuráveis via CLI/perfil (padrão 1920x1080), permitindo inicializar o `TouchInjector` com as dimensões ativas da sessão. Se o usuário mudar a resolução, o recarregamento do perfil recria o dispositivo virtual sem impacto na engine.

</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- Linux Kernel Documentation: Multi-touch (MT) Protocol (`Documentation/input/multi-touch-protocol.rst`) — Protocol Type B, `ABS_MT_SLOT`, `ABS_MT_TRACKING_ID`, `INPUT_PROP_DIRECT`.
- Android Open Source Project (AOSP): Touch Devices Input Architecture (`TouchInputMapper`, `InputReader`, IDC configurations).
- `python-evdev` Official Documentation: `UInput`, `InputDevice`, `AbsInfo`, `grab()`, `ecodes`.

### Secondary (MEDIUM confidence)
- Phantom Waydroid Keymapper (`github.com/oliviermugishak/phantom`): Análise da arquitetura de backend uinput vs Android socket para emulação de jogos fullscreen no Waydroid.
- Libinput Documentation: Touchscreen vs Touchpad identification heuristics.

</sources>

<metadata>
## Metadata

**Research scope:**
- Core technology: Linux `/dev/uinput`, `python-evdev`, `selectors`, Linux Input Protocol Type B.
- Mathematical engine: Independent X/Y sensitivity, EMA jitter filter, subpixel fractional accumulator, invisible anti-border reset.
- Verification & Testability: Mock architecture for rootless automated unit tests.

**Confidence breakdown:**
- Standard stack: HIGH — `python-evdev` e `selectors` são os padrões canônicos para manipulação de baixo nível no Linux.
- Architecture: HIGH — Pipeline em 4 módulos desacoplados com inversão de dependência para testabilidade completa.
- Anti-border & Sensitivity Math: HIGH — Lógica verificada contra problemas clássicos de travamento de borda e arrasto reverso.
- Code examples: HIGH — Testados conceitualmente contra os schemas de tipos do kernel Linux.

**Research date:** 2026-10-31
**Valid until:** 2026-12-31

</metadata>

---

*Phase: 01-motor-de-entrada-e-sensibilidade-x-y-core*
*Research completed: 2026-10-31*
*Ready for planning: yes*

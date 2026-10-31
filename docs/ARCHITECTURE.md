# Arquitetura e Comunicação com o Waydroid

Este documento detalha tecnicamente **como o WayFire se comunica, controla e injeta dados no Waydroid**.

---

## 🏛️ Visão Geral da Arquitetura

O WayFire opera como uma aplicação companheira (*companion/wrapper*) que orquestra o Waydroid a partir do espaço de usuário do Linux:

```
┌────────────────────────────────────────────────────────┐
│                   WayFire (Host Linux)                 │
│                                                        │
│  ┌──────────────────────┐    ┌──────────────────────┐  │
│  │     Launcher UI      │    │    Keymap Editor     │  │
│  │ (GTK4 / Libadwaita)  │    │  (Overlay Wayland)   │  │
│  └──────────┬───────────┘    └──────────┬───────────┘  │
│             │                           │              │
│  ┌──────────▼───────────────────────────▼───────────┐  │
│  │          WayFire Core Engine (Python)            │  │
│  │                                                  │  │
│  │  - Captura bruta de Mouse/Teclado (/dev/input)   │  │
│  │  - Processador de Sensibilidade X / Y            │  │
│  │  - Normalizador de Resoluções e Coordenadas      │  │
│  └──────────┬───────────────────────────┬───────────┘  │
└─────────────┼───────────────────────────┼──────────────┘
              │                           │
  [1. Controle & Setup]         [2. Injeção de Toque <1ms]
  CLI / D-Bus / Propriedades     Linux Kernel /dev/uinput
              │                           │
┌─────────────▼───────────────────────────▼──────────────┐
│                    Waydroid (Android)                  │
│                                                        │
│  - Contêiner LXC compartilhando o Kernel Linux         │
│  - Compositor Wayland reconhece Virtual Touchscreen    │
│  - Jogo Free Fire recebe eventos de toque nativos      │
└────────────────────────────────────────────────────────┘
```

---

## 🔌 1. Controle de Ciclo de Vida e Configurações (CLI / Props)

Para preparar o ambiente antes de o jogo iniciar, o WayFire se comunica diretamente com a API de propriedades e controle do Waydroid:

### A. Troca de Resolução (Nativa ou Esticada)
O Waydroid suporta definição dinâmica das dimensões de tela:
```python
import subprocess

def set_resolution(width: int, height: int):
    # Altera as propriedades de vídeo do contêiner
    subprocess.run(["waydroid", "prop", "set", "persist.waydroid.width", str(width)], check=True)
    subprocess.run(["waydroid", "prop", "set", "persist.waydroid.height", str(height)], check=True)
```
* **Full HD Padrão**: `1920x1080` (16:9).
* **Competitiva Esticada**: `1440x1080` ou `1024x768` (4:3 esticado — aumenta o tamanho aparente dos alvos no jogo).

### B. Spoofing de Hardware (Desbloquear 90/120 FPS)
O Free Fire analisa o modelo do dispositivo para liberar os gráficos no "Ultra" e a taxa de quadros no "Alto (90/120 FPS)". O WayFire injeta propriedades de um dispositivo gamer reconhecido:
```ini
ro.product.brand = asus
ro.product.manufacturer = asus
ro.product.model = ASUS_I005D
ro.product.name = ASUS_I005D
```

### C. Inicialização Automática do Jogo
Em vez de abrir o menu do Android e esperar o usuário clicar no ícone:
```bash
waydroid app launch com.dts.freefireth
```

---

## ⚡ 2. Pipeline de Entrada: Como os Toques Chegam no Android

Esta é a parte mais crítica. Em jogos competitivos de tiro, **latência é inadmissível**.

### Comparação das Abordagens:
| Método | Latência | Estabilidade | Viabilidade no WayFire |
| :--- | :--- | :--- | :--- |
| **Comando `adb shell input tap`** | ~100ms - 200ms | Péssima | ❌ Inutilizável para jogos de tiro. |
| **Servidor Scrcpy via Socket ADB** | ~10ms - 20ms | Média (exige autorização ADB) | ⚠️ Funciona, mas complexo e suscetível a erros de conexão. |
| **Linux `uinput` Virtual Multitouch** | **< 1ms (Instantâneo)** | **Máxima (Nativa do Kernel)** | ✅ **Abordagem Oficial do WayFire**. |

### Como funciona o `uinput` (A abordagem WayFire):
1. O WayFire cria um dispositivo virtual de tela sensível ao toque (*Virtual Multitouch Screen*) diretamente no kernel Linux usando a biblioteca `python-evdev`.
2. Como o Waydroid roda sobre o Wayland do host, o compositor do Linux repassa esse dispositivo virtual diretamente para a camada de entrada do Android (`/dev/input/event*`).
3. O Android enxerga o WayFire como se fosse uma **tela touch física real de celular conectada ao computador**.
4. **Zero necessidade de ativar Depuração USB ou ADB.**

#### Especificação do Dispositivo Virtual Criado pelo WayFire:
```python
from evdev import UInput, ecodes, AbsInfo

capabilities = {
    ecodes.EV_KEY: [ecodes.BTN_TOUCH],
    ecodes.EV_ABS: [
        (ecodes.ABS_MT_SLOT, AbsInfo(value=0, min=0, max=9, fuzz=0, flat=0, resolution=0)),
        (ecodes.ABS_MT_TRACKING_ID, AbsInfo(value=0, min=0, max=65535, fuzz=0, flat=0, resolution=0)),
        (ecodes.ABS_MT_POSITION_X, AbsInfo(value=0, min=0, max=1920, fuzz=0, flat=0, resolution=0)),
        (ecodes.ABS_MT_POSITION_Y, AbsInfo(value=0, min=0, max=1080, fuzz=0, flat=0, resolution=0)),
    ]
}

# Dispositivo registrado diretamente no Kernel Linux
virtual_touch = UInput(capabilities, name="WayFire Virtual Touchscreen")
```

---

## 🎯 3. Matemática da Mira (Conversão de Mouse para Touch)

O mouse do computador emite **movimento relativo** (`dx`, `dy`), enquanto uma tela touchscreen espera **coordenadas absolutas** (`x`, `y`).

### O Algoritmo da Câmera (Aim Lock / Mira FPS):
1. **Região de Toque Virtual**: É definida uma área retangular no lado direito da tela (zona onde o polegar normalmente desliza no celular para mirar).
2. **Ponto de Âncora ($X_0, Y_0$)**: Ao apertar a tecla de suspender (travar o mouse), o WayFire inicia um toque nessa coordenada central da zona de mira.
3. **Cálculo de Deslocamento com Sensibilidade**:
   $$X_{novo} = X_{atual} + (dx \times Sens_X)$$
   $$Y_{novo} = Y_{atual} + (dy \times Sens_Y)$$
4. **Reset Silencioso (Anti-Borda)**: Se o movimento acumulado se aproximar das bordas da zona de mira, o WayFire rapidamente:
   * Levanta o toque virtual (`TRACKING_ID = -1`).
   * Abaixa o toque novamente no centro ($X_0, Y_0$).
   * *Tempo do ciclo: 1 milissegundo.* O jogo nem percebe a transição, garantindo rotação 360° infinita sem travar na borda da tela.

# Phase 1: Motor de Entrada e Sensibilidade X/Y (Core) - Pattern Map

**Phase:** 01-motor-de-entrada-e-sensibilidade-x-y-core  
**Status:** Greenfield (Phase 1 Baseline)  
**Established from:** `docs/ARCHITECTURE.md`, `01-CONTEXT.md`, and `01-RESEARCH.md`

## Overview

Como a Fase 1 inicia o desenvolvimento do WayFire a partir de um repositório limpo (*greenfield*), não há arquivos de código legados pré-existentes no repositório. Todos os padrões arquiteturais, convenções de tipagem e fluxos de dados abaixo são definidos a partir do design canônico estabelecido na documentação de arquitetura e na pesquisa técnica da fase.

---

## File Classification

| File Path | Role | Data Flow | Primary Responsibilities |
|---|---|---|---|
| `src/wayfire/__init__.py` | config/init | package | Exportação de versão e metadados base do pacote `wayfire`. |
| `src/wayfire/core/touch_injector.py` | service | event-driven | Inicialização e emissão de eventos multitouch (`ABS_MT_SLOT`, `ABS_MT_POSITION_X/Y`, `BTN_TOUCH`) via `/dev/uinput`. |
| `src/wayfire/core/mouse_capture.py` | service | event-driven (epoll) | Detecção e multiplexação de mouse/teclado via `selectors`, captura exclusiva (`grab()`) e liberação (`ungrab()`) na hotkey `F1`. |
| `src/wayfire/core/aim_engine.py` | service | transform / math | Conversão de deltas relativos ($dx, dy$) para coordenadas absolutas touch, sensibilidade $X/Y$, filtro anti-jitter (EMA), acumulador de subpixel e reset anti-borda (1ms). |
| `src/wayfire/cli/main.py` | controller | request-response / CLI | Ponto de entrada CLI (`wayfire run`, `wayfire test`), parsing de argumentos com `argparse`, exibição de TUI interativa. |
| `src/wayfire/config/profile.py` | model/config | file-I/O / JSON | Carregamento, validação e persistência de perfis de sensibilidade e mapeamento JSON. |
| `tests/conftest.py` | test fixture | testing | Mocks de `evdev.InputDevice`, `evdev.UInput` e injeção de dependências para execução de testes unitários sem privilégios de root. |
| `tests/test_touch_injector.py` | test | unit test | Validação de capacidades uinput, emissão de slots MT, sincronismo de `BTN_TOUCH` e liberação correta de tracking IDs. |
| `tests/test_aim_engine.py` | test | unit test | Teste da fórmula matemática $X/Y$, acumulador fracionário, suavização EMA e trigger do reset anti-borda a 75%. |
| `tests/test_mouse_capture.py` | test | unit test | Validação do parsing de eventos relativos e alternância de estado travado/suspenso. |

---

## Standard Code Patterns

### 1. Injeção de Dependência e Fallback para Testabilidade
Para permitir testes 100% automatizados sem necessidade de `/dev/uinput` real ou permissões de root em CI/desenvolvimento:

```python
from typing import Optional, Protocol, Any

class UInputDevice(Protocol):
    def write(self, etype: int, code: int, value: int) -> None: ...
    def syn(self) -> None: ...
    def close(self) -> None: ...

class TouchInjector:
    def __init__(self, uinput_dev: Optional[UInputDevice] = None, screen_res: tuple[int, int] = (1920, 1080)):
        self.screen_res = screen_res
        self.dev = uinput_dev or self._create_real_uinput()
```

### 2. Tratamento Seguro de Recursos e Sinais do Sistema (Signal Safety)
Garantir que exceções, `SIGINT` (Ctrl+C) ou `SIGTERM` sempre executem `ungrab()` e fechem descritores para nunca travar o mouse do host:

```python
import signal
import sys

def register_cleanup_handlers(capture_service):
    def _sig_handler(signum, frame):
        capture_service.cleanup()
        sys.exit(0)
    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)
```

### 3. Loop de Multiplexação com `selectors.DefaultSelector`
Multiplexação determinística sem o overhead de loop de eventos assíncrono:

```python
import selectors

selector = selectors.DefaultSelector()
selector.register(mouse_device.fd, selectors.EVENT_READ, data="mouse")
selector.register(keyboard_device.fd, selectors.EVENT_READ, data="keyboard")

while running:
    events = selector.select(timeout=0.01)
    for key, mask in events:
        handle_device_events(key.data)
```

---

## Common Pitfalls & Anti-Patterns to Avoid

- **Nunca usar `asyncio` no loop de baixa latência:** A alternância de contexto do `asyncio` pode introduzir jitter de 2-5ms. Usar polling síncrono com `epoll` / `selectors`.
- **Nunca deixar de liberar `BTN_TOUCH`:** O Waydroid e o Android continuam interpretando toque fantasma se `BTN_TOUCH` não for zerado após soltar todos os slots.
- **Nunca fazer reset anti-borda sem intervalo (0ms):** Enviar `UP` e `DOWN` no mesmo instante pode ser interpretado pelo jogo como movimento instantâneo da borda para o centro (puxão reverso de câmera). O intervalo obrigatório é 1ms com coordenadas na âncora central.

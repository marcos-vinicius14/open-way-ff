---
phase: 03-editor-visual-de-teclas-overlay-wayland
date: 2026-10-31
status: ready-for-planning
requirements: [MAP-02, UI-01, UI-02]
decisions_addressed: [D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-08, D-09, D-10, D-11, D-12, D-13, D-14, D-15, D-16]
---

# Phase 3: Editor Visual de Teclas (Overlay Wayland) - Research & Technical Architecture

## 1. Executive Summary

A **Fase 3** constrói o editor visual interativo e a camada OSD transparente sobreposta ao Waydroid via Wayland Layer Shell (`zwlr_layer_shell_v1` através de `gtk4-layer-shell`), integrando a captura física de periféricos com a injeção uinput de multitouch e persistência reativa em `ProfileManager`.

### Objetivos Nucleares:
1. **Overlay Transparente Wayland (UI-01):** Janela GTK4 fullscreen ancorada nas quatro bordas via `gtk4-layer-shell` na camada `LAYER_OVERLAY` com `exclusive_zone = -1`. Em Modo de Jogo, a superfície define sua região de entrada como vazia (`cairo.Region()`), garantindo pass-through total de cliques e toques para o jogo sem adicionar latência.
2. **Editor Visual Estilo GG Mouse Pro (UI-02):** Em Modo de Edição (`F2` ou banner interativo ao suspender com `F1`), a região de entrada cobre a tela inteira. Um duplo clique em qualquer coordenada cria instantaneamente uma bolinha visual em estado de escuta pulsante `[ ? ]`, vinculando imediatamente a próxima tecla física (teclado ou botões do mouse). Suporta arrastar, redimensionar áreas e excluir (`Del`/`Backspace` ou lixeira).
3. **Mapeamento Polimórfico de Componentes & Macros (MAP-02):** Suporte nativo a `TapWidget` (Single, Hold, Turbo), `DPadWidget` (analógico WASD de 8 direções), `AimWidget` (área de mira) e `FireWidget` (gatilho). Suporte inédito a **Macros Sequenciais** numerados (1, 2, 3...) disparados por uma única tecla com intervalo configurável (padrão 30ms) executados sem bloqueio na thread de input.
4. **Persistência Contínua e Responsiva:** Auto-save com debounce de 500ms salvando no perfil ativo (`~/.config/wayfire/profiles/`), permitindo ajustes imediatos sem interrupção do fluxo de jogo.

---

## 2. Architecture & Technical Domain

### 2.1 Wayland Layer Shell & Input Region Dynamics (D-01, D-04)

O protocolo `zwlr_layer_shell_v1` é o padrão moderno em compositores Wayland (Hyprland, Sway, KDE Wayland) para renderizar superfícies do sistema sobre clientes normais sem participar de regras de tiling ou paginação de janelas.

#### Configuração de Camada e Exclusividade
- **Camada:** `Gtk4LayerShell.Layer.OVERLAY` — desenha acima de janelas fullscreen normais (Waydroid).
- **Âncoras:** `TOP`, `BOTTOM`, `LEFT`, `RIGHT` todas habilitadas para cobrir 100% da viewport do monitor.
- **Zona Exclusiva:** `set_exclusive_zone(window, -1)` — compositor não reserva espaço de tela e ignora painéis/barras de tarefas.
- **Namespace:** `"wayfire-overlay"`.

#### Dinâmica de Input Region (Pass-Through vs Captura)
No Wayland, a capacidade de clicar através de uma superfície é governada por `wl_surface.set_input_region()`, acessível em GTK4 por `gdk_surface_set_input_region(surface, region)`:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           MODO DE JOGO (LOCKED)                         │
│                                                                         │
│  Gdk.Surface.set_input_region(cairo.Region()) [VAZIO]                   │
│  ──> 100% dos cliques do mouse passam direto para o Waydroid/Jogo       │
│  ──> KeyboardMode = NONE (Foco 100% no Waydroid/Kernel)                 │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼ [F1: Suspender Mouse]
┌─────────────────────────────────────────────────────────────────────────┐
│                         MODO DE JOGO (SUSPENDED)                        │
│                                                                         │
│  Pill Topo: [🔓 MOUSE LIVRE [F1] | ⚙️ Editar Teclas]                     │
│  Gdk.Surface.set_input_region(cairo.Region(pill_rect))                  │
│  ──> Apenas a área do banner (ex: 280x36px) intercepta cliques         │
│  ──> O restante (99% da tela) permanece pass-through transparente       │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼ [F2 ou Clique em '⚙️ Editar Teclas']
┌─────────────────────────────────────────────────────────────────────────┐
│                             MODO DE EDIÇÃO                              │
│                                                                         │
│  Gdk.Surface.set_input_region(None) [TELA CHEIA]                        │
│  ──> Superfície inteira intercepta cliques, duplo clique e arrastes     │
│  ──> KeyboardMode = ON_DEMAND (Permite escuta de teclas nas bolinhas)   │
│  ──> Barra de ferramentas retrátil e alças de redimensionamento ativas   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Alternância Híbrida de Modo e Atalhos Globais (D-02, D-10, D-15)

O WayFire possui três atalhos globais de sistema:
- **`F1` (Trava de Mira):** Suspende / bloqueia o cursor do mouse e alterna a captura de movimento da câmera.
- **`F2` (Modo de Edição):** Entra ou sai imediatamente do editor visual interativo.
- **`F3` (Toggle OSD):** Alterna a visibilidade das teclas no HUD (0% vs `osd_opacity`).

```
[Captura de Baixo Nível: InputCaptureManager (evdev)]
       │
       ├─ EV_KEY KEY_F1 ──> toggle_aim_lock() ──> Notifica Overlay (Atualiza Pill & Input Region)
       ├─ EV_KEY KEY_F2 ──> toggle_edit_mode() ──> Notifica Overlay (Alterna Tela Cheia vs Pass-Through)
       ├─ EV_KEY KEY_F3 ──> toggle_osd_visibility() ──> Notifica Overlay (0% vs Opacidade Salva)
       └─ Outras Teclas  ──> KeymapEngine (Injeta toques uinput no jogo)
```

> **Aviso de Teclas Reservadas (D-15):** Se o usuário tentar mapear `F1`, `F2` ou `F3` para uma bolinha no editor, a interface exibe um `Adw.Toast` amigável: *"As teclas F1, F2 e F3 são reservadas para controle do sistema (Mira, Editor e OSD). Reconfigure os atalhos globais se desejar utilizá-las no jogo."*

---

## 3. Component & Widget Hierarchy

### 3.1 Camada Visual GTK4 & Libadwaita

A interface do overlay é composta por uma hierarquia modular de widgets GTK4 dispostos sobre um layout absoluto:

```
Adw.ApplicationWindow (ou Gtk.Window com Gtk4LayerShell)
 └── Adw.ToastOverlay (para notificações e avisos de instância única)
      └── Gtk.Overlay
           ├── Gtk.Fixed (Canvas de Mapeamento Absoluto)
           │    ├── TapWidgetView (círculos de toque estilo GG Mouse Pro)
           │    ├── DPadWidgetView (analógico virtual WASD com alça de raio)
           │    ├── AimWidgetView (área retangular de mira com alças nos cantos)
           │    ├── FireWidgetView (ícone de gatilho/fogo)
           │    └── MacroSequenceView (bolinhas numeradas [Key #1], [Key #2]...)
           │
           ├── FloatingTopBar (Barra superior retrátil no Modo de Edição)
           │    ├── [🕹️ DPad]
           │    ├── [🎯 Mira FPS]
           │    ├── [🔥 Tiro]
           │    ├── [+ Botão]
           │    ├── OpacitySlider (0% a 100%)
           │    └── [✖ Concluir e Salvar]
           │
           └── StatusPill (Banner flutuante no topo em Modo de Jogo)
                ├── '🎯 MIRA TRAVADA' (Verde com fade-out de 1.5s)
                └── '🔓 MOUSE LIVRE [F1] | ⚙️ Editar Teclas' (Amarelo persistente)
```

### 3.2 Visualização OSD e Estilo GG Mouse Pro (D-09, D-11, D-12)

- **Aparência dos Botões (`TapWidgetView`):**
  - Círculo translúcido de raio 24px (diâmetro 48px).
  - Fundo escuro semi-transparente (`rgba(20, 20, 25, 0.70)`).
  - Borda de 2px sólida (`rgba(255, 255, 255, 0.85)`).
  - Rótulo compacto e em negrito centralizado (ex: `SPC`, `SHF`, `M4`, `E`).
  - Estado de Escuta `[ ? ]`: borda pulsante ciano (`#00e5ff`) com animação CSS suave.
  - Feedback ao Pressionar (`.pressed`): brilho alaranjado competitivo (`#ff5000`) com leve expansão de escala (+10%), retornando ao normal ao soltar a tecla física.
- **Visual do D-Pad (`DPadWidgetView`):**
  - Círculo externo demarcando o raio de alcance com linha tracejada fina.
  - Âncora central com direções `W`, `A`, `S`, `D`.
  - Alça circular na borda direita/superior para redimensionar o raio por arrasto.
- **Visual da Mira FPS (`AimWidgetView`):**
  - Retângulo delimitador pontilhado com mira central `+`.
  - Alças interativas nos 4 cantos para redimensionar largura e altura.
  - Popover contextual para calibrar `sens_x` e `sens_y` diretamente sobre o jogo.

### 3.3 Regras de Instância Única (D-08)

- **Instância Única:** Apenas **1** `AimWidget` e **1** `DPadWidget` são permitidos por perfil.
- Se o jogador clicar para adicionar ou arrastar um segundo DPad ou Mira da barra de ferramentas:
  1. A interface não cria um elemento duplicado.
  2. O widget existente é suavemente animado e recentralizado na coordenada clicada.
  3. Um toast informativo é disparado via `Adw.Toast`: *"Apenas um Analógico WASD / Mira FPS é permitido. O componente existente foi reposicionado."*
- `TapWidget` e `FireWidget` podem ser criados em quantidade ilimitada.

---

## 4. Standard Stack, Libraries & Dependencies

### 4.1 Bibliotecas & Módulos Disponíveis no Sistema

| Biblioteca | Versão / Namespace | Disponibilidade no Sistema | Uso no WayFire |
|---|---|---|---|
| `python-gobject` (PyGObject) | `3.56.3` / `gi` | Instalado (`/usr/lib/python3.14/site-packages/gi`) | Binding principal GTK4/Adw |
| `gtk4` | `4.0` (`gi.repository.Gtk`) | Instalado e testado | Janelas, layout `Gtk.Fixed`, gestos e controles |
| `libadwaita` | `1` (`gi.repository.Adw`) | Instalado e testado | Estilização moderna, `ToastOverlay`, `Toast` |
| `gtk4-layer-shell` | `1.0` (`gi.repository.Gtk4LayerShell`) | Instalado (`/usr/lib/libgtk4-layer-shell.so`) | Camada de overlay Wayland sobre o Waydroid |
| `cairo` (`pycairo`) | `1.29.1` (`import cairo`) | Instalado e testado | Manipulação de `cairo.Region` para pass-through |
| `evdev` | `1.9.1` (`import evdev`) | Instalado no venv | Captura física de periféricos e injeção uinput |

### 4.2 Padronização de Teclas & Conversão de Nomes (D-14)

A tabela abaixo unifica a representação entre o schema JSON, o rótulo do OSD e os códigos evdev:

| Tecla / Periférico | Schema JSON (Canônico) | Rótulo Compacto OSD | Código evdev | GDK Keyval / Botão |
|---|---|---|---|---|
| Barra de Espaço | `"Space"` | `"SPC"` | `ecodes.KEY_SPACE` | `Gdk.KEY_space` |
| Shift Esquerdo | `"Shift_L"` | `"SHF"` | `ecodes.KEY_LEFTSHIFT` | `Gdk.KEY_Shift_L` |
| Control Esquerdo | `"Control_L"` | `"CTL"` | `ecodes.KEY_LEFTCTRL` | `Gdk.KEY_Control_L` |
| Alt Esquerdo | `"Alt_L"` | `"ALT"` | `ecodes.KEY_LEFTALT` | `Gdk.KEY_Alt_L` |
| Tab | `"Tab"` | `"TAB"` | `ecodes.KEY_TAB` | `Gdk.KEY_Tab` |
| Caps Lock | `"Caps_Lock"` | `"CPS"` | `ecodes.KEY_CAPSLOCK` | `Gdk.KEY_Caps_Lock` |
| Enter / Return | `"Return"` | `"ENT"` | `ecodes.KEY_ENTER` | `Gdk.KEY_Return` |
| Botão Lateral Mouse 4 | `"Mouse_4"` | `"M4"` | `ecodes.BTN_SIDE` | Mouse Button 8 |
| Botão Lateral Mouse 5 | `"Mouse_5"` | `"M5"` | `ecodes.BTN_EXTRA` | Mouse Button 9 |
| Botão Direito Mouse | `"Mouse_Right"` | `"RMB"` | `ecodes.BTN_RIGHT` | Mouse Button 3 |
| Botão do Meio (Scroll) | `"Mouse_Middle"` | `"MMB"` | `ecodes.BTN_MIDDLE` | Mouse Button 2 |
| Botão Esquerdo Mouse | `"Mouse_Left"` | `"LMB"` | `ecodes.BTN_LEFT` | Mouse Button 1 |
| Letras (ex: E, R, C, F) | `"E"`, `"R"`, `"C"`, `"F"` | `"E"`, `"R"`, `"C"`, `"F"` | `ecodes.KEY_E`, etc. | `Gdk.KEY_e`, `Gdk.KEY_E` |
| Números (ex: 1, 2, 3, 4) | `"1"`, `"2"`, `"3"`, `"4"` | `"1"`, `"2"`, `"3"`, `"4"` | `ecodes.KEY_1`, etc. | `Gdk.KEY_1` |

---

## 5. Implementation Patterns & Code Skeletons

### 5.1 Inicialização do Overlay com Gtk4LayerShell e Fallback (D-04)

```python
"""Overlay window setup with Gtk4LayerShell and automatic graceful fallback."""
from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
try:
    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gtk4LayerShell
    HAS_LAYER_SHELL = True
except (ValueError, ImportError):
    HAS_LAYER_SHELL = False

from gi.repository import Adw, Gdk, Gtk
import cairo


class WayFireOverlayWindow(Gtk.ApplicationWindow):
    """Fullscreen transparent overlay supporting Wayland Layer Shell pass-through."""

    def __init__(self, app: Gtk.Application) -> None:
        super().__init__(application=app, title="WayFire Overlay")
        self.is_layer_shell_active = False

        # Apply CSS for full transparency
        self.add_css_class("wayfire-overlay-window")

        # Layer Shell initialization MUST occur before window is realized/mapped
        if HAS_LAYER_SHELL and self._can_use_layer_shell():
            Gtk4LayerShell.init_for_window(self)
            Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.OVERLAY)
            Gtk4LayerShell.set_namespace(self, "wayfire-overlay")
            Gtk4LayerShell.set_exclusive_zone(self, -1)

            # Anchor to all four edges for true fullscreen
            for edge in (
                Gtk4LayerShell.Edge.TOP,
                Gtk4LayerShell.Edge.BOTTOM,
                Gtk4LayerShell.Edge.LEFT,
                Gtk4LayerShell.Edge.RIGHT,
            ):
                Gtk4LayerShell.set_anchor(self, edge, True)

            # In game mode, keyboard mode is NONE so Waydroid retains focus
            Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.NONE)
            self.is_layer_shell_active = True
        else:
            # Fallback for X11/Xvfb or compositors lacking layer-shell
            self.fullscreen()

        self.connect("realize", self._on_realize)

    def _can_use_layer_shell(self) -> bool:
        display = Gdk.Display.get_default()
        if display is None:
            return False
        try:
            return Gtk4LayerShell.is_supported()
        except Exception:
            return False

    def _on_realize(self, widget: Gtk.Widget) -> None:
        """Set default game mode (empty input region) upon realization."""
        self.set_game_mode(suspended=False)

    def set_game_mode(self, suspended: bool = False, pill_rect: cairo.RectangleInt | None = None) -> None:
        """Switch to Game Mode with empty input region (pass-through) or pill-only region."""
        surface = self.get_surface()
        if not surface:
            return

        if self.is_layer_shell_active:
            Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.NONE)

        if not suspended:
            # 100% pass-through: empty input region
            empty_region = cairo.Region()
            surface.set_input_region(empty_region)
        else:
            # Suspended mode: only the top pill banner intercepts clicks
            if pill_rect is not None:
                region = cairo.Region(pill_rect)
                surface.set_input_region(region)
            else:
                surface.set_input_region(cairo.Region())

    def set_edit_mode(self) -> None:
        """Switch to Edit Mode: full-screen interactive input region and on-demand keyboard."""
        surface = self.get_surface()
        if not surface:
            return

        if self.is_layer_shell_active:
            Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.ON_DEMAND)

        # Passing None to set_input_region restores full-window input capture
        surface.set_input_region(None)
```

### 5.2 Fluxo GG Mouse Pro: Duplo Clique e Captura Imediata (D-05, D-13, UI-02)

```python
"""Interactive GG Mouse Pro button creation flow."""
from gi.repository import Gdk, Gtk
from wayfire.config.widgets import TapWidget


class OverlayCanvas(Gtk.Fixed):
    """Canvas container handling gestures and widget lifecycle."""

    def __init__(self, on_widget_created_cb, on_profile_modified_cb) -> None:
        super().__init__()
        self.on_widget_created_cb = on_widget_created_cb
        self.on_profile_modified_cb = on_profile_modified_cb
        self.active_listening_widget: TapWidgetView | None = None

        # Double click gesture on empty canvas
        self.click_gesture = Gtk.GestureClick.new()
        self.click_gesture.set_button(0)  # Listen to all mouse buttons
        self.click_gesture.connect("pressed", self._on_canvas_pressed)
        self.add_controller(self.click_gesture)

        # Global key controller for listening state
        self.key_controller = Gtk.EventControllerKey.new()
        self.key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(self.key_controller)

    def _on_canvas_pressed(self, gesture: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        btn = gesture.get_current_button()
        if n_press == 2 and btn == 1:  # Double click with left mouse button
            self.create_listening_tap(x, y)

    def create_listening_tap(self, x: float, y: float) -> None:
        # Cancel any previous widget that was waiting for key
        if self.active_listening_widget is not None:
            self.cancel_listening_widget()

        # Create new TapWidget model at (x, y)
        widget_id = f"tap_{int(x)}_{int(y)}"
        tap_model = TapWidget(id=widget_id, key="?", x=x, y=y, mode="single")
        
        # Instantiate visual view
        view = TapWidgetView(tap_model, on_rebound=self._on_widget_rebound)
        view.set_listening(True)
        self.put(view, x - 24, y - 24)  # Center 48x48 circle on click
        self.active_listening_widget = view

    def _on_key_pressed(
        self,
        controller: Gtk.EventControllerKey,
        keyval: int,
        keycode: int,
        state: Gdk.ModifierType,
    ) -> bool:
        if self.active_listening_widget is None:
            return False

        if keyval == Gdk.KEY_Escape:
            self.cancel_listening_widget()
            return True

        canonical_key = keyval_to_canonical_name(keyval)
        if is_reserved_key(canonical_key):
            self.show_toast(f"A tecla {canonical_key} é reservada pelo sistema (F1/F2/F3).")
            return True

        # Bind key to widget
        self.active_listening_widget.bind_key(canonical_key)
        self.active_listening_widget = None
        self.on_profile_modified_cb()
        return True

    def cancel_listening_widget(self) -> None:
        if self.active_listening_widget:
            self.remove(self.active_listening_widget)
            self.active_listening_widget = None
```

### 5.3 Modelo e Fila Não-Bloqueante de Macros Sequenciais (D-16)

```python
"""Sequential Macro data model and non-blocking scheduling queue."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any
from wayfire.config.widgets import BaseWidget


@dataclass
class MacroStep:
    """Single touch action within a sequential macro."""
    x: float | int
    y: float | int
    delay_ms: int = 30  # Milliseconds to wait before executing next step


@dataclass
class MacroWidget(BaseWidget):
    """Sequential macro component triggering a series of ordered touches."""
    key: str = ""
    steps: list[MacroStep] = field(default_factory=list)
    delay_ms: int = 30
    x: float | int = 0
    y: float | int = 0
    type: str = "macro"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "key": self.key,
            "x": self.x,
            "y": self.y,
            "delay_ms": self.delay_ms,
            "steps": [
                {"x": s.x, "y": s.y, "delay_ms": s.delay_ms}
                for s in self.steps
            ],
        }


class NonBlockingMacroScheduler:
    """Executes sequential macro taps via selector event loop without sleeping."""

    def __init__(self, injector, slot_start: int = 4, slot_end: int = 9) -> None:
        self.injector = injector
        self.available_slots = list(range(slot_start, slot_end + 1))
        # Items: (fire_at_timestamp, action, slot, x, y)
        self.queue: list[tuple[float, str, int, int, int]] = []

    def trigger_macro(self, macro: MacroWidget) -> None:
        """Schedule steps in non-blocking queue using monotonic timestamps."""
        if not self.available_slots or not macro.steps:
            return

        slot = self.available_slots.pop(0)
        current_time = time.monotonic()
        accumulated_delay = 0.0

        for idx, step in enumerate(macro.steps):
            touch_down_time = current_time + accumulated_delay
            touch_up_time = touch_down_time + 0.015  # 15ms pulse duration

            self.queue.append((touch_down_time, "down", slot, int(step.x), int(step.y)))
            self.queue.append((touch_up_time, "up", slot, int(step.x), int(step.y)))

            accumulated_delay += (step.delay_ms or macro.delay_ms) / 1000.0

        # Mark slot for recycling after sequence completes
        self.queue.append((current_time + accumulated_delay + 0.01, "release_slot", slot, 0, 0))

    def process_scheduled(self) -> None:
        """Called every poll cycle in the low-latency loop (zero sleep)."""
        if not self.queue:
            return

        now = time.monotonic()
        remaining: list[tuple[float, str, int, int, int]] = []

        for item in self.queue:
            fire_at, action, slot, x, y = item
            if now >= fire_at:
                if action == "down":
                    self.injector.touch_down(slot=slot, x=x, y=y)
                elif action == "up":
                    self.injector.touch_up(slot=slot)
                elif action == "release_slot":
                    if slot not in self.available_slots:
                        self.available_slots.append(slot)
            else:
                remaining.append(item)

        self.queue = remaining
```

### 5.4 Auto-Save Reativo com Debounce de 500ms (D-03)

```python
"""500ms debounced persistence to active profile."""
from gi.repository import GLib
from wayfire.config.profile import WayFireProfile
from wayfire.config.profile_manager import ProfileManager


class ProfileDebounceSaver:
    """Coalesces rapid visual edits into a single atomic profile save."""

    def __init__(self, profile_manager: ProfileManager, debounce_ms: int = 500) -> None:
        self.profile_manager = profile_manager
        self.debounce_ms = debounce_ms
        self._source_id: int | None = None
        self._pending_profile: WayFireProfile | None = None

    def request_save(self, profile: WayFireProfile) -> None:
        """Postpone disk write until 500ms of inactivity."""
        self._pending_profile = profile
        if self._source_id is not None:
            GLib.source_remove(self._source_id)

        self._source_id = GLib.timeout_add(self.debounce_ms, self._execute_save)

    def _execute_save(self) -> bool:
        if self._pending_profile is not None:
            try:
                self.profile_manager.save_profile(self._pending_profile)
            except OSError:
                pass
            self._pending_profile = None
        self._source_id = None
        return GLib.SOURCE_REMOVE

    def flush(self) -> None:
        """Immediately commit any pending changes upon editor exit."""
        if self._source_id is not None:
            GLib.source_remove(self._source_id)
            self._execute_save()
```

---

## 6. Common Pitfalls & Landmines

### 1. Chamada Prematura de `init_for_window`
- **Problema:** Chamar `Gtk4LayerShell.init_for_window(window)` após a janela ter sido realizada (`realize`) ou apresentada (`present`) resulta em `g_warning` ou falha silenciosa do protocolo Wayland.
- **Solução:** Chamar `init_for_window()` e todas as chamadas de configuração de âncora/camada no `__init__` da janela antes de qualquer chamada a `window.present()`.

### 2. Segfault em Construtores GTK4 sem Conexão de Display
- **Problema:** No GTK4 sob Linux, instanciar `Gtk.Fixed()` ou `Gtk.Window()` sem um display ativo (`Gdk.Display.get_default() == None`) provoca `SIGSEGV (code 139)` em chamadas internas do Mesa/EGL.
- **Solução:** Em suítes de teste (como pytest no sandbox ou CI), componentes visuais que tocam widgets GTK devem rodar sob `xvfb-run` ou ter a camada gráfica isolada através de mocks / adaptadores. A lógica pura (modelos, conversores de teclas, scheduler de macros) deve ser desacoplada da GUI.

### 3. Conflito de Foco e Roubo de Teclado no Modo de Jogo
- **Problema:** Se o overlay solicitar foco de teclado (`KeyboardMode.EXCLUSIVE` ou `ON_DEMAND`) durante a partida, o Waydroid e o Free Fire param de receber eventos e perdem foco da janela.
- **Solução:** No Modo de Jogo, o `KeyboardMode` é estritamente `Gtk4LayerShell.KeyboardMode.NONE`. O overlay só muda para `ON_DEMAND` quando o Modo de Edição for ativado explicitamente via `F2` ou pelo banner flutuante.

### 4. Orfandade de `Gtk.Popover` ao Destruir Widgets
- **Problema:** Remover um widget filho do `Gtk.Fixed` que possua um `Gtk.Popover` aberto ou anexado emite aviso crítico de widget órfão (`Gtk-WARNING: Finalizing GtkButton ..., but it still has children left: GtkPopover`).
- **Solução:** Chamar explicitamente `popover.unparent()` e `popover.popdown()` antes de invocar `fixed.remove(widget_view)`.

### 5. Escala de Resolução Esticada (1440x1080 vs Monitor Físico)
- **Problema:** A resolução do monitor físico pode ser 1920x1080 ou 2560x1440, enquanto o perfil do Free Fire opera em 1440x1080 (esticado competitivo 4:3). Se as coordenadas do clique do mouse forem salvas cruas em pixels da tela física, os botões ficarão desalinhados no Waydroid.
- **Solução:** Normalizar todas as coordenadas relativas ao `ResolutionConfig` do perfil ativo:
  $$\text{x\_profile} = \left(\frac{\text{x\_screen}}{\text{width\_screen}}\right) \times \text{width\_profile}$$
  $$\text{y\_profile} = \left(\frac{\text{y\_screen}}{\text{height\_screen}}\right) \times \text{height\_profile}$$

### 6. Concorrência entre Thread de Input (evdev) e Main Loop do GTK
- **Problema:** Disparar atualizações visuais de widgets (como pulso `.pressed` da bolinha) diretamente da thread de polling do evdev causa concorrência de memória e travamento no GTK.
- **Solução:** Enfileirar todas as alterações de interface vindas do evdev através de `GLib.idle_add(callback, *args)`.

---

## 7. Validation & Testing Strategy

A estratégia de testes da Fase 3 divide-se em três níveis para garantir cobertura completa:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        SUÍTE DE TESTES DA FASE 3                       │
├────────────────────────────────┬───────────────────────────────────────┤
│ 1. Testes Unitários Puros       │ - Normalização de coordenadas         │
│    (Rápidos, sem Display)      │ - Conversão de nomes canônicos/OSD    │
│                                │ - Modelagem e serialização de macros  │
│                                │ - Validação de teclas reservadas      │
│                                │ - Fila não-bloqueante do scheduler    │
├────────────────────────────────┼───────────────────────────────────────┤
│ 2. Testes de Integração Modelo  │ - Auto-save debounce e ProfileManager │
│    e Persistência (com Mocks)  │ - Regra de instância única (DPad/Mira)│
│                                │ - Atribuição e alternância de modos   │
├────────────────────────────────┼───────────────────────────────────────┤
│ 3. Testes Visuais e de Gestos  │ - Criação por duplo clique (simulado) │
│    (Headless via Xvfb)         │ - Inicialização de Layer Shell/Fallback│
│                                │ - Ajuste e controle de opacidade (0-1)│
└────────────────────────────────┴───────────────────────────────────────┘
```

### Novos Testes Planejados:
1. `tests/test_key_codes.py`:
   - Validação da tabela canônica bidirecional (GDK keyvals, evdev ecodes, rótulos compactos).
   - Bloqueio de teclas do sistema (`F1`, `F2`, `F3`).
2. `tests/test_keymap_engine.py`:
   - Teste de `TapWidget` nos modos `single`, `hold` e `turbo`.
   - Teste do cálculo vetorial de 8 direções para o `DPadWidget`.
   - Alocação e reciclagem correta de slots multitouch uinput (slots 2 a 9).
3. `tests/test_macro_widget.py`:
   - Serialização e desserialização de `MacroWidget` com passos ordenados.
   - Execução temporizada via `NonBlockingMacroScheduler` sem desvio de latência.
4. `tests/test_overlay_logic.py`:
   - Comportamento de fallback gracioso para janela comum quando `Gtk4LayerShell.is_supported() == False`.
   - Troca de região de entrada (`set_game_mode` vs `set_edit_mode`).
   - Coalescência de salvamento com debounce de 500ms.

---

## 8. Requirements Traceability Matrix

| Requirement ID | Success Criteria / Decision | Architectural Implementation |
|---|---|---|
| **UI-01** | Overlay transparente Wayland com controle de opacidade (0% a 100%) | `WayFireOverlayWindow` via `Gtk4LayerShell` com camada `OVERLAY`, pass-through de input region (`cairo.Region()`), slider de opacidade e toggle rápido `F3`. |
| **UI-02** | Modo de edição interativo estilo GG Mouse Pro | `OverlayCanvas` com duplo clique criando bolinha em escuta `[ ? ]`, captura instantânea da próxima tecla física/mouse, arrastar, redimensionar e excluir. |
| **MAP-02** | Componentes de mapeamento customizáveis (Tap, DPad, Aim, Fire, Macro) | Modelagem polimórfica estendida em `widgets.py`, visualização especializada no editor, despacho uinput multitouch em `KeymapEngine`. |

---

## RESEARCH COMPLETE

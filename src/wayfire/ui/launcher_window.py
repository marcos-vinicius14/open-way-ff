"""WayFire GTK4/Libadwaita desktop launcher window and unified control center."""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
from gi.repository import Adw, Gdk, GLib, Gtk

from wayfire.config.profile import WayFireProfile
from wayfire.config.profile_manager import ProfileManager
from wayfire.core.session_coordinator import GameSessionCoordinator, SessionState
from wayfire.ui.log_dialog import WayFireLogDialog

logger = logging.getLogger(__name__)

LAUNCHER_CSS = """
.wayfire-hero-banner {
    background: linear-gradient(180deg, rgba(30, 30, 35, 0.95), rgba(20, 20, 24, 0.98));
    border-radius: 16px;
    border: 1px solid rgba(255, 87, 34, 0.25);
    padding: 24px;
}

.wayfire-play-btn {
    background: linear-gradient(135deg, #ff5722, #e64a19);
    color: #ffffff;
    font-weight: 800;
    font-size: 16px;
    border-radius: 12px;
    padding: 14px 32px;
    box-shadow: 0 4px 14px rgba(255, 87, 34, 0.4);
    transition: all 200ms ease;
}

.wayfire-play-btn:hover {
    background: linear-gradient(135deg, #ff7043, #f4511e);
    box-shadow: 0 6px 18px rgba(255, 87, 34, 0.6);
}

.wayfire-stop-btn {
    background: linear-gradient(135deg, #d32f2f, #c62828);
    color: #ffffff;
    font-weight: 800;
    font-size: 16px;
    border-radius: 12px;
    padding: 14px 32px;
    box-shadow: 0 4px 14px rgba(211, 47, 47, 0.4);
}

.wayfire-stop-btn:hover {
    background: linear-gradient(135deg, #e53935, #b71c1c);
}

.badge-capa {
    border-radius: 12px;
    padding: 6px 14px;
    font-weight: 700;
    font-size: 13px;
}

.badge-capa-high {
    background: rgba(255, 152, 0, 0.20);
    color: #ffb74d;
    border: 1px solid rgba(255, 152, 0, 0.5);
}

.badge-capa-mid {
    background: rgba(33, 150, 243, 0.18);
    color: #64b5f6;
    border: 1px solid rgba(33, 150, 243, 0.4);
}

.badge-capa-low {
    background: rgba(158, 158, 158, 0.15);
    color: #bdbdbd;
    border: 1px solid rgba(158, 158, 158, 0.3);
}

.badge-pill {
    border-radius: 10px;
    padding: 4px 10px;
    font-weight: 600;
    font-size: 12px;
}

.badge-status-green {
    background: rgba(76, 175, 80, 0.20);
    color: #81c784;
    border: 1px solid rgba(76, 175, 80, 0.4);
}

.badge-status-red {
    background: rgba(244, 67, 54, 0.20);
    color: #e57373;
    border: 1px solid rgba(244, 67, 54, 0.4);
}

.badge-status-yellow {
    background: rgba(255, 193, 7, 0.20);
    color: #ffd54f;
    border: 1px solid rgba(255, 193, 7, 0.4);
}

.pill-button-selected {
    border: 2px solid #ff5722;
    background: rgba(255, 87, 34, 0.15);
}
"""


class WayFireLauncherWindow(Adw.ApplicationWindow):
    """Main desktop launcher window providing 1-click Free Fire execution and setup."""

    def __init__(
        self,
        app: Optional[Adw.Application] = None,
        coordinator: Optional[GameSessionCoordinator] = None,
        profile_manager: Optional[ProfileManager] = None,
        auto_poll_health: bool = True,
    ) -> None:
        if app is not None:
            super().__init__(application=app)
        else:
            super().__init__()

        self.set_title("WayFire 🔥 - Central de Jogos")
        self.set_default_size(820, 720)

        # Force Dark Theme per D-04
        style_mgr = Adw.StyleManager.get_default()
        style_mgr.set_color_scheme(Adw.ColorScheme.FORCE_DARK)

        # Load Custom Stylesheet
        self._apply_css()

        # Backend Models
        self.profile_manager: ProfileManager = (
            profile_manager if profile_manager is not None else ProfileManager()
        )
        self.coordinator: GameSessionCoordinator = (
            coordinator if coordinator is not None else GameSessionCoordinator(profile_manager=self.profile_manager)
        )
        self.active_profile: WayFireProfile = self.profile_manager.get_active_profile()

        # Connect coordinator event dispatchers
        self.coordinator.on_progress = self._on_coordinator_progress
        self.coordinator.on_state_change = self._on_coordinator_state_change

        self.log_dialog: Optional[WayFireLogDialog] = None
        self._syncing_widgets: bool = False

        # Build UI Hierarchy
        self._build_ui()

        # Initial data binding
        self._load_profile_into_ui(self.active_profile)
        self.poll_system_health()

        # Schedule periodic health poll
        self._health_poll_source_id: Optional[int] = None
        if auto_poll_health:
            self._health_poll_source_id = GLib.timeout_add(2000, self.poll_system_health)

    def destroy(self) -> None:
        """Cancel periodic GLib timers and close window."""
        if self._health_poll_source_id is not None:
            try:
                GLib.source_remove(self._health_poll_source_id)
            except Exception:
                pass
            self._health_poll_source_id = None
        super().destroy()

    def _apply_css(self) -> None:
        """Inject application stylesheet into the default display."""
        display = Gdk.Display.get_default()
        if display is not None:
            provider = Gtk.CssProvider()
            provider.load_from_data(LAUNCHER_CSS.encode("utf-8"))
            Gtk.StyleContext.add_provider_for_display(
                display,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

    def _build_ui(self) -> None:
        """Construct the main Libadwaita toolbar view and sections."""
        toolbar_view = Adw.ToolbarView()

        # HeaderBar
        header_bar = Adw.HeaderBar()
        title_widget = Adw.WindowTitle(title="WayFire 🔥", subtitle="Central Competitiva de Jogos")
        header_bar.set_title_widget(title_widget)

        self.btn_logs = Gtk.Button(label="📋 Logs")
        self.btn_logs.connect("clicked", self._on_open_logs_clicked)
        header_bar.pack_end(self.btn_logs)

        toolbar_view.add_top_bar(header_bar)

        # Scrolled container with clamp
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_propagate_natural_height(True)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(780)
        clamp.set_tightening_threshold(600)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(28)
        main_box.set_margin_start(16)
        main_box.set_margin_end(16)

        # 1. Hero Banner
        self._build_hero_banner(main_box)

        # 2. Card de Sensibilidade e Badge de Capa
        self._build_sensitivity_card(main_box)

        # 3. Card de Resolução e Perfis
        self._build_resolution_card(main_box)

        # 4. Card de Diagnóstico de Integridade
        self._build_health_card(main_box)

        clamp.set_child(main_box)
        scrolled.set_child(clamp)
        toolbar_view.set_content(scrolled)
        self.set_content(toolbar_view)

    def _build_hero_banner(self, parent_box: Gtk.Box) -> None:
        """Create Hero Banner with action button, spinner, and status indicators (D-01, D-06)."""
        banner_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        banner_box.add_css_class("wayfire-hero-banner")

        title_lbl = Gtk.Label(label="WAYFIRE 🔥")
        title_lbl.add_css_class("title-1")
        banner_box.append(title_lbl)

        sub_lbl = Gtk.Label(label="Emulador Competitivo de Free Fire no Linux (Near-Zero Latency)")
        sub_lbl.add_css_class("body")
        banner_box.append(sub_lbl)

        # Badges row
        features_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        features_box.set_halign(Gtk.Align.CENTER)
        for text in ("⚡ Latência &lt;1ms", "🎯 Sensibilidade X/Y Independente", "🛡️ Anti-Bug Analógico"):
            b = Gtk.Label(label=text)
            b.set_use_markup(True)
            b.add_css_class("badge-pill")
            b.add_css_class("badge-capa-high")
            features_box.append(b)
        banner_box.append(features_box)

        # Action button and spinner row
        action_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        action_row.set_halign(Gtk.Align.CENTER)
        action_row.set_margin_top(8)

        self.play_button = Gtk.Button(label="🔥 JOGAR FREE FIRE")
        self.play_button.add_css_class("wayfire-play-btn")
        self.play_button.connect("clicked", self._on_action_button_clicked)
        action_row.append(self.play_button)

        self.boot_spinner = Gtk.Spinner()
        self.boot_spinner.set_visible(False)
        action_row.append(self.boot_spinner)

        banner_box.append(action_row)

        self.boot_status_label = Gtk.Label(label="Pronto para jogar")
        self.boot_status_label.add_css_class("dim-label")
        banner_box.append(self.boot_status_label)

        parent_box.append(banner_box)

    def _build_sensitivity_card(self, parent_box: Gtk.Box) -> None:
        """Create sensitivity sliders, spin buttons, and real-time Capa ratio badge (D-02, D-08)."""
        group = Adw.PreferencesGroup()
        group.set_title("Ajuste de Sensibilidade (Puxada de Capa)")
        group.set_description("Calibração independente dos eixos de mira. Ajustes refletem instantaneamente no jogo.")

        # Capa ratio badge header
        badge_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        badge_box.set_halign(Gtk.Align.END)
        self.capa_badge = Gtk.Label(label="🔥 Proporção de Capa: 2.21x (Ideal para Subir Capa)")
        self.capa_badge.add_css_class("badge-capa")
        self.capa_badge.add_css_class("badge-capa-high")
        badge_box.append(self.capa_badge)
        group.set_header_suffix(badge_box)

        # Row Sensibility X
        row_x = Adw.ActionRow(title="Sensibilidade Horizontal (X)", subtitle="Velocidade de rotação 360° da câmera")
        self.scale_x = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.10, 10.00, 0.05)
        self.scale_x.set_hexpand(True)
        self.scale_x.set_draw_value(False)
        self.spin_x = Gtk.SpinButton.new_with_range(0.10, 10.00, 0.05)
        self.spin_x.set_digits(2)

        self.scale_x.connect("value-changed", self._on_scale_x_changed)
        self.spin_x.connect("value-changed", self._on_spin_x_changed)

        box_x = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box_x.set_valign(Gtk.Align.CENTER)
        box_x.append(self.scale_x)
        box_x.append(self.spin_x)
        row_x.add_suffix(box_x)
        group.add(row_x)

        # Row Sensibility Y
        row_y = Adw.ActionRow(title="Sensibilidade Vertical (Y)", subtitle="Altura da mira e controle de puxada de capa")
        self.scale_y = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.10, 10.00, 0.05)
        self.scale_y.set_hexpand(True)
        self.scale_y.set_draw_value(False)
        self.spin_y = Gtk.SpinButton.new_with_range(0.10, 10.00, 0.05)
        self.spin_y.set_digits(2)

        self.scale_y.connect("value-changed", self._on_scale_y_changed)
        self.spin_y.connect("value-changed", self._on_spin_y_changed)

        box_y = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box_y.set_valign(Gtk.Align.CENTER)
        box_y.append(self.scale_y)
        box_y.append(self.spin_y)
        row_y.add_suffix(box_y)
        group.add(row_y)

        parent_box.append(group)

    def _build_resolution_card(self, parent_box: Gtk.Box) -> None:
        """Create resolution pill buttons, profile selector, and package chooser (D-03, D-15)."""
        group = Adw.PreferencesGroup()
        group.set_title("Resolução de Tela e Perfis")

        # Resolution Pills Row
        row_res = Adw.ActionRow(title="Resolução do Contêiner", subtitle="Proporção esticada (4:3) aumenta o tamanho da cabeça dos inimigos")
        pill_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        pill_box.set_valign(Gtk.Align.CENTER)

        self.btn_1080p = Gtk.Button(label="1080p Nativo")
        self.btn_1080p.connect("clicked", lambda _: self._on_resolution_preset_selected(1920, 1080))
        pill_box.append(self.btn_1080p)

        self.btn_1440p = Gtk.Button(label="1440x1080 Esticado [Comp] 🔥")
        self.btn_1440p.connect("clicked", lambda _: self._on_resolution_preset_selected(1440, 1080))
        pill_box.append(self.btn_1440p)

        self.btn_768p = Gtk.Button(label="1024x768 (4:3)")
        self.btn_768p.connect("clicked", lambda _: self._on_resolution_preset_selected(1024, 768))
        pill_box.append(self.btn_768p)

        row_res.add_suffix(pill_box)
        group.add(row_res)

        # Profile selection dropdown
        self.profile_string_list = Gtk.StringList()
        profiles = self.profile_manager.list_profiles()
        for p in profiles:
            self.profile_string_list.append(p)

        self.profile_combo = Adw.ComboRow(title="Perfil Ativo", subtitle="Mapeamentos de teclado, mouse e sensibilidade")
        self.profile_combo.set_model(self.profile_string_list)
        active_name = self.active_profile.profile_name
        if active_name in profiles:
            self.profile_combo.set_selected(profiles.index(active_name))
        self.profile_combo.connect("notify::selected", self._on_profile_selected)
        group.add(self.profile_combo)

        # Package Selector Row (D-15)
        self.package_row = Adw.ComboRow(title="Pacote Free Fire", subtitle="Detectado automaticamente no contêiner")
        self.package_string_list = Gtk.StringList()
        self.package_string_list.append("Free Fire Standard (com.dts.freefireth)")
        self.package_string_list.append("Free Fire MAX (com.dts.freefiremax)")
        self.package_row.set_model(self.package_string_list)
        self.package_row.set_selected(0)
        group.add(self.package_row)

        parent_box.append(group)

    def _build_health_card(self, parent_box: Gtk.Box) -> None:
        """Create the 4-pillar system health diagnostics and auto-fix card (D-13, D-14)."""
        group = Adw.PreferencesGroup()
        group.set_title("Status de Integridade do Sistema")
        group.set_description("Diagnóstico dos requisitos essenciais para emulação competitiva sem travamentos.")

        # Pilar 1: Waydroid Container Service
        self.row_waydroid = Adw.ActionRow(
            title="Serviço Waydroid",
            subtitle="waydroid-container.service em execução",
        )
        self.badge_waydroid = Gtk.Label(label="Verificando...")
        self.badge_waydroid.add_css_class("badge-pill")
        self.btn_fix_waydroid = Gtk.Button(label="Iniciar")
        self.btn_fix_waydroid.set_valign(Gtk.Align.CENTER)
        self.btn_fix_waydroid.connect("clicked", self._on_fix_waydroid_clicked)

        box_w = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box_w.set_valign(Gtk.Align.CENTER)
        box_w.append(self.badge_waydroid)
        box_w.append(self.btn_fix_waydroid)
        self.row_waydroid.add_suffix(box_w)
        group.add(self.row_waydroid)

        # Pilar 2: uinput Permissions
        self.row_uinput = Adw.ActionRow(
            title="Permissões /dev/uinput",
            subtitle="Acesso de escrita para injeção de toques (&lt;1ms)",
        )
        self.badge_uinput = Gtk.Label(label="Verificando...")
        self.badge_uinput.add_css_class("badge-pill")
        self.btn_help_uinput = Gtk.Button(label="Como Corrigir")
        self.btn_help_uinput.set_valign(Gtk.Align.CENTER)
        self.btn_help_uinput.connect("clicked", self._on_help_uinput_clicked)

        box_u = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box_u.set_valign(Gtk.Align.CENTER)
        box_u.append(self.badge_uinput)
        box_u.append(self.btn_help_uinput)
        self.row_uinput.add_suffix(box_u)
        group.add(self.row_uinput)

        # Pilar 3: ASUS ROG Phone 5 Spoofing
        self.row_spoof = Adw.ActionRow(
            title="Spoofing ASUS ROG Phone 5",
            subtitle="Identificação de hardware para desbloquear 90/120 FPS",
        )
        self.badge_spoof = Gtk.Label(label="Verificando...")
        self.badge_spoof.add_css_class("badge-pill")
        self.btn_fix_spoof = Gtk.Button(label="Ativar")
        self.btn_fix_spoof.set_valign(Gtk.Align.CENTER)
        self.btn_fix_spoof.connect("clicked", self._on_fix_spoof_clicked)

        box_s = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box_s.set_valign(Gtk.Align.CENTER)
        box_s.append(self.badge_spoof)
        box_s.append(self.btn_fix_spoof)
        self.row_spoof.add_suffix(box_s)
        group.add(self.row_spoof)

        # Pilar 4: Detected Resolution
        self.row_res_status = Adw.ActionRow(
            title="Resolução do Waydroid",
            subtitle="Dimensões ativas lidas das propriedades persistentes",
        )
        self.badge_res_status = Gtk.Label(label="1920x1080")
        self.badge_res_status.add_css_class("badge-pill")
        self.badge_res_status.add_css_class("badge-capa-mid")
        self.badge_res_status.set_valign(Gtk.Align.CENTER)
        self.row_res_status.add_suffix(self.badge_res_status)
        group.add(self.row_res_status)

        parent_box.append(group)

    def _load_profile_into_ui(self, profile: WayFireProfile) -> None:
        """Synchronize UI controls with profile settings."""
        self._syncing_widgets = True
        try:
            self.scale_x.set_value(profile.sens_x)
            self.spin_x.set_value(profile.sens_x)
            self.scale_y.set_value(profile.sens_y)
            self.spin_y.set_value(profile.sens_y)
            self._update_capa_badge()
            self._update_resolution_pill_selection(profile.screen_width, profile.screen_height)
        finally:
            self._syncing_widgets = False

    def _on_scale_x_changed(self, scale: Gtk.Scale) -> None:
        """Handle scale X change and sync with spin button."""
        val = scale.get_value()
        if not self._syncing_widgets:
            self._syncing_widgets = True
            self.spin_x.set_value(val)
            self._syncing_widgets = False
            self._apply_sensitivity_change()

    def _on_spin_x_changed(self, spin: Gtk.SpinButton) -> None:
        """Handle spin X change and sync with scale slider."""
        val = spin.get_value()
        if not self._syncing_widgets:
            self._syncing_widgets = True
            self.scale_x.set_value(val)
            self._syncing_widgets = False
            self._apply_sensitivity_change()

    def _on_scale_y_changed(self, scale: Gtk.Scale) -> None:
        """Handle scale Y change and sync with spin button."""
        val = scale.get_value()
        if not self._syncing_widgets:
            self._syncing_widgets = True
            self.spin_y.set_value(val)
            self._syncing_widgets = False
            self._apply_sensitivity_change()

    def _on_spin_y_changed(self, spin: Gtk.SpinButton) -> None:
        """Handle spin Y change and sync with scale slider."""
        val = spin.get_value()
        if not self._syncing_widgets:
            self._syncing_widgets = True
            self.scale_y.set_value(val)
            self._syncing_widgets = False
            self._apply_sensitivity_change()

    def _apply_sensitivity_change(self) -> None:
        """Propagate updated sensitivity to coordinator and active profile."""
        sens_x = self.scale_x.get_value()
        sens_y = self.scale_y.get_value()
        self._update_capa_badge()
        self.coordinator.set_sensitivity(sens_x=sens_x, sens_y=sens_y)

    def _update_capa_badge(self) -> None:
        """Recalculate and restyle the Capa ratio badge (D-02)."""
        sens_x = self.scale_x.get_value()
        sens_y = self.scale_y.get_value()
        ratio = sens_y / sens_x if sens_x > 0 else 1.0

        for cls in ("badge-capa-high", "badge-capa-mid", "badge-capa-low"):
            self.capa_badge.remove_css_class(cls)

        if ratio >= 2.0:
            self.capa_badge.set_label(f"🔥 Proporção de Capa: {ratio:.2f}x (Ideal para Subir Capa)")
            self.capa_badge.add_css_class("badge-capa-high")
        elif ratio >= 1.4:
            self.capa_badge.set_label(f"🎯 Proporção de Capa: {ratio:.2f}x (Equilibrada)")
            self.capa_badge.add_css_class("badge-capa-mid")
        else:
            self.capa_badge.set_label(f"Proporção de Capa: {ratio:.2f}x (Padrão)")
            self.capa_badge.add_css_class("badge-capa-low")

    def _on_resolution_preset_selected(self, width: int, height: int) -> None:
        """Handle resolution pill click and update active profile."""
        self._update_resolution_pill_selection(width, height)
        self.coordinator.set_resolution_preset(width, height)
        self.poll_system_health()

    def _update_resolution_pill_selection(self, width: int, height: int) -> None:
        """Update visual highlight on the active resolution pill button."""
        for btn in (self.btn_1080p, self.btn_1440p, self.btn_768p):
            btn.remove_css_class("suggested-action")
            btn.remove_css_class("pill-button-selected")

        if width == 1440 and height == 1080:
            self.btn_1440p.add_css_class("suggested-action")
            self.btn_1440p.add_css_class("pill-button-selected")
        elif width == 1024 and height == 768:
            self.btn_768p.add_css_class("suggested-action")
            self.btn_768p.add_css_class("pill-button-selected")
        else:
            self.btn_1080p.add_css_class("suggested-action")
            self.btn_1080p.add_css_class("pill-button-selected")

    def _on_profile_selected(self, _row: Adw.ComboRow, _param: Any) -> None:
        """Switch active profile when user changes dropdown selection."""
        idx = self.profile_combo.get_selected()
        profiles = self.profile_manager.list_profiles()
        if 0 <= idx < len(profiles):
            chosen = profiles[idx]
            self.profile_manager.set_active_profile(chosen)
            self.active_profile = self.profile_manager.get_active_profile()
            self._load_profile_into_ui(self.active_profile)

    def _on_open_logs_clicked(self, _btn: Gtk.Button) -> None:
        """Present or initialize the WayFireLogDialog."""
        if self.log_dialog is None:
            self.log_dialog = WayFireLogDialog(parent_window=self)
        self.log_dialog.present()

    def _on_action_button_clicked(self, _btn: Gtk.Button) -> None:
        """Toggle game session between Play and Stop (D-01, D-06)."""
        if self.coordinator.state == SessionState.STOPPED:
            self.play_button.set_sensitive(False)
            self.boot_spinner.set_visible(True)
            self.boot_spinner.start()
            self.boot_status_label.set_label("Iniciando partida...")

            # Check selected package
            pkg = None
            if self.package_row.get_selected() == 1:
                pkg = "com.dts.freefiremax"

            is_stretched = bool(self.btn_1440p.has_css_class("pill-button-selected"))

            self.coordinator.start_session_async(
                package=pkg,
                stretched=is_stretched,
                enable_overlay=True,
            )
        elif self.coordinator.state == SessionState.RUNNING:
            self.coordinator.stop_session()

    def _on_coordinator_progress(self, step: int, total: int, message: str) -> None:
        """Update status label during boot sequence."""
        def _update() -> bool:
            self.boot_status_label.set_label(f"Passo {step}/{total}: {message}")
            if self.log_dialog is not None:
                self.log_dialog.append_log(f"[{step}/{total}] {message}\n")
            return False

        if threading.current_thread() is threading.main_thread():
            _update()
        else:
            GLib.idle_add(_update)

    def _on_coordinator_state_change(self, state: SessionState, message: str) -> None:
        """Handle state transitions: hide window on run, restore on stop (D-05, D-06)."""
        def _update() -> bool:
            if self.log_dialog is not None:
                self.log_dialog.append_log(f"[STATE] {state.value.upper()}: {message}\n")

            if state == SessionState.RUNNING:
                self.play_button.set_label("⏹ PARAR JOGO")
                self.play_button.remove_css_class("wayfire-play-btn")
                self.play_button.add_css_class("wayfire-stop-btn")
                self.play_button.set_sensitive(True)

                self.boot_spinner.stop()
                self.boot_spinner.set_visible(False)
                self.boot_status_label.set_label("Partida em andamento")

                # Hide launcher window during gameplay per D-05
                self.set_visible(False)

            elif state == SessionState.STOPPED:
                self.play_button.set_label("🔥 JOGAR FREE FIRE")
                self.play_button.remove_css_class("wayfire-stop-btn")
                self.play_button.add_css_class("wayfire-play-btn")
                self.play_button.set_sensitive(True)

                self.boot_spinner.stop()
                self.boot_spinner.set_visible(False)
                self.boot_status_label.set_label("Pronto para jogar")

                # Restore launcher window after gameplay per D-05
                self.set_visible(True)
                self.present()

            return False

        if threading.current_thread() is threading.main_thread():
            _update()
        else:
            GLib.idle_add(_update)

    def poll_system_health(self) -> bool:
        """Perform non-blocking health check of the 4 pillars (D-13)."""
        try:
            ctrl = self.coordinator.waydroid_controller

            # Pilar 1: Waydroid Container
            is_active = ctrl.is_container_active()
            self._set_badge_status(
                self.badge_waydroid,
                "Ativo" if is_active else "Inativo",
                "green" if is_active else "red",
            )
            self.btn_fix_waydroid.set_visible(not is_active)

            # Pilar 2: uinput permissions
            has_uinput = os.access("/dev/uinput", os.W_OK)
            self._set_badge_status(
                self.badge_uinput,
                "Liberado" if has_uinput else "Sem Permissão",
                "green" if has_uinput else "red",
            )
            self.btn_help_uinput.set_visible(not has_uinput)

            # Pilar 3: ROG Phone Spoofing
            is_spoof = ctrl.is_spoofing_applied()
            self._set_badge_status(
                self.badge_spoof,
                "Ativo (120 FPS)" if is_spoof else "Inativo",
                "green" if is_spoof else "yellow",
            )
            self.btn_fix_spoof.set_visible(not is_spoof)

            # Pilar 4: Detected Resolution
            curr_w, curr_h = ctrl.get_current_resolution()
            self.badge_res_status.set_label(f"{curr_w}x{curr_h}")

        except Exception as e:
            logger.warning("Falha ao checar saúde do sistema: %s", e)

        return True  # Keep GLib timer active

    def _set_badge_status(self, label: Gtk.Label, text: str, color_type: str) -> None:
        """Apply color badge CSS classes."""
        label.set_label(text)
        for cls in ("badge-status-green", "badge-status-red", "badge-status-yellow"):
            label.remove_css_class(cls)

        if color_type == "green":
            label.add_css_class("badge-status-green")
        elif color_type == "red":
            label.add_css_class("badge-status-red")
        else:
            label.add_css_class("badge-status-yellow")

    def _on_fix_waydroid_clicked(self, _btn: Gtk.Button) -> None:
        """Attempt to activate Waydroid container service (D-14)."""
        try:
            self.coordinator.waydroid_controller.ensure_container_active()
            self.poll_system_health()
        except Exception:
            self._show_instructions_dialog(
                title="Iniciar Serviço Waydroid",
                body=(
                    "Não foi possível iniciar o serviço automaticamente.\n\n"
                    "Execute o comando abaixo em seu terminal para habilitar o contêiner:\n\n"
                    "sudo systemctl start waydroid-container.service"
                ),
                command="sudo systemctl start waydroid-container.service",
            )

    def _on_help_uinput_clicked(self, _btn: Gtk.Button) -> None:
        """Show instructions for granting uinput write access (D-14)."""
        user = os.environ.get("USER", "marcos")
        cmd = f"sudo usermod -aG input {user}"
        self._show_instructions_dialog(
            title="Permissão /dev/uinput",
            body=(
                "Para injetar toques virtuais na tela com latência instantânea (<1ms), "
                "o seu usuário precisa pertencer ao grupo 'input'.\n\n"
                "Execute o comando abaixo e faça logout da sua sessão de usuário:\n\n"
                f"{cmd}"
            ),
            command=cmd,
        )

    def _on_fix_spoof_clicked(self, _btn: Gtk.Button) -> None:
        """Apply ASUS ROG Phone 5 spoofing on container."""
        try:
            self.coordinator.waydroid_controller.apply_spoofing()
            self.poll_system_health()
        except Exception as e:
            logger.warning("Falha ao aplicar spoofing: %s", e)

    def _show_instructions_dialog(self, title: str, body: str, command: Optional[str] = None) -> None:
        """Present a helpful MessageDialog with a Copy Command response."""
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=title,
            body=body,
        )
        dialog.add_response("ok", "Entendi")
        if command:
            dialog.add_response("copy", "📋 Copiar Comando")

            def _on_resp(_d: Adw.MessageDialog, resp: str) -> None:
                if resp == "copy":
                    disp = Gdk.Display.get_default()
                    if disp:
                        disp.get_clipboard().set(command)

            dialog.connect("response", _on_resp)

        dialog.present()

import os

from gi.repository import Adw, Gio, GdkPixbuf, GLib, Gtk

from . import ciadpi
from .settings import SettingsDialog
from .updater import Updater

try:
    from .tray import TrayIcon
except Exception:
    TrayIcon = None


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title='byedpi-gtk')
        self.app = application
        self.config = application.config
        self.proxy = ciadpi.ProxyManager()
        self.proxy.connect('state-changed', self._on_state_changed)
        self._settings_dialog = None
        self._tray = None

        self.set_default_size(420, 560)
        self.set_size_request(360, 480)

        self._stack = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.CROSSFADE
        )
        self.set_content(self._stack)

        self._build_loading_view()
        self._build_main_view()

        self._stack.set_visible_child_name('loading')
        self.connect('close-request', self._on_close_request)
        self.connect('notify::visible', lambda *_a: self._refresh_tray_menu())
        self._setup_tray()
        self._start_update_check()

    def _build_loading_view(self):
        self._loading_status = Adw.StatusPage(
            icon_name=self.app.app_id,
            title='byedpi-gtk',
        )
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=18,
            halign=Gtk.Align.CENTER,
        )
        self._loading_spinner = Adw.Spinner(width_request=32, height_request=32)
        self._loading_label = Gtk.Label(label=_('Starting…'))
        self._loading_label.add_css_class('dim-label')
        box.append(self._loading_spinner)
        box.append(self._loading_label)
        self._loading_status.set_child(box)
        self._stack.add_named(self._loading_status, 'loading')

    def _build_main_view(self):
        toolbar = Adw.ToolbarView()
        self._header = Adw.HeaderBar()

        self._menu_button = Gtk.MenuButton(
            icon_name='open-menu-symbolic',
            tooltip_text=_('Main Menu'),
        )
        self._menu_button.set_menu_model(self._build_menu())
        self._settings_button = Gtk.Button(
            icon_name='emblem-system-symbolic',
            tooltip_text=_('Settings'),
        )
        self._settings_button.connect('clicked', self._on_settings_clicked)
        self._header.pack_end(self._menu_button)
        self._header.pack_end(self._settings_button)
        toolbar.add_top_bar(self._header)

        self.toast_overlay = Adw.ToastOverlay()
        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=24,
            margin_top=24,
            margin_bottom=24,
            margin_start=24,
            margin_end=24,
            valign=Gtk.Align.CENTER,
        )

        self._status_icon = Gtk.Image.new_from_icon_name(
            'network-offline-symbolic'
        )
        self._status_icon.set_pixel_size(96)
        self._status_icon.add_css_class('dim-label')

        self._status_label = Gtk.Label()
        self._status_label.add_css_class('title-2')

        self._endpoint_label = Gtk.Label()
        self._endpoint_label.add_css_class('dim-label')
        self._update_endpoint_label()

        self._toggle_button = Gtk.Button()
        self._toggle_button.add_css_class('pill')
        self._toggle_button.set_halign(Gtk.Align.CENTER)
        self._toggle_button.connect('clicked', self._on_toggle_clicked)

        content.append(self._status_icon)
        content.append(self._status_label)
        content.append(self._endpoint_label)
        content.append(self._toggle_button)

        self.toast_overlay.set_child(content)
        toolbar.set_content(self.toast_overlay)
        self._stack.add_named(toolbar, 'main')
        self._apply_state(self.proxy.state)

    def _build_menu(self):
        menu = Gio.Menu()
        menu.append(_('About byedpi-gtk'), 'app.about')
        menu.append(_('Quit'), 'app.quit')
        return menu

    def _update_endpoint_label(self):
        self._endpoint_label.set_text(
            'SOCKS5  {}:{}'.format(
                self.config.get('listen_host'), self.config.get('listen_port')
            )
        )

    def _setup_tray(self):
        if not self.config.get('show_tray') or TrayIcon is None:
            return
        try:
            self._tray = TrayIcon(self.app.app_id, 'byedpi-gtk')
            self._tray.set_icon_pixmap(self._load_icon_pixmaps())
            self._tray.connect('activate', lambda _t: self._toggle_window())
            self._tray.connect('menu-item', self._on_tray_menu)
            self._tray.start()
            self._refresh_tray_menu()
        except Exception:
            self._tray = None

    def _load_icon_pixmaps(self):
        icon_path = os.path.join(
            os.path.dirname(self.app.pkgdatadir), 'icons', 'hicolor',
            'scalable', 'apps', self.app.app_id + '.svg',
        )
        if not os.path.exists(icon_path):
            return []
        pixmaps = []
        for size in (24, 48):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                    icon_path, size, size
                )
            except GLib.Error:
                continue
            pixmaps.append(self._pixbuf_to_argb(pixbuf))
        return pixmaps

    def _pixbuf_to_argb(self, pixbuf):
        width = pixbuf.get_width()
        height = pixbuf.get_height()
        stride = pixbuf.get_rowstride()
        channels = pixbuf.get_n_channels()
        pixels = pixbuf.get_pixels()
        argb = bytearray(width * height * 4)
        out = 0
        for y in range(height):
            row = y * stride
            for x in range(width):
                pos = row + x * channels
                red = pixels[pos]
                green = pixels[pos + 1]
                blue = pixels[pos + 2]
                alpha = pixels[pos + 3] if channels == 4 else 255
                argb[out] = alpha
                argb[out + 1] = red
                argb[out + 2] = green
                argb[out + 3] = blue
                out += 4
        return (width, height, bytes(argb))

    def _refresh_tray_menu(self):
        if self._tray is None:
            return
        connected = self.proxy.is_active()
        visible = self.get_visible()
        self._tray.set_menu([
            {
                'id': 1,
                'label': _('Hide') if visible else _('Show'),
                'action': 'toggle_window',
            },
            {
                'id': 2,
                'label': _('Disconnect') if connected else _('Connect'),
                'action': 'toggle_proxy',
            },
            {'id': 3, 'type': 'separator'},
            {'id': 4, 'label': _('Quit'), 'action': 'quit'},
        ])

    def _on_tray_menu(self, tray, action):
        if action == 'toggle_window':
            self._toggle_window()
        elif action == 'toggle_proxy':
            self._on_toggle_clicked(None)
        elif action == 'quit':
            self.app.quit()

    def _toggle_window(self):
        if self.get_visible():
            self.set_visible(False)
        else:
            self.set_visible(True)
            self.present()
        self._refresh_tray_menu()

    def _on_close_request(self, window):
        if self.config.get('close_to_tray') and self._tray is not None \
                and self._tray.is_active():
            self.set_visible(False)
            self._refresh_tray_menu()
            return True
        return False

    def _start_update_check(self):
        updater = Updater(
            self.app.version,
            self.config.get('check_app_updates'),
            self.config.get('check_ciadpi_updates'),
            self.app.pkgdatadir,
        )
        updater.connect('progress', self._on_update_progress)
        updater.connect('finished', self._on_update_finished)
        updater.run_async()

    def _on_update_progress(self, updater, message):
        self._loading_label.set_text(message)

    def _on_update_finished(self, updater, result):
        self._stack.set_visible_child_name('main')
        for message in result.messages:
            self._toast(message)
        if result.app_update_available:
            self._toast(
                _('A new version of byedpi-gtk is available: {}').format(
                    result.app_latest
                )
            )
        elif result.ciadpi_installed_now:
            self._toast(
                _('byedpi core updated to {}').format(result.ciadpi_latest)
            )
        if self.config.get('autostart_proxy'):
            self._start_proxy()

    def _on_settings_clicked(self, button):
        dialog = SettingsDialog(self.config, self.app.localedir)
        self._settings_dialog = dialog
        dialog.connect('closed', self._on_settings_closed)
        dialog.present(self)

    def _on_settings_closed(self, dialog):
        self._settings_dialog = None
        self._update_endpoint_label()

    def _on_toggle_clicked(self, button):
        if self.proxy.is_active():
            self.proxy.stop()
        else:
            self._start_proxy()

    def _start_proxy(self):
        self._update_endpoint_label()
        self.proxy.start(
            self.config.get('listen_host'),
            self.config.get('listen_port'),
            self.config.get('extra_args'),
        )

    def _on_state_changed(self, proxy, state):
        self._apply_state(state)
        if state == ciadpi.STATE_FAILED:
            self._toast(_('Could not start the proxy. Check the settings.'))
        self._refresh_tray_menu()

    def _apply_state(self, state):
        if state == ciadpi.STATE_STARTING:
            self._status_label.set_text(_('Connecting…'))
            self._status_icon.set_from_icon_name('network-transmit-symbolic')
            self._toggle_button.set_label(_('Connect'))
            self._toggle_button.set_sensitive(False)
        elif state == ciadpi.STATE_RUNNING:
            self._status_label.set_text(_('Connected'))
            self._status_icon.set_from_icon_name('network-vpn-symbolic')
            self._toggle_button.set_label(_('Disconnect'))
            self._toggle_button.remove_css_class('suggested-action')
            self._toggle_button.add_css_class('destructive-action')
            self._toggle_button.set_sensitive(True)
        elif state == ciadpi.STATE_STOPPING:
            self._status_label.set_text(_('Disconnecting…'))
            self._toggle_button.set_sensitive(False)
        elif state == ciadpi.STATE_FAILED:
            self._status_label.set_text(_('Connection failed'))
            self._status_icon.set_from_icon_name('network-error-symbolic')
            self._reset_connect_button()
        else:
            self._status_label.set_text(_('Disconnected'))
            self._status_icon.set_from_icon_name('network-offline-symbolic')
            self._reset_connect_button()

    def _reset_connect_button(self):
        self._toggle_button.set_label(_('Connect'))
        self._toggle_button.remove_css_class('destructive-action')
        self._toggle_button.add_css_class('suggested-action')
        self._toggle_button.set_sensitive(True)

    def retranslate(self):
        self._loading_status.set_title('byedpi-gtk')
        self._loading_label.set_text(_('Starting…'))
        self._menu_button.set_tooltip_text(_('Main Menu'))
        self._menu_button.set_menu_model(self._build_menu())
        self._settings_button.set_tooltip_text(_('Settings'))
        self._apply_state(self.proxy.state)
        self._refresh_tray_menu()
        if self._settings_dialog is not None:
            self._settings_dialog.retranslate()

    def _toast(self, message):
        self.toast_overlay.add_toast(Adw.Toast(title=message, timeout=4))

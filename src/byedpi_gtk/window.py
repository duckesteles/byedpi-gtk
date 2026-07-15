from gi.repository import Adw, Gio, GLib, Gtk

from . import ciadpi
from .settings import SettingsDialog
from .updater import Updater


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title='byedpi-gtk')
        self.app = application
        self.config = application.config
        self.proxy = ciadpi.ProxyManager()
        self.proxy.connect('state-changed', self._on_state_changed)
        self.proxy.connect('log-line', self._on_log_line)

        self.set_default_size(420, 560)
        self.set_size_request(360, 480)

        self._stack = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.CROSSFADE
        )
        self.set_content(self._stack)

        self._build_loading_view()
        self._build_main_view()

        self._stack.set_visible_child_name('loading')
        self._start_update_check()

    def _build_loading_view(self):
        status = Adw.StatusPage(
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
        status.set_child(box)
        self._stack.add_named(status, 'loading')

    def _build_main_view(self):
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()

        menu = Gio.Menu()
        menu.append(_('About byedpi-gtk'), 'app.about')
        menu.append(_('Quit'), 'app.quit')
        menu_button = Gtk.MenuButton(
            icon_name='open-menu-symbolic',
            menu_model=menu,
            tooltip_text=_('Main Menu'),
        )
        settings_button = Gtk.Button(
            icon_name='emblem-system-symbolic',
            tooltip_text=_('Settings'),
        )
        settings_button.connect('clicked', self._on_settings_clicked)
        header.pack_end(menu_button)
        header.pack_end(settings_button)
        toolbar.add_top_bar(header)

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

        self._status_label = Gtk.Label(label=_('Disconnected'))
        self._status_label.add_css_class('title-2')

        self._endpoint_label = Gtk.Label()
        self._endpoint_label.add_css_class('dim-label')
        self._update_endpoint_label()

        self._toggle_button = Gtk.Button(label=_('Connect'))
        self._toggle_button.add_css_class('pill')
        self._toggle_button.add_css_class('suggested-action')
        self._toggle_button.set_halign(Gtk.Align.CENTER)
        self._toggle_button.connect('clicked', self._on_toggle_clicked)

        content.append(self._status_icon)
        content.append(self._status_label)
        content.append(self._endpoint_label)
        content.append(self._toggle_button)

        self.toast_overlay.set_child(content)
        toolbar.set_content(self.toast_overlay)
        self._stack.add_named(toolbar, 'main')

    def _update_endpoint_label(self):
        self._endpoint_label.set_text(
            'SOCKS5  {}:{}'.format(
                self.config.get('listen_host'), self.config.get('listen_port')
            )
        )

    def _start_update_check(self):
        updater = Updater(
            self.app.version,
            self.config.get('check_app_updates'),
            self.config.get('check_ciadpi_updates'),
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
        dialog.connect('closed', lambda *_a: self._update_endpoint_label())
        dialog.present(self)

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
        if state == ciadpi.STATE_STARTING:
            self._status_label.set_text(_('Connecting…'))
            self._status_icon.set_from_icon_name('network-transmit-symbolic')
            self._toggle_button.set_sensitive(False)
        elif state == ciadpi.STATE_RUNNING:
            self._status_label.set_text(_('Connected'))
            self._status_icon.set_from_icon_name(
                'network-vpn-symbolic'
            )
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
            self._toast(_('Could not start the proxy. Check the settings.'))
        else:
            self._status_label.set_text(_('Disconnected'))
            self._status_icon.set_from_icon_name('network-offline-symbolic')
            self._reset_connect_button()

    def _reset_connect_button(self):
        self._toggle_button.set_label(_('Connect'))
        self._toggle_button.remove_css_class('destructive-action')
        self._toggle_button.add_css_class('suggested-action')
        self._toggle_button.set_sensitive(True)

    def _on_log_line(self, proxy, line):
        pass

    def _toast(self, message):
        self.toast_overlay.add_toast(Adw.Toast(title=message, timeout=4))

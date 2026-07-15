import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Adw, Gio, GLib, Gtk

from . import i18n
from .config import Config
from .window import MainWindow


class Application(Adw.Application):
    def __init__(self, version, app_id, pkgdatadir, localedir):
        super().__init__(
            application_id=app_id,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.version = version
        self.app_id = app_id
        self.pkgdatadir = pkgdatadir
        self.localedir = localedir
        self.config = Config()
        i18n.setup(localedir, self.config.get('language'))
        self._apply_theme()
        self.config.connect('changed', self._on_config_changed)

    def _apply_theme(self):
        mapping = {
            'system': Adw.ColorScheme.DEFAULT,
            'light': Adw.ColorScheme.FORCE_LIGHT,
            'dark': Adw.ColorScheme.FORCE_DARK,
        }
        scheme = mapping.get(self.config.get('theme'), Adw.ColorScheme.DEFAULT)
        self.get_style_manager().set_color_scheme(scheme)

    def _on_config_changed(self, config, key):
        if key == 'theme':
            self._apply_theme()
        elif key == 'language':
            i18n.setup(self.localedir, config.get('language'))
            for window in self.get_windows():
                if hasattr(window, 'retranslate'):
                    window.retranslate()

    def do_startup(self):
        Adw.Application.do_startup(self)
        self._setup_actions()

    def _setup_actions(self):
        quit_action = Gio.SimpleAction.new('quit', None)
        quit_action.connect('activate', lambda *_a: self.quit())
        self.add_action(quit_action)
        self.set_accels_for_action('app.quit', ['<Primary>q'])

        about_action = Gio.SimpleAction.new('about', None)
        about_action.connect('activate', self._on_about)
        self.add_action(about_action)

    def do_activate(self):
        window = self.get_active_window()
        if window is None:
            window = MainWindow(application=self)
        window.set_visible(True)
        window.present()

    def _on_about(self, action, param):
        about = Adw.AboutDialog(
            application_name='byedpi-gtk',
            application_icon=self.app_id,
            developer_name='duckesteles',
            version=self.version,
            license_type=Gtk.License.GPL_3_0,
            website='https://github.com/duckesteles/byedpi-gtk',
            issue_url='https://github.com/duckesteles/byedpi-gtk/issues',
        )
        about.present(self.get_active_window())


def main(version, app_id, pkgdatadir, localedir):
    app = Application(version, app_id, pkgdatadir, localedir)
    return app.run(sys.argv)

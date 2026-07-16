import json
import os
from gi.repository import GLib, GObject

DEFAULTS = {
    'listen_host': '127.0.0.1',
    'listen_port': 1080,
    'extra_args': '--tlsrec 1+s',
    'theme': 'system',
    'language': 'system',
    'autostart_proxy': False,
    'check_app_updates': True,
    'check_ciadpi_updates': True,
    'show_tray': True,
    'close_to_tray': False,
}

VALID_THEMES = ('system', 'light', 'dark')


class Config(GObject.Object):
    __gsignals__ = {
        'changed': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self):
        super().__init__()
        self._path = os.path.join(
            GLib.get_user_config_dir(), 'byedpi-gtk', 'config.json'
        )
        self._data = dict(DEFAULTS)
        self._load()

    def _load(self):
        try:
            with open(self._path, 'r', encoding='utf-8') as handle:
                stored = json.load(handle)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return
        if isinstance(stored, dict):
            for key, value in stored.items():
                if key in DEFAULTS and self._valid(key, value):
                    self._data[key] = value

    def _valid(self, key, value):
        default = DEFAULTS[key]
        if isinstance(default, bool):
            return isinstance(value, bool)
        if isinstance(default, int):
            if not isinstance(value, int) or isinstance(value, bool):
                return False
            if key == 'listen_port':
                return 1 <= value <= 65535
            return True
        return isinstance(value, type(default))

    def _save(self):
        directory = os.path.dirname(self._path)
        os.makedirs(directory, mode=0o700, exist_ok=True)
        tmp = self._path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as handle:
            json.dump(self._data, handle, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, self._path)

    def get(self, key):
        return self._data.get(key, DEFAULTS.get(key))

    def set(self, key, value):
        if key not in DEFAULTS:
            return
        if self._data.get(key) == value:
            return
        self._data[key] = value
        try:
            self._save()
        except OSError:
            pass
        self.emit('changed', key)

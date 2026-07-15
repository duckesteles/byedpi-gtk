import os
import shlex
import socket
from gi.repository import GLib, Gio, GObject

STATE_STOPPED = 'stopped'
STATE_STARTING = 'starting'
STATE_RUNNING = 'running'
STATE_STOPPING = 'stopping'
STATE_FAILED = 'failed'

PROBE_ATTEMPTS = 40
PROBE_INTERVAL_MS = 50
STOP_GRACE_MS = 2000


def find_binary():
    data_binary = os.path.join(
        GLib.get_user_data_dir(), 'byedpi-gtk', 'ciadpi'
    )
    if os.access(data_binary, os.X_OK):
        return data_binary
    bundled = '/app/bin/ciadpi'
    if os.access(bundled, os.X_OK):
        return bundled
    return GLib.find_program_in_path('ciadpi')


class ProxyManager(GObject.Object):
    __gsignals__ = {
        'state-changed': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'log-line': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self):
        super().__init__()
        self._process = None
        self._state = STATE_STOPPED
        self._probe_count = 0
        self._host = '127.0.0.1'
        self._port = 1080
        self._stop_timeout = 0

    @GObject.Property(type=str, default=STATE_STOPPED)
    def state(self):
        return self._state

    def _set_state(self, state):
        if state == self._state:
            return
        self._state = state
        self.notify('state')
        self.emit('state-changed', state)

    def is_active(self):
        return self._state in (STATE_STARTING, STATE_RUNNING)

    def start(self, host, port, extra_args):
        if self.is_active():
            return
        binary = find_binary()
        if not binary:
            self.emit('log-line', _('ciadpi binary not found'))
            self._set_state(STATE_FAILED)
            return
        self._host = host
        self._port = port
        argv = [binary, '--ip', host, '--port', str(port)]
        try:
            argv += shlex.split(extra_args)
        except ValueError as error:
            self.emit('log-line', _('Invalid arguments: {}').format(error))
            self._set_state(STATE_FAILED)
            return
        self._set_state(STATE_STARTING)
        try:
            launcher = Gio.SubprocessLauncher.new(
                Gio.SubprocessFlags.STDOUT_PIPE
                | Gio.SubprocessFlags.STDERR_MERGE
            )
            self._process = launcher.spawnv(argv)
        except GLib.Error as error:
            self.emit('log-line', error.message)
            self._process = None
            self._set_state(STATE_FAILED)
            return
        self._process.wait_check_async(None, self._on_process_exit)
        self._read_output()
        self._probe_count = 0
        GLib.timeout_add(PROBE_INTERVAL_MS, self._probe)

    def _read_output(self):
        stream = self._process.get_stdout_pipe()
        if stream is None:
            return
        data = Gio.DataInputStream.new(stream)
        data.read_line_async(GLib.PRIORITY_DEFAULT, None, self._on_line, data)

    def _on_line(self, source, result, data):
        try:
            line, _length = source.read_line_finish_utf8(result)
        except GLib.Error:
            return
        if line is None:
            return
        self.emit('log-line', line)
        data.read_line_async(
            GLib.PRIORITY_DEFAULT, None, self._on_line, data
        )

    def _probe(self):
        if self._state != STATE_STARTING:
            return False
        self._probe_count += 1
        try:
            with socket.create_connection(
                (self._host, self._port), timeout=0.2
            ):
                pass
            self._set_state(STATE_RUNNING)
            return False
        except OSError:
            if self._probe_count >= PROBE_ATTEMPTS:
                self.emit('log-line', _('Timed out waiting for proxy port'))
                self.stop()
                self._set_state(STATE_FAILED)
                return False
            return True

    def stop(self):
        if self._process is None:
            self._set_state(STATE_STOPPED)
            return
        self._set_state(STATE_STOPPING)
        self._process.send_signal(15)
        self._stop_timeout = GLib.timeout_add(
            STOP_GRACE_MS, self._force_stop
        )

    def _force_stop(self):
        self._stop_timeout = 0
        if self._process is not None:
            self._process.force_exit()
        return False

    def _on_process_exit(self, process, result):
        try:
            process.wait_check_finish(result)
        except GLib.Error:
            pass
        if self._stop_timeout:
            GLib.source_remove(self._stop_timeout)
            self._stop_timeout = 0
        self._process = None
        if self._state != STATE_FAILED:
            self._set_state(STATE_STOPPED)

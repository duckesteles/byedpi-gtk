import hashlib
import json
import os
import platform
import tarfile
import tempfile
import urllib.error
import urllib.request
from gi.repository import GLib, Gio, GObject

APP_REPO = 'duckesteles/byedpi-gtk'
BYEDPI_REPO = 'hufrea/byedpi'
LATEST_TEMPLATE = 'https://api.github.com/repos/{}/releases/latest'
TAG_TEMPLATE = 'https://api.github.com/repos/{}/releases/tags/{}'
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0'
REQUEST_TIMEOUT = 15
MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024

ARCH_MAP = {
    'x86_64': 'x86_64',
    'amd64': 'x86_64',
    'i686': 'i686',
    'i386': 'i686',
    'aarch64': 'aarch64',
    'arm64': 'aarch64',
    'armv7l': 'armv7l',
    'armv6l': 'armv6',
    'ppc64': 'powerpc',
    'mips': 'mips',
}


def _managed_dir():
    return os.path.join(GLib.get_user_data_dir(), 'byedpi-gtk')


def _binary_path():
    return os.path.join(_managed_dir(), 'ciadpi')


def _version_state_path():
    return os.path.join(_managed_dir(), 'ciadpi.version')


def read_installed_ciadpi_version():
    try:
        with open(_version_state_path(), 'r', encoding='utf-8') as handle:
            return handle.read().strip() or None
    except OSError:
        return None


def _fetch_json(url):
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        return json.load(response)


def _fetch_latest(repo):
    return _fetch_json(LATEST_TEMPLATE.format(repo))


def _fetch_release_by_tag(repo, tag):
    return _fetch_json(TAG_TEMPLATE.format(repo, tag))


def _normalize(tag):
    return (tag or '').lstrip('vV').strip()


def target_arch():
    machine = platform.machine().lower()
    return ARCH_MAP.get(machine)


def _core_available():
    from .ciadpi import find_binary
    return find_binary() is not None


def _pick_asset(assets, arch):
    suffix = '-{}.tar.gz'.format(arch)
    for asset in assets:
        name = asset.get('name', '')
        if name.startswith('byedpi-') and name.endswith(suffix):
            return asset
    return None


def _download(url, destination):
    if not url.lower().startswith('https://'):
        raise ValueError('refusing non-HTTPS download URL')
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    total = 0
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        with open(destination, 'wb') as handle:
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_DOWNLOAD_BYTES:
                    raise ValueError('download exceeded size limit')
                handle.write(chunk)


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(65536), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _extract_binary(archive_path, arch, destination):
    member_name = 'ciadpi-{}'.format(arch)
    with tarfile.open(archive_path, 'r:gz') as archive:
        try:
            member = archive.getmember(member_name)
        except KeyError:
            member = next(
                (
                    item
                    for item in archive.getmembers()
                    if item.isfile()
                    and os.path.basename(item.name).startswith('ciadpi')
                ),
                None,
            )
            if member is None:
                raise FileNotFoundError(member_name)
        if member.size > MAX_DOWNLOAD_BYTES:
            raise ValueError('core binary exceeds size limit')
        with archive.extractfile(member) as source:
            payload = source.read()
    os.makedirs(os.path.dirname(destination), mode=0o700, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(destination))
    with os.fdopen(tmp_fd, 'wb') as handle:
        handle.write(payload)
    os.chmod(tmp_path, 0o755)
    os.replace(tmp_path, destination)


class UpdateResult:
    def __init__(self):
        self.app_current = None
        self.app_latest = None
        self.app_update_available = False
        self.ciadpi_installed = None
        self.ciadpi_latest = None
        self.ciadpi_installed_now = False
        self.messages = []


class Updater(GObject.Object):
    __gsignals__ = {
        'progress': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'finished': (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }

    def __init__(self, app_version, check_app, check_ciadpi, pkgdatadir):
        super().__init__()
        self._app_version = app_version
        self._check_app = check_app
        self._check_ciadpi = check_ciadpi
        self._pkgdatadir = pkgdatadir

    def _load_manifest(self):
        path = os.path.join(self._pkgdatadir, 'byedpi-upstream.json')
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            return None
        if not isinstance(data, dict) or 'tag' not in data:
            return None
        return data

    def run_async(self):
        task = Gio.Task.new(self, None, self._on_done)
        task.run_in_thread(self._worker)

    def _report(self, message):
        GLib.idle_add(self.emit, 'progress', message)

    def _worker(self, task, source, data, cancellable):
        result = UpdateResult()
        result.app_current = self._app_version
        if self._check_app:
            self._check_app_update(result)
        if self._check_ciadpi:
            self._sync_ciadpi(result)
        elif read_installed_ciadpi_version() is None:
            self._sync_ciadpi(result)
        task.return_value(result)

    def _check_app_update(self, result):
        self._report(_('Checking for application updates…'))
        try:
            data = _fetch_latest(APP_REPO)
        except (urllib.error.URLError, OSError, ValueError):
            return
        latest = _normalize(data.get('tag_name'))
        result.app_latest = latest
        if latest and _normalize(self._app_version) and latest != _normalize(
            self._app_version
        ):
            result.app_update_available = True

    def _warn_if_no_core(self, result, message):
        if not _core_available():
            result.messages.append(message)

    def _sync_ciadpi(self, result):
        self._report(_('Checking byedpi core…'))
        arch = target_arch()
        result.ciadpi_installed = read_installed_ciadpi_version()
        manifest = self._load_manifest()
        if arch is None or manifest is None:
            self._warn_if_no_core(
                result, _('No byedpi core build for this architecture.')
            )
            return
        tag = manifest['tag']
        pinned = _normalize(tag)
        expected_sha = manifest.get('sha256', {}).get(arch)
        result.ciadpi_latest = pinned
        have_binary = os.access(_binary_path(), os.X_OK)
        if have_binary and result.ciadpi_installed == pinned:
            return
        if not expected_sha:
            self._warn_if_no_core(
                result, _('No byedpi core build for this architecture.')
            )
            return
        try:
            release = _fetch_release_by_tag(BYEDPI_REPO, tag)
        except (urllib.error.URLError, OSError, ValueError):
            self._warn_if_no_core(
                result, _('Could not download the byedpi core.')
            )
            return
        asset = _pick_asset(release.get('assets', []), arch)
        if asset is None:
            self._warn_if_no_core(
                result, _('No byedpi core build for this architecture.')
            )
            return
        self._report(_('Downloading byedpi core {}…').format(pinned))
        try:
            with tempfile.TemporaryDirectory() as workdir:
                archive = os.path.join(workdir, 'byedpi.tar.gz')
                _download(asset['browser_download_url'], archive)
                if _sha256(archive) != expected_sha:
                    raise ValueError('byedpi core checksum mismatch')
                _extract_binary(archive, arch, _binary_path())
        except (urllib.error.URLError, OSError, tarfile.TarError,
                FileNotFoundError, ValueError):
            self._warn_if_no_core(
                result, _('Could not verify the byedpi core download.')
            )
            return
        with open(_version_state_path(), 'w', encoding='utf-8') as handle:
            handle.write(pinned)
        result.ciadpi_installed = pinned
        result.ciadpi_installed_now = True

    def _on_done(self, source, task, data=None):
        try:
            result = task.propagate_value().value
        except GLib.Error:
            result = UpdateResult()
        self.emit('finished', result)

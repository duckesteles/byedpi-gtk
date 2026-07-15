project(
  'byedpi-gtk',
  version: '1.0.7',
  license: 'GPL-3.0-or-later',
  meson_version: '>= 0.62.0',
)

app_id = 'io.github.duckesteles.byedpigtk'

dependency('gtk4', version: '>= 4.10')
dependency('libadwaita-1', version: '>= 1.4')
dependency('pygobject-3.0', version: '>= 3.44', required: false)

python = import('python').find_installation('python3')
i18n = import('i18n')

prefix = get_option('prefix')
bindir = get_option('bindir')
datadir = get_option('datadir')
localedir = get_option('localedir')
pkgdatadir = datadir / meson.project_name()
moduledir = python.get_install_dir() / 'byedpi_gtk'

install_data('packaging/byedpi-upstream.json', install_dir: pkgdatadir)

subdir('src')
subdir('data')
subdir('po')

gnome = import('gnome')
gnome.post_install(
  gtk_update_icon_cache: true,
  update_desktop_database: true,
)

conf = configuration_data()
conf.set('PYTHON', python.full_path())
conf.set('VERSION', meson.project_version())
conf.set('APP_ID', app_id)
conf.set('prefix', prefix)
conf.set('localedir', prefix / localedir)
conf.set('pkgdatadir', prefix / pkgdatadir)
conf.set('moduledir', moduledir)

configure_file(
  input: 'byedpi-gtk.in',
  output: 'byedpi-gtk',
  configuration: conf,
  install: true,
  install_dir: bindir,
  install_mode: 'rwxr-xr-x',
)

build_config = configure_file(
  input: 'byedpi_gtk/build_config.py.in',
  output: 'build_config.py',
  configuration: conf,
)

sources = [
  'byedpi_gtk/__init__.py',
  'byedpi_gtk/main.py',
  'byedpi_gtk/window.py',
  'byedpi_gtk/settings.py',
  'byedpi_gtk/config.py',
  'byedpi_gtk/ciadpi.py',
  'byedpi_gtk/updater.py',
  'byedpi_gtk/i18n.py',
]

install_data(sources, install_dir: moduledir)
install_data(build_config, install_dir: moduledir)

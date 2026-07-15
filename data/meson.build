desktop_file = i18n.merge_file(
  input: configure_file(
    input: 'io.github.duckesteles.byedpigtk.desktop.in.in',
    output: 'io.github.duckesteles.byedpigtk.desktop.in',
    configuration: {'BINDIR': prefix / bindir},
  ),
  output: app_id + '.desktop',
  po_dir: '../po',
  type: 'desktop',
  install: true,
  install_dir: datadir / 'applications',
)

metainfo_file = i18n.merge_file(
  input: 'io.github.duckesteles.byedpigtk.metainfo.xml.in',
  output: app_id + '.metainfo.xml',
  po_dir: '../po',
  install: true,
  install_dir: datadir / 'metainfo',
)

install_data(
  'icons/hicolor/scalable/apps/io.github.duckesteles.byedpigtk.svg',
  install_dir: datadir / 'icons/hicolor/scalable/apps',
)

install_data(
  'icons/hicolor/symbolic/apps/io.github.duckesteles.byedpigtk-symbolic.svg',
  install_dir: datadir / 'icons/hicolor/symbolic/apps',
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('validate-desktop', desktop_utils, args: [desktop_file])
endif

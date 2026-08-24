desktop_file = i18n.merge_file(
  input: 'app.sheaf.Sheaf.desktop.in',
  output: 'app.sheaf.Sheaf.desktop',
  type: 'desktop',
  po_dir: meson.project_source_root() / 'po',
  install: true,
  install_dir: get_option('datadir') / 'applications',
)

desktop_file_validate = find_program('desktop-file-validate', required: false)
if desktop_file_validate.found()
  test(
    'validate-desktop',
    desktop_file_validate,
    args: [desktop_file],
  )
endif

metainfo_file = i18n.merge_file(
  input: 'app.sheaf.Sheaf.metainfo.xml.in',
  output: 'app.sheaf.Sheaf.metainfo.xml',
  po_dir: meson.project_source_root() / 'po',
  install: true,
  install_dir: get_option('datadir') / 'metainfo',
)

appstreamcli = find_program('appstreamcli', required: false)
if appstreamcli.found()
  test(
    'validate-metainfo',
    appstreamcli,
    args: ['validate', '--no-net', metainfo_file],
  )
else
  appstream_util = find_program('appstream-util', required: false)
  if appstream_util.found()
    test(
      'validate-metainfo',
      appstream_util,
      args: ['validate-relax', metainfo_file],
    )
  endif
endif

service_conf = configuration_data()
service_conf.set('bindir', get_option('prefix') / get_option('bindir'))

configure_file(
  input: 'app.sheaf.Sheaf.service.in',
  output: 'app.sheaf.Sheaf.service',
  configuration: service_conf,
  install: true,
  install_dir: get_option('datadir') / 'dbus-1' / 'services',
)

install_data(
  'icons/hicolor/scalable/apps/app.sheaf.Sheaf.svg',
  install_dir: get_option('datadir') / 'icons' / 'hicolor' / 'scalable' / 'apps',
)

install_data(
  'icons/hicolor/symbolic/apps/app.sheaf.Sheaf-symbolic.svg',
  install_dir: get_option('datadir') / 'icons' / 'hicolor' / 'symbolic' / 'apps',
)

install_data(
  'omarchy/sheaf.css.tpl',
  install_dir: pkgdatadir / 'omarchy',
)

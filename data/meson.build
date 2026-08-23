desktop_file = 'io.github.jitendravyas.Notes.desktop'
metainfo_file = 'io.github.jitendravyas.Notes.metainfo.xml'

install_data(
  desktop_file,
  install_dir: get_option('datadir') / 'applications',
)

install_data(
  metainfo_file,
  install_dir: get_option('datadir') / 'metainfo',
)

service_conf = configuration_data()
service_conf.set('bindir', get_option('prefix') / get_option('bindir'))

configure_file(
  input: 'io.github.jitendravyas.Notes.service.in',
  output: 'io.github.jitendravyas.Notes.service',
  configuration: service_conf,
  install: true,
  install_dir: get_option('datadir') / 'dbus-1' / 'services',
)

install_data(
  'icons/hicolor/scalable/apps/io.github.jitendravyas.Notes.svg',
  install_dir: get_option('datadir') / 'icons' / 'hicolor' / 'scalable' / 'apps',
)

project(
  'notes',
  version: '0.1.0',
  meson_version: '>= 0.62.0',
  default_options: ['warning_level=2', 'prefix=/usr'],
)

app_id = 'io.github.jitendravyas.Notes'
pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()

gnome = import('gnome')

subdir('data')
subdir('src')

gnome.post_install(
  gtk_update_icon_cache: true,
  update_desktop_database: true,
)

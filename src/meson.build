python = import('python')
py_installation = python.find_installation('python3')

conf = configuration_data()
conf.set('PYTHON', py_installation.full_path())
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'notes.in',
  output: 'notes',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x',
)

install_data(
  [
    'main.py',
    'window.py',
    'markdown.py',
  ],
  install_dir: pkgdatadir,
)

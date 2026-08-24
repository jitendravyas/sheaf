python3 = find_program('python3')
source_root = meson.project_source_root()

test(
  'store',
  python3,
  args: [files('test_store.py')],
  workdir: source_root,
)

test(
  'detect-language',
  python3,
  args: [files('test_detect_language.py')],
  workdir: source_root,
)

test(
  'markdown-links',
  python3,
  args: [files('test_markdown_links.py')],
  workdir: source_root,
)

test(
  'theme',
  python3,
  args: [files('test_theme.py')],
  workdir: source_root,
)

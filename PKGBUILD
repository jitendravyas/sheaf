# Maintainer: Jitendra Vyas <77309+jitendravyas@users.noreply.github.com>
# Starting point for the Arch User Repository. Not published on the AUR yet.

pkgname=sheaf
pkgver=0.1.0
pkgrel=1
pkgdesc="Sheaf — local scratchpad for code snippets, plain text, and Markdown notes"
arch=('any')
url="https://github.com/jitendravyas/sheaf"
license=('MIT')
depends=('gtk4' 'libadwaita' 'gtksourceview5' 'python' 'python-gobject')
makedepends=('meson' 'ninja' 'git' 'gettext')
source=("git+https://github.com/jitendravyas/sheaf.git#branch=main")
sha256sums=('SKIP')

pkgver() {
  cd "$srcdir/sheaf"
  local describe
  if describe=$(git describe --long --tags --abbrev=7 2>/dev/null); then
    echo "$describe" | sed 's/^v//;s/\([^-]*-g\)/r\1/;s/-/./g'
  else
    printf "%s.r%s.g%s" "0.1.0" "$(git rev-list --count HEAD)" "$(git rev-parse --short HEAD)"
  fi
}

build() {
  art="$srcdir/sheaf"
  if command -v arch-meson >/dev/null 2>&1; then
    arch-meson "$art" build
  else
    meson setup build "$art" --prefix=/usr
  fi
  meson compile -C build
}

package() {
  meson install -C build --destdir "$pkgdir"
  install -Dm644 "$srcdir/sheaf/LICENSE" "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}

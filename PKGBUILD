# Maintainer: Jitendra Vyas <77309+jitendravyas@users.noreply.github.com>
# Starting point for the Arch User Repository. Not published on the AUR yet.

pkgname=omarchy-notes
pkgver=0.1.0
pkgrel=1
pkgdesc="Local code snippet scratchpad for the Linux desktop"
arch=('any')
url="https://github.com/jitendravyas/omarchy-notes"
license=('MIT')
depends=('gtk4' 'libadwaita' 'python' 'python-gobject')
makedepends=('meson' 'ninja' 'git')
source=("git+https://github.com/jitendravyas/omarchy-notes.git#branch=main")
sha256sums=('SKIP')

pkgver() {
  cd "$srcdir/omarchy-notes"
  local describe
  if describe=$(git describe --long --tags --abbrev=7 2>/dev/null); then
    echo "$describe" | sed 's/^v//;s/\([^-]*-g\)/r\1/;s/-/./g'
  else
    printf "%s.r%s.g%s" "0.1.0" "$(git rev-list --count HEAD)" "$(git rev-parse --short HEAD)"
  fi
}

build() {
  art="$srcdir/omarchy-notes"
  if command -v arch-meson >/dev/null 2>&1; then
    arch-meson "$art" build
  else
    meson setup build "$art" --prefix=/usr
  fi
  meson compile -C build
}

package() {
  meson install -C build --destdir "$pkgdir"
  install -Dm644 "$srcdir/omarchy-notes/LICENSE" "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}

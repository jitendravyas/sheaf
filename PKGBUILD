# Maintainer: Jitendra Vyas <77309+jitendravyas@users.noreply.github.com>

pkgname=sheaf
pkgver=0.1.0
pkgrel=1
pkgdesc="Local scratchpad for code snippets, plain text, and Markdown notes"
arch=('any')
url="https://github.com/jitendravyas/sheaf"
license=('MIT')
depends=('gtk4' 'libadwaita' 'gtksourceview5' 'python' 'python-gobject')
makedepends=('meson' 'ninja' 'gettext')
source=("$pkgname-$pkgver.tar.gz::https://github.com/jitendravyas/sheaf/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('5c0ce8369969f57f310aa44261358505f0404e3a0537a1a81ecac86c0334e87f')

build() {
  local src="$srcdir/$pkgname-$pkgver"
  meson setup build "$src" --prefix=/usr
  meson compile -C build
}

package() {
  meson install -C build --destdir "$pkgdir"
  install -Dm644 "$srcdir/$pkgname-$pkgver/LICENSE" "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}

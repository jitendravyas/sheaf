# Sheaf

Local GTK 4 / libadwaita scratchpad for code snippets, plain text, and Markdown notes. Search, copy a body to the clipboard, and save under `$XDG_DATA_HOME`. The window title is **Sheaf**. The application id is `app.sheaf.Sheaf`. On first run, snippets.json and window.json are copied from the previous data directory if present.

This project is not on Flathub and is not published to the AUR or other distribution repositories. It has not been widely tested.

![Sheaf app](screenshot.png)

## Requirements

- Python 3
- GTK 4
- libadwaita
- GtkSourceView 5
- PyGObject

On Debian or Ubuntu:

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-gtksource-5 meson ninja-build gettext desktop-file-utils appstream
```

On Arch Linux:

```bash
sudo pacman -S python python-gobject gtk4 libadwaita gtksourceview5 meson ninja gettext desktop-file-utils appstream
```

## Run from source

```bash
python3 src/main.py
```

Notes are stored at `$XDG_DATA_HOME/app.sheaf.Sheaf/snippets.json` (or `~/.local/share/app.sheaf.Sheaf/snippets.json` if `XDG_DATA_HOME` is unset).

Each item is `{id, title, format, language, body, updated}`. `format` is `code`, `text`, or `markdown`. First launch starts empty. New asks for Code, Plain text, or Markdown once; that type is then locked. Edits autosave.

## Build and install with Meson

```bash
meson setup builddir
meson compile -C builddir
meson test -C builddir --print-errorlogs
sudo meson install -C builddir
```

This installs the `notes` command, a desktop entry named Sheaf, AppStream metadata, and the application icon.

## Build with makepkg

The `PKGBUILD` in this repo builds package `sheaf` from https://github.com/jitendravyas/sheaf. It is a template only — the package is not on the AUR.

```bash
makepkg -si
```

## Build a Flatpak locally

The Flatpak manifest is for local packaging tests. There is no Flathub listing.

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//48 org.gnome.Sdk//48
flatpak-builder --user --install --force-clean build-flatpak app.sheaf.Sheaf.json
flatpak run app.sheaf.Sheaf
```

Optional Omarchy theme: copy `data/omarchy/sheaf.css.tpl` to `~/.config/omarchy/themed/` so Sheaf can follow the active palette; otherwise it uses Adwaita.

## License

MIT License. Copyright 2026 Jitendra Vyas.

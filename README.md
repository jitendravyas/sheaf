# Sheaf

A local scratchpad for Linux. Keep the commands and fragments you reuse, jot a reminder, or draft Markdown. Search, copy, paste somewhere else. Nothing leaves this computer.

![Sheaf](screenshot.png)

Sheaf is not in Flathub, the AUR, or other software stores yet. Install it from this repo.

## Install

On Arch and Omarchy, install **sheaf** from the AUR (search in the software installer, or `yay -S sheaf`) once it is listed. On other desktops, install it from Flathub once the listing is up.

Until then, run it from this repo.

## Try it

Needs Python 3, GTK 4, libadwaita, GtkSourceView 5, and PyGObject.

**Arch / Omarchy**

```bash
sudo pacman -S python python-gobject gtk4 libadwaita gtksourceview5
git clone https://github.com/jitendravyas/sheaf.git
cd sheaf
python3 src/main.py
```

**Debian / Ubuntu**

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-gtksource-5
git clone https://github.com/jitendravyas/sheaf.git
cd sheaf
python3 src/main.py
```

To put **Sheaf** in your app menu, install with Meson (see [Build](#build)). The command name is `sheaf`.

## Use it

First launch is empty. Press **Ctrl+N** (or the + button) and pick a type once:

- **Code** — syntax highlighting; language is detected when you paste
- **Plain text** — a note with no formatting
- **Markdown** — write Markdown, preview with **Ctrl+P**

Type is locked after that. Edits save by themselves.

In the list, search by title or body (**Ctrl+F**). Copy a note without opening it (the copy button on the row, or **Ctrl+Shift+C**). Pin favorites so they stay at the top. Delete is undoable from the toast that appears.

Notes live in `~/.local/share/app.sheaf.Sheaf/`. If you used an older build, they are copied here on first run.

On Omarchy, copy `data/omarchy/sheaf.css.tpl` to `~/.config/omarchy/themed/` to follow the active palette. Otherwise Sheaf uses Adwaita.

## Keyboard shortcuts

| Action | Keys |
| --- | --- |
| New note | Ctrl+N |
| Search | Ctrl+F or Ctrl+K |
| Copy body | Ctrl+Shift+C |
| Pin or unpin | Ctrl+Shift+P |
| Delete (undo from the toast) | Ctrl+Delete |
| Markdown preview | Ctrl+P |
| Show or hide the list | F9 |
| All shortcuts | Ctrl+? |

## Build

To install a launcher, icon, and the `sheaf` command:

```bash
# Arch extra build tools
sudo pacman -S meson ninja gettext desktop-file-utils appstream

# Debian / Ubuntu extra build tools
sudo apt install meson ninja-build gettext desktop-file-utils appstream

meson setup builddir
meson compile -C builddir
meson test -C builddir --print-errorlogs
sudo meson install -C builddir
```

There is a `PKGBUILD` (package name `sheaf`) and a Flatpak manifest for local packaging tests. Neither is published.

## License

MIT. Copyright 2026 Jitendra Vyas.

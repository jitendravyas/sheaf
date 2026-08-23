# Snippets

A local scratchpad for **code snippets**, **plain text**, and **Markdown**
notes. Keep the commands and fragments you reuse, write a short note, or
draft Markdown — then find it instantly and copy the body to the clipboard.

It uses GTK 4 and libadwaita. The window title is **Snippets**. The application
id is still `io.github.jitendravyas.Notes` so existing desktop, D-Bus, and
data-directory paths stay stable.

This project is **not** on Flathub, and it is **not** published to the AUR
or other distribution repositories. It has not been widely tested on Linux
desktops yet.

![Snippets app](screenshot.png)

## Why this exists

Omarchy and Arch developers already live in a terminal. Snippets is for the
stuff you should not have to remember: a pacman / `omarchy pkg` line, a git
undo, an ssh `Host` block, a Python venv, an rsync exclude list — plus the
plain-text reminders and Markdown meeting notes that sit next to them. First
launch seeds a few of those. After that it is your scratchpad.

## Install on Omarchy

Omarchy is Arch Linux. The first-class way to install extra apps is the AUR,
not a Quickshell plugin and not a Flathub listing (those may come later).

Once a `PKGBUILD` is published on [aur.archlinux.org](https://aur.archlinux.org):

1. Press **Super+Space**
2. Choose **Install**
3. Search the **AUR** for `omarchy-notes`

Or, later, from a terminal:

```bash
omarchy pkg add omarchy-notes
```

This repository already includes a `PKGBUILD` so that can happen. It is a
template only — the package is **not** on the AUR yet. Until it is published,
install from source with Meson (below) or `makepkg` against this repo.

## Other Linux desktops

On GNOME and most other desktops, people usually install apps from Flathub
after a listing exists:

```bash
flatpak install flathub io.github.jitendravyas.Notes
```

There is no Flathub listing yet. A Flatpak manifest is included for local
builds only.

## Requirements

- Python 3
- GTK 4
- libadwaita
- PyGObject

On Debian or Ubuntu:

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1
```

On Arch Linux (including Omarchy):

```bash
sudo pacman -S python python-gobject gtk4 libadwaita
```

To build and install you also need Meson and Ninja:

```bash
sudo apt install meson ninja-build
# or
sudo pacman -S meson ninja
```

## Run from source

```bash
python3 src/main.py
```

Notes are stored in your user data directory, not next to the source files:

`$XDG_DATA_HOME/io.github.jitendravyas.Notes/snippets.json`

If `XDG_DATA_HOME` is unset, that is
`~/.local/share/io.github.jitendravyas.Notes/snippets.json`.

Each item is `{id, title, format, language, body, updated}`. `format` is
`code`, `text`, or `markdown`. The first launch seeds useful code snippets
plus a plain-text note and a Markdown note. After that, New, Delete, and
edits are saved automatically. New items reuse the last format you chose.

## Build and install with Meson

```bash
meson setup builddir
meson compile -C builddir
sudo meson install -C builddir
```

This installs the `notes` command, a desktop entry named Snippets, AppStream
metadata, and the application icon so the app appears in your application menu.

## Build with makepkg (Arch / Omarchy)

The `PKGBUILD` in this repo builds package `omarchy-notes` from
https://github.com/jitendravyas/omarchy-notes.

```bash
makepkg -si
```

That still does not put the package on the AUR. Publishing means uploading
the PKGBUILD to aur.archlinux.org under `omarchy-notes`.

## Build a Flatpak locally

The repository includes a Flatpak manifest for GNOME Platform 47. That is for
local packaging tests. It is **not** a Flathub listing.

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//47 org.gnome.Sdk//47
flatpak-builder --user --install --force-clean build-flatpak io.github.jitendravyas.Notes.json
flatpak run io.github.jitendravyas.Notes
```

## Features

- Write each item as **code**, **plain text**, or **Markdown**
- Sidebar list with title, format tag (bash / text / md), and a one-line preview
- Instant search (title, language, or body)
- Code mode: language tag and a monospace editor
- Plain text mode: proportional font, language field hidden
- Markdown mode: comfortable editor plus a Preview that renders headings,
  lists, bold/italic, code, and links (a conservative subset, stdlib + GTK)
- Copy the body (toolbar button, Ctrl+Shift+C, or Ctrl+C when you are not selecting text)
- New item (toolbar or Ctrl+N) remembers the last format
- Delete with confirmation
- Autosave
- Single-instance application (`io.github.jitendravyas.Notes`)

## License

MIT License. Copyright 2026 Jitendra Vyas.

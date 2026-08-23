#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Snippets — GTK 4 / libadwaita code snippet scratchpad."""

from __future__ import annotations

import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, Gtk  # noqa: E402

# Allow `python3 src/main.py` before Meson install.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from window import APP_ID, SnippetsWindow  # noqa: E402


class SnippetsApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.create_action("quit", self.on_quit, ["<primary>q"])
        self.create_action("about", self.on_about)

    def do_activate(self) -> None:
        win = self.props.active_window
        if win is None:
            win = SnippetsWindow(application=self)
        win.present()

    def create_action(self, name: str, callback, shortcuts: list[str] | None = None) -> None:
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)

    def on_quit(self, *_args) -> None:
        self.quit()

    def on_about(self, *_args) -> None:
        dialog = Adw.AboutDialog(
            application_name="Snippets",
            application_icon=APP_ID,
            developer_name="Jitendra Vyas",
            version="0.1.0",
            website="https://github.com/jitendravyas/omarchy-notes",
            issue_url="https://github.com/jitendravyas/omarchy-notes/issues",
            license_type=Gtk.License.MIT_X11,
            comments="A local code snippet scratchpad for the Linux desktop.",
            developers=["Jitendra Vyas"],
            copyright="© 2026 Jitendra Vyas",
        )
        dialog.present(self.props.active_window)


def main() -> int:
    app = SnippetsApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())

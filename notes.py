#!/usr/bin/env python3
"""Notes — a compact GTK3 notes app for Linux (Omarchy / Hyprland / any GTK desktop)."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk, Pango  # noqa: E402

try:
    APP_DIR = Path(__file__).resolve().parent
except NameError:
    APP_DIR = Path("/workspace/omarchy-notes")
NOTES_PATH = APP_DIR / "notes.json"

SAMPLE_NOTES = [
    {
        "id": "seed-welcome",
        "title": "Welcome to Notes",
        "body": (
            "A small native notes app for Linux.\n\n"
            "• Click a note on the left to open it\n"
            "• Edit the title or body — changes save automatically\n"
            "• Use New to start a blank note, Delete to remove one\n\n"
            "Notes are stored locally as JSON next to this app."
        ),
        "updated": "2026-08-23T10:15:00+00:00",
    },
    {
        "id": "seed-omarchy",
        "title": "Omarchy desktop notes",
        "body": (
            "Omarchy is Arch Linux with Hyprland.\n\n"
            "This app is a regular GTK3 program, so it runs anywhere "
            "GTK does — including Omarchy, GNOME, and XFCE.\n\n"
            "Launch it with:\n    python3 notes.py"
        ),
        "updated": "2026-08-22T18:40:00+00:00",
    },
    {
        "id": "seed-ideas",
        "title": "Ideas for later",
        "body": (
            "• Keyboard shortcut for new note (Ctrl+N already works)\n"
            "• Search / filter the sidebar\n"
            "• Export a note as Markdown\n"
            "• Sync folder later if we want more than one machine"
        ),
        "updated": "2026-08-21T07:05:00+00:00",
    },
]

CSS = b"""
window {
  background-color: #1c1c1e;
  color: #f2f2f7;
  font-family: "Inter", "Cantarell", "Noto Sans", sans-serif;
  font-size: 13px;
}

headerbar {
  background-image: none;
  background-color: #2c2c2e;
  color: #f2f2f7;
  border-bottom: 1px solid #3a3a3c;
  min-height: 46px;
  padding: 0 8px;
  box-shadow: none;
}

headerbar label {
  color: #f2f2f7;
  font-weight: 600;
  font-size: 14px;
}

headerbar button {
  background-image: none;
  background-color: #3a3a3c;
  color: #f2f2f7;
  border: none;
  border-radius: 8px;
  padding: 6px 14px;
  min-height: 28px;
  box-shadow: none;
}

headerbar button:hover { background-color: #48484a; }

headerbar button.destructive-action {
  background-color: #3a2020;
  color: #ff8a80;
}

headerbar button.suggested-action {
  background-color: #0a84ff;
  color: #ffffff;
}

.sidebar { background-color: #242426; border-right: 1px solid #3a3a3c; }
.sidebar list { background-color: #242426; }
.sidebar row { padding: 10px 12px; border-radius: 8px; margin: 2px 8px; }
.sidebar row:hover { background-color: #2c2c2e; }
.sidebar row:selected { background-color: #0a84ff; }
.sidebar row:selected label { color: #ffffff; }

.note-title { font-weight: 600; font-size: 13px; color: #f2f2f7; }
.note-preview { font-size: 11px; color: #8e8e93; }
.sidebar row:selected .note-preview { color: #d6e9ff; }

entry, entry.text, .title-entry {
  background-image: none;
  background-color: #1c1c1e;
  color: #f2f2f7;
  font-size: 22px;
  font-weight: 600;
  border: none;
  box-shadow: none;
  padding: 16px 20px 8px 20px;
  caret-color: #0a84ff;
}

textview, textview text {
  background-color: #1c1c1e;
  color: #e5e5ea;
  font-size: 14px;
}

.editor-frame, scrolledwindow, stack { background-color: #1c1c1e; }

.status-bar {
  background-color: #2c2c2e;
  color: #8e8e93;
  font-size: 11px;
  padding: 4px 12px;
  border-top: 1px solid #3a3a3c;
}

.empty-label { color: #8e8e93; font-size: 14px; }

scrollbar slider { background-color: #48484a; border-radius: 8px; min-width: 8px; }
scrollbar trough { background-color: #1c1c1e; }
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def preview_of(body: str, limit: int = 56) -> str:
    compact = " ".join((body or "").split())
    if not compact:
        return "Empty note"
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"


def format_updated(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone().strftime("%b %d, %Y  %H:%M")
    except (ValueError, TypeError):
        return iso or ""


class NotesApp(Gtk.Window):
    def __init__(self) -> None:
        settings = Gtk.Settings.get_default()
        if settings is not None:
            settings.set_property("gtk-application-prefer-dark-theme", True)

        super().__init__(title="Notes")
        self.set_default_size(900, 600)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("destroy", Gtk.main_quit)

        self.notes: list[dict] = []
        self.current_id: str | None = None
        self._loading = False
        self._save_timeout: int | None = None

        self._apply_css()
        self._build_ui()
        self._load_notes()
        first = self.notes[0]["id"] if self.notes else None
        self._refresh_list(select_id=first)

    def _apply_css(self) -> None:
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _build_ui(self) -> None:
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title("Notes")
        header.set_subtitle("Local notes")
        self.set_titlebar(header)

        new_btn = Gtk.Button(label="New")
        new_btn.get_style_context().add_class("suggested-action")
        new_btn.set_tooltip_text("Create a note  (Ctrl+N)")
        new_btn.connect("clicked", self.on_new)
        header.pack_start(new_btn)

        del_btn = Gtk.Button(label="Delete")
        del_btn.get_style_context().add_class("destructive-action")
        del_btn.set_tooltip_text("Delete the selected note")
        del_btn.connect("clicked", self.on_delete)
        header.pack_end(del_btn)
        self.delete_button = del_btn

        accel = Gtk.AccelGroup()
        self.add_accel_group(accel)
        new_btn.add_accelerator(
            "clicked", accel, Gdk.KEY_n, Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE
        )

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(root)

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        root.pack_start(paned, True, True, 0)

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar.get_style_context().add_class("sidebar")
        sidebar.set_size_request(260, -1)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-selected", self.on_row_selected)

        side_scroll = Gtk.ScrolledWindow()
        side_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        side_scroll.add(self.listbox)
        sidebar.pack_start(side_scroll, True, True, 0)
        paned.pack1(sidebar, False, False)

        editor = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        editor.get_style_context().add_class("editor-frame")

        self.empty_label = Gtk.Label(label="No note selected.\nClick New to write one.")
        self.empty_label.set_justify(Gtk.Justification.CENTER)
        self.empty_label.get_style_context().add_class("empty-label")

        self.editor_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.title_entry = Gtk.Entry()
        self.title_entry.set_placeholder_text("Title")
        self.title_entry.get_style_context().add_class("title-entry")
        self.title_entry.connect("changed", self.on_editor_changed)
        self.editor_box.pack_start(self.title_entry, False, False, 0)

        self.body_view = Gtk.TextView()
        self.body_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.body_view.set_left_margin(20)
        self.body_view.set_right_margin(20)
        self.body_view.set_top_margin(8)
        self.body_view.set_bottom_margin(20)
        self.body_view.set_accepts_tab(True)
        self.body_buffer = self.body_view.get_buffer()
        self.body_buffer.connect("changed", self.on_editor_changed)

        body_scroll = Gtk.ScrolledWindow()
        body_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        body_scroll.add(self.body_view)
        self.editor_box.pack_start(body_scroll, True, True, 0)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.NONE)
        self.stack.add_named(self.empty_label, "empty")
        self.stack.add_named(self.editor_box, "editor")
        editor.pack_start(self.stack, True, True, 0)

        paned.pack2(editor, True, False)
        paned.set_position(280)

        self.status = Gtk.Label(label="Ready", xalign=0)
        self.status.get_style_context().add_class("status-bar")
        root.pack_end(self.status, False, False, 0)

    def _load_notes(self) -> None:
        if NOTES_PATH.exists():
            try:
                data = json.loads(NOTES_PATH.read_text(encoding="utf-8"))
                if isinstance(data, list) and data:
                    self.notes = data
                    return
            except (OSError, json.JSONDecodeError):
                pass
        self.notes = [dict(n) for n in SAMPLE_NOTES]
        self._write_notes()

    def _write_notes(self) -> None:
        tmp = NOTES_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.notes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, NOTES_PATH)

    def _find(self, note_id: str | None) -> dict | None:
        if not note_id:
            return None
        return next((n for n in self.notes if n["id"] == note_id), None)

    def _refresh_list(self, select_id: str | None = None) -> None:
        self._loading = True
        for child in self.listbox.get_children():
            self.listbox.remove(child)

        ordered = sorted(self.notes, key=lambda n: n.get("updated", ""), reverse=True)
        target_row = None
        for note in ordered:
            row = Gtk.ListBoxRow()
            row.note_id = note["id"]  # type: ignore[attr-defined]

            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            title = Gtk.Label(label=note.get("title") or "Untitled", xalign=0)
            title.get_style_context().add_class("note-title")
            title.set_ellipsize(Pango.EllipsizeMode.END)
            title.set_max_width_chars(28)

            preview = Gtk.Label(label=preview_of(note.get("body", "")), xalign=0)
            preview.get_style_context().add_class("note-preview")
            preview.set_ellipsize(Pango.EllipsizeMode.END)
            preview.set_max_width_chars(32)

            box.pack_start(title, False, False, 0)
            box.pack_start(preview, False, False, 0)
            row.add(box)
            self.listbox.add(row)
            if note["id"] == select_id:
                target_row = row

        self.listbox.show_all()
        if target_row is not None:
            self.listbox.select_row(target_row)
            self._loading = False
            note = self._find(select_id)
            if note:
                self._load_note_into_editor(note)
            return
        if not ordered:
            self._show_empty()
        self._loading = False

    def _show_empty(self) -> None:
        self.current_id = None
        self.stack.set_visible_child_name("empty")
        self.delete_button.set_sensitive(False)
        self.status.set_text("No notes yet")

    def _show_editor(self) -> None:
        self.stack.set_visible_child_name("editor")
        self.delete_button.set_sensitive(True)

    def on_row_selected(self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        if self._loading:
            return
        if row is None:
            self._show_empty()
            return
        self._flush_pending_save()
        note = self._find(getattr(row, "note_id", None))
        if not note:
            self._show_empty()
            return
        self._load_note_into_editor(note)

    def _load_note_into_editor(self, note: dict) -> None:
        self._loading = True
        self.current_id = note["id"]
        self.title_entry.set_text(note.get("title", ""))
        self.body_buffer.set_text(note.get("body", ""))
        self._show_editor()
        self.status.set_text(f"Edited  {format_updated(note.get('updated', ''))}")
        self._loading = False

    def on_editor_changed(self, *_args) -> None:
        if self._loading or not self.current_id:
            return
        note = self._find(self.current_id)
        if not note:
            return
        note["title"] = self.title_entry.get_text()
        start, end = self.body_buffer.get_bounds()
        note["body"] = self.body_buffer.get_text(start, end, True)
        note["updated"] = now_iso()
        self.status.set_text("Saving…")
        if self._save_timeout is not None:
            GLib.source_remove(self._save_timeout)
        self._save_timeout = GLib.timeout_add(350, self._autosave)

    def _autosave(self) -> bool:
        self._save_timeout = None
        self._write_notes()
        self._update_selected_row_labels()
        note = self._find(self.current_id)
        when = format_updated(note["updated"]) if note else ""
        self.status.set_text(f"Saved  {when}")
        return False

    def _flush_pending_save(self) -> None:
        if self._save_timeout is not None:
            GLib.source_remove(self._save_timeout)
            self._save_timeout = None
            self._write_notes()

    def _update_selected_row_labels(self) -> None:
        row = self.listbox.get_selected_row()
        note = self._find(self.current_id)
        if row is None or note is None:
            return
        box = row.get_child()
        children = box.get_children()
        if len(children) >= 2:
            children[0].set_text(note.get("title") or "Untitled")
            children[1].set_text(preview_of(note.get("body", "")))

    def on_new(self, *_args) -> None:
        self._flush_pending_save()
        note = {
            "id": str(uuid.uuid4()),
            "title": "Untitled",
            "body": "",
            "updated": now_iso(),
        }
        self.notes.insert(0, note)
        self._write_notes()
        self._refresh_list(select_id=note["id"])
        self.title_entry.grab_focus()
        self.title_entry.select_region(0, -1)
        self.status.set_text("New note")

    def on_delete(self, *_args) -> None:
        if not self.current_id:
            return
        note = self._find(self.current_id)
        title = (note or {}).get("title") or "Untitled"

        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.NONE,
            text=f"Delete “{title}”?",
        )
        dialog.format_secondary_text("This cannot be undone.")
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Delete", Gtk.ResponseType.ACCEPT)
        dialog.set_default_response(Gtk.ResponseType.CANCEL)
        response = dialog.run()
        dialog.destroy()
        if response != Gtk.ResponseType.ACCEPT:
            return

        self.notes = [n for n in self.notes if n["id"] != self.current_id]
        self.current_id = None
        self._write_notes()
        next_id = self.notes[0]["id"] if self.notes else None
        self._refresh_list(select_id=next_id)
        self.status.set_text("Note deleted")


def main() -> None:
    app = NotesApp()
    app.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()

# SPDX-License-Identifier: MIT
"""Main window for Notes."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Graphene, Gtk, Pango  # noqa: E402

APP_ID = "io.github.jitendravyas.Notes"

SAMPLE_NOTES = [
    {
        "id": "seed-welcome",
        "title": "Welcome to Notes",
        "body": (
            "A simple notes app for your Linux desktop.\n\n"
            "• Select a note in the sidebar to open it\n"
            "• Edit the title or body — changes save automatically\n"
            "• Use New or Ctrl+N to start a note\n"
            "• Delete asks for confirmation first\n\n"
            "Notes stay on this computer in your user data directory."
        ),
        "updated": "2026-08-23T10:15:00+00:00",
    },
    {
        "id": "seed-omarchy",
        "title": "Omarchy desktop notes",
        "body": (
            "Omarchy is Arch Linux with Hyprland.\n\n"
            "Notes is a GTK 4 and libadwaita app, so it fits GNOME, "
            "Omarchy, and other GTK desktops.\n\n"
            "On Omarchy, apps are typically installed from the AUR once "
            "a package is published."
        ),
        "updated": "2026-08-22T18:40:00+00:00",
    },
    {
        "id": "seed-ideas",
        "title": "Ideas for later",
        "body": (
            "• Search the sidebar\n"
            "• Export a note as Markdown\n"
            "• Sync later if you use more than one machine"
        ),
        "updated": "2026-08-21T07:05:00+00:00",
    },
]

CSS = b"""
.title-entry {
  font-size: 22px;
  font-weight: 600;
  background: transparent;
}

.note-title {
  font-weight: 600;
}

.note-preview {
  font-size: 0.85em;
  opacity: 0.65;
}

.status-bar {
  font-size: 0.8em;
  padding: 6px 14px;
  opacity: 0.7;
}
"""


def notes_file() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    directory = base / APP_ID
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "notes.json"


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


class NotesWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs) -> None:
        super().__init__(title="Notes", **kwargs)
        self.set_default_size(960, 640)
        self.set_icon_name(APP_ID)

        self.notes: list[dict] = []
        self.current_id: str | None = None
        self._loading = False
        self._save_timeout: int | None = None

        self._add_icon_search_path()
        self._apply_css()
        self._build_ui()
        self._add_actions()
        self._load_notes()
        first = self.notes[0]["id"] if self.notes else None
        self._refresh_list(select_id=first)

        if os.environ.get("NOTES_SCREENSHOT"):
            GLib.timeout_add(900, self._save_screenshot)

    def _add_icon_search_path(self) -> None:
        icon_dir = Path(__file__).resolve().parent.parent / "data" / "icons"
        if icon_dir.is_dir():
            display = Gdk.Display.get_default()
            if display is not None:
                Gtk.IconTheme.get_for_display(display).add_search_path(str(icon_dir))

    def _apply_css(self) -> None:
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def _add_actions(self) -> None:
        new_action = Gio.SimpleAction.new("new-note", None)
        new_action.connect("activate", self.on_new)
        self.add_action(new_action)

        delete_action = Gio.SimpleAction.new("delete-note", None)
        delete_action.connect("activate", self.on_delete)
        self.add_action(delete_action)

        app = self.get_application()
        if app is not None:
            app.set_accels_for_action("win.new-note", ["<Control>n"])
            app.set_accels_for_action("win.delete-note", ["<Control>Delete"])

    def _build_ui(self) -> None:
        toolbar = Adw.ToolbarView()
        self.set_content(toolbar)

        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title="Notes", subtitle="Local notes"))
        toolbar.add_top_bar(header)

        new_btn = Gtk.Button()
        new_btn.set_child(Adw.ButtonContent(icon_name="list-add-symbolic", label="New"))
        new_btn.add_css_class("suggested-action")
        new_btn.set_tooltip_text("Create a note  (Ctrl+N)")
        new_btn.connect("clicked", self.on_new)
        header.pack_start(new_btn)

        del_btn = Gtk.Button()
        del_btn.set_child(Adw.ButtonContent(icon_name="user-trash-symbolic", label="Delete"))
        del_btn.add_css_class("destructive-action")
        del_btn.set_tooltip_text("Delete the selected note")
        del_btn.connect("clicked", self.on_delete)
        header.pack_end(del_btn)
        self.delete_button = del_btn

        menu = Gio.Menu()
        menu.append("_About Notes", "app.about")
        menu.append("_Quit", "app.quit")
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu)
        menu_btn.set_tooltip_text("Menu")
        header.pack_end(menu_btn)

        split = Adw.OverlaySplitView()
        split.set_sidebar_width_fraction(0.30)
        split.set_min_sidebar_width(240)
        split.set_max_sidebar_width(380)
        split.set_show_sidebar(True)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.add_css_class("navigation-sidebar")
        self.listbox.connect("row-selected", self.on_row_selected)

        side_scroll = Gtk.ScrolledWindow()
        side_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        side_scroll.set_child(self.listbox)
        side_scroll.set_size_request(260, -1)
        split.set_sidebar(side_scroll)

        self.empty_page = Adw.StatusPage(
            icon_name="document-edit-symbolic",
            title="No note selected",
            description="Choose a note in the sidebar or create a new one.",
        )

        self.editor_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.title_entry = Gtk.Entry()
        self.title_entry.set_placeholder_text("Title")
        self.title_entry.add_css_class("title-entry")
        self.title_entry.set_margin_start(8)
        self.title_entry.set_margin_end(8)
        self.title_entry.connect("changed", self.on_editor_changed)
        self.editor_box.append(self.title_entry)

        self.body_view = Gtk.TextView()
        self.body_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.body_view.set_left_margin(20)
        self.body_view.set_right_margin(20)
        self.body_view.set_top_margin(8)
        self.body_view.set_bottom_margin(20)
        self.body_view.set_accepts_tab(True)
        self.body_view.set_vexpand(True)
        self.body_buffer = self.body_view.get_buffer()
        self.body_buffer.connect("changed", self.on_editor_changed)

        body_scroll = Gtk.ScrolledWindow()
        body_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        body_scroll.set_vexpand(True)
        body_scroll.set_child(self.body_view)
        self.editor_box.append(body_scroll)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.NONE)
        self.stack.add_named(self.empty_page, "empty")
        self.stack.add_named(self.editor_box, "editor")
        split.set_content(self.stack)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.append(split)
        split.set_vexpand(True)

        self.status = Gtk.Label(label="Ready", xalign=0)
        self.status.add_css_class("status-bar")
        self.status.add_css_class("dim-label")
        root.append(self.status)

        toolbar.set_content(root)

    def _load_notes(self) -> None:
        path = notes_file()
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list) and data:
                    self.notes = data
                    return
            except (OSError, json.JSONDecodeError):
                pass
        self.notes = [dict(n) for n in SAMPLE_NOTES]
        self._write_notes()

    def _write_notes(self) -> None:
        path = notes_file()
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.notes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, path)

    def _find(self, note_id: str | None) -> dict | None:
        if not note_id:
            return None
        return next((n for n in self.notes if n["id"] == note_id), None)

    def _refresh_list(self, select_id: str | None = None) -> None:
        self._loading = True
        self.listbox.remove_all()

        ordered = sorted(self.notes, key=lambda n: n.get("updated", ""), reverse=True)
        target_row = None
        for note in ordered:
            row = Gtk.ListBoxRow()
            row.note_id = note["id"]  # type: ignore[attr-defined]

            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            box.set_margin_start(10)
            box.set_margin_end(10)
            box.set_margin_top(8)
            box.set_margin_bottom(8)

            title = Gtk.Label(label=note.get("title") or "Untitled", xalign=0)
            title.add_css_class("note-title")
            title.set_ellipsize(Pango.EllipsizeMode.END)
            title.set_max_width_chars(28)

            preview = Gtk.Label(label=preview_of(note.get("body", "")), xalign=0)
            preview.add_css_class("note-preview")
            preview.set_ellipsize(Pango.EllipsizeMode.END)
            preview.set_max_width_chars(32)

            box.append(title)
            box.append(preview)
            row.set_child(box)
            self.listbox.append(row)
            if note["id"] == select_id:
                target_row = row

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
        start = self.body_buffer.get_start_iter()
        end = self.body_buffer.get_end_iter()
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
        if box is None:
            return
        children = []
        child = box.get_first_child()
        while child is not None:
            children.append(child)
            child = child.get_next_sibling()
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

        dialog = Adw.AlertDialog(
            heading=f"Delete “{title}”?",
            body="This cannot be undone.",
        )
        dialog.add_response("cancel", "_Cancel")
        dialog.add_response("delete", "_Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.choose(self, None, self._on_delete_chosen)

    def _on_delete_chosen(self, dialog: Adw.AlertDialog, result) -> None:
        try:
            response = dialog.choose_finish(result)
        except GLib.Error:
            return
        if response != "delete":
            return
        self.notes = [n for n in self.notes if n["id"] != self.current_id]
        self.current_id = None
        self._write_notes()
        next_id = self.notes[0]["id"] if self.notes else None
        self._refresh_list(select_id=next_id)
        self.status.set_text("Note deleted")

    def _save_screenshot(self) -> bool:
        path = os.environ.get("NOTES_SCREENSHOT")
        if not path:
            return False
        native = self.get_native()
        renderer = native.get_renderer() if native is not None else None
        if renderer is None:
            app = self.get_application()
            if app is not None:
                app.quit()
            return False

        width = self.get_width()
        height = self.get_height()
        if width < 8 or height < 8:
            GLib.timeout_add(400, self._save_screenshot)
            return False

        paintable = Gtk.WidgetPaintable.new(self)
        snapshot = Gtk.Snapshot()
        paintable.snapshot(snapshot, width, height)
        node = snapshot.to_node()
        if node is None:
            app = self.get_application()
            if app is not None:
                app.quit()
            return False

        rect = Graphene.Rect()
        rect.init(0, 0, float(width), float(height))
        texture = renderer.render_texture(node, rect)
        texture.save_to_png(path)
        app = self.get_application()
        if app is not None:
            app.quit()
        return False

# SPDX-License-Identifier: MIT
"""Main window for Snippets — code, plain text, and Markdown notes."""

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

from markdown import (  # noqa: E402
    FORMATS,
    inline_to_pango,
    normalize_format,
    parse_markdown,
    sidebar_kind,
)

APP_ID = "io.github.jitendravyas.Notes"

SAMPLE_SNIPPETS = [
    {
        "id": "seed-pacman",
        "title": "Install or update a package",
        "format": "code",
        "language": "bash",
        "body": (
            "# Search the repos, then install\n"
            "pacman -Ss nginx\n"
            "sudo pacman -S nginx\n"
            "\n"
            "# Full system upgrade\n"
            "sudo pacman -Syu\n"
            "\n"
            "# Remove a package and unneeded deps\n"
            "sudo pacman -Rns nginx\n"
            "\n"
            "# Omarchy helper (once the package is in the AUR)\n"
            "omarchy pkg add <name>\n"
            "omarchy pkg update\n"
        ),
        "updated": "2026-08-23T14:10:00+00:00",
    },
    {
        "id": "seed-git-undo",
        "title": "Undo the last git commit",
        "format": "code",
        "language": "git",
        "body": (
            "# Keep all changes, still staged\n"
            "git reset --soft HEAD~1\n"
            "\n"
            "# Keep changes, unstage them (default mixed reset)\n"
            "git reset HEAD~1\n"
            "\n"
            "# Amend the last commit (message or forgotten files)\n"
            "git add <file>\n"
            "git commit --amend --no-edit\n"
            "\n"
            "# Restore one file from HEAD\n"
            "git restore --source=HEAD -- path/to/file\n"
            "\n"
            "# Abort an in-progress rebase or merge\n"
            "git rebase --abort\n"
            "git merge --abort\n"
        ),
        "updated": "2026-08-23T13:40:00+00:00",
    },
    {
        "id": "seed-ssh",
        "title": "SSH config for a host",
        "format": "code",
        "language": "ssh",
        "body": (
            "# ~/.ssh/config\n"
            "Host github.com\n"
            "    HostName github.com\n"
            "    User git\n"
            "    IdentityFile ~/.ssh/id_ed25519\n"
            "    IdentitiesOnly yes\n"
            "\n"
            "Host prod\n"
            "    HostName 203.0.113.10\n"
            "    User deploy\n"
            "    Port 22\n"
            "    IdentityFile ~/.ssh/id_ed25519\n"
            "    ForwardAgent no\n"
            "    ServerAliveInterval 30\n"
            "    ServerAliveCountMax 3\n"
        ),
        "updated": "2026-08-23T12:15:00+00:00",
    },
    {
        "id": "seed-venv",
        "title": "Python virtualenv",
        "format": "code",
        "language": "python",
        "body": (
            "python3 -m venv .venv\n"
            "source .venv/bin/activate\n"
            "python -m pip install -U pip setuptools wheel\n"
            "pip install -r requirements.txt\n"
            "\n"
            "# Freeze what you actually use\n"
            "pip freeze > requirements.txt\n"
            "\n"
            "# Leave the venv\n"
            "deactivate\n"
        ),
        "updated": "2026-08-23T11:05:00+00:00",
    },
    {
        "id": "seed-rsync",
        "title": "rsync a project over SSH",
        "format": "code",
        "language": "bash",
        "body": (
            "rsync -aP --delete \\\n"
            "  --exclude '.git/' \\\n"
            "  --exclude '.venv/' \\\n"
            "  --exclude 'node_modules/' \\\n"
            "  --exclude '__pycache__/' \\\n"
            "  --exclude 'dist/' \\\n"
            "  ./ user@host:~/projects/app/\n"
        ),
        "updated": "2026-08-22T19:30:00+00:00",
    },
    {
        "id": "seed-fetch",
        "title": "Fetch JSON from an API",
        "format": "code",
        "language": "javascript",
        "body": (
            "const res = await fetch(\"https://api.example.com/v1/items\", {\n"
            "  method: \"POST\",\n"
            "  headers: {\n"
            "    \"Content-Type\": \"application/json\",\n"
            "    Accept: \"application/json\",\n"
            "  },\n"
            "  body: JSON.stringify({ name: \"example\" }),\n"
            "});\n"
            "\n"
            "if (!res.ok) {\n"
            "  throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);\n"
            "}\n"
            "\n"
            "const data = await res.json();\n"
        ),
        "updated": "2026-08-22T16:20:00+00:00",
    },
    {
        "id": "seed-desk-reminder",
        "title": "Desk reminder",
        "format": "text",
        "language": "text",
        "body": (
            "Weekly review — keep this short.\n"
            "\n"
            "Inbox to zero, or at least to a list you trust.\n"
            "Check the calendar for the next two weeks.\n"
            "Pick three tasks that actually matter and drop the rest.\n"
            "\n"
            "Send the Omarchy notes update before Friday.\n"
            "Do not start a new side project until the current one ships.\n"
        ),
        "updated": "2026-08-23T15:20:00+00:00",
    },
    {
        "id": "seed-meeting-md",
        "title": "Meeting notes template",
        "format": "markdown",
        "language": "markdown",
        "body": (
            "# Meeting notes\n"
            "\n"
            "A short **template** for standups and *reviews*.\n"
            "\n"
            "## Agenda\n"
            "\n"
            "- What shipped last week\n"
            "- What is blocked\n"
            "- Next steps\n"
            "\n"
            "## Commands\n"
            "\n"
            "Use `omarchy pkg add` when the AUR package exists.\n"
            "\n"
            "```bash\n"
            "sudo pacman -Syu\n"
            "```\n"
            "\n"
            "See the [Arch wiki](https://wiki.archlinux.org) for more.\n"
            "\n"
            "---\n"
            "\n"
            "> Keep it to one page. If it needs a spec, write a spec.\n"
        ),
        "updated": "2026-08-23T16:05:00+00:00",
    },
]

CSS = b"""
.title-entry {
  font-size: 18px;
  font-weight: 600;
  background: transparent;
}

.lang-entry {
  font-family: monospace;
  font-size: 13px;
}

.snippet-title {
  font-weight: 600;
}

.snippet-lang {
  font-family: monospace;
  font-size: 0.75em;
  opacity: 0.72;
}

.snippet-preview {
  font-size: 0.82em;
  opacity: 0.62;
}

textview.snippet-body.kind-code,
textview.snippet-body.kind-code text,
textview.snippet-body.kind-markdown,
textview.snippet-body.kind-markdown text {
  font-family: "Source Code Pro", "JetBrains Mono", "Fira Code",
    "Noto Sans Mono", "DejaVu Sans Mono", monospace;
  font-size: 13px;
}

textview.snippet-body.kind-text,
textview.snippet-body.kind-text text {
  font-family: Cantarell, "Noto Sans", "DejaVu Sans", sans-serif;
  font-size: 14px;
}

.status-bar {
  font-size: 0.8em;
  padding: 6px 14px;
  opacity: 0.7;
}

.search-wrap {
  padding: 8px 10px 6px 10px;
}

.format-row {
  padding: 2px 10px 6px 10px;
}

.md-preview {
  padding: 14px 20px 24px 20px;
}

.md-h1 {
  font-size: 22px;
  font-weight: 700;
}

.md-h2 {
  font-size: 18px;
  font-weight: 700;
}

.md-h3, .md-h4, .md-h5, .md-h6 {
  font-size: 15px;
  font-weight: 600;
}

.md-paragraph, .md-list-item, .md-quote {
  font-size: 14px;
}

.md-codeblock {
  font-family: "Source Code Pro", "JetBrains Mono", "Fira Code",
    "Noto Sans Mono", "DejaVu Sans Mono", monospace;
  font-size: 12.5px;
  background-color: alpha(@window_fg_color, 0.06);
  padding: 10px 12px;
  border-radius: 8px;
}

.md-quote {
  opacity: 0.86;
  padding-left: 12px;
  border-left: 3px solid alpha(@window_fg_color, 0.28);
}

.md-hr {
  margin-top: 4px;
  margin-bottom: 4px;
}

.md-empty {
  opacity: 0.55;
  font-style: italic;
  padding: 24px 8px;
}
"""


def data_dir() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    directory = base / APP_ID
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def snippets_file() -> Path:
    return data_dir() / "snippets.json"


def notes_file() -> Path:
    """Previous app filename — migrated on first launch if present."""
    return data_dir() / "notes.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def preview_of(body: str, limit: int = 52) -> str:
    compact = " ".join((body or "").split())
    if not compact:
        return "Empty"
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"


def format_updated(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone().strftime("%b %d, %Y  %H:%M")
    except (ValueError, TypeError):
        return iso or ""


def normalize_snippet(raw: dict) -> dict:
    fmt = normalize_format(raw.get("format") or raw.get("kind"))
    language = str(raw.get("language") or "")
    if fmt == "text" and not language:
        language = "text"
    if fmt == "markdown" and not language:
        language = "markdown"
    return {
        "id": str(raw.get("id") or uuid.uuid4()),
        "title": str(raw.get("title") or ""),
        "format": fmt,
        "language": language,
        "body": str(raw.get("body") or ""),
        "updated": str(raw.get("updated") or now_iso()),
    }


def matches_query(snippet: dict, query: str) -> bool:
    if not query:
        return True
    q = query.casefold()
    haystack = " ".join(
        (
            snippet.get("title") or "",
            snippet.get("language") or "",
            snippet.get("format") or "",
            snippet.get("body") or "",
        )
    ).casefold()
    return q in haystack


def _clear_box(box: Gtk.Box) -> None:
    child = box.get_first_child()
    while child is not None:
        nxt = child.get_next_sibling()
        box.remove(child)
        child = nxt


class SnippetsWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs) -> None:
        super().__init__(title="Snippets", **kwargs)
        self.set_default_size(1040, 700)
        self.set_icon_name(APP_ID)

        self.snippets: list[dict] = []
        self.current_id: str | None = None
        self._loading = False
        self._save_timeout: int | None = None
        self._filter = ""
        self._last_format = "code"

        self._add_icon_search_path()
        self._apply_css()
        self._build_ui()
        self._add_actions()
        self._load_snippets()
        first = self.snippets[0]["id"] if self.snippets else None
        newest = max(self.snippets, key=lambda s: s.get("updated", ""), default=None)
        select_id = newest["id"] if newest else first

        screenshot = os.environ.get("NOTES_SCREENSHOT") or os.environ.get(
            "SNIPPETS_SCREENSHOT"
        )
        if screenshot:
            md = next(
                (s for s in self.snippets if s.get("format") == "markdown"), None
            )
            if md:
                select_id = md["id"]

        self._refresh_list(select_id=select_id)

        if screenshot:
            GLib.timeout_add(200, self._prepare_screenshot)
            GLib.timeout_add(1200, self._save_screenshot)

    def _prepare_screenshot(self) -> bool:
        if self.current_id:
            snippet = self._find(self.current_id)
            if snippet and snippet.get("format") == "markdown":
                self.view_toggle.set_active_name("preview")
                self._show_preview()
        return False

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
        new_action = Gio.SimpleAction.new("new-snippet", None)
        new_action.connect("activate", self.on_new)
        self.add_action(new_action)

        delete_action = Gio.SimpleAction.new("delete-snippet", None)
        delete_action.connect("activate", self.on_delete)
        self.add_action(delete_action)

        copy_action = Gio.SimpleAction.new("copy-snippet", None)
        copy_action.connect("activate", self.on_copy)
        self.add_action(copy_action)

        find_action = Gio.SimpleAction.new("find", None)
        find_action.connect("activate", self.on_find)
        self.add_action(find_action)

        preview_action = Gio.SimpleAction.new("toggle-preview", None)
        preview_action.connect("activate", self.on_toggle_preview)
        self.add_action(preview_action)

        app = self.get_application()
        if app is not None:
            app.set_accels_for_action("win.new-snippet", ["<Control>n"])
            app.set_accels_for_action("win.delete-snippet", ["<Control>Delete"])
            app.set_accels_for_action("win.copy-snippet", ["<Control><Shift>c"])
            app.set_accels_for_action("win.find", ["<Control>f", "<Control>k"])
            app.set_accels_for_action("win.toggle-preview", ["<Control>p"])

        key = Gtk.EventControllerKey()
        key.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key)

    def _make_toggle(self, name: str, label: str) -> Adw.Toggle:
        toggle = Adw.Toggle()
        toggle.set_name(name)
        toggle.set_label(label)
        return toggle

    def _build_ui(self) -> None:
        toolbar = Adw.ToolbarView()
        self.set_content(toolbar)

        header = Adw.HeaderBar()
        header.set_title_widget(
            Adw.WindowTitle(title="Snippets", subtitle="Code, text, and Markdown")
        )
        toolbar.add_top_bar(header)

        new_btn = Gtk.Button()
        new_btn.set_child(Adw.ButtonContent(icon_name="list-add-symbolic", label="New"))
        new_btn.set_tooltip_text("Create a note  (Ctrl+N)")
        new_btn.connect("clicked", self.on_new)
        header.pack_start(new_btn)

        menu = Gio.Menu()
        menu.append("_About Snippets", "app.about")
        menu.append("_Quit", "app.quit")
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu)
        menu_btn.set_tooltip_text("Menu")
        header.pack_end(menu_btn)

        del_btn = Gtk.Button()
        del_btn.set_child(Adw.ButtonContent(icon_name="user-trash-symbolic", label="Delete"))
        del_btn.add_css_class("destructive-action")
        del_btn.set_tooltip_text("Delete the selected item")
        del_btn.connect("clicked", self.on_delete)
        header.pack_end(del_btn)
        self.delete_button = del_btn

        copy_btn = Gtk.Button()
        copy_btn.set_child(
            Adw.ButtonContent(icon_name="edit-copy-symbolic", label="Copy snippet")
        )
        copy_btn.add_css_class("suggested-action")
        copy_btn.set_tooltip_text("Copy the body  (Ctrl+Shift+C)")
        copy_btn.connect("clicked", self.on_copy)
        header.pack_end(copy_btn)
        self.copy_button = copy_btn

        split = Adw.OverlaySplitView()
        split.set_sidebar_width_fraction(0.32)
        split.set_min_sidebar_width(260)
        split.set_max_sidebar_width(400)
        split.set_show_sidebar(True)

        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text("Search title, language, or body")
        self.search.set_hexpand(True)
        self.search.connect("search-changed", self.on_search_changed)

        search_wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        search_wrap.add_css_class("search-wrap")
        search_wrap.append(self.search)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.add_css_class("navigation-sidebar")
        self.listbox.connect("row-selected", self.on_row_selected)

        placeholder = Gtk.Label(label="No matching notes")
        placeholder.add_css_class("dim-label")
        placeholder.set_margin_top(16)
        placeholder.set_margin_bottom(16)
        self.listbox.set_placeholder(placeholder)

        side_scroll = Gtk.ScrolledWindow()
        side_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        side_scroll.set_vexpand(True)
        side_scroll.set_child(self.listbox)

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar.append(search_wrap)
        sidebar.append(side_scroll)
        sidebar.set_size_request(260, -1)
        split.set_sidebar(sidebar)

        self.empty_page = Adw.StatusPage(
            icon_name="edit-copy-symbolic",
            title="No note selected",
            description="Choose an item in the sidebar, search, or press Ctrl+N.",
        )

        self.editor_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title_row.set_margin_start(10)
        title_row.set_margin_end(10)
        title_row.set_margin_top(8)

        self.title_entry = Gtk.Entry()
        self.title_entry.set_placeholder_text("Title")
        self.title_entry.add_css_class("title-entry")
        self.title_entry.set_hexpand(True)
        self.title_entry.connect("changed", self.on_editor_changed)
        title_row.append(self.title_entry)

        self.lang_entry = Gtk.Entry()
        self.lang_entry.set_placeholder_text("language")
        self.lang_entry.add_css_class("lang-entry")
        self.lang_entry.set_width_chars(12)
        self.lang_entry.set_max_width_chars(16)
        self.lang_entry.set_tooltip_text("Language tag, e.g. bash, python, git, javascript")
        self.lang_entry.connect("changed", self.on_editor_changed)
        title_row.append(self.lang_entry)
        self.editor_box.append(title_row)

        format_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        format_row.add_css_class("format-row")
        format_row.set_hexpand(True)

        self.format_group = Adw.ToggleGroup()
        self.format_group.set_can_shrink(True)
        self.format_group.set_hexpand(False)
        self.format_group.add(self._make_toggle("code", "Code"))
        self.format_group.add(self._make_toggle("text", "Plain text"))
        self.format_group.add(self._make_toggle("markdown", "Markdown"))
        self.format_group.set_active_name("code")
        self.format_group.set_tooltip_text("Write as code, plain text, or Markdown")
        self.format_group.connect("notify::active-name", self.on_format_changed)
        format_row.append(self.format_group)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        format_row.append(spacer)

        self.view_toggle = Adw.ToggleGroup()
        self.view_toggle.set_can_shrink(True)
        self.view_toggle.add(self._make_toggle("edit", "Edit"))
        self.view_toggle.add(self._make_toggle("preview", "Preview"))
        self.view_toggle.set_active_name("edit")
        self.view_toggle.set_tooltip_text("Toggle Markdown preview  (Ctrl+P)")
        self.view_toggle.connect("notify::active-name", self.on_view_changed)
        format_row.append(self.view_toggle)
        self.editor_box.append(format_row)

        self.body_view = Gtk.TextView()
        self.body_view.add_css_class("snippet-body")
        self.body_view.add_css_class("kind-code")
        self.body_view.set_wrap_mode(Gtk.WrapMode.NONE)
        self.body_view.set_monospace(True)
        self.body_view.set_left_margin(16)
        self.body_view.set_right_margin(16)
        self.body_view.set_top_margin(10)
        self.body_view.set_bottom_margin(16)
        self.body_view.set_accepts_tab(True)
        self.body_view.set_vexpand(True)
        self.body_buffer = self.body_view.get_buffer()
        self.body_buffer.connect("changed", self.on_editor_changed)

        body_scroll = Gtk.ScrolledWindow()
        body_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        body_scroll.set_vexpand(True)
        body_scroll.set_child(self.body_view)

        self.preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.preview_box.add_css_class("md-preview")
        self.preview_box.set_hexpand(True)

        preview_scroll = Gtk.ScrolledWindow()
        preview_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        preview_scroll.set_vexpand(True)
        preview_scroll.set_child(self.preview_box)

        self.editor_stack = Gtk.Stack()
        self.editor_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.editor_stack.set_vexpand(True)
        self.editor_stack.add_named(body_scroll, "edit")
        self.editor_stack.add_named(preview_scroll, "preview")
        self.editor_box.append(self.editor_stack)

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

    def _load_snippets(self) -> None:
        path = snippets_file()
        if path.exists():
            loaded = self._read_store(path)
            if loaded:
                self.snippets = loaded
                return
        legacy = notes_file()
        if legacy.exists():
            loaded = self._read_store(legacy)
            if loaded:
                self.snippets = loaded
                self._write_snippets()
                return
        self.snippets = [normalize_snippet(dict(s)) for s in SAMPLE_SNIPPETS]
        self._write_snippets()

    def _read_store(self, path: Path) -> list[dict]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        items: list | None
        extra_format = "code"
        if isinstance(data, dict):
            items = data.get("snippets") or data.get("notes")
            extra_format = normalize_format(data.get("last_format") or "code")
        elif isinstance(data, list):
            items = data
        else:
            items = None
        if extra_format in FORMATS:
            self._last_format = extra_format
        if not isinstance(items, list) or not items:
            return []
        return [normalize_snippet(item) for item in items if isinstance(item, dict)]

    def _write_snippets(self) -> None:
        path = snippets_file()
        payload = {"snippets": self.snippets, "last_format": self._last_format}
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, path)

    def _find(self, snippet_id: str | None) -> dict | None:
        if not snippet_id:
            return None
        return next((s for s in self.snippets if s["id"] == snippet_id), None)

    def _visible(self) -> list[dict]:
        return [
            s
            for s in sorted(self.snippets, key=lambda n: n.get("updated", ""), reverse=True)
            if matches_query(s, self._filter)
        ]

    def _refresh_list(self, select_id: str | None = None) -> None:
        self._loading = True
        self.listbox.remove_all()

        ordered = self._visible()
        target_row = None
        for snippet in ordered:
            row = self._make_row(snippet)
            self.listbox.append(row)
            if snippet["id"] == select_id:
                target_row = row

        if target_row is not None:
            self.listbox.select_row(target_row)
            self._loading = False
            snippet = self._find(select_id)
            if snippet:
                self._load_snippet_into_editor(snippet)
            return
        if not ordered:
            self._show_empty()
        self._loading = False

    def _make_row(self, snippet: dict) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.snippet_id = snippet["id"]  # type: ignore[attr-defined]

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title = Gtk.Label(label=snippet.get("title") or "Untitled", xalign=0)
        title.add_css_class("snippet-title")
        title.set_ellipsize(Pango.EllipsizeMode.END)
        title.set_hexpand(True)
        title.set_max_width_chars(24)

        lang = Gtk.Label(label=sidebar_kind(snippet), xalign=1)
        lang.add_css_class("snippet-lang")
        lang.add_css_class("dim-label")
        lang.set_ellipsize(Pango.EllipsizeMode.END)

        top.append(title)
        top.append(lang)

        preview = Gtk.Label(label=preview_of(snippet.get("body", "")), xalign=0)
        preview.add_css_class("snippet-preview")
        preview.set_ellipsize(Pango.EllipsizeMode.END)
        preview.set_max_width_chars(34)

        box.append(top)
        box.append(preview)
        row.set_child(box)
        return row

    def _show_empty(self) -> None:
        self.current_id = None
        self.stack.set_visible_child_name("empty")
        self.delete_button.set_sensitive(False)
        self.copy_button.set_sensitive(False)
        if self._filter and self.snippets:
            self.empty_page.set_title("No matching notes")
            self.empty_page.set_description("Try another search, or press Ctrl+N.")
            self.status.set_text("No matches")
        elif not self.snippets:
            self.empty_page.set_title("No notes yet")
            self.empty_page.set_description("Press Ctrl+N to create one.")
            self.status.set_text("No notes yet")
        else:
            self.empty_page.set_title("No note selected")
            self.empty_page.set_description(
                "Choose an item in the sidebar, search, or press Ctrl+N."
            )
            self.status.set_text("Ready")

    def _show_editor(self) -> None:
        self.stack.set_visible_child_name("editor")
        self.delete_button.set_sensitive(True)
        self.copy_button.set_sensitive(True)

    def on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        self._filter = (entry.get_text() or "").strip()
        keep = self.current_id
        visible_ids = {s["id"] for s in self._visible()}
        select = keep if keep in visible_ids else (next(iter(visible_ids), None))
        self._refresh_list(select_id=select)

    def on_find(self, *_args) -> None:
        self.search.grab_focus()

    def on_row_selected(self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        if self._loading:
            return
        if row is None:
            self._show_empty()
            return
        self._flush_pending_save()
        snippet = self._find(getattr(row, "snippet_id", None))
        if not snippet:
            self._show_empty()
            return
        self._load_snippet_into_editor(snippet)

    def _current_format(self) -> str:
        name = self.format_group.get_active_name()
        return name if name in FORMATS else "code"

    def _apply_format_ui(self, fmt: str) -> None:
        fmt = normalize_format(fmt)
        is_code = fmt == "code"
        is_md = fmt == "markdown"
        is_text = fmt == "text"

        self.lang_entry.set_visible(is_code)
        self.view_toggle.set_visible(is_md)

        for kind in FORMATS:
            self.body_view.remove_css_class(f"kind-{kind}")
        self.body_view.add_css_class(f"kind-{fmt}")
        self.body_view.set_monospace(not is_text)
        if is_code:
            self.body_view.set_wrap_mode(Gtk.WrapMode.NONE)
        else:
            self.body_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)

        if not is_md:
            if self.view_toggle.get_active_name() != "edit":
                self.view_toggle.set_active_name("edit")
            self.editor_stack.set_visible_child_name("edit")

    def on_format_changed(self, *_args) -> None:
        fmt = self._current_format()
        self._apply_format_ui(fmt)
        if self._loading or not self.current_id:
            return
        snippet = self._find(self.current_id)
        if not snippet:
            return
        snippet["format"] = fmt
        if fmt == "text" and not (snippet.get("language") or "").strip():
            snippet["language"] = "text"
        elif fmt == "markdown" and not (snippet.get("language") or "").strip():
            snippet["language"] = "markdown"
        self._last_format = fmt
        snippet["updated"] = now_iso()
        self.status.set_text("Saving…")
        if self._save_timeout is not None:
            GLib.source_remove(self._save_timeout)
        self._save_timeout = GLib.timeout_add(350, self._autosave)

    def on_view_changed(self, *_args) -> None:
        if self._current_format() != "markdown":
            self.editor_stack.set_visible_child_name("edit")
            return
        if self.view_toggle.get_active_name() == "preview":
            self._show_preview()
        else:
            self.editor_stack.set_visible_child_name("edit")

    def on_toggle_preview(self, *_args) -> None:
        if self._current_format() != "markdown":
            return
        current = self.view_toggle.get_active_name()
        self.view_toggle.set_active_name("edit" if current == "preview" else "preview")

    def _markup_label(self, markup: str, *css: str) -> Gtk.Label:
        label = Gtk.Label()
        label.set_markup(markup)
        label.set_wrap(True)
        label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        label.set_xalign(0)
        label.set_selectable(True)
        label.set_hexpand(True)
        for name in css:
            label.add_css_class(name)
        return label

    def _show_preview(self) -> None:
        _clear_box(self.preview_box)
        body = self._editor_body()
        if not body.strip():
            empty = Gtk.Label(label="Nothing to preview")
            empty.add_css_class("md-empty")
            empty.add_css_class("dim-label")
            empty.set_xalign(0)
            self.preview_box.append(empty)
            self.editor_stack.set_visible_child_name("preview")
            return

        for block in parse_markdown(body):
            kind = block.get("type")
            if kind == "heading":
                level = max(1, min(int(block.get("level") or 1), 6))
                self.preview_box.append(
                    self._markup_label(
                        inline_to_pango(block.get("text") or ""),
                        f"md-h{level}",
                    )
                )
            elif kind == "paragraph":
                self.preview_box.append(
                    self._markup_label(
                        inline_to_pango(block.get("text") or ""),
                        "md-paragraph",
                    )
                )
            elif kind == "quote":
                self.preview_box.append(
                    self._markup_label(
                        inline_to_pango(block.get("text") or ""),
                        "md-quote",
                    )
                )
            elif kind == "code":
                text = block.get("text") or ""
                code = Gtk.Label(label=text)
                code.set_xalign(0)
                code.set_selectable(True)
                code.set_wrap(True)
                code.set_wrap_mode(Pango.WrapMode.CHAR)
                code.add_css_class("md-codeblock")
                code.set_hexpand(True)
                self.preview_box.append(code)
            elif kind == "hr":
                rule = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
                rule.add_css_class("md-hr")
                self.preview_box.append(rule)
            elif kind in ("ul", "ol"):
                items = block.get("items") or []
                for index, item in enumerate(items, start=1):
                    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                    bullet = Gtk.Label(label=f"{index}." if kind == "ol" else "•")
                    bullet.set_xalign(0)
                    bullet.add_css_class("dim-label")
                    bullet.set_width_chars(2)
                    row.append(bullet)
                    row.append(
                        self._markup_label(inline_to_pango(item), "md-list-item")
                    )
                    self.preview_box.append(row)

        self.editor_stack.set_visible_child_name("preview")

    def _load_snippet_into_editor(self, snippet: dict) -> None:
        self._loading = True
        self.current_id = snippet["id"]
        self.title_entry.set_text(snippet.get("title", ""))
        self.lang_entry.set_text(snippet.get("language", ""))
        self.body_buffer.set_text(snippet.get("body", ""))
        fmt = normalize_format(snippet.get("format"))
        if self.format_group.get_active_name() != fmt:
            self.format_group.set_active_name(fmt)
        self._apply_format_ui(fmt)
        if self.view_toggle.get_active_name() != "edit":
            self.view_toggle.set_active_name("edit")
        self.editor_stack.set_visible_child_name("edit")
        self._last_format = fmt
        self._show_editor()
        self.status.set_text(f"Edited  {format_updated(snippet.get('updated', ''))}")
        self._loading = False

    def on_editor_changed(self, *_args) -> None:
        if self._loading or not self.current_id:
            return
        snippet = self._find(self.current_id)
        if not snippet:
            return
        snippet["title"] = self.title_entry.get_text()
        snippet["language"] = self.lang_entry.get_text().strip()
        snippet["format"] = self._current_format()
        snippet["body"] = self._editor_body()
        snippet["updated"] = now_iso()
        self._last_format = snippet["format"]
        self.status.set_text("Saving…")
        if self._save_timeout is not None:
            GLib.source_remove(self._save_timeout)
        self._save_timeout = GLib.timeout_add(350, self._autosave)

    def _autosave(self) -> bool:
        self._save_timeout = None
        self._write_snippets()
        self._update_selected_row_labels()
        snippet = self._find(self.current_id)
        when = format_updated(snippet["updated"]) if snippet else ""
        self.status.set_text(f"Saved  {when}")
        return False

    def _flush_pending_save(self) -> None:
        if self._save_timeout is not None:
            GLib.source_remove(self._save_timeout)
            self._save_timeout = None
            self._write_snippets()

    def _update_selected_row_labels(self) -> None:
        row = self.listbox.get_selected_row()
        snippet = self._find(self.current_id)
        if row is None or snippet is None:
            return
        box = row.get_child()
        if box is None:
            return
        children = []
        child = box.get_first_child()
        while child is not None:
            children.append(child)
            child = child.get_next_sibling()
        if len(children) < 2:
            return
        top = children[0]
        top_kids = []
        kid = top.get_first_child()
        while kid is not None:
            top_kids.append(kid)
            kid = kid.get_next_sibling()
        if len(top_kids) >= 2:
            top_kids[0].set_text(snippet.get("title") or "Untitled")
            top_kids[1].set_text(sidebar_kind(snippet))
        children[1].set_text(preview_of(snippet.get("body", "")))

    def _editor_body(self) -> str:
        start = self.body_buffer.get_start_iter()
        end = self.body_buffer.get_end_iter()
        return self.body_buffer.get_text(start, end, True)

    def on_copy(self, *_args) -> None:
        if not self.current_id:
            return
        text = self._editor_body()
        display = Gdk.Display.get_default()
        if display is None:
            self.status.set_text("Clipboard unavailable")
            return
        display.get_clipboard().set(text)
        self.status.set_text("Copied")

    def _has_text_selection(self) -> bool:
        widget = self.get_focus()
        if widget is None:
            return False
        if isinstance(widget, Gtk.TextView):
            return widget.get_buffer().get_has_selection()
        if isinstance(widget, Gtk.Editable):
            bounds = widget.get_selection_bounds()
            if not bounds:
                return False
            if isinstance(bounds, tuple) and len(bounds) == 2:
                return bounds[0] != bounds[1]
            return True
        return False

    def _on_key_pressed(self, _controller, keyval, _keycode, state) -> bool:
        ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(state & Gdk.ModifierType.SHIFT_MASK)
        if not ctrl:
            return False
        if keyval not in (Gdk.KEY_c, Gdk.KEY_C):
            return False
        if shift:
            self.on_copy()
            return True
        if self._has_text_selection():
            return False
        self.on_copy()
        return True

    def on_new(self, *_args) -> None:
        self._flush_pending_save()
        if self._filter:
            self._filter = ""
            self.search.set_text("")
        fmt = self._last_format if self._last_format in FORMATS else "code"
        language = ""
        if fmt == "text":
            language = "text"
        elif fmt == "markdown":
            language = "markdown"
        snippet = {
            "id": str(uuid.uuid4()),
            "title": "Untitled",
            "format": fmt,
            "language": language,
            "body": "",
            "updated": now_iso(),
        }
        self.snippets.insert(0, snippet)
        self._write_snippets()
        self._refresh_list(select_id=snippet["id"])
        self.title_entry.grab_focus()
        self.title_entry.select_region(0, -1)
        self.status.set_text("New snippet" if fmt == "code" else "New note")

    def on_delete(self, *_args) -> None:
        if not self.current_id:
            return
        snippet = self._find(self.current_id)
        title = (snippet or {}).get("title") or "Untitled"

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
        self.snippets = [s for s in self.snippets if s["id"] != self.current_id]
        self.current_id = None
        self._write_snippets()
        visible = self._visible()
        next_id = visible[0]["id"] if visible else None
        self._refresh_list(select_id=next_id)
        self.status.set_text("Deleted")

    def _save_screenshot(self) -> bool:
        path = os.environ.get("SNIPPETS_SCREENSHOT") or os.environ.get("NOTES_SCREENSHOT")
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


# SPDX-License-Identifier: MIT
"""Main window for Sheaf — code, plain text, and Markdown notes."""

from __future__ import annotations

import copy
import json
import os
import re
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GtkSource", "5")
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Graphene, Gtk, GtkSource, Pango  # noqa: E402

from markdown import (  # noqa: E402
    FORMATS,
    cap_markdown_source,
    inline_to_pango,
    normalize_format,
    parse_markdown,
    sidebar_kind,
)
from theme import apply_omarchy_palette, load_omarchy_colors  # noqa: E402

APP_ID = "app.sheaf.Sheaf"
# Previous application id — used only to copy snippets.json / notes.json / window.json once.
OLD_APP_ID = "io.github.jitendravyas.Notes"

MAX_NOTE_BODY_BYTES = 1_000_000
MAX_STORE_BYTES = 32 * 1024 * 1024
SEARCH_DEBOUNCE_MS = 150
AUTOSAVE_DEBOUNCE_MS = 400
PREVIEW_DEBOUNCE_MS = 200

CSS = b"""
.sheaf-window {
  --sheaf-bg: @window_bg_color;
  --sheaf-fg: @window_fg_color;
  --sheaf-accent: @accent_bg_color;
  --sheaf-red: @error_color;
  --sheaf-sidebar: @sidebar_bg_color;
}

.title-entry {
  font-size: 22px;
  font-weight: 700;
  background: transparent;
  box-shadow: none;
  min-height: 40px;
  padding-left: 2px;
}

.title-entry:focus,
.title-entry:focus-within {
  box-shadow: inset 0 -2px var(--sheaf-accent, @accent_bg_color);
  background: transparent;
}

.lang-dropdown {
  min-width: 180px;
}

.lang-dropdown > button {
  min-width: 180px;
  padding-left: 12px;
  padding-right: 10px;
}

.snippet-title {
  font-weight: 600;
  font-size: 0.98em;
}

.snippet-lang {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.04em;
  padding: 2px 8px;
  min-height: 18px;
  border-radius: 999px;
  background-color: alpha(var(--sheaf-fg, @window_fg_color), 0.08);
}

.type-badge {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.03em;
  padding: 3px 10px;
  border-radius: 999px;
  background-color: alpha(var(--sheaf-fg, @window_fg_color), 0.08);
}

.snippet-preview {
  font-size: 0.82em;
  color: alpha(var(--sheaf-fg, @window_fg_color), 0.62);
}

.row-action {
  min-width: 22px;
  min-height: 22px;
  padding: 0;
}

/* Only a pinned row shows a pin. Others appear on hover. */
.row-action.pin-off,
.row-action.pin-off image {
  opacity: 0;
}
list.navigation-sidebar > row:hover .row-action.pin-off,
list.navigation-sidebar > row:hover .row-action.pin-off image,
list.navigation-sidebar > row:selected .row-action.pin-off,
list.navigation-sidebar > row:selected .row-action.pin-off image {
  opacity: 0.4;
}
.row-action.pin-on,
.row-action.pin-on image,
button.pin-on {
  opacity: 1;
  color: var(--sheaf-accent, @accent_color);
}

.sidebar-pane {
  background-color: var(--sheaf-sidebar, @sidebar_bg_color);
}

.sidebar-search {
  border-radius: 16px;
  min-height: 36px;
}

.search-wrap {
  padding: 10px 12px 10px 12px;
}

.editor-meta {
  padding: 2px 12px 8px 12px;
}

.view-toggle {
  font-size: 0.9em;
}

list.navigation-sidebar {
  background: transparent;
  padding: 2px 0 10px 0;
}

list.navigation-sidebar > row {
  border-radius: 10px;
  margin: 1px 8px;
  padding: 0;
}

list.navigation-sidebar > row:hover {
  background-color: alpha(var(--sheaf-fg, @window_fg_color), 0.06);
}

list.navigation-sidebar > row:selected {
  background-color: alpha(var(--sheaf-accent, @accent_bg_color), 0.20);
}

list.navigation-sidebar > row:selected:hover {
  background-color: alpha(var(--sheaf-accent, @accent_bg_color), 0.26);
}

list.navigation-sidebar > row:selected .snippet-title {
  font-weight: 700;
}

list.navigation-sidebar > row:selected .snippet-lang {
  background-color: alpha(var(--sheaf-accent, @accent_bg_color), 0.22);
}

textview.snippet-body.kind-code,
textview.snippet-body.kind-code text,
sourceview.snippet-body.kind-code,
sourceview.snippet-body.kind-code text,
textview.snippet-body.kind-markdown,
textview.snippet-body.kind-markdown text {
  font-family: "Source Code Pro", "JetBrains Mono", "Fira Code",
    "Noto Sans Mono", "DejaVu Sans Mono", monospace;
  font-size: 14px;
}

textview.snippet-body.kind-text,
textview.snippet-body.kind-text text {
  font-family: Cantarell, "Noto Sans", "DejaVu Sans", sans-serif;
  font-size: 15px;
}

.md-preview {
  padding: 16px 22px 28px 22px;
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
  font-size: 15px;
}

.md-codeblock {
  font-family: "Source Code Pro", "JetBrains Mono", "Fira Code",
    "Noto Sans Mono", "DejaVu Sans Mono", monospace;
  font-size: 13px;
  background-color: alpha(var(--sheaf-fg, @window_fg_color), 0.06);
  padding: 10px 12px;
  border-radius: 8px;
}

.md-quote {
  color: alpha(var(--sheaf-fg, @window_fg_color), 0.82);
  padding-left: 12px;
  border-left: 3px solid alpha(var(--sheaf-fg, @window_fg_color), 0.28);
}

.md-hr {
  margin-top: 4px;
  margin-bottom: 4px;
}

.md-empty {
  font-style: italic;
  padding: 28px 8px;
}

.chooser-intro {
  font-size: 0.95em;
}

.sidebar-placeholder {
  padding: 28px 16px 20px 16px;
}
"""


def xdg_data_home() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return Path(base).expanduser().resolve()


def _path_under_dir(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def migrate_legacy_data() -> list[str]:
    """Copy snippets.json / notes.json / window.json from the previous app-id data dir.

    On first run after the id change: if the new dir is missing or has no
    snippets.json, and the old dir has snippets.json, notes.json, and/or
    window.json, copy those files into the new dir. notes.json is also
    copied when the new store already exists, as long as dest notes.json
    is missing. The old directory is left as a backup. Both locations
    must stay under XDG_DATA_HOME.
    """
    try:
        root = xdg_data_home()
        new_dir = (root / APP_ID).resolve()
        old_dir = (root / OLD_APP_ID).resolve()
    except OSError:
        return []
    if not _path_under_dir(new_dir, root) or not _path_under_dir(old_dir, root):
        return []
    if not old_dir.is_dir():
        return []

    names = ("snippets.json", "notes.json", "window.json")
    if (new_dir / "snippets.json").is_file():
        names = ("notes.json",)

    copied: list[str] = []
    for name in names:
        try:
            src = (old_dir / name).resolve()
            dest = (new_dir / name).resolve()
        except OSError:
            continue
        if not _path_under_dir(src, old_dir) or not _path_under_dir(dest, new_dir):
            continue
        if not src.is_file() or dest.exists():
            continue
        try:
            new_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            os.chmod(dest, 0o600)
        except OSError:
            continue
        copied.append(name)
    return copied


def data_dir() -> Path:
    migrate_legacy_data()
    root = xdg_data_home()
    directory = (root / APP_ID).resolve()
    if not _path_under_dir(directory, root):
        raise ValueError("data dir escapes XDG data home")
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def safe_store_path(filename: str) -> Path:
    """Resolve a data-file name and reject anything that escapes the XDG dir."""
    if filename != Path(filename).name or filename in ("", ".", ".."):
        raise ValueError("store path escapes data directory")
    root = data_dir()
    path = (root / filename).resolve()
    if not _path_under_dir(path, root):
        raise ValueError("store path escapes data directory")
    return path


def snippets_file() -> Path:
    return safe_store_path("snippets.json")


def notes_file() -> Path:
    """Previous app filename — migrated on first launch if present."""
    return safe_store_path("notes.json")


DEFAULT_WINDOW_WIDTH = 1040
DEFAULT_WINDOW_HEIGHT = 700
MIN_WINDOW_WIDTH = 480
MIN_WINDOW_HEIGHT = 360
MAX_WINDOW_EDGE = 16384


def window_file() -> Path:
    return safe_store_path("window.json")


def clamp_window_size(width: object, height: object) -> tuple[int, int]:
    """Coerce a size to integers and clamp to a sane range."""
    try:
        w = int(width)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        w = DEFAULT_WINDOW_WIDTH
    try:
        h = int(height)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        h = DEFAULT_WINDOW_HEIGHT
    w = max(MIN_WINDOW_WIDTH, min(w, MAX_WINDOW_EDGE))
    h = max(MIN_WINDOW_HEIGHT, min(h, MAX_WINDOW_EDGE))
    return w, h


def parse_window_state(data: object) -> dict:
    """Extract width, height, and maximized from a window.json payload."""
    if not isinstance(data, dict):
        return {
            "width": DEFAULT_WINDOW_WIDTH,
            "height": DEFAULT_WINDOW_HEIGHT,
            "maximized": False,
        }
    width, height = clamp_window_size(data.get("width"), data.get("height"))
    return {
        "width": width,
        "height": height,
        "maximized": data.get("maximized") is True,
    }


def load_window_state_text(text: str) -> dict:
    try:
        data = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return parse_window_state(None)
    return parse_window_state(data)


def load_window_state(path: Path | None = None) -> dict:
    defaults = parse_window_state(None)
    try:
        target = path if path is not None else window_file()
        resolved = target.resolve()
        if not _path_under_dir(resolved, data_dir()):
            return defaults
        if not resolved.is_file() or resolved.stat().st_size > 65536:
            return defaults
        return load_window_state_text(resolved.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defaults


def window_state_payload(
    width: object, height: object, maximized: object = False
) -> dict:
    w, h = clamp_window_size(width, height)
    return {"width": w, "height": h, "maximized": maximized is True}


def save_window_state(
    width: object,
    height: object,
    maximized: object = False,
    path: Path | None = None,
) -> None:
    target = path if path is not None else window_file()
    atomic_write_json(target, window_state_payload(width, height, maximized))


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


def _coerce_text(value: object, default: str = "") -> str:
    if value is None or isinstance(value, (dict, list)):
        return default
    return str(value)


def _coerce_pinned(value: object) -> bool:
    """True, JSON true, 1, or the string true count as pinned."""
    if value is True:
        return True
    if value == 1 and not isinstance(value, bool):
        return True
    if isinstance(value, str) and value.strip().casefold() == "true":
        return True
    return False


def normalize_snippet(raw: object) -> dict | None:
    """Coerce a mapping into a snippet, or None if the item is garbage."""
    if not isinstance(raw, dict):
        return None
    expected = {"id", "title", "format", "kind", "language", "body", "updated", "pinned"}
    if not expected.intersection(raw.keys()):
        return None
    body_raw = raw.get("body")
    if isinstance(body_raw, (list, dict)):
        return None
    body = _coerce_text(body_raw)
    encoded = body.encode("utf-8")
    if len(encoded) > MAX_NOTE_BODY_BYTES:
        body = encoded[:MAX_NOTE_BODY_BYTES].decode("utf-8", errors="ignore")
    fmt = normalize_format(raw.get("format") or raw.get("kind"))
    language = _coerce_text(raw.get("language"))
    if fmt == "text" and not language:
        language = "text"
    if fmt == "markdown" and not language:
        language = "markdown"
    return {
        "id": _coerce_text(raw.get("id")) or str(uuid.uuid4()),
        "title": _coerce_text(raw.get("title")),
        "format": fmt,
        "language": language,
        "body": body,
        "updated": _coerce_text(raw.get("updated")) or now_iso(),
        "pinned": _coerce_pinned(raw.get("pinned")),
    }


def parse_store_payload(data: object) -> tuple[list[dict], str | None]:
    """Validate JSON store shape; skip garbage items. Never eval/pickle."""
    last_format: str | None = None
    if isinstance(data, dict):
        items = data.get("snippets")
        if items is None:
            items = data.get("notes")
        extra = data.get("last_format")
        if extra is not None:
            last_format = normalize_format(extra)
    elif isinstance(data, list):
        items = data
    else:
        return [], None
    if not isinstance(items, list):
        return [], last_format
    out: list[dict] = []
    for item in items:
        snippet = normalize_snippet(item)
        if snippet is not None:
            out.append(snippet)
    return out, last_format


def load_store_text(text: str) -> list[dict]:
    try:
        data = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return []
    items, _last = parse_store_payload(data)
    return items


def choose_initial_snippets(
    store_exists: bool,
    store_items: list[dict],
    store_ok: bool,
    legacy_exists: bool,
    legacy_items: list[dict],
    legacy_ok: bool,
) -> tuple[list[dict], bool]:
    """Decide (snippets, should_write) when opening the store.

    An existing snippets.json is authoritative: a parsed empty list stays
    empty, and a corrupt/unreadable/oversize file starts as [] without
    rewriting the bad file. notes.json is only used when snippets.json
    is missing. First run with no usable store writes an empty list.
    """
    if store_exists:
        if store_ok:
            return list(store_items), False
        return [], False
    if legacy_exists and legacy_ok and legacy_items:
        return list(legacy_items), True
    return [], True


def atomic_write_json(path: Path, payload: object) -> None:
    """Write JSON via a same-directory temp file, then os.replace. Mode 0o600."""
    root = data_dir()
    resolved = path.resolve()
    if not _path_under_dir(resolved, root):
        raise ValueError("store path escapes data directory")
    tmp = resolved.with_name(resolved.name + ".tmp")
    if not _path_under_dir(tmp, root):
        raise ValueError("temp path escapes data directory")
    blob = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(blob)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
    os.replace(tmp, resolved)
    os.chmod(resolved, 0o600)


PLAIN_LANGUAGE_IDS = frozenset(("", "plain", "text", "plaintext", "plain-text", "none"))

LANGUAGE_ALIASES = {
    "python": "python3",
    "py": "python3",
    "python2": "python",
    "bash": "sh",
    "shell": "sh",
    "zsh": "sh",
    "ksh": "sh",
    "dash": "sh",
    "javascript": "js",
    "node": "js",
    "nodejs": "js",
}

SHEBANG_HINTS = (
    ("python3", "python3"),
    ("python2", "python"),
    ("pypy", "python3"),
    ("python", "python3"),
    ("nodejs", "js"),
    ("node", "js"),
    ("ruby", "ruby"),
    ("perl", "perl"),
    ("php", "php"),
    ("lua", "lua"),
    ("awk", "awk"),
    ("fish", "fish"),
    ("bash", "sh"),
    ("zsh", "sh"),
    ("dash", "sh"),
)

EXT_HINTS = {
    ".py": "python3",
    ".py3": "python3",
    ".pyi": "python3",
    ".sh": "sh",
    ".bash": "sh",
    ".zsh": "sh",
    ".js": "js",
    ".mjs": "js",
    ".ts": "typescript",
    ".tsx": "typescript-jsx",
    ".jsx": "jsx",
    ".json": "json",
    ".rs": "rust",
    ".go": "go",
    ".rb": "ruby",
    ".c": "c",
    ".h": "chdr",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".hpp": "cpphdr",
    ".java": "java",
    ".kt": "kotlin",
    ".swift": "swift",
    ".md": "markdown",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".toml": "toml",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".xml": "xml",
    ".sql": "sql",
    ".lua": "lua",
    ".php": "php",
    ".zig": "zig",
}

_PATH_EXT = re.compile(r"(?:^|[\s'\"`=(])(?:[~.]?/?[\w./-]+?)(\.[A-Za-z0-9]+)\b")

SKIP_LANG_IDS = frozenset({"def", "testv1"})

SHORT_PASTE = 80


_LANGUAGE_MANAGER: GtkSource.LanguageManager | None = None
_PICKER_LANGUAGES: list[tuple[str, str]] | None = None


def language_manager() -> GtkSource.LanguageManager:
    global _LANGUAGE_MANAGER
    if _LANGUAGE_MANAGER is None:
        _LANGUAGE_MANAGER = GtkSource.LanguageManager.get_default()
    return _LANGUAGE_MANAGER


def list_picker_languages() -> list[tuple[str, str]]:
    global _PICKER_LANGUAGES
    if _PICKER_LANGUAGES is not None:
        return _PICKER_LANGUAGES
    manager = language_manager()
    items: list[tuple[str, str]] = []
    for lang_id in manager.get_language_ids() or []:
        if lang_id in SKIP_LANG_IDS:
            continue
        lang = manager.get_language(lang_id)
        if lang is None or lang.get_hidden():
            continue
        items.append((lang_id, lang.get_name()))
    items.sort(key=lambda item: item[1].casefold())
    _PICKER_LANGUAGES = items
    return items


def resolve_language_id(value: str) -> str:
    raw = (value or "").strip()
    if not raw or raw.casefold() in PLAIN_LANGUAGE_IDS:
        return ""
    manager = language_manager()
    alias = LANGUAGE_ALIASES.get(raw.casefold())
    if alias and manager.get_language(alias) is not None:
        return alias
    if manager.get_language(raw) is not None:
        return raw
    folded = raw.casefold()
    for lang_id in manager.get_language_ids() or []:
        lang = manager.get_language(lang_id)
        if lang is None:
            continue
        if lang_id.casefold() == folded or lang.get_name().casefold() == folded:
            return lang_id
    return raw


def guess_from_shebang(text: str) -> str:
    first = (text or "").lstrip("\ufeff").split("\n", 1)[0].strip()
    if not first.startswith("#!"):
        return ""
    lower = first.lower()
    for needle, lang_id in SHEBANG_HINTS:
        if needle in lower:
            return lang_id
    if lower.endswith("/sh") or lower.endswith(" env sh") or lower.rstrip().endswith(" sh"):
        return "sh"
    return ""


def guess_from_filename_hint(text: str) -> str:
    head = "\n".join((text or "").split("\n", 5)[:5])
    for match in _PATH_EXT.finditer(head):
        ext = match.group(1).lower()
        if ext in EXT_HINTS:
            return EXT_HINTS[ext]
    return ""


_PY_DEF = re.compile(r"(?m)^\s*(async\s+)?def\s+\w+\s*\(")
_PY_CLASS = re.compile(r"(?m)^\s*class\s+\w+")
_PY_FROM = re.compile(r"(?m)^\s*from\s+[\w.]+\s+import\b")
_PY_IMPORT = re.compile(r"(?m)^\s*import\s+[\w.]+")
_PY_MAIN = re.compile(r"""if\s+__name__\s*==\s*['"]__main__['"]""")
_JS_FUNCTION = re.compile(r"(?m)^\s*(export\s+)?(async\s+)?function\b|\bfunction\s*\(")
_JS_CONST = re.compile(r"(?m)^\s*(const|let|var)\s+\w+")
_JS_ARROW = re.compile(r"=>")
_JS_CONSOLE = re.compile(r"\bconsole\.(log|error|warn|info|debug)\s*\(")
_JS_IMPORT_FROM = re.compile(r"(?m)^\s*import\s+.+\s+from\s+")
_JS_EXPORT = re.compile(r"(?m)^\s*export\s+(default\s+)?")
_GO_SIG = re.compile(r"(?m)^(package\s+\w+|func\s+\w+\s*\()")
_RS_SIG = re.compile(r"(?m)^\s*(pub\s+)?(async\s+)?fn\s+\w+|^\s*use\s+[\w:]+")
_HTML_SIG = re.compile(r"(?is)^\s*(<!DOCTYPE\s+html|<html\b|<head\b|<body\b|<div\b|<span\b|<p\b|<section\b)")
_CSS_SIG = re.compile(r"(?m)^\s*([.#]?[\w-]+|body|html|\*)\s*\{[^}]*[\w-]+\s*:")


def guess_from_heuristics(text: str) -> str:
    """Match common code shapes that have no shebang or filename."""
    sample = (text or "").lstrip("\ufeff")
    stripped = sample.strip()
    if not stripped:
        return ""
    if stripped[0] in "{[":
        try:
            json.loads(stripped)
            return "json"
        except json.JSONDecodeError:
            head = stripped[:80]
            if ":" in head or '"' in head[:40]:
                return "json"
    if _HTML_SIG.match(stripped):
        return "html"
    if _CSS_SIG.search(sample):
        return "css"
    if _JS_IMPORT_FROM.search(sample) or _JS_CONSOLE.search(sample):
        return "js"
    if _JS_FUNCTION.search(sample) or _JS_CONST.search(sample) or _JS_EXPORT.search(sample):
        return "js"
    if _JS_ARROW.search(sample) and ("(" in sample or _JS_CONST.search(sample)):
        return "js"
    if _PY_DEF.search(sample) or _PY_CLASS.search(sample) or _PY_FROM.search(sample) or _PY_MAIN.search(sample):
        return "python3"
    if _PY_IMPORT.search(sample):
        return "python3"
    if _GO_SIG.search(sample):
        return "go"
    if _RS_SIG.search(sample):
        return "rust"
    if _looks_like_shell(sample):
        return "sh"
    return ""

_SHELL_FIRST = frozenset((
    "echo", "export", "cd", "ls", "mkdir", "source", "set",
    "pacman", "apt", "apt-get", "dnf", "yum", "brew",
    "systemctl", "git", "rsync", "ssh", "omarchy", "makepkg",
    "for", "while", "if", "then", "fi", "done", "esac",
))


def _looks_like_shell(sample: str) -> bool:
    hits = 0
    for raw in sample.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("sudo "):
            line = line[5:].lstrip()
            hits += 1
        token = line.split(" ", 1)[0]
        token = token.split("=", 1)[0]
        if token in _SHELL_FIRST:
            hits += 1
        elif line.startswith("if ["):
            hits += 1
    return hits >= 1


def _known_language(manager: GtkSource.LanguageManager, lang_id: str) -> str:
    if lang_id and manager.get_language(lang_id) is not None:
        return lang_id
    return ""


def detect_language(pasted: str, content: str) -> str:
    """Guess a GtkSource language id from paste and/or the full buffer.

    Prefer shebang/filename, then content heuristics, then Gio/GtkSource.
    """
    manager = language_manager()
    samples = [sample for sample in (pasted, content) if sample and sample.strip()]

    for sample in samples:
        hinted = guess_from_shebang(sample) or guess_from_filename_hint(sample)
        found = _known_language(manager, hinted)
        if found:
            return found

    for sample in samples:
        found = _known_language(manager, guess_from_heuristics(sample))
        if found:
            return found

    for sample in samples:
        data = sample.encode("utf-8", errors="replace")
        content_type, _uncertain = Gio.content_type_guess(None, data)
        if not content_type or content_type in ("text/plain", "application/octet-stream"):
            continue
        lang = manager.guess_language(None, content_type)
        if lang is not None and lang.get_id() not in SKIP_LANG_IDS:
            return lang.get_id()

    for sample in samples:
        match = _PATH_EXT.search(sample.split("\n", 1)[0])
        if not match:
            continue
        fake_name = "snippet" + match.group(1).lower()
        lang = manager.guess_language(fake_name, None)
        if lang is not None and lang.get_id() not in SKIP_LANG_IDS:
            return lang.get_id()
    return ""


def should_autodetect(current_language: str, pasted: str) -> bool:
    """Keep a user-picked language when the paste is only a short scrap."""
    has_choice = bool(resolve_language_id(current_language))
    short = len(pasted) < SHORT_PASTE
    if has_choice and short:
        return False
    return True


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


def sort_visible(items: list[dict], query: str) -> list[dict]:
    """Pinned matches first, then unpinned; each group newest-first.

    Missing or falsey ``pinned`` is treated as unpinned. Search still filters.
    Equivalent to sorting by ``(-1 if pinned else 0, updated desc)``.
    """
    matched = [item for item in items if matches_query(item, query)]
    return sorted(
        matched,
        key=lambda item: (
            bool(item.get("pinned")),
            item.get("updated") or "",
        ),
        reverse=True,
    )


def restore_at_index(items: list, item: dict, index: int) -> int:
    """Insert item at index, clamping to [0, len(items)]. Returns the index used."""
    idx = max(0, min(int(index), len(items)))
    items.insert(idx, item)
    return idx


def _clear_box(box: Gtk.Box) -> None:
    child = box.get_first_child()
    while child is not None:
        nxt = child.get_next_sibling()
        box.remove(child)
        child = nxt


class SheafWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs) -> None:
        super().__init__(title="Sheaf", **kwargs)
        geometry = load_window_state()
        self.set_default_size(geometry["width"], geometry["height"])
        if geometry["maximized"]:
            self.maximize()
        self.set_icon_name(APP_ID)
        self.connect("close-request", self._on_close_request)

        self.snippets: list[dict] = []
        self.current_id: str | None = None
        self._loading = False
        self._save_timeout: int | None = None
        self._search_timeout: int | None = None
        self._preview_timeout: int | None = None
        self._filter = ""
        self._last_format = "code"
        self._new_chooser_dialog = None
        self._pending_undos: dict[int, dict] = {}

        self._add_icon_search_path()
        self.add_css_class("sheaf-window")
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

        self._refresh_list(select_id=select_id)

        if screenshot:
            if os.environ.get("NOTES_SCREENSHOT_DIALOG"):
                GLib.timeout_add(350, self._open_chooser_for_shot)
                GLib.timeout_add(1900, self._save_screenshot)
            else:
                GLib.timeout_add(200, self._prepare_screenshot)
                GLib.timeout_add(1800, self._save_screenshot)

    def _prepare_screenshot(self) -> bool:
        if self.view_toggle.get_active_name() != "edit":
            self.view_toggle.set_active_name("edit")
        if self._current_format() == "code":
            self.editor_stack.set_visible_child_name("code")
            self.source_view.grab_focus()
        return False

    def _open_chooser_for_shot(self) -> bool:
        self._show_new_chooser()
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
        # None → keep Adwaita / system colors via var(--sheaf-*, @adwaita) fallbacks.
        apply_omarchy_palette(self, load_omarchy_colors())

    def _add_actions(self) -> None:
        new_action = Gio.SimpleAction.new("new-snippet", None)
        new_action.connect("activate", self.on_new)
        self.add_action(new_action)

        delete_action = Gio.SimpleAction.new("delete-snippet", None)
        delete_action.connect("activate", self.on_delete)
        self.add_action(delete_action)
        self.delete_action = delete_action
        self.delete_action.set_enabled(False)

        copy_action = Gio.SimpleAction.new("copy-snippet", None)
        copy_action.connect("activate", self.on_copy)
        self.add_action(copy_action)

        pin_action = Gio.SimpleAction.new("pin-snippet", None)
        pin_action.connect("activate", self.on_pin)
        self.add_action(pin_action)

        find_action = Gio.SimpleAction.new("find", None)
        find_action.connect("activate", self.on_find)
        self.add_action(find_action)

        preview_action = Gio.SimpleAction.new("toggle-preview", None)
        preview_action.connect("activate", self.on_toggle_preview)
        self.add_action(preview_action)

        shortcuts_action = Gio.SimpleAction.new("show-shortcuts", None)
        shortcuts_action.connect("activate", self.on_show_shortcuts)
        self.add_action(shortcuts_action)

        sidebar_action = Gio.SimpleAction.new("toggle-sidebar", None)
        sidebar_action.connect("activate", self.on_toggle_sidebar)
        self.add_action(sidebar_action)

        close_action = Gio.SimpleAction.new("close", None)
        close_action.connect("activate", self.on_close_window)
        self.add_action(close_action)

        undo_action = Gio.SimpleAction.new("undo-delete", None)
        undo_action.connect("activate", self.on_undo_delete)
        self.add_action(undo_action)
        self.undo_delete_action = undo_action
        self.undo_delete_action.set_enabled(False)

        app = self.get_application()
        if app is not None:
            app.set_accels_for_action("win.new-snippet", ["<Control>n"])
            app.set_accels_for_action("win.delete-snippet", ["<Control>Delete"])
            app.set_accels_for_action("win.copy-snippet", ["<Control><Shift>c"])
            app.set_accels_for_action("win.pin-snippet", ["<Control><Shift>p"])
            app.set_accels_for_action("win.find", ["<Control>f", "<Control>k"])
            app.set_accels_for_action("win.toggle-preview", ["<Control>p"])
            app.set_accels_for_action("win.show-shortcuts", ["<Control>question", "<Control>F1"])
            app.set_accels_for_action("win.toggle-sidebar", ["F9"])
            app.set_accels_for_action("win.close", ["<Control>w"])

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
        header.set_title_widget(Adw.WindowTitle(title="Sheaf"))
        toolbar.add_top_bar(header)

        sidebar_btn = Gtk.ToggleButton()
        sidebar_btn.set_icon_name("sidebar-show-symbolic")
        sidebar_btn.set_tooltip_text("Notes list (F9)")
        sidebar_btn.set_valign(Gtk.Align.CENTER)
        header.pack_start(sidebar_btn)
        self.sidebar_toggle = sidebar_btn

        new_btn = Gtk.Button()
        new_btn.set_child(Adw.ButtonContent(icon_name="list-add-symbolic", label="New"))
        new_btn.add_css_class("suggested-action")
        new_btn.set_tooltip_text("Create a note — pick a type  (Ctrl+N)")
        new_btn.connect("clicked", self.on_new)
        header.pack_start(new_btn)

        menu = Gio.Menu()
        shortcuts_section = Gio.Menu()
        shortcuts_section.append("_Keyboard Shortcuts", "win.show-shortcuts")
        menu.append_section(None, shortcuts_section)
        delete_section = Gio.Menu()
        delete_section.append("_Delete Note", "win.delete-snippet")
        menu.append_section(None, delete_section)
        app_section = Gio.Menu()
        app_section.append("_About Sheaf", "app.about")
        app_section.append("_Quit", "app.quit")
        menu.append_section(None, app_section)
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu)
        menu_btn.set_tooltip_text("Menu  (F10)")
        header.pack_end(menu_btn)

        split = Adw.OverlaySplitView()
        split.set_sidebar_width_fraction(0.32)
        split.set_min_sidebar_width(260)
        split.set_max_sidebar_width(400)
        split.set_show_sidebar(True)
        self.split = split
        split.bind_property(
            "show-sidebar",
            sidebar_btn,
            "active",
            GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
        )
        split.bind_property(
            "collapsed",
            sidebar_btn,
            "visible",
            GObject.BindingFlags.SYNC_CREATE,
        )
        breakpoint = Adw.Breakpoint.new(
            Adw.BreakpointCondition.parse("max-width: 720sp")
        )
        breakpoint.add_setter(split, "collapsed", True)
        self.add_breakpoint(breakpoint)

        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text("Search notes")
        self.search.set_hexpand(True)
        self.search.add_css_class("sidebar-search")
        self.search.set_tooltip_text("Search title, language, or body  (Ctrl+F)")
        self.search.connect("search-changed", self.on_search_changed)

        search_wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        search_wrap.add_css_class("search-wrap")
        search_wrap.append(self.search)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.add_css_class("navigation-sidebar")
        self.listbox.connect("row-selected", self.on_row_selected)

        placeholder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        placeholder.add_css_class("sidebar-placeholder")
        placeholder.set_halign(Gtk.Align.CENTER)
        ph_icon = Gtk.Image.new_from_icon_name("edit-find-symbolic")
        ph_icon.set_pixel_size(28)
        ph_icon.add_css_class("dim-label")
        self._placeholder_title = Gtk.Label(label="No notes yet")
        self._placeholder_title.add_css_class("dim-label")
        self._placeholder_title.add_css_class("title-4")
        self._placeholder_title.set_use_markup(False)
        self._placeholder_hint = Gtk.Label(label="Press Ctrl+N")
        self._placeholder_hint.add_css_class("dim-label")
        self._placeholder_hint.add_css_class("caption")
        self._placeholder_hint.set_use_markup(False)
        placeholder.append(ph_icon)
        placeholder.append(self._placeholder_title)
        placeholder.append(self._placeholder_hint)
        self.listbox.set_placeholder(placeholder)

        side_scroll = Gtk.ScrolledWindow()
        side_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        side_scroll.set_vexpand(True)
        side_scroll.set_child(self.listbox)

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar.add_css_class("sidebar-pane")
        sidebar.append(search_wrap)
        sidebar.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        sidebar.append(side_scroll)
        sidebar.set_size_request(260, -1)
        split.set_sidebar(sidebar)

        self.empty_page = Adw.StatusPage(
            icon_name=APP_ID,
            title="No notes yet",
            description="New note, or press Ctrl+N.",
        )
        empty_new = Gtk.Button()
        empty_new.set_child(Adw.ButtonContent(icon_name="list-add-symbolic", label="New note"))
        empty_new.add_css_class("suggested-action")
        empty_new.add_css_class("pill")
        empty_new.set_halign(Gtk.Align.CENTER)
        empty_new.connect("clicked", self.on_new)
        self.empty_page.set_child(empty_new)

        self.editor_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title_row.set_margin_start(14)
        title_row.set_margin_end(14)
        title_row.set_margin_top(14)
        title_row.set_margin_bottom(2)

        self.title_entry = Gtk.Entry()
        self.title_entry.set_placeholder_text("Title")
        self.title_entry.add_css_class("title-entry")
        self.title_entry.set_hexpand(True)
        self.title_entry.connect("changed", self.on_editor_changed)
        title_row.append(self.title_entry)

        self._lang_ids = [""]
        self._lang_model = Gtk.StringList.new(["Plain"])
        for lang_id, lang_name in list_picker_languages():
            self._lang_ids.append(lang_id)
            self._lang_model.append(lang_name)
        self.lang_dropdown = Gtk.DropDown(model=self._lang_model)
        self.lang_dropdown.set_enable_search(True)
        self.lang_dropdown.add_css_class("lang-dropdown")
        self.lang_dropdown.set_valign(Gtk.Align.CENTER)
        self.lang_dropdown.set_size_request(180, -1)
        self.lang_dropdown.set_tooltip_text("Language for syntax highlighting")
        self.lang_dropdown.connect("notify::selected", self.on_language_changed)
        self.editor_box.append(title_row)

        format_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        format_row.add_css_class("editor-meta")
        format_row.set_hexpand(True)
        self.format_row = format_row

        format_row.append(self.lang_dropdown)

        self.format_badge = Gtk.Label(label="code")
        self.format_badge.add_css_class("type-badge")
        self.format_badge.set_use_markup(False)
        self.format_badge.set_tooltip_text("Type is locked")
        self.format_badge.set_valign(Gtk.Align.CENTER)
        format_row.append(self.format_badge)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        format_row.append(spacer)

        self.view_toggle = Adw.ToggleGroup()
        self.view_toggle.set_can_shrink(True)
        self.view_toggle.add_css_class("view-toggle")
        self.view_toggle.add(self._make_toggle("edit", "Edit"))
        self.view_toggle.add(self._make_toggle("preview", "Preview"))
        self.view_toggle.set_active_name("edit")
        self.view_toggle.set_valign(Gtk.Align.CENTER)
        self.view_toggle.set_halign(Gtk.Align.END)
        self.view_toggle.set_tooltip_text("Toggle Markdown preview  (Ctrl+P)")
        self.view_toggle.connect("notify::active-name", self.on_view_changed)
        format_row.append(self.view_toggle)
        self.editor_box.append(format_row)

        self.body_view = Gtk.TextView()
        self.body_view.add_css_class("snippet-body")
        self.body_view.add_css_class("kind-text")
        self.body_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.body_view.set_monospace(False)
        self.body_view.set_left_margin(18)
        self.body_view.set_right_margin(18)
        self.body_view.set_top_margin(12)
        self.body_view.set_bottom_margin(18)
        self.body_view.set_accepts_tab(True)
        self.body_view.set_vexpand(True)
        self.body_buffer = self.body_view.get_buffer()
        self.body_buffer.connect("changed", self.on_editor_changed)

        body_scroll = Gtk.ScrolledWindow()
        body_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        body_scroll.set_vexpand(True)
        body_scroll.set_child(self.body_view)

        self.source_buffer = GtkSource.Buffer()
        self.source_buffer.set_highlight_syntax(True)
        self.source_buffer.connect("changed", self.on_editor_changed)
        self.source_buffer.connect("insert-text", self._on_source_insert_text)

        self.source_view = GtkSource.View(buffer=self.source_buffer)
        self.source_view.add_css_class("snippet-body")
        self.source_view.add_css_class("kind-code")
        self.source_view.set_wrap_mode(Gtk.WrapMode.NONE)
        self.source_view.set_monospace(True)
        self.source_view.set_left_margin(18)
        self.source_view.set_right_margin(18)
        self.source_view.set_top_margin(12)
        self.source_view.set_bottom_margin(18)
        self.source_view.set_accepts_tab(True)
        self.source_view.set_vexpand(True)
        self.source_view.set_show_line_numbers(True)
        self.source_view.set_show_right_margin(False)
        self.source_view.set_highlight_current_line(True)
        self.source_view.set_tab_width(4)
        self.source_view.set_insert_spaces_instead_of_tabs(True)
        self.source_view.set_auto_indent(True)
        self.source_view.set_pixels_above_lines(2)
        self.source_view.set_pixels_below_lines(1)
        self._sync_source_scheme()
        Adw.StyleManager.get_default().connect(
            "notify::dark", lambda *_args: self._sync_source_scheme()
        )

        source_scroll = Gtk.ScrolledWindow()
        source_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        source_scroll.set_vexpand(True)
        source_scroll.set_child(self.source_view)

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
        self.editor_stack.add_named(source_scroll, "code")
        self.editor_stack.add_named(preview_scroll, "preview")
        self.editor_box.append(self.editor_stack)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.NONE)
        self.stack.add_named(self.empty_page, "empty")
        self.stack.add_named(self.editor_box, "editor")
        split.set_content(self.stack)

        overlay = Adw.ToastOverlay()
        overlay.set_child(split)
        self.toast_overlay = overlay
        toolbar.set_content(overlay)

    def _load_snippets(self) -> None:
        path = snippets_file()
        store_exists = path.exists()
        store_items: list[dict] = []
        store_ok = False
        if store_exists:
            store_items, store_ok = self._read_store(path)

        legacy_exists = False
        legacy_items: list[dict] = []
        legacy_ok = False
        if not store_exists:
            legacy = notes_file()
            legacy_exists = legacy.exists()
            if legacy_exists:
                legacy_items, legacy_ok = self._read_store(legacy)

        self.snippets, should_write = choose_initial_snippets(
            store_exists,
            store_items,
            store_ok,
            legacy_exists,
            legacy_items,
            legacy_ok,
        )
        if should_write:
            self._write_snippets()

    def _read_store(self, path: Path) -> tuple[list[dict], bool]:
        try:
            resolved = path.resolve()
            if not _path_under_dir(resolved, data_dir()):
                return [], False
            if resolved.stat().st_size > MAX_STORE_BYTES:
                return [], False
            data = json.loads(resolved.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            return [], False
        items, extra_format = parse_store_payload(data)
        if extra_format in FORMATS:
            self._last_format = extra_format
        return items, True

    def _write_snippets(self) -> None:
        path = snippets_file()
        payload = {"snippets": self.snippets, "last_format": self._last_format}
        atomic_write_json(path, payload)

    def _find(self, snippet_id: str | None) -> dict | None:
        if not snippet_id:
            return None
        return next((s for s in self.snippets if s["id"] == snippet_id), None)

    def _visible(self) -> list[dict]:
        return sort_visible(self.snippets, self._filter)

    def _row_ids(self) -> list[str]:
        ids: list[str] = []
        index = 0
        while True:
            row = self.listbox.get_row_at_index(index)
            if row is None:
                break
            ids.append(getattr(row, "snippet_id", "") or "")
            index += 1
        return ids

    def _sync_existing_rows(self, ordered: list[dict]) -> bool:
        """Update labels in place when membership and order are unchanged."""
        if self._row_ids() != [snippet["id"] for snippet in ordered]:
            return False
        index = 0
        for snippet in ordered:
            row = self.listbox.get_row_at_index(index)
            if row is None:
                return False
            self._update_row_from_snippet(row, snippet)
            index += 1
        return True

    def _refresh_list(self, select_id: str | None = None) -> None:
        ordered = self._visible()
        incremental = self._sync_existing_rows(ordered)
        target_row = None
        if incremental:
            index = 0
            while True:
                row = self.listbox.get_row_at_index(index)
                if row is None:
                    break
                if getattr(row, "snippet_id", None) == select_id:
                    target_row = row
                    break
                index += 1
        else:
            self._loading = True
            self.listbox.remove_all()
            for snippet in ordered:
                row = self._make_row(snippet)
                self.listbox.append(row)
                if snippet["id"] == select_id:
                    target_row = row

        if target_row is not None:
            same = select_id is not None and select_id == self.current_id
            self._loading = True
            self.listbox.select_row(target_row)
            self._loading = False
            snippet = self._find(select_id)
            if snippet and not same:
                self._load_snippet_into_editor(snippet)
            return
        if not ordered:
            self._show_empty()
        self._loading = False

    def _make_row(self, snippet: dict) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.snippet_id = snippet["id"]  # type: ignore[attr-defined]
        snippet_id = snippet["id"]
        pinned = bool(snippet.get("pinned"))

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        pin_btn = Gtk.Button()
        pin_btn.add_css_class("flat")
        pin_btn.add_css_class("row-action")
        pin_btn.set_valign(Gtk.Align.CENTER)
        pin_btn.set_can_focus(False)
        self._apply_pin_style(pin_btn, pinned)
        pin_btn.connect("clicked", self._on_row_pin, snippet_id)
        self._isolate_row_button(pin_btn)

        title = Gtk.Label(label=snippet.get("title") or "Untitled", xalign=0)
        title.add_css_class("snippet-title")
        title.set_use_markup(False)
        title.set_ellipsize(Pango.EllipsizeMode.END)
        title.set_hexpand(True)
        title.set_max_width_chars(20)

        lang = Gtk.Label(label=sidebar_kind(snippet), xalign=1)
        lang.add_css_class("snippet-lang")
        lang.add_css_class("dim-label")
        lang.set_use_markup(False)
        lang.set_ellipsize(Pango.EllipsizeMode.END)
        lang.set_valign(Gtk.Align.CENTER)

        copy_btn = Gtk.Button()
        copy_btn.set_icon_name("edit-copy-symbolic")
        copy_btn.add_css_class("flat")
        copy_btn.add_css_class("row-action")
        copy_btn.set_valign(Gtk.Align.CENTER)
        copy_btn.set_can_focus(False)
        copy_btn.set_tooltip_text("Copy body")
        copy_btn.connect("clicked", self._on_row_copy, snippet_id)
        self._isolate_row_button(copy_btn)

        top.append(pin_btn)
        top.append(title)
        top.append(lang)
        top.append(copy_btn)

        preview = Gtk.Label(label=preview_of(snippet.get("body", "")), xalign=0)
        preview.add_css_class("snippet-preview")
        preview.set_use_markup(False)
        preview.set_ellipsize(Pango.EllipsizeMode.END)
        preview.set_max_width_chars(34)
        preview.set_margin_start(28)

        box.append(top)
        box.append(preview)
        row.set_child(box)
        row.title_label = title  # type: ignore[attr-defined]
        row.lang_label = lang  # type: ignore[attr-defined]
        row.preview_label = preview  # type: ignore[attr-defined]
        row.pin_button = pin_btn  # type: ignore[attr-defined]
        motion = Gtk.EventControllerMotion()
        motion.connect("enter", lambda *_a: self._on_row_hover(row, True))
        motion.connect("leave", lambda *_a: self._on_row_hover(row, False))
        row.add_controller(motion)
        return row

    def _set_delete_enabled(self, enabled: bool) -> None:
        action = getattr(self, "delete_action", None)
        if action is not None:
            action.set_enabled(enabled)

    def _toast(self, title: str, timeout: int = 2) -> Adw.Toast:
        toast = Adw.Toast.new(title)
        toast.set_timeout(timeout)
        toast.set_use_markup(False)
        self.toast_overlay.add_toast(toast)
        return toast

    def _show_empty(self) -> None:
        self.current_id = None
        self.stack.set_visible_child_name("empty")
        self._set_delete_enabled(False)
        if self._filter and self.snippets:
            self.empty_page.set_title("No matching notes")
            self.empty_page.set_description("Try another search, or create a new note.")
            self._placeholder_title.set_text("No matching notes")
            self._placeholder_hint.set_text("Try another search")
        elif not self.snippets:
            self.empty_page.set_title("No notes yet")
            self.empty_page.set_description("New note, or press Ctrl+N.")
            self._placeholder_title.set_text("No notes yet")
            self._placeholder_hint.set_text("Press Ctrl+N")
        else:
            self.empty_page.set_title("No note selected")
            self.empty_page.set_description("Choose a note in the sidebar, or press Ctrl+N.")
            self._placeholder_title.set_text("No notes yet")
            self._placeholder_hint.set_text("Press Ctrl+N")

    def _show_editor(self) -> None:
        self.stack.set_visible_child_name("editor")
        self._set_delete_enabled(True)

    def _clear_timeout(self, name: str) -> None:
        handle = getattr(self, name)
        if handle is not None:
            GLib.source_remove(handle)
            setattr(self, name, None)

    def on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        self._filter = (entry.get_text() or "").strip()
        self._clear_timeout("_search_timeout")
        self._search_timeout = GLib.timeout_add(SEARCH_DEBOUNCE_MS, self._apply_search)

    def _apply_search(self) -> bool:
        self._search_timeout = None
        keep = self.current_id
        visible_ids = {s["id"] for s in self._visible()}
        select = keep if keep in visible_ids else (next(iter(visible_ids), None))
        self._refresh_list(select_id=select)
        return False

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
        if self.split.get_collapsed():
            self.split.set_show_sidebar(False)

    def _current_format(self) -> str:
        snippet = self._find(self.current_id)
        if snippet:
            return normalize_format(snippet.get("format"))
        return "code"

    def _apply_format_ui(self, fmt: str, snippet: dict | None = None) -> None:
        fmt = normalize_format(fmt)
        is_code = fmt == "code"
        is_md = fmt == "markdown"

        self.lang_dropdown.set_visible(is_code)
        self.view_toggle.set_visible(is_md)
        self.format_row.set_visible(True)

        titles = {"code": "Code", "text": "Text", "markdown": "Markdown"}
        self.format_badge.set_text(titles[fmt])
        self.format_badge.set_tooltip_text(f"{titles[fmt]} — type is locked")

        for kind in FORMATS:
            self.body_view.remove_css_class(f"kind-{kind}")
        self.body_view.add_css_class(f"kind-{'markdown' if is_md else 'text'}")
        self.body_view.set_monospace(is_md)
        self.body_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)

        if is_code:
            if self.view_toggle.get_active_name() != "edit":
                self.view_toggle.set_active_name("edit")
            self.editor_stack.set_visible_child_name("code")
        elif not is_md:
            if self.view_toggle.get_active_name() != "edit":
                self.view_toggle.set_active_name("edit")
            self.editor_stack.set_visible_child_name("edit")

    def _sync_source_scheme(self) -> None:
        manager = GtkSource.StyleSchemeManager.get_default()
        dark = Adw.StyleManager.get_default().get_dark()
        name = "Adwaita-dark" if dark else "Adwaita"
        scheme = manager.get_scheme(name) or manager.get_scheme("classic")
        if scheme is not None:
            self.source_buffer.set_style_scheme(scheme)

    def _selected_language_id(self) -> str:
        index = int(self.lang_dropdown.get_selected())
        if index < 0 or index >= len(self._lang_ids):
            return ""
        return self._lang_ids[index]

    def _apply_source_language(self, lang_id: str) -> None:
        resolved = resolve_language_id(lang_id)
        lang = language_manager().get_language(resolved) if resolved else None
        self.source_buffer.set_language(lang)
        self.source_buffer.set_highlight_syntax(lang is not None)

    def _set_language_choice(self, value: str, apply: bool = True, persist: bool = False) -> None:
        resolved = resolve_language_id(value)
        key = resolved or (value or "").strip()
        if key and key not in self._lang_ids:
            self._lang_ids.append(key)
            self._lang_model.append(key)
        index = self._lang_ids.index(key) if key in self._lang_ids else 0
        was_loading = self._loading
        self._loading = True
        self.lang_dropdown.set_selected(index)
        if apply:
            self._apply_source_language(key)
        self._loading = was_loading
        if persist:
            self.on_editor_changed()

    def on_language_changed(self, *_args) -> None:
        if self._loading:
            return
        lang_id = self._selected_language_id()
        self._apply_source_language(lang_id)
        self.on_editor_changed()

    def _on_source_insert_text(self, _buffer, _location, text, _length) -> None:
        if self._loading or self._current_format() != "code":
            return
        if not text or (len(text) <= 2 and "\n" not in text):
            return
        GLib.idle_add(self._detect_language_from_paste, str(text))

    def _detect_language_from_paste(self, pasted: str) -> bool:
        if self._current_format() != "code":
            return False
        snippet = self._find(self.current_id)
        current = (snippet.get("language") if snippet else "") or self._selected_language_id()
        if not should_autodetect(current, pasted):
            return False
        guessed = detect_language(pasted, self._editor_body())
        if not guessed:
            return False
        if resolve_language_id(current) == guessed:
            return False
        self._set_language_choice(guessed, apply=True, persist=True)
        return False

    def on_view_changed(self, *_args) -> None:

        if self._current_format() != "markdown":
            name = "code" if self._current_format() == "code" else "edit"
            self.editor_stack.set_visible_child_name(name)
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

    def _markup_label(self, text: str, *css: str) -> Gtk.Label:
        label = Gtk.Label()
        label.set_markup(inline_to_pango(text))
        label.set_wrap(True)
        label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        label.set_xalign(0)
        label.set_selectable(True)
        label.set_hexpand(True)
        for name in css:
            label.add_css_class(name)
        return label

    def _schedule_preview_rebuild(self) -> None:
        self._clear_timeout("_preview_timeout")
        self._preview_timeout = GLib.timeout_add(PREVIEW_DEBOUNCE_MS, self._debounced_preview)

    def _debounced_preview(self) -> bool:
        self._preview_timeout = None
        if (
            self._current_format() == "markdown"
            and self.view_toggle.get_active_name() == "preview"
        ):
            self._show_preview()
        return False

    def _show_preview(self) -> None:
        _clear_box(self.preview_box)
        body, truncated = cap_markdown_source(self._editor_body())
        if not body.strip():
            empty = Gtk.Label(label="Nothing to preview")
            empty.add_css_class("md-empty")
            empty.add_css_class("dim-label")
            empty.set_use_markup(False)
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
                        block.get("text") or "",
                        f"md-h{level}",
                    )
                )
            elif kind == "paragraph":
                self.preview_box.append(
                    self._markup_label(
                        block.get("text") or "",
                        "md-paragraph",
                    )
                )
            elif kind == "quote":
                self.preview_box.append(
                    self._markup_label(
                        block.get("text") or "",
                        "md-quote",
                    )
                )
            elif kind == "code":
                text = block.get("text") or ""
                code = Gtk.Label(label=text)
                code.set_use_markup(False)
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
                        self._markup_label(item, "md-list-item")
                    )
                    self.preview_box.append(row)

        if truncated:
            note = Gtk.Label(label="Preview truncated")
            note.add_css_class("dim-label")
            note.add_css_class("caption")
            note.set_use_markup(False)
            note.set_xalign(0)
            self.preview_box.append(note)

        self.editor_stack.set_visible_child_name("preview")

    def _load_snippet_into_editor(self, snippet: dict) -> None:
        self._loading = True
        self.current_id = snippet["id"]
        self.title_entry.set_text(snippet.get("title", ""))
        fmt = normalize_format(snippet.get("format"))
        body = snippet.get("body", "")
        if fmt == "code":
            self.source_buffer.set_text(body)
            self._set_language_choice(snippet.get("language", ""), apply=True)
        else:
            self.body_buffer.set_text(body)
        self._apply_format_ui(fmt, snippet)
        if self.view_toggle.get_active_name() != "edit":
            self.view_toggle.set_active_name("edit")
        self.editor_stack.set_visible_child_name("code" if fmt == "code" else "edit")
        self._last_format = fmt
        self._show_editor()
        self._clear_timeout("_preview_timeout")
        self._loading = False

    def on_editor_changed(self, *_args) -> None:
        if self._loading or not self.current_id:
            return
        snippet = self._find(self.current_id)
        if not snippet:
            return
        snippet["title"] = self.title_entry.get_text()
        if normalize_format(snippet.get("format")) == "code":
            snippet["language"] = self._selected_language_id()
        snippet["body"] = self._editor_body()
        snippet["updated"] = now_iso()
        titles = {"code": "Code", "text": "Text", "markdown": "Markdown"}
        self.format_badge.set_text(titles.get(normalize_format(snippet.get("format")), "Code"))
        self._update_selected_row_labels()
        if normalize_format(snippet.get("format")) == "markdown":
            self._schedule_preview_rebuild()
        self._clear_timeout("_save_timeout")
        self._save_timeout = GLib.timeout_add(AUTOSAVE_DEBOUNCE_MS, self._autosave)

    def _autosave(self) -> bool:
        self._save_timeout = None
        self._write_snippets()
        self._update_selected_row_labels()
        return False

    def _flush_pending_save(self) -> None:
        if self._save_timeout is not None:
            GLib.source_remove(self._save_timeout)
            self._save_timeout = None
            self._write_snippets()

    def _update_row_from_snippet(self, row: Gtk.ListBoxRow, snippet: dict) -> None:
        title_w = getattr(row, "title_label", None)
        lang_w = getattr(row, "lang_label", None)
        preview_w = getattr(row, "preview_label", None)
        pin_w = getattr(row, "pin_button", None)
        if title_w is not None:
            title_w.set_use_markup(False)
            title_w.set_text(snippet.get("title") or "Untitled")
        if lang_w is not None:
            lang_w.set_use_markup(False)
            lang_w.set_text(sidebar_kind(snippet))
        if preview_w is not None:
            preview_w.set_use_markup(False)
            preview_w.set_text(preview_of(snippet.get("body", "")))
        if pin_w is not None:
            self._apply_pin_style(pin_w, bool(snippet.get("pinned")))

    def _update_selected_row_labels(self) -> None:
        row = self.listbox.get_selected_row()
        snippet = self._find(self.current_id)
        if row is None or snippet is None:
            return
        if getattr(row, "snippet_id", None) != snippet["id"]:
            return
        self._update_row_from_snippet(row, snippet)

    def _editor_body(self) -> str:
        buf = self.source_buffer if self._current_format() == "code" else self.body_buffer
        start = buf.get_start_iter()
        end = buf.get_end_iter()
        return buf.get_text(start, end, True)

    def _pin_icon(self, pinned: bool) -> str:
        if not hasattr(self, "_pin_icons"):
            unpinned = "view-pin-symbolic"
            pinned_icon = "view-pin-symbolic"
            display = Gdk.Display.get_default()
            if display is not None:
                theme = Gtk.IconTheme.get_for_display(display)
                if not theme.has_icon("view-pin-symbolic"):
                    if theme.has_icon("starred-symbolic"):
                        pinned_icon = "starred-symbolic"
                        unpinned = (
                            "non-starred-symbolic"
                            if theme.has_icon("non-starred-symbolic")
                            else "starred-symbolic"
                        )
            self._pin_icons = (unpinned, pinned_icon)
        return self._pin_icons[1] if pinned else self._pin_icons[0]

    def _apply_pin_style(self, button: Gtk.Button, pinned: bool) -> None:
        button.set_icon_name(self._pin_icon(pinned))
        button.set_tooltip_text("Unpin" if pinned else "Pin to top")
        hovered = bool(getattr(button, "_row_hovered", False))
        if pinned:
            button.set_opacity(1.0)
        elif hovered:
            button.set_opacity(0.4)
        else:
            button.set_opacity(0.0)
        button.remove_css_class("suggested-action")
        button.remove_css_class("pin-on")
        button.remove_css_class("pin-off")
        button.add_css_class("pin-on" if pinned else "pin-off")

    def _isolate_row_button(self, button: Gtk.Widget) -> None:
        """Claim the click after the button handles it so the row is not the only target."""
        gesture = Gtk.GestureClick()
        gesture.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        gesture.connect(
            "released",
            lambda gest, *_args: gest.set_state(Gtk.EventSequenceState.CLAIMED),
        )
        button.add_controller(gesture)

    def _on_row_hover(self, row: Gtk.ListBoxRow, hovered: bool) -> None:
        pin_btn = getattr(row, "pin_button", None)
        if pin_btn is None:
            return
        pin_btn._row_hovered = hovered  # type: ignore[attr-defined]
        snippet = self._find(getattr(row, "snippet_id", None))
        self._apply_pin_style(pin_btn, bool(snippet and snippet.get("pinned")))

    def _toggle_pin(self, snippet_id: str | None) -> None:

        snippet = self._find(snippet_id)
        if not snippet:
            return
        snippet["pinned"] = not bool(snippet.get("pinned"))
        self._write_snippets()
        keep = self.current_id
        self._refresh_list(select_id=keep)

    def on_pin(self, *_args) -> None:
        if not self.current_id:
            return
        self._toggle_pin(self.current_id)

    def _on_row_pin(self, _button: Gtk.Button, snippet_id: str) -> None:
        self._toggle_pin(snippet_id)

    def _copy_body_of(self, snippet_id: str | None) -> None:
        snippet = self._find(snippet_id)
        if not snippet:
            return
        if snippet_id == self.current_id:
            text = self._editor_body()
            self._flush_pending_save()
        else:
            text = snippet.get("body") or ""
        display = Gdk.Display.get_default()
        if display is None:
            self._toast("Clipboard unavailable")
            return
        display.get_clipboard().set(str(text))
        self._toast("Copied")

    def _on_row_copy(self, _button: Gtk.Button, snippet_id: str) -> None:
        self._copy_body_of(snippet_id)

    def on_copy(self, *_args) -> None:
        if not self.current_id:
            return
        self._copy_body_of(self.current_id)

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
        self._clear_timeout("_search_timeout")
        self._show_new_chooser()

    def _show_new_chooser(self) -> None:
        dialog = Adw.Dialog()
        dialog.set_content_width(420)
        dialog.set_follows_content_size(True)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title="New note"))
        toolbar.add_top_bar(header)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_start(24)
        content.set_margin_end(24)
        content.set_margin_top(12)
        content.set_margin_bottom(24)

        intro = Gtk.Label(label="What kind of note?")
        intro.add_css_class("title-4")
        intro.set_use_markup(False)
        intro.set_xalign(0)
        content.append(intro)

        hint = Gtk.Label(label="The type is locked after you create it.")
        hint.add_css_class("dim-label")
        hint.add_css_class("chooser-intro")
        hint.set_use_markup(False)
        hint.set_xalign(0)
        hint.set_wrap(True)
        content.append(hint)

        preferred = self._last_format if self._last_format in FORMATS else "code"
        options = (
            ("code", "Code", "Monospace snippet with syntax highlighting", "utilities-terminal-symbolic"),
            ("text", "Plain text", "A simple note without formatting", "document-edit-symbolic"),
            ("markdown", "Markdown", "Write now and preview when you want", "text-x-generic-symbolic"),
        )

        group = Gtk.ListBox()
        group.add_css_class("boxed-list")
        group.set_selection_mode(Gtk.SelectionMode.NONE)
        group.set_activate_on_single_click(True)

        for name, title, subtitle, icon_name in options:
            row = Adw.ActionRow()
            row.set_title(title)
            row.set_subtitle(subtitle)
            row.set_activatable(True)
            row.add_prefix(Gtk.Image.new_from_icon_name(icon_name))
            if name == preferred:
                last = Gtk.Label(label="Last used")
                last.add_css_class("dim-label")
                last.add_css_class("caption")
                last.set_use_markup(False)
                row.add_suffix(last)
            row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            row.connect("activated", self._on_chooser_picked, dialog, name)
            group.append(row)

        content.append(group)

        cancel = Gtk.Button(label="Cancel")
        cancel.add_css_class("flat")
        cancel.set_tooltip_text("Close without creating a note")
        cancel.connect("clicked", lambda *_args: dialog.close())
        header.pack_start(cancel)

        toolbar.set_content(content)
        dialog.set_child(toolbar)
        self._new_chooser_dialog = dialog
        dialog.connect("closed", self._on_chooser_closed)
        dialog.present(self)

    def _on_chooser_closed(self, dialog: Adw.Dialog) -> None:
        # Escape / Cancel / header close must not create an Untitled note.
        if self._new_chooser_dialog is dialog:
            self._new_chooser_dialog = None

    def _on_chooser_picked(self, _button, dialog: Adw.Dialog, fmt: str) -> None:
        self._new_chooser_dialog = None
        dialog.close()
        self._create_snippet(fmt)

    def _create_snippet(self, fmt: str) -> None:
        fmt = normalize_format(fmt)
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
            "pinned": False,
        }
        self._last_format = fmt
        self.snippets.insert(0, snippet)
        self._write_snippets()
        self._refresh_list(select_id=snippet["id"])
        self.title_entry.grab_focus()
        self.title_entry.select_region(0, -1)

    def on_show_shortcuts(self, *_args) -> None:
        window = Gtk.ShortcutsWindow(transient_for=self, modal=True)
        section = Gtk.ShortcutsSection()
        section.set_property("section-name", "shortcuts")
        section.set_property("title", "General")
        group = Gtk.ShortcutsGroup()
        group.set_property("title", "Notes")
        entries = (
            ("New note", "<Control>n"),
            ("Search", "<Control>f <Control>k"),
            ("Copy body", "<Control><Shift>c"),
            ("Pin or unpin", "<Control><Shift>p"),
            ("Delete note", "<Control>Delete"),
            ("Toggle notes list", "F9"),
            ("Markdown preview", "<Control>p"),
            ("Keyboard shortcuts", "<Control>question"),
            ("Close window", "<Control>w"),
            ("Quit", "<Control>q"),
        )
        for title, accelerator in entries:
            shortcut = Gtk.ShortcutsShortcut()
            shortcut.set_property("title", title)
            shortcut.set_property("accelerator", accelerator)
            group.add_shortcut(shortcut)
        section.add_group(group)
        window.add_section(section)
        window.present()

    def on_toggle_sidebar(self, *_args) -> None:
        self.split.set_show_sidebar(not self.split.get_show_sidebar())

    def on_close_window(self, *_args) -> None:
        self.close()

    def _persist_window_state(self) -> None:
        try:
            width, height = self.get_default_size()
            if width <= 0:
                width = self.get_width()
            if height <= 0:
                height = self.get_height()
            save_window_state(width, height, self.is_maximized())
        except (OSError, ValueError):
            pass

    def flush_for_quit(self) -> None:
        """Persist pending edits and window size; cancel leftover timeouts."""
        self._clear_timeout("_search_timeout")
        self._clear_timeout("_preview_timeout")
        self._flush_pending_save()
        self._persist_window_state()

    def _on_close_request(self, *_args) -> bool:
        self.flush_for_quit()
        return False

    def on_delete(self, *_args) -> None:
        if not self.current_id:
            return
        self._flush_pending_save()
        snippet = self._find(self.current_id)
        if not snippet:
            return
        title = snippet.get("title") or "Untitled"
        index = next(
            (i for i, item in enumerate(self.snippets) if item["id"] == snippet["id"]),
            len(self.snippets),
        )
        visible_ids = [item["id"] for item in self._visible()]
        try:
            pos = visible_ids.index(snippet["id"])
        except ValueError:
            pos = -1
        removed = copy.deepcopy(snippet)
        self.snippets = [item for item in self.snippets if item["id"] != snippet["id"]]
        self.current_id = None
        self._write_snippets()
        if pos >= 0 and pos + 1 < len(visible_ids):
            next_id = visible_ids[pos + 1]
        elif pos > 0:
            next_id = visible_ids[pos - 1]
        else:
            next_id = None
        self._refresh_list(select_id=next_id)
        toast = Adw.Toast.new(f"Deleted “{title}”")
        toast.set_button_label("Undo")
        toast.set_timeout(5)
        toast.set_use_markup(False)
        toast.connect("button-clicked", self._on_delete_toast_undo)
        toast.connect("dismissed", self._on_delete_toast_dismissed)
        self._pending_undos[id(toast)] = {
            "snippet": removed,
            "index": index,
            "toast": toast,
        }
        self._sync_undo_delete_action()
        self.toast_overlay.add_toast(toast)

    def _sync_undo_delete_action(self) -> None:
        action = getattr(self, "undo_delete_action", None)
        if action is not None:
            action.set_enabled(bool(self._pending_undos))

    def _pop_pending_undo(self, toast: Adw.Toast | None = None) -> dict | None:
        if toast is not None:
            return self._pending_undos.pop(id(toast), None)
        if not self._pending_undos:
            return None
        _key, pending = self._pending_undos.popitem()
        return pending

    def _restore_deleted(self, pending: dict) -> None:
        snippet = pending.get("snippet")
        if not isinstance(snippet, dict) or not snippet.get("id"):
            return
        if self._find(snippet["id"]):
            return
        restore_at_index(self.snippets, snippet, pending.get("index", 0))
        self._write_snippets()
        self._refresh_list(select_id=snippet["id"])
        self._toast("Restored")

    def _on_delete_toast_undo(self, toast: Adw.Toast) -> None:
        pending = self._pop_pending_undo(toast)
        self._sync_undo_delete_action()
        if pending:
            self._restore_deleted(pending)

    def _on_delete_toast_dismissed(self, toast: Adw.Toast) -> None:
        self._pending_undos.pop(id(toast), None)
        self._sync_undo_delete_action()

    def on_undo_delete(self, *_args) -> None:
        pending = self._pop_pending_undo()
        self._sync_undo_delete_action()
        if not pending:
            return
        toast = pending.get("toast")
        if toast is not None:
            toast.dismiss()
        self._restore_deleted(pending)

    def _save_screenshot(self) -> bool:
        path = os.environ.get("SNIPPETS_SCREENSHOT") or os.environ.get("NOTES_SCREENSHOT")
        if not path:
            return False
        display = os.environ.get("DISPLAY") or ":3"
        try:
            completed = subprocess.run(
                ["import", "-display", display, "-window", "root", path],
                check=False,
                timeout=12,
                capture_output=True,
            )
            if (
                completed.returncode == 0
                and Path(path).is_file()
                and Path(path).stat().st_size > 200
            ):
                app = self.get_application()
                if app is not None:
                    app.quit()
                return False
        except (OSError, subprocess.SubprocessError, Exception):
            pass
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


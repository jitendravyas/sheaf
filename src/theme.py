# SPDX-License-Identifier: MIT
"""Optional Omarchy palette for Sheaf.

Resolution order:

1. ``~/.config/omarchy/themed/sheaf.css`` (Omarchy renders
   ``sheaf.css.tpl`` on theme switch)
2. The active theme ``colors.toml`` under common current-theme paths
3. ``None`` — keep Adwaita / system CSS

No extra dependencies: the TOML subset used by Omarchy palettes is
parsed here.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Mapping

MAX_PALETTE_BYTES = 256 * 1024

SEMANTIC_KEYS = ("background", "foreground", "accent", "red")
COLOR_INDEX_KEYS = tuple(f"color{i}" for i in range(16))
PALETTE_KEYS = SEMANTIC_KEYS + COLOR_INDEX_KEYS

CSS_VARIABLES = {
    "background": "--sheaf-bg",
    "foreground": "--sheaf-fg",
    "accent": "--sheaf-accent",
    "red": "--sheaf-red",
    "sidebar": "--sheaf-sidebar",
    **{f"color{i}": f"--sheaf-color{i}" for i in range(16)},
}

_LEGACY_KEYS = {
    "bg": "background",
    "fg": "foreground",
    "sheaf-bg": "background",
    "sheaf-fg": "foreground",
    "sheaf-accent": "accent",
    "sheaf-red": "red",
    "sheaf-sidebar": "sidebar",
    **{f"sheaf-color{i}": f"color{i}" for i in range(16)},
}

_HEX = re.compile(
    r"^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$"
)
_BARE_HEX = re.compile(r"^[0-9A-Fa-f]{6}$")
_PLACEHOLDER = re.compile(r"\{\{[^}]+\}\}")
_ASSIGN = re.compile(
    r"(?i)(?:--)?(?P<key>[A-Za-z_][A-Za-z0-9_-]*)\s*[:=]\s*"
    r"(?P<val>\"[^\"]+\"|'[^']+'|#[0-9A-Fa-f]{3,8}|[0-9A-Fa-f]{6})"
)
_THEME_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _xdg_home(env_name: str, *fallback: str) -> Path:
    raw = os.environ.get(env_name)
    if raw:
        return Path(raw).expanduser()
    return Path.home().joinpath(*fallback)


def config_home() -> Path:
    return _xdg_home("XDG_CONFIG_HOME", ".config")


def state_home() -> Path:
    return _xdg_home("XDG_STATE_HOME", ".local", "state")


def themed_sheaf_css_path(cfg: Path | None = None) -> Path:
    return (cfg or config_home()) / "omarchy" / "themed" / "sheaf.css"


def normalize_hex(value: str) -> str | None:
    text = (value or "").strip().strip("\"'").strip()
    if not text:
        return None
    if _BARE_HEX.fullmatch(text):
        text = "#" + text
    if not _HEX.fullmatch(text):
        return None
    if len(text) == 4:
        text = "#" + "".join(ch * 2 for ch in text[1:])
    return text.lower()


def _canonical_key(raw: str) -> str:
    key = (raw or "").strip().lstrip("-").replace("_", "-").casefold()
    if key.startswith("sheaf-"):
        mapped = _LEGACY_KEYS.get(key)
        if mapped:
            return mapped
    key = key.replace("-", "_")
    return _LEGACY_KEYS.get(key, key)


def parse_palette_text(text: str) -> dict[str, str]:
    """Parse a flat colors.toml, CSS custom-property file, or key=value list."""
    if not text or _PLACEHOLDER.search(text):
        return {}
    found: dict[str, str] = {}
    for match in _ASSIGN.finditer(text):
        key = _canonical_key(match.group("key"))
        color = normalize_hex(match.group("val"))
        if color is None:
            continue
        if key in PALETTE_KEYS or key in ("sidebar", "bg", "fg"):
            found[key] = color
        elif key in _LEGACY_KEYS:
            found[_LEGACY_KEYS[key]] = color
    return found


def parse_colors_toml(text: str) -> dict[str, str]:
    """Public entry for the unit test — same parser, TOML-shaped input."""
    return parse_palette_text(text)


def parse_sheaf_css(text: str) -> dict[str, str]:
    return parse_palette_text(text)


def _complete_palette(raw: Mapping[str, str]) -> dict[str, str] | None:
    colors = {key: value for key, value in raw.items() if normalize_hex(value)}
    if not colors:
        return None
    if "accent" not in colors and "color4" in colors:
        colors["accent"] = colors["color4"]
    if "red" not in colors and "color1" in colors:
        colors["red"] = colors["color1"]
    if "sidebar" not in colors:
        for fallback in (
            "lighter_background",
            "dark_background",
            "background",
            "color0",
        ):
            if fallback in colors:
                colors["sidebar"] = colors[fallback]
                break
    return colors


def _read_palette_file(path: Path) -> dict[str, str] | None:
    try:
        if not path.is_file():
            return None
        if path.stat().st_size > MAX_PALETTE_BYTES:
            return None
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    return _complete_palette(parse_palette_text(text))


def _read_theme_name(path: Path) -> str | None:
    try:
        if not path.is_file() or path.stat().st_size > 1024:
            return None
        name = path.read_text(encoding="utf-8").strip().splitlines()[0].strip()
    except (OSError, IndexError):
        return None
    if not _THEME_NAME.fullmatch(name):
        return None
    return name


def _add_unique(paths: list[Path], seen: set[Path], path: Path) -> None:
    try:
        resolved = path.resolve()
    except OSError:
        return
    if resolved in seen or not resolved.is_file():
        return
    if resolved.name != "colors.toml":
        return
    seen.add(resolved)
    paths.append(resolved)


def _scan_dir_for_toml(directory: Path, paths: list[Path], seen: set[Path]) -> None:
    direct = directory / "colors.toml"
    if direct.is_file():
        _add_unique(paths, seen, direct)
        return
    try:
        children = sorted(directory.iterdir(), key=lambda item: item.name)
    except OSError:
        return
    for child in children:
        if child.is_file() and child.name == "colors.toml":
            _add_unique(paths, seen, child)
        elif child.is_dir():
            nested = child / "colors.toml"
            if nested.is_file():
                _add_unique(paths, seen, nested)


def colors_toml_candidates(
    cfg: Path | None = None,
    state: Path | None = None,
) -> list[Path]:
    """Ordered list of colors.toml paths that might hold the active theme."""
    cfg = cfg or config_home()
    state = state or state_home()
    found: list[Path] = []
    seen: set[Path] = set()

    explicit = (
        cfg / "omarchy" / "current" / "theme" / "colors.toml",
        cfg / "omarchy" / "theme" / "colors.toml",
        state / "omarchy" / "current" / "theme" / "colors.toml",
    )
    for path in explicit:
        _add_unique(found, seen, path)

    for directory in (
        cfg / "omarchy" / "current" / "theme",
        cfg / "omarchy" / "theme",
        state / "omarchy" / "current" / "theme",
        cfg / "omarchy" / "current",
    ):
        if directory.is_dir():
            _scan_dir_for_toml(directory, found, seen)

    names: list[str] = []
    for name_file in (
        cfg / "omarchy" / "current" / "theme.name",
        state / "omarchy" / "current" / "theme.name",
    ):
        name = _read_theme_name(name_file)
        if name and name not in names:
            names.append(name)

    for name in names:
        for root in (
            cfg / "omarchy" / "themes" / name / "colors.toml",
            Path("/usr/share/omarchy/themes") / name / "colors.toml",
        ):
            _add_unique(found, seen, root)

    return found


def checked_paths(
    cfg: Path | None = None,
    state: Path | None = None,
) -> list[Path]:
    """Every location consulted, including ones that do not exist."""
    cfg = cfg or config_home()
    state = state or state_home()
    ordered = [
        themed_sheaf_css_path(cfg),
        cfg / "omarchy" / "current" / "theme" / "colors.toml",
        cfg / "omarchy" / "theme" / "colors.toml",
        state / "omarchy" / "current" / "theme" / "colors.toml",
        cfg / "omarchy" / "current" / "theme.name",
        state / "omarchy" / "current" / "theme.name",
    ]
    return ordered


def load_omarchy_colors(
    cfg: Path | None = None,
    state: Path | None = None,
) -> dict[str, str] | None:
    """Return a palette dict or None to keep Adwaita / system CSS."""
    cfg = cfg or config_home()
    state = state or state_home()

    css_path = themed_sheaf_css_path(cfg)
    from_css = _read_palette_file(css_path)
    if from_css:
        return from_css

    for path in colors_toml_candidates(cfg, state):
        parsed = _read_palette_file(path)
        if parsed:
            return parsed
    return None


def palette_css(colors: Mapping[str, str]) -> str:
    """GTK CSS that sets --sheaf-* variables on the application window."""
    lines = [".sheaf-window {"]
    for key in ("background", "foreground", "accent", "red", "sidebar") + COLOR_INDEX_KEYS:
        value = colors.get(key)
        var = CSS_VARIABLES.get(key)
        if not value or not var:
            continue
        hex_color = normalize_hex(value)
        if hex_color:
            lines.append(f"  {var}: {hex_color};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def apply_omarchy_palette(window: object, colors: Mapping[str, str] | None) -> None:
    """Attach palette CSS variables to *window*. No-op when colors is None."""
    if not colors:
        return
    try:
        from gi.repository import Gdk, Gtk
    except (ImportError, ValueError):
        return
    css = palette_css(colors)
    provider = Gtk.CssProvider()
    provider.load_from_data(css.encode("utf-8"))
    display = None
    getter = getattr(window, "get_display", None)
    if callable(getter):
        display = getter()
    if display is None:
        display = Gdk.Display.get_default()
    if display is None:
        return
    Gtk.StyleContext.add_provider_for_display(
        display,
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 10,
    )
    add_class = getattr(window, "add_css_class", None)
    if callable(add_class):
        add_class("sheaf-window")


def paths_checked_for_report() -> list[str]:
    return [str(path) for path in checked_paths()]


__all__ = (
    "PALETTE_KEYS",
    "apply_omarchy_palette",
    "checked_paths",
    "colors_toml_candidates",
    "load_omarchy_colors",
    "normalize_hex",
    "palette_css",
    "parse_colors_toml",
    "parse_palette_text",
    "parse_sheaf_css",
    "paths_checked_for_report",
    "themed_sheaf_css_path",
)

#!/usr/bin/env python3
"""Parse Omarchy colors.toml / sheaf.css and resolve with Adwaita fallback."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from theme import (  # noqa: E402
    load_omarchy_colors,
    normalize_hex,
    palette_css,
    parse_colors_toml,
    parse_sheaf_css,
    themed_sheaf_css_path,
)

SAMPLE_TOML = """
# Tokyo-ish sample used by the unit test — not loaded at runtime.
mode = "dark"

accent = "#7aa2f7"
selection = "#292e42"
muted = "#414868"

background = "#1a1b26"
foreground = "#a9b1d6"
red = "#f7768e"

color0 = "#32344a"
color1 = "#f7768e"
color2 = "#9ece6a"
color3 = "#e0af68"
color4 = "#7aa2f7"
color5 = "#ad8ee6"
color6 = "#449dab"
color7 = "#787c99"
color8 = "#444b6a"
color9 = "#ff7a93"
color10 = "#b9f27c"
color11 = "#ff9e64"
color12 = "#7da6ff"
color13 = "#bb9af7"
color14 = "#0db9d7"
color15 = "#acb0d0"
"""


def assert_true(cond: bool, msg: object) -> None:
    if not cond:
        raise AssertionError(msg)


def test_parse_colors_toml() -> None:
    colors = parse_colors_toml(SAMPLE_TOML)
    assert_true(colors["background"] == "#1a1b26", colors)
    assert_true(colors["foreground"] == "#a9b1d6", colors)
    assert_true(colors["accent"] == "#7aa2f7", colors)
    assert_true(colors["red"] == "#f7768e", colors)
    assert_true(colors["color0"] == "#32344a", colors)
    assert_true(colors["color1"] == "#f7768e", colors)
    assert_true(colors["color4"] == "#7aa2f7", colors)
    assert_true(colors["color15"] == "#acb0d0", colors)
    assert_true("mode" not in colors, colors)
    assert_true("selection" not in colors, colors)
    assert_true(normalize_hex("1A1B26") == "#1a1b26", normalize_hex("1A1B26"))
    assert_true(normalize_hex("#abc") == "#aabbcc", normalize_hex("#abc"))
    assert_true(parse_colors_toml("") == {}, "empty")
    assert_true(parse_colors_toml("not = colors") == {}, "junk")
    # Unresolved Omarchy placeholders must not be treated as a palette.
    assert_true(parse_colors_toml("background = {{ background }}") == {}, "tpl")


def test_accent_and_red_fallbacks() -> None:
    colors = parse_colors_toml(
        'background = "#111111"\nforeground = "#eeeeee"\n'
        'color1 = "#ff0000"\ncolor4 = "#0000ff"\n'
    )
    from theme import _complete_palette

    filled = _complete_palette(colors)
    assert_true(filled is not None, filled)
    assert_true(filled["accent"] == "#0000ff", filled)
    assert_true(filled["red"] == "#ff0000", filled)


def test_parse_sheaf_css() -> None:
    css = """
    :root {
      --sheaf-bg: #1a1b26;
      --sheaf-fg: #a9b1d6;
      --sheaf-accent: #7aa2f7;
      --sheaf-red: #f7768e;
      --sheaf-color0: #32344a;
      --sheaf-color15: #acb0d0;
    }
    background=#1a1b26
    """
    colors = parse_sheaf_css(css)
    assert_true(colors["background"] == "#1a1b26", colors)
    assert_true(colors["foreground"] == "#a9b1d6", colors)
    assert_true(colors["accent"] == "#7aa2f7", colors)
    assert_true(colors["red"] == "#f7768e", colors)
    assert_true(colors["color0"] == "#32344a", colors)
    assert_true(colors["color15"] == "#acb0d0", colors)
    assert_true(parse_sheaf_css("--sheaf-bg: {{ background }};") == {}, "unrendered")


def test_palette_css_variables() -> None:
    css = palette_css(
        {
            "background": "#1a1b26",
            "foreground": "#a9b1d6",
            "accent": "#7aa2f7",
            "red": "#f7768e",
            "color0": "#32344a",
        }
    )
    assert_true("--sheaf-bg: #1a1b26;" in css, css)
    assert_true("--sheaf-fg: #a9b1d6;" in css, css)
    assert_true("--sheaf-accent: #7aa2f7;" in css, css)
    assert_true("--sheaf-red: #f7768e;" in css, css)
    assert_true("--sheaf-color0: #32344a;" in css, css)
    assert_true(".sheaf-window" in css, css)


def test_resolve_none_without_omarchy() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cfg = Path(tmp) / "config"
        state = Path(tmp) / "state"
        cfg.mkdir()
        state.mkdir()
        assert_true(load_omarchy_colors(cfg, state) is None, "empty homes")
        assert_true(
            themed_sheaf_css_path(cfg) == cfg / "omarchy" / "themed" / "sheaf.css",
            themed_sheaf_css_path(cfg),
        )


def test_resolve_prefers_sheaf_css() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cfg = Path(tmp) / "config"
        state = Path(tmp) / "state"
        themed = cfg / "omarchy" / "themed"
        current = cfg / "omarchy" / "current" / "theme"
        themed.mkdir(parents=True)
        current.mkdir(parents=True)
        (current / "colors.toml").write_text(
            'background = "#000000"\nforeground = "#ffffff"\naccent = "#ff00ff"\n',
            encoding="utf-8",
        )
        (themed / "sheaf.css").write_text(
            "--sheaf-bg: #1a1b26;\n--sheaf-fg: #a9b1d6;\n--sheaf-accent: #7aa2f7;\n",
            encoding="utf-8",
        )
        colors = load_omarchy_colors(cfg, state)
        assert_true(colors is not None, colors)
        assert_true(colors["background"] == "#1a1b26", colors)
        assert_true(colors["accent"] == "#7aa2f7", colors)


def test_resolve_colors_toml_when_no_css() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cfg = Path(tmp) / "config"
        state = Path(tmp) / "state"
        current = cfg / "omarchy" / "current" / "theme"
        current.mkdir(parents=True)
        (current / "colors.toml").write_text(SAMPLE_TOML, encoding="utf-8")
        colors = load_omarchy_colors(cfg, state)
        assert_true(colors is not None, colors)
        assert_true(colors["background"] == "#1a1b26", colors)
        assert_true(colors["color15"] == "#acb0d0", colors)


def main() -> int:
    test_parse_colors_toml()
    test_accent_and_red_fallbacks()
    test_parse_sheaf_css()
    test_palette_css_variables()
    test_resolve_none_without_omarchy()
    test_resolve_prefers_sheaf_css()
    test_resolve_colors_toml_when_no_css()
    print("ok  theme toml/css parser and resolve order")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

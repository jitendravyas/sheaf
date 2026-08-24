#!/usr/bin/env python3
"""Link allowlist and markdown preview cap."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from markdown import (  # noqa: E402
    PREVIEW_MAX_BYTES,
    PREVIEW_MAX_LINES,
    cap_markdown_source,
    inline_to_pango,
    parse_markdown,
    safe_href,
)


def assert_true(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_safe_href_allows_http_https() -> None:
    assert_true(safe_href("https://example.com") == "https://example.com", "https")
    assert_true(safe_href("http://example.com/a?b=1") == "http://example.com/a?b=1", "http")
    assert_true(safe_href("  HTTPS://Example.COM/x  ") == "HTTPS://Example.COM/x", "scheme case")
    assert_true(safe_href("https://127.0.0.1:8080/path") is not None, "loopback")


def test_safe_href_rejects_dangerous() -> None:
    blocked = [
        "javascript:alert(1)",
        "JAVASCRIPT:alert(1)",
        "data:text/html,hi",
        "DATA:text/plain,x",
        "file:///etc/passwd",
        "file://localhost/etc/passwd",
        "vbscript:msgbox(1)",
        "VBSCRIPT:msgbox",
        "./secret.txt",
        "../etc/passwd",
        "/etc/passwd",
        "foo/bar.md",
        "notes.json",
        "#anchor",
        "//evil.example/x",
        "https://",
        "http://",
        "",
        "   ",
        "mailto:user@example.com",
    ]
    for url in blocked:
        assert_true(safe_href(url) is None, f"should reject {url!r}")


def test_inline_to_pango_allowlist() -> None:
    good = inline_to_pango("See [Arch wiki](https://wiki.archlinux.org).")
    assert_true('<a href="https://wiki.archlinux.org">' in good, good)
    assert_true("Arch wiki" in good, good)

    escaped = inline_to_pango("[x](https://example.com?a=1&b=2)")
    assert_true("https://example.com?a=1&amp;b=2" in escaped, escaped)

    label = inline_to_pango("[<b>x</b>](https://ok.example)")
    assert_true("&lt;b&gt;x&lt;/b&gt;" in label, label)
    assert_true("<a href=" in label, label)

    for raw, label_text in (
        ("javascript:alert(1)", "click"),
        ("data:text/html,hi", "x"),
        ("file:///etc/passwd", "secret"),
        ("vbscript:msgbox", "vb"),
        ("./secret.txt", "rel"),
        ("../escape", "up"),
        ("/etc/passwd", "abs"),
    ):
        markup = inline_to_pango(f"[{label_text}]({raw})")
        assert_true("<a href=" not in markup, f"link leaked for {raw!r}: {markup}")
        assert_true(label_text in markup, f"label missing for {raw!r}: {markup}")


def test_parse_markdown_still_works() -> None:
    blocks = parse_markdown("# Hello\n\nA **bold** [link](https://example.com).\n")
    kinds = [b["type"] for b in blocks]
    assert_true(kinds == ["heading", "paragraph"], kinds)


def test_preview_cap() -> None:
    lines = "\n".join(f"line {i}" for i in range(PREVIEW_MAX_LINES + 50))
    capped, truncated = cap_markdown_source(lines)
    assert_true(truncated, "line cap should truncate")
    assert_true(capped.count("\n") == PREVIEW_MAX_LINES - 1, capped.count("\n"))

    huge = "x" * (PREVIEW_MAX_BYTES + 200)
    capped, truncated = cap_markdown_source(huge)
    assert_true(truncated, "byte cap should truncate")
    assert_true(len(capped.encode("utf-8")) <= PREVIEW_MAX_BYTES, len(capped.encode("utf-8")))


def main() -> int:
    test_safe_href_allows_http_https()
    test_safe_href_rejects_dangerous()
    test_inline_to_pango_allowlist()
    test_parse_markdown_still_works()
    test_preview_cap()
    print("ok  markdown links and preview cap")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

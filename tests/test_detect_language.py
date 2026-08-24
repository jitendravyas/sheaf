#!/usr/bin/env python3
"""Assertions for paste language auto-detect."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from window import detect_language, should_autodetect  # noqa: E402


def check(pasted: str, expected: str) -> None:
    got = detect_language(pasted, pasted)
    assert got == expected, f"{pasted!r} -> {got!r}, expected {expected!r}"
    print(f"ok  {pasted!r} -> {got}")


def main() -> int:
    check("def foo():", "python3")
    check("function()", "js")
    check('{"a":1}', "json")
    check("#!/bin/bash", "sh")
    check("class Foo:", "python3")
    check("from pathlib import Path", "python3")
    check("if __name__ == '__main__':", "python3")
    check("const x = 1", "js")
    check("console.log('hi')", "js")
    check("import x from 'y'", "js")
    check("package main\nfunc Hello() {}", "go")
    check("fn main() {}", "rust")
    check("<div class=\"x\">hi</div>", "html")
    check("body { color: red; }", "css")
    check("sudo pacman -Syu", "sh")
    assert should_autodetect("python3", "x") is False
    assert should_autodetect("", "def foo():") is True
    assert should_autodetect("js", "a" * 90) is True
    print("all assertions passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

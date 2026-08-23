# SPDX-License-Identifier: MIT
"""Conservative Markdown subset → block list and Pango markup.

Enough for headings, lists, bold/italic, inline code, fenced blocks,
quotes, rules, and links. Not a CommonMark implementation.
"""

from __future__ import annotations

import html
import re

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_UL = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_OL = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
_QUOTE = re.compile(r"^>\s?(.*)$")
_HR = re.compile(r"^(?:-{3,}|\*{3,}|_{3,})\s*$")
_FENCE = re.compile(r"^```\s*(\w+)?\s*$")
_CONT = re.compile(r"^ {2,}\S")

_INLINE = re.compile(
    r"`([^`]+)`"
    r"|\[([^\]]+)\]\(([^)]+)\)"
    r"|\*\*\*(.+?)\*\*\*"
    r"|___(.+?)___"
    r"|\*\*(.+?)\*\*"
    r"|__(.+?)__"
    r"|(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)"
    r"|(?<!_)_(?!_)(.+?)(?<!_)_(?!_)"
)


def _esc(text: str) -> str:
    return html.escape(text, quote=False)


def inline_to_pango(text: str) -> str:
    """Turn a conservative inline subset into Pango markup."""
    parts: list[str] = []
    pos = 0
    for match in _INLINE.finditer(text):
        parts.append(_esc(text[pos : match.start()]))
        if match.group(1) is not None:
            parts.append(f"<tt>{_esc(match.group(1))}</tt>")
        elif match.group(2) is not None:
            url = html.escape(match.group(3).strip(), quote=True)
            parts.append(f'<a href="{url}">{_esc(match.group(2))}</a>')
        elif match.group(4) is not None:
            parts.append(f"<b><i>{_esc(match.group(4))}</i></b>")
        elif match.group(5) is not None:
            parts.append(f"<b><i>{_esc(match.group(5))}</i></b>")
        elif match.group(6) is not None:
            parts.append(f"<b>{_esc(match.group(6))}</b>")
        elif match.group(7) is not None:
            parts.append(f"<b>{_esc(match.group(7))}</b>")
        elif match.group(8) is not None:
            parts.append(f"<i>{_esc(match.group(8))}</i>")
        elif match.group(9) is not None:
            parts.append(f"<i>{_esc(match.group(9))}</i>")
        pos = match.end()
    parts.append(_esc(text[pos:]))
    return "".join(parts).replace("\n", " ")


def parse_markdown(source: str) -> list[dict]:
    """Parse *source* into a list of block dictionaries."""
    lines = (source or "").replace("\r\n", "\n").split("\n")
    blocks: list[dict] = []
    i = 0
    in_fence = False
    fence_lang = ""
    fence_lines: list[str] = []
    para: list[str] = []

    def flush_para() -> None:
        if not para:
            return
        blocks.append({"type": "paragraph", "text": "\n".join(para)})
        para.clear()

    while i < len(lines):
        line = lines[i]

        if in_fence:
            if _FENCE.match(line):
                blocks.append(
                    {"type": "code", "lang": fence_lang, "text": "\n".join(fence_lines)}
                )
                in_fence = False
                fence_lang = ""
                fence_lines = []
            else:
                fence_lines.append(line)
            i += 1
            continue

        fenced = _FENCE.match(line)
        if fenced:
            flush_para()
            in_fence = True
            fence_lang = fenced.group(1) or ""
            fence_lines = []
            i += 1
            continue

        if line.strip() and _HR.match(line.strip()):
            flush_para()
            blocks.append({"type": "hr"})
            i += 1
            continue

        heading = _HEADING.match(line)
        if heading:
            flush_para()
            blocks.append(
                {
                    "type": "heading",
                    "level": len(heading.group(1)),
                    "text": heading.group(2).strip(),
                }
            )
            i += 1
            continue

        quoted = _QUOTE.match(line)
        if quoted:
            flush_para()
            collected = [quoted.group(1)]
            i += 1
            while i < len(lines):
                more = _QUOTE.match(lines[i])
                if not more:
                    break
                collected.append(more.group(1))
                i += 1
            blocks.append({"type": "quote", "text": "\n".join(collected)})
            continue

        unordered = _UL.match(line)
        if unordered:
            flush_para()
            items: list[str] = []
            while i < len(lines):
                item = _UL.match(lines[i])
                if item:
                    items.append(item.group(2))
                    i += 1
                    continue
                if items and _CONT.match(lines[i]):
                    items[-1] = items[-1] + " " + lines[i].strip()
                    i += 1
                    continue
                break
            blocks.append({"type": "ul", "items": items})
            continue

        ordered = _OL.match(line)
        if ordered:
            flush_para()
            items = []
            while i < len(lines):
                item = _OL.match(lines[i])
                if item:
                    items.append(item.group(3))
                    i += 1
                    continue
                if items and _CONT.match(lines[i]):
                    items[-1] = items[-1] + " " + lines[i].strip()
                    i += 1
                    continue
                break
            blocks.append({"type": "ol", "items": items})
            continue

        if not line.strip():
            flush_para()
            i += 1
            continue

        para.append(line)
        i += 1

    if in_fence:
        blocks.append({"type": "code", "lang": fence_lang, "text": "\n".join(fence_lines)})
    flush_para()
    return blocks


FORMATS = ("code", "text", "markdown")


def normalize_format(value: object) -> str:
    raw = str(value or "").strip().casefold()
    if raw in ("md", "markdown"):
        return "markdown"
    if raw in ("text", "plain", "plaintext", "plain-text"):
        return "text"
    if raw in ("code", "snippet"):
        return "code"
    return "code"


def sidebar_kind(snippet: dict) -> str:
    """Short sidebar tag: language for code, otherwise text / md."""
    fmt = normalize_format(snippet.get("format"))
    if fmt == "text":
        return "text"
    if fmt == "markdown":
        return "md"
    lang = str(snippet.get("language") or "").strip()
    return lang or "code"

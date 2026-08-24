#!/usr/bin/env python3
"""JSON schema skip, body cap, atomic write, path safety."""

from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from window import (  # noqa: E402
    APP_ID,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    MAX_NOTE_BODY_BYTES,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    OLD_APP_ID,
    atomic_write_json,
    choose_initial_snippets,
    clamp_window_size,
    load_store_text,
    load_window_state,
    load_window_state_text,
    migrate_legacy_data,
    normalize_snippet,
    parse_store_payload,
    parse_window_state,
    restore_at_index,
    safe_store_path,
    save_window_state,
    snippets_file,
    sort_visible,
    window_file,
    window_state_payload,
)


def assert_true(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_schema_skips_garbage() -> None:
    payload = [
        {"title": "ok", "body": "hello", "format": "text"},
        "not a dict",
        123,
        None,
        {"body": ["nested", "garbage"]},
        {"body": {"x": 1}},
        {"title": 42, "body": "number title", "format": "text", "id": "n1"},
        {"snippets": "nope"},
    ]
    items, last = parse_store_payload(payload)
    ids_or_titles = {(s.get("id"), s.get("title"), s.get("body")) for s in items}
    assert_true(last is None, last)
    assert_true(len(items) == 2, [ (s["title"], s["body"]) for s in items ])
    bodies = [s["body"] for s in items]
    assert_true("hello" in bodies, bodies)
    assert_true("number title" in bodies, bodies)
    titles = [s["title"] for s in items]
    assert_true("42" in titles, titles)
    assert_true("nested" not in "".join(bodies), bodies)

    wrapped = {"snippets": payload, "last_format": "markdown"}
    items, last = parse_store_payload(wrapped)
    assert_true(last == "markdown", last)
    assert_true(len(items) == 2, len(items))

    assert_true(parse_store_payload("nope") == ([], None), "non-list")
    assert_true(parse_store_payload({"snippets": {"a": 1}})[0] == [], "snippets not list")
    assert_true(load_store_text("not-json") == [], "invalid json")
    assert_true(load_store_text('{"snippets": [1, 2, "x"]}') == [], "all garbage")


def test_body_cap() -> None:
    huge = "a" * (MAX_NOTE_BODY_BYTES + 500)
    snippet = normalize_snippet({"title": "big", "body": huge, "format": "text"})
    assert_true(snippet is not None, "huge body should coerce, not skip")
    assert_true(len(snippet["body"].encode("utf-8")) <= MAX_NOTE_BODY_BYTES, len(snippet["body"]))


def test_normalize_skips_non_dict() -> None:
    assert_true(normalize_snippet("x") is None, "string")
    assert_true(normalize_snippet(None) is None, "none")
    assert_true(normalize_snippet([1]) is None, "list")


def test_path_escape_and_atomic_write() -> None:
    previous = os.environ.get("XDG_DATA_HOME")
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["XDG_DATA_HOME"] = tmp
        path = snippets_file()
        assert_true(path.name == "snippets.json", path)
        assert_true(str(path.resolve()).startswith(str(Path(tmp).resolve())), str(path))

        raised = False
        try:
            safe_store_path("../escape.json")
        except ValueError:
            raised = True
        assert_true(raised, "relative escape should raise")

        raised = False
        try:
            safe_store_path("sub/dir/notes.json")
        except ValueError:
            raised = True
        assert_true(raised, "nested path should raise")

        payload = {"snippets": [{"id": "a", "title": "t", "format": "text",
                                 "language": "text", "body": "b", "updated": "2026-01-01T00:00:00+00:00"}],
                   "last_format": "text"}
        atomic_write_json(path, payload)
        assert_true(path.is_file(), "wrote")
        mode = stat.S_IMODE(path.stat().st_mode)
        assert_true(mode == 0o600, oct(mode))
        assert_true(not path.with_name(path.name + ".tmp").exists(), "tmp leftover")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert_true(data["snippets"][0]["title"] == "t", data)

        outside = Path(tmp).resolve().parent / "not-sheaf.json"
        raised = False
        try:
            atomic_write_json(outside, payload)
        except ValueError:
            raised = True
        assert_true(raised, "write outside data dir should raise")
        assert_true(not outside.exists(), "should not create escaped file")
    if previous is None:
        os.environ.pop("XDG_DATA_HOME", None)
    else:
        os.environ["XDG_DATA_HOME"] = previous


def test_restore_at_index() -> None:
    items = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    idx = restore_at_index(items, {"id": "x"}, 1)
    assert_true(idx == 1, idx)
    assert_true([item["id"] for item in items] == ["a", "x", "b", "c"], items)

    items = [{"id": "a"}]
    idx = restore_at_index(items, {"id": "z"}, 99)
    assert_true(idx == 1, idx)
    assert_true([item["id"] for item in items] == ["a", "z"], items)

    items = [{"id": "a"}]
    idx = restore_at_index(items, {"id": "z"}, -5)
    assert_true(idx == 0, idx)
    assert_true([item["id"] for item in items] == ["z", "a"], items)

    items = []
    idx = restore_at_index(items, {"id": "only"}, 3)
    assert_true(idx == 0, idx)
    assert_true(items == [{"id": "only"}], items)

    items = [{"id": "keep"}]
    idx = restore_at_index(items, {"id": "front"}, 0)
    assert_true(idx == 0, idx)
    assert_true([item["id"] for item in items] == ["front", "keep"], items)


def test_normalize_pinned() -> None:
    base = {"title": "t", "body": "b", "format": "text"}
    pinned_true = normalize_snippet({**base, "pinned": True})
    assert_true(pinned_true is not None and pinned_true["pinned"] is True, pinned_true)
    pinned_false = normalize_snippet({**base, "pinned": False})
    assert_true(pinned_false is not None and pinned_false["pinned"] is False, pinned_false)
    defaulted = normalize_snippet(dict(base))
    assert_true(defaulted is not None and defaulted["pinned"] is False, defaulted)
    from_string = normalize_snippet({**base, "pinned": "true"})
    assert_true(from_string is not None and from_string["pinned"] is True, from_string)
    from_one = normalize_snippet({**base, "pinned": 1})
    assert_true(from_one is not None and from_one["pinned"] is True, from_one)
    from_json_true = normalize_snippet({**base, "pinned": True})
    assert_true(from_json_true is not None and from_json_true["pinned"] is True, from_json_true)
    leftover = normalize_snippet({**base, "pinned": "false"})
    assert_true(leftover is not None and leftover["pinned"] is False, leftover)


def test_sort_visible() -> None:
    items = [
        {"id": "a", "title": "alpha", "body": "x", "updated": "2026-01-03T00:00:00+00:00", "pinned": False},
        {"id": "b", "title": "beta", "body": "y", "updated": "2026-01-02T00:00:00+00:00", "pinned": True},
        {"id": "c", "title": "gamma", "body": "z", "updated": "2026-01-01T00:00:00+00:00", "pinned": True},
        {"id": "d", "title": "delta", "body": "w", "updated": "2026-01-04T00:00:00+00:00", "pinned": False},
        {"id": "e", "title": "epsilon", "body": "needle", "updated": "2026-01-05T00:00:00+00:00"},
    ]
    ordered = sort_visible(items, "")
    assert_true(
        [item["id"] for item in ordered] == ["b", "c", "e", "d", "a"],
        [item["id"] for item in ordered],
    )
    filtered = sort_visible(items, "needle")
    assert_true([item["id"] for item in filtered] == ["e"], [item["id"] for item in filtered])
    pinned_hit = sort_visible(items, "beta")
    assert_true([item["id"] for item in pinned_hit] == ["b"], [item["id"] for item in pinned_hit])
    both = sort_visible(
        [
            {"id": "old-pin", "title": "keep", "body": "zzz", "updated": "2026-01-01T00:00:00+00:00", "pinned": True},
            {"id": "new-unpin", "title": "keep", "body": "zzz", "updated": "2026-01-09T00:00:00+00:00", "pinned": False},
            {"id": "other", "title": "skip", "body": "no", "updated": "2026-01-10T00:00:00+00:00", "pinned": True},
        ],
        "keep",
    )
    assert_true(
        [item["id"] for item in both] == ["old-pin", "new-unpin"],
        [item["id"] for item in both],
    )
    missing_pin = {"id": "m", "title": "miss", "body": "", "updated": "2026-01-06T00:00:00+00:00"}
    mixed = sort_visible([items[1], missing_pin], "")
    assert_true([item["id"] for item in mixed] == ["b", "m"], [item["id"] for item in mixed])


def test_window_state() -> None:
    w, h = clamp_window_size(100, 50)
    assert_true((w, h) == (MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT), (w, h))
    w, h = clamp_window_size(2000, 1200)
    assert_true((w, h) == (2000, 1200), (w, h))
    w, h = clamp_window_size("nope", None)
    assert_true((w, h) == (DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT), (w, h))
    w, h = clamp_window_size(99_999, -3)
    assert_true(w <= 16384 and h == MIN_WINDOW_HEIGHT, (w, h))

    parsed = parse_window_state({"width": 800, "height": 600, "maximized": True})
    assert_true(parsed == {"width": 800, "height": 600, "maximized": True}, parsed)
    parsed = parse_window_state("junk")
    assert_true(parsed["width"] == DEFAULT_WINDOW_WIDTH, parsed)
    assert_true(parsed["maximized"] is False, parsed)
    parsed = parse_window_state({"width": -10, "height": 40, "maximized": "yes"})
    assert_true(parsed["width"] == MIN_WINDOW_WIDTH, parsed)
    assert_true(parsed["height"] == MIN_WINDOW_HEIGHT, parsed)
    assert_true(parsed["maximized"] is False, parsed)
    assert_true(
        load_window_state_text("not-json")["width"] == DEFAULT_WINDOW_WIDTH,
        "bad json",
    )
    payload = window_state_payload(900, 500, True)
    assert_true(payload == {"width": 900, "height": 500, "maximized": True}, payload)

    previous = os.environ.get("XDG_DATA_HOME")
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["XDG_DATA_HOME"] = tmp
        path = window_file()
        assert_true(path.name == "window.json", path)
        missing = load_window_state()
        assert_true(missing["width"] == DEFAULT_WINDOW_WIDTH, missing)
        save_window_state(900, 500, True)
        loaded = load_window_state()
        assert_true(loaded == {"width": 900, "height": 500, "maximized": True}, loaded)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert_true(data["width"] == 900, data)
        mode = stat.S_IMODE(path.stat().st_mode)
        assert_true(mode == 0o600, oct(mode))
        assert_true(not path.with_name(path.name + ".tmp").exists(), "tmp leftover")
        # snippets.json stays notes-only
        notes = snippets_file()
        if notes.exists():
            store = json.loads(notes.read_text(encoding="utf-8"))
            assert_true("width" not in store, store)
    if previous is None:
        os.environ.pop("XDG_DATA_HOME", None)
    else:
        os.environ["XDG_DATA_HOME"] = previous


def test_migrate_legacy_data() -> None:
    previous = os.environ.get("XDG_DATA_HOME")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["XDG_DATA_HOME"] = tmp
            old = Path(tmp) / OLD_APP_ID
            new = Path(tmp) / APP_ID
            old.mkdir()
            (old / "snippets.json").write_text('{"snippets": []}\n', encoding="utf-8")
            (old / "window.json").write_text(
                '{"width": 800, "height": 600, "maximized": false}\n',
                encoding="utf-8",
            )

            copied = migrate_legacy_data()
            assert_true(copied == ["snippets.json", "window.json"], copied)
            assert_true((new / "snippets.json").is_file(), "new snippets")
            assert_true((new / "window.json").is_file(), "new window")
            assert_true((old / "snippets.json").is_file(), "old snippets kept")
            assert_true((old / "window.json").is_file(), "old window kept")
            assert_true(
                str((new / "snippets.json").resolve()).startswith(str(Path(tmp).resolve())),
                "escaped XDG",
            )
            assert_true(
                (new / "snippets.json").read_text(encoding="utf-8")
                == (old / "snippets.json").read_text(encoding="utf-8"),
                "content",
            )

            copied = migrate_legacy_data()
            assert_true(copied == [], copied)

        with tempfile.TemporaryDirectory() as tmp:
            os.environ["XDG_DATA_HOME"] = tmp
            old = Path(tmp) / OLD_APP_ID
            new = Path(tmp) / APP_ID
            old.mkdir()
            new.mkdir()
            (old / "snippets.json").write_text('{"snippets": ["old"]}\n', encoding="utf-8")
            (old / "window.json").write_text('{"width": 1}\n', encoding="utf-8")
            (new / "snippets.json").write_text('{"snippets": ["new"]}\n', encoding="utf-8")
            copied = migrate_legacy_data()
            assert_true(copied == [], copied)
            assert_true(
                (new / "snippets.json").read_text(encoding="utf-8") == '{"snippets": ["new"]}\n',
                "must not overwrite",
            )
            assert_true(not (new / "window.json").exists(), "do not copy window if new store exists")

        with tempfile.TemporaryDirectory() as tmp:
            os.environ["XDG_DATA_HOME"] = tmp
            old = Path(tmp) / OLD_APP_ID
            new = Path(tmp) / APP_ID
            old.mkdir()
            (old / "window.json").write_text('{"width": 900, "height": 500}\n', encoding="utf-8")
            copied = migrate_legacy_data()
            assert_true(copied == ["window.json"], copied)
            assert_true((new / "window.json").is_file(), "window only")
            assert_true(not (new / "snippets.json").exists(), "no snippets in old")

        with tempfile.TemporaryDirectory() as tmp:
            os.environ["XDG_DATA_HOME"] = tmp
            copied = migrate_legacy_data()
            assert_true(copied == [], "no old dir")
            assert_true(not (Path(tmp) / APP_ID).exists(), "must not create new dir")

        with tempfile.TemporaryDirectory() as tmp:
            os.environ["XDG_DATA_HOME"] = tmp
            old = Path(tmp) / OLD_APP_ID
            new = Path(tmp) / APP_ID
            old.mkdir()
            (old / "notes.json").write_text(
                '{"notes": [{"title": "legacy", "body": "hi", "format": "text"}]}\n',
                encoding="utf-8",
            )
            copied = migrate_legacy_data()
            assert_true(copied == ["notes.json"], copied)
            assert_true((new / "notes.json").is_file(), "notes copied")
            assert_true((old / "notes.json").is_file(), "old notes kept")
            assert_true(
                not (new / "snippets.json").exists(),
                "migrate must not invent snippets.json",
            )
            assert_true(
                (new / "notes.json").read_text(encoding="utf-8")
                == (old / "notes.json").read_text(encoding="utf-8"),
                "notes content",
            )

        with tempfile.TemporaryDirectory() as tmp:
            os.environ["XDG_DATA_HOME"] = tmp
            old = Path(tmp) / OLD_APP_ID
            new = Path(tmp) / APP_ID
            old.mkdir()
            new.mkdir()
            (old / "notes.json").write_text('{"notes": ["old"]}\n', encoding="utf-8")
            (old / "snippets.json").write_text('{"snippets": ["old"]}\n', encoding="utf-8")
            (new / "snippets.json").write_text('{"snippets": ["new"]}\n', encoding="utf-8")
            copied = migrate_legacy_data()
            assert_true(copied == ["notes.json"], copied)
            assert_true(
                (new / "snippets.json").read_text(encoding="utf-8")
                == '{"snippets": ["new"]}\n',
                "must not overwrite snippets",
            )
            assert_true(
                (new / "notes.json").read_text(encoding="utf-8") == '{"notes": ["old"]}\n',
                "notes copied beside existing snippets",
            )
            (old / "notes.json").write_text('{"notes": ["newer"]}\n', encoding="utf-8")
            copied = migrate_legacy_data()
            assert_true(copied == [], copied)
            assert_true(
                (new / "notes.json").read_text(encoding="utf-8") == '{"notes": ["old"]}\n',
                "must not overwrite notes",
            )
            assert_true(
                (new / "snippets.json").read_text(encoding="utf-8")
                == '{"snippets": ["new"]}\n',
                "snippets still not overwritten",
            )
    finally:
        if previous is None:
            os.environ.pop("XDG_DATA_HOME", None)
        else:
            os.environ["XDG_DATA_HOME"] = previous


def test_choose_initial_snippets() -> None:
    items = [{"id": "real"}]
    legacy = [{"id": "old"}]

    got, write = choose_initial_snippets(
        False, [], False, False, [], False
    )
    assert_true(got == [], got)
    assert_true(write is True, write)

    got, write = choose_initial_snippets(
        True, [], True, True, legacy, True
    )
    assert_true(got == [], got)
    assert_true(write is False, write)

    got, write = choose_initial_snippets(
        True, items, True, True, legacy, True
    )
    assert_true(got == items, got)
    assert_true(write is False, write)

    got, write = choose_initial_snippets(
        True, items, False, True, legacy, True
    )
    assert_true(got == [], got)
    assert_true(write is False, write)

    got, write = choose_initial_snippets(
        False, [], False, True, legacy, True
    )
    assert_true(got == legacy, got)
    assert_true(write is True, write)

    got, write = choose_initial_snippets(
        False, [], False, True, [], True
    )
    assert_true(got == [], got)
    assert_true(write is True, write)

    got, write = choose_initial_snippets(
        False, [], False, False, [], False
    )
    assert_true(got == [], got)
    assert_true(write is True, write)

    got, write = choose_initial_snippets(
        False, [], False, True, [], False
    )
    assert_true(got == [], got)
    assert_true(write is True, write)


def main() -> int:
    test_schema_skips_garbage()
    test_body_cap()
    test_normalize_skips_non_dict()
    test_path_escape_and_atomic_write()
    test_restore_at_index()
    test_normalize_pinned()
    test_sort_visible()
    test_window_state()
    test_migrate_legacy_data()
    test_choose_initial_snippets()
    print("ok  store schema, cap, atomic write, restore_at_index, pinned, sort_visible, window_state, migrate, choose_initial")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

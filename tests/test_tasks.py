from datetime import date

from zktatr.db import split_open, split_today
from zktatr.models import Note, Task

TODAY = date(2026, 11, 11)


def task(**kw) -> Task:
    return Task.from_note(Note(path="tasks/x.md", title=kw.pop("title", "t"), meta=kw))


def test_open_shows_every_open_task_sorted_by_priority():
    ts = [
        task(title="future", due="2026-11-12", priority=10),
        task(title="late", due="2026-11-09", priority=20),
        task(title="nodue", priority=90),
        task(title="done", status="done", done="2026-11-01"),
    ]
    todo, _ = split_open(ts, TODAY)
    assert [t.title for t in todo] == ["nodue", "late", "future"]


def test_today_is_due_today_and_overdue_same_order_as_open():
    ts = [
        task(title="future", due="2026-11-12", priority=99),
        task(title="late", due="2026-11-09", priority=20),
        task(title="now", due="2026-11-11", priority=80),
        task(title="nodue", priority=90),
    ]
    todo, _ = split_today(ts, TODAY)
    assert [t.title for t in todo] == ["now", "late"]  # priority, not overdue-first


def test_done_today_only():
    ts = [
        task(title="a", status="done", done="2026-11-11"),
        task(title="b", status="done", done="2026-11-10"),
    ]
    for split in (split_open, split_today):
        todo, done = split(ts, TODAY)
        assert not todo and [t.title for t in done] == ["a"]


def test_messy_frontmatter():
    t = task(status=None, priority="high", tags="x", link=["http://l"], due="garbage")
    assert (t.status, t.priority, t.tags, t.link, t.due) == ("open", 50, [], "http://l", None)


# --- subtasks / dependencies -------------------------------------------------
from zktatr.tree import Row, build_rows


def node(stem, **kw) -> Task:
    return Task.from_note(Note(path=f"tasks/{stem}.md", title=kw.pop("title", stem), meta=kw))


def shape(tasks, today=TODAY, split=split_open):
    todo, _ = split(tasks, today)
    return [(r.task.title, r.depth) for r in build_rows(tasks, todo)]


def test_multi_level_tree_and_ref_styles():
    a = node("2026-11-11-aaaaaaaa", title="A", depends=["2026-11-11-bbbbbbbb"])
    b = node("2026-11-11-bbbbbbbb", title="B", depends=[["cccccccc"]])  # [[wikilink]] style
    c = node("2026-11-11-cccccccc", title="C", depends="tasks/2026-11-11-dddddddd.md")
    d = node("2026-11-11-dddddddd", title="D")
    assert shape([d, c, b, a]) == [("A", 0), ("B", 1), ("C", 2), ("D", 3)]


def test_done_subtask_hidden_but_counted():
    a = node("2026-11-11-aaaaaaaa", title="A", depends=["bbbbbbbb", "cccccccc"])
    b = node("2026-11-11-bbbbbbbb", title="B", status="done", done="2026-11-01")
    c = node("2026-11-11-cccccccc", title="C")
    todo, _ = split_open([a, b, c], TODAY)
    rows = build_rows([a, b, c], todo)
    assert [(r.task.title, r.depth) for r in rows] == [("A", 0), ("C", 1)]
    assert (rows[0].done_deps, rows[0].total_deps) == (1, 2)


def test_child_with_future_due_hidden_not_orphaned_parent():
    a = node("2026-11-11-aaaaaaaa", title="A", due="2026-11-11")
    b = node("2026-11-11-bbbbbbbb", title="B", depends=["aaaaaaaa"], due="2026-12-01")
    assert shape([a, b], split=split_today) == [("A", 0)]
    assert shape([a, b]) == [("B", 0), ("A", 1)]  # `todo` shows everything


def test_cycles_and_unknown_refs_do_not_hang():
    a = node("2026-11-11-aaaaaaaa", title="A", depends=["bbbbbbbb", "nope", "aaaaaaaa"])
    b = node("2026-11-11-bbbbbbbb", title="B", depends=["aaaaaaaa"])
    out = shape([a, b])
    assert sorted(t for t, _ in out) == ["A", "B"]


def test_duplicate_titles_are_not_resolved_by_title():
    a = node("2026-11-11-aaaaaaaa", title="A", depends=["Dup"])
    d1 = node("2026-11-10-dddddddd", title="Dup")
    d2 = node("2026-11-11-eeeeeeee", title="Dup")
    assert [d for _, d in shape([a, d1, d2])] == [0, 0, 0]


from zktatr.tree import group_rows


def test_group_by_tag_set_children_follow_parent():
    a = node("2026-11-11-aaaaaaaa", title="A", tags=["x", "y"], depends=["bbbbbbbb"])
    b = node("2026-11-11-bbbbbbbb", title="B", tags=["z"])  # own tag ignored
    c = node("2026-11-11-cccccccc", title="C", tags=["x"])
    d = node("2026-11-11-dddddddd", title="D")
    e = node("2026-11-11-eeeeeeee", title="E", tags=["w"])
    tasks = [a, b, c, d, e]
    todo, _ = split_open(tasks, TODAY)
    groups = group_rows(build_rows(tasks, todo))
    assert [(k, [r.task.title for r in rows]) for k, rows in groups] == [
        ("x y", ["A", "B"]),
        ("w", ["E"]),
        ("x", ["C"]),
        (None, ["D"]),
    ]


from zktatr import pick as pk


def test_fzf_input_is_path_then_plain_text():
    a = node("2026-11-11-aaaaaaaa", title="A", tags=["x"], due="2026-11-09", depends=["bbbbbbbb"])
    b = node("2026-11-11-bbbbbbbb", title="B")
    todo, _ = split_open([a, b], TODAY)
    lines = pk.fzf_input(build_rows([a, b], todo), TODAY).splitlines()
    assert lines[0] == "tasks/2026-11-11-aaaaaaaa.md\t50 A 0/1 ! #x"
    assert lines[1].startswith("tasks/2026-11-11-bbbbbbbb.md\t50 └─ B")


def test_zk_edit_gets_all_paths_in_one_call(monkeypatch, tmp_path):
    monkeypatch.setenv("ZK_NOTEBOOK_DIR", str(tmp_path))
    cmd = pk.zk_edit_command(["tasks/a.md", "tasks/b.md"])
    assert cmd == ["zk", "edit", "--notebook-dir", str(tmp_path),
                   str(tmp_path / "tasks/a.md"), str(tmp_path / "tasks/b.md")]


import time
from datetime import datetime

from zktatr.models import local_date


def test_done_and_edited_today_counts_even_without_done_field():
    mod = datetime.now().astimezone().isoformat(sep=" ")
    t = Task.from_note(Note(path="tasks/x.md", title="t", meta={"status": "done"}, modified=mod))
    todo, done = split_open([t], date.today())
    assert not todo and done == [t]


def test_open_task_edited_today_is_not_done_today():
    mod = datetime.now().astimezone().isoformat(sep=" ")
    t = Task.from_note(Note(path="tasks/x.md", title="t", meta={"status": "open"}, modified=mod))
    assert split_open([t], date.today())[1] == []


def test_done_edited_earlier_is_not_done_today():
    t = Task.from_note(Note(path="tasks/x.md", title="t", meta={"status": "done"},
                            modified="2026-11-01 10:00:00.123456789+00:00"))
    assert split_open([t], TODAY)[1] == []


def test_modified_is_converted_from_utc_to_local_date(monkeypatch):
    monkeypatch.setenv("TZ", "Europe/Copenhagen")
    time.tzset()
    try:
        # 23:30 UTC on the 10th is 00:30 on the 11th in Copenhagen (UTC+1).
        assert local_date("2026-11-10 23:30:00.972759539+00:00") == date(2026, 11, 11)
        assert local_date("garbage") is None and local_date("") is None
    finally:
        monkeypatch.undo()
        time.tzset()


def test_markup_escape_keeps_bracketed_text():
    from textual.content import Content

    from zktatr.app import escape

    for s in ["[X] done", "[WIP] fix", "[workflow] onboard", "plain"]:
        assert Content.from_markup(escape(s)).plain == s


def test_priority_100_shows_bang():
    from zktatr.app import render_task

    def line(prio):
        t = node("2026-11-11-aaaaaaaa", title="A", priority=prio)
        return render_task(build_rows([t], [t])[0], TODAY)

    assert "[dim]![/]" in line(100)
    for prio in (25, 50, 75):
        assert "[dim]-[/]" in line(prio) and "!" not in line(prio)


def test_fzf_input_includes_finished_with_marker():
    a = node("2026-11-11-aaaaaaaa", title="A")
    d = node("2026-11-11-dddddddd", title="D", status="done", tags=["x"])
    rows = build_rows([a], [a]) + [Row(d, 0, "", 0, 0)]
    lines = pk.fzf_input(rows, TODAY).splitlines()
    assert lines[1] == "tasks/2026-11-11-dddddddd.md\tX D #x"

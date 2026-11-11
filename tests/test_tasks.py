from datetime import date

from task_tui.db import split_today
from task_tui.models import Note, Task

TODAY = date(2026, 11, 11)


def task(**kw) -> Task:
    return Task.from_note(Note(path="tasks/x.md", title=kw.pop("title", "t"), meta=kw))


def test_no_due_date_counts_as_todo():
    todo, done = split_today([task(status="open")], TODAY)
    assert len(todo) == 1 and not done


def test_future_due_hidden_overdue_first():
    ts = [
        task(title="future", due="2026-11-12"),
        task(title="late", due="2026-11-09", priority=1),
        task(title="nodue", priority=90),
    ]
    todo, _ = split_today(ts, TODAY)
    assert [t.title for t in todo] == ["late", "nodue"]


def test_done_today_only():
    ts = [
        task(title="a", status="done", done="2026-11-11"),
        task(title="b", status="done", done="2026-11-10"),
    ]
    todo, done = split_today(ts, TODAY)
    assert not todo and [t.title for t in done] == ["a"]


def test_messy_frontmatter():
    t = task(status=None, priority="high", tags="x", link=["http://l"], due="garbage")
    assert (t.status, t.priority, t.tags, t.link, t.due) == ("open", 50, [], "http://l", None)


# --- subtasks / dependencies -------------------------------------------------
from task_tui.tree import build_rows


def node(stem, **kw) -> Task:
    return Task.from_note(Note(path=f"tasks/{stem}.md", title=kw.pop("title", stem), meta=kw))


def shape(tasks, today=TODAY):
    todo, _ = split_today(tasks, today)
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
    todo, _ = split_today([a, b, c], TODAY)
    rows = build_rows([a, b, c], todo)
    assert [(r.task.title, r.depth) for r in rows] == [("A", 0), ("C", 1)]
    assert (rows[0].done_deps, rows[0].total_deps) == (1, 2)


def test_child_with_future_due_hidden_not_orphaned_parent():
    a = node("2026-11-11-aaaaaaaa", title="A")
    b = node("2026-11-11-bbbbbbbb", title="B", depends=["aaaaaaaa"], due="2026-12-01")
    assert shape([a, b]) == [("A", 0)]


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

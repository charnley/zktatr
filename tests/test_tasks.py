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

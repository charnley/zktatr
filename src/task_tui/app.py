"""Textual TUI: today's tasks in a centered panel."""
from __future__ import annotations

from datetime import date

from rich.markup import escape
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Static

from .db import db_path, tasks_today
from .models import Task


def render_task(t: Task, today: date) -> str:
    text = f"[dim]{t.priority:>3}[/]  {escape(t.title)}"
    if t.due and t.due < today:
        text += f" [red]overdue {(today - t.due).days}d[/]"
    elif t.due == today:
        text += " [yellow]due today[/]"
    if t.tags:
        text += " [#808080]" + escape(" ".join(f"#{x}" for x in t.tags)) + "[/]"
    return text


class TaskApp(App):
    TITLE = "Tasks"
    CSS = """
    Screen { align: center middle; }
    #panel {
        width: 90%;
        max-width: 100;
        height: 90%;
        padding: 1 2;
    }
    .section { text-style: bold; margin-top: 1; }
    #todo-title { margin-top: 0; }
    #todo-title { color: $warning; }
    #done-title { color: $success; }
    """
    BINDINGS = [
        Binding("ctrl+d", "quit", "Quit", show=False),
        # Textual binds ctrl+q to quit by default; it clashes with tmux.
        Binding("ctrl+q", "noop", show=False),
        Binding("r", "refresh_tasks", "Refresh", show=False),
    ]

    POLL_SECONDS = 1.0

    def compose(self) -> ComposeResult:
        with Vertical(id="panel"):
            with VerticalScroll():
                yield Static(id="todo-title", classes="section")
                yield Static(id="todo")
                yield Static(id="done-title", classes="section")
                yield Static(id="done")

    def on_mount(self) -> None:
        self._seen = self._fingerprint()
        self.action_refresh_tasks()
        self.set_interval(self.POLL_SECONDS, self._poll)

    def _fingerprint(self) -> tuple:
        """Changes whenever zk writes the index (or the day rolls over)."""
        db = db_path()
        parts: list = [date.today()]
        for f in (db, db.with_name(db.name + "-wal")):
            try:
                st = f.stat()
                parts.append((st.st_mtime_ns, st.st_size))
            except FileNotFoundError:
                parts.append(None)
        return tuple(parts)

    def _poll(self) -> None:
        fp = self._fingerprint()
        if fp != self._seen:
            self._seen = fp
            self.action_refresh_tasks()

    def action_noop(self) -> None:
        pass

    def action_refresh_tasks(self) -> None:
        today = date.today()
        todo, done = tasks_today(today)
        self.query_one("#todo-title", Static).update(f"To do ({len(todo)})")
        self.query_one("#todo", Static).update(
            "\n".join(render_task(t, today) for t in todo) or "[dim]nothing left, nice[/]"
        )
        self.query_one("#done-title", Static).update(f"Done today ({len(done)})")
        self.query_one("#done", Static).update(
            "\n".join(f"[green]✓[/]    {escape(t.title)}" for t in done)
            or "[dim]nothing yet[/]"
        )

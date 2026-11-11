"""Textual TUI: today's tasks in a centered panel."""

from datetime import date

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Static

from .db import db_path, load_tasks, split_today
from .models import Task
from .pick import open_in_editor, pick
from .tree import Row, build_rows, group_rows


def escape(text: str) -> str:
    """Make `text` literal in Textual markup.

    Neither rich's nor textual's `escape` handles tags like `[X]` or `[WIP]`,
    which Textual would swallow, so escape every opening bracket.
    """
    return text.replace("[", "\\[")


def render_task(row: Row, today: date, hide_tag: str | None = None) -> str:
    t = row.task
    text = f"[dim]{t.priority:>3}[/]  [#808080]{escape(row.prefix)}[/]{escape(t.title)}"
    if row.total_deps:
        text += f" [#808080]{row.done_deps}/{row.total_deps}[/]"
    if t.due and t.due < today:
        text += f" [red]overdue {(today - t.due).days}d[/]"
    elif t.due == today:
        text += " [yellow]due today[/]"
    tags = [x for x in t.tags if x != hide_tag]
    if tags:
        text += " [#808080]" + escape(" ".join(f"#{x}" for x in tags)) + "[/]"
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
    """
    BINDINGS = [
        Binding("ctrl+d", "quit", "Quit", show=False),
        # Textual binds ctrl+q to quit by default; it clashes with tmux.
        Binding("ctrl+q", "noop", show=False),
        Binding("r", "refresh_tasks", "Refresh", show=False),
        Binding("enter", "pick", "Open", show=False),
        Binding("slash", "pick", "Open", show=False),
    ]

    POLL_SECONDS = 1.0

    def __init__(self, group: str | None = None) -> None:
        super().__init__()
        self.group = group
        self._pick_rows: list[Row] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="panel"):
            with VerticalScroll():
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

    def action_pick(self) -> None:
        if not self._pick_rows:
            return
        try:
            with self.suspend():
                paths = pick(self._pick_rows, date.today())
                if paths:
                    open_in_editor(paths)
        except RuntimeError as e:
            self.notify(str(e), severity="error")
        self._seen = None  # edits re-index; make sure the next poll reloads
        self.action_refresh_tasks()

    def action_noop(self) -> None:
        pass

    def _render_todo(self, rows: list[Row], today: date) -> str:
        if self.group != "tag":
            return "\n".join(render_task(r, today) for r in rows)
        blocks = []
        for key, group in group_rows(rows):
            header = f"[bold #808080]{escape(key) if key else 'untagged'} ({len(group)})[/]"
            lines = "\n".join(render_task(r, today, hide_tag=key) for r in group)
            blocks.append(header + "\n" + lines)
        return "\n\n".join(blocks)

    def action_refresh_tasks(self) -> None:
        today = date.today()
        tasks = load_tasks()
        todo, done = split_today(tasks, today)
        rows = build_rows(tasks, todo)
        # fzf lists tasks in the same order as the screen.
        self._pick_rows = (
            [r for _, g in group_rows(rows) for r in g] if self.group == "tag" else rows
        )
        self.query_one("#todo", Static).update(
            self._render_todo(rows, today) or "[dim]nothing left, nice[/]"
        )
        self.query_one("#done-title", Static).update("Finished:")
        self.query_one("#done", Static).update(
            "\n".join(f"[dim]{escape('[X]')}  {escape(t.title)}[/]" for t in done)
            or "[dim]nothing yet[/]"
        )

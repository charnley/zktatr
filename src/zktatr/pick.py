"""fzf picker + `zk edit` hand-off."""

import shutil
import subprocess
from datetime import date
from pathlib import Path

from .db import notebook_dir
from .tree import Row

# With a query typed, enter takes every match; with none, only the highlighted
# line (tab still marks individual lines either way).
ENTER = "enter:transform:[ -n {q} ] && echo select-all+accept || echo accept"
HEADER = "enter: open all matches  tab: mark  esc: cancel"


def fzf_input(rows: list[Row], today: date) -> str:
    """`path<TAB>text` per task; fzf only shows and searches the text."""
    lines = []
    for r in rows:
        t = r.task
        text = f"{t.priority:>3}  {r.prefix}{t.title}"
        if r.total_deps:
            text += f" {r.done_deps}/{r.total_deps}"
        if t.due and t.due < today:
            text += f" overdue {(today - t.due).days}d"
        elif t.due == today:
            text += " due today"
        if t.tags:
            text += " " + " ".join(f"#{x}" for x in t.tags)
        text = " ".join(text.split())  # no tabs/newlines inside a field
        lines.append(f"{t.path}\t{text}")
    return "\n".join(lines) + "\n"


def fzf_command() -> list[str]:
    return [
        "fzf", "--multi", "--exact", "--layout=reverse", "--no-sort", "--tiebreak=index",
        "--delimiter=\t", "--with-nth=2..", "--prompt=task> ", f"--header={HEADER}",
        f"--bind={ENTER}",
    ]  # fmt: skip


def pick(rows: list[Row], today: date) -> list[str]:
    """Run fzf over `rows`; returns selected note paths (empty on cancel)."""
    if shutil.which("fzf") is None:
        raise RuntimeError("fzf not found on PATH")
    # fzf draws on /dev/tty, so capturing stdout does not disturb the UI.
    res = subprocess.run(
        fzf_command(), input=fzf_input(rows, today), text=True, stdout=subprocess.PIPE
    )
    if res.returncode != 0:  # 1 = no match, 130 = cancelled
        return []
    return [line.split("\t", 1)[0] for line in res.stdout.splitlines() if line]


def zk_edit_command(paths: list[str]) -> list[str]:
    nb = notebook_dir()
    return ["zk", "edit", "--notebook-dir", str(nb), *(str(Path(nb, p)) for p in paths)]


def open_in_editor(paths: list[str]) -> None:
    """One `zk edit` call, so zk's configured editor gets all files at once."""
    if shutil.which("zk") is None:
        raise RuntimeError("zk not found on PATH")
    res = subprocess.run(zk_edit_command(paths))
    if res.returncode != 0:
        raise RuntimeError(f"zk edit exited with {res.returncode}")
